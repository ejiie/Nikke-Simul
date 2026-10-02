# 단일 덱 compute 계약 — I-BE / client_f32 (2026-09-28)

**현재 보스 조건 확장:** 아래 F-COND-B 절은 거리/약점과 저장 모드 계약을 추가한다. summary는 `cpu-summary.3-boss-conditions`로 갱신됐다. 단일 hit schema3 wire와 수동 bool 입력은 그대로다.

현재 hit wire는 아래 **I-BE schema 3** 절이다. 이전 B-CPU·B-TUNE-1 절은 변경 이력을 보존한다. `final_round_even`을 명시한 기존 요청은 해당 과거 정책을 계속 선택하며, 새 요청의 기본값은 `client_f32`다.

기준 a5ccba6663241e61783b509fc69098ad3c9ecef2. C#의 확정 DTO 원본은 `src/Nikke.Contracts/Compute.cs`, JSON은 기존 Wire.Json camelCase다. 아래는 구현 연결 계약이며 GPU·통계 구현 완료 선언이 아니다. 추가 호환 필드는 허용하며 의미 변경은 버전 변경/보고가 필요하다.

## API

기존 localhost/동일 출처/X-Nikke-Token 정책을 그대로 사용한다.

| 요청 | 응답 |
|---|---|
| GET /api/compute/hardware | HardwareProfile (매번 현재 탐지, bounded timeout) |
| POST /api/compute/experiments | ExperimentRequest → BatchStatus, 202 |
| GET /api/compute/experiments/{id} | BatchStatus |
| POST /api/compute/experiments/{id}/cancel | BatchStatus |
| POST /api/compute/experiments/{id}/resume | BatchStatus, 새 attempt |
| GET /api/compute/experiments/{id}/results?offset=0&limit=100 | BatchResults; limit 최대 1000 |
| GET /api/compute/experiments/{id}/statistics?cut=... | StatisticsResult; Analysis 미연결 시 409 analysis_not_integrated |
| GET /api/compute/experiments/{id}/comparison | baselineExperimentId와 후보의 OlComparison; Analysis 미연결 시 409 |
| GET /api/compute/experiments/{id}/ol-candidates | OlCandidateCatalog: catalogVersion, candidates[{id,before,after,thresholdSensitive}], exclusions, gameVerified=false |

요청 예: `{ "snapshotId":"...", "characterIds":["...","...","...","...","..."], "conditions":{"roundingPolicy":"final_round_even","combat":{"durationFrames":10800,"enemyDefense":30925}}, "runs":1000, "phase":"final", "execution":{"requested":"auto"}, "useSavedTactic":true }`. conditions는 기존 SkillReplayConditions 전체 규격이며 기본 durationFrames=10800, synchro=400을 적용한다. 나머지 전투 조건은 기존 엔진 유효성 검사를 따른다. 저장 택틱은 현재 snapshot/편성과 일치할 때만 적용하고 stale은 거부한다. 명시 conditions와 최종 적용 입력을 fingerprint에 포함한다. durationFrames는 프레임(60Hz), 피해는 게임 피해 단위, 시간은 ms, OL value는 기존 normalized 비율이다(공증 10%=0.1). optionId는 presentation.overloadOptions의 definitionUid(예: StatAtk, StatChargeTime), slot은 head/torso/arm/leg, lineIndex는 1~3. StatChargeTime/StatAccuracyCircle의 value는 음수이며 원본 raw 부호 규칙을 유지한다. 캐릭터는 예시의 말줄임표를 실제 snapshot ID로 바꾼다. SG를 포함한 덱은 기존 pelletCoefficientPolicy를 반드시 명시한다.

Phase는 warmup/pilot/exploration/final. 통계 표본은 같은 phase/input/backend 의미만 집계한다. 튜닝 warmup은 결과 표본으로 저장하지 않는다. RecordLevel은 현재 summary만 허용한다. requested=auto/cpu/gpu. GPU provider가 full battle 정확성/self-test/실측을 통과하기 전 runtimeStatus=not_implemented, eligible=false; auto는 CPU fallback, 강제 gpu는 실행 전 409 gpu_unavailable. inventory의 이름은 사용 가능 판정이 아니다.

## 실행/저장 경계

IPreparedExperiment는 준비된 비공개 입력을 보유하고 Run 호출마다 전투 상태와 RNG를 새로 만든다. PersistedInput은 재시작 복구용 opaque 값이며 외부 wire로 공개하지 않는다. 엔진 담당은 준비된 summary API와 cancellation 계약을 제공한다. Backend adapter는 현재 엔진 Run도 연결할 수 있지만 최적화 summary 통합 여부/버전을 구별한다. CPU 결과를 GPU로 표기하지 않는다.

runId는 experimentId:index, attempt는 배치 재개 세대. 저장 키는 (experimentId,index), 현재 attempt만 신규 결과를 수용한다. 이미 유효한 index는 재실행/재집계하지 않는다. crash 시 unfinished 상태를 cancelled/partial로 복구하고 명시 resume으로 미완료 index를 보충한다. 실패 결과는 정상 0 표본이 아니다. resume은 실패·취소 index만 새 attempt로 실행하며 기존 유효 결과는 같은 입력/수치 backend의 표본으로 유지한다. queued/running/cancelling/cancelled/completed/failed를 구분한다. valid/failed는 현재 index 기준, cancelled는 취소 종료에서 미완료 index 수다.

