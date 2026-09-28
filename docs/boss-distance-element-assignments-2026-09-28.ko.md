# 보스 거리·약점 속성 조건 — F-COND-1 배정 (2026-09-28)

## 최신 상태

- **F-COND-U mock 단계: 완료, Director 검토 수용.** UI `cc24bc9`(`cd004f1` ff 후), [보고서](C:/Users/user/orca/workspaces/Nikke-Simul/UI/docs/boss-distance-element-ui.ko.md). 변경은 `apps/desktop-ui`(app.js·새 `combat-conditions.js`·simul.css·single-deck-stats.js)·UI tests·UI 문서뿐. Director가 mock 캡처(거리·약점 팝업, 폼 1500px)를 확인했다: 32×32 아이콘 버튼 + 현재 값, 거리 슬라이더·숫자·미설정·멤버별 판정·무기군 표, 약점 팝업의 5속성 이미지·"보스의 약점 속성 — 이 속성 니케가 우월 코드 보너스를 받습니다" 경고·속성별 덱 멤버. 캡처의 멤버 무기·속성·예외 값은 **합성 mock 데이터**이며 실제 캐릭터 정보가 아니다.
  - `COND_WIRE.confirmed=false`라 실제 폼·요청은 아직 바뀌지 않았다. 잠정 wire(`GET /api/runtime/combat-ranges?snapshotId=`, `combat.bossDistance`/`bossWeakElement`, `Fire/Water/Wind/Iron/Electronic`)는 `combat-conditions.js` 한 곳에 모았다. Backend 확정 wire 통지 대기.
  - 검증은 mock만: 단위 8/8, mock Chromium, 기존 회귀 통과(audit 브라우저 첫 실행의 로컬 연결 거부 1건은 코드 변경 없이 재실행 2회 통과).
- **F-COND-E: 완료, Director 검토 수용.** 엔진 `d21895b`(`cd004f1` 일반 merge) → `f9ce075`(구현) → `f374c1d`(기록), [보고서](C:/Users/user/orca/workspaces/Nikke-Simul/시뮬레이션-엔진-담당/docs/boss-distance-element-engine.ko.md). 변경은 Engine·엔진 tests·보고서뿐. Director가 `BossConditionResolver`를 읽었다: 양끝 포함, RL 0–0 보너스 없음, 거리는 normal만·속성은 모든 피해, 사거리·속성 불명 멤버는 추정 없이 오류, 구 bool과 새 필드 혼용 거부(`boss_conditions_mixed_with_legacy`). `f374c1d`는 Backend와 충돌 없이 merge된다.
  - 엔진 보고 검증: Release Core/Engine 174/174(기존 147 + 신규 27), 기존 5인 180초 client 1,346,863,834 / legacy 1,346,859,763 정확 재현.
  - 내부 계약: `WeaponReplayConditions.BossDistance`(int?)·`BossWeakElement`(string, `Electronic` 철자), `WeaponReplayMember.BonusRangeMin/Max`(int?)·`Element`. 새 요청에서 이전 bool 기본 false를 채우면 혼용 오류가 난다.
  - Backend 추가 의존: `ComputeOverloadCatalog`의 `IncElementDmg` 유효 후보 판단이 전역 `combat.ElementAdvantage`를 읽으므로 새 모드에서는 멤버별 약점 일치로 연결해야 한다.
