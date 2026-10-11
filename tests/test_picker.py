"""Test the in-game picker of src/personal_booster.lua against a stand-in Mod Options Menu.

Needs the lupa package (pip install lupa). The stand-in keeps the parts of the
Mod Options Menu API v3 the mod uses: register_option (choice rows), get, set
(no callbacks) and on_change (called when the player applies an edit). The mod
handles applied edits in its next update, as it does in the game.
"""

import os
import sys
import tempfile

from lupa.luajit21 import LuaRuntime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = open(os.path.join(ROOT, "src", "personal_booster.lua"), "rb").read().decode("utf-8")
COUNT = "personal_booster.count"
RANK = "personal_booster.place."
DEFAULTS = ["HellpodSpaceOptimization", "Vitality", "Stamina", "MuscleEnhancement"]
H, V, S, M = DEFAULTS
U, F, X = "UAVRecon", "FieryDrop", "ShockPods"

STAND_IN = """
local saved = ...
local api = {options = {}, values = {}, callbacks = {}, order = {}}
local function text(value, limit)
    if type(value) == 'function' then value = value() end
    assert(type(value) == 'string' and value ~= '', 'bad text')
    local length = 0
    for _ in value:gmatch('[^\\128-\\191]') do length = length + 1 end
    assert(length <= limit, 'text too long: ' .. value)
    return value
end
function api.register_option(id, spec)
    if api.options[id] then return false, 'option already registered differently' end
    assert(spec.type == 'choice' and spec.mod_id == 'modocracy.personal_booster' and #spec.choices >= 2 and #spec.choices <= 16)
    text(spec.label, 64); text(spec.mod, 40); text(spec.description, 400)
    for _, choice in ipairs(spec.choices) do text(choice, 48) end
    api.options[id] = spec
    api.order[#api.order + 1] = id
    local value = saved[id]
    if type(value) ~= 'number' or value < 1 or value > #spec.choices then value = spec.default end
    api.values[id] = value
    return true
end
function api.get(id) return api.values[id] end
function api.set(id, value)
    local spec = api.options[id]
    if not spec or type(value) ~= 'number' or value < 1 or value > #spec.choices then return false, 'invalid' end
    api.values[id] = value
    return true
end
function api.on_change(id, callback)
    local list = api.callbacks[id] or {}
    list[#list + 1] = callback
    api.callbacks[id] = list
    return true
end
-- The player edits rows and applies them: callbacks run in the order given.
function api.player(edits)
    for _, edit in ipairs(edits) do
        api.values[edit[1]] = edit[2]
        for _, callback in ipairs(api.callbacks[edit[1]] or {}) do callback(edit[2], edit[1]) end
    end
end
function api.label(id) return text(api.options[id].label, 64) end
function api.description(id) return text(api.options[id].description, 400) end
function api.shown(id) return api.options[id].choices[api.values[id]] end
return api
"""


class Game:
    """One game session: a fresh Lua state running the mod beside the stand-in menu."""

    def __init__(self, folder, saved=None, with_menu=True):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.folder = folder
        api = self.lua.execute(STAND_IN, self.lua.table_from(saved or {}))
        self.api = api if with_menu else None
        if with_menu:
            self.lua.globals().ModOptionsMenu = api
        chunk = self.lua.eval("loadstring")(SOURCE, "=personal_booster")
        assert not isinstance(chunk, tuple), chunk[1]
        chunk()
        self.state = self.lua.globals().PersonalBooster
        self.state.test_use(self.lua.table_from({"folder": folder}))
        self.lua.globals().update()

    def apply(self, *edits):
        """The player sets rows (booster name or COUNT, shown value) and applies; then the mod's next update."""
        values = {"OFF": 1, "1": 2, "2": 3, "3": 4, "4": 5}
        rows = []
        for row, shown in edits:
            value = int(shown[0]) + 1 if row == COUNT else values[shown]
            rows.append(self.lua.table_from([row if row == COUNT else RANK + row, value]))
        self.api.player(self.lua.table_from(rows))
        self.lua.globals().update()

    def picks(self):
        p = self.state.picks
        return [p[i] for i in range(1, len(p) + 1)]

    def places(self):
        """Booster -> shown place for every booster not OFF, and the shown count."""
        shown = {}
        order = self.api["order"]
        for i in range(1, len(order) + 1):
            row = order[i]
            if row.startswith(RANK) and self.api.shown(row) != "OFF":
                shown[row[len(RANK):]] = self.api.shown(row)
        return shown, self.api.shown(COUNT)

    def log(self):
        """This session's log lines (the game is absent here, so it ends with a stop line)."""
        path = os.path.join(self.folder, "PersonalBooster.log")
        lines = open(path, encoding="utf-8").read().splitlines()
        return [line[9:] for line in lines if not line[9:].startswith("stopped: game.dll")]

    def saved_values(self):
        return {k: v for k, v in self.api["values"].items()}


