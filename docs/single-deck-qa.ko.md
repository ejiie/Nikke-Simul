# Q-CPU/GPU 독립 소규모 수용 — 2026-09-16

**판정: 지정 소규모 CPU/API·통계·명시 OL 비교·저장 복구 및 fallback 안전성 통과. 자동 최적 동시성 수용은 보류. GPU 전체 전투와 GPU 실패 후 CPU retry는 미구현 상태 유지.** 실제 사용자 덱·게임 정확도·대량 성능·배포 수용은 아니다.

## 이번 확정 기준과 실제 실행

제품 `48c11d8654fc7a9be32cfd2ae1f5f2bc66475887`을 기존 QA `4564408754d89b91964ef06033d717812bd89c52`와 충돌 없는 일반 merge로 통합했다. 검증 HEAD는 `380a444e51e38860b3ca6bad8d8a808a4b95c58a`다. E 0d23366, S 480cf8a/b9ce963, hit/crit 979325c, signed OL 81be5d0을 포함한다. `181b0a5`의 최종 Backend 보고서·계약을 git show로 끝까지 읽고 현재 지침/엔진/통계 보고서를 대조했다. 문서 커밋을 제품 커밋으로 혼동하지 않았다.

제품 파일을 수정하지 않았으며 제품 SHA 대비 src/apps/tools/data-pipeline/scripts 차이가 없다. 기존 package-lock SHA-256 `2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767` 보존. 원본 계정DB/세션·presentation 캐시·EXE·5180/5181에는 이번 후속 검수에서 접근/갱신/종료하지 않았다. 허용된 공개 game-catalog, calculation current/hash manifest의 파일, runtime current/catalog **12개만** 읽고 새 artifacts로 복사했다. 실행 전후 12개 SHA-256 변경 0. 원본 계정 전체 hash 검사로 확대 주장하지 않는다.

Backend `check_compute_api.py`의 공개 파일 allowlist와 새 합성 계정 준비 부분만 `public_fixture.py`에 출처를 명시해 재사용했다. 수용 검사는 별도로 작성했다. 합성 계정의 5인 순서는 리타 5011·블랑 5008·앨리스 5004·누아르 5009·모더니아 5044, 400, 180초, fixed DEF30925, crit sample, 저장된 합성 택틱이다. 원본 사용자 스펙/현재 사용자 덱을 검증한 것이 아니다. CPU 생산 경로에 seed를 넣지 않았다.

| 검사 | 새 실제 근거와 판정 |
|---|---|
| API Release 빌드 | 경고 0 / 오류 0. `artifacts/single-deck-qa/build-8cfd21fc0b354443ae8298f2878064fe/build.log` |
| 실제 CPU/API 주 실행 | `small-a6f3938d1793/`: 13항목 중 직접 12 통과, QA 기본값 기대 차이 1건은 실제 저장 증거 재분석 통과. 최종 유효 전투는 5실험 총 15회(3+2+2+6+2) |
| 정상 0·캐시·warmup 제외·취소 edge API | `edges-873f8312e1c1/summary.json` passed. 새 1프레임 5인 fixture의 4실험 각 2회, 이후 180초 요청의 pre-running 취소 |
| 실제 BatchStore/Analysis/ExecutionPolicy probe | `probe-3c75a53fc91b4a009c54d46de351e967/storage-summary.json`: 7항목 통과. 합성 RunSummary로 실제 제품 저장소·분석·정책을 호출 |
| 실제 준비 입력 튜닝 관측 | 같은 probe의 `tuning-observation.json`: 동일 공개 5인 180초 준비 입력, 두 10초 진단 및 후속 캐시 조회. 최적화 수용 미달을 재현 |
| QA 자체 회귀 | `oracle-9c3644eaa7b54641b68f7a8886bd8643/`: 최신 계약/독립 적분 포함 42 통과. 이 수를 제품 API 수용으로 대체하지 않음 |

위 경로는 모두 본인 `artifacts/single-deck-qa/` 아래 상대 경로다. API는 OS가 배정한 5180/5181 이외 포트만 사용하고 finally에서 본인이 시작한 PID만 종료했다. 타 worktree 편집/배포/push/새 worker·Run·Dispatch/lifecycle 작업 없음.

## 기능별 수용 근거

### summary.1과 입력 고정

