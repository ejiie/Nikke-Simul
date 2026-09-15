# 단일 덱 CPU/GPU 엔진 작업

기준 `a5ccba6663241e61783b509fc69098ad3c9ecef2`. 시작 `3b92101`은 기준의 조상이므로 ff-only 반영했고 기존 package-lock.json을 보존했다. 다른 작업공간/원본 데이터/캐시/EXE/5180/5181은 변경하지 않는다.

## Backend 호출 계약 (선행 제공)

B-CPU `f2327e5`의 `docs/single-deck-compute-contract.ko.md`와 `src/Nikke.Contracts/Compute.cs`를 읽었다. 외부 DTO/route는 그 계약을 따른다. 엔진은 Contracts/Data/Jobs를 참조하지 않는다.

`Nikke.Engine.Skills.PreparedSkillReplay.Create(IReadOnlyList<SkillReplayMember>, SkillGraph, SkillReplayConditions)`로 입력을 한 번 깊은 복사·검증한다. 준비 객체의 입력은 외부에 노출하지 않는다. summary 기록 수준은 DamageLog=null, Combat.Trace=false, AutoBurst.TimelineLimit=0으로 정규화한다. 호출자는 최종 기록 수준을 입력 fingerprint에 포함한다. HP/스킬/무기/OL/택틱/고정 DEF 및 duration 수치는 바꾸지 않는다. 계정 스탯/싱크로 400 준비는 Backend 소유다.

`prepared.Run(CancellationToken cancellationToken = default)`은 새 전투 상태 및 seed를 지정하지 않은 per-run RNG를 생성한다. 동일 준비 객체의 여러 Run 호출을 Backend의 bounded worker가 병렬 실행할 수 있다. 전투 내부는 순차이며 프레임 순서를 유지한다. 취소는 프레임 경계에서 OperationCanceledException, 잘못된 입력/실행은 예외로 반환하며 부분 전투를 정상 0 표본으로 반환하지 않는다. JSON 직렬화·계정 조회·준비는 per-run 경로에 없다.

반환 `SkillRunSummary`: `ImplementationVersion="cpu-summary.1"`, `RulesVersion`, `TeamDamage`, `Members`(편성 순서), `FullBursts`(실제 진입 횟수), `ElapsedMilliseconds`(전투 실행, 준비 시간 제외). `SkillRunMemberSummary`: `CharacterId`, `Damage`, `Shots`, `Hits`, `CriticalHits`, `Reloads`, `BurstCasts`. Reloads는 기존 ReloadCompleted 내부 이벤트 수, Hits는 기존 평타 명중 수(직접 스킬/추가타는 포함하지 않음), CriticalHits는 기존 모든 피해 경로의 크리 수다. Backend MemberRunSummary에 같은 이름/단위로 매핑하며 run/attempt/index/실험/fingerprint/backend/phase는 Backend가 붙인다.

단일 히트 `HitCalculator.Calculate(HitContext, string roundingPolicy)`는 지정 정책 하나의 double 피해만 반환하며 기존 유효성/산술 순서를 유지한다. 기존 Compare는 audit 기준으로 남긴다. 실행 시 상세 damage log가 필요한 대상에는 기존 Calculation 근거를 보존한다.

GPU primitive 검사는 전체 전투 backend 승격 근거가 아니다. 동일 5인 full battle kernel/정확성/전송 포함 benchmark가 완료되지 않은 동안 GPU는 eligible=false/not_implemented, auto 선택 금지다. 강제 GPU 요청 거부와 CPU fallback 표기는 Backend가 담당한다.

이 선행 문서 커밋 시점에는 구현/측정 검증 중이다. 최종 결과는 아래에 별도 기록한다.

## 확정 구현과 독립 검증 (2026-09-15)

선행 호출 계약 커밋은 `7bd2aef`다. `PreparedSkillReplay`와 `HitCalculator.Calculate`를 실제 구현했다. 최종 구현 커밋은 아래 인계 기록에서 식별한다. Backend `f2327e5`는 읽기만 했으며 타 브랜치를 병합하거나 타 작업공간을 수정하지 않았다. 조건의 실제 필드 이름은 `enemyDefense`다.

