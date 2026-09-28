# Q-F32 — 단계 A 및 B1 독립 수용 (2026-09-28)

## 최신 판정 — 단계 B1

**B1 API·wire·저장·버전/캐시 분리 수용 통과. 자체 API 검사85/85, 후속 캐시·저장 입력 검사9/9. 차단 결함 발견0. B2 브라우저/UI는 Director 별도 통지 대기. Q-CPU-10K 및 부하 측정은 계속 보류.** 아래 단계 A 기록은 당시 근거로 보존하며 A 숫자를 B1 검사에 합산하지 않는다.

시작 HEAD `cdca644`, status는 미추적 package-lock.json뿐. 최신 Director 배정서 전체, Backend 확정 wire의 I-BE schema3/compute 역사 분리 절 및 I-BE 보고서 전체를 UTF-8로 읽었다. Backend **`74ca24fc9b242b6268856f82a4c722f2e57f9b9c`**를 일반 merge해 이전 QA를 보존했다(충돌 없음). Backend의 `check_client_f32_api.py`와 Backend 테스트를 실행·import하거나 판정 기대값으로 재사용하지 않았다.

새 QA `check_f32_b1.py`가 실제 HTTP 요청/응답·SQLite 저장을 검사한다. 단일 히트 기대값은 단계 A에서 만든 독립 Fraction/binary32 기준으로 원요청에서 계산했다. 통계는 자기 기존 독립 Student/HF7/Wilson 도구를 사용한다. `F32Boundary`는 실제 BatchStore 쓰기 거부와 동일 하드웨어의 버전별 tuning key, 실제 ExecutionPolicy 캐시 수용을 호출하는 QA 전용 probe다. 제품 메서드 반환은 검사 대상이며 그 값을 스스로 정답으로 삼지 않는다.

격리 API 포트 **63740**, 자기 새 dataRoot `artifacts/single-deck-qa/f32-b1-88f22794209a/data`. 실행 PID19764→재시작8976, 둘 다 자기 스크립트에서 종료·wait 완료. 공개12파일은 원본을 다시 읽지 않고 기존 자기 `load1000-3db71912a601/data` allowlist에서 복사했다. **계정 DB는 새 합성5인으로 생성**했으며 원본/기존 계정DB나 세션을 복제하지 않았다. 새로운 API/QA probe Release 빌드는 각각 경고0/오류0이다.

### B1 실제 결과