실제 API 입력/결과/자기 격리 DB의 prepared payload를 대조했다. `engineVersion=cpu-summary.1`, 400, 5인 순서, `fixed:30925`, 10800프레임, 저장 택틱과 입력 fingerprint 일치. 결과는 실제 PreparedCompute → PreparedSkillReplay.Run 경로이며 각 실행의 신규 runId·members·fullBursts·양수 피해를 확인했다. baseline/양수 OL/음수 OL의 물리 입력 fingerprint가 서로 다르고 동일 baseline을 resume할 때 유지됐다.

택틱 검사 최초 실패는 제품 오류가 아니었다. QA 요청 기대값에 없던 `firstBurst3CharacterId:null`을 DTO가 정상 기본값으로 저장했다. 기대 fixture에 명시하고 저장된 요청/준비 입력 모두 정확 비교했다. 원래 `summary.json`의 실패를 삭제하지 않았고 `baseline-reanalysis.json` 및 `final-audit.json`에 교정 이유와 판정을 남겼다. 전체 전투를 재실행한 것처럼 표시하지 않는다.

### 통계·카운터·컷

limit=1로 전체 유효 페이지를 읽고 최신 Backend adapter로 runId/index/attempt/편성/합계를 확인했다. 해당 전체 배열의 팀 및 5인 평균·표본 SD·median/P5/P95를 별도 Fraction 산술/HF7로 검산했다. Student-t 및 Welch CI는 제품의 incomplete-beta 역산과 별개로 `x=sqrt(df)*tan(theta)` 치환 밀도를 Simpson 적분/역산하여 비교했다. df1/df2 폐쇄형 기대값 회귀도 통과했다. 작은 표본의 CI는 게임 정확도를 보장하지 않는다.

실제 baseline 컷은 첫 표본 피해 **855055161**로 지정했다. 성공은 엄격한 `damage > cut`, n=3에서 1/3이며 Wilson 문구도 `strict damage > cut`이다. 1프레임 API 전투에서는 피해 0인 두 표본이 valid=2/mean=0이고 cut=0 성공은 0이다. n=0의 null 통계와 partial=true, 완료 n=2/partial=false, 2.2초 뒤 조회의 일치를 확인했다. 동일 완료 통계 재조회도 일치했다. 캐시는 계약상 최대 2초의 같은 시점 snapshot이며 최신 status와 항상 같은 순간의 n이라고 확대하지 않는다.

준비 당시 잘못 넣었던 `CriticalHits <= Hits` 제약을 QA에서 제거했다. 실제 제품 Store/Analysis에 Hits=0/CriticalHits=3을 전달해 정상 수용, shots/hits/crits/reloads/burstCasts 각각 음수를 넣으면 거부함을 확인했다. 평타 Hits와 전체 피해 CriticalHits는 서로 다른 계수다. 크리를 잘라내거나 표본을 삭제하지 않는다.

### 취소·재시작·resume·저장

180초 6회 배치가 일부 완료됐을 때 취소했다. 정상 결과 **2개**를 보존하고 재시작/resume attempt2로 남은 4개를 완료했다. 최종 attempt 배열은 `[1,1,2,2,2,2]`, 유효 n=6/partial=false이며 이전 결과 JSON이 그대로다. 별도 2회 배치를 프로세스 강제 종료한 뒤 재시작했을 때 `cancelled/process_interrupted`, valid=0/cancelled=2였고 resume attempt2 후 정상 2개가 됐다.

실제 BatchStore probe는 정상 0과 실패 payload=null 분리, 중복·충돌의 first-write-wins(기존 정상 결과 불변), 잘못된 chunk 전체 rollback, 재구성에 따른 crash 복구, 이전 attempt의 늦은 Write 무시, 정상 old index 보존을 검증했다. 실패 전투 주입은 합성 RunSummary/RunWrite를 실제 저장 경계에 전달한 검사이며, 자연적으로 엔진이 실패한 실제 사용자 전투를 관측한 것은 아니다.

주 실행의 취소→종료 관측은 약 **190ms**, 상태 API 546회 p95 약 **175ms**/최대 약691ms다. 작은 edge 요청의 pre-running 취소 응답 약58ms/종료 약70ms다. 이는 API 관측 지연이며 UI 응답 시간이나 다른 장치/전후 처리량 비교가 아니다. edge 산출물의 과거 키 `cancelDuringTuning`만으로 내부 warmup 진입을 입증할 수 없다. API queued는 탐지/튜닝을 함께 포함하므로 도구의 최종 명칭은 `cancelBeforeRunning`으로 정정했다. 실제 warmup 중 취소는 아래 probe의 OperationCanceledException 기록으로 구분한다.

### OL 명시 비교