- 입력 준비 1회/비공개 깊은 복사, 실행마다 새 전투 상태와 seed 미지정 `Random` 인스턴스, 전투 간 병렬 호출, 프레임 경계 취소를 구현했다. 실패·취소는 예외이며 정상 0 표본으로 바꾸지 않는다. Backend가 IPreparedExperiment adapter에서 취소·실패 상태를 구분해야 한다.
- 정책 하나를 직접 계산해 후보 3개/CalculationTerm/리플렉션 할당을 제거했다. 명시적 전체 double 입력·버프·배율·선택 결과 정밀도 보호를 유지했다. 상세 damage log 대상만 기존 Compare 계산 근거를 생성한다.
- 무기 파생 상태는 초기화, 관련 효과(5/14/61) 적용·갱신·제거, 같은 그룹의 효과 교체, 무기 교체·만료 때 무효화한다. 기존 즉시 갱신/다음 프레임 갱신 시점을 유지한다. summary는 외부용 timeline 수집을 생략하지만 내부 이벤트 전파/카운터/버스트 처리는 유지한다.
- 배열 풀링은 도입하지 않았다. frame skip/event-driven/SIMD는 효과 만료·HoT 마지막 tick·동일 프레임 스킬 연쇄·차지 snapshot·정수화 순서의 동일성 증명과 별도 이득 측정이 아직 없어 기본 경로에 적용하지 않았다. 남은 프레임 LINQ/효과 배열과 결과 DTO 할당은 후속 최적화 대상이다.

Release Core/Engine 테스트 **122/122 통과, 실패 0, skip 0, 표시 실행 시간 26초**. 근거 `artifacts/engine-compute/final/engine.trx`. 기존 damage log/앨리스 charge/버스트·스킬 회귀를 포함한다. 신규 검증은 3개 정책 각각 2,560개 경계 조합의 audit 정확 일치, 모든 double 필드의 NaN/무한/상한 위반, private copy 후 호출자 입력 변경, 병렬 8회 상태 분리, 자동 버스트·reload 집계, 사전 및 실행 중 취소/재실행을 포함한다. 확률 검증은 생산 RNG를 사용하는 독립 24회·각 600프레임, p=0.15 크리의 사전 고정 6σ 이항 허용 범위를 적용했고 통과했다. 실제 게임 피해 분포를 검증한 것은 아니다.

## 성능 근거

동일 공개 가능한 합성 fixture(실제 계정 입력 아님): `tools/benchmarks/engine/fixture.json`, SHA256 `e14a48955bdbc42f15b6e361ef2ab54a5dc66b5c3df46484346b5a3d2cf40f9b`. 5인 180초, StatAttack=100000, **enemyDefense=30925 고정**, crit off, 수동 조작 없음, I/II 지연을 허용 범위 내 1프레임으로 고정한 결정적 비교다. 기본 생산 난수/DEF 정책을 바꾸지 않는다. 원본 fixture의 trace/damage log는 harness가 off로 정규화한다.

.NET 10.0.11 / SDK 10.0.400 / Windows 10.0.26200 x64 / 가용 논리 CPU 16에서 Release, 각 전투 2회 워밍업 후 5회 측정. 할당은 호출 스레드의 GC.GetAllocatedBytesForCurrentThread, GC는 측정 구간의 세대별 수다. 입력 준비·직렬화·저장 시간은 summary 수치에 포함되지 않는다.

| 실행 | ms/회 | bytes/회 | GC 0/1/2 (5회) | 피해 checksum (5회) |
|---|---:|---:|---|---:|
| 기준 a5ccba6 replay, trace/log off | 2526.89798 | 188682252 | 100/2/0 | 6734298815 |
| 최적화 후 일반 replay, trace/log off | 837.12434 | 39308024 | 20/0/0 | 6734298815 |
| 최적화 후 prepared summary | 136.31838 | 39269297 | 20/0/0 | 6734298815 |

근거: `artifacts/engine-bench/baseline-a5ccba6/metrics.json` 및 `artifacts/engine-bench/optimized-cpu-1/metrics.json`. 이 짧은 측정에서 기준 대비 summary 할당은 약 79.2% 감소했다. 시간은 JIT tiering/실행 순서/공유 호스트 부하의 영향을 받으므로 1천/1만/5만회 처리량이나 사용자 실제 덱 성능으로 외삽하지 않는다.

비용 분리 microbenchmark는 hit 100회 워밍업/10,000회 측정: 기준 Compare 0.09340289ms/5464 bytes, 최적화 후 같은 audit Compare 0.04219533ms/5639 bytes, single-policy 0.00030052ms/72 bytes. 모든 checksum=3626430000. audit 자체의 측정 시간 변동도 크므로 single-policy의 절대 속도 배율을 보장하지 않는다. 정적 hot path 조사와 이 구간별 시간/할당 측정으로 리플렉션·후보/term 배열 및 프레임별 무기 재계산을 우선 제거했다. 샘플링 profiler의 스택별 CPU 비율은 수집하지 않았다.

## GPU 조사·실행 근거

