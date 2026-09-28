# client_f32 통합 연결·독립 QA 배정 — 2026-09-28

## 최신 상태 — 2026-09-28

- **Q-F32 단계 A: 합성 엔진 수용 통과, 차단 결함 0.** [Q-F32 보고서](C:/Users/user/orca/workspaces/Nikke-Simul/검수/docs/client-f32-qa.ko.md)(검수 `cdca644`), 엔진 `5ced15a` 일반 merge `adb7d05`(충돌 없음), 근거 검수 `artifacts/single-deck-qa/f32-stage-a/`(Git 제외). Director가 보고서와 커밋 범위를 확인했다: QA 커밋의 `src`·`apps`·`scripts`·`tools/data-pipeline` 변경 0. 전투·검사 재실행은 하지 않았다.
  - 독립 기준: 엔진 golden/oracle 미사용. `Fraction` 정확 유리수 → binary32 nearest-even 자체 구현과 최종 half-away. 산술·경계·예외 **326/326**(중간 6항 비트, 공격력 `long`, 정밀도 거부, NaN/Inf, overflow).
  - replay **54/54**: client 7,979히트 독립 재계산 일치, 팀 1,346,859,763 → 1,346,863,834(+4,071) 재현, 팀 = 구성원 = 히트 합, 발수·명중·풀버스트 9회 불변. 전환 전 `53b3d10^` 소스를 분리 빌드해 과거 3정책을 실행한 결과가 전환 후 명시 선택 결과와 히트별 frame·피해·누적까지 정확히 같다. 정책별 병렬 2회·취소·취소 후 prepared 재사용 통과.
  - 미판정: API/UI·v2 변환·wire·fingerprint/캐시 종단(단계 B), 실게임 정확도, 실측 18점, SW, GPU, 성능. Q-CPU-10K 보류 유지, 재개 시 기준 재고정.
- **I-UI 단계 A: 완료, Director 검토 수용.** [I-UI 보고서](C:/Users/user/orca/workspaces/Nikke-Simul/UI/docs/client-f32-ui.ko.md), UI 브랜치 `96faf5d`(Backend `f4ab2fc` 일반 merge, 충돌 0, merge 결과 `src`가 `f4ab2fc`와 동일) → `548a6b4`(화면 준비) → `30ea4f2`(보고서). 변경은 `apps/desktop-ui`·`apps/web`·UI tests·UI 문서뿐이다.
  - 준비: `hit-policy.js`(client 기본·과거 3개 비교 후보, `statDamageRatio`·`defenceRatioRate` 실험·미확정 표시, 큰 `long` number/문자열 대응), 피해 로그 client 항·카드·산식, web 후보표·실험 입력. `CLIENT_F32_WIRE.confirmed=false`라 **실제 요청·선택지는 아직 바뀌지 않는다**(기본 legacy 유지).
  - 검증은 mock·기존 회귀만: mock 단위 13/13, vitest 10/10 + tsc, mock 브라우저 12/12(1500/850/500px), 기존 damage audit 19/19·브라우저·솔로레이드·통계 통과. 실제 API 종단·Backend 빌드는 미실행(단계 B).
  - I-BE에 넘긴 결정 대기: 큰 `long` JSON 표현, schema 3 `HitRequest` 필드, v2 변환 표시, 오류 형태 — 모두 I-BE 지시 2·3항 범위.
  - 참고(후속 후보): 엔진 client audit term에 charge·element가 별도 항으로 없다(각각 `base`·최종 곱에 포함). UI는 hit 입력으로 표시한다. 실측 실험 단계에서 항별 추적이 필요하면 엔진 audit 확장을 별도 배정한다.
