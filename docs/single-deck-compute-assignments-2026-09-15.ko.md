# 단일 덱 CPU/GPU 통계·오버로드 평가 착수

## 승인과 현재 단계

2026-09-15 사용자 승인: 리타·블랑·앨리스·누아르·모더니아 단일 덱 반복 실행 통계와 이를 이용한 OL 추천 개발 착수. 앞선 최적화 방안 전면 채택. 다른 PC에서도 CPU/GPU를 탐지하고 지원 능력과 실측에 맞게 자동 설정해야 한다.

이 문서는 구현 지시와 수용 조건이다. 구현·검수·배포 완료 보고가 아니다. 기존 Orca 터미널에 일반 작업 지시로 전달한다. 새 Run/Task/Dispatch/워커를 만들지 않는다. 담당자별 독립 구현 후 확정 커밋을 Director에 인계하며, 의존 커밋이 없으면 독립 부분까지 완료하고 미연결 범위를 명시한다.

## 공통 기준·보존

- 공통 제품 기준 a5ccba6663241e61783b509fc69098ad3c9ecef2. 각자 AGENTS.md, README, implementation-plan P06/P08/P09, p04-team-burst, damage-calibration-analysis를 읽는다. 작업공간 지침도 확인한다.
- 본인 git status/log/조상 관계를 먼저 확인한다. 깨끗한 조상 브랜치만 ff-only로 기준 반영. 분기된 자기 완료 커밋은 보존하는 일반 merge를 사용하고 겹치는 미커밋 변경은 보고한다. reset/checkout/stash로 밀어내지 않는다. Backend 5b7685f 같은 후속 문서 커밋도 보존한다.
- 본인 worktree만 편집한다. 기존 package-lock.json은 보존·커밋 제외. 원본 계정 DB/세션/캐시를 복제·초기화·동기화·수정하지 않는다. 원본 5180/5181 및 EXE·바로가기·배포 경로를 변경하거나 종료하지 않는다. 검수용 서버/결과는 자기 artifacts와 격리 포트만 사용한다. 필요한 공개 자료는 읽기 전용, 비밀·계정 데이터는 보고서에 노출하지 않는다.
- 승인된 범위 구현·테스트는 추가 기능 승인을 되묻지 않고 수행한다. 도구 승인 절차는 준수하고 전역 권한·관리자·샌드박스 설정은 변경하지 않는다. 원격 push/드라이버 자동 설치/새 워커 생성 금지.
- 엔진 규칙·단위·정수화·같은 프레임 순서·버스트 충전 및 지연을 성능 이유로 변경하지 않는다. 생산 경로 고정 시드 금지 유지. 난수 종류와 실행 상태 격리, 실패와 정상 0 구분, 모델 오차와 표본 오차 구분.
- 제품 내부에 개발 PC 경로/CPU 모델/스레드 수를 하드코딩하지 않는다. Windows 데스크톱의 다른 PC가 우선 대상이며 다른 OS 지원까지 완료 주장하지 않는다.
- 기존 실측 DEF 30925→31784 및 20억 현상은 재검증 요청하지 않는다. 이번 성능 비교는 현행 고정 DEF 정책을 명시하여 수행한다. 자동 DEF 전환/게임 영점 검증 전 결과는 모델 기반 실험이며 실전 검증 완료 추천으로 표시하지 않는다.
- 결과는 자기 역할 보고서 docs/single-deck-{engine,backend,statistics,ui,qa}.ko.md에 커밋·실행 명령·실제/합성 구분·측정치·미완료를 남긴다. 완료 시 Director 기존 터미널을 CLI로 조회하고 확정 커밋/보고서/수용 결과/의존·미완료를 한 번 전달한다. lifecycle 권한 없는 worker_done은 사용하지 않는다.

## 공통 제품 계약: B-CPU가 먼저 확정

독립 개발을 위한 최소 의미 계약이다. 구체 DTO/route는 Backend가 docs/single-deck-compute-contract.ko.md에 먼저 확정·공유하며 UI/통계는 임의로 다른 wire 규격을 만들지 않는다.

