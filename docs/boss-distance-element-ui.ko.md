# 보스 거리·약점 속성 조건 — UI (F-COND-U)

> 2026-09-29 후속: 속성 이름 영어 병기·약점 팝업 설명 문장·거리 표의 출처/미확정 문구·예외 캐릭터 코드 표시는 사용자 요구 R1·R2로 바뀌었다 — [F2-U](combat-conditions-cleanup-ui.ko.md). 아래 문구 예시는 당시 기록이다.

2026-09-28~29. **U-FIX-2 완료**(사거리·속성 데이터 오류 진단, 7절). 2026-09-28. **mock 단계 완료**(1~5절, 당시 기록) → **단계 B 완료**(Backend 확정 `796eec3` merge, 확정 wire 연결, 실제 격리 API·브라우저 검증 — 6절). 이 문서는 UI 구현·검증 보고이며 독립 QA 수용·원본 배포 보고가 아니다. 1~5절과 6절이 다르면 6절이 우선한다.

배정: [F-COND-1 지시서](C:/Users/user/orca/workspaces/Nikke-Simul/Director/docs/boss-distance-element-assignments-2026-09-28.ko.md)의 "결정한 기본값"·"공통 기준"·"F-COND-U" 절. 공통 기준은 [client_f32 통합 지시서](C:/Users/user/orca/workspaces/Nikke-Simul/Director/docs/client-f32-integration-assignments-2026-09-28.ko.md)의 "공통 기준·보존"을 따른다. Director 문서는 읽기만 했다.

## 1. 기준·보존

- 시작 HEAD `0e83328`(U-FIX-1). Director `cd004f1`(원본 main, client_f32 배포본)을 일반 merge했다 — 이미 `0e83328`을 포함해 **fast-forward**, `apps` 차이 0. 미추적 `package-lock.json`(SHA-256 `2ef4178a…c767`) 보존·커밋 제외.
- 편집: `apps/desktop-ui/{combat-conditions.js(신규), app.js, single-deck-stats.js, simul.css}`, `tests/ui/{combat_conditions.test.mjs, check_combat_conditions_mock.py, fixtures/combat-ranges-mock.json}`(신규), 이 문서. 엔진·Backend·QA 파일 수정 없음. 단일 히트 검산(web `/legacy/`)은 바꾸지 않았다.
- API 서버를 띄우지 않았다. 원본 배포본 사용 중이므로 5180/5181·원본 경로 프로세스·EXE·원본 계정/캐시는 읽지도 건드리지도 않았다. 새 Run/Dispatch/워커·push·배포 없음.

## 2. 구현 (mock 단계 — 당시 기록)

### 2.1 flag와 live 보존

mock 단계 당시 `combat-conditions.js`의 `COND_WIRE.confirmed = false`였고 **그동안 live 화면·요청은 기존과 같았다**(체크박스 `distance`/`element`, `combat.properDistance`/`elementAdvantage` bool). 새 컨트롤·요청 필드·결과 모드 표시·통계 카드는 모두 `confirmed`일 때만 나온다. 잠정 wire 세부(경로 `GET /api/runtime/combat-ranges?snapshotId=`, 사거리 응답 형태 등)는 이 파일 한 곳에만 두었고, 단계 B에서 확정 계약으로 교체했다(잠정 경로는 Backend가 채택하지 않음).

### 2.2 화면