- **I-BE: 완료, Director 검토 수용.** [I-BE 보고서](C:/Users/user/orca/workspaces/Nikke-Simul/Backend/docs/client-f32-integration.ko.md), 확정 wire는 [compute 계약](C:/Users/user/orca/workspaces/Nikke-Simul/Backend/docs/single-deck-compute-contract.ko.md)의 I-BE schema 3 절. Backend `74ca24f`(엔진 `5ced15a` 일반 merge `f818f3b` 포함). Director가 커밋 범위를 확인했다: `f818f3b..74ca24f`에서 Core/Engine/Analysis/apps 변경 0, 변경은 Api·Contracts·Data·Backend tests·문서, audit 도구 2개의 `packages.lock.json` 보완뿐. `74ca24f`는 UI `30ea4f2`·QA `cdca644`와 충돌 없이 merge된다(`git merge-tree` 확인). 테스트 재실행은 하지 않았다.
  - wire 핵심: hit 응답 최상위 `candidates`/`selectedCandidate`(구 comparison 봉투 제거), schema 3 기본 `client_f32` + 과거 3후보(계산 불가 후보는 null + 이유), v2 요청은 원본 + `conversion` 보존하며 1/0 명시 변환, hit import와 저장 조회 GET, `rawRate10000`/`exactAmount`/`exactEffectiveAttack`/client `exactDamage`는 **출력 십진 문자열**(입력은 문자열 또는 안전 정수 number), 선택 audit 포함.
  - compute: `hitOverrides`로 두 rate·runtimeAttackBuffs·attackFlatBuffs 실험, schema·정책·summary·raw 포함 fingerprint, 구버전 batch 재개 거부, 구결과 조회 가능·통계 분리.
  - 검증(Backend 보고): 전체 Release 경고 0/오류 0, 329 tests(Backend 141, Core 147, Analysis 41). 격리 API(포트 54516) v3/v2/import/저장/네 후보/오류 6종, 5인 600프레임 batch 세 조건(client/legacy/실험값) 각 1회, fingerprint·튜닝 키 분리. 공개 레벨·호감도 24,360셀·큐브/소장품/장비에서 **소수 native 발견 0**.
- **단계 B 통지(2026-09-28):** I-UI 단계 B와 Q-F32 단계 B를 시작한다. Q-F32 단계 B는 두 부분으로 나눈다 — **B1(지금)**: Backend `74ca24f`를 merge해 API·v2 변환·wire·오류·fingerprint/캐시·구결과 혼합 금지 종단 수용. **B2(I-UI 단계 B 인계 후 Director 통지)**: UI 확정 커밋으로 브라우저·피해 로그·통계 화면 종단 수용.
  - 통지 전달: I-UI 단계 B → `term_c322a450…` 요청 `8a8cbd2b-7013-4708-b2c8-7e2cc25813ef`, Q-F32 B1 → `term_234e279b…` 요청 `21fda1d7-621f-433d-959a-027be4c2c4a3`. 둘 다 accepted=true, `input_accepted`·`turn_started`. 전달 직전 두 터미널 idle 확인. Q-F32에는 Backend의 `check_client_f32_api.py`를 판정 근거로 재사용하지 말라고 지시했다.
- **Q-F32 B1: API·이력 분리 수용 통과, 차단 결함 0.** 검수 `058b8a5`(Backend `74ca24f` 일반 merge `4a05a26`), 보고서 최신 B1 절, 근거 검수 `artifacts/single-deck-qa/f32-b1-88f22794209a/`(Git 제외). Director가 커밋 범위를 확인했다: merge 이후 `src`·`apps`·`scripts`·`tools/data-pipeline` 변경 0(QA 도구·보고서만). 재실행은 하지 않았다.
  - Backend 검사 스크립트·테스트를 실행·import·정답 재사용하지 않은 자체 검사: 실제 API **85/85**, 후속 캐시·입력 **9/9**. v3 client 150건·과거 후보 100건 독립 `Fraction` 산술, v2 원본 + `conversion`(1/0), import·저장 GET·재시작 조회, 네 후보·선택 audit, 계산 불가 후보 null + 이유, exact 문자열·큰 정수, 소수·과정밀·underflow·unsafe number·overflow 오류(오류는 저장 안 됨).
  - compute(합성 5인·400·600프레임·DEF 30925·worker 1): default·legacy·stat·defence·raw·rate·flat 각 1회 → fingerprint 7개·튜닝 키 7개 분리. 동일 조건 재요청은 검증된 캐시 재사용, 구 캐시 존재 시 새 키 miss, 변조 payload 복구 거부.
  - 구 이력: 이전 Q-LOAD-1000 합성 calibration 20행을 격리 이관(계정 DB 복제 없음) — 원본 GET 동일, resume 409 `engine_or_rules_version_changed`, 구 fingerprint RunSummary의 새 batch 쓰기 거부(0행), 새 통계 n1과 구 통계 n20 분리.
  - 미판정: B2(브라우저·UI·피해 로그/통계 화면), 실게임·실측 18점·실사용자 덱·GPU·SW·성능. Q-CPU-10K 보류 유지.