실제 공개 catalogVersion에 따른 후보 89개를 확인했다. 합성 계정의 실제 present T10 앨리스 head/1만 대상이며 같은 옵션·같은 값은 제외됐다. StatAtk 양수 tier 전체(현값 제외), StatChargeTime 음수 tier 전체가 이산 원천 목록과 일치한다. 방어/명중원·비상성 원소 피해 등 무효과 후보가 없다. 양수 차지값·동일 줄 중복 요청·absent 줄은 각각 400과 해당 안전한 오류 코드를 반환했다.

StatAtk **+0.0547**, StatChargeTime **-0.0609**를 각각 새로운 실험으로 180초 전투 2회 전체 재실행하고 팀 평균 차이·독립 Welch CI를 검산했다. baseline run을 재사용하지 않았으며 합성 원본 snapshot은 최종까지 불변이다. 비교 verdict는 두 건 모두 **unverified_design_or_input_difference**, gameVerified=false다. holdout orchestration이 미연결된 상태를 개선 확정·게임 추천·비용 효율로 승격하지 않는다.

## 자동튜닝 미완료 조사와 수정 담당

**안전 fallback은 통과했지만 자동 최적화는 수용하지 않는다.** 최초 실제 API baseline은 worker1/chunk1/benchmark_budget_cpu_fallback/not_measured였다. 후속 baseline resume에는 실제 측정 캐시의 worker2/measured_cache가 사용됐다(`selection-audit.json`). 추가 1프레임 실제 API는 캐시 재사용 및 DEF30925→30926이라는 통제된 입력 변경 시 입력/실행 fingerprint 변경과 재측정을 확인했다. 이 단일 프레임 변경은 캐시 키 검사이며 자동 DEF 전환 구현이나 게임 현상 재검증이 아니다. 합성 정책 probe에서는 장치/driver/runtime hash, engine/rules/workload/자원 상한 차이의 키 무효화를 따로 검사했다. 다른 실제 PC/드라이버 변경 실측은 아니다.

원인 분리:

1. `ExecutionPolicy.Select`는 준비 완료 후 **전체 10초** token을 시작하고 full 180초 warmup 1회를 먼저 수행한다. 준비 복원 자체는 밖에 있다. probe에서 Prepare 복원 약5258ms는 튜닝 예산과 별도 관측이다.
2. 두 독립 Select 호출 모두 warmup만 실행하다 취소됐다. 각 warmup은 약10083ms/10257ms 뒤 OperationCanceledException, 완료=false. worker1/2 후보 호출 수는 **0**이었다. 선택은 worker1/not_measured이고 불완전 warmup은 정상 표본/측정 캐시로 저장되지 않았다. 근거는 wrapper가 실제 PreparedCompute.Run의 phase/index/완료/예외/token을 기록한 것이다.
3. 코드상 warmup을 통과해도 후보는 worker1→2→4… 순서이며 각각 workers×2 전투 **묶음 전체 완료** 후에만 측정으로 인정된다. 후보별 예약 예산이나 최소 측정 기회가 없고, 남은 시간이 부족하면 완료된 일부 호출도 해당 후보 측정으로 인정되지 않는다. 이번 두 관측의 직접 중단 원인은 후보 배정 이전 warmup 예산 소진이다.
4. JIT/tiering은 warmup 안에서 발생할 수 있지만 JIT event trace를 수집하지 않았으므로 원인을 JIT 하나로 확정하지 않는다. 같은 두 구간의 프로세스 CPU 시간은 약3141ms/2844ms로 벽시계 10초와 달랐다. 이는 시간 예산이 계산량만의 함수가 아님을 보여주며 OS 스케줄링/전력/공유 호스트 영향의 세부 비율은 미확정이다. 다른 benchmark 프로세스는 실행 전 조회에서 발견되지 않았지만 계속된 독점 상태를 보장하지 않으며, 사전 단독 측정 합의가 없으므로 속도 개선율·최적 worker 비교를 하지 않는다.

**Q-TUNE-1 / 담당 B-CPU(필요 시 E-CPU 협업):** 10초 안에 warmup이 끝나지 않는 공개 5인 입력에서 선택 후보를 한 번도 평가하지 못한다. 최소 재현은 아래 Probe를 별도 프로세스에서 실제 prepared-synthetic.json/hardware.json과 함께 실행하는 것이다. 제품 변경은 하지 않았다.