| 범위 | 독립 근거와 판정 |
|---|---|
| v3 정상·기본·네 후보 | 100×2×(1−.25)=client150, 과거3개100; 각 정책 명시선택, 후보 순서·선택audit10항·원요청 일치. 2^24 선감산도 독립 일치 |
| v2 명시 변환 | 원본 input 보존, schema2→3 및 method/defaults(1,0) 일치. 새 rate가 들어간 v2는400 |
| import·저장·GET | 과거 comparison artifact의 원후보/관측/메모 전체 sourceArtifact 보존, 새ID·선택정책·conversion 확인. 새 응답 재import도 새ID이며 기존 기록 불변. 파일=GET=응답, API 재시작 후 v2/import 조회 동일 |
| 십진 문자열 | raw1450·exact17 출력은 문자열, 공격력132. exactAmount9007199254740993을 무손실 공격력 문자열로 보존, client exactDamage 독립 일치 |
| 불가 후보 | 큰 정수에서 과거3후보 unavailable, damage/residual/relativeError=null, terms=[], 이유 존재. 불가정책 선택은400이며 피해0/자동fallback/저장 없음 |
| 제약 오류 | 소수ATK/DEF/flat, 과정밀rate, raw불일치, unsafe number, overflow, 알 수 없는 필드/정책/schema, decimal 문자열의 지수·소수·공백·범위초과 거부. 100.000000000000000001 / 1e−400 / rate0.01400000000000000001 원문도400. 오류요청 전후 저장 파일 수 불변 |
| compute hitOverrides | 각조건1회: default/legacy/statDamageRatio2/defenceRatioRate.25/runtime raw1450/runtime rate.145/exact flat100. 정상7배치, schema3/summary2/level400/DEF30925/저장택틱 확인, override 실제 준비 payload 보존 |
| fingerprint·튜닝 키 | 7물리 입력·7실행 키 각각 구분. 같은rate라도 raw존재 여부가 다르면 fingerprint 구분. 원조건 재요청은 동일 키·validated_policy_cache. 새7조건 모두cache miss |
| 정상통계·튜닝 제외 | 각 배치 정상n1, 팀=5인합, 독립 팀·5인 통계 일치. warmup/후보튜닝 호출은 결과n에 미포함. 재시작 뒤도 각n1 유지 |
| 역사·구결과 | 이전 자기 Q-LOAD-1000에서 실제 생성된 cpu-summary.1 calibration20개를 읽기 전용으로 읽어 **compute 행만** 격리DB에 이관. 구20개 payload 그대로 GET 조회, schema2/summary null 유지. resume409 engine_or_rules_version_changed |
| 새 결과와 혼합 거부 | 구 RunSummary의 식별자만 신규배치에 맞춘 뒤 원래 구fingerprint로 실제 BatchStore.Write 호출→invalid_run_summary, 결과수0. 새 실제엔진1회 결과만 저장 후 API 통계n1. 구 통계는별도n20으로 독립 검산 |
| baseline·오염 | override가 다른 baseline 연결400, 허용 외 override/5인 밖 ID400. 저장payload의 statDamageRatio만 변조하면 prepared_input_fingerprint_mismatch로 복구 거부 |
| 구캐시·새캐시 | 실제 자기 구튜닝 cache파일을 별도 cache-probe에 복사한 상태에서 현재 prepared Select는miss/measured, 두 번째는validated_policy_cache. 구파일들 내용 일치·신규키와 분리. 동일 hw/자원에서 engine만/rules만/workload만 바꾼 키도 각기 다름 |

새 실제 정상 전투 결과는 API7변형+동일입력 재요청1+저장경계 probe1 = **9개**다. 튜닝 호출은 별도이며 배치 통계에 넣지 않는다. 모두600프레임/10초 합성 전투, worker1이다. 구20개는 조회만 했고 재실행하지 않았다. 자동버스트 지연은 입력의 기존 기본범위(1~10프레임)를 유지했으므로 조건별 단일 피해 숫자를 효과 크기·성능 비교로 쓰지 않는다. 특히 raw/rate 물리값이 같아도 별도 호출의 전투 피해가 항상 같다는 주장을 하지 않는다.

### B1 근거·재현·보존

확정 근거 루트 **`C:/Users/user/orca/workspaces/Nikke-Simul/검수/artifacts/single-deck-qa/f32-b1-88f22794209a/`**:

- `summary.json` API85건, `http.json` 원요청·응답·오류, `api-*.log`.
- `supplemental-audit.json` 후속9건 및7배치별 실제피해/전체fingerprint/튜닝키/n. `*-prepared.json`, `*-batch.json`.
- `old-history-source.json`, `old-run.json`, `boundary.json`: 구20개 provenance 및 실제쓰기 거부, 신규n1.
- `cache-probe-result.json`, `cache-probe/`: 구캐시존재 하의 실제 miss→reuse와 변조복구 거부. `source-hashes.json`, `preservation.json`.
- 빌드 로그: `artifacts/single-deck-qa/f32-b1-build/api.log`, `boundary.log`.

재현: API와 `tests/single_deck_compute_qa/F32Boundary/F32Boundary.csproj`를 Release 빌드 후 `python tests/single_deck_compute_qa/check_f32_b1.py --dotnet <dotnet>` 실행. 현재 도구는 자기 기존 공개 fixture/구 calibration 경로를 명시적으로 고정하며 없으면 중단한다. 다른 PC에서 사용자 원본 자료를 추정해 찾거나 복제하지 않는다. 이 실행은 우선API85건을 완료한 뒤 캐시 probe/읽기 전용 추가판정9건을 수행했다. 최종 도구는 같은 순서를 한 번에 실행할 수 있도록 연결했고, 후속9건은 `--audit-existing <evidence>`로도 재검산한다. 최종 연결 이후 전체API를 불필요하게 다시 실행하지 않았다.

