# 전투 조건 정리·보스 선택 — UI (F2-U, R1~R8)

2026-09-29. **1단계 완료**(R1·R2·R3·R5·R6·R7 실제 연결, R4·R8 mock — 1~5절, 당시 기록) → **2단계 완료**(R4·R8 확정 wire 연결, 출처 표기 삭제, 실제 격리 API 검증 — 6절). 이 문서는 UI 구현·검증 보고이며 독립 QA·원본 배포 보고가 아니다. 1~5절과 6절이 다르면 6절이 우선한다.

배정: Director [F-COND-2 지시서](C:/Users/user/orca/workspaces/Nikke-Simul/Director/docs/combat-conditions-cleanup-assignments-2026-09-29.ko.md)의 "근거"·"공통 기준"·"F2-U" 절, 요구 원문 [R1~R8](C:/Users/user/orca/workspaces/Nikke-Simul/Director/docs/user-requests-2026-09-29.ko.md). Director 문서는 읽기만 했다.

## 1. 기준·보존

- 시작 HEAD `77264bf`(U-FIX-2). Director `e98db6a`를 일반 merge — fast-forward, `apps` 차이 0. 미추적 `package-lock.json`(SHA-256 `2ef4178a…c767`) 보존·커밋 제외.
- 편집: `apps/desktop-ui/{raid-conditions.js(신규), combat-conditions.js, app.js, simul.css}`, `tests/ui/**`, 이 문서, 자기 문서 두 곳의 안내 줄. Backend·엔진·QA 파일 수정 없음. 단일 히트 검산(web)은 바꾸지 않았다.
- 원본 배포본 사용 중이므로 5180/5181·원본 경로 프로세스·원본 `data/local`·EXE는 읽거나 건드리지 않았다. 실제 API 검증은 새 격리 dataRoot·임의 포트만 사용했다. 새 Run/Dispatch/워커·push·배포 없음.
- 참조 UI는 사용자의 다른 프로젝트 원격 저장소의 보스 카드 화면을 읽기 전용으로 참고했다(카드 구성: 시즌 배지·보스 이미지·이름·기본 약점, 선택 강조). 사용자 지시대로 코드·화면에 출처 표기를 남기지 않았다. 로컬 zip에는 해당 화면이 없었다.

## 2. 요구별 구현

| 요구 | 구현 | wire |
|---|---|---|
| R1 약점 팝업 | "니케 자신의 속성이나 보스 자신의 속성이 아닙니다…" 삭제, 상단 경고 유지. 속성 이름 한국어만(작열·수냉·풍압·철갑·전격) — 팝업 버튼, 현재 값(`약점 · 작열`), 결과·통계의 조건 문구 모두 | 변경 없음 |
| R2 거리 팝업 표 | 무기군 칸 = `weapon-*.png`(어두운 칩 배경, 흰 아이콘이 보이도록) + 이름. 열 제목 `적정 사거리`. 예외 캐릭터는 앱의 캐릭터 표시 데이터(presentation `displayName`)에서 한글 이름만(`하란: 25–45`), 코드 미노출. 하단 원천·sha·"실게임 검증 전"·"참고용" 문구 삭제. 미확정 문구 삭제: `보너스 없음(확인 필요)` → `보너스 없음 (0–0)`, 설명의 "(평타만, 양끝 포함 · 잠정)" 삭제 | 변경 없음 |
| R3 시간 | 입력 삭제. 요청 `durationFrames` = 10,800(180초) 고정 | 기존 필드 |
| R4 방어력 | **DEF wire 확정 후** 적 방어력 선택 삭제, 요청은 자동 전환 모드, 안내 `적 방어력은 30,925로 시작해 이 덱의 누적 대미지가 20억을 넘은 뒤부터 31,784로 자동 전환됩니다.` **확정 전(현재 live)** 은 기존 고정 DEF 선택과 기존 안내를 유지(자동 전환이 실제로 적용되지 않는데 그렇게 표시하지 않기 위해) | 잠정, mock |
| R5 크리티컬 | 유지, 기본값 `확률 적용`(sample), 선택지 순서 확률 적용·끔·항상 크리 | 기존 필드 |
| R6 대미지 정책 | 변경 없음(확정 시 제거 예정) | — |
| R7 샷건 계수 | 입력 삭제. `pelletCoefficientPolicy` = `per_trigger`(발사 1회) 고정 | 기존 필드 |
| R8 보스 선택 | **보스 wire 확정 후** 크리티컬·대미지 정책 줄 **아래**에 선택된 보스 카드(작은 가로형)와 클릭 시 카드 격자 대화상자(시즌 배지·이미지·이름·기본 약점 아이콘, 선택 강조, 키보드·ESC·포커스 복귀). 기본은 더미 보스(`현재 동작 · 보스별 조건 없음`). 안내 `보스 선택은 표시·저장만 합니다. 보스별 약점·거리 반영은 다음 단계입니다.` 선택 id를 요청 메타데이터로 보냄. 이미지 없는 보스는 그라데이션 자리표시. UI에 출처 표시 없음 | 잠정, mock |
| 결과 카드 | 저장된 조건을 저장값 그대로 한 줄 표시: `180초 · 방어력 자동 전환 (30,925 → 31,784) · 크리티컬 확률 적용 · 샷건 계수 발사 1회`, 이전 기록은 `120초 · 방어력 30,925 고정 · 크리티컬 끔 · 샷건 계수 펠릿마다`처럼 당시 값. Backend가 방어력 모드 표시 객체를 주면 그 label을 쓴다 | — |
| 단일 덱 통계 | 같은 폼 조건을 쓰므로 같은 규칙(180초·발사 1회·크리 기본·DEF 모드·보스 메타데이터) | — |

