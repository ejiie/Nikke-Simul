# B-CPU Backend 실행 기록

2026-09-15 사용자 승인 배정의 Backend 소유 범위. 전체 배정, AGENTS.md, README, implementation-plan(P06/P08/P09), p04-team-burst, damage-calibration-analysis를 UTF-8로 읽었다. 시작 HEAD `5b7685f`, 기존 untracked package-lock.json만 존재하고 이전 B-IMG 실행 작업은 종료 상태였다. 공통 기준 a5ccba6663241e61783b509fc69098ad3c9ecef2와 분기된 문서 커밋을 보존해 일반 merge `db5d9a5`로 반영했다.

## 선행 계약

`f2327e5a99e9a6ce23e5377a53842fba63274331`: `src/Nikke.Contracts/Compute.cs`, `docs/single-deck-compute-contract.ko.md`. HardwareProfile/ExecutionSelection/ExperimentInput/RunSummary/Statistics/OlComparison와 IPreparedExperiment/IComputeAnalysis 및 route를 먼저 커밋했다.

기존 세션 list/read 확인 후 공유했다. 통계 term_ede55cad-1b9e-40bc-a65a-15b4e9c7a19d 요청 531b8b48-abb2-401e-aa88-db0433568e75, 엔진 term_44567be4-135b-442d-8194-a623c9adf71b 요청 ae243fa1-61ab-4681-9beb-f184a95d568b, 기존 Claude UI term_818b41f3-3b0b-475f-83cc-db252fb90e38 요청 08a26a4f-8195-4571-8f4d-404f02040756. 각각 accepted/input_accepted이며 당시 실행 중인 턴의 추가 turn_started 관측은 없었다. 재전송하지 않았다. 입력 접수와 제품 수용은 다르다. 엔진의 선행 문서 7bd2aef 수신, 구현 완료 커밋은 별도로 취급한다.

## 구현

- Compute: Windows 읽기 전용 CIM inventory를 제한 시간 내 실행, 실패 시 안전한 원인 코드와 CPU fallback. 모든 발견 GPU는 안정적 PNP ID hash/vendor/driver와 별도 runtime/self-test/correctness/benchmark 상태를 가진다. 실제 full-battle provider가 없으므로 not_implemented/eligible=false, 강제 GPU는 실행 전에 gpu_unavailable. 드라이버 설치·GPU 성공 위장 없음.
- CPU 병렬도는 Environment.ProcessorCount로 현재 프로세스 가용 범위를 잡으며 물리 코어는 조회 불명 시 null. 메모리는 GC가 제공하는 가용 한도를 기준으로 보수적 제한. 다른 PC의 CPU 모델/경로/스레드 수를 하드코딩하지 않는다.
- Auto: 실제 준비 입력을 이용한 최대 10초의 취소 가능 warmup/후보 worker 측정(1/2/4/... 가용 상한 내, cpu-policy-2). 기본 상한 8은 응답성 보호 정책이지 개발 PC 코어 수가 아니다. 측정 미완료 시 1 worker fallback, 완료 표본만 선택에 사용. 튜닝 표본은 본 결과 DB에 넣지 않는다. 장치·driver·런타임·엔진·규칙·입력·자원 상한 fingerprint별 별도 tuning 디렉터리이며 다른 PC 캐시는 키 불일치로 무효화한다. 짧은 튜닝은 최적 성능 보장이 아니다.
- Jobs/Storage: 외부 dataRoot/compute의 별도 batches.db, bounded channel와 단일 writer, run 단위 CPU 병렬성. 한 API에서는 한 batch/benchmark만 계산한다. 원본 계정 저장소와 결과 DB를 분리한다. queued/running/cancelling/cancelled/completed/failed, partial과 정상 0을 구별한다. (experiment,index) 유일 키와 현재 attempt 검사로 오래된/중복 결과를 차단한다. crash는 cancelled/process_interrupted로 복구하고 명시 resume에서 실패·미완료 index만 새 attempt로 실행한다.
- Data: 5인 스탯을 synchro 400으로 한 번 준비, private frozen 입력에 전투 조건·택틱·버전·OL을 포함하고 fingerprint를 저장한다. run별 전투 상태/RNG를 분리한다. 생산 고정 seed 없음. 가상 OL은 snapshot 깊은 복사에 실제 부위·줄을 유지해 적용하고 공개 옵션 단계/부호/중복을 검사한다. 원본 장비 저장 API를 호출하지 않는다.
- API: 기존 토큰/동일 출처 정책 아래 compute/hardware 및 experiments create/status/cancel/resume/results/statistics/comparison/ol-candidates. 현재 snapshot/편성과 일치하는 저장 택틱만 적용, stale 거부. 확정 Analysis 구현을 DI로 등록하고 전체 유효 표본의 일관된 저장소 snapshot을 전달한다.

