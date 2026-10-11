# Personal Booster

A Helldivers 2 mod that keeps the game's rule of **one booster per player**, but lets you choose all of them.

With N players in the squad, your picks 1 to N are active for you, and the boosters your teammates brought are not. Teammates keep their own boosters on their own PCs. Boosters the game grants through the DSS are left as they are.

| Squad | Your boosters |
|---|---|
| Solo | pick 1 |
| 2 players | picks 1-2 |
| 3 players | picks 1-3 |
| 4 players | picks 1-4 |

Unofficial. Not affiliated with Arrowhead Game Studios. Use at your own risk.

## Install

1. Download `Personal-Booster-v<version>.zip` from [Releases](../../releases).
2. Import it in Arsenal or HD2MM, enable it, then Purge and Deploy.
3. Do not enable Booster Buster at the same time.

No mod loader is needed. If you also use **Bingus Shared Loader**, keep the loader **last** in the load order as its instructions say: it then starts Personal Booster itself, and everything else works as before.

Supported game build: Steam build 25480438 (EXE 1.8.46015.0).

## Picking boosters

- **With Mod Options Menu** (part of Vanilla Plus Megapack, which needs Bingus Shared Loader): Options > MODS > PERSONAL BOOSTER. Give each booster a place: OFF or 1-4. Setting a place puts the booster there and moves the others down. After Apply, the places and the count (`0/4`-`4/4`) update at once.
- **Without it**: edit `%LOCALAPPDATA%\PersonalBooster\PersonalBooster.order`, one booster per line, first line first. The mod rereads it every few seconds.

Booster names for the order file: `HellpodSpaceOptimization`, `Vitality`, `Stamina`, `MuscleEnhancement`, `UAVRecon`, `IncreasedReinforcementBudget`, `FlexibleReinforcementBudget`, `LocalizationConfusion`, `FastExtraction`, `SlowStunResistance`, `CombatDrugs`, `FieryDrop`, `DoubleSampleChance`, `DeathMarch`, `BigEnemiesDropSamples`, `ShockPods`, `SmokePods`, `FireExtinguish`.

The first time, Hellpod Space Optimization, Vitality, Stamina and Muscle Enhancement are picked in that order.

## How it works

The game decides whether a booster is active with one small function. It looks through the boosters the game grants (the DSS list), then through each squad member's equipped booster.

Personal Booster finds that function in game memory by its code pattern and reads from its instructions where the squad record is, where the booster slots are and how far apart they are. It finds the game's booster name table by following it from `None` to `Count`. Every 2 seconds it writes your picks into the squad's booster slots, one per player, **in this PC's memory only**. Game code is not changed and the DSS list is not written. If anything does not match what the mod expects, it stops before writing and says why in the log.

The archive holds two resources:

- `mods/modocracy/personal_booster`: the mod. Bingus Shared Loader finds it by its first line.
- `core/wwise/lua/wwise_flow_callbacks`: a bridge used when no loader is installed. It runs the game's original Wwise callbacks, then starts the mod. The release ZIP embeds those original callbacks from the supported game build. They are not part of this repository.

Seen in game (2026-10-11): boosters in teammates' slots take effect for you; Firebomb Hellpods sets fire only at your own hellpod, damages enemies, and also burns teammates when another player hosts. Effects decided by the host (reinforcement budget, Localization Confusion, extraction, samples) follow the host's game.

## Log

`%LOCALAPPDATA%\PersonalBooster\PersonalBooster.log`, started afresh each session.

- `ready: ...`: the booster check and name table were found
- `picked n/4: ...`: picks changed
- `active: ... (N players)`: your boosters now active, and any granted by the game
- `write #N: ...`: slots written, with what they held before
- `stopped: ...`: a safety check stopped the mod, with the reason

## Build from source

Needs Python 3.10+, and `lupa` and `Pillow` for the tests and the icon.

```
python tools/extract_callbacks.py   # finds the original Wwise callbacks in your install
python tools/build.py               # writes dist/Personal-Booster-v<version>.zip
```

`extract_callbacks.py` looks through the patch archives in your game's `data` folder for an embedded copy of the original callbacks (for example the one inside Bingus Shared Loader) and checks it against the supported build's SHA-256. It changes nothing in the game folder.

Tests:

```
python tests/test_lua.py      # compiles with LuaJIT 2.1; planning, patterns, check decoding
python tests/test_memory.py   # a stand-in game.dll in memory: finding, reading and writing (Windows)
python tests/test_picker.py   # the Options > MODS picker with a stand-in Mod Options Menu
python tests/test_bridge.py   # the Wwise callbacks bridge
python tests/test_patch.py    # the archive writer (needs published mods unpacked in extracted/)
```

`tools/make_icon.py` draws `assets/icon.png`.

## License

Zero-Clause BSD (0BSD), see [LICENSE](LICENSE). The game's original Wwise callbacks embedded in release ZIPs belong to their owners and are not covered by this license.

---

## 한국어

게임 규칙대로 **참가 인원 1명당 부스터 1개**를 쓰되, 그 부스터를 전부 내가 고르는 헬다이버즈2 모드입니다.

- 인원이 N명이면 내 순서 1~N번이 나에게 적용되고, 팀원이 고른 부스터는 내 게임에서 무시됩니다. 팀원은 각자 자기 부스터를 그대로 씁니다.
- 함대 강화(DSS)로 게임이 주는 부스터는 그대로 받습니다.
- **모드 로더가 필요 없습니다.** Bingus Shared Loader를 함께 쓴다면 로더를 목록 **맨 아래**에 두세요.
- 부스터 고르기: Mod Options Menu가 있으면 옵션 → MODS → PERSONAL BOOSTER에서 부스터마다 순서(끄기, 1~4)를 정합니다. 없으면 `%LOCALAPPDATA%\PersonalBooster\PersonalBooster.order` 파일에 한 줄에 하나씩 적습니다.
- 내 PC 메모리의 분대원 부스터 칸만 바꾸고, 게임 코드는 바꾸지 않습니다. 예상과 다르면 아무것도 쓰지 않고 멈춥니다.
- 비공식 모드입니다. 사용에 따른 책임은 사용자에게 있습니다.
