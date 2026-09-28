# 단일 덱 compute 계약 v1 — B-CPU

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