- **F-COND-B:** 진행 중. 엔진 `f374c1d` merge 통지(2026-09-28). 전달 `term_e5d05982…` 요청 `d7835645-d743-4bfc-9d22-fe30b2806d5d`, accepted=true·`input_accepted`(작업 중 턴에 전달). 직후 화면에서 엔진 파일 merge 출력을 확인했다.
- **F-COND-B: 완료, Director 검토 수용.** Backend `796eec3`(`cd004f1`·엔진 `f374c1d` ff 후), [보고서](C:/Users/user/orca/workspaces/Nikke-Simul/Backend/docs/boss-distance-element-backend.ko.md), 확정 wire는 [compute 계약](C:/Users/user/orca/workspaces/Nikke-Simul/Backend/docs/single-deck-compute-contract.ko.md) F-COND-B 절. Director 확인: `f374c1d..796eec3`에서 Core/Engine/Analysis/apps 변경 0, UI `cc24bc9`·QA `1abba9b`와 충돌 없이 merge된다. 재실행은 하지 않았다.
  - wire: `GET /api/runtime/combat-conditions`(무기군 사거리 표·예외·속성·rangeRule·gameVerified), `GET /api/snapshots/{id}/combat-conditions?characterIds=…`(멤버 사거리·속성, 요청 순서). **UI mock의 `combat-ranges` 경로와 다르다.** replay/compute `conditions.combat.bossDistance`(0–100 또는 null)·`bossWeakElement`(Fire/Water/Wind/Iron/Electronic 또는 null), 새 모드에서는 `properDistance`/`elementAdvantage` 생략(혼용 400), 모두 미설정인 새 모드는 두 필드 null 명시. 저장 replay·batch.input에 `conditionCompatibility`(`per_member`/`legacy_global`, 표시 label, 구 bool 두 값, boss 두 값), 조회 `/api/runtime/skill-replays/{id}/condition-compatibility`·`/api/compute/experiments/{id}/condition-compatibility`(원래 GET·export·파일 재작성 없음). `IncElementDmg` OL 후보도 멤버별 약점 일치로 연결.
  - 데이터: 공개 roster(SHA `8568963a…`) 192명에서 사거리 집계, 하란(5042) SR 예외 25–45·RL 0–0 원천 그대로.
  - Backend 보고 검증: Release 경고 0/오류 0, .NET 372(Backend 157, Core 174, Analysis 41), Python 10. 격리 API: 192명·6무기군·예외, 기존 bool replay 1,586,529·멤버 결과 전환 전 정확 재현, 거리 35/Fire 멤버별 hit flag, null 모드 저장, 잘못된 입력 8종 400, 120프레임 batch 세 조건 fingerprint·캐시·통계 분리, Fire 속성 OL 후보는 앨리스·모더니아만.
  - **배포 의존(중요):** Git 제외 runtime에 `combatProfiles`를 준비해야 한다 — `tools/data-pipeline/prepare_combat_conditions.py --runtime-root <대상>/runtime --source-roster <고정 blabla_roledata.json>`. 기존 graph·구 catalog 보존, 새 runtime ID `9c98c91c…`. 원본 `data/local`에는 아직 실행하지 않았다(배포 단계에서 사용자 확인 후 실행).
- **통지(2026-09-28):** F-COND-U 실제 연결(단계 B), F-COND-Q 독립 수용 단계 1(API) 배정. 전달: UI `term_c322a450…` 요청 `c9f7cb76-696a-414e-9316-54b2e5aec021`, QA `term_234e279b…` 요청 `9f839749-74ae-4ac4-a096-dd566524cfaa`. 둘 다 accepted=true, `input_accepted`·`turn_started`. 둘 다 격리 dataRoot에서만 runtime을 준비하고 원본 `data/local`에는 실행하지 말라고 지시했다.

### F-COND-Q — 독립 QA (검수 담당)

소유·금지는 [client_f32 통합 지시서](client-f32-integration-assignments-2026-09-28.ko.md)의 Q-F32와 같다(제품 수정 금지, 담당 검사 스크립트·정답 재사용 금지, 합성 계정·격리 포트·격리 dataRoot, 부하·Q-CPU-10K 보류).

- **단계 1(지금, API):** Backend `796eec3`를 일반 merge. 격리 dataRoot에 `prepare_combat_conditions.py`로 runtime을 준비하고 자체 검사로: 사거리 표·예외가 roster 원천과 일치(독립 집계), 멤버 프로필, 경계 min−1/min/max/max+1·RL 0–0·SR 예외·사거리/속성 불명 오류, 거리는 normal만·속성은 모든 피해, 섞인 덱에서 멤버별 hit flag와 독립 산술 피해, 구 bool replay·batch의 정확 재현과 `conditionCompatibility` 표시·조회(원본 파일 불변), 혼용·범위 밖·잘못된 속성 400, fingerprint·캐시·통계 분리, 속성 OL 후보의 멤버별 판단.
- **단계 2(UI 인계 후 Director 통지):** 실제 브라우저로 아이콘 버튼·두 팝업·약점 경고 문구·멤버별 미리보기·이전 방식 표시·레이아웃·키보드/ESC·기존 회귀.

## 사용자 요청

배포본을 사용한 사용자의 첫 개선 요청(2026-09-28, 솔로 레이드 "전투 조건" 화면 캡처 첨부):

- **적정 거리**: 체크박스 대신 보스 거리를 **0 ~ 100**으로 설정한다.
- **우월 코드**: 체크박스 대신 **5속성 중 하나**를 고른다. 사용자가 고르는 것은 **그 보스의 약점 속성**이며, 잘못 고르지 않도록 UI에 명시한다.
- 각 항목 옆에 **정사각형 작은 아이콘**을 두고 클릭하면 팝업을 연다.
  - 거리 팝업: 보스 거리를 입력하고, **무기군별 적정 사거리**를 함께 보여 입력 시 참고하게 한다.
  - 약점 팝업: **5속성 이미지** 중 하나를 클릭하면 그 속성으로 설정된다.

