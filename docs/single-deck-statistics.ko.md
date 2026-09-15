# 단일 덱 S-CPU/OL 통계 구현 — 2026-09-15

## 기준·소유·현재 범위

착수 지시 `Director/docs/single-deck-compute-assignments-2026-09-15.ko.md`를 UTF-8로 끝까지 읽고 공통/S-CPU 절을 수행했다. AGENTS.md, README, implementation-plan P06/P08/P09, p04-team-burst 및 damage-calibration-analysis를 확인했다. 시작 HEAD `5172afe`, 기존 미추적 package-lock.json뿐. 중복 전투/테스트 프로세스는 없었고 다른 통계 터미널에는 실행 작업 지시가 없음을 읽기 전용 확인했다. 현재 터미널은 `term_ede55cad-1b9e-40bc-a65a-15b4e9c7a19d`다.

`a5ccba6663241e61783b509fc69098ad3c9ecef2`로 ff-only 성공하여 이전 완료 커밋을 보존했다. 이후 Backend 확정 계약 **`f2327e5a99e9a6ce23e5377a53842fba63274331`**를 ff-only로 반영했다. Backend의 기존 분기 문서 커밋도 함께 보존됐으며 임의 DTO/route를 만들지 않았다. 원본 계정/세션/캐시/EXE/5180/5181·다른 worktree 편집·push·새 worker/Run/Dispatch·worker_done은 수행하지 않았다. package-lock.json SHA-256은 작업 전후 `2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767`로 동일하며 커밋 제외다.

소유 산출물:

- `src/Nikke.Analysis`: Contracts만 참조하는 독립 .NET 10 라이브러리. 통계/OL 내부 타입과 확정 `IComputeAnalysis` adapter.
- `tests/Nikke.Analysis.Tests`: 전용 project·lock·독립 수치/계약/holdout 테스트.
- `tools/single-deck-analysis`: native 합성 입력의 실제 엔진 연동 및 완전한 BatchResults JSON 분석 CLI.
- 본 보고서. 공용 solution·Engine/Core/Contracts/API/Data/UI/Storage 파일은 직접 수정하지 않았다.

확정 구현·테스트·연동 도구 커밋: **`480cf8a6394d42a19484e0ca9cae1129395f8b20`**. 본 보고서는 후속 문서 커밋으로 인계한다. Backend는 이 구현 커밋을 통합한 뒤 Analysis 참조/등록을 수행할 수 있다.

## 통계 의미와 자원 한도

`Moments`는 첫 표본을 기준값으로 뺀 Welford 집계와 Chan 병합을 사용한다. 큰 공통 피해값의 작은 변동을 보존하며 raw 제곱합에서 제곱평균을 빼는 불안정한 분산식을 사용하지 않는다. 독립 fixture 8×10^15+[0,1,2,3,4] 반복 50000개에서 기대 평균/표본분산 및 교차 분할 병합을 확인했다. 이 50000은 **수치 fixture 개수**이며 50000회 전투 실측이 아니다. 허용 숫자는 finite 및 절댓값 ≤9×10^15다.

`DistributionAccumulator`는 정확한 중앙값/P5/P95를 위해 값을 저장한다. 보간은 Hyndman–Fan type 7, 인덱스 `(n−1)p`. 기본 최대 50000개, 초과/호환되지 않는 cut·단위 병합은 명시 오류다. 평균/분산은 O(1) 추가, 분위수 저장은 metric당 O(N), snapshot의 정렬은 O(N log N)이다. 무한 저장이나 조용한 표본 삭제/근사 분위수 전환은 없다. 큰 배치에서 진행률마다 snapshot을 반복 정렬하지 말고 Backend가 요청 주기를 제한해야 한다.

평균 CI는 표본 SD/√n에 Student-t 분위수를 곱한 고정-N 95% 구간이다. t 분위수는 incomplete beta CDF 역산이며 외부 통계 런타임 의존이 없다. n=0은 평균/분위수/CI가 null, n=1은 평균/분위수만 계산하고 SD/평균 CI는 null이다. 정상 피해 0은 유효 표본이다. 분포의 P5/P95는 한 판 결과 분위수로 평균 CI와 다르다. 비정규 전투 분포에서는 t 구간이 대표본 근사이며 n이 작을 때 정규 모집단 가정 없이 정확한 95% 보장을 하지 않는다.