수정 수용 조건: 워밍업/후보별 단계·완료 수·예산 소진 사유를 관측 가능하게 하고, 준비/JIT와 후보 비교의 예산 정책을 분리하거나 측정 가능한 제한적 정책을 명시한다. 후보별 측정 기회를 보장하지 못하면 최적화 성공으로 표시하지 않는다. 전체 상한·취소·메모리 보호, incomplete 제외, fallback 사유·not_measured 유지, 버전/입력/장치 변경 캐시 무효화가 유지돼야 한다. 단독 측정 구간에서 대표 입력의 **완료 표본으로 실제 선택과 캐시 재사용**을 입증한 뒤 자동 최적화 수용을 재판정한다. 단순히 예산 숫자를 늘렸다는 이유로 수용하지 않는다.

## GPU·미완료·후속 조건

실제 hardware API는 inventory와 GPU 실행을 분리했고 모든 발견 GPU는 eligible=false/runtimeStatus=not_implemented였다. auto의 실제 결과 backend=cpu/fallbackReason=gpu_unavailable, 강제 GPU는 실행 전 409였다. full-battle GPU와 GPU 실행 실패 후 CPU retry는 미구현·미검증으로 유지한다. CPU 성공을 GPU 성공으로 표현하지 않는다.

1천/1만/5만, 장시간/전후 속도 비교, 다른 PC·외장 GPU 실측, 실제 사용자 덱, 브라우저 UI, 자동 holdout 추천, 게임 영점/자동 DEF 전환, 배포는 이번 미실행이다. 대량 측정은 Director가 타 담당과 단독 시간대를 확정하고, 튜닝 단계 관측/버전·입력·자원 상한을 고정한 후 별도 후속 지시에서만 착수한다.

## 재현 명령·실패 이력

```powershell
& '<python>' tests/single_deck_compute_qa/run_small.py --source-data '<공개 dataRoot>' --dotnet '<dotnet>'
& '<python>' tests/single_deck_compute_qa/run_edges.py --source-data '<공개 dataRoot>' --dotnet '<dotnet>'
& '<dotnet>' build tests/single_deck_compute_qa/Probe/Probe.csproj -c Release -p:RestoreConfigFile=nuget.config -p:NuGetAudit=false
& '<dotnet>' tests/single_deck_compute_qa/Probe/bin/Release/net10.0/Probe.dll '<새 자기 artifacts>' '<새 합성 prepared-synthetic.json>' '<그 실행 hardware.json>'
& '<python>' tests/single_deck_compute_qa/test_oracle.py
```

Python은 기존 codex runtime Python, dotnet은 기존 원본 `.tools/dotnet/dotnet.exe`를 실행했다. SDK 실행은 원본 사용자 EXE 실행이 아니다. DOTNET_CLI_HOME은 검수 `.tools/dotnet-home`, NuGet은 기존 package 캐시다. Probe 빌드도 경고0/오류0 (`probe-build-b7a38f1825124f0e8872cb9e6b3005cd/build.log`).

첫 `small-45af2400a025`는 날짜가 바뀐 실행 중단 구간에 상태 조회 RemoteDisconnected로 중단됐다. 서버 로그에 원인을 확정할 추가 오류가 없어 제품 결함으로 단정하지 않는다. 원본 공개12개 hash 불변, 자기 서버 정리 후 새 경로로 실행했다. 이 최초 summary의 running은 중단 시점 기록이며 통과가 아니다. 러너는 이제 중단 시 aborted를 기록한다. 두 번째 실행의 QA null 기본값 문제도 위처럼 원본 실패 기록과 재분석을 함께 보존했다.

이번 확정 QA 커밋은 이 기록과 QA 소유 도구만 포함한다. Director에게 범위별 판정·자동튜닝 Q-TUNE-1·결과 커밋·보고서를 기존 일반 터미널로 한 번 전달한다. 입력 접수는 통합·배포 승인 또는 제품 전체 완료가 아니다.

---

# 이전 준비 기록 — 2026-09-15 (아래 대기 상태는 역사 기록)

**독립 수용 도구·fixture 준비 완료, 제품 수용 미판정.** CPU/GPU/배치/Analysis의 확정 구현 커밋은 아직 전달되지 않았다. 준비 중 Backend 계약 커밋 `f2327e5a99e9a6ce23e5377a53842fba63274331`이 생성되어 문서·DTO를 읽고 BatchResults 검사 adapter를 연결했다. 새 제품의 실제 CPU 배치, GPU kernel, OL 추천, 1천/1만/5만회 성능 실행을 완료했다고 보고하지 않는다.

## 기준·작업 상태