def order_file(folder):
    path = os.path.join(folder, "PersonalBooster.order")
    return open(path).read().split() if os.path.exists(path) else None


def expect(game, picks):
    assert game.picks() == picks, game.picks()
    shown, count = game.places()
    assert shown == {name: str(i) for i, name in enumerate(picks, 1)}, shown
    assert count == f"{len(picks)}/4", count


def main():
    lua = LuaRuntime()
    lua.eval("loadstring")(SOURCE, "=my_boosters")()
    placed = lua.globals().PersonalBooster.placed

    def place(picks, name, at):
        out = placed(lua.table_from(picks), name, at)
        return [out[i] for i in range(1, len(out) + 1)]

    assert place([H, V, S, M], U, 2) == [H, U, V, S], "a fifth pushes the last one off"
    assert place([H, V, S, M], M, 1) == [M, H, V, S], "moving up"
    assert place([H, V, S, M], H, 4) == [V, S, M, H], "moving down"
    assert place([H, V], U, 4) == [H, V, U], "a place past the end goes to the end"
    assert place([H, V, S], V, 0) == [H, S], "OFF removes"
    assert place([], U, 0) == []

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
        # First start: nothing saved, so the defaults are picked and shown at once.
        game = Game(folder)
        expect(game, DEFAULTS)
        assert order_file(folder) == DEFAULTS
        assert "picker ready in Options > MODS, picked 4/4" in game.log()[0], game.log()
        assert game.api.label(RANK + U) == "UAV Recon Booster"
        assert game.api.label(COUNT) == "Picked boosters"
        assert "One booster per player is active" in game.api.description(RANK + U)

        # Putting a fifth at place 2: the others move down, the last falls off.
        game.apply((U, "2"))
        expect(game, [H, U, V, S])
        assert order_file(folder) == [H, U, V, S]
        assert game.log()[-1] == "picked 4/4: " + ", ".join([H, U, V, S])

        # OFF removes and the count drops at once.
        game.apply((V, "OFF"))
        expect(game, [H, U, S])

        # A place past the end goes to the end.
        game.apply((M, "4"))
        expect(game, [H, U, S, M])
        game.apply((F, "4"), (S, "OFF"))
        expect(game, [H, U, F])
        game.apply((X, "4"))
        expect(game, [H, U, F, X])

        # Several edits in one apply run in order.
        game.apply((X, "1"), (H, "OFF"))
        expect(game, [X, U, F])

        # Editing the count row changes nothing and is set back.
        lines = len(game.log())
        game.apply((COUNT, "0/4"))
        expect(game, [X, U, F])
        assert len(game.log()) == lines, "no change, no log line"

        # Korean game language: Korean names and descriptions.
        game.lua.globals().BingusTranslations = game.lua.table_from({"game_language": "ko"})
        assert game.api.label(RANK + U) == "UAV 정찰 부스터"
        assert game.api.label(COUNT) == "선택한 부스터"
        assert game.api.description(RANK + F).startswith("헬포드가 착지할 때 화염 폭발이 일어납니다.")

        # Next session: the saved order gives the same picks and rows.
        saved = game.saved_values()
        expect(Game(folder, saved), [X, U, F])

        # The order file lost: the rows' saved places give the order.
        os.remove(os.path.join(folder, "PersonalBooster.order"))
        lost = Game(folder, saved)
        expect(lost, [X, U, F])
        assert order_file(folder) == [X, U, F]

        # Values saved by the earlier My Boosters versions are ignored.
        old = dict(saved)
        old["jj.my_boosters.rank.Vitality"] = 2
        expect(Game(folder, old), [X, U, F])

        # Everything removed stays removed next session.
        lost.apply((X, "OFF"), (U, "OFF"), (F, "OFF"))
        expect(lost, [])
        assert order_file(folder) == []
        expect(Game(folder, lost.saved_values()), [])

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
        # Without Mod Options Menu the defaults are used and saved as the order file to edit.
        plain = Game(folder, with_menu=False)
        assert plain.picks() == DEFAULTS
        assert order_file(folder) == DEFAULTS

    print("OK: picker places, moves, removes, shows places and count at once, and restores the order")
    return 0


if __name__ == "__main__":
    sys.exit(main())