- **I-UI 단계 B: 완료, Director 검토 수용.** [I-UI 보고서](C:/Users/user/orca/workspaces/Nikke-Simul/UI/docs/client-f32-ui.ko.md) 10절. UI `ab40dd1`(Backend `74ca24f` 일반 merge, 충돌 0) → `0278286`(schema 3 wire 연결·실제 API 검증 스크립트) → `343877e`(기록). Director 확인: merge 이후 변경은 `apps/desktop-ui`·`apps/web`·UI tests·UI 문서·README뿐, 제품 `src` 변경 0. `343877e`는 QA `058b8a5`와 충돌 없이 merge된다. 재실행은 하지 않았다.
  - 연결: 솔로레이드·통계·web 기본 `client_f32`(과거 3개 비교 후보), web 요청 schema 3 + roundingPolicy + 두 rate, 수동 버프 `rawRate10000` 문자열(0.01%보다 정밀하면 브라우저에서 거부), `candidates`/`selectedCandidate` 표시, 계산 불가 후보는 0이 아닌 이유 표시, exact 문자열 우선, 선택 audit 표, v2 conversion·400 오류 한국어, 통계 화면 schema/policy/summaryVersion 카드와 409 설명, 긴 fingerprint 카드 넘침(기존 결함) 수정.
  - 실제 격리 API(UI worktree Release, 새 dataRoot·합성 계정): web client 118,985 vs 과거 79,323/79,324/79,323(`statDamageRatio` 2, `defenceRatioRate` 0.25 — Director 산술 확인 79,323 × 2 × 0.75 ≈ 118,984.5), desktop replay 로그 전 항목 `client_f32`, 타격 #946 최종 1,711,007 = 저장값, 통계 batch schema 3·`cpu-summary.2-client-f32`·n=1, 1500/850/500px 넘침 0·JS 오류 0. mock·기존 회귀 통과.
  - 미실행: EXE 빌드·배포, Backend 전체 테스트 재실행, `hitOverrides` UI 입력(이번 범위 아님), 큰 정수·계산 불가 후보의 실제 브라우저 렌더(mock 단위만).
- **Q-F32 B2 통지(2026-09-28):** UI `343877e` 기준 브라우저·UI 종단 수용 시작. 전달 `term_234e279b…` 요청 `04c61b1a-358e-4d74-903a-0483b85e8593`, accepted=true, `input_accepted`·`turn_started`. UI의 `check_client_f32_live.py`·mock을 판정 근거로 재사용하지 말고, UI가 mock으로만 본 큰 정수·계산 불가 후보 렌더를 실제 브라우저로 확인하라고 지시했다.
- **Q-F32 B2: 전체 수용 보류, UI 결함 2건.** 검수 `c1cf869`(UI `343877e` 일반 merge `74a4225`), 보고서 최신 B2 절, 근거 검수 `artifacts/single-deck-qa/f32-b2-02a9eb8a5f02/`. 자체 Chromium + 실제 격리 API 77건 중 **75 통과 / 2 실패**(UI live 검사·mock·응답 mock 재사용 없음).
  - 통과: 큰 홀수 exact `9845047699970465`와 과거 3개 계산 불가 이유의 실제 렌더, 기본·과거 정책, 두 실험 입력, raw 문자열·과정밀 거부, 400, v2(요청 쪽에서 schema 2로 보내 실제 응답 표시 — 자연 import 경로 보장은 아님), 409, replay 400·풀버스트·선택 audit·저장값 일치.
  - **B2-STAT-1**: 정상 n=1 batch의 평균·중앙값·P5·P95(53,451,919)가 있는데 `unsupportedReason=mean_ci_requires_n_at_least_2`를 지표 전체 미지원으로 처리해 값을 숨긴다. Director 확인: `apps/desktop-ui/compute-adapter.js` `describeMetricStatistics`의 `unsupported = Boolean(unsupportedReason)`.
  - **B2-STAT-2**: baseline 없는 완료 실험의 comparison 요청이 `400 baseline_required`인데 API 장애로 분류되어 "compute API 미연결"로 표시된다. Director 확인: `CONTRACT_ERROR_CODES`에 `baseline_required`가 없어 `single-deck-stats.js`의 `call()`이 `endpointStatus='unavailable'`로 둔다.
  - 두 결함 모두 `abcd5b5`(통계 화면 최초 구현)부터 있던 코드이며 client_f32 산술과 무관하다. 도입 시점의 원인 판정은 하지 않는다.
