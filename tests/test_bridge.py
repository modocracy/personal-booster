"""Test the Wwise callbacks bridge that tools/build.py writes (needs lupa).

A stand-in for the game's original callbacks is compiled with LuaJIT and put in the
bridge the way the build puts the real one. Running the bridge must run the
original with the startup arguments, keep all of its results, then start the mod
once through require.
"""

import os
import struct
import sys

from lupa.luajit21 import LuaRuntime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import build  # noqa: E402

ORIGINAL = """
local a, b = ...
original_ran = (original_ran or 0) + 1
original_args = {a, b}
return 'first', nil, a, nil
"""

HARNESS = r"""
local bridge, original = ...
local stock = string.dump(assert(loadstring(original)))
required, printed = {}, {}
require = function(name)
    required[#required + 1] = name
    if fail_require then error('no such resource') end
    PersonalBooster = {}
end
print = function(text) printed[#printed + 1] = text end
local chunk = assert(loadstring(bridge(stock)))
return function(...) return select('#', chunk(...)), chunk(...) end
"""


def main():
    lua = LuaRuntime(unpack_returned_tuples=True, encoding=None)  # strings as bytes
    to_bridge = lambda stock: build.bridge_source(struct.pack("<II", len(stock), 2) + stock)  # noqa: E731
    run = lua.execute(HARNESS.encode(), to_bridge, ORIGINAL.encode())
    g = lua.globals()

    count, *results = run(b"boot", 7)
    assert count == 4 and results[:4] == [b"first", None, b"boot", None], (count, results)
    assert g[b"original_args"][1] == b"boot" and g[b"original_args"][2] == 7
    assert list(g[b"required"].values()) == [b"mods/modocracy/personal_booster"], "the mod is required once"

    # The bridge runs again (another load of the resource): the mod is not required twice.
    run(b"again", 1)
    assert list(g[b"required"].values()) == [b"mods/modocracy/personal_booster"]

    # A failing require is reported, and the original's results still come back.
    g[b"PersonalBooster"] = None
    g[b"fail_require"] = True
    count, *results = run(b"x", 2)
    assert count == 4 and results[2] == b"x"
    assert any(b"[PersonalBooster] not started:" in text for text in g[b"printed"].values())

    # The embedded string is the original byte for byte.
    payload = b"\x1bLJ" + bytes(range(256)) * 3
    source = build.bridge_source(struct.pack("<II", len(payload), 2) + payload)
    literal = source.split(b'local ORIGINAL = "')[1].split(b'"\n')[0]
    assert bytes(int(literal[i + 1:i + 4]) for i in range(0, len(literal), 4)) == payload

    print("OK: the bridge runs the original callbacks, keeps their results and starts the mod once")
    return 0


if __name__ == "__main__":
    sys.exit(main())