- Q-IMG는 `d67204bcc09e0b88d5cad84538c1a6e705419918`에서 검수·보고를 완료했다. 시작 시 이전 검수 프로세스가 없고, 미커밋 상태는 기존 untracked package-lock.json뿐이었다.
- 해당 HEAD가 공통 제품 기준 `a5ccba6663241e61783b509fc69098ad3c9ecef2`의 조상임을 확인하여 `git merge --ff-only`로 반영했다. 기존 조사·검수·분기 커밋이 모두 보존됐다. reset/checkout/stash 없음.
- Director 지시서 `single-deck-compute-assignments-2026-09-15.ko.md` 전체, 공통 기준·계약·Q 절, README, implementation-plan(P06/P08/P09 포함), p04-team-burst, damage-calibration-analysis를 UTF-8로 읽었다. 통합 후 새 AGENTS.md와 갱신 README도 읽었다. 시작 전 상위 디렉터리에는 적용 AGENTS.md가 없었다.
- 제품/Backend/Engine/Analysis/UI를 수정하지 않았다. 이번 소유 산출물은 `tests/single_deck_compute_qa/**` 및 본 보고서다. 공용 solution/project/package-lock 수정·커밋 없음.

## 실제 만든 검사

| 산출물 | 역할 |
|---|---|
| `oracle.py` | 하드웨어 선택 증거, 최신 attempt 집계, 독립 통계, 통제 조건 엔진 비교, OL holdout, portable 결과 구조의 독립 판정 |
| `test_oracle.py` | 정상 fixture와 손상·오분류·중복·미확정 입력을 판정기가 탐지하는지 검사. 실제 CLI 실행/입력 hash 보존/종료 코드도 포함 |
| `check_evidence.py` | 읽기 전용 QA 증거 JSON 검증 CLI. 항상 새 자기 artifacts에 결과를 기록하며 종료 0을 제품 수용으로 표현하지 않음 |
| `backend_v1.py`, `test_backend_v1.py` | 확정 f2327e5의 camelCase BatchResults 페이지 검증과 합성 wire 회귀. 확정 route 목록 보존 |
| `fixtures/portable-synthetic.json` | 합성 Windows/CPU 선택/측정 구조 예제. 표시된 수치는 실측이 아님 |
| `fixtures/batch-zero-synthetic.json` | 정상 완료 피해 0과 실패·취소를 구분하는 합성 fixture |
| `acceptance-plan.json` | 하드웨어/엔진/배치/통계/OL/성능 단계와 실제 미실행 상태 |

**portable/batch-zero JSON들은 QA 내부 정규화 증거 형식이다. Backend wire DTO/route를 정의하지 않았다.** Backend `docs/single-deck-compute-contract.ko.md`는 준비 착수 시 없었지만 후속 확인에서 커밋 f2327e5가 생겼다. 해당 커밋의 문서 전체와 `src/Nikke.Contracts/Compute.cs`를 읽어 별도 `backend_v1.py`를 연결했다. 커밋은 계약 2파일만 포함하며 제품 구현 완료가 아니다. 미커밋 Backend 파일을 제품으로 가져오지 않았다.

wire adapter는 확정 GET results 응답의 고정된 전체 페이지를 받는다. offset/limit, 조회 중 바뀐 BatchStatus, 유효 index 중복, 잘못된 runId, 미래 attempt, 순서가 바뀐 5인, phase/input/backend 혼합, 실제 합계·개수를 검사한다. **재개 후 이전 세대의 이미 유효한 index는 보존**하므로 모든 row의 attempt를 현재 배치 attempt와 같게 강제하지 않는다. 결과 API에 실패 attempt 이력이 없으므로 이를 조작해 복원하지 않으며 이력/저장 복구 검증은 실제 API 실행 후 별도 수행한다. GPU 상태 문자열 enum/정밀 portable exporter/Analysis CI는 구현 확인 후 연결한다.

하드웨어 검사는 가용 CPU 병렬도/메모리 상한, 불명 topology null, Intel/AMD/NVIDIA 합성 다중 GPU, driver/runtime/FP64/kernel/수치/분포/전체 시간 검증 누락, 탐지 timeout/예외/권한 거부/원격 연결 해제, 장치 ID 중복, stale 캐시를 포함한다. GPU 이름 발견만으로 eligible을 허용하지 않고, 강제 GPU 불가 시 실행 전 오류와 auto CPU 사유를 구분한다. 이 검사는 **탐지 결과의 합성 판정**이며 해당 vendor 하드웨어 또는 실제 timeout 프로세스를 검증한 것이 아니다.

