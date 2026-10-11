-- HD2-Addon: mods/modocracy/personal_booster
-- Personal Booster for Helldivers 2.
--
-- The game allows one booster per player. This mod keeps that rule but lets this
-- player choose all of them: with N players in the squad, picks 1 to N are active
-- for this player, and the boosters teammates brought are not. Teammates keep
-- their own boosters on their own PCs.
--
-- How: the game decides whether a booster is active with one small function that
-- looks through the boosters the game grants (the DSS list) and then each squad
-- member's equipped booster. This mod rewrites only the squad's equipped boosters
-- in this PC's memory, 1 slot per player. The DSS list and game code are left as
-- they are. Anything that does not match what the mod expects stops it before it
-- writes.
--
-- Picking: in Options > MODS when Mod Options Menu (Vanilla Plus Megapack) is
-- installed, otherwise by editing PersonalBooster.order (one booster per line) in
-- %LOCALAPPDATA%\PersonalBooster.
--
-- Starting: Bingus Shared Loader finds and starts this resource by its first line.
-- Without it, this mod's own Wwise callbacks bridge starts it (see tools/build.py).
--
-- Released under the Zero-Clause BSD license.

local MOD_ID = 'modocracy.personal_booster'
local FOLDER_NAME = 'PersonalBooster'
local MAX_PICKS = 4
-- Picked until the player picks, and when nothing else is saved.
local DEFAULT_PICKS = {'HellpodSpaceOptimization', 'Vitality', 'Stamina', 'MuscleEnhancement'}
-- Boosters the host's game applies to the whole squad (mission budget, encounters,
-- extraction, samples). A slot the game filled with one of these is left alone, so
-- a teammate's pick still works for everyone when this player hosts.
local HOST_DECIDED = {'IncreasedReinforcementBudget', 'FlexibleReinforcementBudget', 'LocalizationConfusion',
                      'FastExtraction', 'DoubleSampleChance', 'BigEnemiesDropSamples'}
local CHECK_EVERY = 2000 -- milliseconds between memory checks
local ORDER_EVERY = 5 -- memory checks between rereads of the order file without the menu

-- Internal name, English name, Korean name, English effect, Korean effect.
local BOOSTERS = {
    {'HellpodSpaceOptimization', 'Hellpod Space Optimization', '헬포드 공간 최적화',
     'Full magazines, grenades and stims on drop and reinforce.', '투하하거나 증원될 때 탄창, 수류탄, 주사기가 가득 채워집니다.'},
    {'Vitality', 'Vitality Enhancement', '체력 강화', 'Less damage taken.', '받는 피해가 줄어듭니다.'},
    {'Stamina', 'Stamina Enhancement', '스태미나 강화', 'More stamina and faster recovery.',
     '스태미나가 늘고 더 빨리 회복됩니다.'},
    {'MuscleEnhancement', 'Muscle Enhancement', '근력 강화', 'Weaker terrain slow.', '지형 때문에 느려지는 효과가 약해집니다.'},
    {'UAVRecon', 'UAV Recon Booster', 'UAV 정찰 부스터', 'Wider radar.', '레이더 범위가 넓어집니다.'},
    {'IncreasedReinforcementBudget', 'Increased Reinforcement Budget', '증원 예산 증가',
     'More reinforcements. Decided by the host.', '증원 횟수가 늘어납니다. 방장이 판정합니다.'},
    {'FlexibleReinforcementBudget', 'Flexible Reinforcement Budget', '유연한 증원 예산',
     'Reinforcements recover faster. Decided by the host.', '증원이 더 빨리 회복됩니다. 방장이 판정합니다.'},
    {'LocalizationConfusion', 'Localization Confusion', '위치 혼란', 'Fewer encounters. Decided by the host.',
     '적과 마주치는 일이 줄어듭니다. 방장이 판정합니다.'},
    {'FastExtraction', 'Expert Extraction Pilot', '숙련된 추출 파일럿',
     'Shorter extraction call-in. Decided by the host.', '추출선 호출 시간이 짧아집니다. 방장이 판정합니다.'},
    {'SlowStunResistance', 'Motivational Shocks', '동기부여 충격', 'Weaker slow and stun.', '감속과 기절 효과가 약해집니다.'},
    {'CombatDrugs', 'Experimental Infusion', '실험용 주입', 'Stims apply a stronger effect.', '주사기 효과가 강해집니다.'},
    {'FieryDrop', 'Firebomb Hellpods', '파이어밤 헬포드', 'Fire explosion when a hellpod lands.',
     '헬포드가 착지할 때 화염 폭발이 일어납니다.'},
    {'DoubleSampleChance', 'Sample Scanner', '샘플 스캐너', 'A chance that a picked-up sample counts twice. Decided by the host.',
     '주운 샘플이 두 개로 계산될 확률이 생깁니다. 방장이 판정합니다.'},
    {'DeathMarch', 'Dead Sprint', '데드 스프린트', 'Sprint with no stamina, at the cost of health.',
     '스태미나가 없어도 체력을 써서 달릴 수 있습니다.'},
    {'BigEnemiesDropSamples', 'Sample Extricator', '샘플 추출기', 'Heavy enemies drop samples. Decided by the host.',
     '대형 적이 샘플을 떨어뜨립니다. 방장이 판정합니다.'},
    {'ShockPods', 'Stun Pods', '스턴 포드', 'Stun when a hellpod lands.', '헬포드가 착지할 때 주변을 기절시킵니다.'},
    {'SmokePods', 'Concealed Insertion', '은밀 강하', 'Smoke when a hellpod lands.', '헬포드가 착지할 때 연막이 퍼집니다.'},
    {'FireExtinguish', 'Integrated Extinguishers', '통합 소화기', 'Burning ends faster.', '몸에 붙은 불이 더 빨리 꺼집니다.'},
}

