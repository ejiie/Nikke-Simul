# U-CPU — 단일 덱 통계·장치 선택 UI (2026-09-15)

담당: `Director/docs/single-deck-compute-assignments-2026-09-15.ko.md`의 U-CPU 절. 소유 범위는 `apps/desktop-ui/**`와 UI 전용 테스트, 이 보고서다. 엔진·Backend·Analysis·QA 파일과 다른 worktree는 편집하지 않았다.

기준: 공통 제품 기준 `a5ccba6663241e61783b509fc69098ad3c9ecef2`. 화면 최초 구현은 `26afcf8`(계약 확정 전, 임시 규격)이며, 이 문서는 **Backend 선행 계약 `f2327e5` 확정 공유 이후의 연결 상태**를 기록한다.

## 1. 계약 반영 (Backend v1 · f2327e5)

`Backend/docs/single-deck-compute-contract.ko.md`와 `src/Nikke.Contracts/Compute.cs`의 확정 규격으로 어댑터를 교체했다. wire 매핑은 `apps/desktop-ui/compute-adapter.js` 한 곳에 있으며 `COMPUTE_CONTRACT_VERSION = 'backend-v1-f2327e5'`로 표시한다. UI는 임의 wire 규격을 만들지 않는다.

| 항목 | 반영 |
|---|---|
| 경로 | `GET /api/compute/hardware`, `POST /api/compute/experiments`, `GET /experiments/{id}`, `POST /{id}/cancel`, `POST /{id}/resume`, `GET /{id}/results?offset=&limit=`(최대 1000), `GET /{id}/statistics?cut=`, `GET /{id}/comparison` |
| DTO | `HardwareProfile`/`GpuProfile`, `ComputeOptions`, `ExecutionSelection`, `ExperimentRequest`, `ExperimentInput`, `BatchStatus`, `BatchResults`, `Interval`, `MetricStatistics`, `StatisticsResult`, `OlChange`, `OlComparison` |
| 요청 | `runs`, `phase`(warmup/pilot/exploration/final), `recordLevel="summary"`, `execution{requested,maxWorkers,memoryLimitBytes,deviceId,retune}`, `useSavedTactic`, 선택적 `olChanges`/`baselineExperimentId` |
| 오류 | 409 `analysis_not_integrated`(통계·비교), 409 `gpu_unavailable`(강제 GPU), 그 외 코드는 코드 그대로 표시 |

**조건 필드**: 계약 예시의 `targetDefense`는 문서 오타이고 실제 엔진 필드는 `enemyDefense`다. `buildExperimentRequest`는 `targetDefense`가 들어오면 `enemyDefense`로 옮기고 오타 필드를 제거한다. 회귀에서 요청 본문에 `targetDefense`가 없음을 검사한다. Backend의 문서 정정 예정 사항과 일치한다.

## 2. 구현

새 탭 `단일 덱 통계`(`data-tab="stats"`, `#stats-content`), 모듈 `compute-adapter.js`(계약 매핑)와 `single-deck-stats.js`(렌더러 `renderSingleDeckStats`, 모델 `buildStatsModel`, 컨트롤러 `createSingleDeckStatsView`). `app.js`는 탭 제목·인스턴스 생성·`setPage('stats')` 연결과 조건 수집만 담당하며, Q3 harness가 잘라 실행하는 솔로 레이드 submit 구간 밖에 배치했다.

화면: 덱·택틱 요약(싱크로 400 고정, `durationFrames`/초 병기, `defPolicy` 표시, 표본 단계, 입력 fingerprint), 실행 횟수·표본 단계·컷 기준 입력과 실행/취소/재개, 진행률과 요청·유효·실패·취소(미완료) 수, 부분 결과·attempt·재시작 복구 배지, 장치 패널(자동 기본, 탐지 상태, 실제 backend와 근거, CPU fallback 원인, 장치별 4단계 검증 상태 표, 고급의 장치·worker·메모리 상한·재튜닝·재측정), 통계(팀 카드와 니케별 표, 평균 CI와 P5·P95 구분, 컷 확률·CI, 방식 표기), OL 가상 후보 비교(변경 부위·줄·옵션·수치, 팀 평균 차이와 CI, 판정).

표시 규칙:

- 값이 없으면 `미확인`, `unsupportedReason`이 있으면 `미지원`, n=0/1은 `표본 없음` / `표본 1건 · 산포/신뢰구간 없음`. 정상 0은 0으로 표시하고 미확인과 구분한다.
- GPU는 payload `eligible=true`만 사용 가능이며 고급 선택지에 나온다. `runtimeStatus=not_implemented`나 FP64 미지원 장치는 이름이 보여도 선택할 수 없다. 강제 GPU는 Backend 409를 그대로 보여 준다.
- 실제 backend가 진실이다. `requested=gpu`인데 `backend!=gpu`면 경고를 띄우고 GPU 성공으로 표시하지 않는다. auto의 CPU fallback은 원인과 함께 별도 표기한다.
- 실패는 정상 0 표본이 아니고, 취소 시 미완료 수는 표본에서 제외됨을 명시한다. 재개는 새 attempt이며 기존 유효 결과를 중복 집계하지 않는다고 적는다.
- OL 판정은 `differenceCi`가 0을 제외할 때만 개선/악화다. 응답 `verdict`가 이를 만족하지 않으면 `우열 미확정`으로 표시하고 불일치를 경고한다. 모듈 비용·확률 UI는 만들지 않는다.
- `gameVerified=false`와 현행 고정 DEF 정책을 화면에 남긴다.