Windows 설치 OpenCL runtime을 쓰는 자체 P/Invoke primitive probe를 `src/Nikke.Engine/Gpu/OpenClPrimitiveProbe.cs`에 구현했다. 라이브러리/드라이버를 복사하거나 새 NuGet 의존성을 도입하지 않는다. 표준 API를 직접 호출하는 자체 코드이며 외부 소스 코드 반입이 없다. OpenCL 1.2 호환 API/FP64 확장을 사용한다. double은 선택 지원 기능이므로 이름 탐지와 정밀도 지원을 분리한다. 근거: [Khronos OpenCL C 공식 명세](https://registry.khronos.org/OpenCL/specs/unified/html/OpenCL_C.html), [cl_khr_fp64](https://registry.khronos.org/OpenCL/specs/unified/refpages/man/html/cl_khr_fp64.html), [프로그램 생성 API](https://registry.khronos.org/OpenCL/specs/unified/refpages/man/html/clCreateProgramWithSource.html).

25개 double 입력 × 6개 출력(150값)의 floor/ties-to-even/away-from-zero 및 타격 정수화 경계 kernel을 준비했다. ±0.5 이웃, 정수 이웃, DEF·차지 및 큰 값 경계를 포함한다. FP_CONTRACT OFF, fast-math 미사용, FP64 원정밀도 유지, 배열 묶음 전송/회수 후 CPU 값과 정확 일치 검사다. harness는 숨겨진 자기 자식 프로세스를 생성하고 30초 timeout 시 해당 자식만 종료한다. 제품 EXE·서버 프로세스와 무관하다.

실제 탐지: **Intel(R) Iris(R) Xe Graphics / Intel(R) Corporation / driver 31.0.101.4314**, OpenCL 장치는 있으나 double capability 없음 → `fp64_unavailable`, `valuesChecked=0`. 따라서 실제 GPU kernel 수치 검사·전송 포함 속도 검증은 **미실행**이다. CPU로 대신 계산해 통과로 표시하지 않았다. 근거 `artifacts/engine-compute/gpu-probe-1/probe.json` 및 최종 probe 결과. 다른 Intel/AMD/NVIDIA 장치는 미보유·미검증이다.

**동일 5인 전체 전투 GPU kernel은 미구현**이다. primitive 결과와 무관하게 FullBattleStatus=`not_implemented`, FullBattleEligible=false가 고정된 실험용 probe이며 제품 GPU provider로 등록하지 않는다. Backend의 auto CPU fallback/강제 GPU 거부 및 다른 PC의 hardware inventory·자동 worker 조정은 Backend 소유다. timeout/fp64 지원 GPU에서의 실제 kernel 성공 검증도 후속 대상이다.

## 재현과 미완료 의존성

저장소 기준 SDK가 PATH에 있는 다른 Windows PC에서 실행:

```powershell
dotnet test tests/Nikke.Core.Tests/Nikke.Core.Tests.csproj -c Release --logger 'trx;LogFileName=engine.trx' --results-directory artifacts/engine-compute/verify
dotnet run --project tools/benchmarks/engine/EngineBench.csproj -c Release -- artifacts/engine-bench/verify
dotnet run --project tools/benchmarks/engine/EngineBench.csproj -c Release --no-build -- --gpu-probe artifacts/engine-compute/gpu-verify
```

실제 실행에서는 SDK `C:/Users/user/Documents/GitHub/Nikke-Simul/.tools/dotnet/dotnet.exe`를 읽기 전용 실행하고 DOTNET_CLI_HOME=`$PWD/.tools/dotnet-home`, NUGET_PACKAGES=`$PWD/.tools/nuget-packages`, DOTNET_CLI_TELEMETRY_OPTOUT=1로 격리했다. 최초 benchmark restore는 `-p:RestoreConfigFile=nuget.config`, 이후 명령은 `--no-restore`를 사용했다. benchmark 출력은 FileMode.CreateNew이므로 재실행은 새 결과 디렉터리를 사용한다. 위 SDK 경로는 본인 측정 환경 기록이며 제품 코드에는 하드코딩하지 않았다.

미완료: Backend Data의 IPreparedExperiment 실제 adapter 연결/API cancel-resume-results/저장 복구 종단, UI/Analysis/OL 추천 연결, 실제 400레벨 대상 덱·현재 tactic 입력의 대량 실행, QA 순차 1천/1만/5만회·다른 PC 자동 설정 검수, FP64 GPU primitive 실행/전체 전투 kernel/장치별 end-to-end benchmark. 여기서는 합성 입력 엔진 독립 검증만 완료했다. 기존 실측 DEF 재검증/게임 영점/자동 DEF 전환 수용/배포 완료를 주장하지 않는다. package-lock.json은 기존 untracked 상태로 보존하고 커밋에서 제외한다.
