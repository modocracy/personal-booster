<p align="center"><img src="assets/icon.png" width="128" alt="Personal Booster 아이콘"></p>

# Personal Booster

[English](README.md) · [개발 문서 (영어)](docs/DEVELOPMENT.md)

게임 규칙대로 **참가 인원 1명당 부스터 1개**를 쓰되, 그 부스터를 전부 내가 고르는 헬다이버즈2 모드입니다.

분대 인원이 N명이면 내 순서 1~N번이 나에게 적용되고, 팀원이 고른 부스터는 내 게임에서 무시됩니다. 팀원은 각자 자기 PC에서 자기 부스터를 그대로 씁니다. 함대 강화(DSS)로 게임이 주는 부스터는 그대로 받습니다.

| 분대 | 적용되는 내 부스터 |
|---|---|
| 솔로 | 1번 |
| 2명 | 1~2번 |
| 3명 | 1~3번 |
| 4명 | 1~4번 |

누가 들어오거나 나가면 2초 안에 자동으로 바뀝니다.

비공식 모드이며 Arrowhead Game Studios와 관계없습니다. 사용에 따른 책임은 사용자에게 있습니다.

## 설치

1. [Releases](../../releases)에서 `Personal-Booster-v<버전>.zip`을 받습니다. 아직 올라온 게 없다면 [직접 빌드](docs/DEVELOPMENT.md#build)할 수 있습니다.
2. Arsenal이나 HD2MM에서 zip을 가져와 켜고, Purge → Deploy를 누릅니다.
3. Booster Buster와 함께 켜지 마세요. 함께 켜져 있으면 Personal Booster가 스스로 멈춥니다.

**모드 로더가 필요 없고**, 옵션 → MODS 메뉴도 들어 있습니다.

**Bingus Shared Loader**를 함께 쓴다면 로더 안내대로 로더를 목록 **맨 아래**에 두세요. 그러면 로더가 Personal Booster를 실행하고, Vanilla Plus Megapack이 있으면 그쪽 메뉴를 씁니다.

지원 게임 빌드: Steam build 25480438 (EXE 1.8.46015.0)

## 부스터 고르기

### 게임 안에서

옵션 → MODS → PERSONAL BOOSTER

- 맨 위 **선택한 부스터** 줄은 고른 개수(`0/4`~`4/4`)를 보여 줍니다. 표시용이라 바꿔도 아무 일도 일어나지 않습니다.
- 부스터마다 순서를 **끄기**, **1**, **2**, **3**, **4** 중에서 고릅니다.
  - 숫자를 고르면 그 순서에 들어가고, 원래 그 자리부터 뒤에 있던 부스터는 한 칸씩 밀립니다. 4번 뒤로 밀린 부스터는 빠집니다.
  - 지금 고른 개수보다 큰 숫자를 고르면 맨 뒤로 들어갑니다. 2개를 골랐을 때 4를 고르면 3번이 됩니다.
  - 끄기를 고르면 빠지고, 뒤에 있던 부스터가 한 칸씩 당겨집니다.
- **적용(Apply)**을 누르면 순서와 개수가 바로 다시 표시되고, 2초 안에 게임에 반영됩니다.

### 파일로

`%LOCALAPPDATA%\PersonalBooster\PersonalBooster.order` 파일에 고른 부스터가 한 줄에 하나씩, 1번부터 적혀 있습니다. 메뉴에서 바꾸면 이 파일도 함께 바뀝니다.

- 메뉴가 있으면 이 파일은 게임을 시작할 때만 읽습니다. 플레이 중에는 메뉴에서 바꾸세요.
- 메뉴가 실행되지 않았다면 이 파일로 고릅니다. 약 10초마다 다시 읽습니다.

모르는 이름과 중복은 건너뛰고, 앞의 4개만 씁니다. 처음에는 헬포드 공간 최적화, 체력 강화, 스태미나 강화, 근력 강화 순서로 골라져 있습니다.

| 파일에 쓰는 이름 | 부스터 |
|---|---|
| `HellpodSpaceOptimization` | 헬포드 공간 최적화 |
| `Vitality` | 체력 강화 |
| `Stamina` | 스태미나 강화 |
| `MuscleEnhancement` | 근력 강화 |
| `UAVRecon` | UAV 정찰 부스터 |
| `IncreasedReinforcementBudget` | 증원 예산 증가 |
| `FlexibleReinforcementBudget` | 유연한 증원 예산 |
| `LocalizationConfusion` | 위치 혼란 |
| `FastExtraction` | 숙련된 추출 파일럿 |
| `SlowStunResistance` | 동기부여 충격 |
| `CombatDrugs` | 실험용 주입 |
| `FieryDrop` | 파이어밤 헬포드 |
| `DoubleSampleChance` | 샘플 스캐너 |
| `DeathMarch` | 데드 스프린트 |
| `BigEnemiesDropSamples` | 샘플 추출기 |
| `ShockPods` | 스턴 포드 |
| `SmokePods` | 은밀 강하 |
| `FireExtinguish` | 통합 소화기 |

한국어 부스터 이름은 이 모드에서 붙인 이름이라 게임의 공식 한국어 표기와 다를 수 있습니다.

## 작동 원리

게임은 작은 함수 하나로 부스터가 켜져 있는지 판단합니다. 이 함수는 함대 강화(DSS)가 주는 부스터와 분대원 각자가 장착한 부스터를 확인합니다. Personal Booster는 2초마다 **내 PC 메모리에 있는** 분대원 부스터 칸을 확인하고, 내 순서와 다르면 1명당 1개씩 내 부스터를 써넣습니다. 게임 코드는 바꾸지 않고, 함대 강화 부스터도 건드리지 않습니다. 메모리 구조가 예상과 조금이라도 다르면 아무것도 쓰지 않고 멈추고, 로그에 이유를 남깁니다.

자세한 내용은 [개발 문서](docs/DEVELOPMENT.md)에 있습니다.

## 게임에서 확인된 것

1.1.0 버전에서 확인 (2026-10-11)

- 게임 안에서 부스터 확인 함수와 부스터 이름표(부스터 20종)를 찾습니다.
- 솔로에서는 1번만 적용됩니다.
- 모드 로더 없이도 스스로 실행되고, 게임 소리가 정상이며, 함께 들어 있는 옵션 → MODS 메뉴가 동작합니다.

같은 분대원 칸에 써넣던 이전 버전에서 확인 (2026-10-11)

- 팀원 칸에 써넣은 부스터가 나에게 적용됩니다.
- 파이어밤 헬포드는 내 헬포드가 착지한 곳에만 불이 붙고 팀원 헬포드에는 붙지 않습니다. 솔로에서 불이 적에게 실제로 피해를 주고, 남의 방에서는 아군에게도 불이 붙었습니다. 다른 사람의 게임에도 불이 실제로 생긴다는 뜻입니다.

확인하지 않은 것: 미션 전체를 방장이 판정하는 부스터(증원 예산, 위치 혼란, 추출, 샘플 관련)는 방장 게임을 따를 것으로 예상됩니다. 이런 부스터는 내가 방장일 때만 효과가 있을 수 있습니다.

## 로그

`%LOCALAPPDATA%\PersonalBooster\PersonalBooster.log` (게임을 켤 때마다 새로 시작)

| 줄 | 뜻 |
|---|---|
| `Mod Options Menu: bundled` | 이 모드에 들어 있는 메뉴가 실행됨 |
| `Mod Options Menu: already running` | 다른 메뉴(Vanilla Plus Megapack)를 사용 |
| `Mod Options Menu: bundled copy not started: ...` | 메뉴 없음, 순서 파일로 고르기 |
| `picker ready in Options > MODS, picked n/4: ...` | 메뉴 준비 완료 |
| `picked n/4: ...` | 고른 부스터가 바뀜 |
| `ready: booster check found, ...` | 부스터 확인 함수와 이름표를 찾음 |
| `waiting for the squad` / `squad found, ...` | 불러오는 중. 함선이나 미션 사이에서는 정상 |
| `active: ... (N players)` | 지금 적용 중인 내 부스터와 게임이 준 부스터 |
| `write #N: ...` | 칸에 써넣은 기록과 써넣기 전 값 |
| `stopped: ...` | 안전장치가 작동해 멈춤, 이유 포함 |

## 게임이 업데이트되면

모드는 게임 코드와 데이터를 모양으로 찾기 때문에, 게임이 업데이트되면 `stopped:` 줄을 남기고 멈출 수 있습니다. 이때는 아무것도 쓰지 않습니다.

로더 없이 쓸 때 실행되는 브리지에는 지원 빌드의 원본 사운드 스크립트(Wwise callbacks)가 들어 있습니다. 업데이트로 이 스크립트가 바뀌면, Personal Booster가 업데이트될 때까지 소리에 문제가 생길 수 있습니다. **게임이 업데이트되면 새 빌드용 버전이 나올 때까지 Personal Booster를 꺼 두세요.** 또는 Bingus Shared Loader를 맨 아래에 두고 함께 쓰세요.

## 라이선스

Zero-Clause BSD (0BSD), [LICENSE](LICENSE) 참고. 배포 zip에는 게임의 원본 사운드 스크립트도 들어 있습니다(소리 파일이 아니라, 사운드 엔진에 무엇을 재생할지 알려 주는 약 10KB 크기의 Lua 바이트코드). 이 스크립트의 권리는 원래 소유자에게 있으며 이 라이선스가 적용되지 않습니다.