- **U-FIX-1 배정(2026-09-28):** I-UI 담당이 두 결함을 수정한다. 조건:
  1. 지표별 지원 여부를 분리한다. CI처럼 n≥2가 필요한 항목만 사유를 표시하고, 계산된 점 추정값(평균·중앙값·분위수)은 표시한다. n=1 값이 API 값과 일치, n=0은 값을 만들지 않음, n≥2에서 CI 표시를 검증한다. Analysis/Backend 계약상 `unsupportedReason`의 의미가 "지표 전체 미지원"이라면 UI에서 임의로 재해석하지 말고 근거와 함께 Director에 보고한다(Analysis·Backend 코드 수정 금지).
  2. `baseline_required` 같은 계약 응답(비교 대상 없음)을 transport 장애와 분리해 "비교 기준 없음"으로 표시하고 endpoint 상태를 바꾸지 않는다. 다른 4xx 계약 코드도 같은 기준으로 점검한다.
  3. 실제 격리 API·브라우저로 두 시나리오와 기존 회귀를 재확인하고, 확정 커밋을 Director에 한 번 인계한다. 이후 Director가 Q-F32에 B2 재수용(두 결함 + 회귀)을 통지한다.
  - 전달: `term_c322a450…` 요청 `3aa5365e-2134-4c66-8777-e3fc77639206`, accepted=true, `input_accepted`·`turn_started`. 검수 담당은 수정 통지 대기.
- **U-FIX-1: 완료, Director 검토 수용.** UI `0e83328`(`343877e` 후속 단일 커밋), 보고서 11절. 변경은 `apps/desktop-ui`(app.js·compute-adapter.js·single-deck-stats.js)·UI tests·UI 문서뿐이며 QA `c1cf869`와 충돌 없이 merge된다.
  - B2-STAT-1: 지표 필드별 지원 분리 — API가 준 평균·중앙값·P5·P95·cut은 항상 표시, 사유는 해당 범위의 null 필드만 설명(`mean_ci_requires_n_at_least_2` → sampleSd·meanCi). Director 확인: `src/Nikke.Analysis/ComputeAnalysis.cs`가 N<2에서 사유와 함께 Mean·Median·P5·P95를 채우므로 사유가 "지표 전체 미지원"을 뜻하지 않는다. 계약 충돌 없음.
  - B2-STAT-2: `api()`가 HTTP status를 오류에 부착, 4xx는 도달한 API의 계약 응답(연결 유지), 5xx·transport는 장애. `baseline_required`는 OL 섹션 "비교 기준 없음"으로 표시.
  - UI 보고 검증(실제 격리 API + Chromium): n=1 API 26,392,278 = 화면 평균·중앙값·P5·P95와 니케별 5행 일치, SD·평균 CI만 미지원 표시; 실제 400 `baseline_required`에도 연결 유지·오류 0; runs 2에서 평균 CI·SD 표시; compute route 차단 시 "미연결". 기존 회귀 통과. 한계: n=0은 실제 API로 만들 수 없어 단위 테스트만.
- **Q-F32 B2 재수용 통지(2026-09-28):** UI `0e83328` 기준으로 두 결함 재검 + B2 회귀. 전달 `term_234e279b…` 요청 `971a2fb0-fb21-4d77-a22f-955de8e90c70`, accepted=true, `input_accepted`·`turn_started`. UI live 검사·mock 재사용 금지.
- **Q-F32 B2 재수용: 최종 통과.** 검수 `1abba9b`(UI `0e83328` 일반 merge `04a3a58`), 보고서 최신 U-FIX-1 절, 근거 검수 `artifacts/single-deck-qa/f32-b2-4484abbe01df/`. Director 확인: merge 이후 제품 변경 0, `1abba9b`는 엔진 `5ced15a`·Backend `74ca24f`·UI `0e83328`을 모두 포함한다.
  - 자체 Chromium + 격리 API **91/91**: 기존 B2 77건(이전 75 + 결함 2) 전부 통과 + 신규 14. UI live 검사·mock 재사용 없음.
  - B2-STAT-1 해소: n=1 평균·중앙값·P5·P95(각 53,285,096)와 5인 값 API = 화면, SD·평균 CI만 미지원. 실제 n=2(600프레임 2회) 독립 통계 검산 — SD 5,375.43, Student CI [32,642,198.72, 32,738,791.28] 화면 일치.
  - B2-STAT-2 해소: 실제 400 `baseline_required`·`invalid_experiment_input`, 404, 409 warmup 모두 연결 유지. 로컬 HTTP 503 주입·connection refused 주입은 "미연결", 해제 후 복구.
  - 미판정: 실제 n=0 API, 모든 4xx 개별 코드, 제품 자연 5xx, 실게임·실사용자 덱·성능·배포.