1단계 당시 잠정 wire(`enemyDefenseMode`, `GET /api/runtime/solo-raid-bosses`, `conditions.boss`)는 `raid-conditions.js` 한 곳에 두었고 두 flag가 false였다. 2단계에서 확정 wire로 교체했다(6절 — 잠정 필드는 Backend가 채택하지 않음).

Q3 하니스(`tests/q3/check_ui_contract.mjs`)가 submit 콜백 본문만 실행하므로 콜백 안의 새 값은 상수·`typeof` 가드로 자기완결을 유지했다(26/26).

경계 규칙(적정 거리 양끝 포함)은 화면에서 뺐고, 현재 계산은 엔진 규칙(양끝 포함)을 그대로 따른다 — 사용자 확인 대기(요구 원문 R2-5).

## 3. 검증

### 3.1 실제 격리 API + Chromium (R1·R2·R3·R5·R7 및 기존 기능 회귀)

전투 시간이 180초로 고정되면서 live 검사의 replay·실험도 모두 180초 전투로 실행했다.

| 명령 | 결과 |
|---|---|
| `python tests/ui/check_combat_conditions_live.py --dotnet … --source-data <Backend I-BE 격리 run의 data> --source-roster <공개 roster> --assets <Backend image-catalog 격리 사본 assets/ui>` | 통과 `artifacts/ui/combat-conditions-live/run-2d8e38647453`. 격리 dataRoot에 presentation 카탈로그(`presentation.json`, 같은 격리 사본)·속성/무기 아이콘을 복사(원천 해시 불변). 무기군 표 6행이 API와 일치, SR 예외가 **`하란: 25–45`**(코드·영문 없음), RL `0–0 · 보너스 없음`, 현재 값 `약점 · 작열`, 거리 35·약점 Fire replay에서 앨리스 평타 135발 모두 properDistance=false/elementAdvantage=true, 통계 카드 `보스 거리·약점(멤버별) · 보스 거리 35 · 약점 작열` |
| `check_combat_profile_errors_ui.py …` | 통과 `combat-profile-errors/run-5dfc8e23dec5` (손상 runtime 3종 진단 유지) |
| `check_client_f32_live.py …` | 통과 `client-f32-live/run-20d413964cf4` (client_f32·U-FIX-1 n=1/n=2·no-baseline·transport 장애) |

### 3.2 mock

