"""Run src/personal_booster.lua against a stand-in game.dll in memory (Windows, needs lupa).

The stand-in is a small PE image: headers with two sections, the booster check
(the game's bytes, with its globals pointing into the image), the booster name
strings and their pointer table, and the mode, DSS list and squad records. The
mod finds all of it the way it does in the game, through the same Windows calls,
then reads and writes the squad slots.
"""

import os
import struct
import sys
import tempfile

from lupa.luajit21 import LuaRuntime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = open(os.path.join(ROOT, "src", "personal_booster.lua"), "rb").read().decode("utf-8")

# The game's booster check (Steam build 25480438); rel32 fields are filled in below.
CHECK = bytes.fromhex(
    "488b0d00000000488b0500000000837908007606837940047446448b481033c9448bc14585c974103910743741ffc0"
    "4883c008453bc172f0488b0500000000448b80e80800004585c0741548058c0a00003910740effc14883c040413bc8"
    "72f132c0c3b001c3")
NAMES = ["None", "Vitality", "Stamina", "MuscleEnhancement", "UAVRecon", "IncreasedReinforcementBudget",
         "FlexibleReinforcementBudget", "HellpodSpaceOptimization", "LocalizationConfusion", "FastExtraction",
         "SlowStunResistance", "CombatDrugs", "FieryDrop", "DoubleSampleChance", "DeathMarch",
         "BigEnemiesDropSamples", "ShockPods", "SmokePods", "FireExtinguish", "DefensiveAmmoPod", "Booster20",
         "Count"]
ID = {name: i for i, name in enumerate(NAMES)}
H, V, S, M, X = ID["HellpodSpaceOptimization"], ID["Vitality"], ID["Stamina"], ID["MuscleEnhancement"], ID["ShockPods"]

SIZE = 0x10000
CHECK_AT, DECOY_AT = 0x1200, 0x1800
MODE_GLOBAL, DSS_GLOBAL, SQUAD_GLOBAL = 0x3000, 0x3008, 0x3010
STRINGS, TABLE, STRAY = 0x4000, 0x5000, 0x5800
MODE, DSS, SQUAD, SQUAD2 = 0x6000, 0x6100, 0x7000, 0x9000

HARNESS = r"""
local ffi = require('ffi')
ffi.cdef[[void *VirtualAlloc(void *, size_t, uint32_t, uint32_t);]]
local memory = ffi.C.VirtualAlloc(nil, ...)
assert(memory ~= nil)
local p = ffi.cast('uint8_t *', memory)
local mem = {base = tonumber(ffi.cast('uintptr_t', memory))}
function mem.put(offset, bytes) ffi.copy(p + offset, bytes, #bytes) end
function mem.u32(offset, value)
    local cell = ffi.cast('uint32_t *', p + offset)
    if value ~= nil then cell[0] = value end
    return cell[0]
end
function mem.u64(offset, value) ffi.cast('uint64_t *', p + offset)[0] = value end
return mem
"""


def image(base, check=CHECK, table=True):
    out = bytearray(SIZE)
    out[0:2] = b"MZ"
    struct.pack_into("<I", out, 0x3C, 0x100)
    out[0x100:0x104] = b"PE\0\0"
    struct.pack_into("<HH", out, 0x104, 0x8664, 2)
    struct.pack_into("<H", out, 0x114, 0xF0)
    struct.pack_into("<H", out, 0x118, 0x20B)
    for i, (rva, size) in enumerate([(0x1000, 0x2000), (0x3000, SIZE - 0x3000)]):
        struct.pack_into("<II", out, 0x208 + 40 * i + 8, size, rva)

    code = bytearray(check)
    for at, ends, target in ((0x03, 0x07, MODE_GLOBAL), (0x0A, 0x0E, DSS_GLOBAL), (0x3B, 0x3F, SQUAD_GLOBAL)):
        struct.pack_into("<i", code, at, target - (CHECK_AT + ends))
    out[CHECK_AT:CHECK_AT + len(code)] = code
    out[DECOY_AT:DECOY_AT + 40] = CHECK[0x1E:0x46]  # the search anchor alone, not a match

    struct.pack_into("<QQQ", out, MODE_GLOBAL, base + MODE, base + DSS, base + SQUAD)
    at, pointers = STRINGS, []
    for name in NAMES:
        pointers.append(base + at)
        out[at:at + len(name) + 1] = name.encode() + b"\0"
        at += len(name) + 1
    if table:
        for i, pointer in enumerate(pointers):
            struct.pack_into("<Q", out, TABLE + 8 * i, pointer)
    struct.pack_into("<Q", out, STRAY, pointers[ID["HellpodSpaceOptimization"]])  # a pointer outside any table
    return bytes(out)