- **결론: client_f32 통합 연결·독립 QA 수용 완료(B1·B2).** 통합 기준은 QA `1abba9b`(제품 전체 + QA 도구·보고서).
- **Director 통합(2026-09-28, 사용자 지시로 1단계만):** Director에 `1abba9b`를 `--no-ff` merge했다. `README.md` 내용 충돌 1건은 양쪽 서술을 합쳐 해결했다(UI의 정책 비교 설명 + Director의 공식·결정·통합 상태). 원본 `main` 로컬 통합·EXE 빌드·원본 경로 배포·실행 검증은 이 단계에서 미실행이었고, 이후 사용자 승인으로 수행했다(아래). 원본 실행 경로는 계속 `C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe`이고 이번 통합으로 바뀌지 않았다.
  - 통합 확인: merge 커밋 `6cbb2db`의 `src`·`tests`·`apps` 트리가 QA 수용 커밋 `1abba9b`와 동일하다(`git diff` 0). Director에서 locked restore → Release build(경고 0·오류 0) → test를 실행해 **329/329 통과**(Analysis 41, Sync 99, Core 147, Compute 42). SDK는 원본 저장소 `.tools/dotnet`을 읽기 전용 실행했고 CLI home·NuGet 캐시는 Director `.tools` 아래를 사용했다. UI 브라우저·API 종단은 QA B2 근거에 의존하며 Director에서 재실행하지 않았다.
- **원본 배포(2026-09-28, 사용자 승인 2~5단계): 완료.** 원본 `main` ff(`a5ccba6` → `a302931`), 기존 실행본 백업, 원본 위치 빌드, 바탕 화면 바로가기 실행·projectRoot·UI 9파일 바이트 일치·헤드리스 로드 오류 0·계정/캐시 보존 동일. 상세 [2026-09-28 원본 배포 기록](desktop-release-original-2026-09-28.ko.md).

## 승인과 근거

2026-09-28 사용자가 **통합 연결 작업과 독립 QA 수용** 착수를 승인했다. 대상은 엔진 브랜치의 H-F32 구현이다: 구현 `53b3d10`, 보고서 기록 `5ced15a`(브랜치 `시뮬레이션-엔진-담당`). 먼저 읽을 문서:

- [H-F32·H-SRC 배정과 최신 상태](hit-damage-assignments-2026-09-28.ko.md)
- [클라이언트 공식·사용자 결정·H-SRC 요약](hit-damage-client-formula.ko.md)
- 엔진 보고서 `C:/Users/user/orca/workspaces/Nikke-Simul/시뮬레이션-엔진-담당/docs/hit-damage-client-f32.ko.md` — 특히 "후속 연결·미실행·질문" 절
- H-SRC 보고서 `C:/Users/user/orca/workspaces/Nikke-Simul/Backend/docs/hit-damage-source-investigation.ko.md`

**프로젝트 방향(사용자, 2026-09-28):** 포트폴리오 목적이다. 남은 공식 세부(곱셈별 float32 저장 경계, 반올림 방식, 공격력 버프 곱의 자료형, `statDamageRatio`·`defenceRatioRate` 의미)는 클라이언트 분석에 매몰되지 않고 **실측 대조 실험으로 찾아간다.** 그 과정의 역사가 결과물이다. 따라서 과거 정책(`legacy_term_floor`·`final_round_even`·`nested_floor`)과 기각·보류 가설을 삭제하지 말고 비교 후보로 선택·재현 가능하게 유지한다. 실험·판정 근거를 보고서에 남긴다.

이 문서는 지시와 수용 조건이다. 구현·검수·배포 완료 보고가 아니다.

## 공통 기준·보존