| 명령 | 증거 | 결과 |
|---|---|---|
| `node tests/ui/raid_conditions.test.mjs` | mock 단위 | 4/4: 고정값·크리 기본, DEF 모드 wire 전/후 요청·안내, 저장 조건 문구(새·옛 기록), 보스 목록(더미 우선·선택·출처 미표시·escape) |
| `node tests/ui/combat_conditions.test.mjs` | mock 단위 | 12/12 (R1 영어 없음·문구 삭제, R2 아이콘·한글 이름·코드/출처/미확정 문구 없음으로 기대값 갱신) |
| `python tests/ui/check_raid_conditions_mock.py --assets …` | mock 브라우저. `raid-conditions.js`만 이 실행에서 두 flag true로 제공(디스크 false), 보스 목록·이미지는 합성 | 통과 `artifacts/ui/raid-conditions-mock/run-d27128bd6fe7`: 디스크 flag의 live 폼은 고정 DEF 선택 유지·보스 없음·시간/샷건 없음·크리 기본 확률 적용. 확정 폼은 시간/샷건/방어력 입력 없음, 대미지 정책 유지, 보스 선택이 크리·정책 아래·기본 더미, 대화상자 카드 4장(더미 우선, 이미지 로드), 키보드로 보스 선택·포커스 복귀·ESC, R1/R2 문구, replay·통계 요청(`durationFrames 10800`, `per_trigger`, `enemyDefenseMode`, `enemyDefense` 없음, 크리 sample, `boss.id`), 저장 조건 줄 새/이전 기록, 1500/850/500px 넘침 0, JS 오류 0 |

### 3.3 기존 회귀

`tests/q3/check_ui_contract.mjs` 26/26, `single_deck_stats`·`client_f32_mock`·`damage_audit` 단위, vitest 13/13, `check_combat_conditions_mock.py`, `check_solo_raid_level.py`(기대값을 180초·발사 1회 고정으로 갱신), `check_client_f32_mock_browser.py`, `check_single_deck_stats_browser.py` 모두 통과. 기존 live 검사들은 시간 입력 제거에 맞게 시간 입력 조작을 뺐다. 전체 실행 중 `check_solo_raid_level.py` 1회, `check_single_deck_stats_browser.py` 1회가 앱 준비 대기 60초 초과로 실패했고, 코드 변경 없이 곧바로 재실행하면 각각 3/3·2/2 통과했다(빌드 직후 부하 시점과 겹침, 원인 확정 안 함).

## 4. 확정 wire 연결 시 할 일 (당시 계획 — 모두 수행, 6절)

1. Backend 확정 커밋 merge, 계약의 방어력 모드 필드·보스 목록 경로·응답 형태·선택 저장 필드로 `DEF_WIRE`·`BOSS_WIRE`·`normalizeBosses` 교체 후 `confirmed:true`.
2. 저장 결과의 방어력 모드·보스 표시 형태(예: compatibility 류 표시 객체)가 있으면 결과 카드·통계 카드에 연결. 이전 고정 DEF 기록은 저장값 그대로.
3. 실제 격리 API·브라우저: 방어력 자동 전환 요청·결과 표시(전환 시점 표시가 있으면 연결), 보스 목록·이미지·선택 저장, 기존 회귀. EXE 배포 안 함.

## 5. 1단계 미실행·한계 (당시 기록)

- 1단계에서는 R4·R8 실제 API 연결이 없었다(6절에서 수행).
- mock 보스 이름·이미지(`모의 보스 A` 등)는 합성이다.
- 예외 캐릭터 한글 이름은 presentation 카탈로그에 의존한다. 카탈로그에 없는 캐릭터는 API의 영문 이름으로 대체된다(코드는 표시하지 않음).
- EXE 빌드·배포 없음.

## 6. 2단계 — R4·R8 확정 wire, 출처 표기 삭제 (2026-09-29)

Director 통지: Backend 확정 `aa1b71e`(엔진 `1a86ec9` 포함) merge(`92aef7b`, 충돌 0), 이어서 보스 한국어 이름 보완 `b977e77`(aa1b71e 직계, src/apps 변경 0) merge(`bcdd73a`, 충돌 0). 확정 wire는 Backend `docs/single-deck-compute-contract.ko.md` F2-B 절, 배경 `docs/combat-conditions-cleanup-backend.ko.md`.

### 6.1 연결

