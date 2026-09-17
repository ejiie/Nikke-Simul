# Q-TUNE-1 후속 수정과 수용 경계

## 현재 판정: 기능상 종결

QA 확정 `606b5685c237446616efd909339c58b28508182e`의 후속 보고서와 새 artifacts의 튜닝/API/저장 summary를 Director가 읽고 대조했다. 제품40078d0/보고서d8be9d3 및 기존QA12d767e는 QA merge `59ad23c`로 보존 통합됐으며, d8be9d3 대비 QA 확정의 src/apps/scripts/tools/data-pipeline 변경은 없다. **Q-TUNE-1은 제한 후보 튜닝 기능 문제로서 수용 통과·종결한다.** 이번 수용 범위의 보고된 차단 결함은 없다. Director가 테스트를 재실행한 결과는 아니며 독립 QA 근거를 검토한 수용 결정이다.

- 독립 튜닝11/11(합성9 + 실제 공개입력 자연/11초 지연 주입2), 실제 API6/6, 저장 경계7/7 통과. Backend 자체34/API4 및 과거 판정 수를 합산하지 않는다.
- QA worktree의 `artifacts/single-deck-qa/tune-probe-14d1980b0b2e48f4b4abf0c3d84cadcf/summary.json`, `tune-api-621ea4771669/summary.json`, `tune-storage-0a3ca63006544683ab56b14262b2b1b0/storage-summary.json`에서 전 항목 passed를 확인했다. API 근거는 product40078d0, performanceAcceptance=false, sourceChanges=[]다.
- warmup timeout 후 완전 후보 실행, 부분 후보 제외/캐시 금지, fallback/취소/메모리, 캐시 변경 무효화·실패 retune, 튜닝 표본 통계 제외, 저장/재시작/resume를 수용한다. 실제 사용자 계정 덱/게임 정확도 검수가 아니라 새 합성 계정과 공개5인180초/400/고정DEF30925 입력의 기능 검수다.
- cpu-policy-3은 worker1/2 제한 탐색이다. 최적 worker·성능 순위·개선율·다른PC·단독 지속부하·1천/1만/5만은 미판정이다. 26/50초는 cooperative deadline이지 엄격한 벽시계 SLA가 아니다. 11초 주입을 자연 JIT 실패로 해석하지 않는다.

다음 단계는 단독 측정 시간과 입력/정책/자원/전원·런타임 조건을 확보한 뒤 별도 지시로 1천→1만→5만 순차 검증하는 것이다. 이번 수신 처리에서는 새 작업 배정·대량 실행·제품 병합·원본 배포·원격 업로드를 하지 않았다. 아래 인계 시점의 미완료 표현은 역사 기록이며 이 절이 Q-TUNE-1 최신 상태다.

## 확인한 결과

QA 확정 `12d767e7ad11ba22e66bd7f6b48b377ab56076ef`의 `docs/single-deck-qa.ko.md` 전체와 제품 `48c11d8:src/Nikke.Compute/ExecutionPolicy.cs`를 대조했다. CPU summary/400/5인/고정 DEF30925/저장 택틱, 소규모 실제 통계·signed OL 명시 비교·취소/재개/저장복구·CPU fallback 안전성은 QA 수용 통과다. 실제 사용자 계정 덱·대량 처리량·브라우저·GPU·자동 OL 추천·배포 수용은 아니다.

Q-TUNE-1: 실제 180초 준비 입력의 두 진단에서 전체 10초 예산이 warmup 도중 소진되어 후보 호출 0. 준비 복원 시간은 예산 밖이다. 후보별 예약 없이 worker별 2배 개수의 묶음 전체 완료만 측정으로 인정한다. 후속 API의 worker2 measured_cache 관측도 있으므로 모든 튜닝이 항상 실패한다고 일반화하지 않는다. JIT 단독 원인이나 호스트 부하 기여율은 미확정이다.

## B-TUNE-1: 기존 Backend에 수정 인계

기존 Backend worktree/터미널을 재사용한다. 새 워커/Run/Dispatch 없음. 소유는 `src/Nikke.Compute/**`, 필요한 최소 `src/Nikke.Contracts/Compute.cs` 호환 추가와 Jobs/API 연결, Backend 전용 테스트, `docs/single-deck-backend.ko.md` 및 compute 계약 문서다. Engine/Analysis/UI/독립 QA 제품·검사 파일은 수정하지 않는다. 필요한 엔진 변경은 근거와 함께 별도 보고한다.

