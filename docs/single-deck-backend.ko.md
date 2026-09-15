# B-CPU Backend 실행 기록

2026-09-15 사용자 승인 배정의 Backend 소유 범위. 전체 배정, AGENTS.md, README, implementation-plan(P06/P08/P09), p04-team-burst, damage-calibration-analysis를 UTF-8로 읽었다. 시작 HEAD `5b7685f`, 기존 untracked package-lock.json만 존재하고 이전 B-IMG 실행 작업은 종료 상태였다. 공통 기준 a5ccba6663241e61783b509fc69098ad3c9ecef2와 분기된 문서 커밋을 보존해 일반 merge `db5d9a5`로 반영했다.

## 선행 계약

`f2327e5a99e9a6ce23e5377a53842fba63274331`: `src/Nikke.Contracts/Compute.cs`, `docs/single-deck-compute-contract.ko.md`. HardwareProfile/ExecutionSelection/ExperimentInput/RunSummary/Statistics/OlComparison와 IPreparedExperiment/IComputeAnalysis 및 route를 먼저 커밋했다.

기존 세션 list/read 확인 후 공유했다. 통계 term_ede55cad-1b9e-40bc-a65a-15b4e9c7a19d 요청 531b8b48-abb2-401e-aa88-db0433568e75, 엔진 term_44567be4-135b-442d-8194-a623c9adf71b 요청 ae243fa1-61ab-4681-9beb-f184a95d568b, 기존 Claude UI term_818b41f3-3b0b-475f-83cc-db252fb90e38 요청 08a26a4f-8195-4571-8f4d-404f02040756. 각각 accepted/input_accepted이며 당시 실행 중인 턴의 추가 turn_started 관측은 없었다. 재전송하지 않았다. 입력 접수와 제품 수용은 다르다. 엔진의 선행 문서 7bd2aef 수신, 구현 완료 커밋은 별도로 취급한다.

## 구현

- Compute: Windows 읽기 전용 CIM inventory를 제한 시간 내 실행, 실패 시 안전한 원인 코드와 CPU fallback. 모든 발견 GPU는 안정적 PNP ID hash/vendor/driver와 별도 runtime/self-test/correctness/benchmark 상태를 가진다. 실제 full-battle provider가 없으므로 not_implemented/eligible=false, 강제 GPU는 실행 전에 gpu_unavailable. 드라이버 설치·GPU 성공 위장 없음.
- CPU 병렬도는 Environment.ProcessorCount로 현재 프로세스 가용 범위를 잡으며 물리 코어는 조회 불명 시 null. 메모리는 GC가 제공하는 가용 한도를 기준으로 보수적 제한. 다른 PC의 CPU 모델/경로/스레드 수를 하드코딩하지 않는다.
- Auto: 실제 준비 입력을 이용한 최대 3초의 취소 가능 warmup/후보 worker 측정(1/2/4/... 가용 상한 내). 기본 상한 8은 응답성 보호 정책이지 개발 PC 코어 수가 아니다. 측정 미완료 시 1 worker fallback, 완료 표본만 선택에 사용. 튜닝 표본은 본 결과 DB에 넣지 않는다. 장치·driver·런타임·엔진·규칙·입력·자원 상한 fingerprint별 별도 tuning 디렉터리이며 다른 PC 캐시는 키 불일치로 무효화한다. 짧은 튜닝은 최적 성능 보장이 아니다.
- Jobs/Storage: 외부 dataRoot/compute의 별도 batches.db, bounded channel와 단일 writer, run 단위 CPU 병렬성. 한 API에서는 한 batch/benchmark만 계산한다. 원본 계정 저장소와 결과 DB를 분리한다. queued/running/cancelling/cancelled/completed/failed, partial과 정상 0을 구별한다. (experiment,index) 유일 키와 현재 attempt 검사로 오래된/중복 결과를 차단한다. crash는 cancelled/process_interrupted로 복구하고 명시 resume에서 실패·미완료 index만 새 attempt로 실행한다.
- Data: 5인 스탯을 synchro 400으로 한 번 준비, private frozen 입력에 전투 조건·택틱·버전·OL을 포함하고 fingerprint를 저장한다. run별 전투 상태/RNG를 분리한다. 생산 고정 seed 없음. 가상 OL은 snapshot 깊은 복사에 실제 부위·줄을 유지해 적용하고 공개 옵션 단계/부호/중복을 검사한다. 원본 장비 저장 API를 호출하지 않는다.
- API: 기존 토큰/동일 출처 정책 아래 compute/hardware 및 experiments create/status/cancel/resume/results/statistics/comparison. 현재 snapshot/편성과 일치하는 저장 택틱만 적용, stale 거부. Analysis 미연결 시 analysis_not_integrated를 반환하며 통계를 임의 계산하지 않는다.

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

엔진 최적 summary 구현/성능 전후 근거, Analysis adapter 최종 구현은 담당 확정 커밋 수신 후 연결 대상이다. GPU full battle provider/실제 장치 kernel/self-test/정확성/전송 포함 성능이 없으면 GPU fallback 재시도 경로를 실제 검증 완료라 하지 않는다. 합성 Intel/AMD/NVIDIA 탐지 테스트는 그 vendor 장치 실측이 아니다.

QA 소유 1000/10000/50000회 지속 부하·전체 장치 속도, 실제 브라우저 종단, 실게임 영점, 자동 20억 DEF 전환, 비용/확률 기반 OL 추천은 본 검증 통과와 분리한다. 고정 DEF 30925 정책의 모델 기반 실험이며 이미 관측된 31784 전환 현상을 재검증 요청하지 않는다. 배포·push·신규 worker/Run/Dispatch/lifecycle worker_done 없음.