## Analysis 연결

IComputeAnalysis는 확정 in-process 인터페이스이며 통계 프로젝트는 Nikke.Contracts만 참조해 adapter를 구현할 수 있다. Backend가 API 등록·solution/project 참조를 소유한다. 통계 담당의 자체 내부 타입은 자유이며 wire는 위 DTO에 변환한다. RunSummary.Members는 순서 유지 5인, fullBursts는 팀 진입 횟수, member burstCasts/reloads는 내부 이벤트 개수다. 평균 CI와 P5/P95를 구별하고 n=0/1의 불명값은 null. MethodVersion/QuantileMethod/Interval.Method에 Student-t, type7, Wilson, Welch 등 실제 사용 방식을 기록한다. 실패/미완료 run은 IEnumerable에 포함하지 않는다. 부분 결과 여부는 BatchStatus에서 받는다.

OL change는 실제 character/slot/lineIndex를 보존하고 원본을 변경하지 않는다. optionId/value는 고정 GameSnapshot 옵션 범위에 대조한다. baselineExperimentId는 기준 실험 참조이며 후보와 입력 차이를 검증해야 한다. 추천 탐색·holdout 배정은 S-CPU/OL 소유, Backend는 가상 변경 준비와 전투 전체 재실행을 제공한다. 잠금/비용/확률 미확정 추천 숫자는 만들지 않는다. 현행 고정 DEF 정책이며 자동 20억 DEF 전환/게임 영점 수용과 분리한다.

## 확정 구현 연결 보완

엔진 0d23366의 PreparedSkillReplay(cpu-summary.1), 통계 480cf8a 및 호환 수정 979325c/81be5d0을 연결했다. Hits는 평타 명중이며 CriticalHits는 스킬 피해도 포함하므로 서로 대소 제약을 두지 않는다. 통계는 페이지 일부가 아닌 저장소의 전체 유효 표본을 같은 시점에 읽어 전달한다. 조회 캐시는 최대 16개, 2초이며 응답의 n/partial은 그 시점 값이다. 명시 warmup 실험의 통계 조회는 409 warmup_excluded_from_statistics다.

입력 fingerprint는 전투 물리 입력·버전을 식별하고 phase 자체는 포함하지 않는다. phase는 별도 메타데이터로 집계/비교에서 검사하므로 탐색·최종 표본을 혼합하지 않는다. OL 후보 before/after는 OlChange 형태다. 원본 또는 해당 실험 가상 변경 후 실제 T10의 present 줄에만 후보를 만든다. 카탈로그의 정확한 이산 수치와 부호를 유지하며 현재 값·장비 내 중복 옵션·현재 조건의 무효과 옵션은 제외한다. 방어/명중률은 이 피해 모델에서 후보 제외, 원소 피해는 elementAdvantage, 크리는 sample, 차지 옵션은 차지 무기에 한해 제공한다. 제외 판정은 게임 전체 효과의 부정이 아니다.

후보 after를 새 ExperimentRequest.olChanges로 전달하면 동일 400/택틱/조건으로 전체 전투를 다시 실행한다. baselineExperimentId가 있으면 snapshot/5인 순서/조건/phase 일치도 검사한다. v1 비교는 frozen independent holdout 배정 검증 callback을 등록하지 않았으므로 최종 표본이라도 기본 verdict=unverified_design_or_input_difference다. 자동 선별→refinement→holdout orchestration 및 게임 검증 완료 추천으로 승격하지 않는다. 이 단계의 API는 후보 열거 및 명시적 가상 후보 비교를 제공한다.

## B-TUNE-1 호환 추가 — cpu-policy-3 (2026-09-17)

ExecutionSelection의 optional `tuning`에 단계 관측을 추가한다. 기존 필드/route는 유지한다. `policyVersion`, `status`, `cacheSource`, `preparationMilliseconds`, `totalBudgetMilliseconds`, `elapsedMilliseconds`, `plannedWorkers`, `resourceWorkerLimit`, `stages`, `stopReason`, `scope`를 반환한다. stage는 name(warmup/candidate), workers, requested/started/completed/interrupted, budgetMilliseconds/elapsedMilliseconds, status, stopReason, runsPerSecond다. 끝나지 않은 호출의 elapsed/count는 처리량 분자에 포함하지 않는다.