1. 기존 제품 `48c11d8`, 보고서 `181b0a5` 및 자기 변경을 보존한다. QA `12d767e` 보고서를 읽고 소유 Probe를 참고하여 새 자기 artifacts에서 실패를 재현한다. QA 산출물을 변경하거나 과거 실패 기록을 지우지 않는다.
2. 입력 준비·warmup·후보 측정의 시간 예산/취소 의미를 명시하고 분리한다. 각 단계의 벽시계·완료/중단 표본 수, 시도한 worker 수, 소진 사유, 캐시 출처를 관측 가능하게 한다. 전체 상한·메모리 보호·외부 취소를 유지하며 느린 PC에서 무제한 튜닝하지 않는다.
3. 대표 workload와 자원 한도에 맞는 제한적 측정 정책을 구현한다. 일부 후보만 측정했으면 탐색 범위를 표시하고, 하나도 측정하지 못하면 not_measured+안전 fallback을 유지한다. 불완전 전투나 서로 다른 관측 길이의 raw 완료 수를 공정한 처리량 비교로 사용하지 않는다. warmup/pilot은 정상 통계 표본에서 제외한다. 단순 예산 숫자 증가만으로 수정 수용을 주장하지 않는다.
4. 튜닝 정책 버전/캐시를 갱신한다. 구 정책/불완전 측정/변경된 장치·driver·runtime·engine·입력·자원 한도의 캐시를 무효화하고 정상 새 캐시만 재사용한다. 사용자에게 미측정/부분측정/측정 완료/캐시 사용을 구별하여 반환한다.
5. 느린 warmup, 느린 후보, 일부 후보 완료 후 timeout, 외부 취소, 제한 메모리, cache 오염/구버전/입력 변경을 단위 검증한다. 실제 동일 공개 5인180초 입력에서 완료된 후보 표본으로 선택 및 재조회 캐시 사용을 입증한다. 타 담당 benchmark와 겹치지 않음을 확인하고, 독점 확인 불가 시 성능 순위 수용 대신 기능 근거만 남긴다.
6. 계정 DB/세션 복제·수정, 원본 캐시/EXE/5180·5181 접근/종료, 타 worktree 편집, 배포/push 금지. 자기 격리 합성 계정+공개 입력만 사용하고 원본 공개 파일 hash를 보존한다. package-lock 보존. 이번 작업에 1천/1만/5만 장시간 부하나 GPU/holdout 새 구현을 섞지 않는다.

완료 인계는 확정 제품 커밋·보고서·실제/합성 구분·재현/수정/회귀 근거·단계별 실측·아직 미수용인 항목을 기존 Director 터미널에 한 번 전달한다. 독립 QA 재수용은 별도이며 Backend가 자체 테스트만으로 Q-TUNE-1 종결을 선언하지 않는다.

전달 확인: Orca runtime `0baeeac8-72a2-40f0-aabd-9882916a8a93`, 기존 worktree `07c470de-0a43-4d90-9eb6-240a5de9258c::C:/Users/user/orca/workspaces/Nikke-Simul/Backend`, handle `term_6c0c321c-15a9-4f93-8784-5a88b484ee45`. 요청 `fa17a1da-8546-4882-8aa2-78fcafc9b75b`는 accepted=true/input_accepted/turn_started. 담당자가 새 지시서·QA 확인 및 재현 후 수정 착수를 응답했다. 수정 완료·독립 재검수 통과는 아직 아니다.

## Q-TUNE-1 독립 재검수 인계

Backend 제품 `40078d06a3d236ec7de5987d6be3c96d2a34ec86`, 보고서 `d8be9d3490cc95c4d389247eb4007c3c7de69441`를 수신했다. Director가 보고서와 ExecutionPolicy/TuningBudget을 읽었다. cpu-policy-3은 준비 별도, warmup2초/후보별24초, worker1/2 각각 완전전투2회, 전체26/50초 cooperative deadline이다. 자연 구정책 진단은 성공했고 11초 warmup 지연 주입에서만 이전 실패를 통제 재현했다. Backend 자체34회귀/API4검사 통과 보고는 독립 QA 수용과 구분한다. 제한 후보 선택·캐시 기능 근거이며 최적 worker/성능 순위 근거가 아니다.