| 요구 | 구현 |
|---|---|
| 체크박스 → 아이콘 버튼 + 현재 값 | 32×32 정사각형 버튼 2개(`↔` / 선택한 속성 아이콘, 없으면 `◇`)와 `적정 거리 · 35`·`적정 거리 · 미설정`, `약점 · 작열(Fire)`·`약점 · 없음` 표시. `코어 명중` 체크박스는 그대로. hidden input을 만들지 않고 상태는 컨트롤러가 가진다 |
| 거리 팝업 | `<dialog>` 모달. 슬라이더 + 숫자 입력(0–100 정수, 소수·범위 밖·문자는 오류 표시 후 적용 거부, 절삭·보정 없음) + `미설정`. 현재 덱 멤버별 판정(적정 거리 `min–max` / 범위 밖 / RL `보너스 없음(데이터 0–0, 확인 필요)` / 사거리 정보 없음)을 입력 중 실시간 갱신. 무기군별 적정 사거리 표(API 값, 인원, 예외 캐릭터). "무기군 표는 참고용, 판정은 캐릭터별 값" 안내 |
| 약점 팝업 | 제목 `보스의 약점 속성`, 강조 문구 **"보스의 약점 속성 — 이 속성 니케가 우월 코드 보너스를 받습니다."**, "니케 자신의 속성이나 보스 자신의 속성이 아닙니다 · 상성표 미사용" 설명. `code-*.png` 5속성 버튼 + `없음`, 각 버튼 아래 그 속성의 덱 멤버(`덱: 리타, 누아르` / `덱에 없음`). 클릭 즉시 설정 |
| 키보드·ESC | 버튼 Enter로 열기, 모달 포커스, ESC·취소·닫기는 **적용 없이** 닫기, 닫힌 뒤 연 버튼으로 포커스 복귀. 속성 버튼 Enter 선택 |
| 1500/850/500px | 대화상자 `min(640px, 100vw−32px)`, 500px에서 거리 입력 2열·속성 2열. 가로 넘침 0 |
| 이전 방식 표시 | `describeConditionMode`: 저장 조건에 새 필드가 있으면 `보스 거리 35 · 약점 작열(Fire) (멤버별 판정)`, bool만 있으면 **`이전 방식(전원 적용) · 적정 거리 적용 · 우월 코드 미적용`**(경고색). 재해석하지 않고 저장값 그대로 설명. 솔로 레이드 결과 카드에 표시. 컨트롤도 `legacy` 표시를 받을 수 있다(현재 UI에는 저장 조건을 폼으로 다시 여는 경로가 없어 결과 표시만 사용) |
| 단일 덱 통계 조건 | 통계 화면은 솔로 레이드 폼의 조건을 쓴다. 요청에 같은 새 필드를 넣고, 덱 카드에 `보스 거리·약점` 요약(솔로 레이드에서 변경)을 표시 |

판정 규칙은 Director 잠정 기본값을 그대로 표시한다: 캐릭터별 `min ≤ 거리 ≤ max`(양끝 포함, 잠정), 평타만, RL 0–0은 보너스 없음·확인 필요, 미설정 = 전원 없음, 약점 = 멤버 속성 일치. UI의 멤버별 표시는 **미리보기**이며 실제 판정은 엔진이 한다. 사거리 데이터가 없는 멤버는 추정하지 않고 `사거리 정보 없음`. 멤버 속성은 사거리 응답 값을 쓰고, 없으면 presentation `elementCode`를 쓴다. presentation의 `weaponCode` 기본값(`sniper_rifle`)은 미리보기에 쓰지 않는다.

## 3. mock 단계 검증 — 모두 mock (당시 기록)