- 입력 준비/복구는 동기식 Data 계약이므로 튜닝 예산 밖에서 따로 시간을 기록하고 전후 요청 취소를 검사한다. 준비 도중 프레임 취소나 별도 hard timeout을 지원한다고 하지 않는다. 호출자가 시간을 제공하지 않으면 null이다.
- warmup은 최대2초/1회이며 완료가 후보 진입의 필수 조건이 아니다. 후보는 자원 상한 내 `[1]` 또는 `[1,2]`를 사전 고정한다. 4/8/...은 이번 제한 탐색 밖이며 resourceWorkerLimit와 plannedWorkers로 범위를 드러낸다.
- 후보마다 같은 전체 전투2회·독립24초를 예약한다. 순차/동시 실행 모두 동일 입력·동일 완료 작업량2회의 실제 벽시계 처리량으로 비교한다. 총 실행 deadline은 1후보26초/2후보50초다. 각 단계의 cooperative 프레임 취소 완료를 기다린 뒤 다음 단계를 시작하므로 타임아웃 작업이 뒤에서 겹치지 않는다. 취소·스케줄링 지연만큼 deadline 관측은 넘을 수 있다. 메모리 초과는 단계 전/진행 중 검사해 중단하며 정상 표본을 만들지 않는다.
- 최종 status는 not_measured/partial/measured/cache_reused다. measured는 **사전 고정한 제한 후보를 모두 측정**했다는 뜻이며 최적 성능 수용이 아니다. partial은 완료 후보만 이 시도에서 선택하고 캐시는 쓰지 않는다. 후보0이면 CPU1/not_measured fallback. 미완료 묶음에 완료된 호출이 있어도 그 묶음 전체를 처리량 비교에서 제외한다.
- 캐시는 전체 계획의 완전한 측정 근거·처리량·선택 worker/chunk·버전·장치/driver/runtime/engine/rules/input/자원 fingerprint를 검사한다. 구버전/증거 없는/부분/오염 캐시는 거부한다. retune 또는 무효 캐시는 새 시도 전에 제거해 실패 뒤 이전 선택이 살아남지 않는다. cache_reused의 stages/elapsed는 원래 측정 근거이고 현재 preparationMilliseconds는 새 준비 시간이다. cacheSource는 miss/invalid/retune/validated_policy_cache다.
- queued 상태의 warmup/candidate 및 취소된 튜닝 관측은 GET status로 조회한다. 최근64 종료 attempt의 중간/취소 관측은 프로세스 메모리에 보존하며 재시작 시 사라진다. 정상 선택의 최종 tuning은 기존 selection JSON과 함께 영속 저장된다. 저장소 schema 변경은 없다. warmup과 튜닝 전투는 정상 결과 DB/Statistics에 저장하지 않는다.

실제 단독 benchmark 합의가 없는 진단은 선택·캐시 기능만 입증한다. scope=bounded_candidates_not_global_optimum이며 전역 최적 worker/속도 개선율/대량 수용을 뜻하지 않는다.

## I-BE schema 3 — 단일 히트 wire

확정 DTO는 `src/Nikke.Contracts/HitCalculation.cs`다. 모든 속성은 아래 camelCase 철자를 사용한다. 단일 히트는 성공 응답을 격리 또는 사용자 지정 `dataRoot/hit-calculations/{id}.json`에 저장한다. 자동으로 기존 파일을 덮어쓰거나 최신 공식으로 다시 저장하지 않는다.

| 요청 | 동작 |
|---|---|
| POST /api/calculations/hit | 아래 요청 → `HitCalculationResponse`, HTTP 200 |
| POST /api/calculations/hit/import | 저장된 artifact JSON → 새 ID의 변환·검산 기록, HTTP 200 |
| GET /api/calculations/hit/{id} | 저장 당시 응답 그대로 조회; 없는 ID 404 |

```json
{
  "inputSchemaVersion": 3,
  "roundingPolicy": "client_f32",
  "observedDamage": 150,
  "input": {
    "statAttack": 100,
    "defense": 0,
    "coefficient": 1,
    "statDamageRatio": 2,
    "defenceRatioRate": 0.25
  }
}
```

`inputSchemaVersion`은 필수이고 2 또는 3만 허용한다. `observedDamage`는 생략/null 가능, 양의 안전 정수 number만 허용한다. `roundingPolicy` 생략 시 `client_f32`; 선택지는 순서대로 `client_f32`, `legacy_term_floor`, `final_round_even`, `nested_floor`다. 마지막 세 정책은 기존 산술을 보존한 비교 후보이며 새 두 rate를 적용하지 않는다. 새 두 rate는 실험·원천 매핑 미확정 항목이다. `statDamageRatio`를 스킬 계수라고 확정하지 않는다. 생략 기본값은 각각 **1, 0**이고 임의의 추정값을 넣지 않는다. `coefficient`와 별도 필드다.

응답은 과거 `{inputSchemaVersion, comparison:{...}}` 봉투 대신 **최상위 DTO**다. UI는 `response.candidates`와 `response.selectedCandidate.terms`를 읽는다. 필드:

- `id`, `createdAt`, `inputSchemaVersion:3`, `rulesVersion:"p02.4-client-f32"`, `status:"provisional_rounding"`.
- `input`: 중립값·생략 필드를 채운 실제 schema 3 입력. `originalInput`: 요청 원본 객체.
- `conversion:{originalSchemaVersion,targetSchemaVersion,converted,method,appliedDefaults}`. v3는 `converted:false,method:"none"`; v2는 `originalSchemaVersion:2,targetSchemaVersion:3,converted:true,method:"v2_to_v3_neutral_rates",appliedDefaults:{statDamageRatio:1,defenceRatioRate:0}`.
- `effectiveAttack`은 client 경로의 number 표시값, `exactEffectiveAttack`은 그 정수의 정확한 십진 문자열이다. 과거 후보의 공격력은 그 후보의 `terms` 중 `effectiveAttack.after`를 사용한다.
- `selectedPolicy`, `selectedCandidate`, `candidates`(항상 위 순서의 4개), `observedDamage`, `limitations`, `sourceArtifact`(가져오기 원본; 일반 요청 null).
- 후보는 `policy,damage,residual,relativeError,terms,status,errorCode,exactDamage`. `status:"available"`이면 계산값·audit를 사용한다. 큰 정수 등 과거 산술 한계에서는 해당 후보만 `status:"unavailable"`, `damage/residual/relativeError:null`, `terms:[]`, `errorCode`에 이유를 반환한다. 이를 피해 0으로 표시하지 않는다. 선택한 후보가 unavailable이면 요청 자체를 HTTP 400으로 거부한다.
- client 후보 `exactDamage`는 정확한 십진 정수 문자열이다. 과거 후보는 안전한 number 범위만 지원하고 `exactDamage:null`이다. audit의 `before/after`와 일반 피해·잔차 number는 binary64 표시값이므로 큰 정수 표시는 exact 필드를 우선한다. 전체 덱 `RunSummary`의 합산 피해는 기존 double 규격을 유지한다.

client audit term 순서는 `effectiveAttack,effectiveDefense,difference,base,B,extra,reduction,defenceRatio,product,final`이다. 각 항은 `name,before,after,operation`을 가진다. 과거 후보의 `charge,P,B2,B3,B4,B5` 등은 그대로 유지되며 하나의 설명을 모든 후보에 공통 적용하지 않는다.

### v2 및 저장 파일 변환

schema 2 요청의 원본에 새 rate가 들어 있으면 `schema2_cannot_contain_schema3_rates`로 거부한다. 두 필드가 없는 원본을 보존하고 (1,0)을 채워 schema 3 제약으로 검산한다. v2의 소수 native ATK/DEF/고정량도 임의 반올림하지 않고 오류다. 변환은 과거 관측 결과를 새로운 확정 사실로 승격하지 않는다.

`/hit/import`는 옛 다운로드 `{inputSchemaVersion:2,comparison:{input:{...},observedDamage:...},...}`와 새 최상위 응답을 받는다. 명시 원본 schema가 필요하다. 선택 정책은 comparison/최상위의 `selectedPolicy`, 또는 artifact의 `roundingPolicy`를 사용하고 없으면 client 기본값이다. 과거 artifact 전체(당시 후보·관측·메모 포함)를 `sourceArtifact`에 남기고 새 계산을 새 ID로 저장한다. 기존 파일 일괄 재해석·덮어쓰기는 하지 않는다. GET은 계산 없이 저장 당시 내용을 돌려준다.

### 공격력 정수와 raw wire

`statAttack`, `defense`, `attackFlatBuffs[].amount`는 정수 number이며 Core의 입력 범위 검사도 적용한다. 소수는 절삭하지 않는다. 공격력 `attackBuffs`/`runtimeAttackBuffs`의 `rate`는 비율 number(14.5%=0.145), 정확한 1/10000 단위만 허용한다. 원문 숫자를 검사하므로 `0.01400000000000000001`, `1e-400`, 정수 뒤 극소 소수도 거부한다.

| 필드 | 입력 | 출력/보존 |
|---|---|---|
| `rawRate10000` | signed long 십진 문자열 권장; ±9007199254740991 범위의 정수 number도 허용 | 항상 십진 문자열 또는 null |
| `exactAmount` | 동일. 큰 long은 반드시 문자열 | 항상 십진 문자열 또는 null |
| `rate` / `amount` | 일반 number. 대응 exact 필드가 있으면 생략 가능 | 표시용 number와 exact 필드를 함께 반환 |

두 표현을 함께 주면 Core가 서로 일치하는지 검사한다. 문자열에 지수·소수·공백은 허용하지 않는다. long 범위는 -9223372036854775808~9223372036854775807이며 실제 공격력·피해 계산의 overflow/음수/범위 제한은 별도로 검사한다. 큰 JSON number를 반올림해서 받아들이지 않는다. `rawRate10000:"1450"`은 rate0.145, `exactAmount:"9007199254740993"`은 binary64로 표현할 수 없는 정확한 고정량이다. UI는 문자열을 `Number()`로 변환해 다시 전송하지 않는다.

```json
{
  "inputSchemaVersion": 3,
  "input": {
    "statAttack": 100,
    "attackBuffs": [{"source":"OL","rawRate10000":"1450","stacks":1}],
    "attackFlatBuffs": [{"source":"experiment","exactAmount":"100"}]
  }
}
```

제약 위반은 HTTP 400 `{message:"..."}`다. 대표 메시지는 `*_must_be_integer_never_truncated`, `rate_requires_exact_1_per_10000_units`, `invalid_hit_json: ...exact_integer_requires_decimal_string_or_safe_integer_number`, `invalid_client_f32_input: ...`, `hit_integer_overflow: ...`. 입력 오류는 정상 피해나 다른 정책 자동 fallback으로 저장하지 않는다.