하드웨어 근거: [Microsoft Environment.ProcessorCount](https://learn.microsoft.com/en-us/dotnet/api/system.environment.processorcount?view=net-10.0), [Win32_VideoController](https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-videocontroller). WMI AdapterRAM은 uint32이고 일부 비 WDDM 장치 값은 부정확할 수 있으므로 authoritative compute 메모리/FP64 능력으로 사용하지 않는다. 런타임 provider가 검증하지 않은 GPU 메모리·정밀도는 null이다. 다른 OS 지원 완료는 주장하지 않는다.

## 검증 실행

Backend 전용 `tests/Nikke.Compute.Tests` 및 `check_compute_api.py`. 모든 새 결과는 Backend artifacts/single-deck-backend 아래 생성한다. API 검사는 원본 공개 game-catalog, calculation의 hash manifest와 명시 파일, runtime current/catalog만 복사하고 전후 SHA-256 비교한다. **원본 accounts.db/세션/인증/캐시는 복제·수정하지 않는다.** 새 DB에 합성 계정을 만들고 실제 5인 공개 자료와 실제 CPU 엔진/API를 연결한다. 저장 택틱도 합성 계정에만 기록한다. 원본 5180/5181/EXE/바로가기와 다른 worktree는 변경하지 않는다.

```powershell
$env:DOTNET_CLI_HOME = Join-Path $PWD '.tools/dotnet-home'
$env:NUGET_PACKAGES = '<기존 로컬 패키지 캐시>'
& '<dotnet>' restore src/Nikke.Api/Nikke.Api.csproj --configfile nuget.config --source $env:NUGET_PACKAGES -p:NuGetAudit=false
& '<dotnet>' build src/Nikke.Api/Nikke.Api.csproj -c Release --no-restore
& '<dotnet>' restore tests/Nikke.Compute.Tests/Nikke.Compute.Tests.csproj --configfile nuget.config --source $env:NUGET_PACKAGES -p:NuGetAudit=false
& '<dotnet>' test tests/Nikke.Compute.Tests/Nikke.Compute.Tests.csproj -c Release --no-restore --logger trx --results-directory '<새 실행 경로>'
& '<python>' tests/Nikke.Compute.Tests/check_compute_api.py --source-data '<준비된 공개 dataRoot>' --dotnet '<dotnet>'
```

다른 Windows PC의 portable smoke도 마지막 명령을 사용한다. Python 3와 .NET 10 Release API 빌드 및 공개 계산/runtime 자료가 필요하다. 실행 파일 또는 SDK 위치는 인자로 받는다. 계정 복사·드라이버 설치는 요구하지 않는다. 하드웨어 탐지, 실제 선택, 5인 180초 소량 표본과 취소/재시작/재개, 원본 공개 자료 hash가 실행별 summary.json에 기록된다. 이는 EXE 단독 portable 배포 완료를 뜻하지 않는다.

최초 복원/빌드는 샌드박스의 사용자 NuGet.Config 읽기·기존 DLL 쓰기 권한 거부로 실패했다. 승인 도구 경계를 거쳐 local config/cache로 재실행했다. 첫 실제 컴파일의 중복 익명 속성명 오류 1개를 수정한 뒤 API Release 빌드 경고/오류 0. 초기 Backend 전용 회귀 **14 통과/실패 0/skip 0**, 실행 기간 17초. 근거 `artifacts/single-deck-backend/unit-first/user_BOOK-UB6JGJ0BM4_2026-09-15_11_24_03_net10.0.trx`.

## 미완료·수용 경계

GPU full battle provider/실제 장치 kernel/self-test/정확성/전송 포함 성능이 없으므로 GPU 실행 실패 후 새 CPU attempt 자동 재시도는 미구현·미검증이다. 현재 auto의 실행 전 CPU fallback과 강제 GPU 거부만 구현했다. 합성 Intel/AMD/NVIDIA 탐지 테스트는 그 vendor 장치 실측이 아니다. 다른 PC의 portable 명령을 제공했지만 다른 실제 PC 실행은 미검증이다.

QA 소유 1000/10000/50000회 지속 부하·전체 장치 속도, 실제 브라우저 종단, 실게임 영점, 자동 20억 DEF 전환, 비용/확률 기반 OL 추천은 본 검증 통과와 분리한다. 고정 DEF 30925 정책의 모델 기반 실험이며 이미 관측된 31784 전환 현상을 재검증 요청하지 않는다. 배포·push·신규 worker/Run/Dispatch/lifecycle worker_done 없음.

## 확정 의존 구현 연결

독립 Backend 구현 `e7980ef` 후 엔진 `0d23366`을 merge `16f7d0f`, 통계 구현 `480cf8a`/보고서 `b9ce963`을 merge `0ad4da5`, hit/crit 수정 `979325c`를 merge `3056c59`, signed OL 수정 `81be5d0`을 merge `36d255f`로 보존 반영했다. 엔진/Analysis 소유 파일을 직접 수정하지 않았다. 공용 solution/API/Data 참조는 Backend가 등록했다.

PreparedCompute는 PreparedSkillReplay.Create를 준비/복구 때 한 번 호출하고 Run마다 cpu-summary.1 요약을 매핑한다. 물리 입력 fingerprint에서 phase를 분리하여 같은 후보의 탐색/최종 입력을 비교할 수 있지만, RunSummary와 통계의 phase 혼합 검사는 유지한다. CriticalHits는 전체 피해 크리로 normal Hits보다 클 수 있고 저장/통계 모두 독립 비음수 카운터로 처리한다. 잘못된 합계·시간·음수 카운터는 저장하지 않는다. 메모리와 응답성 보호를 위해 실행/대기 준비 배치 최대 4개, 통계 조회 캐시는 16개/2초로 제한했다. 캐시의 backend/device/chunk/검증 버전까지 검사해 GPU 오표기를 차단한다.

Data의 ComputeOverloadCatalog는 pinned GameSnapshot.OptionSteps와 실제 T10 present 부위/줄을 S의 OverloadCandidates.Generate에 전달한다. 별도 rate 창작 없이 부호와 이산 tier를 보존한다. 현재 전투 조건에서 효과 없는 방어/명중률, 비차지 무기의 차지 옵션, crit off의 크리 옵션, 비상성의 원소 피해는 후보에서 제외한다. API 후보의 after를 명시 후보 실험에 전달하면 원본 불변 전체 전투가 실행된다. 기본 비교는 unverified_design_or_input_difference이며 독립 holdout 검증이 없으면 추천으로 승격하지 않는다. S의 자동 screening/refinement/final 평가 orchestration은 아직 제품 API에 연결하지 않았고 이번 범위는 실제 카탈로그 후보 열거·명시 가상 비교다.

통합 빌드 첫 시도에서 Contracts/Analysis EquipmentLine 이름 충돌 2개 진단을 명시 타입으로 해결했다. 이후 API Release **경고 0/오류 0**(18.92초). Backend 통합 회귀 **18/18 통과, 실패 0/skip 0**, 8초. 근거 `artifacts/single-deck-backend/unit-integrated/user_BOOK-UB6JGJ0BM4_2026-09-15_11_56_53_net10.0.trx`.

최초 API smoke `d4ed374a1db44ac6b7ae5c7c51d13719`는 실제 CPU·강제 GPU 거부·취소/재시작/재개까지 진행했으나 합성 fixture에서 SavedAt을 생략하여 마지막 snapshot 불변 비교가 실패했다. 날짜를 명시하도록 fixture를 수정했고 이 실행을 통과로 세지 않는다. 해당 원본 공개 파일 12개 SHA-256은 전후 동일했다. 후속 검증은 새 격리 dataRoot를 사용한다.

통합 smoke `b167e9cd29d84627956731e0051df123/summary.json`은 **7개 검사 모두 passed**. 새 합성 계정, 공개 5인, 180초/400/DEF30925, 저장 택틱 적용, 실제 CPU→Analysis 평균/CI, 공식 tier 후보 89개, 앨리스 head/1의 StatAtk +0.0547 및 StatChargeTime -0.0198 각각 4회 전체 재실행과 비교, 강제 GPU 409, 취소/프로세스 재시작/resume attempt2 및 원본 snapshot 불변을 확인했다. 공개 원본 12개 hash 동일, 격리 포트 53158만 사용했다. 실제 장치 inventory는 가용 CPU16/물리12, Intel Iris Xe driver31.0.101.4314, 실패 없음, eligible=false였다. 이 장치 발견은 GPU 실행 검증이 아니다.

위 실행의 첫 4회 배치 wall14.038초, 개별 전투1056.75~2026.05ms, 각 fullBursts11이었다. 초기 cpu-policy-1의 3초 예산은 cold JIT를 포함해 측정 표본을 끝내지 못했고 worker1/benchmark_not_measured로 정직하게 fallback했다. 이를 근거로 최종 cpu-policy-2는 전체 튜닝 예산을 취소 가능한 10초로 보완하고 캐시 버전을 변경했다. 이 수치는 동일 조건 성능 전후 비교나 대량 부하 수용으로 사용하지 않는다.

기존 Sync 회귀도 **81/81 통과, 실패0/skip0**, 12초. 근거 `artifacts/single-deck-backend/sync-integrated/user_BOOK-UB6JGJ0BM4_2026-09-15_12_03_16_net10.0.trx`. 엔진122/122 및 통계41/41은 담당 인계 근거이며 이 보고서의 Backend 자체 재실행 수로 합산하지 않는다.

최종 cpu-policy-2 API Release 빌드 **경고0/오류0**, 16.92초. Backend 회귀 **18/18 통과**, 실패0/skip0, 10초. 근거 `artifacts/single-deck-backend/unit-policy2/user_BOOK-UB6JGJ0BM4_2026-09-15_12_07_49_net10.0.trx`. 초기 untracked package-lock.json SHA-256 `2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767`은 동일하며 커밋에서 제외한다. Sync/API의 packages.lock.json에는 필요한 Analysis project reference만 반영했다.

최종 정책의 실제 API 재검증 `artifacts/single-deck-backend/70ef351ac0f54a61b742d33cf215ba50/summary.json`도 **7/7 passed**, 격리 포트52994, 공개 원본12개 변경0, 합성 snapshot 변경0. baseline/양수 OL/음수 OL/취소 후 재개가 각각 최종 유효4회이며 전체 전투·통계·미확정 비교가 연결됐다. 첫4회 wall41.158초, 개별1908.72~4466.84ms, fullBursts각11. 이 실행에서도 10초 튜닝 안에 측정 후보를 끝내지 못해 worker1/benchmark_not_measured fallback을 반환했다. 따라서 실제 장치의 최적 동시성·처리량을 수용했다고 주장하지 않는다. 측정/캐시 선택과 변경 무효화는 합성 workload 회귀 통과이며, 실제 정책 최적성은 QA 순차 부하 검증에 남긴다. 변동 원인을 분리한 성능 비교는 미실행이다.

Backend 자체 최종 검증은 전용18 + 기존Sync81 = **99개 테스트 통과**와 실제 API7개 검사 통과다. 재실행 횟수를 합쳐 테스트 수를 부풀리지 않는다. 모든 API 테스트 프로세스는 도구 종료 시 본인 생성 PID만 종료했고, 원본 계정/세션/캐시는 열거나 복제하지 않았다. 원본5180/5181/EXE/다른 작업공간/원격 push에 대한 변경 없음.

## 최종 커밋과 인계

확정 제품·통합 검증 커밋은 **48c11d8654fc7a9be32cfd2ae1f5f2bc66475887**이다. 이 커밋은 e7980ef 및 확정 E/S 의존 커밋을 모두 포함한다. 본 문서와 `docs/single-deck-compute-contract.ko.md`가 인계 보고서/계약이며 portable 검증 명령은 위 절에 있다. 최종 git status는 보존한 untracked package-lock.json만 남았다.

반환 대상은 기존 Director `term_f54735fc-6293-41b3-ae3a-984fd0d5b42a`이며 CLI list/read로 실행 중인 기존 세션을 확인했다. 제품/보고서 커밋과 실제99 tests/API7 checks, GPU 전체 전투·자동 holdout orchestration·실제 최적 병렬도/대량 부하·브라우저/배포 미수용을 한 번 전달한다. 입력 접수는 Director 통합 또는 QA 통과를 뜻하지 않는다.

## B-TUNE-1 / Q-TUNE-1 후속 — 2026-09-17

이 절은 위 cpu-policy-2 기록의 후속이다. 시작 HEAD181b0a5, 제품48c11d8 및 기존 이력 보존, untracked package-lock.json만 존재했다. Director의 `compute-tuning-followup-2026-09-17.ko.md` 전체와 QA `12d767e7ad11ba22e66bd7f6b48b377ab56076ef:docs/single-deck-qa.ko.md` 전체를 읽었다. QA Probe 소유 코드는 git show로 참고만 했으며 병합·수정하지 않았다. Compute/최소Contracts/Jobs/API 및 Backend 전용tests/문서만 수정한다. Data/Engine/Analysis/UI/QA/다른 worktree 변경 없음.

### 재현과 원인

별도 Backend `tests/Nikke.Tuning.Probe`는 공개 game-catalog/calculation/runtime allowlist12개만 새 artifacts에 복사하고 SHA-256 전후 검사한다. C# Data adapter로 새 합성 5인·400·180초·DEF30925·crit sample·택틱·앨리스 T10 head/1을 준비한다. 원본 계정/세션/캐시/EXE를 읽거나 복제하지 않는다. 생산 고정seed 없음. 준비·복원 비용과 튜닝 Run 호출을 따로 측정한다.

- 자연 실행 `artifacts/tuning-followup/before-3d7eefa9e91e48ed96b43fc6a00b3a79/observation.json`: cpu-policy-2, 준비1630.4391ms, Select4499.9418ms, warmup2115.4851ms 완료, 후보 호출6개 완료. 오늘의 자연 실행에서는 QA의 warmup 소진이 발생하지 않았다. QA의 실패 기록을 부정하거나 항상 실패라고 일반화하지 않는다.
- 통제 재현 `before-slow-fade6d31ac7243f9adfd4616294d85a0/observation.json`: 동일 실제 prepared 입력 wrapper의 warmup에만 취소 가능한11초 대기를 주입했다. 준비368.9337ms, Select10038.3317ms, warmup10030.3642ms 후 OperationCanceledException, 후보0, worker1/not_measured. 이 지연은 합성 주입이며 자연 JIT/PC 성능 실측으로 표시하지 않는다.
- 직접 원인은 warmup과 모든 후보가 단일10초 token을 공유하고, warmup 취소 예외가 후보 루프 전체를 빠져나가는 제어 흐름이다. JIT/스케줄링/호스트 부하의 기여율은 이 작업에서 확정하지 않는다.

### 수정 정책과 관측 경계

cpu-policy-3: 입력 준비 시간은 API create/resume에서 별도로 측정하며 Data 동기식 계약에 따라 전후 취소 검사만 한다. warmup2초와 각 후보24초 예약을 분리한다. 자원 상한 내 `[1]` 또는 `[1,2]`라는 사전 고정 제한 탐색이며 후보마다 동일한 완전 전투2회만 비교한다. 4/8/...은 이번 짧은 탐색 밖으로 명시한다. 전체 튜닝 deadline은26/50초, 프레임 취소 종료를 기다리고 다음 후보를 시작한다. timeout 작업을 background에 버려 중첩하지 않는다. 이는 timeout 숫자만 늘린 수정이 아니라 warmup 실패 격리·동일 완료 작업량·후보 예약·부분 측정 구분·캐시 증거 검증 변경이다.

status의 execution.tuning에 단계별 예약/벽시계/started/completed/interrupted/stopReason/처리량, 계획worker와 자원상한, 준비시간, 캐시출처를 반환한다. 종료상태는 not_measured/partial/measured/cache_reused이며 measured는 제한 후보 전부 완료를 뜻한다. 일부 호출만 완료한 후보는 처리량 비교에서 통째로 제외한다. 부분 후보 집합은 이 attempt에서만 선택하고 캐시에 저장하지 않는다. 외부 취소는 호출자에게 OperationCanceledException으로 전달하고 마지막 관측은 cancelled다. 관리 heap을20ms 간격으로 확인해 단계 도중에도 메모리 초과를 중단한다. 이는 OS RSS의 엄격한 물리메모리 상한이 아니다.

새 캐시는 정책버전/장치·driver·runtime/engine/rules/input/자원 키와 모든 후보의 완전한 횟수·시간·계산 처리량·선택 worker/chunk를 재검증한다. 구버전·부분·오염·증거 없는 캐시는 거부한다. retune 실패 시 이전 파일이 되살아나지 않도록 시작 전에 제거한다. warmup/튜닝 전투는 정상 run DB에 쓰지 않는다. 종료된 최근64 attempt의 중간/취소 관측은 메모리에만 유지되고 재시작하면 소실되며, 정상 최종 선택 관측은 기존 selection JSON으로 저장한다.

### 독립 회귀

기존18 + 신규16 = **34/34 통과, 실패0/skip0**. 신규 항목은 느린warmup→후보예약/캐시, 느린후보·일부호출완료/부분후보, warmup/후보 외부취소, 시작전/진행중 메모리초과, 메모리상한의1worker계획, 구버전/부분/증거없음/처리량오염/GPU오염/잘못된JSON, retune실패의구캐시제거, 입력·engine·rules·하드웨어/자원 fingerprint 변경이다.

최종 근거 `artifacts/tuning-followup/unit-final/user_BOOK-UB6JGJ0BM4_2026-09-17_22_12_20_net10.0.trx`, 테스트6초. 진단 도구 Release15.26초 및 API Release31.30초, 각각 경고0/오류0. 이전 동일34개 실행 `unit-v3/...22_09_12...trx`도9초 통과했으며 최종 개수에 중복 합산하지 않는다.

### 재현 명령과 미수용 범위

```powershell
$env:DOTNET_CLI_HOME = Join-Path $PWD '.tools/dotnet-home'
$env:NUGET_PACKAGES = '<기존 로컬 패키지 캐시>'
& '<dotnet>' restore tests/Nikke.Tuning.Probe/Nikke.Tuning.Probe.csproj --configfile nuget.config --source $env:NUGET_PACKAGES -p:NuGetAudit=false
& '<dotnet>' build tests/Nikke.Tuning.Probe/Nikke.Tuning.Probe.csproj -c Release --no-restore
& '<dotnet>' tests/Nikke.Tuning.Probe/bin/Release/net10.0/Nikke.Tuning.Probe.dll '<공개 dataRoot>' '<새 자기 artifacts>'
# warmup 제어 흐름 진단만 합성 지연을 주입한다. 전투 입력/엔진은 동일하다.
& '<dotnet>' tests/Nikke.Tuning.Probe/bin/Release/net10.0/Nikke.Tuning.Probe.dll '<공개 dataRoot>' '<다른 새 artifacts>' --slow-warmup
& '<python>' tests/Nikke.Compute.Tests/check_tuning_api.py --fixture '<위 새 probe artifacts>' --dotnet '<dotnet>'
& '<dotnet>' test tests/Nikke.Compute.Tests/Nikke.Compute.Tests.csproj -c Release --no-restore --logger trx --results-directory '<새 결과 경로>'
```

구정책 비교는 당시 구DLL을 대상으로 --baseline 옵션을 사용해 캐시 재조회 없이1번만 진단했다. 현재 코드에서 --baseline을 쓴다고 구정책이 되는 것은 아니다. 재현 도구는 args로 경로를 받아 제품에 개발PC 경로를 넣지 않는다. API검사는 새 합성 DB/동적 포트 및 본인 PID 정리만 사용한다.

dotnet/Python process 이름·PID·시작시각 조회는 sandbox 거부 후 도구 승인 경계로 다시 읽었다. 여러 dotnet 프로세스가 존재했고 사전 단독 측정 합의/지속 독점 확인은 없었다. 이 작업의 실제 선택·캐시 결과는 기능 증거이며 성능 순위·최적worker·속도 개선율을 수용하지 않는다. 1천/1만/5만 부하, GPU/OL 추가개발, 실제 사용자계정/브라우저/게임영점/배포는 미실행이다. Q-TUNE-1 종결은 QA 독립 재수용 이후의 판단이며 Backend 자체 테스트로 선언하지 않는다.

### 수정 후 실제 결과

아래 실행은 서로 겹치지 않게 순차 실행했다. 두 probe와 수정 전 재현 모두 물리 입력 fingerprint `3e3a780cc11264d7613cf8b69b17d0f7f5592951a55fb3214b6eebe5fe789b58`로 동일하다. 시간은 ms이며 준비는 튜닝 밖이다. 지연 주입은 warmup에만 적용했고 후보는 실제180초 전투 전체다.

| 새 근거 (artifacts/tuning-followup 아래) | 준비 | warmup 완료/중단·벽시계 | worker1 후보 | worker2 후보 | 최종/재조회 |
|---|---:|---|---|---|---|
| after-10d6425d5dcd4501903ea11535bfd495/observation.json | 1531.4398 | 0/1, 2025.0091 | 2/2완료, 2254.9938 | 2/2완료, 527.0355 | measured, worker2, 총4822.5097; measured_cache, Run호출0 |
| after-slow-9e31141a9de74b1380c5bb90bed19246/observation.json | 910.2464 | 0/1, 2020.1953 (합성지연) | 2/2완료, 2753.9051 | 2/2완료, 646.5898 | measured, worker2, 총5429.7482; measured_cache, Run호출0 |

후보 중단0, 각각 독립24초 예약 내 완료. 두 실행 모두 warmup의 미완료 전투는 피해 표본이나 처리량에 포함하지 않았다. worker2는 이 제한 표본에서 정책이 선택한 값이며 단독 측정에 따른 성능 순위 수용이 아니다. 초기 cold/tiering 영향의 제거·원인 비율을 입증한 것도 아니다.

실제 API `after-slow-9e31141a9de74b1380c5bb90bed19246/tuning-api-summary.json`: **4/4 checks passed**, 격리 포트61369. queued의 tuning.status=warmup을 실제 관측하고 취소했다. warmup98.0035ms 후 external_cancelled, 튜닝전체103.0734ms, 정상valid0. 이는 API 응답 SLA가 아닌 내부 단계 관측이다. 다음 시도는 준비190.214ms, warmup2003.4167ms 중단, worker1의2회2894.6682ms/worker2의2회669.3803ms 모두 완료, 제한선택5570.7212ms 후 정상배치2회 완료. 다음 새 배치는 measured_cache/cache_reused로 정상2회 완료했다. 결과와 통계n=2를 대조해 warmup/튜닝 제외를 확인했고 합성 snapshot도 동일했다. 본인이 시작한 API PID만 종료했다.

수정 전 자연/지연 및 수정 후 자연/지연의 각 `source-hashes.json`에서 공개12개 원본 변경0. 원본 계정/세션/캐시/EXE/5180/5181/타worktree 접근·갱신·종료 없음. package-lock SHA-256 `2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767` 보존·커밋제외. push/배포/새worker/Run/Dispatch/lifecycle 없음. 이번 확정 검증은 **Backend34 tests + 실제 API4 checks + 동일 입력의 선택/캐시2진단**이며 중복 재실행이나 구 QA 수를 합산하지 않는다.

B-TUNE-1 확정 제품 커밋: **40078d0** (`fix(compute): reserve tuning stages and validate complete measurement caches`). 앞선181b0a5/48c11d8을 보존한 후속이며 최종 status는 기존 untracked package-lock.json뿐이다. 기존 Director 터미널 list/read 확인(현재 runtime0baeeac8-72a2-40f0-aabd-9882916a8a93, handle term_f54735fc-6293-41b3-ae3a-984fd0d5b42a) 후 이 커밋과 보고서·위 실제/합성 구분·34회귀/API4/캐시 근거 및 QA/독점측정 미수용을 한 번 인계한다. 최초 제한 실행의 CLI 경로 인식 실패는 같은 실행 파일로 권한 절차를 거쳐 재조회 성공했으며 다른 실행 파일로 전환하지 않았다.