## 3. 작업 중 발견하고 고친 결함 (UI 소유)

계약 적용 후 브라우저 회귀가 가로챈 요청 본문에서 `conditions.combat`이 비어 있었다(`enemyDefense`/`durationFrames` 누락). 원인은 `app.js`의 조건 수집이 계약 이전 형태(`{durationSeconds, enemyDefense}`)를 반환해 `buildExperimentRequest`가 `conditions.combat`을 찾지 못한 것이다. 조건 수집을 전체 `SkillReplayConditions` 형태로 고치고, 요청 본문 검사(방어력·프레임·정수화 정책·recordLevel·runs·오타 필드 부재)를 회귀에 추가했다. 화면 표시는 fixture의 `input`을 쓰고 있어 이 결함이 화면만으로는 드러나지 않았다.

## 4. 검증

| 명령 | 결과 |
|---|---|
| `node tests/ui/single_deck_stats.test.mjs artifacts/ui/single-deck-stats/unit` | 13/13 통과 (`contract: backend-v1-f2327e5`) |
| `python tests/ui/check_single_deck_stats_browser.py` | 통과 · 증거 `artifacts/ui/single-deck-stats/run-9bcf8b574583/` |
| `node tests/q3/check_ui_contract.mjs <engine result.json>` | 26/26 통과 |
| `python tests/ui/check_solo_raid_level.py` | 통과 (요청 `scenarioLevel` 400/400) |
| `node tests/ui/damage_audit.test.mjs <saved replay> …` | 19/19 통과 |
| `python tools/data-pipeline/tests/check_damage_log_ui.py` | 통과, JS 오류 0 |

단위 검사: 계약 경로 문자열(`results?offset=0&limit=100`, `statistics?cut=`), `eligible` 기반 GPU 사용 가능 판정과 선택지, CPU 전용·probe 실패·원격 세션, auto fallback과 강제 GPU 불일치, BatchStatus 카운트·attempt·부분·버튼, 오류 코드 문구, 팀/니케 통계와 `input.characterIds` 순서, n=0/1·정상 0·`unsupportedReason`, OL 판정 4종(응답이 개선이라 해도 CI가 0을 포함하면 미확정), `buildExperimentRequest`의 `enemyDefense` 변환과 기본값, HTML escape, 컨트롤러의 실행/취소/재개·복구·409 처리.

브라우저 상태 검사(`evidenceKind: synthetic_http_fixture`): 계약 경로를 fixture로 모의했다.

- 장치: `not_implemented`/FP64 미지원만 있을 때 선택지 `['자동 선택 (권장)', 'CPU']`, 사유 문구 표시. probe 실패 후에도 GPU 선택지 없음.
- 강제 GPU: 409 `gpu_unavailable`을 화면에 표시.
- 실행→완료: n 1,000, 평균 CI `152,083,461.2 ~ 152,681,125.6`, 컷 68.3%, 니케별 표, OL `개선`.
- 요청 본문: `durationFrames 10800`, `enemyDefense 30925`, `roundingPolicy legacy_term_floor`, `recordLevel summary`, `runs 1000`, `phase final`, `useSavedTactic true`, `targetDefense` 없음, `targetLabel single_deck_statistics`.
- 취소→`부분 결과`·니케별 `미지원`·OL `우열 미확정`과 판정 불일치 경고. 재개→`attempt 2`. 새로고침→저장된 `exp-synthetic-1`로 `재시작 복구`.
- Analysis 409: 통계·비교 패널이 `통계 모듈(Analysis) 미연결`만 표시하고 수치를 만들지 않음.
- 1500/850/500px 가로 넘침 0, JS 예외 0, 기존 솔로 레이드 폼 레벨 입력 0개. 격리 서버 이미지 404 25건은 자산 경고로 분리.

## 5. 미완료·의존

- **실제 배치 API 종단 검증은 아직 없다.** 위 브라우저 검사는 전부 합성 fixture 응답이며 Backend 제품 구현이 올라오면 같은 계약으로 실연결 검사를 추가한다.
- 실제 CPU/GPU 장치 탐지·실행·성능은 측정하지 않았다. fixture의 벤더·장치 이름은 합성이다.
- 엔진 최적 summary/cancellation 호출 계약과 그 커밋을 Backend `term_6c0c321c-15a9-4f93-8784-5a88b484ee45`에 알리는 일은 **E-CPU(엔진 담당) 소유**다. UI는 그 API를 직접 호출하지 않으므로 이 보고서로 대신 선언하지 않는다.
- 통계 산출은 S-CPU, 대규모 부하·수용은 Q-CPU 소유다. 화면은 받은 값을 표시만 한다.
- 비용 효율·모듈 예산 추천 UI는 자료 확인 전이라 만들지 않았다(P08-B/C 후속).
- 결과 표시는 모델 기반 실험이며 게임 영점·자동 DEF 전환 수용과 구분한다.

## 6. 보존

원본 계정 DB·세션·캐시, 5180/5181 서버, EXE·바로가기, 다른 worktree를 변경하지 않았다. 검증 산출물은 git 제외 `artifacts/ui/single-deck-stats/`에만 남겼다. 기존 미추적 `package-lock.json`은 보존하고 커밋에서 제외했다(sha256 `2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767`). 원격 push와 새 워커 생성은 하지 않았다.