## 현재 구조와 필요한 변경 (Director 확인)

- 조건은 덱 전체에 하나의 bool이다: `combat.properDistance`, `combat.elementAdvantage`(`apps/desktop-ui/app.js`의 솔로 레이드·단일 덱 통계 폼). 엔진은 `SkillReplay.cs`에서 `ProperDistance = normal && C.ProperDistance`, `ElementAdvantage = C.ElementAdvantage`로 **모든 멤버에게 같은 값**을 준다.
- 요청대로라면 멤버마다 달라진다: 멤버 무기의 적정 사거리 `[min, max]`에 보스 거리가 들어가면 적정 거리, 멤버 속성이 보스 약점 속성과 같으면 우월 코드.
- 제품 런타임 카탈로그에는 사거리 데이터가 **없다**(`bonusrange` 키 없음). 공개 roster(`Nikke-Dmg-Simulator/Database/raw/blabla_roledata.json`, H-SRC 근거 S7)에는 캐릭터별 `bonusrange_min/max`가 있다. Director 집계: SG 0–25(26명), SMG 15–35(30), AR 25–45(35), MG 35–55(24), SR 45–100(35, 예외 1명 25–45), RL 0–0(41). 속성 5종(Fire·Water·Wind·Iron·Electronic).
- 속성 아이콘은 이미 있다: `data/local/presentation/assets/ui/code-{fire,water,wind,iron,electric}.png`.

## 결정한 기본값 (실험 후보로 기록)

사용자 방향(포트폴리오, 실험으로 찾아감)에 따라 아래는 잠정 기본값이며, 실측으로 바뀔 수 있는 가설로 문서에 남긴다.

1. 적정 거리 판정은 **캐릭터별** `bonusrange_min ≤ 거리 ≤ bonusrange_max`(양끝 포함, 잠정). 무기군 표는 참고 표시용이며 계산은 캐릭터 값을 쓴다(SR 예외 캐릭터 반영). 기존과 같이 일반 공격(normal)에만 적용한다.
2. **RL `0–0`**은 데이터 그대로 "적정 거리 보너스 없음"으로 계산·표시하고, 확인 필요 항목으로 표시한다.
3. 거리는 **정수 0–100** 또는 **미설정**. 미설정은 기존 체크 해제와 같다(전원 적정 거리 보너스 없음).
4. 약점 속성은 5속성 중 하나 또는 **없음**. 멤버 속성 = 약점 속성이면 우월 코드. 속성 상성표(누가 누구를 이기는지)는 쓰지 않는다 — 사용자가 약점을 직접 지정한다.
5. **기존 저장 조건 호환**: 이전 bool 조건(`properDistance`/`elementAdvantage`)으로 저장된 전술·실험은 조용히 재해석하지 않는다. 이전 방식("전원 적용")으로 명시 표시하고 그대로 재현 가능하게 둔다. 새로 저장하는 조건은 새 필드를 쓴다.
6. 단일 히트 검산(한 타격의 수동 입력)은 이번 범위가 아니다. 기존 체크 입력을 유지한다.

## 공통 기준

[client_f32 통합 지시서](client-f32-integration-assignments-2026-09-28.ko.md)의 "공통 기준·보존"을 그대로 따른다(본인 worktree만 편집, 일반 merge, 원본 계정·캐시·EXE·5180/5181 불변, 디컴파일·push·배포·새 워커 금지, package-lock 보존, 완료 시 Director 터미널 재확인 후 한 번 인계). 모든 담당의 기준 커밋은 Director `cd004f1`(= 원본 `main`, client_f32 배포본)이다. 먼저 자기 브랜치에 일반 merge한다.

**중요: 원본 사용자가 지금 배포본 앱을 사용 중이다.** 5180/5181과 원본 경로의 프로세스를 건드리지 않는다.

## F-COND-E — 엔진 (시뮬레이션 엔진 담당)

소유: `src/Nikke.Core/**`, `src/Nikke.Engine/**`, 엔진 tests, 보고서 `docs/boss-distance-element-engine.ko.md`.