기존 검수 worktree/터미널에 다음 후속을 맡긴다. 제품 수정이나 대량 부하가 아니라 독립 소규모 재수용이다.

1. 자기 QA `12d767e`와 기존 변경을 보존하고 제품40078d0 및 보고서d8be9d3을 일반 merge로 통합한다. 충돌 시 임의 덮어쓰기 없이 보고한다. 자기 QA 파일·새 artifacts·보고서만 소유하며 제품 수정은 Backend에 결함 인계한다.
2. 이전 QA 실패를 보존한다. 기존 Q-TUNE-1 재현/수용 조건과 새 계약을 대조하고 Backend 테스트 통과를 독립 판정으로 대신하지 않는다. 자연 실행과 지연 주입 재현을 구분한다.
3. 같은 공개5인180초/400/DEF30925 입력으로 준비·warmup·후보별 완료/중단/시간/원인과 cache 출처를 독립 대조한다. warmup timeout 후 후보 예약, 동일 완전전투2회 처리량, worker1/2 제한 범위 표시, 전체 cooperative deadline 및 중단 후 작업 중첩 여부를 확인한다. 성능 순위·최적성 수용은 하지 않는다.
4. 느린 후보/일부 완료/외부 취소/메모리 보호에서 불완전 후보 제외, 유효 후보만 선택, 부분 집합 캐시 금지, 0후보 not_measured fallback을 검사한다. 구버전·오염·입력/엔진/규칙/하드웨어·자원 변경 무효화와 실패한 retune 이후 구 캐시 부활 금지를 확인한다.
5. 실제 격리 API에서 단계 관측, warmup 취소 valid0, 정상 결과 통계에서 튜닝 제외, measured_cache 재조회 Run0 및 저장/재시작 호환을 대조한다. 필요한 기존 소규모 회귀를 실행하되 합성/실제/재실행 개수를 구분한다.
6. 새 합성 계정 및 허용 공개 입력만 사용한다. 원본 계정DB/세션/캐시/EXE/5180/5181·타worktree·package-lock 보존. 자기 서버만 정리한다. 1천/1만/5만, GPU/OL 새 구현, 배포/push, 새worker/Run/Dispatch/lifecycle는 이번 지시에서 제외한다.
7. 확정 QA 커밋·보고서·독립 근거·통과/차단결함/미판정 범위를 기존 Director에 한 번 인계한다. 기능상 Q-TUNE-1 종결 여부와 지속 부하/단독 성능 측정 미수용을 별도로 판정한다.

전달 확인: 기존 worktree `07c470de-0a43-4d90-9eb6-240a5de9258c::C:/Users/user/orca/workspaces/Nikke-Simul/검수`, handle `term_30f7a75f-412b-4f2f-9bd3-863c417a5e7e`, runtime `0baeeac8-72a2-40f0-aabd-9882916a8a93`를 재확인했다. 요청 `e7a5fef0-d63a-4277-996f-da7540de46cd`는 accepted=true/input_accepted/turn_started다. 독립 재검수 착수이며 완료·수용 통과·Director 제품 통합 또는 배포를 의미하지 않는다.

## 이후 순서와 사용자 원격 업로드 지시

튜닝 수정 확정 → QA 재수용 → 단독 측정 조건·입력 고정 후 1천/1만/5만 순차 검증. UI 및 자동 OL 최종 평가 연결, 실제 GPU 전투 backend는 각 기존 담당 범위에서 미완료로 유지한다. 현재 Director에는 제품 커밋을 병합/배포하지 않았다.

2026-09-16 사용자는 현재 작업 종료 후 **새 GitHub 비공개 저장소 생성 및 코드 업로드**를 명시 승인했다. 이전 push 미승인 상태를 이 목적·시점·새 비공개 저장소 범위에서만 갱신한다. 지금 원격 생성/push를 시작하는 지시는 아니다. 완료 시 통합 소스·테스트·문서를 대상으로 비밀정보 및 업로드할 Git 이력까지 점검하고 계정 DB/토큰/세션/캐시/빌드 산출물을 제외한다. 기존 원격을 임의로 바꾸거나 공개 저장소에 올리지 않는다. 생성 후 실제 visibility=private와 업로드 커밋을 확인하고 사용자에게 URL을 보고한다. 인증 불가/민감 이력 충돌은 업로드 전에 보고한다.