| 명령 | 증거 종류 | 결과 |
|---|---|---|
| `node tests/ui/combat_conditions.test.mjs` | mock 단위 | 8/8: flag false면 요청 필드 null(live 유지)·true면 `{bossDistance, bossWeakElement}`, 거리 엄격 파싱(−1/101/35.5/1e2/문자 거부), 경계 min−1/min/max/max+1·미설정·RL 0–0·불명, 섞인 덱 결과(in/in/no_bonus/out/in, 속성 일치), 무기군 표 6행·예외·0–0 문구, 약점 문구·아이콘 5개·덱 멤버, 요약·이전 방식 문구, escape |
| `python tests/ui/check_combat_conditions_mock.py --assets <Backend 격리 image-catalog 사본의 assets/ui>` | mock 브라우저(Chromium, 모든 `/api` 합성 HTTP, `combat-conditions.js`만 이 실행에서 `confirmed:true`로 제공, 디스크 파일은 false) | 통과 `artifacts/ui/combat-conditions-mock/run-28a261217a57`. 폼에 옛 체크박스·hidden input 없음, 아이콘 32×32 두 개, 키보드로 거리 팝업 열기, 35 입력 시 멤버 판정, 101 오류·적용 거부, 슬라이더 35 적용·포커스 복귀, 50 입력 후 ESC → 35 유지, 약점 문구·속성 이미지 로드·`덱: 리타, 누아르`, Enter로 작열 선택, 1500/850/500px 폼·두 팝업 뷰포트 안·가로 넘침 0, replay 요청 `bossDistance:35, bossWeakElement:"Fire"`·bool 없음, 결과 `per_member`, bool만 저장된 응답 → `이전 방식(전원 적용) · 적정 거리 적용 · 우월 코드 미적용`, 통계 카드 표시·통계 요청 같은 필드, JS 오류 0. 아이콘은 Backend `artifacts/image-catalog-fix/0af4c1f9…/origin/presentation/assets/ui`를 읽기 전용 제공(원본 데이터 루트 미사용) |
| `node tests/ui/{single_deck_stats,client_f32_mock,damage_audit}.test.mjs`, vitest | 기존 회귀 | 통과 (17/17, 13/13, 19/19, 13/13) |
| `check_solo_raid_level.py`(flag false: 기존 체크박스·bool 요청), `check_single_deck_stats_browser.py`, `check_client_f32_mock_browser.py`, `check_damage_audit_browser.py --real-replay <Director 저장 replay>` | 기존 회귀 | 통과. damage audit 브라우저는 첫 실행이 로컬 정적 서버 `ERR_CONNECTION_REFUSED` 콘솔 오류 1건으로 실패했고, 코드 변경 없이 2회 재실행 모두 통과 — 일시 연결 문제로 판단하나 재현 원인은 확정하지 않았다 |

mock 사거리 fixture(당시 `tests/ui/fixtures/combat-ranges-mock.json`, 단계 B에서 확정 형태의 `combat-conditions-mock.json`으로 대체): 무기군 범위·인원은 Director 집계를 옮긴 값, 멤버별 값은 경계·0–0 사례를 만들기 위한 **합성 배정**이며 실제 캐릭터 데이터가 아니다.

## 4. 확정 wire 연결 시 할 일 (당시 계획 — 모두 수행, 6절)

1. Backend 확정 커밋 merge, 계약 문서의 조건 필드·사거리 API 경로·응답 형태·속성 철자에 맞춰 `COND_WIRE`와 `normalizeRanges`·`conditionWire` 교체 후 `confirmed:true`.
2. 이전 bool 저장본 호환 응답 형태(명시 표시 필드가 있으면 그것을 사용)와 새·옛 필드 동시 지정 오류 문구 연결.
3. 실제 격리 API·브라우저: 사거리 표·멤버 판정이 API 값과 일치, replay·통계 요청 새 필드, 결과·로그의 멤버별 적정 거리/우월 코드, 이전 방식 표시, 기존 회귀. EXE 배포 안 함.

## 5. mock 단계 미실행·한계 (당시 기록)

- mock 단계에서는 실제 API 연결·종단 검증이 없었다(6절에서 수행).
- 저장된 조건을 폼으로 다시 여는 기능은 현재 UI에 없어 "이전 방식" 표시는 결과 카드에서만 한다. 통계 화면은 실험 요청 조건을 응답에서 다시 받지 않으므로 복원 실험의 조건 모드는 표시하지 않는다(Backend가 조건을 돌려주면 연결 가능).
- 적정 거리·우월 코드 판정 규칙(양끝 포함, RL 0–0)은 Director 잠정 가설이며 실측 검증 전이다.

## 6. 단계 B — 확정 wire 연결·실제 격리 API 검증

Director 통지(2026-09-28): Backend 확정 `796eec3bd4c6852c8dba7618c2b8584c142ad4c1`(엔진 `f374c1d` 포함) merge, 확정 wire는 Backend `docs/single-deck-compute-contract.ko.md` F-COND-B 절, 배경 `docs/boss-distance-element-backend.ko.md`.