추적 제품 src/apps/scripts/tools-data-pipeline 직접수정0(승인merge 수신 제외). 기존 QA/단계A artifacts 보존. package-lock SHA256 `2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767` 전후동일·커밋제외. 공개12파일 hash변경0, 실제 구합성compute DB 전후hash동일. 사용자 원본 계정·세션·캐시·EXE·바로가기·5180/5181 접근/변경/종료없음. 타worktree 편집/배포/push/새worker/Run/Dispatch/lifecycle없음.

**미완료:** B2 브라우저/UI·피해로그/통계화면, 실게임·실측18점·실사용자덱·SW·GPU·성능/부하. Backend329통과나 이전A결과를 이번API 통과 수로 재사용하지 않았다. 제품 배포도 하지 않았다. Director에 B1 확정QA커밋/본보고서/독립근거/경계를 한 번 전달하고 B2 통지를 기다린다.

---

## 단계 A — 당시 독립 엔진 수용 기록

**판정: 단계 A 합성 산술·과거 정책 보존·기본 replay·소규모 병렬/취소 수용. 차단 결함 발견 0. 실게임 정확성·API/UI 종단 수용 아님. 단계 B는 Director 통지 대기.**

## 기준과 독립성

Director의 `client-f32-integration-assignments-2026-09-28.ko.md` 전체와 선행 H-F32/H-SRC 배정, client 공식·사용자 결정, 엔진 보고서(후속 연결·미실행·질문 포함), Backend 원천 조사 보고서를 UTF-8로 끝까지 읽었다. 시작 `git status`는 미추적 package-lock.json만 있었다. 자기 QA `44cbe5d` 및 이전 커밋을 보존하여 엔진 `5ced15a`(구현 `53b3d10`)를 일반 merge했다. 충돌 없음, merge `adb7d05`.

엔진의 golden JSON·oracle Python·엔진 테스트 기대값을 실행하거나 재사용하지 않았다. 새 QA `check_client_f32.py`는 **Fraction 정확 유리수 → 지수/24비트 가수 nearest-even 양자화**로 각 binary32 연산을 직접 정의한다. 최종 피해는 별도의 유리수 half-away 반올림과 최소1을 적용한다. 엔진의 struct 기반 oracle 구현과 독립이며, 기대값 생성 시 제품 함수를 호출하지 않는다. 알려진 1/1.5 비트, 2^24 tie 및 subnormal tie, 양·음 x.5를 자체 점검한다. 고정 난수는 QA 산술 fixture 생성용이며 제품 RNG를 변경하지 않는다.

기존 `tools/benchmarks/engine/fixture.json`은 요구된 공통 **입력**으로만 사용했다(SHA256 `e14a48955bdbc42f15b6e361ef2ab54a5dc66b5c3df46484346b5a3d2cf40f9b`). 엔진이 기록한 replay 결과 파일은 읽거나 가져오지 않았다. 전환 전 코드는 `git archive 53b3d10^ src/Nikke.Core src/Nikke.Engine`로 자기 artifacts에 추출해 별도 빌드했고, 동일 QA replay harness로 실제 실행했다. git checkout/reset/stash, 다른 worktree 생성·편집 없음.

## 실제 검사 결과

| 독립 검사 | 결과 |
|---|---|
| 산술·경계·예외 | **326/326 통과** |
| replay·과거 결과·집계·병렬·취소 판정 | **54/54 통과** |
| 기본 client 전체 히트 독립 재계산 | **7,979/7,979 일치** |
| 현재 산술/현재 replay/전환 전 replay Release 빌드 | 각각 경고0·오류0 |