class Game:
    def __init__(self, folder, check=CHECK, table=True):
        self.lua = LuaRuntime()
        self.mem = self.lua.execute(HARNESS, SIZE, 0x3000, 0x04)
        self.mem.put(0, image(self.mem.base, check, table))
        self.folder = folder
        chunk = self.lua.eval("loadstring")(SOURCE, "=personal_booster")
        assert not isinstance(chunk, tuple), chunk[1]
        chunk()
        self.state = self.lua.globals().PersonalBooster
        clock = self.lua.eval("(function() local t = 0; return function() t = t + 10000; return t end end)()")
        self.state.test_use(self.lua.table_from({"base": self.mem.base, "folder": folder, "clock": clock}))
        self.seen = 0

    def u32(self, offset, value=None):
        return self.mem.u32(offset, value)

    def slot(self, index, value=None, record=SQUAD):
        return self.u32(record + 0xA8C + 0x40 * (index - 1), value)

    def squad(self, *ids, record=SQUAD):
        self.u32(record + 0x8E8, len(ids))
        for i, value in enumerate(ids, 1):
            self.slot(i, value, record)

    def slots(self, record=SQUAD):
        return [self.slot(i, record=record) for i in range(1, self.u32(record + 0x8E8) + 1)]

    def update(self, times=1):
        for _ in range(times):
            self.lua.globals().update()

    def log(self):
        lines = open(os.path.join(self.folder, "PersonalBooster.log"), encoding="utf-8").read().splitlines()
        new, self.seen = lines[self.seen:], len(lines)
        return [line[9:] for line in new]


def main():
    if sys.platform != "win32":
        print("SKIP: needs Windows")
        return 0

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
        game = Game(folder)
        game.u32(DSS, X)            # the game grants one booster through the DSS list
        game.u32(DSS + 0x10, 1)
        game.squad(ID["CombatDrugs"])
        game.update(2)              # the squad is looked at twice before anything is written
        lines = game.log()
        assert any(line == "ready: booster check found, 20 boosters in the game, 64 squad slot bytes apart"
                   for line in lines), lines
        assert any("(edit " in line and "PersonalBooster.order" in line for line in lines), lines

        # Solo: pick 1 in the one slot; the DSS list and the count stay as the game has them.
        assert game.slots() == [H] and game.u32(DSS) == X and game.u32(DSS + 0x10) == 1
        assert game.state.status == "active: HellpodSpaceOptimization (1 players), granted by the game: ShockPods"
        assert any(line.startswith("write #1: mode 0/0, players 1, squad before: CombatDrugs") for line in lines)

        # Teammates join: one pick per player.
        game.squad(H, S)
        game.update()
        assert game.slots() == [H, V]
        game.squad(H, V, X, ID["UAVRecon"])
        game.update()
        assert game.slots() == [H, V, S, M]
        game.log()
        game.update()
        assert not any(line.startswith("write") for line in game.log()), "nothing changed, nothing written"

        # The game puts a teammate's booster back: written again. A player leaves: one fewer.
        game.slot(2, X)
        game.update()
        assert game.slot(2) == V
        game.u32(SQUAD + 0x8E8, 3)
        game.update()
        assert game.state.status.startswith("active: HellpodSpaceOptimization, Vitality, Stamina (3 players)")

        # A slot holding something that is not a booster id: nothing is written.
        game.slot(3, 999)
        game.update()
        assert game.slot(3) == 999 and game.state.status == "waiting for the squad"
        game.slot(3, S)

        # A new squad record (next mission): written after it is seen twice; the old one is left.
        game.squad(X, record=SQUAD2)
        game.mem.u64(SQUAD_GLOBAL, game.mem.base + SQUAD2)
        game.update()
        assert game.slots(SQUAD2) == [X] and game.state.status == "squad found, checking again before writing"
        game.update()
        assert game.slots(SQUAD2) == [H] and game.slots() == [H, V, S]

        # The order file is the picker without Options > MODS: edits are read within a few checks.
        with open(os.path.join(folder, "PersonalBooster.order"), "w") as f:
            f.write("Stamina\nShockPods\nnot_a_booster\nStamina\n")
        game.update(5)
        picks = game.state.picks
        assert [picks[i] for i in range(1, len(picks) + 1)] == ["Stamina", "ShockPods"]
        assert game.slots(SQUAD2) == [S]
        assert any("picked 2/4: Stamina, ShockPods (from the order file)" in line for line in game.log())

        # Booster Buster also running: stop.
        game.lua.globals().MissionBoosters = game.lua.table()
        game.update()
        assert game.state.status == "stopped: Booster Buster is also installed, disable one of them"

    for name, game_args, expected in [
        ("a different check", {"check": CHECK[:0x5A] + b"\x41" + CHECK[0x5B:]},
         "stopped: booster check offsets look wrong, nothing written"),
        ("no check", {"check": b"\x90" * len(CHECK)}, "stopped: booster check found 0 times, nothing written"),
        ("no name table", {"table": False}, "stopped: booster name table not found, nothing written"),
    ]:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
            game = Game(folder, **game_args)
            game.squad(X)
            game.update(3)
            assert game.state.status == expected, (name, game.state.status)
            assert game.slots() == [X], name + ": nothing written"

    print("OK: finds the check and the name table in a stand-in game.dll and writes one pick per player")
    return 0


if __name__ == "__main__":
    sys.exit(main())