### 6.1 merge

일반 merge `e3dc7b8`, 충돌 0. 자기 커밋 `cc24bc9` 보존.

### 6.2 연결 (확정 wire)

| 항목 | 연결 |
|---|---|
| flag | `COND_WIRE.confirmed = true`. 솔로 레이드 폼에서 옛 체크박스 `distance`/`element`가 사라지고 아이콘 컨트롤이 기본이 됐다 |
| 무기군 표 | `GET /api/runtime/combat-conditions`: `weaponRanges[].{weaponType, characterCount, ranges[isTypical], exceptions[profile], rangeBonusAvailable, diagnostics}` → 대표 구간(`isTypical`)·인원·예외 캐릭터(`이름 (#ID): min–max`). `rangeBonusAvailable:false`(RL)는 `0–0 · 보너스 없음(확인 필요)`. 속성 아이콘은 `elements[].iconUrl`. `source`(path·version)와 `실게임 검증 전`(gameVerified=false) 표시. 409 `combat_profile_catalog_missing` 등 오류는 표 자리에 메시지로 표시 |
| 멤버 판정 미리보기 | `GET /api/snapshots/{id}/combat-conditions?characterIds=…`(덱 순서). profile의 `bonusRangeMin/Max`·`element`·`rangeBonusAvailable`로 표시. 편성이 바뀌면 다시 조회 |
| 요청 | `conditions.combat.bossDistance`(0–100/null)·`bossWeakElement`(`Fire/Water/Wind/Iron/Electronic`/null)를 **항상 둘 다** 보낸다(모두 미설정도 명시 null). `properDistance`/`elementAdvantage`는 보내지 않는다. 솔로 레이드 replay와 단일 덱 통계 실험 모두 |
| 저장 모드 표시 | replay 응답 최상위·`BatchStatus.input`의 `conditionCompatibility`(`per_member`/`legacy_global`, `label`)의 label을 그대로 쓰고 값만 덧붙인다: `보스 거리·약점(멤버별) · 보스 거리 35 · 약점 작열(Fire)`, `이전 방식(전원 적용) · 적정 거리 적용 · 우월 코드 미적용`(경고색). 필드가 없는 과거 기록은 `…/condition-compatibility` 읽기 전용 endpoint로 표시한다. compatibility 객체를 combat에 다시 합치지 않는다 |
| 통계 화면 | 실행 전에는 폼의 예정 조건, 실험이 있으면 저장된 `conditionCompatibility`를 `보스 거리·약점` 카드에 표시(`저장된 실험 조건`) |
| Q3 하니스 호환 | `tests/q3/check_ui_contract.mjs`는 `app.js`의 submit 콜백 본문만 VM에서 실행한다. mock 단계 `cc24bc9`에서 콜백이 모듈 수준 헬퍼를 호출해 이 검사가 **23/26으로 깨져 있었다**(mock 단계 회귀 목록에 이 검사를 넣지 않아 놓침). 새 조건 필드 계산을 콜백 안으로 옮겨 26/26 복구 |

### 6.3 검증 — 증거 종류 구분

**실제 격리 API + Chromium**: `python tests/ui/check_combat_conditions_live.py --dotnet <SDK dotnet.exe> --source-data <Backend I-BE 격리 run의 data> --source-roster <Nikke-Dmg-Simulator/Database/raw/blabla_roledata.json> --assets <Backend image-catalog 격리 사본 assets/ui>` → **통과** `artifacts/ui/combat-conditions-live/run-7e01729b52f5`(최종 코드; 앞선 `run-f205cb15a298`·`run-3b7aa39eaa24`도 통과).