-- The booster check, from the start of the function. ?? marks bytes the game
-- build decides: three rip-relative globals and the struct offsets the mod reads.
--   00 mov rcx, [mode]            07 mov rax, [dss list]
--   0E-19 in one mode, jump to 60 (nothing is active)
--   1A mov r9d, [rax+count]       1E-37 search the DSS list, 8 bytes per entry
--   38 mov rax, [squad]           3F mov r8d, [rax+players]
--   4B add rax, slots             51-5F search one slot per player, stride bytes apart
--   60 xor al, al / ret           63 mov al, 1 / ret
local CHECK_PATTERN = [[
    48 8B 0D ?? ?? ?? ??   48 8B 05 ?? ?? ?? ??   83 79 08 00   76 06   83 79 40 04   74 46
    44 8B 48 ??   33 C9   44 8B C1   45 85 C9   74 10   39 10   74 37   41 FF C0   48 83 C0 08
    45 3B C1   72 F0   48 8B 05 ?? ?? ?? ??   44 8B 80 ?? ?? ?? ??   45 85 C0   74 15
    48 05 ?? ?? ?? ??   39 10   74 0E   FF C1   48 83 C0 ??   41 3B C8   72 F1   32 C0 C3   B0 01 C3
]]
local CHECK_FIELDS = {
    mode = {rel32 = 0x03, ends = 0x07},
    dss = {rel32 = 0x0A, ends = 0x0E},
    squad = {rel32 = 0x3B, ends = 0x3F},
    dss_count = {u8 = 0x1D},
    players = {u32 = 0x42},
    slots = {u32 = 0x4D},
    stride = {u8 = 0x5A},
}
local NAME_ANCHOR = 'HellpodSpaceOptimization'

------------------------------------------------------------------------------------
-- Pure steps, free of memory access so they can be tested.

-- assert() without the source position, so log lines read as plain messages.
local function need(value, message)
    if not value then error(message, 0) end
    return value
end