배치 검사는 runId+attempt 충돌을 거부하며 이전 attempt는 명시적 discarded로만 남긴다. 실패 GPU attempt를 폐기한 뒤 CPU attempt를 수용하는 fixture와 stale 결과를 이중 집계하는 결함 fixture를 대조한다. 실패·취소의 damage=null과 정상 완료 0, 부분 결과, 5인 합계, 입력/수치 모델/backend 혼합, pilot과 final 혼입을 검사한다. crash/restart와 bounded writer의 **실제 저장 복구·부하 검사는 아직 미실행**이다.

통계 기준은 독립 Fraction 산술의 평균/표본분산, HF7 분위수, 엄격한 컷 초과(>)와 Wilson 95% CI다. 빈 표본은 null, n=1의 표본 SD는 null이다. `2^60+[0,1,2]`의 SD=1을 확인하여 큰 피해의 상쇄 오류를 탐지한다. 팀 분위수를 개인 분위수의 합으로 대체하는 사례도 거부한다. 실제 Analysis의 평균 CI·분위수 규격이 미수신이므로 `meanCi=null / pending_analysis_contract`를 명시했다. HF7/Wilson을 제품 계약으로 강제하지 않으며 다른 명시적 방법은 별도 독립 기대값으로 연결한다.

OL 준비 검사는 원본 hash 불변, 탐색/기준 최종/후보 최종 run 집합의 상호 분리, 독립 표본 설계, 전투 전체 재실행 여부, 0을 포함하는 차이 CI의 우열 미확정을 검사한다. 수치가 양/음인 CI의 판정 부호도 확인한다. 실제 부위·줄·유효 옵션 생성과 엔진 재평가, 독립 차이 CI 계산은 제품 연결 후 검사한다. 모듈 비용 효율을 창작해 채우는 증거는 거부한다.

## 사전 정확성·분포 수용 기준

1. 비확률 고정 조건 및 명시적 테스트 전용 RNG 스트림에서는 피해·발사·명중·크리·재장전·버스트·잔탄·같은 프레임 이벤트 순서·난수 소비 수가 정확히 일치해야 한다. 입력 전후 hash도 같아야 한다. 로그 on/off 및 최적화 전후를 비교한다. 테스트 스트림을 생산 경로 고정 seed로 도입하지 않는다.
2. 실제 확률 전투의 순차/병렬·CPU/GPU 결과는 독립 표본으로 비교한다. 단순히 차이 검정에서 유의하지 않다는 이유로 동등하다고 하지 않는다. 사전 고정 범위의 Hoeffding 평균 차이 구간과 두 DKW 누적분포 띠를 사용한다. 36개 지표(팀+5인 × 피해/발사/명중/크리/재장전/버스트), 지표당 2개 gate에 family alpha=0.05를 배분한다. 두 표본 반경 합을 사용하므로 보수적이다.
3. 평균 차이 구간 전체가 사전 평균 허용폭 안에, CDF 거리의 보수적 상한이 0.05 안에 들어와야 분포 gate를 통과한다. `equivalent()`는 bounds와 mean_margin을 필수 입력으로 받는다. 평균 허용폭은 평가 표본을 보기 전에 확정한 기준 평균의 0.1%를 초기 목표로 하되, 기준 0이면 비확률 정확 비교로 분리한다. 엔진 지원 입력에서 정당화할 수 있는 각 지표의 상·하한 및 pilot 기준을 **최종 평가 전에 별도 preregistration으로 고정**한다. 아직 실제 덱 입력이 없으므로 임의 피해 상한 숫자를 만들지 않았다.
4. 이 bounds/허용폭 등록이 없거나 구간이 넓으면 미판정이다. 5만회에서도 미판정일 수 있으며 표본을 계속 엿보다 통과 시점에 중단하지 않는다. 고정-N 평가를 새로 설계하면 새 실험 ID와 사전 기준으로 분리한다. 이번 합성 검사는 식·gate 동작을 검사할 뿐 표본 독립성 자체를 증명하지 않는다. 난수 상태 공유는 엔진 병렬 상태 검사로 따로 검증한다.
5. GPU는 실제 장치의 kernel 실행·double/floor/round 경계·5인 분포·전송/준비/회수 포함 전체 시간 증거가 모두 있어야 승격한다. CPU에서 계산한 값을 GPU 성공으로 표시하거나 실제 미보유 GPU를 합성 결과로 승격하지 않는다.

