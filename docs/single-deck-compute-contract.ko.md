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

요청 예: `{ "snapshotId":"...", "characterIds":["...","...","...","...","..."], "conditions":{"roundingPolicy":"final_round_even","combat":{"durationFrames":10800,"targetDefense":30925}}, "runs":1000, "phase":"final", "execution":{"requested":"auto"}, "useSavedTactic":true }`. conditions는 기존 SkillReplayConditions 전체 규격이며 기본 durationFrames=10800, synchro=400을 적용한다. 나머지 전투 조건은 기존 엔진 유효성 검사를 따른다. 저장 택틱은 현재 snapshot/편성과 일치할 때만 적용하고 stale은 거부한다. 명시 conditions와 최종 적용 입력을 fingerprint에 포함한다. durationFrames는 프레임(60Hz), 피해는 게임 피해 단위, 시간은 ms, OL value는 기존 normalized 비율이다(공증 10%=0.1).

Phase는 warmup/pilot/exploration/final. 통계 표본은 같은 phase/input/backend 의미만 집계한다. 튜닝 warmup은 결과 표본으로 저장하지 않는다. RecordLevel은 현재 summary만 허용한다. requested=auto/cpu/gpu. GPU provider가 full battle 정확성/self-test/실측을 통과하기 전 runtimeStatus=not_implemented, eligible=false; auto는 CPU fallback, 강제 gpu는 실행 전 409 gpu_unavailable. inventory의 이름은 사용 가능 판정이 아니다.

## 실행/저장 경계

IPreparedExperiment는 준비된 비공개 입력을 보유하고 Run 호출마다 전투 상태와 RNG를 새로 만든다. PersistedInput은 재시작 복구용 opaque 값이며 외부 wire로 공개하지 않는다. 엔진 담당은 준비된 summary API와 cancellation 계약을 제공한다. Backend adapter는 현재 엔진 Run도 연결할 수 있지만 최적화 summary 통합 여부/버전을 구별한다. CPU 결과를 GPU로 표기하지 않는다.

runId는 experimentId:index, attempt는 배치 재개 세대. 저장 키는 (experimentId,index), 현재 attempt만 신규 결과를 수용한다. 이미 유효한 index는 재실행/재집계하지 않는다. crash 시 unfinished 상태를 cancelled/partial로 복구하고 명시 resume으로 미완료 index를 보충한다. 실패 결과는 정상 0 표본이 아니다. resume은 실패·취소 index만 새 attempt로 실행하며 기존 유효 결과는 같은 입력/수치 backend의 표본으로 유지한다. queued/running/cancelling/cancelled/completed/failed를 구분한다. valid/failed는 현재 index 기준, cancelled는 취소 종료에서 미완료 index 수다.

## Analysis 연결

IComputeAnalysis는 확정 in-process 인터페이스이며 통계 프로젝트는 Nikke.Contracts만 참조해 adapter를 구현할 수 있다. Backend가 API 등록·solution/project 참조를 소유한다. 통계 담당의 자체 내부 타입은 자유이며 wire는 위 DTO에 변환한다. RunSummary.Members는 순서 유지 5인, fullBursts는 팀 진입 횟수, member burstCasts/reloads는 내부 이벤트 개수다. 평균 CI와 P5/P95를 구별하고 n=0/1의 불명값은 null. MethodVersion/QuantileMethod/Interval.Method에 Student-t, type7, Wilson, Welch 등 실제 사용 방식을 기록한다. 실패/미완료 run은 IEnumerable에 포함하지 않는다. 부분 결과 여부는 BatchStatus에서 받는다.

OL change는 실제 character/slot/lineIndex를 보존하고 원본을 변경하지 않는다. optionId/value는 고정 GameSnapshot 옵션 범위에 대조한다. baselineExperimentId는 기준 실험 참조이며 후보와 입력 차이를 검증해야 한다. 추천 탐색·holdout 배정은 S-CPU/OL 소유, Backend는 가상 변경 준비와 전투 전체 재실행을 제공한다. 잠금/비용/확률 미확정 추천 숫자는 만들지 않는다. 현행 고정 DEF 정책이며 자동 20억 DEF 전환/게임 영점 수용과 분리한다.