- Director 문서는 읽기 전용. 본인 worktree만 편집한다. `git status`/`git log`로 상태를 먼저 확인하고 자기 커밋을 보존한다. 다른 브랜치 반영은 일반 merge(가능하면 ff)로 하며 reset/checkout/stash로 밀어내지 않는다. 충돌은 임의로 덮어쓰지 말고 근거와 함께 해결하거나 보고한다. 미추적 `package-lock.json`은 보존·커밋 제외.
- 원본 계정 DB·세션·캐시를 복제·초기화·동기화·수정하지 않는다. 원본 EXE·바로가기·배포 경로·5180/5181 서버를 변경·종료하지 않는다. 검증 서버·데이터는 자기 artifacts·격리 포트·격리 dataRoot만 사용한다. 계정 입력이 필요하면 기존 합성 계정·공개 입력 경로를 쓴다.
- 게임 실행 파일 디컴파일·프로세스 접근·후킹·데이터 재수집 금지. 원격 push·배포·새 Orca Run/Dispatch/하위 워커·`worker_done` 금지. 1천/1만/5만 장시간 부하 측정은 이번 범위가 아니다.
- 엔진 산술(`ClientFloatDamage`, 공격력 `long` 조립, 반올림)은 소유 담당 외에는 수정하지 않는다. 결함은 근거와 함께 Director에 보고한다.
- 합성 fixture·기존 실측 대조·실제 게임 관측을 구분해 보고한다. 테스트 통과를 실게임 정확성 수용으로 표현하지 않는다.
- 완료 시 `terminal list --worktree 'path:C:/Users/user/orca/workspaces/Nikke-Simul/Director' --json`으로 Director 터미널을 재확인한 뒤 확정 커밋·보고서 절대 경로·검증 결과·미완료를 `terminal send --terminal <handle> --text '<요약>' --enter --wait-submit 10 --json`으로 **한 번** 전달한다. 배정 시점 Director handle `term_73afed41-4bf2-4551-8ed4-01c8a64e47bc`. stale이면 재조회, 임의 셸 전송·무응답 재전송 금지.

## 진행 순서

```text
I-BE Backend 통합 (지금)        ─┐
I-UI UI 준비 A (지금)            │→ Director가 I-BE 커밋을 UI·QA에 통지
Q-F32 QA 단계 A: 엔진 수용 (지금) ┘
        ↓
I-UI 단계 B: Backend 통합 커밋 연결
Q-F32 단계 B: API·UI 종단 수용
        ↓
Director 통합 → 원본 배포 (별도 지시)
```

## I-BE — Backend 통합 연결

worktree `C:/Users/user/orca/workspaces/Nikke-Simul/Backend` (현재 `f4ab2fc`, 제품 `40078d0`). 소유: `src/Nikke.Api/**`, `src/Nikke.Contracts/**`, `src/Nikke.Data/**`, `src/Nikke.Compute/**`, `src/Nikke.Jobs/**`, `src/Nikke.Storage/**`, 필요한 solution/project 참조, Backend 전용 tests, `docs/single-deck-backend.ko.md`·compute 계약 문서·자기 보고서 `docs/client-f32-integration.ko.md`. Core/Engine/Analysis/UI/QA 파일은 수정하지 않는다(merge로 들어오는 엔진 커밋은 그대로 보존).