| 항목 | 연결 |
|---|---|
| R4 요청 | `DEF_WIRE.confirmed=true`. 새 요청은 `conditionProfile`을 보내지 않고(solo_raid 기본) `enemyDefense`·`defenseMode`도 보내지 않는다 — 서버 기본값(자동 전환, 시작 30,925)을 쓴다. `durationFrames 10800`·`per_trigger`는 기본값과 같은 값으로 명시(허용됨). `legacy` 프로필은 UI가 보내지 않는다 |
| R4 표시 | 결과 카드 조건 줄: 저장 `battleConditions`의 label과 값(`180초 · 덱 누적 피해에 따라 방어력 자동 전환 (30,925 → 31,784) · 크리티컬 확률 적용 · 샷건 계수 발사 1회 · 보스 …`). 이전 기록은 `…/skill-replays/{id}/battle-conditions`로 당시 조건(`이전 방식(고정 방어력) · 방어력 31,784`, 당시 시간·샷건). 실제 전환은 `result.defense`: `방어력 30,925 → 31,784 · 8.13초(488프레임) 블랑 타격 후 전환 · 누적 2,000,645,839` 또는 `방어력 전환 없음 · 끝까지 30,925 (누적 피해 20억 이하)`, fixed는 `방어력 31,784 고정`, 기록 없음(null)은 줄을 만들지 않음. 내부 hitTraceId는 표시하지 않음 |
| R4 통계 | 실험 `input.battleConditions`(없으면 `…/compute/experiments/{id}/battle-conditions`)와 `input.boss`로 `전투 조건` 카드 |
| R8 목록 | `BOSS_WIRE.confirmed=true`, `GET /api/presentation/solo-raid-bosses`. `bosses`만 선택 대상(기본 `defaultBossId`, 더미 우선, 나머지 최신 시즌 순). `diagnostics`가 있을 때만 `일부 보스 이름 준비 중`(`boss_catalog_not_prepared`는 `보스 목록 준비 중 · 지금은 더미 보스만 선택할 수 있습니다.`) — 제외 보스 이름·영문·원문 메시지는 표시하지 않음. 이미지 없는 항목은 그라데이션 자리표시, 더미는 줄무늬 |
| R8 저장 | 두 POST 최상위 `bossId`(솔로 레이드 replay, 통계 실험 — `buildExperimentRequest`에 `bossId` 추가). 결과·실험의 `boss.name`을 조건 줄에 표시 |
| 결과 조건 위치 | 실제 저장 replay는 조건을 `result.conditions`에 둔다(최상위 `conditions` 없음) — 조건 줄은 `result.conditions.combat`을 우선 읽는다. 1단계 mock은 최상위를 가정해 실제 API에서 크리티컬이 빠지는 것을 2단계 live 검사로 발견·수정 |
| 출처 표기 삭제(사용자 지시) | `app.js` 고급 진단 `화면·이미지 출처`의 `화면: Nikke-Local-Lab ·` 삭제(제목 `이미지 출처`, 이미지 출처 문구는 유지). 출처 서술 주석 정리: `cards.js`·`local-lab-detail.js` 첫 줄, 같은 성격의 `local-lab-account.js`·`local-lab-adapter.js` 첫 줄과 `simul.css` 주석 2곳. 파일 이름·함수 이름(`renderLocalLabDetail` 등)은 바꾸지 않음. 내부 설계 기록 문서(`docs/desktop-ui-migration.ko.md` 등)의 이식 이력은 역사 기록이라 손대지 않았다 |
| 기타 | 더미 카드 자리표시의 `더미` 글자 제거(이름과 중복) |

### 6.2 검증 — 실제 격리 API + Chromium

`python tests/ui/check_raid_conditions_live.py --dotnet … --source-data <Backend I-BE 격리 run의 data> --source-roster <공개 roster> --assets <격리 아이콘 사본> --boss-presentation <격리 보스 캐시> --expect-bosses 43` → **통과** `artifacts/ui/raid-conditions-live/run-45c85a7260d5`(b977e77 기준; aa1b71e 기준 `run-5a127a70f632`도 통과).

