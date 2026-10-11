"""Build dist/Personal-Booster-v<version>.zip for Arsenal / HD2MM.

The archive holds three Lua resources:
  mods/modocracy/personal_booster       the mod (src/personal_booster.lua)
  mods/modocracy/mod_options_menu       Mod Options Menu (third_party/), started by the mod
                                        when no other copy runs, for the Options > MODS picker
  core/wwise/lua/wwise_flow_callbacks   a bridge that runs the game's original Wwise
                                        callbacks, then starts the mod, so no mod loader
                                        is needed
The bridge embeds the game's original callbacks, which are not part of this
repository: run tools/extract_callbacks.py first (it reads them from your own install).
"""

import json
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import patch  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION = "1.2.1"
GUID = "a4402f3c-f59a-4ea6-bade-151439092102"
ARCHIVE = "9ba626afa44a3aa3.patch_0"
MOD_RESOURCE = "mods/modocracy/personal_booster"
MENU_RESOURCE = "mods/modocracy/mod_options_menu"
BRIDGE_RESOURCE = "core/wwise/lua/wwise_flow_callbacks"
CALLBACKS = os.path.join(ROOT, "build", "wwise_flow_callbacks.lua.main")
HEADER = re.compile(rb"^-- HD2-Addon: (mods/[A-Za-z0-9_]+/[A-Za-z0-9_/]+)\n")

DESCRIPTION = (
    "One booster per player, as in the game, but you pick them all: with N players, your picks 1-N "
    "apply to you and teammates' boosters are ignored on your PC. Pick in Options > MODS (Mod Options "
    "Menu is included). Needs no mod loader; "
    "with Bingus Shared Loader, keep the loader last. Do not use with Booster Buster."
)

BRIDGE = """-- Personal Booster: Wwise flow callbacks bridge, for play without a mod loader.
-- Runs the game's original callbacks (embedded below, from Steam build 25480438),
-- then starts {mod}. A mod loader that replaces this resource and wins the load
-- order starts the mod by itself instead.
local ORIGINAL = "{original}"

local function start_personal_booster()
    if rawget(_G, 'PersonalBooster') then return end
    local ok, err = pcall(require, '{mod}')
    if not ok then pcall(print, '[PersonalBooster] not started: ' .. tostring(err)) end
end

local function after_callbacks(...)
    start_personal_booster()
    return ...
end

return after_callbacks(assert(loadstring(ORIGINAL, '=wwise_flow_callbacks'))(...))
"""


def lua_string(data: bytes) -> str:
    return "".join(f"\\{byte:03d}" for byte in data)


def bridge_source(callbacks_resource: bytes) -> bytes:
    length = int.from_bytes(callbacks_resource[:4], "little")
    bytecode = callbacks_resource[8:8 + length]
    assert bytecode[:3] == b"\x1bLJ", "the original callbacks are not LuaJIT bytecode"
    return BRIDGE.format(mod=MOD_RESOURCE, original=lua_string(bytecode)).encode()


def main():
    source = open(os.path.join(ROOT, "src", "personal_booster.lua"), "rb").read().replace(b"\r\n", b"\n")
    assert HEADER.match(source).group(1).decode() == MOD_RESOURCE
    if not os.path.exists(CALLBACKS):
        print("Missing " + CALLBACKS + ": run python tools/extract_callbacks.py first.")
        return 1
    bridge = bridge_source(open(CALLBACKS, "rb").read())
    menu = open(os.path.join(ROOT, "third_party", "mod_options_menu.lua"), "rb").read().replace(b"\r\n", b"\n")
    assert not menu.startswith(b"-- HD2-Addon:"), "the bundled menu must not declare itself to loaders"

    manifest = {
        "Version": 1,
        "Guid": GUID,
        "Name": "Personal Booster " + VERSION,
        "Description": DESCRIPTION,
        "Options": [{
            "Name": "Personal Booster " + VERSION,
            "Description": DESCRIPTION,
            "Include": ["data"],
            "Image": "icon.png",
        }],
        "IconPath": "icon.png",
    }
    os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
    out = os.path.join(ROOT, "dist", f"Personal-Booster-v{VERSION}.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest, indent=2) + "\n")
        z.write(os.path.join(ROOT, "assets", "icon.png"), "icon.png")
        z.writestr("data/" + ARCHIVE, patch.build_many(
            [(MOD_RESOURCE, source), (MENU_RESOURCE, menu), (BRIDGE_RESOURCE, bridge)]))
        z.writestr("data/" + ARCHIVE + ".gpu_resources", b"")
        z.writestr("data/" + ARCHIVE + ".stream", b"")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