컷 성공은 **damage > cut**(동일 값 제외), 분모는 완료된 유효 표본이다. 95% Wilson score CI를 사용하며 0/n, n/n에도 0폭 확신을 만들지 않는다. 표본 오차 구간은 엔진 모델 오차/게임 정확도를 포함하지 않는다.

`ExperimentAccumulator`는 불변 experiment/input/backend/phase별로 격리한다. 같은 runId의 다른 attempt도 중복 추가를 거부하고, partition 병합에서 ID 중복·서로 다른 수치 backend·단계·입력·cut을 거부한다. failed/cancelled/completed-but-incomplete를 각각 세고 정상 0 표본으로 넣지 않는다. 잘못된 입력은 집계 상태를 변경하기 전에 거부한다. 팀 통계는 매 실행의 팀 총피해에서 계산하며 개인 분위수의 합을 팀 분위수로 만들지 않는다.

## Backend 연결

확정 `Compute.cs`의 `RunSummary`/`BatchStatus`와 `IComputeAnalysis`를 직접 사용한다. DI 등록 예: `IComputeAnalysis` → `Nikke.Analysis.ComputeAnalysis`. Backend가 API/solution/project 참조를 소유한다. 필요한 참조는 `src/Nikke.Analysis/Nikke.Analysis.csproj`이며 Analysis가 API를 참조하지 않는다.

- `Summarize(batch,runs,cut)`에는 **모든 현재 유효 index의 결과**를 전달한다. 페이지 일부만 전달하면 Valid 수 불일치로 거부한다. 재개 후 유지된 정상 old-attempt 표본은 허용하되 같은 index/runId 중복, future attempt, 잘못된 `experimentId:index`, 다른 phase/fingerprint/backend를 거부한다. 실패·취소 수는 BatchStatus에서 받는다.
- 5인 순서/ID, synchro 400, 정상 숫자, 팀 피해 합, valid/requested/partial 일관성을 검사한다. Hits는 평타 명중, CriticalHits는 모든 피해 경로 크리이므로 두 카운터 사이 대소관계를 강제하지 않는다. hit/shot 비율을 명중률로 해석하지 않는다.
- `StatisticsResult` v1에는 팀/개인 **피해** 분포를 반환한다. `Aggregate` 내부 결과에는 피해 외 팀 fullBursts, 실행 ms, 각 멤버 shots/hits/criticalHits/reloads/burstCasts도 집계한다. 현재 wire의 Members 값은 MetricStatistics 하나여서 이 추가 지표 전체를 statistics route에 표시할 필드는 없다. 추가 wire 설계는 Backend 소유이며 미지원 지표를 임의 필드로 내보내지 않았다.
- `Compare`는 snapshot/data/engine/rules/DEF/기간/편성/phase/backend 일치를 확인하고 독립 Welch-Satterthwaite 차이 CI와 개인·동료·사이클 차이를 반환한다. 실행 조건 전체와 “선언한 OL만 변경” 여부는 v1 ExperimentInput만으로 입증할 수 없다. 기본 verdict는 `unverified_design_or_input_difference`; CI 숫자만으로 추천 승격하지 않는다.
- Backend가 frozen holdout 배정 및 선언한 OL만 변경됨을 검증할 때 생성자 `verifyFrozenHoldoutDesign` callback을 제공할 수 있다. 비교 family 크기는 사전에 고정한 `comparisonFamilySize`로 제공한다. 부분 배치는 `partial_unresolved`, 탐색 표본은 `exploratory_only`. 이 callback 없이 임의로 true를 주입하지 않는다. 실제 장비·수치 허용범위 검증은 Backend 준비 adapter의 책임이다.

## OL 후보와 독립 최종 평가

`OverloadCandidates.Generate`는 Backend가 고정한 catalog version/실제 장비 부위·줄/유효 옵션 값 목록을 입력받는다. 원본 장비를 편집하지 않는 before/after immutable record만 생성한다. 기존 줄 번호 1~3·부위·캐릭터를 유지하고 동일 장비 중복 옵션, 동일 값 변경 없음, 미지원·모델 효과 없음, 비정상 수치를 제외/거부한다. 옵션 확률·모듈 비용·잠금 규칙은 생성하지 않는다. 실제 game catalog adapter 제공 전 이 목록의 공식 게임 유효성 검증 완료를 주장하지 않는다.

