# 보스 거리·약점 속성 조건 — F-COND-1 배정 (2026-09-28)

## 최신 상태

- **사용자 확인(2026-09-29): 사거리 데이터(무기군·캐릭터별 `bonusrange_min/max`, 하란 #5042 SR 25–45 예외, RL 0–0 = 적정 거리 보너스 없음)는 이미 검증된 내용이다.** 아래 기록의 "잠정·확인 필요·실게임 가설" 중 사거리 **데이터 값과 RL 0–0 해석**에 해당하는 부분은 이 확인으로 해소됐다(당시 기록은 역사로 보존). 경계값 **양끝 포함**(`min ≤ 거리 ≤ max`) 규칙은 이번 확인 범위가 명시되지 않아 확인 대기로 둔다. 앱 화면 문구("확인 필요"·"잠정")와 API `gameVerified=false`는 아직 코드에 남아 있다.
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
- **F-COND-Q 단계 1: 정상 경로 통과, 전체 수용 보류(결함 1건).** 검수 `53d183d`(Backend `796eec3` merge), [QA 보고서](C:/Users/user/orca/workspaces/Nikke-Simul/검수/docs/boss-distance-element-qa.ko.md), 근거 검수 `artifacts/single-deck-qa/conditions-cc81af4fb37e/`. 자체 검사 83/83 + 추가 11/12 = **94/95**(Backend·엔진 검사·정답 미사용).
  - 통과: 공개 192명 독립 집계·프로필·6무기군·SR 예외·RL 일치, 실제 5인 API 경계 18조건, 별도 resolver 1,253사례, 실제 2,087히트(비normal 614) 독립 Fraction/binary32 산술·멤버별 flag 일치, 구 bool replay·batch 정확 재현(이전 QA API DLL 직접 실행과 대조)·구 GET/export/hash 불변·compatibility·구 resume 409, 조건 5종 fingerprint·튜닝 키·통계 분리, 속성 OL 후보 멤버별 판정.
  - **F-COND-Q-1(Backend):** 격리 runtime에서 `combatProfiles.characters.5004.bonusRangeMin`만 제거하면 프로필 GET이 200으로 앨리스 SR을 min 0/max 100으로 내고, 거리 35·Fire replay도 200으로 저장된다(원천은 45–100). Director 확인: `src/Nikke.Contracts/CombatConditions.cs`의 `int BonusRangeMin`(non-nullable) 역직렬화가 누락을 0으로 채우고 `CombatProfileCatalog` 범위 검사를 통과해, 엔진의 불명 검사에 도달하지 못한다. max·element 누락은 500 빈 응답, 멤버 전체 누락은 400. 정상 prepare 산출물에는 누락이 없으므로 **비정상 runtime 방어 경로 결함**이며 실제 배포 손상은 아니다.
- **B-FIX-2 배정(2026-09-28, F-COND-B 담당):** 필수 키·타입 누락을 보존해(0 채움 금지) 조회·replay·compute 모두 계산·저장 전에 명시적 400/409 진단을 반환한다. 500 빈 응답도 같은 진단으로 바꾼다. 유효한 min 0(SG·RL)·RL 0–0·SR 예외·구 bool 회귀를 유지한다. wire(오류 코드·필드)가 바뀌면 인계에 명시한다. 이후 QA가 이 결함과 회귀를 재수용한다. 전달 `term_e5d05982…` 요청 `5d8caf26-1230-46bf-946e-c0c7ec136f1c`, accepted=true·`input_accepted`(재전송 없음).
- **F-COND-U 단계 B: 완료, Director 검토 수용.** UI `e3dc7b8`(Backend `796eec3` merge, 충돌 0) → `09e27cb`(확정 wire 연결·실제 검증), 보고서 6절. 변경은 `apps/desktop-ui`·UI tests·UI 문서뿐(제품 `src` 0). QA 소유 `tests/q3/check_ui_contract.mjs`는 수정하지 않았다.
  - 연결: 옛 체크박스 제거, replay·통계 요청에 `bossDistance`/`bossWeakElement` 항상 전송(미설정은 명시 null, 옛 bool 미전송), 무기군 표·멤버 미리보기는 확정 API, `conditionCompatibility` label 표시, 통계 카드 저장 모드 표시.
  - 발견·수정: mock 단계 `cc24bc9`부터 QA 계약 검사 `tests/q3/check_ui_contract.mjs`가 23/26 실패(submit 콜백이 모듈 헬퍼 호출) → 앱 코드의 콜백을 자기완결로 고쳐 26/26. 실제 데이터 sha 문구 팝업 잘림 → 줄바꿈.
  - UI 보고 실제 격리 API + Chromium: 격리 runtime에만 `prepare_combat_conditions.py` 실행(원본 `data/local` 미실행), 표·멤버 판정 API 일치, 거리 35·Fire replay에서 앨리스 평타 12발 모두 properDistance=false·elementAdvantage=true(기대 일치), 모두 미설정 null → per_member, 이전 방식 legacy_global 라벨, 통계 batch per_member·`cpu-summary.3-boss-conditions`, 혼용 400, 1500/850/500 넘침 0·JS 오류 0. 기존 회귀 통과.
  - 미실행: EXE 배포, 실제 409 `combat_profile_catalog_missing` 화면(mock 단위만), RL 멤버 포함 덱(표로만 확인).
- **F-COND-Q 단계 2 통지는 B-FIX-2 인계 후 재수용과 묶어 한 번에 보낸다**(오류 진단 wire가 바뀔 수 있고 검수 세션 사용 한도가 낮음).
- **B-FIX-2: 완료, Director 검토 수용.** Backend `97ba7bf`(`796eec3` 위), 보고서 마지막 B-FIX-2 절. Director 확인: Core/Engine/Analysis/apps 변경 0, UI `09e27cb`·QA `53d183d`와 충돌 없이 merge된다.
  - 수정: DTO 생성 전 필수 키·타입·범위 검사, 스탯·전투 계산 전 catalog 검증. **확정 오류 wire: HTTP 409 `{code: combat_profile_invalid, message, characterId, field, reason}`**(reason: missing/null/wrong_type/out_of_range/unsupported_value/id_mismatch/weapon_mismatch/hash_mismatch). 두 combat-conditions GET, skill/weapon replay POST, compute POST 공통. 멤버 전체 누락 400·구 catalog 자료 없음 409는 유지, 성공 wire·fingerprint 불변.
  - Backend 보고 검증: .NET 408/408, 잘못된 runtime 21종 × API 5개 = 105/105 모두 409, 실패 시 replay/compute 파일 불변·실험 0건. 정상 회귀(SG·RL min 0, RL 0–0, SR 예외, 구 bool replay 1,586,529·compute 1,847,281, 새 모드 결과·OL 후보) 유지.
- **U-FIX-2 배정(2026-09-29, F-COND-U 담당):** UI에 `combat_profile_invalid`·`combat_profile_catalog_missing` 전용 표시가 없어 서버 원문 메시지만 노출된다(Director 확인: `apps/desktop-ui`에 해당 코드 매핑 없음). Backend `97ba7bf`를 merge하고 두 팝업·검산 결과·통계 화면에서 한국어 진단(어느 캐릭터·필드·사유, 데이터 준비 필요 안내)을 표시하며, 연결 장애로 분류하지 않는다. 격리 runtime을 일부러 손상시켜 실제 브라우저로 확인한다. 전달 `term_c322a450…` 요청 `8321e00b-a9af-4c17-a1a1-e136e49b764f`, accepted=true·`input_accepted`·`turn_started`.
- **U-FIX-2: 완료, Director 검토 수용.** UI `1a40692`(Backend `97ba7bf` merge, 충돌 0) → `77264bf`, 보고서 7절. 변경은 `apps/desktop-ui`·UI tests·UI 문서뿐(제품 `src`·QA `tests/q3` 0). `77264bf`는 엔진 `f374c1d`·Backend `97ba7bf`·`cd004f1`을 모두 포함하고 QA `53d183d`와 충돌 없이 merge된다.
  - 변경: `api()`가 오류 본문(code·details) 보존, `combat_profile_invalid`(캐릭터 이름/ID·필드·reason 8종 한국어)·`combat_profile_catalog_missing`·`combat_member_profile_missing`을 한국어 진단 + `prepare_combat_conditions.py` 준비 안내 + 서버 원문으로 거리·약점 팝업·솔로레이드 결과·통계 오류 목록에 표시. 409/400은 도달 응답이라 연결 상태 유지.
  - 추가 발견·수정: `09e27cb`부터 있던 팝업 포커스/close 경쟁(빠른 키보드 재열기 시 버튼 포커스 누락·새 팝업 내용 삭제). mock 브라우저 간헐 실패로 드러났고 동기 포커스 복귀·재열림 시 close 무시로 고쳐 5/5.
  - UI 보고 실제 격리 API + Chromium: 사례마다 새 dataRoot에 prepare 후 격리 runtime만 손상(5004 `bonusRangeMin` 삭제, 5011 element null, 미준비) → 실제 409와 네 화면의 기대 진단, 연결 정상, 넘침 0·JS 오류 0. 기존 회귀 통과. 한계: `combat_member_profile_missing` 400은 단위만, EXE 배포 없음.
- **F-COND-Q 재수용 + 단계 2 통지(2026-09-29):** UI `77264bf` 기준으로 B-FIX-2 재수용(API)과 브라우저 단계 2를 한 번에 요청한다. 전달 `term_234e279b…` 요청 `4bb3c6ad-05a2-4ef3-a516-ccbc19e04585`, accepted=true·`input_accepted`·`turn_started`.
- **F-COND-Q 최종: 통과.** 검수 `d71c7a2`(UI `77264bf` 일반 merge `a0f16d2`), QA 보고서 최신 2026-09-29 절, 근거 검수 `artifacts/single-deck-qa/conditions-14a3ee04039a`(API 83)·`conditions-browser-954724d9ce7f`(브라우저 141)·`f32-b2-b01862749de6`(기존 91). Director 확인: merge 이후 제품 변경 0.
  - 자체 검사 **315/315**(정상 API 83 + B-FIX-2·실제 Chromium 141 + 기존 client_f32·통계 91), 별도 Q3 계약 harness 26/26. 담당 검사·mock·정답 재사용 없음.
  - F-COND-Q-1 해소: 필드 누락·null·잘못된 타입·범위·미지원 속성·ID 불일치 16종 × 두 GET·replay·compute = 64응답 모두 409 `combat_profile_invalid`, characterId/field/reason 정확, 0 채움·500 없음, 실패 시 파일·실험 불변. 정상 SG/RL min 0·SR 예외·구 bool 정확 재현 유지.
  - 브라우저: 32px 아이콘·두 팝업·약점 경고·5속성 이미지·멤버 미리보기, 새/null 요청에 구 bool 없음, 저장 모드·구 bool 표시, replay·통계 값, 손상 데이터 한국어 진단 4화면·연결 유지, 키보드/ESC/포커스 복귀, 1500/850/500 통과. QA 예비 실행의 팝업 멈춤은 QA 선택자 오류로 확인되어 제품 결함으로 세지 않았다.
  - 미판정(QA 시점): 실게임 가설(양끝 포함·RL 0–0 — 이후 사거리 데이터·RL 0–0은 사용자 검증 완료, 양끝 포함은 확인 대기), 실사용자 덱, 성능, RL 멤버 전체 전투 UI, reason 8종 전체 문구, weapon replay 손상 endpoint. Q-CPU-10K 보류.
- **Director 통합(2026-09-29): 완료.** QA `d71c7a2`를 `--no-ff` merge(`52ff31f`, 충돌 없음, `src`·`tests`·`apps`·`tools` 트리가 `d71c7a2`와 동일). Director에서 locked restore → Release build(경고 0·오류 0) → test **408/408**(Analysis 41, Core 174, Sync 148, Compute 45). 원본 배포는 사용자 확인 후 별도 — 배포 시 원본 `data/local/runtime`에 `prepare_combat_conditions.py` 실행이 필요하다(기존 runtime 보존, 새 runtime 추가).
- **원본 배포(2026-09-29, 사용자 승인): 완료.** 원본 `main` ff(`cd004f1` → `4b4403e`), 원본 runtime 준비(새 `9c98c91c…`, 기존 보존, `current.json` 백업), 실행본 백업·빌드, 바로가기 실행·UI 10파일 바이트 일치·새 API 실데이터·두 팝업 표시·계정/캐시 보존 동일. 상세 [2026-09-29 원본 배포 기록](desktop-release-original-2026-09-29.ko.md).

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

1. 적정 거리 판정은 **캐릭터별** `bonusrange_min ≤ 거리 ≤ bonusrange_max`(양끝 포함, 잠정 — 사거리 값 자체는 2026-09-29 사용자 검증 완료, 양끝 포함은 확인 대기). 무기군 표는 참고 표시용이며 계산은 캐릭터 값을 쓴다(SR 예외 캐릭터 반영). 기존과 같이 일반 공격(normal)에만 적용한다.
2. **RL `0–0`**은 데이터 그대로 "적정 거리 보너스 없음"으로 계산·표시하고, 확인 필요 항목으로 표시한다. → 2026-09-29 사용자 검증 완료(보너스 없음 해석 확정).
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
