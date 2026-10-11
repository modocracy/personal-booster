"""Find the game's original Wwise flow callbacks in an installed patch archive.

The game keeps core/wwise/lua/wwise_flow_callbacks in its packed bundles. Loaders
that replace that resource (Bingus Shared Loader, this mod) embed the original
LuaJIT bytecode so the game's callbacks keep working. This script looks through
every patch archive in the game's data folder for an embedded copy whose bytes
match the supported game build, and writes it as a Lua resource (u32 length,
u32 2, bytecode) for tools/build.py. Nothing in the game folder is changed.

usage: extract_callbacks.py [<game data folder>] [<output file>]
"""

import hashlib
import os
import struct
import sys

DATA = r"C:\Program Files (x86)\Steam\steamapps\common\Helldivers 2\data"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "build", "wwise_flow_callbacks.lua.main")

# Steam build 25480438 / EXE 1.8.46015.0: SHA-256 of the resource (header and bytecode),
# as published by Bingus Shared Loader (scripts/build.py, CALLBACK_SHA).
CALLBACK_SHA = "05BBF52978028758B39F5B91A30A695D20069CEABD774D88755F0582A296BEC9"
CALLBACK_SIZE = 10263
LUAJIT = b"\x1bLJ\x02"


def resource(bytecode):
    return struct.pack("<II", len(bytecode), 2) + bytecode


def find(data_folder):
    for name in sorted(os.listdir(data_folder)):
        if ".patch_" not in name or name.endswith((".stream", ".gpu_resources")):
            continue
        data = open(os.path.join(data_folder, name), "rb").read()
        at = data.find(LUAJIT)
        while at != -1:
            candidate = resource(data[at:at + CALLBACK_SIZE])
            if hashlib.sha256(candidate).hexdigest().upper() == CALLBACK_SHA:
                return name, candidate
            at = data.find(LUAJIT, at + 1)
    return None, None


def main():
    data_folder = sys.argv[1] if len(sys.argv) > 1 else DATA
    out = sys.argv[2] if len(sys.argv) > 2 else OUT
    name, found = find(data_folder)
    if not found:
        print("The supported original Wwise callbacks were not found in any patch archive.")
        print("Install a loader that embeds them (for example Bingus Shared Loader) and deploy once,")
        print("or check that the game build matches Steam build 25480438.")
        return 1
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "wb").write(found)
    print(f"{out} (from {name}, SHA-256 {CALLBACK_SHA[:16]}...)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