- 준비: 새 dataRoot·새 합성 계정·임의 포트, `prepare_combat_conditions.py`는 격리 runtime에만. 보스는 **`tools/data-pipeline/prepare_solo_raid_bosses.py --presentation-root artifacts/ui/boss-presentation-cache/<ts>-b977e77/presentation`**(격리 캐시, 네트워크)로 준비 → `{"displayed":43,"excluded":0,"complete":true}`, 이미지 42장. 원본 `data/local` 미실행. 원천·roster·아이콘·보스 파일 해시 전후 동일. 합성 HTTP는 bootstrap 연결·combat-powers `{}`뿐.
- 보스: API 43개(더미 + 시즌 1~42, 제외 0, complete true) = 대화상자 카드 43장, 이름 전부 API의 한국어 이름, 이미지 42장 로드, diagnostics 0이라 안내 없음. 기본 더미.
- 기본 replay(시즌 42 `앨트루이아` 선택): 요청 `bossId` 최상위, `conditionProfile`·`enemyDefense`·`defenseMode` 없음, 180초·per_trigger·sample. 응답 `battleConditions` solo_raid, `boss.name` 일치. 화면 조건 줄·방어력 줄(전환 없음)이 응답과 일치.
- 전환 replay: 나가는 요청에만 Backend 임계값 fixture와 같은 합성 100배 공격력 창(`attackBuffWindows`)을 추가(응답 실제). 실제 `result.defense.switchAfterHit`(488프레임·블랑·누적 2,000,645,839) → 화면 `방어력 30,925 → 31,784 · 8.13초(488프레임) 블랑 타격 후 전환 · 누적 2,000,645,839`. 1500/850/500px 넘침 0.
- 이전 방식 replay: 나가는 요청을 `conditionProfile:"legacy"`·120초·per_pellet·DEF 31,784 fixed로 바꿔 전송(UI는 보내지 않는 경로). 실제 `battleConditions.profile=legacy` → `120초 · 이전 방식(고정 방어력) · 방어력 31,784 · … · 샷건 계수 펠릿마다`, `방어력 31,784 고정`. endpoint 값 동일.
- 통계 runs 1: 요청 최상위 `bossId`, batch completed, `input.boss.name`·`battleConditions`·`defPolicy team_damage_threshold:30925:2000000000:31784`, 카드에 label·보스 이름. JS 오류 0.

### 6.3 mock·기존 회귀 (최종 코드)

| 명령 | 결과 |
|---|---|
| `node tests/ui/raid_conditions.test.mjs` | 5/5 (확정 wire: DEF 필드 미전송·endpoint, battleConditions 문구 새/이전, result.defense 전환/없음/fixed/null, 보스 목록 확정 형태·diagnostics 있을 때만 안내·제외 보스 미표시·escape) |
| `python tests/ui/check_raid_conditions_mock.py --assets …` | 통과 `raid-conditions-mock/run-189e8e9e0fd9`(확정 route·필드, 이전 기록 battle-conditions 조회) |
| `check_combat_conditions_live.py`, `check_combat_profile_errors_ui.py`, `check_client_f32_live.py` (실제 격리 API) | 통과 `run-973814429ac2`, `run-e4d8e48e4b62`, `run-f6401de85a6b` |
| Q3 26/26, `combat_conditions` 12/12, `single_deck_stats`, `client_f32_mock`, `damage_audit`, vitest 13/13, `check_combat_conditions_mock.py`, `check_client_f32_mock_browser.py`, `check_damage_audit_browser.py --real-replay` | 통과 |
| `check_solo_raid_level.py`, `check_single_deck_stats_browser.py` | 방어력 선택이 없어져 기대값 갱신(고정 DEF 미전송 확인) 후 통과 |

### 6.4 미실행·한계

- EXE 빌드·배포 없음. 원본 경로·5180/5181·원본 `data/local` 미접촉. **배포 시 원본 presentation에 `prepare_solo_raid_bosses.py`, runtime에 `prepare_combat_conditions.py` 준비가 필요**하다(Backend 보고와 같음). 준비 전에는 보스 목록이 더미만 + `보스 목록 준비 중` 안내다.
- 20억 초과 전환은 합성 100배 공격력 창으로만 재현했다(합성 계정 180초 기본 피해는 20억 미만). 경계 세부(정확히 20억 무전환·다음 타격부터)는 Backend 문서상 실게임 확인 대기 가설이다.
- 보스 선택은 표시·저장만 한다(보스별 약점·거리·DEF 반영은 다음 단계).

## 7. U-FIX-3 — 통계 DEF 카드(F2-Q-1)·캐릭터 코드 노출 정리 (2026-09-29)

배정: Director 지시서 `F2-Q`·`U-FIX-3` 항목, QA 보고서 `검수/docs/combat-conditions-cleanup-qa.ko.md`(검수 `09c9d8a`, 근거 `f2-2a4bc7b9cd59/defect-F2-Q-1.*`, 읽기만 함). 기준 `dae1949`, 새 merge 없음.

### 7.1 F2-Q-1 — DEF 정책 카드

`single-deck-stats.js`의 `DEF 정책` 카드 부제가 `'자동 20억 전환 없음'` 고정 문자열이었다. 저장 정책(`input.battleConditions`, 없으면 `/battle-conditions`, 그다음 `input.defPolicy`)과 실행 결과(`/results`의 `runs[].defense`, 최대 1,000행)로 `describeDefensePolicy`(raid-conditions.js)가 만든다:

| 경우 | 값 | 부제 |
|---|---|---|
| 실행 전(예정) | `자동 전환 (30,925 → 31,784)` | `누적 대미지 20억 초과 후 다음 타격부터 전환` |
| 자동·전환 없음 | 같음 | `전환 없음 · N회 모두 누적 20억 이하` |
| 자동·전환 있음 | 같음 | 1회: `방어력 30,925 → 31,784 · 20.88초(1,253프레임) 누아르 타격 후 전환 · 누적 2,000,901,314`, 여러 회: `N회 중 K회 전환 · 첫 결과: …`(1,000행 초과면 `(불러온 결과 기준)`) |
| 자동·전환 기록 없음(과거 행 null) | 같음 | `… · 실행 결과의 전환 기록 없음` |
| 이전 방식 fixed | `이전 방식 · 방어력 31,784 고정` | `이전 방식(고정 방어력) · 누적 대미지에 따른 전환 없음(당시 조건)` |

### 7.2 캐릭터 코드 노출 정리 (데이터 속성·내부 키 유지)

| 위치 | 이전 | 이후 |
|---|---|---|
| `single-deck-stats.js` 덱 목록 | 이름 + `#5004` 배지, 덱 정보가 없으면 이름 자리에 코드 | 한글 이름만(`data-character-id` 속성으로 보존), 없으면 `이름 미확인` |
| `single-deck-stats.js` 통계 멤버 이름 map | 이름 없으면 코드 | `이름 미확인` |
| `compute-adapter.js` OL 비교 변경 항목·이름 함수 | 이름 없으면 코드 | `이름 미확인` |
| `damage-log-adapter.js` 효과 출처(`auditNikkeText`) | `누아르 (#5009)`, `니케 #5008` | `누아르`, `이름 미확인 니케` |
| `combat-conditions.js` 사거리·속성 진단(`앨리스(#5004)`, `#9999`) | 코드 포함 | 이름만, 없으면 `이름 미확인 캐릭터` |
| `combat-conditions.js` 멤버 미리보기·이름 map | 이름 없으면 코드/영문 | `이름 미확인` |
| `app.js` 편성 멤버·조건 멤버·전술 요약·버스트 사이클 표·검산 결과 멤버 제목 | presentation 이름 없으면 코드 | snapshot 한글 이름, 없으면 `이름 미확인`(결과 제목은 `data-character-id` 보존) |
| `damage-log.js` 피해 로그 대상 이름 | 이름 없으면 코드 | `이름 미확인` |
| `burst-tactics.js` 전술 목록 이름 | 이름 없으면 코드 | `이름 미확인` |

타격·발사·함수·버스트 시전 번호, replay ID는 캐릭터 코드가 아니라 유지했다. 니케 관리·편성 카드 렌더에는 화면 문자로 나가는 코드가 없었다(데이터 속성·캐시 키만).

### 7.3 검증

- **실제 격리 API + Chromium** `python tests/ui/check_raid_conditions_live.py … --expect-bosses 43` → 통과 `artifacts/ui/raid-conditions-live/run-91b31b09b729`: 통계 실험 3건 — 기본(자동·전환 없음) `전환 없음 · 1회 모두 누적 20억 이하`, 나가는 요청에만 합성 100배 공격 창을 넣은 자동 전환 실험 `방어력 30,925 → 31,784 · 20.88초(1,253프레임) 누아르 타격 후 전환 · 누적 2,000,901,314`(실제 `runs[].defense`와 일치), 나가는 요청을 `conditionProfile:"legacy"`·fixed 31,784로 바꾼 실험 `이전 방식 · 방어력 31,784 고정`(`defPolicy fixed:31784`). 솔로 레이드·통계 화면 표시 텍스트에서 캐릭터 코드(`50xx`) 0건. 원천 해시 불변.
- 단위: raid 6/6(DEF 카드 5경우·옛 문구 부재·코드/trace ID 미노출), 통계 19/19(덱 목록 코드 없음·`이름 미확인`), 조건 12/12·damage_audit 19/19(코드 없는 이름으로 기대값 갱신).
- 기존 회귀: Q3 26/26, client_f32_mock, vitest 13/13, raid·combat·client_f32 mock 브라우저, 솔로 레이드·통계·damage audit 브라우저, combat-conditions·profile-errors·client_f32 live 모두 통과.
- EXE·원본 `data/local`·5180/5181 미접촉.