`OverloadEvaluation.EvaluateAsync`는 Backend callback에 `EvaluationRequest`를 전달하는 독립 orchestration 코어다. wire route가 아니며 새 Orca worker/Run을 생성하지 않는다. callback은 불변 가상 OL 입력으로 **전투 전체를 다시 실행**해야 한다. 고정 로그 배율 계산은 최종 평가 경로가 아니다.

1. 모든 후보 소규모 screening(default 100) → 팀 평균 상위 및 CI가 겹치는 불확실 후보·임계점 민감 후보 refinement(default 1000).
2. refinement 팀 평균으로 finalist 집합(default 최대 3)을 확정한다. 후보 풀 내부 탐색이며 전역 최적을 주장하지 않는다. 예산 제한으로 제외한 불확실 후보의 우열을 확정하지 않는다.
3. 새 기준 및 각 finalist의 독립 final(default 각 10000) 전투. 전체 전투 실행 표기, exact N, partial/실패/취소 없음, 새로운 experiment/run ID, 동일 공통 조건·수치 backend, phase별 동일 후보 fingerprint를 요구한다. 탐색 sample reuse·fingerprint 변동·후보 간 동일 준비 입력·취소를 거부한다. seed pairing을 도입하지 않는다.
4. 최종 팀 평균 차이의 Welch CI에 finalist 수 Bonferroni 보정을 적용한다. 가족을 고정한 뒤 최종 데이터를 보므로 탐색 winner’s curse를 최종 표본에 재사용하지 않는다. CI가 0과 겹치면 unresolved, 양수면 model_improvement, 음수면 model_worse. 양쪽 표본분산이 모두 0이어도 확률적 우위를 입증한 것으로 처리하지 않고 zero_variance_unresolved다. 동료·사이클 변화 구간은 보조 탐색 지표이며 다중 지표 전체의 동시 보장을 주장하지 않는다.

holdout fixture는 탐색에서 1000 피해로 운 좋게 선정된 후보가 새 final에서 기준과 동일한 10/11 분포이면 개선 0/unresolved가 되는지 확인한다. 모든 단계는 실제 숫자를 만들어낸 **합성 callback 검증**이며 공식 5인 OL 배치 실행이 아니다.

## 표본 수·대량 실행 계획

pilot 1000 → 사전 고정 final 10000 → 지속 부하 검증 50000 순서로 QA와 Backend가 실제 배치 실행한다. `Inference.Plan`은 pilot SD와 지정한 평균 CI 절대 반폭으로 필요한 N을 계산하고 budget 초과를 표시한다. 상대 정밀도를 원하면 고정한 pilot 평균 기준으로 절대 반폭을 정한 뒤 N을 확정해야 한다. pilot n<2 또는 표본분산 0은 유한 N 정확도 증거가 아니므로 RequiredN=null이다.

계획식은 pilot 기반 추정이며 실제 달성 보장이나 중단 규칙이 아니다. 무제한 CI 관찰 후 유리한 시점에 멈추는 실행을 일반 고정-N 95% 보장으로 표시하지 않는다. 탐색/적응 추가 표본과 final을 섞지 않는다. 1000/10000/50000 **전투** 및 CPU/GPU 성능·다른 PC 탐지/자동 튜닝 검수는 이번 역할에서 실행하지 않았다. Backend·Engine·QA의 장치 실측 없이 GPU 적합이나 자동 설정 완료를 주장하지 않는다.

사용자 확인된 DEF 30925→31784와 20억 현상은 재검증 대상이 아니다. 현재 평가 정책은 고정 DEF이며 자동 전환·게임 영점 미수용 상태를 모델 실험과 구별한다.

## 재현·근거

```powershell
$env:DOTNET_CLI_HOME = Join-Path $PWD '.tools/dotnet-home'
$env:NUGET_PACKAGES = 'C:/Users/user/Documents/GitHub/Nikke-Simul/.tools/nuget-packages'
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$taskOut = Join-Path $PWD ('artifacts/single-deck-statistics/unit-' + [guid]::NewGuid().ToString('N'))
& 'C:/Users/user/Documents/GitHub/Nikke-Simul/.tools/dotnet/dotnet.exe' test tests/Nikke.Analysis.Tests/Nikke.Analysis.Tests.csproj -c Release --logger 'trx;LogFileName=analysis.trx' --results-directory $taskOut
```