## 실제 실행과 근거

공통 기준에서 기존 `EngineIntegrationExampleTests` **2개 통과, 실패/skip 0, 테스트 기간 23초**. 로그 on/off 결과·난수 소비 일치, JSON round-trip, 명시적 수집 0과 미수집 구분을 검증했다. 출력은 새 `artifacts/single-deck-qa/baseline-152926643101428598b4623dbc4e1f3f/`의 test.log, baseline.trx, engine-example-* 파일이다. 합성 입력의 실제 기존 엔진 실행이며 요청된 실계정 5인 덱 또는 최적화 후 제품 검증이 아니다. fixture는 고정 DEF=10, 테스트 전용 RNG, 180초다.

그 새 엔진 출력에 기존 독립 피해 산술 도구를 실행해 **종료 0**을 확인했다. 근거: `artifacts/s3/20260915T015516Z-57fd1a5e0c0c4dd5913caef8d1ca41f6/analysis.json`. 과거 저장 로그를 다시 실행한 것처럼 인용하지 않았다. 피해 산술·종료 경계 검증은 게임 관측값 대조가 아니다.

최종 QA 자체 회귀 결과 및 보존 증거는 아래 완료 기록에 남긴다. 최초 29개, CLI/엔진/OL predicate 추가 후 32개 실행은 모두 통과했다. 32개 실행 근거 `artifacts/single-deck-qa/oracle-69c4f0dad57e4e0fa7c9ef95489fb0f0/summary.json`과 tests.log. 이후 OL CI 부호 판정 강화의 최종 재실행도 별도로 기록한다. 합성 단위 테스트와 실제 제품 검증을 합산하지 않는다.

```powershell
$taskQaPython = 'C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $taskQaPython tests/single_deck_compute_qa/test_oracle.py
& $taskQaPython tests/single_deck_compute_qa/check_evidence.py tests/single_deck_compute_qa/fixtures/portable-synthetic.json --kind portable
& $taskQaPython tests/single_deck_compute_qa/check_evidence.py tests/single_deck_compute_qa/fixtures/batch-zero-synthetic.json --kind batch
& $taskQaPython tests/single_deck_compute_qa/check_evidence.py tests/single_deck_compute_qa/fixtures/backend-results-v1-synthetic.json --kind backend-results-v1
# 기존 엔진 기준 테스트: NIKKE_E2_EXAMPLE_ROOT는 새 자기 artifacts 경로
& '<dotnet>' test tests/Nikke.Core.Tests/Nikke.Core.Tests.csproj -c Release --filter 'FullyQualifiedName~EngineIntegrationExampleTests' -p:RestoreLockedMode=true -p:RestoreConfigFile=nuget.config --logger 'trx;LogFileName=baseline.trx' --results-directory '<새 baseline 경로>'
& $taskQaPython tools/damage-calibration/analyze.py '<새 engine-example의 result.json>'
```

실제 dotnet은 기존 `.tools/dotnet/dotnet.exe`, DOTNET_CLI_HOME은 검수 `.tools/dotnet-home`, NuGet 캐시는 기존 것을 사용했다. 별도 서버·GPU benchmark·전역 설정·드라이버 설치 없음. CLI 정상 종료는 `productAcceptance=not_evaluated`를 유지하며 손상 입력은 종료 2다.

## 후속 순차 부하 실행 계획