1. 조건 계약에 `BossDistance`(int? 0–100)와 `BossWeakElement`(5속성 또는 null)를 추가한다. 멤버 입력에 적정 사거리 `[min, max]`와 속성을 받는 필드를 추가한다(값은 Backend가 채움 — 엔진은 원천을 읽지 않는다).
2. 멤버별로 `ProperDistance = normal && distance != null && min ≤ distance ≤ max`, `ElementAdvantage = weak != null && member.Element == weak`. 멤버 사거리·속성이 불명이면 추정하지 말고 명시적 오류 또는 진단으로 남긴다.
3. 이전 bool 조건 경로는 그대로 두고, 새 필드와 동시 지정은 오류로 거부한다. 규칙 버전을 올려 fingerprint·캐시가 분리되게 한다.
4. 검증: 경계(min−1/min/max/max+1), RL 0–0, SR 예외 캐릭터, 미설정, 약점 없음, 섞인 덱(멤버마다 결과 다름), 이전 bool 경로의 기존 결과 정확 재현, 팀 합 = 구성원 합.

## F-COND-B — Backend

소유: `src/Nikke.Api/**`, `src/Nikke.Contracts/**`, `src/Nikke.Data/**`, `src/Nikke.Compute/**`, `src/Nikke.Jobs/**`, `src/Nikke.Storage/**`, `tools/data-pipeline/**`, Backend tests, 보고서 `docs/boss-distance-element-backend.ko.md`.

1. 버전 고정 원천에서 캐릭터별 `bonusrange_min/max`와 속성을 카탈로그에 추가한다(원천·버전·hash 기록, 게임 파일 재수집 금지). RL 0–0과 SR 예외를 원천 그대로 둔다.
2. UI용 읽기 전용 API: 무기군별 적정 사거리 표(데이터에서 집계, 예외 캐릭터 목록 포함, 하드코딩 금지)와 덱 멤버별 사거리·속성.
3. 솔로 레이드 replay·단일 덱 compute 조건 wire에 `bossDistance`·`bossWeakElement`를 추가하고, 이전 bool 조건 저장본의 명시 호환(결정 5)을 구현한다. fingerprint에 새 조건을 포함한다.
4. 엔진 커밋을 받으면 일반 merge해 연결한다. 그 전에는 카탈로그·API·계약부터 진행한다. UI가 따를 wire를 계약 문서에 확정한다.

## F-COND-U — UI (Claude UI 담당)

소유: `apps/desktop-ui/**`, UI tests, 보고서 `docs/boss-distance-element-ui.ko.md`.

1. 솔로 레이드 "전투 조건"과 단일 덱 통계 조건에서 적정 거리·우월 코드 체크박스를 **정사각형 작은 아이콘 버튼 + 현재 값 표시**로 바꾼다(예: "적정 거리 · 35", "약점 · 불(Fire)", 미설정 표시).
2. **거리 팝업**: 0–100 정수 입력(슬라이더 + 숫자), 미설정 선택, 무기군별 적정 사거리 표(API 값), 가능하면 현재 덱 멤버 각각이 그 거리에서 적정 거리인지 표시. RL은 "보너스 없음(데이터 0–0, 확인 필요)".
3. **약점 속성 팝업**: 5속성 이미지(`code-*.png`) 중 하나 클릭으로 설정, "없음" 선택. 제목·설명에 **"보스의 약점 속성 — 이 속성 니케가 우월 코드 보너스를 받습니다"**를 명시해 니케 속성이나 보스 속성으로 오해하지 않게 한다. 덱에서 해당 속성 멤버를 표시하면 좋다.
4. 키보드·ESC 닫기, 1500/850/500px 레이아웃, 이전 방식 조건을 연 경우 "이전 방식(전원 적용)" 표시.
5. Backend wire 확정 전에는 mock으로 화면을 먼저 만들고, 확정 후 실제 격리 API로 연결한다(mock과 실제를 구분). 단일 히트 검산은 바꾸지 않는다.

## 이후

세 담당 인계 후 Director가 통합 순서를 정하고 검수 담당(Q)에 독립 수용을 배정한다. 이어서 Director 통합·원본 배포(사용자 확인 후).

## 전달 확인

지시서 커밋 `5b2059a`. 전달 직전 세 터미널 idle 확인.

| 담당 | 터미널 | 요청 ID | 착수 근거 |
|---|---|---|---|
| F-COND-E 엔진 | `term_5e3783c1…` (codex) | `7fb48184-69b2-41ea-a912-d84a161fd502` | `input_accepted`·`turn_started` |
| F-COND-B Backend | `term_e5d05982…` (codex) | `8be4fa1e-6d7a-49fd-9faf-a1134d23b401` | `input_accepted`. 화면에서 Working 확인, 재전송 없음 |
| F-COND-U UI | `term_c322a450…` (claude) | `2777e10c-ee07-433a-b412-8bbb3a6cffd3` | `input_accepted`·`turn_started` |

검수 담당에는 아직 배정하지 않았다. 착수 확인이며 구현 완료가 아니다.
