# client_f32 통합 연결·독립 QA 배정 — 2026-09-28

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