- 확정 제품과 Backend 계약 수신 → 자기 QA 커밋 보존 FF/일반 merge → 코드/단위 회귀 → 허용 입력 준비 → 취소/재개/복구 소규모 실제 API 검증 → 담당자들과 단독 측정 시간 합의 순으로 진행한다. 동시에 다른 benchmark가 실행되면 비교 측정을 시작하지 않는다. 지금은 부하 시간을 예약했다고 주장하지 않는다.
- 실제 덱 순서: 리타·블랑·앨리스·누아르·모더니아, 400, 기본 180초. snapshot/data/engine/rules/build/tactic fingerprint와 현재 저장 택틱을 기록한다. 원본 snapshot을 복제할 수 없으므로 Backend의 허용된 불변 입력 adapter가 필요하다. 이번 합성 baseline의 DEF=10을 실제 덱 정책으로 넘기지 않는다.
- 현행 고정 DEF 요청값을 입력 provenance에 명시한다. 실측 30925→31784 및 20억 현상을 재검증하거나 자동 DEF 전환을 이번 성능 경로에 추가하지 않는다. 실전 영점 미검증은 계속 구분한다.
- 1천 pilot, 별도 1만 고정-N 본 평가, 별도 5만 지속 실행 순서. warmup/pilot/선별 표본은 최종 집계에서 제외한다. 단일 장치의 cold/warm, 전후 동일 조건을 기록하고 실제 유효 표본수/전체 벽시계 시간으로 run/s를 계산한다. 예상 완료 시간은 실측과 구분한다.
- 할당/GC/최대 메모리/저장 크기/UI p95 응답/취소 지연을 수집한다. 수집 불가 metric은 null+사유다. workload·driver/runtime/kernel/정책 fingerprint 변경이나 다른 PC의 캐시 복사 시 재평가한다. 실제 계측 exporter는 Backend 확정 portable 규격에 연결한다.
- 반응성 초기 QA 목표는 취소 API 응답 2초 이내, 화면 상태 polling p95 500ms 이내, 작업 취소 완료 5초 이내다. 메모리는 명시된 상한을 검증하고 고정값을 제품에 심지 않는다. Backend의 취소/메모리 계약과 불일치하면 실측 전에 조정·기록한다. 이 목표를 아직 제품 SLA 또는 측정 결과로 발표하지 않는다.

## 미완료·승격 범위

준비 도구·합성 판정기 및 확정 계약의 BatchResults adapter만 완료다. 실제 하드웨어 탐지/튜닝/CPU fallback, 새 summary 최적화 전후 정확성/성능, 실제 배치 API/저장 crash 복구/취소·재개/UI, 실제 1천/1만/5만회, GPU kernel·외장 GPU 실측, 실제 Analysis 평균 CI/OL 후보 실행은 **미실행·미연결**이다. 사용자 계정/장비를 바꾸거나 복제하여 공백을 메우지 않았다. 게임 검증 완료 추천·GPU 지원 완료·성능 개선 수치·배포 완료를 주장하지 않는다.

원본 계정 DB/세션을 읽거나 복제하지 않았고 원본 캐시를 갱신하지 않았다. 5180/5181에 요청·종료하지 않았으며 EXE/바로가기/배포 경로를 수정하지 않았다. 실제 사용자 EXE 경로는 AGENTS.md의 원본 `C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe`다. 새 워커/Run/Dispatch/lifecycle 생성, worker_done, 원격 push 없음. 최종 결과 커밋/본 보고서/준비 판정/의존성을 Director의 기존 터미널에 한 번 전달한다.

## 완료 기록

- 최종 **39개 통과 / 실패 0 / 오류 0, 종료 0**. QA 핵심/CLI 32개 + f2327e5 wire adapter 7개다. `artifacts/single-deck-qa/oracle-fa19fa30aeea42608d418911ebea7ff6/{summary.json,tests.log}`. 실행 당시 제품 HEAD=a5ccba6이며 최종 QA 코드가 미커밋 상태에서 실행된 뒤 결과 커밋에 포함된다. 모든 fixture는 synthetic이며 productAcceptance=not_evaluated다.
- OL CI 부호 강화 후 wire 연결 전 32개도 `oracle-7e7e121e7dcc4335960e1266d1303801/`에서 통과했다. 앞선 실행/증거를 덮어쓰지 않았다.
- 보호 파일 읽기 대조 `artifacts/single-deck-qa/guard-a128a20f6c9c4ab8bc855ef681c9ddf6/{before.json,after.json,ports.json}`: package-lock·현재 원본 EXE·공개 presentation 3개 manifest의 **5개 hash 모두 대조 구간에서 불변**. 계정 DB/세션 또는 원본 전체 파일을 hash한 증거로 확대하지 않는다. 원본 캐시는 갱신하지 않았으며 이 보호 대조에서 manifest만 읽었다.
- package-lock SHA-256은 시작 시와 끝 모두 `2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767`, 현재 원본 EXE는 `37095189856789568f4133a20b4f40bcda8509a7a8f8ddd4fb7ffdda0de02214`다. 과거 Director EXE hash와 혼동하지 않는다. 관찰 당시 사용자 listener는 5181/PID 26896이며 5180은 없었다. 본 작업은 두 포트에 연결/기동/종료하지 않았다.
- `git diff --check` 확인 후 QA 소유 파일만 커밋한다. 기존 untracked package-lock은 제외한다. Director 전달은 **독립 준비 완료 / 확정 제품 검수 대기**이며 제품 통과 보고가 아니다. 일반 terminal list/read 확인 후 한 번 전달하고 새 artifacts의 영수증을 보존한다.