1. 엔진 브랜치 `5ced15a`를 일반 merge한다. 엔진 커밋 내용을 수정하지 않는다. merge 후 전체 빌드·기존 Backend 테스트로 깨지는 지점을 먼저 목록화한다.
2. **단일 히트 API(`/api/calculations/hit`, `src/Nikke.Api/Program.cs`의 `HitRequest`)**: InputSchemaVersion 3 입력(`statDamageRatio`, `defenceRatioRate` 포함)을 받는다. 기존 schema 2 요청과 저장된 schema 2 입력은 **조용히 재해석하지 않는다.** 새 두 필드를 중립값(1, 0)으로 채운 명시적 v2→v3 변환으로 처리하고, 응답·저장에 원본 schema와 변환 사실을 남긴다. v3 제약(소수 공격력·DEF·고정 부여, 1/10000보다 정밀한 공격력 비율) 위반은 절삭하지 않고 명확한 오류로 반환한다. 응답은 네 후보(`client_f32` 기본 + 과거 3개)와 선택 정책의 audit term을 포함한다.
3. **계약 문서화**: Contracts DTO와 compute 계약 문서에 schema 3, 새 입력 2개, 선택 정책 목록, `RawRate10000`/`ExactAmount` 표현, 큰 `long` 값의 JSON 전달 방식(number/문자열) 결정을 기록한다. UI가 따를 wire 규격은 Backend가 확정한다.
4. **계정 snapshot → HitContext 준비(`src/Nikke.Data`)**: 공격력 버프 비율은 원천 raw(1/10000 분자)가 있으면 `StatRateBuff.FromRaw`로 전달한다. 계정·카탈로그 값에 소수 native 스탯·DEF·고정량이 실제로 존재하는지 합성/공개 입력과 기존 코드 경로로 확인하고, 있으면 절삭하지 말고 목록과 근거를 보고한다(사용자 답변: 클라이언트는 `Attack = statAtk + Σ round(statAtk × atkBuff × buffNum)`로 정수화된 공격력을 대미지 식에 넘긴다).
5. **compute·저장 분리**: `ComputePreparation`의 fingerprint에 엔진·규칙·summary 버전과 RoundingPolicy가 이미 들어간다. `StatDamageRatio`·`DefenceRatioRate`·raw 입력이 실험 입력에 들어오면 fingerprint에도 포함한다. 이전 버전의 튜닝 캐시·batch 결과·통계가 새 결과와 섞이지 않음을 테스트로 확인한다(구 캐시 재사용 금지, 구 결과는 조회 가능하되 새 집계에 혼합 금지). 과거 정책을 명시 선택한 실험은 그 정책으로 재현 가능해야 한다.
6. 검증: Backend 전체 테스트, 격리 API 실행으로 v3 정상/v2 변환/제약 위반 오류/네 후보 응답/단일 덱 batch 1회 소규모 실행(client_f32 결과와 fingerprint 분리)을 확인한다. 합성 계정·공개 입력만 사용한다.

완료 조건: 확정 커밋, 보고서, 계약 변경 요약(UI가 따라야 할 wire 규격), 테스트·API 근거, 남은 제약을 Director에 한 번 인계. **UI·QA에 직접 전송하지 않는다.** Director가 통지한다.

## I-UI — UI 연결 (Claude UI 담당)

worktree `C:/Users/user/orca/workspaces/Nikke-Simul/UI` (현재 `abcd5b5`). 소유: `apps/desktop-ui/**`, 필요 시 `apps/web/**`(기존 웹 UI의 `src/calculation.ts` 등 후보 목록 참조), UI 전용 tests, 자기 보고서 `docs/client-f32-ui.ko.md`. 엔진/Backend/QA 파일 금지.

**단계 A (지금):**
1. Backend 현재 커밋(`f4ab2fc`, `40078d0` 포함)을 일반 merge해 자기 통계 화면 `abcd5b5`와 맞춘다. 충돌·계약 불일치를 보고서에 기록한다.
2. `apps/desktop-ui/app.js`, `damage-log-adapter.js`, `apps/web/src/calculation.ts`에서 정수화 후보 3개 고정 가정, `inputSchemaVersion` 2, B2~B5 설명이 쓰이는 곳을 목록화한다.
3. 단계 B에서 구현할 화면 변경을 준비한다: 단일 히트 검산의 후보 표시(`client_f32` 기본, 과거 3개는 "비교 후보"로 유지), 새 입력 `statDamageRatio`(기본 1)·`defenceRatioRate`(기본 0) — 둘 다 **실험·미확정 항목**임을 표시하고 추정값을 기본으로 채우지 않는다, 피해 로그의 항 설명을 client 공식(`base`·B·extra·감소·방어비율·속성)으로 갱신. 확정 wire 규격 전에는 mock fixture와 브라우저 렌더링 테스트까지만 한다. mock 통과와 실제 API 종단 통과를 구분한다.

**단계 B (Director 통지 후):** Backend 확정 커밋을 merge하고 확정 wire 규격대로 연결한다. 실제 격리 API·브라우저에서 v3 요청·네 후보 표시·새 입력·오류 메시지·피해 로그·통계 화면 회귀를 확인한다. 기존 피해 로그·레벨 400·버스트 UI 회귀를 유지한다. EXE 배포는 하지 않는다.

완료 조건: 단계별 확정 커밋, 보고서, mock/실제 API 구분 근거를 Director에 인계(단계 A 완료 시 1회, 단계 B 완료 시 1회).

## Q-F32 — 독립 QA 수용 (검수 담당)

worktree `C:/Users/user/orca/workspaces/Nikke-Simul/검수` (현재 `44cbe5d`). 소유: `tests/single_deck_compute_qa/**`, `tools/benchmarks/qa/**`, 새 QA 도구·fixture, 자기 보고서 `docs/client-f32-qa.ko.md`. 제품 코드 수정 금지 — 결함은 재현 근거와 함께 Director에 보고한다. **Q-CPU-10K(1만 회 측정)는 계속 보류**하며, 이번 전환으로 엔진 규칙이 바뀌었으므로 재개 시 기준을 새로 잡아야 한다는 점만 보고서에 기록한다.