## 8. U-FIX-4 — 내부 키 화면 노출 정리(F2-Q-2) (2026-09-29)

배정: Director 지시서 `F2-Q 재수용`·`U-FIX-4`, QA 보고서 최신 절(검수 `eb7c23f`, 근거 `f2-ufix3-preparation/defect-F2-Q-2.json`, 읽기만 함). 사용자 지시: "화면에서는 이름으로 표시해야 함". 기준 `ad6d3f0`, 새 merge 없음. API·저장 source 키와 데이터 속성은 그대로 두고 **표시 문자열만** 바꿨다.

### 8.1 source 키 표시 — `display-labels.js`(신규) `describeSourceKey`

| 저장 source 키 | 화면 |
|---|---|
| `overload:5004:head:1:StatAtk` | `앨리스 · 머리 1번 줄 · 공격력` (부위 머리/몸통/팔/다리, 옵션 공격력·방어력·최대 장탄 수·크리티컬 확률/대미지·차지 대미지/속도·우월코드 대미지·명중률, 모르는 옵션 `오버로드 옵션`, 이름 없으면 `이름 미확인`) |
| `cube:<id>:<옵션>` / `collection:<id>:<옵션>` | `큐브 · 공격력` / `소장품 · 크리티컬 대미지`, 옵션을 모르면 `큐브 효과` / `소장품 효과` |
| `equipment:<부위>` | `장비 · 몸통` |
| `manual:attack:<n>` | `직접 입력한 버프 n` |
| `function:<id>` | U-FIX-4 당시 `스킬 효과 · 함수 <id>` → U-FIX-5에서 번호 제거(9절) |
| `skill:<캐릭터>:<함수>` | 기존대로 `누아르 · 스킬 1 · 함수 …`(이름만, 코드 없음) |
| 그 밖(합성 창 source 등) | `기타 효과` — 코드·원문 없음 |

### 8.2 같은 유형 정리 목록

| 위치 | 이전 | 이후 |
|---|---|---|
| `damage-log-adapter.js` 타격 검산 근거 `최종 공격력 입력` (F2-Q-2) | `상시 비율 · overload:5004:head:1:StatAtk +4.77%` | `상시 비율 · 앨리스 · 머리 1번 줄 · 공격력 +4.77%` |
| `damage-log-adapter.js` 효과 적용 기준 | `basis native_recipient`, 모르는 값은 `basis <원문>` | `수혜자 기초 스탯 기준` 등 한국어, 모르면 `적용 기준 미확인`/`적용 기준 미기록` |
| `damage-log-adapter.js` 미해석 효과 | `미해석 효과 (type 999)` | `미해석 효과` |
| `single-deck-stats.js` OL 후보 비교 표 | 부위 `head`, 옵션 `StatAtk` 원문 | `머리`, `공격력`(`data-slot`·`data-option` 보존) |
| `single-deck-stats.js` 표본 단계 카드 | `final`/`pilot` 원문 | `최종`/`파일럿`/`탐색`/`예열` |
| `app.js` 고급 진단 수집 확인 | 이슈 `path`(내부 경로·캐릭터 코드 포함 가능) · 메시지 | 메시지만(`data-issue-path` 보존) |

유지(내부 키가 아닌 기술 식별자·허용 범위, 당시 기록 — 함수 번호는 9절에서 제거): 타격·발사·함수·버스트 시전 번호, replay ID, 통계 화면의 입력 fingerprint·rules/summary 버전·schema, 대미지 정책 id(`client_f32` 등 선택지와 같은 정책 이름), 검산 단계 표의 엔진 연산 설명(`저장된 연산` 열), 사거리·속성 진단의 서버 원문(QA가 구조화 필드 경로를 허용 범위로 기록).

### 8.3 검증

