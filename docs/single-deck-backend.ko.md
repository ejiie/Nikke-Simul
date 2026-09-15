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