산술 검사는 `ClientFloatDamage`와 `HitCalculator.CalculateClient`의 attack/defence/difference/피해 및 base·B·extra·reduction·defenceFactor·최종곱의 **binary32 비트**를 비교했다. 직접 rates와 HitContext 연결 경로를 별도로 검사했다.

- 2^24 전후 해상도와 16777217−16777216=1의 long 선감산, long.MaxValue 인접 두 값 차이, 최종2^63 거부/바로 아래 float 허용.
- x.5 사사오입, 음수·0 결과의 최소1, defenceRatioRate 0/.25/1, statDamageRatio 0/.75/1/2, 비중립 charge/element/extra/reduction.
- 12개 직접 float 입력과 22개 HitContext double 입력 각각 NaN/±Inf 거부. float 중간 곱 overflow 및 long 변환 overflow 탐지.
- 공격력100·14.5%=115, −14.5%=85, 동일1.4% 두 그룹/중첩=103, 다른1.4%·1.3%=102, 음수 .5 tie, 고정량 후순위, exact long.MaxValue 전달. 중간 곱/총합/고정량 checked overflow, 소수 native/DEF/flat 및 과정밀·raw 불일치 거부.
- normal/skill/dot/sequential/distribution/true 및 활성/비활성 조건별 HitContext 변환을 독립 계산. 원천 의미 대응을 확정한 검사는 아니다.

## 합성 5인 180초 재현

native ATK100000, DEF30925, core=true, crit off, 수동 없음, I/II 지연1프레임, III 진입28프레임으로 고정했다. 실제 사용자 계정·스펙이 아니다. fixture의 명시 legacy를 default 실행에서만 새 `SkillReplayConditions` 기본값으로 교체하여 기본 정책이 client_f32임을 확인했다. 다섯 캐릭터별 로그는 같은 결정적 입력을 각1회 재실행해 수집했으며 각 로그의 complete/비절단 상태와 전체 합을 확인했다.

| 구성원 | 전환 전 legacy | 새 default client | 차이 | shots/hits 동일 |
|---|---:|---:|---:|---:|
| fixture-i | 302651627 | 302652598 | +971 | 1948/1948 |
| fixture-ii | 302651627 | 302652598 | +971 | 1948/1948 |
| 5004 앨리스형 합성 | 136253255 | 136253442 | +187 | 187/187 |
| fixture-iii | 302651627 | 302652598 | +971 | 1948/1948 |
| fixture-excluded | 302651627 | 302652598 | +971 | 1948/1948 |
| 팀 | **1346859763** | **1346863834** | **+4071** | 풀버스트9회 동일 |

팀합=구성원합=독립 산술 히트합. crit도0으로 불변. 일반 합성원 각각977히트는 동일,971히트는+1; 앨리스형187히트 전부+1이다. 예: (100000−30925)×2.5=172687.5는 binary32로 정확 표현되고 최종 half-away로172688. legacy는 base69075+core69075+floor(burst34537.5)=172687. 독립 재계산의 입력과 비트·구체 frame 사례는 replay-audit.json에 있다.

**과거 세 정책** legacy_term_floor/final_round_even/nested_floor 각각 전환 전 실제 실행과 전환 후 명시 선택 실행의 팀·전체 구성원 객체·풀버스트, 모든 히트의 frame/피해/누적피해가 정확히 같았다. 이 보존 판정은 중립 신규항인 해당 합성 입력 범위다. 비중립 statDamageRatio/defenceRatioRate를 무시하는 과거 정책을 동일 공식의 정밀도만 다른 후보라고 해석하지 않는다.

정책별 PreparedSkillReplay 동일 객체에서 병렬2회 결과를 상세 replay와 대조했다. 사전 취소, 1ms 타이머를 건 동기 실행의 OperationCanceledException, 취소 후 동일 prepared 재사용 결과를 확인했다. 취소 지연 성능 보장·대규모 race 스트레스 검증은 아니다. 성능 숫자/순위는 수집·비교하지 않았다.

## 근거와 재현

자기 근거 루트: `C:/Users/user/orca/workspaces/Nikke-Simul/검수/artifacts/single-deck-qa/f32-stage-a/`.

