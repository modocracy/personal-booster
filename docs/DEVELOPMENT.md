# Development

[README](../README.md) · [한국어 README](../README.ko.md)

## How it works

### The booster check

The game decides whether a booster is active with one small function (Steam build 25480438):

```
00  mov rcx, [mode]          ; in one mode (rcx+8 > 0 and rcx+0x40 == 4) nothing is active
07  mov rax, [dss list]
1A  mov r9d, [rax+count]     ; search the DSS list, 8 bytes per entry
38  mov rax, [squad]
3F  mov r8d, [rax+players]   ; then one slot per player
4B  add rax, slots           ; slots stride bytes apart
60  xor al, al / ret         ; not active
63  mov al, 1 / ret          ; active
```

`src/personal_booster.lua` finds it in `game.dll` by its code pattern (`CHECK_PATTERN`; `??` marks bytes a game build may change), searching every section listed in the PE headers in memory. It requires exactly one match. From the matched bytes it reads the three rip-relative globals and the squad offsets: the player count offset, the slots offset and the slot stride. The offsets are checked for plausibility before use.

### The booster name table

Booster ids are indexes into a table of string pointers that starts at `None` and ends at `Count`. The mod finds the string `HellpodSpaceOptimization`, then every 8-byte pointer to it, and from each walks back to `None` and forward to `Count`. Every table found must agree and must hold all 18 boosters the mod offers.

### The memory step

Every 2 seconds (`CHECK_EVERY`) the mod reads the squad record. A new record is read twice before anything is written. With N players (1-4), slot i should hold pick i, and slots past the picks are emptied. When a slot differs, the mod writes the slots, reads them back, and logs the write. The DSS list is only read, for the log. Every read and write is checked against `VirtualQuery` first, and any mismatch stops the mod before it writes.

The pure steps (`plan`, `differs`, `placed`, `parse_pattern`, `decode_check`) are published on the `PersonalBooster` global for the tests.

### The picker

Mod Options Menu redraws row values as soon as code sets them, but row names only when the escape menu opens. So the count and the places are row values: `personal_booster.count` (`0/4`-`4/4`, set back after any edit) and `personal_booster.place.<booster>` (OFF, 1-4). The menu's callbacks only queue the edits; the mod applies them in its next update, after the menu has applied every edit, then sets every row.

The pick order lives in `%LOCALAPPDATA%\PersonalBooster\PersonalBooster.order`. At start the mod reads that file; without it, the rows' saved places; without those, the defaults. Without the menu, the file is reread every 5 checks (`ORDER_EVERY`).

The menu is Mod Options Menu, included in `third_party/mod_options_menu.lua` as shipped in Vanilla Plus Megapack v40, with its first line (its `-- HD2-Addon:` declaration) replaced by a notice so that a loader does not start it on its own. Personal Booster requires it when no `ModOptionsMenu` global exists yet. With Bingus Shared Loader, Vanilla Plus Megapack starts before discovered mods, so its copy wins when installed.

Without Bingus Shared Loader, Mod Options Menu saves its own values file into the loader's log folder only if that folder exists. The picks do not depend on it: the order file is the record.

### Starting without a loader

The game does not run mod Lua by itself. The archive therefore also replaces `core/wwise/lua/wwise_flow_callbacks`, which the game loads at startup, with a bridge: it runs the game's original callbacks (embedded as a string and loaded with `loadstring`), passes their results through unchanged, then requires `mods/modocracy/personal_booster` unless it is already running.

Bingus Shared Loader replaces the same resource. When it wins the load order (it asks to be last), its bridge runs instead and it starts Personal Booster by the `-- HD2-Addon:` line at the top of the mod.

### The archive

`dist/Personal-Booster-v<version>.zip` holds an Arsenal / HD2MM manifest, the icon and `data/9ba626afa44a3aa3.patch_0` with three Lua resources:

| Resource | Content |
|---|---|
| `mods/modocracy/personal_booster` | `src/personal_booster.lua` |
| `mods/modocracy/mod_options_menu` | `third_party/mod_options_menu.lua` |
| `core/wwise/lua/wwise_flow_callbacks` | the bridge, with the game's original callbacks |

Resource names are hashed with MurmurHash64A (`tools/murmur.py`). `tools/patch.py` writes the archive: a 0x48-byte header, one type entry, one 0x50-byte entry per resource, and each resource (u32 length, u32 2, body) at a 16-byte boundary.

## Build

Needs Python 3.10+.

```
python tools/extract_callbacks.py   # finds the game's original Wwise callbacks in your install
python tools/build.py               # writes dist/Personal-Booster-v<version>.zip
```

The game keeps its original callbacks in packed bundles. `extract_callbacks.py` looks through the patch archives in the game's `data` folder for an embedded copy (for example the one inside Bingus Shared Loader) whose SHA-256 matches the supported build, and writes it to `build/`. It changes nothing in the game folder. The callbacks are not committed to this repository.

`python tools/make_icon.py` redraws `assets/icon.png` (needs Pillow).

## Tests

Need [lupa](https://pypi.org/project/lupa/) (LuaJIT 2.1, the game's Lua).

```
python tests/test_lua.py      # compiles the mod; planning, patterns, check decoding, starting the menu
python tests/test_memory.py   # a stand-in game.dll in memory: finding, reading and writing (Windows)
python tests/test_picker.py   # the Options > MODS picker with a stand-in Mod Options Menu
python tests/test_bridge.py   # the Wwise callbacks bridge
python tests/test_patch.py    # the archive writer against published mods unpacked in extracted/
```

`test_memory.py` builds a small PE image with the game's booster check, the name strings and their pointer table, and the mode, DSS and squad records, then runs the mod against it through the same Windows calls it uses in the game. `test_patch.py` skips when `extracted/` is missing.

## Supporting a new game build

1. Check the log: `stopped: booster check found 0 times` means the check's code changed; a name table message means the table moved or changed.
2. Update `CHECK_PATTERN` and, if needed, `CHECK_FIELDS` and the stand-in in `tests/test_memory.py`.
3. Update `CALLBACK_SHA` and `CALLBACK_SIZE` in `tools/extract_callbacks.py` for the new original callbacks, and the build number in the bridge text in `tools/build.py`.
4. If Mod Options Menu needs an update for the build, replace `third_party/mod_options_menu.lua` the same way.