## I-BE compute 준비·역사 분리

`ExperimentRequest.conditions.roundingPolicy`는 같은 네 정책이며 생략 시 client 기본값이다. 선택 실험용 optional `hitOverrides`는 캐릭터 ID별 객체다. 허용 필드는 `statDamageRatio`, `defenceRatioRate`, `runtimeAttackBuffs`, `attackFlatBuffs`뿐이다. 위 raw/exact 규격을 사용한다. 선택한 5인 밖의 ID/다른 필드는 오류다. 배열을 지정하면 해당 기본 입력 배열을 교체하고, 엔진이 생성하는 실제 스킬 버프·고정 부여는 기존 로직대로 추가한다. snapshot 자체는 바꾸지 않는다.

```json
"hitOverrides": {
  "5004": {
    "statDamageRatio": 2,
    "defenceRatioRate": 0.25,
    "runtimeAttackBuffs": [{"source":"experiment","rawRate10000":"1450"}],
    "attackFlatBuffs": [{"source":"experiment","exactAmount":"100"}]
  }
}
```

새 `BatchStatus.input`은 `inputSchemaVersion:3`, `roundingPolicy`, `summaryVersion:"cpu-summary.2-client-f32"`를 명시한다. engineVersion도 그 summary 버전이며 rulesVersion에는 SkillReplay/TeamBurst/HitCalculator/StatBuffCalculator 버전과 정책을 함께 기록한다. members 전체의 두 rate·raw/exact 표현, graph, 최종 조건·데이터 버전을 canonical fingerprint에 포함한다. 의미상 같은 rate라도 raw 존재 여부가 다른 원천 입력은 별도 fingerprint다. phase는 별도 집계 경계로 기존 유지한다.

튜닝 키가 새 workload/engine/rules를 포함하므로 이전 캐시를 재사용하지 않는다. 구 기록에서 새 메타데이터가 빠지면 schema2/null로 읽어 조회 가능성을 유지한다. 복구 시 버전·schema·정책 및 저장 payload 재계산 fingerprint가 모두 일치해야 하며, 이전 버전 재개는 HTTP 409 `engine_or_rules_version_changed`, 변조 입력은 `prepared_input_fingerprint_mismatch`다. 구 결과 삭제나 새 버전 라벨 재부여는 없다. 현재 엔진에서 과거 정책을 명시한 **새 실험**은 실행 가능하다.

통계는 experiment별 유효 결과만 읽고 저장 시 input fingerprint를 검사한다. baseline 후보 비교는 같은 rules/schema/policy/summary와 동일 hitOverrides를 요구한다. 정책 실험끼리는 별개 기록으로 조회하며 OL 비교 통계에 혼합하지 않는다. 이 변경은 Analysis 산술이나 통계 방법을 수정하지 않는다.

## F-COND-B — 보스 거리·약점 조건 (2026-09-28)

원천·준비·전체 응답 필드와 실제 검증은 [boss-distance-element-backend.ko.md](boss-distance-element-backend.ko.md)에 있다. UI mock의 잠정 combat-ranges route는 채택하지 않았다.

| GET | 응답 |
|---|---|
| `/api/runtime/combat-conditions` | runtimeDataId, schemaVersion1, source(path/sha256/version/origin/locale), weaponRanges, elements, rangeRule, gameVerified:false |
| `/api/snapshots/{id}/combat-conditions?characterIds=5011,5008,5004,5009,5044` | runtimeDataId, snapshotId, members(요청 순서의 보유1~5인) |
| `/api/runtime/skill-replays/{id}/condition-compatibility` | old/new 저장 replay의 모드·설명·값 |
| `/api/compute/experiments/{id}/condition-compatibility` | old/new 저장 experiment의 모드·설명·값 |

weaponRanges 원소는 `weaponType,characterCount,ranges,exceptions,rangeBonusAvailable,diagnostics`. ranges 원소는 `min,max,count,isTypical,characterIds`; 대표구간은 인원 최다(동률 min/max 순), 다른 구간의 실제 멤버를 exceptions에 제공한다. 모든 구간·예외는 192명 원천의 집계다.

members/예외 profile은 `characterId,name,weaponType,bonusRangeMin,bonusRangeMax,element,rangeBonusAvailable,diagnostic`. RL0–0은 false와 `rl_zero_range_no_bonus_unverified`. elements는 `{value,iconUrl}` 5개이고 Electronic은 `/editor/assets/ui/code-electric.png`다. UI는 이 캐릭터 값으로 참고 표시한다. 실제 판정은 엔진이 수행한다. old catalog에 자료가 없으면409 `combat_profile_catalog_missing`, 미보유·중복·초과 인원400이다.

새 replay/compute 요청은 `conditions.combat`에서:

```json
{"durationFrames":10800,"enemyDefense":30925,"bossDistance":35,"bossWeakElement":"Fire"}
```

