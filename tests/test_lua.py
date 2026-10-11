"""Compile src/personal_booster.lua with LuaJIT 2.1 and test its pure steps.

Needs the lupa package (pip install lupa). Loading the chunk only runs its top
level, which publishes the pure steps on the PersonalBooster global.
"""

import os
import sys
import tempfile

from lupa.luajit21 import LuaRuntime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = open(os.path.join(ROOT, "src", "personal_booster.lua"), "rb").read().decode("utf-8")
CHECK = bytes.fromhex(
    "488b0d00000000488b0500000000837908007606837940047446448b481033c9448bc14585c974103910743741ffc0"
    "4883c008453bc172f0488b0500000000448b80e80800004585c0741548058c0a00003910740effc14883c040413bc8"
    "72f132c0c3b001c3")
H, V, S, M = 7, 1, 2, 3
WANT = [H, V, S, M]


def load():
    lua = LuaRuntime(unpack_returned_tuples=True)
    chunk = lua.eval("loadstring")(SOURCE, "=personal_booster")
    assert not isinstance(chunk, tuple), chunk[1]
    chunk()
    state = lua.globals().PersonalBooster
    assert state.status == "starting" and callable(lua.globals().update)
    return lua, state


def as_list(t):
    return [t[i] for i in range(1, len(t) + 1)]


def main():
    lua, state = load()
    table = lua.table_from

    def plan(squad, want=WANT):
        target, active = state.plan(table(want), table(squad))
        return as_list(target), as_list(active), state.differs(table(squad), target)

    # One pick per player, from the first; empty slots past the picks.
    assert plan([9]) == ([H], [H], True)
    assert plan([9, 4]) == ([H, V], [H, V], True)
    assert plan([9, 4, 5, 6]) == (WANT, WANT, True)
    assert plan([9, 4, 5, 6], [H, V]) == ([H, V, 0, 0], [H, V], True)
    assert plan([9], []) == ([0], [], True)
    assert plan([H, V])[2] is False, "nothing to write once the slots match"

    # Patterns: ?? bytes are free, the longest fixed run is the search anchor.
    pattern = state.parse_pattern("48 ?? 0D 33 C9 44 ?? 01")
    assert as_list(pattern.bytes) == [0x48, False, 0x0D, 0x33, 0xC9, 0x44, False, 0x01]
    anchor_is = lua.eval("function(p) return p.anchor == string.char(0x0D, 0x33, 0xC9, 0x44) end")
    assert anchor_is(pattern) and pattern.at == 2

    # Decoding the check: globals from rip-relative operands, offsets from the code.
    code = bytearray(CHECK)
    code[0x03:0x07] = (0x100).to_bytes(4, "little")
    code[0x0A:0x0E] = (-0x20 & 0xFFFFFFFF).to_bytes(4, "little")
    code[0x3B:0x3F] = (0x10).to_bytes(4, "little")
    check = state.decode_check(bytes(code), 0x10000)
    assert (check.mode, check.dss, check.squad) == (0x10000 + 7 + 0x100, 0x10000 + 0x0E - 0x20, 0x10000 + 0x3F + 0x10)
    assert (check.dss_count, check.players, check.slots, check.stride) == (0x10, 0x8E8, 0xA8C, 0x40)

    # Without the game: the first update stops cleanly and says why.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
        lua, state = load()
        state.test_use(lua.table_from({"folder": folder}))
        lua.globals().update()
        lua.globals().update()
        lines = open(os.path.join(folder, "PersonalBooster.log"), encoding="utf-8").read().splitlines()
        assert lines[-1][9:] == "stopped: game.dll is not loaded yet", lines

    print("OK: LuaJIT 2.1 compiles the mod; planning, patterns and check decoding behave as expected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