- `cases.jsonl`, `expected.json`, `actual.jsonl`, `arithmetic-audit.json`: 독립326건 원자료/판정.
- `current/`, `previous/`: 정책별 실제 replay·5인 히트 로그·parallel/cancel 결과. 이전 로그에도 제품 객체의 새 필드를 소급 삽입하지 않았다.
- `replay-audit.json`:54개 판정,7979히트 검산, 차이 분포·사례.
- `baseline.zip`, `baseline/`: 전환 전 Core/Engine만 분리한 실제 빌드 입력. `build-*.log`, `provenance.json`:빌드·고정 hash·보존 근거.

도구: `tests/single_deck_compute_qa/F32Probe`(제품 호출·비트 출력만), `F32Replay`(공통 전후 실행), `check_client_f32.py`(기대값과 판정). SDK는 기존 `.tools/dotnet/dotnet.exe` 읽기 전용 실행, CLI_HOME은 자기 worktree. Python 표준 라이브러리만 사용한다. 실행 순서:

```text
python tests/single_deck_compute_qa/check_client_f32.py generate <evidence>
dotnet build tests/single_deck_compute_qa/F32Probe/F32Probe.csproj -c Release
dotnet <F32Probe.dll> <evidence>/cases.jsonl  → <evidence>/actual.jsonl
python tests/single_deck_compute_qa/check_client_f32.py verify <evidence>
dotnet build tests/single_deck_compute_qa/F32Replay/Replay.csproj -c Release -p:EngineRoot=<QA root>
dotnet <Replay.dll> tools/benchmarks/engine/fixture.json <evidence>/current legacy_term_floor final_round_even nested_floor default
```

전환 전 archive 아래 probe에 동일 F32Replay 소스를 두고 EngineRoot를 archive 루트로 빌드해 previous에 과거3개 정책만 실행한다. 이후 `python .../check_client_f32.py replay <evidence>`. 최초 QA 프로젝트 상대참조 경로 오타로 빌드가 실패했으나 QA csproj에서 수정 후 위 최종 빌드 통과했다. 제품 결함으로 집계하지 않는다. 타이머 취소/재사용 검사를 추가한 후 현재 replay를 다시 실행했다.

## 보존·미판정·후속

제품 파일은 merge 수신 외 직접 수정0. package-lock.json SHA256 `2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767` 전후 동일·커밋 제외. 원본 계정/세션/캐시 복제·접근·편집·수집·동기화 없음. 원본 EXE·바로가기·5180/5181 접근/변경/종료 없음. 사용자 실행 경로는 계속 `C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe`. 이번 로컬 빌드는 배포가 아니다. 게임 바이너리/프로세스 분석, GPU,1천/1만/5만 부하, push/배포, 새 Run/Dispatch/하위 worker/lifecycle 없음.

단계 B의 Backend/UI 확정 커밋·wire 계약은 아직 통지받지 않았다. v2→v3, API 오류·후보4개, UI 피해 로그·통계, fingerprint/캐시·구결과 혼합 방지는 **이번 미실행/미판정**, Director 통지 후 별도 수용한다. 기존 엔진147 테스트 통과를 독립 수용 숫자로 재사용하지 않았다. 실측18점·실게임 관측·실제 사용자 덱·SW 단일타격 후속·GPU·전역 성능도 미판정이다. break/parts 의미와 statDamageRatio/defenceRatioRate 원천, 클라이언트 세부 저장·반올림은 보고서의 잠정 가설로 유지한다.

**Q-CPU-10K는 계속 보류.** 엔진 규칙/summary 버전이 바뀌었으므로 재개 시 입력·DLL·정책·예산을 새 기준으로 다시 고정해야 한다. 기존 배터리 창 승인이나 calibration을 재사용해 실행하지 않는다. 확정 QA 커밋·본보고서·근거·단계별 판정을 Director 터미널 재조회 후 한 번 전달하고 단계 B를 기다린다.