`bossDistance`는 정수0–100/null, `bossWeakElement`는 Fire/Water/Wind/Iron/**Electronic**/null(대소문자 구분). 미설정/없음을 새 모드로 보존하려면 두 필드를 null로 명시한다. `properDistance`/`elementAdvantage`는 **생략**한다. 새 필드와 과거 bool 동시 지정은 false/null도400 `boss_conditions_mixed_with_legacy`로 거부한다. 이전 bool만 지정한 요청은 기존 전원 적용 경로를 유지한다. 거리 경계 양끝 포함, RL0–0 보너스 없음, normal에만 거리·모든 피해에 약점 일치는 잠정 실험 규칙이다. 단일 hit의 수동 bool은 이번 변경 밖이다.

새 replay 최상위와 compute `input`에 `conditionCompatibility:{mode,label,legacyProperDistance,legacyElementAdvantage,bossDistance,bossWeakElement}`가 들어간다. mode는 `per_member`/`legacy_global`, label은 `보스 거리·약점(멤버별)`/`이전 방식(전원 적용)`이다. UI 재실행은 mode별 원래 필드만 구성한다. compatibility의 legacy 필드를 그대로 새 combat에 합치지 않는다. 새 두 값 null은 engine result.conditions에서 생략될 수 있으므로 mode와 명시값 복원에는 이 metadata를 사용한다. old record는 위 읽기 endpoint로 확인하며 원본 GET/export와 파일을 재작성하지 않는다.

준비 members에는 `weapon.bonusRangeMin/bonusRangeMax/element`가 채워진다. 전체 member metadata/조건/원천 runtime ID/compatibility mode가 fingerprint에 포함되고 `boss-distance-element.1-inclusive`, skills/team4, summary3가 rules/cache를 구분한다. old 버전 결과는 조회 가능하고 resume은 기존 버전 불일치409를 유지한다. 과거 bool을 명시한 새 실행은 가능하다. IncElementDmg OL 후보도 새 모드의 멤버별 약점 일치에 따라 생성하고, 과거 bool에서는 기존 전역 적용을 유지한다.

Git 제외 runtime 확장을 준비한 뒤 해당 dataRoot의 새 API 프로세스가 읽어야 한다. 이 작업은 원본 카탈로그·배포/서버를 변경하지 않았다. 배포 시 Director가 profile 준비와 코드 일치를 확인해야 한다.

### B-FIX-2 — 불명 profile 오류 wire

runtime `combatProfiles`의 필수 JSON 키는 DTO 생성 전에 검사한다. 사거리 min/max는 JSON 정수0–100, min≤max이어야 하고 문자열 숫자·null·누락을 0으로 바꾸지 않는다. element는 정확한 5종 문자열이다. 명시 min0(SG/RL), RL0–0, SR 캐릭터별 예외는 유효하다.

카탈로그의 필수 키 누락·null·잘못된 타입/값은 **HTTP409**와 아래 JSON으로 반환한다. 두 combat-conditions 조회와 skill/weapon replay 생성, compute 실험 생성에 공통 적용한다. 잘못된 profile은 스탯·전투 계산 및 replay/실험 저장 전에 거부한다. 필드 단위 fallback은 없다.

```json
{
  "code": "combat_profile_invalid",
  "message": "combat_profile_invalid: combatProfiles.characters.5004.bonusRangeMin: missing",
  "characterId": "5004",
  "field": "combatProfiles.characters.5004.bonusRangeMin",
  "reason": "missing"
}
```

`reason`: `missing`(키 없음), `null`(명시 null), `wrong_type`(정수/문자열/객체 타입 불일치), `out_of_range`(사거리 범위·순서), `unsupported_value`(속성/무기/스키마 등), `id_mismatch`, `weapon_mismatch`, `hash_mismatch`(출처 sha256/version 불일치). `field`는 combatProfiles부터 시작하는 JSON 경로이고, 카탈로그·출처 수준 오류는 `characterId:null`이다. 성공 응답과 요청 조건 필드는 바뀌지 않는다. UI는 기존 `message`로 오류를 표시할 수 있고 세부 분류에는 code/field/reason을 사용한다.

profile 멤버 전체 누락은 기존 HTTP400 `{message:"combat_member_profile_missing:<id>"}`, 전체 combatProfiles가 없는 옛 catalog의 자료 요구는 기존409 `combat_profile_catalog_missing`를 유지한다. 자료가 전혀 없는 옛 catalog의 metadata 불필요 bool 경로와 기존 기록 읽기는 유지한다. 반면 combatProfiles가 있는 catalog의 필드 손상은 과거 bool 요청이어도 묵인하지 않는다. 이 수정은 정상 계산값·fingerprint·엔진 버전을 바꾸지 않는다.

## F2-B — 전투 조건 정리·보스 선택 확정 wire (2026-09-29)

### 신규 요청과 이전 조건 재현

적용 경로는 `POST /api/runtime/skill-replays`, `POST /api/compute/experiments`다. 요청 최상위 optional `conditionProfile`은 생략 또는 `solo_raid`가 새 규칙, `legacy`는 명시적인 이전 조건 재현이다. **UI 신규 실행에는 legacy를 넣지 않는다.** 과거 조건으로 재실행할 때만 legacy를 넣고 당시 combat 값을 보낸다. 프로필을 조건 값으로 추정하지 않는다.

