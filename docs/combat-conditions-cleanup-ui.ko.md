# 전투 조건 정리·보스 선택 — UI (F2-U, R1~R8)

2026-09-29. **1단계 완료**: R1·R2·R3·R5·R6·R7은 기존 wire만으로 연결해 실제 격리 API에서도 확인했다. **R4(방어력 자동 전환)·R8(보스 선택)은 mock으로 화면을 만들었고 Backend 확정 wire는 Director 통지 대기**다. 이 문서는 UI 구현·검증 보고이며 독립 QA·원본 배포 보고가 아니다.

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

잠정 wire 세부는 `raid-conditions.js` 한 곳에 있다: `DEF_WIRE.combatFields()` = `{enemyDefenseMode:'cumulative_switch'}`, `BOSS_WIRE.listRoute` = `GET /api/runtime/solo-raid-bosses`, 응답 `{bosses:[{id,name,season,imageUrl,weakElement,dummy}]}`, 요청 `conditions.boss = {id}`. 둘 다 `confirmed:false`. Backend 계약 확정 후 교체하고 true로 바꾼다.

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

## 4. 확정 wire 연결 시 할 일 (Director 통지 후)

1. Backend 확정 커밋 merge, 계약의 방어력 모드 필드·보스 목록 경로·응답 형태·선택 저장 필드로 `DEF_WIRE`·`BOSS_WIRE`·`normalizeBosses` 교체 후 `confirmed:true`.
2. 저장 결과의 방어력 모드·보스 표시 형태(예: compatibility 류 표시 객체)가 있으면 결과 카드·통계 카드에 연결. 이전 고정 DEF 기록은 저장값 그대로.
3. 실제 격리 API·브라우저: 방어력 자동 전환 요청·결과 표시(전환 시점 표시가 있으면 연결), 보스 목록·이미지·선택 저장, 기존 회귀. EXE 배포 안 함.

## 5. 미실행·한계

- R4·R8 실제 API 연결 없음(wire 미확정). 잠정 필드 이름은 바뀔 수 있다.
- 보스 이미지·이름은 mock 합성(`모의 보스 A` 등)이며 실제 솔로 레이드 보스 데이터가 아니다.
- 예외 캐릭터 한글 이름은 presentation 카탈로그에 의존한다. 카탈로그에 없는 캐릭터는 API의 영문 이름으로 대체된다(코드는 표시하지 않음).
- EXE 빌드·배포 없음.
