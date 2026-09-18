# Q-CPU-10K — calibration 완료, 본3만회 미시작 (2026-09-18)

**판정: worker4/8/15 각128회 calibration 및 전체 독립 검산 통과. 본4→8→15 각10000회는 시간·배터리 admission 모두 불충족하여 시작하지 않았다.** 본 완료n은 각각0/0/0, 본 wall/통계는 null이다. calibration을1만회 결과나 순위 수용으로 승격하지 않는다.

## 기준·입력·준비

Director `cpu-worker-10000-2026-09-18.ko.md` 전체, 기존 cpu-worker-scaling 보고서/실행기를 읽었다. QA **8871f3860c1d97411a8beba610e933584016654c**, 제품 **40078d06a3d236ec7de5987d6be3c96d2a34ec86**와 기존 이력을 보존했다. 현재 창은 **11:05~11:40 KST**, 자동 연장 없음. 최초 확인11:06:19에는 배터리57%였고 준비 후 calibration 시작은55%였다. 지시 전58%와 구별한다.

기존 `ScaleProbe`/supervisor에 명시적 **cpu-10k 모드**를 추가했다. 기존 scale 모드의 날짜/계획 및 과거 artifacts는 보존한다. 새 mode는 calibration4/8/15각128, 본순서4→8→15각10000 연속, 본직전64warmup, phase=pilot, 고정cut855466067을 새 preregistration에 기록한다. C#은 calibration·counter·취소 smoke 후 admission 파일을 기다리고, allowed=false이면 본warmup/본실험 없이 종료한다. 결정 파일 전달은 QA에서 atomic replace로 보완했다. 이는 실제 거절 실행 이후의 안전한 파일 전달 보완이며 calibration을 재실행한 것이 아니다.

제품 소스/자동Policy1/2/API/SQLite/캐시는 바꾸지 않았다. 기존 수용 Data/Engine/Core/Contracts/Analysis DLL5개를 읽기 전용 Reference로 고정하고 SHA 전후 대조했다. Release 경고0/오류0,2.30초. 빌드 근거 `artifacts/single-deck-qa/tenk-build-80534b7f46da4c66b1b8b6fbd7c72f25/build.log`.

입력은 이전 자기 artifact의 **합성 계정** prepared다. 실제 사용자 계정이 아니다. 리타/블랑/앨리스/누아르/모더니아,400/skills10,돌파·코어·호감도·콘솔0,큐브·소장품없음,대부분 장비미착용/앨리스머리T10 강화0 공격OL4.77%1줄.180초/DEF30925/core true/crit sample 및 저장 합성 택틱을 그대로 사용했다. 원본 계정/스냅샷을 복제하거나 실제 사용자 덱에 맞춰 조정하지 않았다.

입력파일 SHA **0ddbc609da1378afd9df49fc1826165dd2e0ed675e3ebdf41086da538a63db5e**, 물리 fingerprint **f9cfbd31c4e250690a804b7fac2a7f1ab71d30c3c9bb0324fab74b2c1c57a70e**, engine cpu-summary.1. data/rules/snapshot/tactic 버전·SHA는 preparation/source-fixed-fingerprints에 있다. Restore1회 **120.256ms**, 전투별 상태/RNG는 제품 경로 그대로다. 고정seed·SIMD·프레임skip·전투규칙 변경 없음.

가용논리CPU16에서 요청15는 CPU-1 한도15 이내다. 사전 메모리4,179,603,456 bytes는15×64MiB=1,006,632,960 bytes 예약 이상이다.15를 축소해 표시하지 않았고 실제 maxActive15를 calibration에서 관측했다. 이는15가 최적 worker라는 뜻이 아니다.

## calibration 실제 결과 (본1만회 결과 아님)

프로세스PID17168, **11:10:32.603~11:10:50.981 KST**, 배터리55%→55%, Offline/SAMSUNG MODE/batterySaver0. 상태 `calibration_only_admission_denied`, C# `admission_denied`, blocks=[], activeAfter0, 종료코드0. 종료 후 자기 PID가 없음을 확인했다.