- 격리: 이 worktree Release API(경고 0·오류 0), 임의 포트, run 폴더 안 새 dataRoot·새 합성 계정. 공개 카탈로그 allowlist 복사 후 **그 격리 runtime에만** `tools/data-pipeline/prepare_combat_conditions.py --runtime-root <격리>/runtime --source-roster <공개 roster>` 실행(원본 `data/local` 미실행). 새 runtime `9c98c91c…71cd`(Backend 보고와 같은 ID). 속성 아이콘은 격리 사본에서 복사. 원천·roster·아이콘 해시 전후 동일. 합성 HTTP는 bootstrap 연결 추가·combat-powers `{}`뿐이고, 이전 방식 시나리오 한 건만 **나가는 요청**을 옛 bool로 바꿔 실제 API로 보냈다(응답은 실제).
- 표·미리보기 = API: 무기군 6행(SG 0–25/26, SMG 15–35/30, AR 25–45/35, MG 35–55/24, SR 45–100/36·예외 Harran #5042 25–45, RL 0–0 보너스 없음/41)이 API 응답과 일치. 합성 덱 profile(리타 SMG 15–35 Iron, 블랑 AR 25–45 Wind, 앨리스 SR 45–100 Fire, 누아르 SG 0–25 Wind, 모더니아 MG 35–55 Fire)로 거리 35 판정 in/in/out/out/in. 약점 팝업 5속성 이미지 로드, 속성별 덱 멤버 표시가 API 속성과 일치.
- 거리 35·약점 Fire replay: 요청 `bossDistance:35, bossWeakElement:"Fire"`, 옛 bool 없음, 200, `conditionCompatibility.mode=per_member`, 결과 문구가 API label로 시작. **엔진 결과**: 피해 로그 대상 앨리스의 평타 12발 전부 `properDistance=false, elementAdvantage=true`(거리 범위 밖·Fire 일치 기대와 일치).
- 모두 미설정 replay: 요청 두 필드 명시 null, 200, `per_member`, `보스 거리 미설정 · 약점 없음`.
- 이전 방식 replay(요청만 옛 bool로 변경): 실제 응답 `legacy_global`/`이전 방식(전원 적용)` → 화면 `이전 방식(전원 적용) · 적정 거리 적용 · 우월 코드 미적용`, `condition-compatibility` endpoint 값 동일.
- 통계 runs 1: 요청 같은 두 필드, batch completed, `input.conditionCompatibility` per_member, `summaryVersion cpu-summary.3-boss-conditions`, 카드 `보스 거리·약점(멤버별) · 보스 거리 35 · 약점 작열(Fire)` / `저장된 실험 조건`.
- 혼용 요청(API 직접, UI는 보내지 않음): 400 `boss_conditions_mixed_with_legacy`.
- 1500/850/500px: 두 팝업 뷰포트 안·가로 넘침 0, 통계 넘침 0, JS 오류 0. 실제 데이터 스크린샷에서 원천 sha 문구가 대화상자 오른쪽으로 잘리는 것을 발견해 줄바꿈 CSS를 추가했다.

**mock·기존 회귀** (최종 코드):

| 명령 | 증거 종류 | 결과 |
|---|---|---|
| `node tests/ui/combat_conditions.test.mjs` | mock 단위(확정 형태 fixture) | 9/9 |
| `python tests/ui/check_combat_conditions_mock.py --assets …` | mock 브라우저(모든 /api 합성, 확정 route) | 통과 `run-cbf4851eadab`: 기존 항목 + compatibility 없는 기록의 endpoint 조회 |
| `node tests/q3/check_ui_contract.mjs <검수 Q3 engine-example result.json>` | Q3 하니스(읽기 전용 입력) | 26/26 (수정 전 23/26) |
| `python tests/ui/check_client_f32_live.py …` | 실제 격리 API 회귀(client_f32·U-FIX-1) | 통과 `run-6a6e9cfb2848`. summary 버전을 하드코딩 `cpu-summary.2-client-f32` 대신 API 값으로 확인하도록 검사 수정(Backend가 `cpu-summary.3-boss-conditions`로 올림) |
| `check_solo_raid_level.py` | 합성 HTTP 회귀 | 통과. 기대값을 새 조건(두 필드 명시 null, 옛 bool 부재)으로 갱신 |
| `single_deck_stats`·`client_f32_mock`·`damage_audit` 단위, vitest, `check_single_deck_stats_browser.py`, `check_client_f32_mock_browser.py`, `check_damage_audit_browser.py --real-replay` | 기존 회귀 | 모두 통과 (17/17, 13/13, 19/19, 13/13) |

### 6.4 미실행·한계

- EXE 빌드·배포 없음. 원본 경로·5180/5181·원본 data/local 미접촉. **배포 시 원본 dataRoot runtime에도 `prepare_combat_conditions.py` 준비가 필요**하다(Backend 보고와 같음). 준비 전 runtime에서는 사거리 API가 409 `combat_profile_catalog_missing`이다(단계 B 당시 실제 409 화면 미확인 → 7절 U-FIX-2에서 실제 API로 확인).
- 합성 덱에 RL 멤버가 없어 실제 API의 멤버 `보너스 없음` 표시는 무기군 표로만 확인했다(멤버 행은 mock 단위·브라우저에서 확인).
- 판정 규칙(양끝 포함, RL 0–0, 평타만 거리)은 잠정 가설이며 실측 전이다. 엔진 멤버별 플래그는 피해 로그 대상 1명(앨리스)만 UI 검사에서 대조했다. 전 멤버 엔진 검증은 엔진·Backend·QA 범위다.
- 저장 조건을 폼으로 다시 여는 기능은 없어 이전 방식 표시는 결과 카드·통계 카드에서만 한다.

## 7. U-FIX-2 — 사거리·속성 데이터 오류 진단 (2026-09-29)

배정: Director 지시서 `B-FIX-2`·`U-FIX-2` 항목, Backend `97ba7bf` 보고서 마지막 B-FIX-2 절과 계약 문서 B-FIX-2 절. Backend `97ba7bf`를 일반 merge(`1a40692`, 충돌 0). Backend·엔진·QA 파일은 수정하지 않았다.

### 7.1 변경

- 오류 wire: HTTP 409 `{code:"combat_profile_invalid", message, characterId, field, reason}`(두 combat-conditions GET, replay POST, compute POST 공통), 기존 409 `combat_profile_catalog_missing`, 400 `combat_member_profile_missing:<id>`.
- `app.js` `api()`: HTTP 오류에 `status`와 함께 `code`·`details`(응답 본문)를 붙인다(메시지 불변).
- `combat-conditions.js` `describeCombatProfileError`: 한국어 진단 `사거리·속성 데이터 오류 · 앨리스(#5004) · 최소 사거리(bonusRangeMin) · 값 없음(키 누락). 서버 runtime의 사거리·속성 데이터 확인 후 prepare_combat_conditions.py로 다시 준비해야 합니다.` 이름은 덱 표시 이름(없으면 `#ID`), 카탈로그·출처 수준은 `카탈로그·출처 · <field>`. reason 8종 한국어(missing 값 없음(키 누락)/null 값이 null/wrong_type 자료형 오류/out_of_range 범위 오류(0–100, 최소 ≤ 최대)/unsupported_value 지원하지 않는 값/id_mismatch ID 불일치/weapon_mismatch 무기군 불일치/hash_mismatch 출처 해시 불일치), 모르는 reason·field는 원문. catalog_missing은 `이 runtime에는 사거리·속성 데이터(combatProfiles)가 준비되지 않았습니다 … 준비해야 합니다`, member_missing은 `리타(#5011)의 사거리·속성 데이터가 없습니다 …`. 서버 원문도 함께 표시한다.
- 표시 위치: 거리 팝업(무기군 표 자리·현재 덱 자리 각각, 멤버 조회 오류는 이전에는 삼켜졌음), 약점 팝업(덱 멤버 속성 확인 실패), 솔로 레이드 결과(`data-profile-error`), 단일 덱 통계 오류 목록. 경고 스타일(`.cond-load-error`)·줄바꿈.
- 연결 상태: 통계의 `classifyApiFailure`가 `error.code`를 우선 사용하고 세 코드를 계약 코드 목록에 추가. 409/400은 도달한 API 응답이라 `실제 API 응답` 상태를 유지한다(transport·5xx만 장애).
- 발견·수정한 대화상자 결함(`09e27cb`부터 잠재): 적용 후 포커스 복귀가 비동기 `close` 이벤트에만 있어, 키보드로 바로 다시 열면 포커스가 버튼에 없거나 늦게 온 `close` 처리기가 새로 연 팝업 내용을 지울 수 있었다. mock 브라우저 검사가 이번에 간헐 실패(3/4)해 드러났다. 적용 시 동기 포커스 복귀, `close` 처리기는 다시 열린 상태면 무시, 데이터가 이미 있으면 팝업을 다시 그리지 않도록 수정 — 이후 mock 검사 5/5 통과.

### 7.2 검증

**실제 격리 API + Chromium, 일부러 손상한 runtime**: `python tests/ui/check_combat_profile_errors_ui.py --dotnet … --source-data <Backend I-BE 격리 run의 data> --source-roster <공개 roster> --assets <격리 아이콘 사본>` → **통과** `artifacts/ui/combat-profile-errors/run-c405d3997fe1`(최종 코드; 앞선 `run-ce2c6287d744`·`run-a9a60e686f56`도 통과).

- 사례마다 새 격리 dataRoot·새 합성 계정·임의 포트. `prepare_combat_conditions.py` 후 **그 격리 runtime만** 손상해 `write_runtime`으로 hash-valid하게 기록: ① `5004.bonusRangeMin` 삭제, ② `5011.element = null`, ③ 준비하지 않은 runtime(combatProfiles 없음). 원천·roster·아이콘 해시 전후 동일. 원본 `data/local`·5180/5181 미접촉. 합성 HTTP는 bootstrap 연결·combat-powers `{}`뿐.
- 실제 응답: ①② 409 `combat_profile_invalid`(characterId/field/reason 포함), ③ 409 `{message:"combat_profile_catalog_missing: prepare pinned public roster catalog"}`.
- 화면: 세 사례 모두 거리 팝업 두 곳·약점 팝업·솔로 레이드 결과·통계 오류 목록에 기대 진단(①`앨리스(#5004) · 최소 사거리(bonusRangeMin) · 값 없음(키 누락)`, ②`리타(#5011) · 속성(element) · 값이 null`, ③`준비되지 않았습니다`)과 `prepare_combat_conditions.py` 안내 표시. replay·compute POST 실제 409. 통계 상단 `실제 API 응답`, `미연결` 없음. 1500/850/500px 가로 넘침 0·팝업 뷰포트 안, JS 오류 0.

**mock·기존 회귀** (최종 코드):

| 명령 | 결과 |
|---|---|
| `node tests/ui/combat_conditions.test.mjs` | 12/12 (신규 3: reason 8종·이름·필드·카탈로그 수준·메시지 전용 형태, catalog/member missing·무관 오류 null, 팝업 오류 표시) |
| `node tests/ui/single_deck_stats.test.mjs` | 18/18 (신규 1: 실험 생성 409 → 연결 유지·한국어 진단) |
| `check_combat_conditions_live.py`, `check_client_f32_live.py` (실제 격리 API) | 통과 `combat-conditions-live/run-ef88d25a4afd`(최종), `client-f32-live/run-73fbc79b5854` |
| `check_combat_conditions_mock.py` | 최종 코드 5/5 통과(수정 전 간헐 실패, 7.1) |
| `tests/q3/check_ui_contract.mjs <Q3 engine-example result.json>` | 26/26 |
| `check_solo_raid_level.py`, `check_single_deck_stats_browser.py`, `check_client_f32_mock_browser.py`, `check_damage_audit_browser.py --real-replay`, `client_f32_mock`·`damage_audit` 단위, vitest | 모두 통과 |

### 7.3 한계

- `combat_member_profile_missing`(400)은 단위 테스트만 했다(실제 runtime 손상 사례는 필드 손상 2종과 카탈로그 없음).
- EXE 배포 없음. 배포 시 원본 runtime 준비(`prepare_combat_conditions.py`)가 필요하다는 점은 6.4와 같다.