최종 독립 회귀 **25 통과 / 실패 0 / skip 0**, 테스트 실행기 기간 3초. Release 빌드 성공, 경고/오류 없음. 근거 `artifacts/single-deck-statistics/unit-0bb5f8ab15bc4f459af67ba8333ec18f/{analysis.trx,test.log}`. 앞선 수치 코어만 17개 통과한 출력 `unit-8d800f9bbecd4955b0c0a9c4365fdbeb`도 보존했으며 최종 수와 혼동하지 않는다.

TRX SHA-256: `9bb40544d93890af75f939e4af3a18b641b7e35668c74645f1490a8faa26166f`. 이번 실행에서 테스트 실패는 없었다. `git diff --check` 및 staged 검사 통과(LF/CRLF 안내만).

실제 엔진 → RunSummary → 분석 연동 실행:

```powershell
& 'C:/Users/user/Documents/GitHub/Nikke-Simul/.tools/dotnet/dotnet.exe' run --project tools/single-deck-analysis/SingleDeckAnalysis.csproj -c Release -- --engine-input artifacts/s3/engine-a59a2f4c30db4a55994bebb5ff2958b7/engine-example-b930d3c5bbcd452894ed33b3220084fc/input.json 3
```

종료 0. 이전 확정 합성 E2 input만 본인 artifacts에서 읽고 새 엔진 실행을 3회 수행했다. 입력 SHA-256 `e14a48955bdbc42f15b6e361ef2ab54a5dc66b5c3df46484346b5a3d2cf40f9b`는 실행 전후 동일하다. 입력이나 결과 로그를 복제해 표본 수를 늘리지 않았으며 각 실행마다 seed 인자 없는 새 Random 인스턴스/전투 상태를 사용했다. damageLog/trace off에서도 내부 reload 및 burst 이벤트를 sink로 집계했다. 5명/10800프레임, **합성 고정 DEF=10**의 연동 fixture이므로 실제 대상 DEF 30925/31784 성능 비교나 공식 계정 스펙 실험으로 해석하면 안 된다. 이 native fixture에는 synchro 메타데이터가 없음을 결과에 명시했고 임의로 400이라고 채우지 않았다.

실제 팀 피해 `[1800603,1797781,1800925]`, 각 fullBursts=9. 팀 평균 `1799769.6666666667`, sample SD `1729.7448752152247`, median `1800603`, P5 `1798063.2`, P95 `1800892.8`. 평균 t CI는 `[1795472.7421904376,1804066.5911428959]`이며 n=3에서 분포 가정 없이 게임 오차 95% 보장을 뜻하지 않는다. 별도 배열 평균과 집계 평균의 일치 검사 통과. cold/warm 분리 없는 기록 시간은 각각 10248.8457/5460.2216/2172.1792ms이며 역할 간 동시 작업 환경이라 성능 개선율/run/s 근거로 사용하지 않는다.

실제 증거 `artifacts/single-deck-statistics/integration-e012a23638ef4e8db037fac47efce36c/statistics.json`, SHA-256 `db2a91d55895b1d5bc3c5603fabfc669ec61c5d297ff9de0bbe12473de57ee1e`. 호출 로그 `artifacts/single-deck-statistics/smoke-52181d8976f74183938d078e59d81004/run.log`. 전부 본인 새 출력 경로다.

Backend가 준비한 완전한 결과 JSON에는 `--batch-results <BatchResults JSON>`을 사용할 수 있다. 분할 조회라면 모든 유효 rows를 모아 전달해야 한다. 이 CLI 모드와 공식 계정 배치 API 종단은 이번 미실행이며 adapter는 위 합성 계약 회귀로 검증했다.