-- want: picked booster ids in order. own: the id the game put in each squad slot.
-- keep: ids decided by the host (id -> true). Slots the game filled with a kept id
-- stay as they are; the other slots get the picks in order, skipping picks a kept
-- slot already holds, and are emptied past the picks. Returns the slots, the picks
-- written and the ids kept.
local function plan(want, own, keep)
    local target, active, kept, taken = {}, {}, {}, {}
    for i = 1, #own do
        if keep[own[i]] and not taken[own[i]] then
            target[i], taken[own[i]] = own[i], true
            kept[#kept + 1] = own[i]
        end
    end
    local next_pick = 1
    for i = 1, #own do
        if target[i] == nil then
            while want[next_pick] and taken[want[next_pick]] do next_pick = next_pick + 1 end
            local id = want[next_pick]
            target[i] = id or 0
            if id then
                active[#active + 1], taken[id], next_pick = id, true, next_pick + 1
            end
        end
    end
    return target, active, kept
end

local function differs(have, want)
    for i = 1, #want do
        if have[i] ~= want[i] then return true end
    end
    return false
end

-- The pick order after a booster is set to a place (0 removes it). The others
-- move down; one pushed past MAX_PICKS falls off.
local function placed(list, name, place)
    local out = {}
    for _, other in ipairs(list) do
        if other ~= name then out[#out + 1] = other end
    end
    if place > 0 then table.insert(out, math.min(place, #out + 1), name) end
    while #out > MAX_PICKS do table.remove(out) end
    return out
end

-- '48 8B ?? ...' -> {bytes = {0x48, 0x8B, false, ...}, anchor = longest fixed run, at = its start}
local function parse_pattern(text)
    local bytes = {}
    for token in text:gmatch('%S+') do
        bytes[#bytes + 1] = token ~= '??' and need(tonumber(token, 16), 'bad pattern byte ' .. token)
    end
    local best_from, best_length, from = 1, 0, nil
    for i = 1, #bytes + 1 do
        if bytes[i] then
            from = from or i
        elseif from then
            if i - from > best_length then best_from, best_length = from, i - from end
            from = nil
        end
    end
    local anchor = {}
    for i = best_from, best_from + best_length - 1 do anchor[#anchor + 1] = string.char(bytes[i]) end
    return {bytes = bytes, anchor = table.concat(anchor), at = best_from - 1}
end

local function pattern_matches(pattern, text)
    if #text < #pattern.bytes then return false end
    for i, byte in ipairs(pattern.bytes) do
        if byte and text:byte(i) ~= byte then return false end
    end
    return true
end

local function le(text, at, size, signed)
    local value = 0
    for i = size, 1, -1 do value = value * 256 + text:byte(at + i) end
    if signed and value >= 2 ^ (size * 8 - 1) then value = value - 2 ^ (size * 8) end
    return value
end

-- The fields of CHECK_FIELDS from the check's bytes found at address.
local function decode_check(text, address)
    local out = {}
    for name, field in pairs(CHECK_FIELDS) do
        if field.rel32 then
            out[name] = address + field.ends + le(text, field.rel32, 4, true)
        elseif field.u32 then
            out[name] = le(text, field.u32, 4)
        else
            out[name] = text:byte(field.u8 + 1)
        end
    end
    return out
end

-- Offsets the mod relies on, checked before anything is written.
local function sane_check(check)
    return check.players < 0x4000 and check.slots < 0x4000 and check.dss_count <= 0x80
        and check.stride >= 8 and check.stride % 8 == 0 and check.slots % 4 == 0 and check.players % 4 == 0
end

------------------------------------------------------------------------------------
-- State, files and log.

if rawget(_G, 'PersonalBooster') then return end
local picks = {}
for i, name in ipairs(DEFAULT_PICKS) do picks[i] = name end
local state = {version = '1.2.0', status = 'starting', picks = picks, plan = plan, differs = differs,
               placed = placed, parse_pattern = parse_pattern, decode_check = decode_check}
_G['PersonalBooster'] = state

local ffi, bit, win
local test = nil -- set by state.test_use

local function bind_windows()
    if win then return win end
    ffi = require('ffi')
    bit = rawget(_G, 'bit') or require('bit')
    if not pcall(ffi.typeof, 'pb_region') then
        ffi.cdef[[
            typedef struct {
                uintptr_t base, allocation_base;
                uint32_t allocation_protect, pad0;
                size_t size;
                uint32_t state, protect, type, pad1;
            } pb_region;
            void *pb_GetModuleHandleA(const char *) __asm__("GetModuleHandleA");
            void *pb_GetCurrentProcess(void) __asm__("GetCurrentProcess");
            uint64_t pb_GetTickCount64(void) __asm__("GetTickCount64");
            size_t pb_VirtualQuery(uintptr_t, pb_region *, size_t) __asm__("VirtualQuery");
            int pb_ReadProcessMemory(void *, uintptr_t, void *, size_t, size_t *) __asm__("ReadProcessMemory");
            int pb_WriteProcessMemory(void *, uintptr_t, const void *, size_t, size_t *) __asm__("WriteProcessMemory");
            int pb_CreateDirectoryA(const char *, void *) __asm__("CreateDirectoryA");
        ]]
    end
    need(ffi.sizeof('pb_region') == 48, 'unexpected MEMORY_BASIC_INFORMATION size')
    local k = ffi.load('kernel32')
    win = {k = k, process = k.pb_GetCurrentProcess(), info = ffi.new('pb_region[1]'),
           done = ffi.new('size_t[1]'), buffer = ffi.new('uint8_t[?]', 0x100000), cell = ffi.new('uint32_t[1]')}
    return win
end

local function folder()
    local base = os.getenv('LOCALAPPDATA')
    if not base then return nil end
    local path = base .. '\\' .. FOLDER_NAME
    pcall(function() bind_windows().k.pb_CreateDirectoryA(path, nil) end)
    return path
end

local log_file
local function log(message)
    state.status = message
    pcall(function()
        if log_file == nil then
            local where = test and test.folder or folder()
            log_file = where and io.open(where .. '\\' .. FOLDER_NAME .. '.log', 'w') or false
        end
        if log_file then
            log_file:write(os.date('%H:%M:%S ') .. message .. '\n')
            log_file:flush()
        end
    end)
end

local function index_in(list, value)
    for i = 1, #list do
        if list[i] == value then return i end
    end
end

local KNOWN = {}
for _, booster in ipairs(BOOSTERS) do KNOWN[booster[1]] = true end

local function set_picks(list)
    local names = {}
    for i, name in ipairs(list) do names[i] = name end -- list may be picks itself
    for i = #picks, 1, -1 do picks[i] = nil end
    for _, name in ipairs(names) do
        if KNOWN[name] and #picks < MAX_PICKS and not index_in(picks, name) then picks[#picks + 1] = name end
    end
end

local function picked_text()
    return #picks == 0 and 'none' or table.concat(picks, ', ')
end

local function order_path()
    local where = test and test.folder or folder()
    return where and (where .. '\\' .. FOLDER_NAME .. '.order')
end

-- The saved pick order, or nil when there is no file.
local function read_order()
    local path = order_path()
    local file = path and io.open(path, 'rb')
    if not file then return nil end
    local text = file:read('*a') or ''
    file:close()
    local names = {}
    for name in text:gmatch('[%w_]+') do names[#names + 1] = name end
    return names, text
end

local function save_order()
    local ok, err = pcall(function()
        local file = need(io.open(need(order_path(), 'no folder for the order file'), 'wb'))
        file:write(table.concat(picks, '\n') .. '\n')
        file:close()
    end)
    if not ok then log('pick order not saved: ' .. tostring(err)) end
end

local function korean()
    local translations = rawget(_G, 'BingusTranslations')
    local language = type(translations) == 'table' and translations.game_language
    return type(language) == 'string' and language:sub(1, 2) == 'ko'
end

------------------------------------------------------------------------------------
-- Picker in Options > MODS (Mod Options Menu). Row values are redrawn as soon as
-- code sets them, row names only when the escape menu opens, so the count and the
-- places are values: a first row shows the count (0/4-4/4), each booster row its
-- place (OFF, 1-4). Setting a place puts the booster there; the others move down.
-- Applied edits are handled in this mod's next update, after the menu has applied
-- all of them, and the rows then show the result.

-- Options > MODS comes from Mod Options Menu. Vanilla Plus Megapack's copy starts
-- before this mod when it is installed (Bingus Shared Loader starts the pack first);
-- otherwise the copy bundled with this mod starts here.
local BUNDLED_MENU = 'mods/modocracy/mod_options_menu'
if not rawget(_G, 'ModOptionsMenu') then
    local ok, err = pcall(require, BUNDLED_MENU)
    state.menu_start = ok and 'bundled' or ('bundled copy not started: ' .. tostring(err))
else
    state.menu_start = 'already running'
end

local COUNT_OPTION = 'personal_booster.count'
local PLACE_PREFIX = 'personal_booster.place.'
local PLACE_CHOICES = {'OFF', '1', '2', '3', '4'} -- choice = place + 1
local COUNT_CHOICES = {'0/4', '1/4', '2/4', '3/4', '4/4'} -- choice = count + 1
local menu = {api = nil, given_up = false, edits = {}, order_text = false, checks = 0}

local function show_picks()
    local api = menu.api
    for _, booster in ipairs(BOOSTERS) do
        local id, value = PLACE_PREFIX .. booster[1], (index_in(picks, booster[1]) or 0) + 1
        if api.get(id) ~= value then api.set(id, value) end
    end
    if api.get(COUNT_OPTION) ~= #picks + 1 then api.set(COUNT_OPTION, #picks + 1) end
end

local function apply_edits()
    local edits, before = menu.edits, picked_text()
    menu.edits = {}
    local list = picks
    for _, edit in ipairs(edits) do
        if edit.name and type(edit.value) == 'number' then list = placed(list, edit.name, edit.value - 1) end
    end
    set_picks(list)
    show_picks()
    if picked_text() ~= before then
        save_order()
        log('picked ' .. #picks .. '/' .. MAX_PICKS .. ': ' .. picked_text())
    end
end

local TAIL = {
    ' Set 1-4 to put it at that place; the others move down. OFF removes it.'
        .. ' One booster per player is active, from place 1: solo uses place 1, two players places 1-2.',
    ' 1~4를 고르면 그 순서에 들어가고 나머지는 한 칸씩 밀립니다. 끄기를 고르면 빠집니다.'
        .. ' 참가 인원 1명당 1개씩 1번부터 적용됩니다 (1명이면 1번, 2명이면 1~2번).',
}

local function register_rows(api)
    local function add(id, spec)
        spec.type, spec.mod, spec.mod_id = 'choice', 'Personal Booster', MOD_ID
        local ok, why = api.register_option(id, spec)
        if not ok then error(id .. ': ' .. tostring(why), 0) end
    end
    add(COUNT_OPTION, {
        label = function() return korean() and '선택한 부스터' or 'Picked boosters' end,
        choices = COUNT_CHOICES,
        default = 1,
        description = function()
            return korean() and '고른 부스터 수입니다. 아래 부스터에 순서(1~4)를 정하면 선택됩니다.'
                or 'How many boosters are picked. Give a booster below a place (1-4) to pick it.'
        end,
    })
    for row, booster in ipairs(BOOSTERS) do
        add(PLACE_PREFIX .. booster[1], {
            label = function() return korean() and booster[3] or booster[2] end,
            choices = PLACE_CHOICES,
            default = 1,
            gap = row == 1,
            description = function()
                return korean() and (booster[5] .. TAIL[2]) or (booster[4] .. TAIL[1])
            end,
        })
    end
end

-- Without a saved order, the rows' saved places give it; without those, the defaults.
local function first_picks(api)
    local saved = read_order()
    if saved then return saved end
    local ranked = {}
    for row, booster in ipairs(BOOSTERS) do
        local value = api and api.get(PLACE_PREFIX .. booster[1])
        if type(value) == 'number' and value > 1 then ranked[#ranked + 1] = {value, row, booster[1]} end
    end
    if #ranked == 0 then return DEFAULT_PICKS end
    table.sort(ranked, function(a, b) return a[1] < b[1] or (a[1] == b[1] and a[2] < b[2]) end)
    local list = {}
    for i, item in ipairs(ranked) do list[i] = item[3] end
    return list
end

local function start_menu()
    local api = rawget(_G, 'ModOptionsMenu')
    if type(api) ~= 'table' or type(api.register_option) ~= 'function' then return false end
    local ok, why = pcall(register_rows, api)
    if not ok then
        menu.given_up = true
        log('Options > MODS unavailable: ' .. tostring(why))
        return false
    end
    api.on_change(COUNT_OPTION, function() menu.edits[#menu.edits + 1] = {} end)
    for _, booster in ipairs(BOOSTERS) do
        local name = booster[1]
        api.on_change(PLACE_PREFIX .. name, function(value)
            menu.edits[#menu.edits + 1] = {name = name, value = value}
        end)
    end
    menu.api = api
    set_picks(first_picks(api))
    show_picks()
    save_order()
    log('picker ready in Options > MODS, picked ' .. #picks .. '/' .. MAX_PICKS .. ': ' .. picked_text())
    return true
end

-- Without the menu: the order file is the picker, reread every few checks.
local function reread_order()
    local names, text = read_order()
    if text == menu.order_text then return end
    menu.order_text = text
    if not names then
        save_order()
        menu.order_text = select(2, read_order())
        log('picked ' .. #picks .. '/' .. MAX_PICKS .. ': ' .. picked_text() .. ' (edit '
            .. tostring(order_path()) .. ' to change)')
        return
    end
    set_picks(names)
    log('picked ' .. #picks .. '/' .. MAX_PICKS .. ': ' .. picked_text() .. ' (from the order file)')
end

------------------------------------------------------------------------------------
-- Memory of this process.

local READABLE = {[0x02] = true, [0x04] = true, [0x08] = true, [0x20] = true, [0x40] = true, [0x80] = true}
local WRITABLE = {[0x04] = true, [0x08] = true, [0x40] = true, [0x80] = true}

-- The committed region holding address: base, end and access byte, or nil.
local function region(address)
    local w = bind_windows()
    if address < 0x10000 or w.k.pb_VirtualQuery(address, w.info, 48) == 0 then return nil end
    local r = w.info[0]
    if r.state ~= 0x1000 or bit.band(r.protect, 0x100) ~= 0 then return nil end
    local base = tonumber(r.base)
    return base, base + tonumber(r.size), bit.band(r.protect, 0xFF)
end

local function can(address, size, access)
    local first, last, kind = region(address)
    return first ~= nil and access[kind] == true and address + size <= last
end

local function read(address, size)
    local w = bind_windows()
    need(size > 0 and size <= 0x100000, 'read size')
    if w.k.pb_ReadProcessMemory(w.process, address, w.buffer, size, w.done) == 0
        or tonumber(w.done[0]) ~= size then
        error(string.format('cannot read %d bytes at 0x%X', size, address), 0)
    end
    return ffi.string(w.buffer, size)
end

local function u32(address) return le(read(address, 4), 0, 4) end
local function u64(address) return le(read(address, 8), 0, 8) end

local function write_u32(address, value)
    local w = bind_windows()
    w.cell[0] = value
    if w.k.pb_WriteProcessMemory(w.process, address, w.cell, 4, w.done) == 0 or tonumber(w.done[0]) ~= 4 then
        error(string.format('cannot write at 0x%X', address), 0)
    end
end

-- Calls visit(address) for every place in [from, to) where text occurs, reading
-- readable regions in chunks that overlap by #text - 1 bytes.
local function search(from, to, text, visit)
    local at = from
    while at < to do
        local first, last, kind = region(at)
        if not first then
            local w = bind_windows()
            if w.k.pb_VirtualQuery(at, w.info, 48) == 0 then return end
            at = tonumber(w.info[0].base) + tonumber(w.info[0].size)
        else
            local stop = math.min(last, to)
            if READABLE[kind] then
                local chunk_at = at
                while chunk_at < stop do
                    local size = math.min(0x100000, stop - chunk_at)
                    local chunk = read(chunk_at, size)
                    local i = 1
                    while true do
                        local found = chunk:find(text, i, true)
                        if not found then break end
                        visit(chunk_at + found - 1)
                        i = found + 1
                    end
                    if chunk_at + size >= stop then break end
                    chunk_at = chunk_at + size - (#text - 1)
                end
            end
            at = stop
        end
    end
end

------------------------------------------------------------------------------------
-- game.dll: its sections, the booster check and the booster name table.

local game = nil -- {base, sections, check, ids, names, count}

local function module_base()
    if test and test.base then return test.base end
    local handle = bind_windows().k.pb_GetModuleHandleA('game.dll')
    need(handle ~= nil, 'game.dll is not loaded yet')
    return tonumber(ffi.cast('uintptr_t', handle))
end

-- Section ranges from the PE headers in memory.
local function sections_of(base)
    local nt = base + u32(base + 0x3C)
    need(read(nt, 4) == 'PE\0\0', 'game.dll has no PE header')
    local header = read(nt + 4, 20)
    local count, optional_size = le(header, 2, 2), le(header, 16, 2)
    need(le(read(nt + 24, 2), 0, 2) == 0x20B, 'game.dll is not 64-bit')
    need(count > 0 and count < 64, 'unexpected section count')
    local table_at, out = nt + 24 + optional_size, {}
    for i = 0, count - 1 do
        local entry = read(table_at + i * 40, 40)
        local size, rva = le(entry, 8, 4), le(entry, 12, 4)
        if size > 0 then out[#out + 1] = {base + rva, base + rva + size} end
    end
    return out
end

local function find_check(sections)
    local pattern = parse_pattern(CHECK_PATTERN)
    local hits, seen = {}, {}
    for _, range in ipairs(sections) do
        search(range[1], range[2], pattern.anchor, function(found)
            local start = found - pattern.at
            if not seen[start] and can(start, #pattern.bytes, READABLE) then
                seen[start] = true
                local text = read(start, #pattern.bytes)
                if pattern_matches(pattern, text) then hits[#hits + 1] = {start, text} end
            end
        end)
    end
    need(#hits == 1, 'booster check found ' .. #hits .. ' times, nothing written')
    local check = decode_check(hits[1][2], hits[1][1])
    need(sane_check(check), 'booster check offsets look wrong, nothing written')
    return check
end

-- An identifier string at address, or nil.
local function name_at(address)
    local first, last, kind = region(address)
    if not first or not READABLE[kind] then return nil end
    return read(address, math.min(64, last - address)):match('^(%a[%w_]*)%z')
end

-- The name table holding the pointer at slot: pointers to 'None', the boosters and
-- 'Count', in that order. Returns name -> index and the index of 'Count'.
local function table_at(slot)
    local first = slot
    for _ = 1, 64 do
        local name = can(first, 8, READABLE) and name_at(u64(first))
        if not name then return nil end
        if name == 'None' then break end
        first = first - 8
    end
    local ids = {}
    for index = 0, 63 do
        local at = first + index * 8
        local name = can(at, 8, READABLE) and name_at(u64(at))
        if not name or (index == 0) ~= (name == 'None') then return nil end
        ids[name] = index
        if name == 'Count' then return ids, index end
    end
end

local function find_names(sections)
    local strings, found = {}, {}
    for _, range in ipairs(sections) do
        search(range[1], range[2], NAME_ANCHOR .. '\0', function(at) strings[#strings + 1] = at end)
    end
    for _, string_at in ipairs(strings) do
        local pointer = ffi.string(ffi.new('uint64_t[1]', string_at), 8)
        for _, range in ipairs(sections) do
            search(range[1], range[2], pointer, function(slot)
                if slot % 8 == 0 then
                    local ids, count = table_at(slot)
                    if ids then found[#found + 1] = {ids, count} end
                end
            end)
        end
    end
    need(#found >= 1, 'booster name table not found, nothing written')
    local ids, count = found[1][1], found[1][2]
    for _, other in ipairs(found) do
        need(other[2] == count, 'booster name tables disagree, nothing written')
        for name, index in pairs(other[1]) do
            need(ids[name] == index, 'booster name tables disagree, nothing written')
        end
    end
    for name in pairs(KNOWN) do
        need(ids[name] and ids[name] > 0 and ids[name] < count, 'booster ' .. name .. ' not in the name table')
    end
    return ids, count
end

local function find_game()
    local base = module_base()
    local sections = sections_of(base)
    local check = find_check(sections)
    local ids, count = find_names(sections)
    local names = {}
    for name, index in pairs(ids) do names[index] = name end
    log(string.format('ready: booster check found, %d boosters in the game, %d squad slot bytes apart',
        count - 1, check.stride))
    return {base = base, check = check, ids = ids, names = names, count = count}
end

------------------------------------------------------------------------------------
-- The memory step.

local squad_seen
local writes = 0
-- Per slot of the current squad record: the id this mod last wrote, and the id the
-- game last put there (any value other than this mod's own write).
local slot_memo = {wrote = {}, own = {}}

local function names_of(ids)
    local out = {}
    for i, id in ipairs(ids) do out[i] = id == 0 and '-' or (game.names[id] or tostring(id)) end
    return table.concat(out, ', ')
end

local function step()
    if rawget(_G, 'MissionBoosters') then error('Booster Buster is also installed, disable one of them', 0) end
    local check = game.check
    local squad_at = u64(check.squad)
    if squad_at == 0 or squad_at % 8 ~= 0 then return 'waiting for the squad' end
    if squad_at ~= squad_seen then
        squad_seen = squad_at
        slot_memo = {wrote = {}, own = {}}
        return 'squad found, checking again before writing'
    end
    if not can(squad_at + check.players, 4, READABLE) then return 'waiting for the squad' end
    local players = u32(squad_at + check.players)
    if players < 1 or players > 4 then return 'waiting for the squad' end
    local slots = squad_at + check.slots
    if not can(slots, check.stride * (players - 1) + 4, READABLE) then return 'waiting for the squad' end
    local squad = {}
    for i = 1, players do
        squad[i] = u32(slots + check.stride * (i - 1))
        if squad[i] >= game.count then return 'waiting for the squad' end
    end

    local granted = {}
    local dss_at = u64(check.dss)
    if dss_at ~= 0 and can(dss_at, check.dss_count + 4, READABLE) then
        local n = u32(dss_at + check.dss_count)
        for i = 1, math.min(n, check.dss_count / 8) do granted[i] = u32(dss_at + 8 * (i - 1)) end
    end

    local own = {}
    for i = 1, players do
        if squad[i] ~= slot_memo.wrote[i] then slot_memo.own[i] = squad[i] end
        own[i] = slot_memo.own[i]
    end
    local want, keep = {}, {}
    for i, name in ipairs(picks) do want[i] = game.ids[name] end
    for _, name in ipairs(HOST_DECIDED) do keep[game.ids[name]] = true end
    local target, active, kept = plan(want, own, keep)
    local text = 'active: ' .. (#active == 0 and 'none' or names_of(active)) .. ' (' .. players .. ' players)'
        .. (#kept > 0 and (', kept for the host: ' .. names_of(kept)) or '')
        .. (#granted > 0 and (', granted by the game: ' .. names_of(granted)) or '')
    if not differs(squad, target) then return text end

    if not can(slots, check.stride * (players - 1) + 4, WRITABLE) then return 'squad slots are read-only' end
    for i = 1, players do
        write_u32(slots + check.stride * (i - 1), target[i])
        slot_memo.wrote[i] = target[i]
    end
    local after = {}
    for i = 1, players do after[i] = u32(slots + check.stride * (i - 1)) end
    need(not differs(after, target), 'write check failed')
    writes = writes + 1
    if writes <= 20 or writes % 100 == 0 then
        local mode_at = u64(check.mode)
        local mode = mode_at ~= 0 and can(mode_at + 8, 0x3C, READABLE)
            and (u32(mode_at + 8) .. '/' .. u32(mode_at + 0x40)) or 'none'
        log('write #' .. writes .. ': mode ' .. mode .. ', players ' .. players .. ', squad before: '
            .. names_of(squad))
    end
    return text
end

------------------------------------------------------------------------------------
-- Update hook.

local stopped, next_check = false, 0

local function now()
    if test and test.clock then return test.clock() end
    return tonumber(bind_windows().k.pb_GetTickCount64())
end

local function tick()
    if not menu.reported then
        menu.reported = true
        log('Mod Options Menu: ' .. state.menu_start)
    end
    if not menu.api and not menu.given_up then start_menu() end
    if menu.api and #menu.edits > 0 then apply_edits() end
    if stopped then return end
    local ok, err = pcall(function()
        local time = now()
        if time < next_check then return end
        next_check = time + CHECK_EVERY
        if not menu.api then
            if menu.checks % ORDER_EVERY == 0 then reread_order() end
            menu.checks = menu.checks + 1
        end
        game = game or find_game()
        local message = step()
        if message ~= state.status then log(message) end
    end)
    if not ok then
        stopped = true
        log('stopped: ' .. tostring(err))
    end
end

-- For tests: t = {base = stand-in game.dll, folder = files folder, clock = function}.
function state.test_use(t)
    test = t
end

local previous = rawget(_G, 'update')
update = function(...)
    local ok, err = pcall(tick)
    if not ok and not stopped then
        stopped = true
        log('stopped: ' .. tostring(err))
    end
    if type(previous) == 'function' then return previous(...) end
end