- **실제 격리 API + Chromium** `check_raid_conditions_live.py … --expect-bosses 43` → 통과 `artifacts/ui/raid-conditions-live/run-dc278931ceeb`: QA 재현과 같은 앨리스 머리 1번 줄 StatAtk 4.77% 합성 계정의 180초 replay, 앨리스 타격 #200 검산 근거 `상시 비율 · 앨리스 · 머리 1번 줄 · 공격력 +4.77%`·`고정 가산 · 누아르 · 스킬 1 · 함수 227111001 +12,717`, 패널 본문 원문 키·코드 0건, 1500/850/500 넘침 0. 패널 조회 전후 `GET /runtime/skill-replays/{id}` 동일·총피해 동일(재계산·재저장 없음). DEF 카드 3경우·보스·코드 스캔 등 기존 항목도 통과, 원천 해시 불변.
- **실제 기존 저장 replay(재계산 없음)** `python tests/ui/check_source_labels_saved.py --saved-replay <Director 격리 live ui-response.json>` → 통과 `artifacts/ui/source-labels/run-eec83adc0ec8`: 저장본 그대로 제공(합성 HTTP), overload·skill source 타격 #184 `상시 비율 · 앨리스 · 머리 1번 줄 · 공격력 +11.11%` 등, 원문 키·코드 0건, 1500/850/500, 저장 파일 SHA-256 전후 동일. 이 저장본의 cube·collection 키는 타격 공격력 입력 밖에만 있어 해당 라벨은 단위 테스트로 확인했다.
- 단위: `display_labels.test.mjs` 3/3(키 14종·기준·미해석, 패널 텍스트, 저장 entry 불변), damage_audit 19/19(기준·미해석 기대값 갱신), 통계 19/19·조건 12/12·raid 6/6.
- 기존 회귀: Q3 26/26, vitest 13/13, raid·combat·client_f32 mock, 솔로 레이드·통계·damage audit 브라우저, combat-conditions·profile-errors·client_f32 live 모두 통과. EXE·원본 `data/local`·5180/5181 미접촉.

## 9. U-FIX-5 — 함수 번호 표시 제거 (2026-09-29, 사용자 결정)

화면 표시 원칙(사용자 결정): **함수 번호는 화면에서 지운다.** 타격·발사 번호, replay ID, fingerprint·규칙·summary 버전·schema, 대미지 정책 id는 유지한다. 기준 `00911ce`, 새 merge 없음. 내부 키·데이터 속성은 그대로다.

| 위치 | 이전 | 이후 |
|---|---|---|
| `display-labels.js` `function:<id>` source | `스킬 효과 · 함수 127131004` | 저장 스킬 슬롯으로 해석되면 `누아르 · 스킬 1`, 아니면 `스킬 효과` |
| `damage-log-adapter.js` 효과 출처·공격력 입력의 슬롯 설명(`auditOriginText`) | `스킬 1 · 함수 227110701`, `함수 N · 슬롯 미확인(하위 스킬·연결 함수)`, `함수 N`, `함수 ID 미기록` | `스킬 1`/`스킬 2`/`버스트`, 해석 못 하면 `스킬 효과`, 기록 없음은 `스킬 정보 미기록` |

앱의 다른 화면(솔로 레이드 결과 카드의 효과 이름은 이미 `스킬 1 대미지`·`추가 효과 N`, 통계·조건·편성 화면)에는 함수 번호 표시가 없었다(`apps/desktop-ui` 전체 `함수` 문자열 검색 0건). `버스트 시전 이벤트 #N`은 함수 번호가 아니어서 유지했다.

검증:
- **실제 격리 API + Chromium** `check_raid_conditions_live.py … --expect-bosses 43` → 통과 `artifacts/ui/raid-conditions-live/run-eb23cb8b89b5`: 앨리스 타격 #200 `상시 비율 · 앨리스 · 머리 1번 줄 · 공격력 +4.77%`·`고정 가산 · 누아르 · 스킬 1 +12,717`, 패널 본문에 `함수 N`·원문 키 0건, 저장 replay 조회 전후 동일. 보스·DEF 카드 3경우·코드 스캔 등 기존 항목 통과.
- **실제 기존 저장 replay(재계산 없음)** `check_source_labels_saved.py` → 통과 `artifacts/ui/source-labels/run-2d667263b13e`: `고정 가산 · 누아르 · 스킬 1 +17,191` 등, `함수 N` 0건, 파일 해시 불변.
- 단위: display_labels 3/3(함수 source 해석/미해석·패널 `함수` 문자 없음), damage_audit 19/19(기대값 갱신. U-FIX-3 때 주석 삽입으로 한 줄에 붙어 실행되지 않던 `originText` 단언을 분리해 다시 검사). 기존 회귀(Q3 26/26, vitest 13/13, 통계·조건·raid 단위, mock·브라우저·live) 모두 통과. EXE·원본 `data/local`·5180/5181 미접촉.