새 요청의 combat 생략 기본값:

```json
{"durationFrames":10800,"pelletCoefficientPolicy":"per_trigger","defenseMode":"team_damage_threshold","enemyDefense":30925,"critMode":"sample"}
```

- durationFrames·pelletCoefficientPolicy·defenseMode는 명시 시 위 값과 같아야 한다. 다른 값/null/타입은400. 오류 message: `solo_raid_duration_fixed_10800`, `solo_raid_pellet_policy_fixed_per_trigger`, `solo_raid_defense_mode_requires_team_damage_threshold`.
- 자동 모드 enemyDefense는 생략 가능하며 서버가30925로 고정한다. 명시 숫자의 음수·소수·문자열/null은400 `invalid_enemy_defense`; 유효 정수를 보내도 자동 모드의 시작값30925로 정규화해 결과·저장에 남긴다.
- critMode의 명시 선택과 기존 roundingPolicy 선택은 유지한다. 대미지 정책 생략 기본은 기존 client_f32다. bossDistance/bossWeakElement와 구 bool 혼용 금지는 그대로다.
- `conditionProfile:"legacy"`는 당시 시간·per_trigger/per_pellet·크리·EnemyDefense를 보존하고 defenseMode=fixed만 허용한다(생략 시 fixed 명시). 다른 모드는400 `legacy_defense_mode_requires_fixed`. 새 사용자 조건과 분리된 비교·구 결과 재현 경로다. 프로필 미지원 값은400 `condition_profile_invalid`.
- 단일 hit 수동 검산·다중 정책 weapon-reference 경로는 이전 명시 조건을 유지한다. weapon replay에 자동 DEF를 보내면400 `weapon_reference_requires_fixed_defense_use_skill_replay`; 자동 전투는 skill replay를 사용한다.

### DEF 표시·저장

신규 saved skill replay 최상위와 compute `BatchStatus.input`에 `battleConditions`가 들어간다:

```json
{"profile":"solo_raid","label":"덱 누적 피해에 따라 방어력 자동 전환","defenseMode":"team_damage_threshold","initialDefense":30925,"switchedDefense":31784,"damageThreshold":2000000000,"durationFrames":10800,"pelletCoefficientPolicy":"per_trigger"}
```

legacy는 `profile:"legacy",label:"이전 방식(고정 방어력)",defenseMode:"fixed"`, initialDefense는 당시 값, switchedDefense/damageThreshold는 null이다. 기존 `conditionCompatibility`는 거리·약점 old/new 전용으로 유지한다. DEF 모드를 그 필드에서 추정하지 않는다.

기존 저장 파일을 수정하지 않고 표시 정보를 얻는 GET:

- `/api/runtime/skill-replays/{id}/battle-conditions`
- `/api/compute/experiments/{id}/battle-conditions`

모드가 없는 옛 저장 조건은 fixed로 해석한다. 기존 GET/export는 원문을 보존하고 새 기본값을 덧씌우지 않는다. 엔진/rules 버전이 다른 옛 batch resume은 기존409 규칙을 유지한다.

실제 전환 결과는 skill replay `result.defense`와 compute results의 `runs[].defense`다:

```json
{"mode":"team_damage_threshold","initialDefense":30925,"finalDefense":31784,"damageThreshold":2000000000,"switchAfterHit":{"frame":1133,"hitTraceId":3804,"hitOrdinal":2011,"characterId":"5009","effect":"normal_attack","cumulativeDamage":2001052869,"previousDefense":30925,"newDefense":31784}}
```

위 값은 합성 검증 예다. 전환 없으면 switchAfterHit=null이며 fixed는 damageThreshold=null이다. 과거 compute 행에는 defense=null일 수 있으며 “기록 없음”으로 취급한다. hitTraceId는 초과를 만든 피해 이벤트 ID다. 그 타격에는 previousDefense, 다음 처리 타격부터 newDefense를 적용한다. trace 미수집/잘림이어도 이 요약은 저장된다. 경계 세부(정확히20억 무전환·다음 타격부터)는 실게임 확인 대기 가설이다.

compute input.defPolicy는 `fixed:<당시 DEF>` 또는 `team_damage_threshold:30925:2000000000:31784`. 조건의 모드와 `cpu-summary.4-defense-switch`, skills/team5 버전으로 fingerprint·튜닝 키를 구분한다. Contracts·DB JSON에 전환 DTO를 보존하며 통계 산술은 변경하지 않는다.

### 보스 목록과 선택 — 표시 전용

`GET /api/presentation/solo-raid-bosses`:

```json
{"schemaVersion":1,"defaultBossId":"dummy","bosses":[{"id":"dummy","name":"더미 보스","imageUrl":null,"season":null},{"id":"solo-raid-41","name":"리버렐리오 바디","imageUrl":"/editor/assets/bosses/<opaque-id>.png","season":41}],"diagnostics":[{"id":"solo-raid-42","season":42,"code":"korean_name_unavailable","displayable":false,"message":"한국어 이름 원천 미확인"}],"complete":false}
```