- HardwareProfile: OS/architecture, 사용 가능한 CPU 병렬도/코어 정보(불명은 null), 메모리 한도, 모든 GPU의 안정적 장치 식별자·vendor·driver·실행 backend·정밀도/메모리 능력, 탐지 실패 원인. 이름 발견과 실제 kernel 실행 가능은 별도 상태.
- ExecutionSelection: requested=auto/cpu/gpu, effective backend/device, worker 수/chunk 크기/메모리 상한, 선택 근거, 검증·벤치마크 버전, fallback 원인. 지원되지 않는 강제 gpu는 실행 전 명확한 오류; auto는 CPU fallback. CPU에서 계산해 놓고 GPU 성공으로 표시하지 않는다.
- ExperimentInput: snapshot/data/engine/rules 버전, 5인 순서/스탯/OL/택틱/조건의 fingerprint, synchro 400, duration 180초 기본, 횟수/예산, 기록 수준. 입력을 고정하고 불변 준비 객체로 만든다.
- Batch lifecycle: create/status/cancel/resume/results. queued/running/cancelling/cancelled/completed/failed를 분리, requested/valid/failed/cancelled 수와 partial 표시. runId+attempt의 명시적 중복 방지. 불완전 전투는 정상 표본이 아니다.
- RunSummary: 실행 식별·설정·backend, 팀/5인 피해·발사/명중/크리/재장전/버스트 요약 및 실행 시간. 상세 로그 기본 off; 내부 전투 이벤트 유지. 원본 데이터와 분리된 bounded queue+batch writer.
- Statistics: n/mean/sample SD/mean CI/median/P5/P95/cut success+CI, 팀 및 니케별 지표, 방식/단위/미지원 표시. 분위수와 평균 CI 혼동 금지.
- OL comparison: 원본 불변 가상 변경(캐릭터/부위/줄/옵션/수치), 기준·후보 실험 ID, 팀 평균 차이와 CI·자신/동료 및 사이클 영향. 탐색·확정 표본 분리, 통계 불명확 시 우열 미확정.

## E-CPU/GPU — 시뮬레이션 엔진 담당