| worker | calibration n / 실제 maxActive | 실측 wall | CPU초 | 본10000 선형 예상, 실측 아님 | 본 완료n |
|---|---|---:|---:|---:|---:|
| 4 | 128 / 4 | **4.796407초** | 17.750 | 374.719초 | **0** |
| 8 | 128 / 8 | **6.693050초** | 37.547 | 522.895초 | **0** |
| 15 | 128 / 15 | **4.302736초** | 29.063 | 336.151초 | **0** |

세 calibration 모두 정상128, 실패0/취소0/정상피해0 표본0. index0..127/중복누락0/5인 순서/팀=5인/독립 비음수카운터/phase·fingerprint를 검산하고384개 전 결과를 보존했다. Hits와 CriticalHits의 대소 제약은 추가하지 않았다. 음수Hits validator 검사 통과. 별도20ms cancellation smoke는 요청32, 정상0/중단호출2/미완료32/실패0, 실측22.192ms, 종료활성0이었다. 취소 표본을 피해0으로 저장하지 않았다.

## 본 측정 admission — 두 조건 불충족

**11:10:49.696 KST**에3후보 실제128회 시간으로 계산했다.15의 시간은 이전2/4/8에서 외삽하지 않았다. 계산과 판정은 `admission.json`에 본측정 이전 저장했다.

- 본30000 예상합계1233.765초, 직전warmup64×3의 예상7.896초를 포함한 합계 **1241.661초(20분41.66초)**.
- 지시된 시간1.5배+180초 적용: **2042.492초(34분2.49초)**. 당시 창 잔여 **1750.303초(29분10.30초)**. 예상종료11:44:52로11:40 초과, timeAccepted=false.
- 현재 calibration 정수 배터리55→55지만 소모0으로 가정하지 않았다. max(현재 관측률0, 기존5%p/284.6초)의 **0.0175685%p/초 ≈1.0541%p/분**를 적용했다.
- 보수 시간 동안의 예상감소35.884%p, 종료예상 **19.116%**로 요구35% 미만, batteryAccepted=false. 여유를 뺀 단순1241.661초만 적용해도 약33.19%로35% 미만이다.

`allowed=false`로 본직전warmup64×3 및 본3만회를 전혀 시작하지 않았다. 횟수를 줄여 일부를 몰래 실행하거나 유리한 calibration을 다시 뽑지 않았다.30% 보호하한을 낮추거나AC로 전환하지 않았다. **완료n=calibration384, 본0/30000**이다.

이번 추정에 따른 필요 조건은 **본 시작 시 배터리 최소약71%(계산70.884%) 및 남은 실행구간 최소34분3초**이며 준비/calibration 시간은 별도 확보해야 한다. 이는 현재 짧은 측정의 계획값이라 충전 이후 새 구간에서도 재확인이 필요하다. 다른 전원 조건을 선택하려면 해당 조건의 새 승인/별도 calibration이 필요하며 이번 결과를AC 성능으로 바꾸지 않는다.

## calibration 통계와 미수용 통계

아래는 **각 n128인 calibration 팀 통계**다. 본 n10000 통계는 존재하지 않는다. 팀·5인 전체 평균/표본SD/중앙값/P5/P95/Student 평균95%CI를 독립 Fraction/HF7/수치적분으로 검산했다. 고정cut855466067은 이전 calibration 기준이며 실게임 목표 피해가 아니다.

| worker | 평균 | 표본SD | 중앙값 | P5 / P95 | 관측 최소 / 최대 |
|---|---:|---:|---:|---|---|
| 4 | 855,846,061.664 | 4,215,296.340 | 855,587,413 | 849,041,346.45 / 863,059,184.50 | 844,988,352 / 866,932,090 |
| 8 | 855,488,319.203 | 4,435,736.286 | 855,263,464 | 848,212,074.85 / 863,253,323.90 | 846,222,066 / 872,001,214 |
| 15 | 855,621,227.219 | 4,505,489.155 | 855,711,423.5 | 848,556,931.45 / 862,065,309.45 | 841,677,975 / 867,348,019 |