예시 목록은 축약했다. 실제 표시 목록은 한국어 원천을 확인한 항목만이다. 확인하지 못한 보스는 `bosses`에서 제외하고 diagnostics로 반환하며 영어로 대체하지 않는다. `boss_image_unavailable`은 이미지 실패, catalog 미준비는 dummy만 + `boss_catalog_not_prepared`. complete=false면 전체 원천 목록의 일부가 제외된 상태다. UI는 bosses만 선택 대상으로 쓰고 diagnostics를 준비 상태 안내에 사용한다. 원본 영문명/몬스터ID/URL/SHA256은 응답에 없다. 이미지 파일명도 원본 hash가 아닌 불투명 ID다. dummy의 null imageUrl은 기본 더미 표시를 사용한다.

두 POST의 최상위 `bossId`에 선택 ID를 보낸다(생략/null은 dummy). 알 수 없거나 제외된 ID는400 `boss_id_unknown`. 결과 최상위 `boss`(skill replay), `input.boss`(compute)에 선택 당시 `{id,name,imageUrl,season}`를 저장한다. 보스 이름을 클라이언트 입력으로 받지 않는다. 구 저장본의 boss=null은 과거 미기록이며 원문을 다시 쓰지 않는다.

boss 메타데이터는 조건·전투 데이터 버전·fingerprint·튜닝 키에 넣지 않는다. 보스 선택만 달라도 계산 결과·키는 같고 저장 실험 ID와 표시 선택만 구분된다. 보스별 약점/거리/DEF/스킬 자동 변경은 이번 범위가 아니다.

Git 제외 presentation 준비 명령은 `python tools/data-pipeline/prepare_solo_raid_bosses.py --presentation-root <격리 dataRoot>/presentation`. 원본에는 이번 작업에서 실행하지 않았다. 목록/이미지와 코드를 같이 준비해야 실제 보스가 표시되며 상세 범위는 [F2-B 보고서](combat-conditions-cleanup-backend.ko.md)를 따른다.

### 보스 정적 속성 — 표시 전용 (B-DATA-1)

`GET /api/presentation/solo-raid-bosses/attributes`는 위 보스 목록과 **별도 wire**다(목록 필드 `id/name/imageUrl/season`은 그대로). `schemaVersion:1`, `kind:"solo_raid_boss_static_attributes"`, `fields`(필드별 원천·단위·신뢰도), `bosses`(시즌 1~42, `id`는 `solo-raid-<시즌>`), `diagnostics`, `complete`, `source`(StaticData 사본과 표의 SHA-256·레코드 수, 준비 시각). 값이 없으면 `null`이고 0·기본값으로 채우지 않는다. 확인하지 못한 값은 명시적 `null`이며 보스의 `unconfirmed`에 이유 코드(`challenge_level_stats`, `level_change_step_<n>_stats`, `core_position` 등)가 함께 있어야 한다(선언 없는 null·키 누락·문자열 숫자는 손상으로 409). 같은 계약을 읽기 경로 전체에 일반적으로 적용한다: non-nullable 멤버와 **모든 컬렉션·딕셔너리 요소**의 null은 어느 깊이에서든 409이고, nullable 멤버의 null은 `unconfirmed` 선언 코드(`element`·`weak_element`·`model_prefab`·`challenge_level_stats`·`level_change_rows`·`level_change_step_<n>_stats`·`core_position`) 또는 다른 필드로 설명될 때만 허용한다. `challenge.levelChangeGroupId`(preset 원값, 0 = 레벨 변경 그룹 없음)가 0이 아니면 `levelChange`가 있어야 하고(없으면 `level_change_rows` 선언 필요), 0이면 `levelChange`는 null이어야 한다. `rangeTo:null`(상한 없음)은 마지막 단계에서만 허용한다. 미사용 시즌은 `reason` 외 속성을 갖지 않는다. 시즌 41·42처럼 사용한 StaticData 사본에 없는 시즌은 `status:"unavailable"`, `reason:"static_data_season_missing"`이며 속성은 모두 없다. 준비 전에는 `bosses:[]` + `boss_attributes_not_prepared`, 손상 파일은 409 `boss_attributes_invalid`.

**이 값은 계산·fingerprint·튜닝 키·저장 결과에 반영되지 않는다.** 보스 선택은 계속 표시 전용이다. 상세 필드·신뢰도·미확인 목록은 [B-DATA-1 보고서](boss-static-attributes-backend.ko.md).

### 사거리 확인 범위

combat-conditions catalog의 `gameVerified:true`는 사용자 확인을 마친 **캐릭터별 사거리 데이터·RL0–0** 범위다. RL diagnostic은 `rl_zero_range_no_bonus`로 바뀌고 rangeBonusAvailable=false는 유지한다. 전투 전체·보스 기믹·대미지 실측까지 검증됐다는 뜻이 아니다. 경계 양끝 포함은 현 계산 유지·문서상 확인 대기이며 UI 미확정 문구로 표시하지 않는다.