**단계 A (지금) — 엔진 H-F32 독립 수용:**
1. 엔진 브랜치 `5ced15a`를 일반 merge한다(자기 QA 커밋 보존).
2. **엔진의 golden/oracle을 재사용하지 말고** 독립 binary32 기준(예: numpy `float32` 또는 자체 struct 구현)을 작성해 `ClientFloatDamage`·`HitCalculator.CalculateClient`의 중간값(base·B·extra·곱)과 최종 피해를 대조한다. 2^24 경계, x.5 사사오입, `max(1)`, `defenceRatioRate` 0/양수/1, `statDamageRatio` ≠ 1, NaN/Inf·long 범위 초과 탐지를 포함한다.
3. 공격력 `long` 조립: 14.5% 경계(100 → 115), 동일 비율 그룹·중첩, 서로 다른 비율, 음수 비율 사사오입, 고정 부여 후순위, checked overflow, 소수·과정밀 입력 거부를 독립 기대값으로 검사한다.
4. 과거 정책 재현: `legacy_term_floor` 등을 명시 선택하면 전환 전 결과와 **정확히 같음**을 기존 합성 replay로 확인한다(엔진 보고: 전환 후 legacy 재실행이 전환 전과 동일).
5. 기본 경로: 합성 5인 180초(DEF 30925) replay에서 client 결과의 팀 합 = 구성원 합 = 히트 합, 발수·명중·풀버스트 횟수 불변, 엔진 보고 수치(팀 1,346,859,763 → 1,346,863,834)의 독립 재현, 히트별 차이 일부를 독립 산술로 설명(예: 172687.5 → 172688). 병렬 실행·취소 회귀는 소규모로만 확인한다.
6. 판정: 통과/차단 결함/미판정 범위를 구분한다. 성능 비교는 하지 않는다.

**단계 B (Director 통지 후):** I-BE·I-UI 확정 커밋을 merge해 격리 API·브라우저로 v2 변환·v3 정상·제약 위반 오류·네 후보·fingerprint 분리(구 캐시·구 통계 혼합 금지)·피해 로그 표시를 종단 검수한다.

완료 조건: 단계별 확정 QA 커밋, 보고서, 독립 근거, 판정을 Director에 인계(단계 A 1회, 단계 B 1회).

## 이후

Q-F32 단계 B 통과 후 Director가 통합하고 원본 배포(AGENTS.md 절차)를 별도 지시한다. 실측 18점 client_f32 대조·float32 저장 경계/반올림 실험, SW 단일 타격 검사, H-SRC 후속(break/parts 분리 등)은 그 다음 별도 배정이다.

## 전달 확인

Orca runtime `a0bed151-149f-486b-a796-53848c05acdc`. 지시서 커밋 `bc25518`. 전달 직전 `terminal read`로 세 터미널이 idle 입력 대기 상태임을 확인했다.

| 담당 | 터미널 | 요청 ID | 착수 근거 |
|---|---|---|---|
| I-BE Backend | `term_e5d05982-dabd-4b09-9242-c75d3d7b6010` (codex, H-SRC 세션 계속) | `93189f10-11ca-4137-a1c8-2de9d58d2a08` | accepted=true, `input_accepted`. 영수증에는 turn_started가 없었으나 화면에서 파일 확인 명령 실행과 `Working` 상태를 확인했다. 재전송하지 않았다 |
| I-UI UI | `term_c322a450-b75e-485d-91e5-cf9ed7ec6e38` (claude) | `4305104d-652d-4420-829f-5439b9e2e742` | accepted=true, `input_accepted`·`turn_started`. 단계 A만 |
| Q-F32 검수 | `term_234e279b-927e-4118-a8fe-f90736db2e68` (codex, 기존 Q-CPU-10K 세션) | `82ffae07-97b2-4cef-8d08-b99a382661b5` | accepted=true, `input_accepted`·`turn_started`. 단계 A만 |

검수 Codex 화면에 주간 사용 한도 25% 미만 경고가 있었다. 엔진 터미널에는 보내지 않았다. 이 기록은 착수 확인이며 구현·검수 완료가 아니다.