소유: src/Nikke.Core/Combat/HitCalculator.cs 관련 계산 경량 경로, src/Nikke.Engine/**(GPU 커널은 src/Nikke.Engine/Gpu/**), 엔진 전용 tests 및 tools/benchmarks/engine/**, 자기 보고서. Backend/API/Storage/Analysis/UI/공용 solution은 수정하지 않는다. 기존 엔진 csproj의 필요한 GPU 의존 변경은 본인 소유이며 공식 문서/라이선스/런타임 지원 근거 기록.

1. 먼저 Release 워밍업과 기존 상세/로그 off 기준 성능·할당·GC를 측정. 프레임/타격/배열/리플렉션/정수화 후보 비교 비용을 프로파일링하고 전후 같은 조건을 보고한다.
2. 준비된 불변 입력으로 실행하는 summary 경로 구현. 정책 하나만 계산하고 audit 없이도 정상 산식/유효성 보호 유지. 효과·무기 상태 변경 시 갱신, hot path 할당 감소, 가능 시 배열/인덱스 사용. 풀링은 완전 reset·병렬 누수 테스트가 있을 때만 채택. trace off가 내부 이벤트/전투 결과를 바꾸지 않게 한다.
3. 단일 전투 순차·전투 간 병렬 계약을 Backend에 제공한다. per-run RNG 격리, 규칙 변경 없는 난수 분포 유지. 고정 seed 도입 금지. 고정 조건/경계/기존 회귀로 기준 일치, 확률 경로는 독립 표본 검증.
4. GPU는 실제 지원 가능한 backend 조사→수치 primitive/타격 경계 self-test→동일 5인 배치 kernel의 순서로 구현·실험. 수치 배열/묶음 전송/요약 회수, double/floor/round 정확성, 분기/메모리/취소 timeout 고려. float로 몰래 낮추거나 CPU를 GPU로 위장하지 않는다. 전체 전투 backend 미완료면 정확히 미완료로 보고하고 auto 선택 불가로 둔다.
5. 프레임 건너뛰기/event-driven 및 SIMD는 채택된 후속 최적화 후보로 검토하되 순서·경계 동일성 증명과 실측 이득 없이는 기본 경로로 전환하지 않는다. 실제 구현한 최적화와 보류 사유를 각각 기록.

완료 조건: CPU summary 구현·회귀·정확성/성능 전후 근거. GPU는 실제 kernel 검증 및 end-to-end 속도까지 통과한 장치만 eligible; 미보유 장치 실측은 미검증. Backend에 호출 계약을 먼저 공유하고 최종 커밋 인계.

## B-CPU — Backend·하드웨어·배치 실행 담당

소유: src/Nikke.Compute/** 신규 하드웨어 탐지/자동 설정, src/Nikke.Jobs/** 신규 배치, src/Nikke.Contracts 내 신규 compute/batch DTO 파일, src/Nikke.Data 준비 adapter와 OL 가상 변경, src/Nikke.Storage 신규 batch 저장, src/Nikke.Api 최소 연결/신규 service, 필요한 solution/project references, backend 전용 tests, docs/single-deck-compute-contract.ko.md와 자기 보고서. 엔진/GPU kernel/Analysis/UI/QA 파일 금지.

1. 최소 wire 및 Engine/Analysis 연결 계약을 먼저 커밋하고 기존 담당에게 공유한다. 자기 브랜치 분기 커밋을 보존한다.
2. CPU/GPU 탐지: Intel/AMD/NVIDIA, 다중 GPU/외장 미연결/원격 세션/권한 거부/driver 또는 runtime 부재/비정상 메모리 값 처리. GPU는 inventory→runtime capability→실제 self-test→정확성 통과→benchmark 통과 단계를 구분. probe timeout과 예외 격리, CPU fallback. 자동 드라이버 설치 없음.
3. auto 정책: 가용 CPU/메모리 한도에 따른 보수적 기본값, 짧고 취소 가능한 workload benchmark 후 동시성/chunk 선택. 예: 1/2/4/8/...은 실제 가용 수로 제한. 명목 코어 수만으로 최적 판단하지 않는다. GPU가 더 빠르거나 검증됐다고 추정하지 않는다. fingerprint(장치/driver/runtime/engine/kernel/workload/정책) 변화 시 재탐지/재평가. 튜닝 캐시는 계정과 분리하며 다른 PC로 복사된 캐시 무효화. 지속 부하에서 메모리/응답성 보호.
4. run 단위 bounded CPU 병렬 실행, 입력 준비 1회, 전투 상태 격리, bounded queue+단일 batch writer. create/status/cancel/resume/results 및 crash/restart/중복 방지. 오래된 attempt 결과가 재개 후 이중 집계되지 않도록 함. GPU 실패 batch는 폐기·원인 기록 후 새 CPU attempt로 처리, 중복 없음. 다른 수치 의미의 backend 결과 혼합 금지.
5. seed 고정 없이 실행 독립성 유지. warmup/pilot/최종 표본 구분. JSON 상세 기록을 매번 만들지 않음. 원본 스냅샷 불변 가상 OL 입력 준비와 Analysis 연결. 현재 저장 택틱/400 고정/외부 dataRoot 호환 유지.
6. API와 실제 CPU 배치를 격리 데이터로 연결. GPU provider 미완료면 capability는 unavailable/not_implemented로 정직하게 반환. 외부 PC의 사용자 계정/경로/CPU를 가정하지 않는 portable 실행 확인 명령 제공.

완료 조건: 탐지 실패 행렬·자동 재설정·취소/재개/중복·저장 복구 회귀와 실제 CPU 배치/API 근거. 자기 벤치마크는 짧게; 최종 1천/1만/5만회 전체 장치 부하 측정은 QA가 순차 수행하여 담당별 동시 부하로 측정 오염하지 않음.

## S-CPU/OL — 통계·육성 담당

소유: 신규 src/Nikke.Analysis/**와 전용 project/tests, tools/single-deck-analysis/**, 자기 보고서. 공용 solution/Contracts/Engine/API/Data/UI 수정 금지. 필요한 project 참조는 Backend에 전달.

1. 불변 RunSummary를 받는 합산 가능한 안정적 평균/표본 분산 집계, 중앙값/P5/P95(방법 명시), 평균 CI, 컷 초과확률과 CI를 구현. n=0/1, 정상 0, 실패/취소/부분 결과, 매우 큰 피해, 분포 fixture 검증. 팀 분위수를 개인 분위수 합으로 만들지 않는다.
2. pilot 1000 → 고정 N 10000 → 50000 지속 검증 계획; 평균 정밀도에 필요한 N 산출. 무제한 CI 엿보기 중단을 일반 고정-N 95% 보장으로 표시하지 않음. 탐색용 적응 표본과 독립 최종 평가를 분리. 여러 후보 비교의 선택 편향·다중 비교와 불확실성을 보고.
3. 단일 덱 OL 후보 탐색/평가 구현: 기준 스탯/장비의 실제 부위·줄 유지, 유효 옵션·수치만 생성, 현재 덱 팀 평균 피해를 첫 목적값으로 함. 적은 표본 선별→유망/불확실 후보 추가→독립 최종 표본. 동일 seed pairing 도입 금지. 전후 차이 CI는 독립 표본 설계에 맞춤.
4. 최종 후보는 전투 전체 재실행. 장탄·차지 임계점/버프 수혜 대상/동료 효과를 포함하며 고정 로그에 배율만 곱해 확정하지 않는다. 근사는 선별용이라고 표시하고 경계 주변은 정밀 평가. 무효/무효과/미지원 옵션을 추천하지 않는다.
5. 첫 완료 범위는 옵션 변경 가치 추천. 잠금·확률·모듈 비용 자료가 확인되지 않은 비용 효율/예산 정책은 숫자를 창작하지 않고 후속으로 분리. 현재 모델 기반 결과를 게임 검증 완료로 표시하지 않는다.

완료 조건: 통계 독립 fixture/큰 값 안정성/후보 선택 holdout 검증 및 실제 엔진 결과 연동 근거. 엔진/Backend 확정 전 synthetic 검증만 했다면 명시. 결과·계약을 Backend 및 Director에 인계.

## U-CPU — 기존 Claude UI 담당

소유: apps/desktop-ui/**, UI 전용 tests 및 자기 보고서. 기존 Claude 담당 터미널 사용; 이전 Gemini/다른 UI 터미널에 중복 배정하지 않는다. 사용자 모델 지정 유지, 다른 모델로 임의 대체하지 않는다.

1. 최소 단일 덱 통계 화면: 현재 덱/택틱 요약, 횟수, 실행/취소/재개, 완료 표본 수와 진행률, 평균/분포/CI, 니케별 결과. 400 고정·기존 간단 버스트 UI 유지.
2. 장치 자동 선택 기본. 탐지 CPU/GPU, 실제 사용 backend와 선택 이유/CPU fallback을 구별. 고급 영역에서 지원 범위 내 CPU/GPU 선택·자원 상한·재측정. 미지원 GPU는 사용 가능처럼 보이지 않게 한다. 장치 없음/탐지 실패/측정 중/취소/부분 결과/재시작 복구 처리.
3. OL 가상 후보 비교 결과(부위·줄·옵션·수치, 팀 개선 및 CI, 우열 미확정) 연결. 원본 장비 수정과 혼동하지 않게 한다. 비용 효율 확정 없는 모듈 추천 UI를 만들지 않는다.
4. Backend 계약 확정 전에는 독립 렌더링 fixture와 브라우저 테스트부터 수행. mock 화면 통과와 실제 API 종단 통과를 구분, 실제 연결은 확정 계약을 따른다. 기존 피해 로그·레벨400·버스트 UI 회귀 유지.

완료 조건: 실제 브라우저 상태별 검증과 실제 배치 API 연결 후 결과/오류/취소/재개 확인. EXE 배포는 Director에 인계.

## Q-CPU/GPU — 기존 검수 담당

소유: tests/single_deck_compute_qa/**, tools/benchmarks/qa/**, 자기 보고서. 제품 수정하지 않는다. 기존 Q-IMG 완료 담당 한 터미널에만 전달한다.

1. 지금 독립 수용 도구와 fixture/검사표를 준비한다. CPU topology/메모리/GPU vendor·다중 GPU·없음·driver 부재·runtime 미지원·FP64 미지원·탐지 timeout·probe 예외·stale cache·GPU 실패 후 CPU fallback을 포함. 합성 탐지는 해당 vendor 실제 검증이 아니다.
2. 엔진 전후 고정 조건/경계 정확성, 로그 on/off, 전투 상태/난수 격리, 통계 독립 기준, 취소/재개/중복/충돌 저장/partial 결과 검증. 통계 분포 비교의 사전 수용 기준을 보고서에 정한다.
3. 제품 확정 커밋 수신 후 안전한 일반 merge/ff로 자기 작업 보존하며 독립 검수. 실제 덱은 원본 스냅샷을 변경/복제하지 않는 기존 공개·허용 입력 경로로 준비하며 불가하면 이유 보고. 대량 결과 저장은 자기 artifacts/격리 dataRoot. 고정400·현재 택틱 fingerprint와 DEF 정책 명시.
4. 1천 pilot→1만 본 실행→5만 지속 실행. 기준 성능 측정은 담당자들과 순서를 맞춰 다른 benchmark가 동시에 돌지 않도록 함. run/s·할당/GC·최대 메모리·저장 크기·UI 응답 및 취소 지연, 전후 warm/cold 구분. 모든 규모 실제 미실행은 미실행으로 보고, 추정치를 실측처럼 쓰지 않음.
5. GPU는 실제 kernel/장치/수치·분포/전체시간 수용이 모두 필요. 다른 PC용 portable self-test/benchmark 결과 schema를 검증하고 미보유 외장 GPU는 미검증 유지. CPU fallback 실제 작동을 별도 수용.
6. 원본 데이터/서버/EXE 보존 증거, 제품 커밋, actual vs synthetic, 미완료 목록과 승격 가능 범위를 Director에 전달. 준비가 끝나도 제품 미수신이면 검수 통과라 하지 않는다.

## 통합·배포의 다음 담당

Director는 확정 커밋과 독립 검수 결과를 받아 통합한다. 실제 GPU 경로 미구현/미검증을 GPU 지원 완료로 축약하지 않는다. 성능 최적화·통계 수용과 게임 영점/자동 DEF 전환 수용은 별도 표시한다. 원본 main 로컬 통합, 원본 EXE/backend/UI 갱신 및 사용자 실제 경로 실행 검증은 AGENTS.md에 따른 후속 배포 단계이며 현재 착수와 혼동하지 않는다.