| worker | 평균 Student95% CI | strict damage > cut | Wilson95% CI |
|---|---|---|---|
| 4 | [855,108,786.990, 856,583,336.338] | 64/128=50.000% | [41.4652%,58.5348%] |
| 8 | [854,712,488.571, 856,264,149.835] | 63/128=49.21875% | [40.7077%,57.7753%] |
| 15 | [854,833,196.490, 856,409,257.948] | 66/128=51.5625% | [42.9862%,60.0477%] |

5인 전체 통계/극값/고정컷·Wilson은 `calibration-w{4,8,15}-independent-audit.json` 및 final-audit에 보존했다. 제품 DTO는 개인컷을 제공하지 않아 **개인 고정컷·Wilson/극값은 QA 관측 필드**에 별도 기록했으며 제품 규격을 확장하지 않았다. 분위수/SD CI는 구현되지 않아 null+사유로 표시한다. 최소·최대는 관측극값이며 미래 범위가 아니다. 평균CI로 SD/분위수의 신뢰도를 대신하지 않는다.

calibration은 후보별 성능1회이며 본측정도 계획상1회뿐이다.128개 피해 표본을128개 성능 benchmark 반복으로 세지 않는다. 이전 API61.975초 또는 별도 배터리 구간1000회와 직접 속도를 비교하지 않는다. 안정 순위/반복분산/사전bounds·margins 없는 분포동등성/자동OL추천/게임정확도/AC·다른PC/전역최적성은 모두 미판정이다.

## 관측·보존·인계

시작/종료 Orca Backend/엔진/통계/UI terminal0, 별도 계산 부하 관측0. 짧은 calibration 중 telemetry4회, 최대간격5.109초, 시스템CPU최대56.24%/외부CPU최대23.62%, 가용물리최소7,406,006,272 bytes, 디스크여유최소52,703,219,712 bytes. 보호프로세스190~192개는 개별 조회불가로 전체CPU 관측을 함께 사용했다. 온도/GC/할당량/UI는 null+미수집 사유. 이 짧은 결과로1만 지속부하 메모리/전원 안정성을 수용하지 않는다.

원본 계정DB/세션/캐시/EXE/5180/5181 접근·갱신·종료 없음. 타worktree는 지시서 읽기 외 편집하지 않았다. 자기 이전 prepared만 읽고 원본 공개자료도 다시 수집하지 않았다. package-lock SHA `2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767`, 입력 및 수용DLL5개 전후 동일. 제품 source diff0. 본작업 종료 후 자기프로세스0. 같은 worktree의 다른 모델선택 터미널에 작업을 보내지 않았다. GPU/추가OL/SIMD/프레임skip/5만/worker16/제품정책·배포push/새worker·Run·Dispatch·lifecycle 없음.

근거: **`artifacts/single-deck-qa/worker-10k-1c1c2c5f7312/`**, 핵심 `preregistration.json`, `calibrations.json`, `admission.json`, `summary.json`, `harness-summary.json`, `final-audit.json`,128회×3 rows/timing/statistics/independent-audit,취소·counter smoke 및 telemetry. `--mode cpu-10k`를 추가했지만 본10000 연속 분기는 이번에 실제 실행 검증되지 않았다. 본진척1000마다기록·전체10페이지 독립검산·배열할당/출력시간분리 코드는 준비됐으며1만 완료로 보고하지 않는다.

확정 QA커밋/본보고서/3후보 calibration 실측·통계/본n0/필요조건/미판정을 현재 Director `term_6e774787-1510-4736-872a-8b9be666e2b0`에 한 번 인계하고 대기한다.11:40까지 남은 시간에 다른 부하를 추가하지 않으며 창은 조기 해제할 수 있다.
