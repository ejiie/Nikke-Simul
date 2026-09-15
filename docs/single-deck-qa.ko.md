# Q-CPU/GPU 독립 검수 준비 — 2026-09-15

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