통계 독립 근거: [NIST 평균 t 구간](https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm), [NIST Wilson score 구간](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm), [NIST 독립 평균 차이 구간](https://www.itl.nist.gov/div898/software/dataplot/refman1/auxillar/diffmean.htm), [R 공식 type 7 분위수](https://stat.ethz.ch/R-manual/R-devel/library/stats/html/quantile.html). 독립 fixture는 1..5의 평균3/분산2.5/P5=1.2/P95=4.8, t(df=1/2/9/30/1000) 표준 수치, Wilson 50/100, Welch 차이10/df8을 확인한다.

## 남은 연결·수용

- Backend가 Analysis project 참조/DI/통계·비교 API route를 연결하고 complete RunSummary enumeration을 전달해야 한다. 이번 커밋에서 API 종단 연결 완료를 주장하지 않는다.
- 공식 리타·블랑·앨리스·누아르·모더니아 실제 스탯/OL catalog 기반 준비 adapter와 가상 변경 전체 재실행 연결은 Backend 의존이다. 현재 후보 생성/holdout은 독립 코어·합성 검증이며 실제 계정 추천 결과를 생성하지 않았다.
- Engine의 새 prepared/summary 최적화 및 GPU kernel을 기다리지 않고 기존 엔진을 통한 연동 확인 경로를 제공했다. 최적화 성능·GPU·다른 PC 실측·50000회 전투·비용 효율·원본 배포는 미완료/타 담당 범위다.
- 실게임 관측 데이터 부재와 gameVerified=false 유지. 추천은 옵션 변경의 모델 가치이며 게임 검증 완료·모듈 예산 최적 정책으로 표시하지 않는다.

## B-CPU 호환 수정 — Hits와 CriticalHits 의미 분리

Backend의 확정 Compute.cs/IComputeAnalysis 계약을 다시 읽고 E-CPU `0d23366:docs/single-deck-engine.ko.md`와 해당 SkillReplay 구현을 읽기 전용 대조했다. `if (crit) a.Crits++`는 모든 피해 경로에 적용되지만 `if (normal) a.Hits++`는 평타에만 적용된다. 따라서 CriticalHits > Hits는 유효한 결과이며, 최초 `480cf8a`의 크기 비교 검증은 잘못된 가정이었다.

`ComputeAnalysis.Aggregate`에서 이 관계 검사만 제거하고 각 카운터를 그대로 독립 집계한다. 음수/비정상 값 검사와 팀 피해/편성/중복/attempt/phase/backend/partial 검증은 유지한다. 직접 스킬 크리가 있는 평타 0명중 `(Hits=0,CriticalHits=3)` 및 추가 피해 포함 `(2,5)`의 adapter 합성 회귀를 추가했다. 음수 Hits/CriticalHits 거부도 각각 검사한다. 카운터를 자르거나 크리를 평타 명중 수로 맞추지 않는다.

외부 DTO·공용 solution·API 등록·엔진 제품 코드는 수정하지 않는다. 기존 `src/Nikke.Analysis/Nikke.Analysis.csproj` → Contracts 참조와 `ComputeAnalysis : IComputeAnalysis`를 유지한다. 통계 방법은 기존 MethodVersion/QuantileMethod/Interval.Method의 type7/Student-t/Wilson/Welch 표기를 유지한다. 이 수정의 수용은 adapter 경계 검증이며 실제 API 배치 완료나 게임 정확도 판정이 아니다.

실제 실행: 위와 같은 DOTNET_CLI_HOME/NUGET_PACKAGES 환경에서 `dotnet test tests/Nikke.Analysis.Tests/Nikke.Analysis.Tests.csproj -c Release --no-restore --logger 'trx;LogFileName=analysis.trx' --results-directory <새 경로>` 사용. 수정 전에는 `--filter FullyQualifiedName~Wire_adapter_keeps_normal_hits`로 새 정상 사례 2개의 실패를 재현했다. 수정 후 필터 없는 전체 회귀 **29 통과 / 실패 0 / skip 0**(기존 25 + 신규 4), 표시 테스트 시간 1초. 빌드 경고/오류 없음, git diff 검사 통과. 확정 결과는 본 절과 코드·회귀를 포함한 후속 수정 커밋으로 Backend에 전달한다.

- 수정 전 실패 근거: `artifacts/single-deck-statistics/crit-before-4f071ab475a345fba50d3a988215e0d0/{analysis.trx,test.log}`.
- 최종 회귀 근거: `artifacts/single-deck-statistics/crit-after-a1ff7b324b25461abc7e906be777ec73/{analysis.trx,test.log}`.
- 시작 HEAD `b9ce963`, 이전 미추적 package-lock.json 보존(앞선 SHA-256 동일). 다른 담당의 진행 중인 제품 커밋은 병합하지 않고 확정 문서/코드만 읽기 전용 대조했다.
