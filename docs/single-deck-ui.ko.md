# U-CPU — 단일 덱 통계·장치 선택 UI (2026-09-15)

담당: `Director/docs/single-deck-compute-assignments-2026-09-15.ko.md`의 U-CPU 절. 소유 범위는 `apps/desktop-ui/**`와 UI 전용 테스트, 이 보고서다. 엔진·Backend·Analysis·QA 파일과 다른 worktree는 편집하지 않았다.

기준: 공통 제품 기준 `a5ccba6663241e61783b509fc69098ad3c9ecef2`로 fast-forward(직전 UI 커밋 `75e8ae5` 포함, 분기 커밋 보존). 기존 미추적 `package-lock.json`은 그대로 두었고 커밋에서 제외했다(sha256 `2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767`).

## 1. 계약 상태 — 이번 범위의 한계

Backend의 `docs/single-deck-compute-contract.ko.md`는 아직 없고, Backend worktree(`5b7685f`)에 `Nikke.Compute`/`Nikke.Jobs`/compute route도 없다. 그래서 지시 4항에 따라 **독립 렌더링 fixture와 브라우저 테스트부터** 수행했다.

- 모든 wire 필드명과 route는 `apps/desktop-ui/compute-adapter.js` 한 곳에 모았고 `COMPUTE_CONTRACT_STATUS = 'provisional_pending_backend_contract'`로 표시했다. 계약이 확정되면 이 파일만 바꾼다.
- 화면 상단이 응답 출처를 구분한다: `연결 확인 중` / `배치 API 미연결 · 계약 확정 전` / `실제 API 응답`.
- **이번 검증은 전부 합성 HTTP fixture다. 실제 배치 API 종단 통과가 아니다.** 실제 연결은 확정 계약을 따른다.

## 2. 구현

새 탭 `단일 덱 통계`(`data-tab="stats"`, `#stats-content`)와 모듈 두 개를 추가했다.

- `apps/desktop-ui/compute-adapter.js`: HardwareProfile / ExecutionSelection / Batch lifecycle / RunSummary 통계 / OL comparison / ExperimentInput 매핑과 표시 규칙.
- `apps/desktop-ui/single-deck-stats.js`: 순수 렌더러 `renderSingleDeckStats`, 모델 조립 `buildStatsModel`, 화면 컨트롤러 `createSingleDeckStatsView`(실행/취소/재개/폴링/재시작 복구).
- `app.js`는 탭 제목·인스턴스 생성·`setPage('stats')` 연결만 추가했다. 기존 솔로 레이드 폼과 제출 경로는 건드리지 않았다(Q3 harness가 잘라 실행하는 submit 콜백 구간 밖에 배치).

화면 구성: 덱·택틱 요약(싱크로 400 고정, 180초 기본, 현행 고정 DEF 정책 명시), 실행 횟수와 실행/취소/재개, 진행률과 요청·유효·실패·취소 표본 수, 부분 결과와 재시작 복구 배지, 장치 패널(자동 선택 기본, 탐지 상태, 실제 backend와 선택 근거, CPU fallback 원인, 장치별 검증 단계 표, 고급의 장치·worker·메모리 상한과 재측정), 통계(n·평균·표본 표준편차·평균 CI·중앙값·P5·P95·컷 초과확률과 CI·니케별 표), OL 가상 후보 비교표.

표시 규칙(모두 회귀로 고정):

- 값이 없으면 `미확인`, 지원하지 않으면 `미지원`, 표본이 없거나 1건이면 `표본 없음` / `표본 1건 · 산포/신뢰구간 없음`. 정상 0은 0으로 표시하고 미확인과 구분한다.
- GPU는 payload가 self-test·정확성·성능 검증 통과를 말한 장치만 `사용 가능`이고 고급 선택지에 나온다. 이름만 탐지되었거나 FP64 미지원 등으로 단계가 낮은 장치는 사용 불가로 표시하고 선택지에서 뺀다.
- 실제 backend가 진실이다. GPU 지정이 CPU로 떨어지면 fallback 원인과 함께 "GPU 성공으로 표시하지 않습니다"를 띄운다.
- 평균 CI와 P5·P95를 한 줄로 구분해 적는다. 컷 확률과 CI는 별도 카드다.
- OL 후보는 차이 CI가 0을 포함하면 `우열 미확정`이다. 가상 변경이며 원본 장비를 수정하지 않는다는 안내를 고정 문구로 둔다. 모듈 비용·확률 UI는 만들지 않았다.
- 중단된 불완전 전투 수는 표본에서 제외했다고 별도로 적는다. 재개는 새 attempt이며 이전 결과를 중복 집계하지 않는다는 payload 문구를 그대로 보여 준다.

## 3. 검증

| 명령 | 결과 |
|---|---|
| `node tests/ui/single_deck_stats.test.mjs artifacts/ui/single-deck-stats/unit` | 12/12 통과 |
| `python tests/ui/check_single_deck_stats_browser.py` | 통과 · 증거 `artifacts/ui/single-deck-stats/run-a3807cbf7870/` |
| `node tests/q3/check_ui_contract.mjs <engine result.json>` | 26/26 통과 |
| `python tests/ui/check_solo_raid_level.py` | 통과 (요청 `scenarioLevel` 400/400) |
| `node tests/ui/damage_audit.test.mjs <saved replay> …` | 19/19 통과 |
| `python tools/data-pipeline/tests/check_damage_log_ui.py` | 통과, JS 오류 0 |

단위 테스트(합성 fixture): 검증 단계별 GPU 사용 가능 판정과 선택지 노출, CPU/GPU 표기 분리와 fallback, 배치 상태별 버튼·카운트·진행률, 평균 CI와 분위수 분리, n=0/1·정상 0·미지원 지표, OL 판정 3종과 빈 결과, 고정 400·DEF 정책 문구, 출처 배지, HTML escape, 컨트롤러의 엔드포인트 부재 처리와 실행→취소→재개 흐름.

브라우저 상태 검증(`evidenceKind: synthetic_http_fixture`, 기준 커밋 `a5ccba6` 위 미커밋 상태):

- 장치 선택지 `['자동 선택 (권장)', 'CPU', 'GPU · 합성 GPU 검증본']` — 이름만 탐지/정확성 실패 장치는 제외.
- 탐지 실패 재측정 후 선택지 `['자동 선택 (권장)', 'CPU']`, `probe timeout` 원인과 CPU fallback 구분 문구 확인.
- 실행 → 완료: n 1,000, 평균 95% CI `152,083,461.2 ~ 152,681,125.6`, 컷 초과확률 68.3%, 니케별 표, OL `우열 미확정` 포함.
- 취소 → `취소됨`·`부분 결과`·`미지원` 지표·`표본에서 제외` 문구.
- 재개 → `실행 중`과 "중복 집계하지 않습니다" 문구, attempt 2.
- 재시작 복구 → 저장된 batch id `batch-synthetic-2`로 새로고침 후 `재시작 복구` 표시.
- 1500/850/500px 가로 넘침 0(표는 자체 스크롤 영역), JS 예외 0. 격리 정적 서버에 초상화 이미지가 없어 생기는 404 22건은 자산 경고로 분리 기록.
- 기존 솔로 레이드 화면 유지 확인: `#replay-form`의 레벨 입력 0개.

## 4. 미완료·의존

- 실제 배치 API·하드웨어 탐지 응답과의 종단 연결(B-CPU 계약 확정 후). 현재 화면은 계약 확정 전 상태를 명시적으로 표시한다.
- 실제 CPU/GPU 장치에서의 탐지·실행·성능은 이 작업에서 측정하지 않았다. fixture의 벤더/장치 이름은 합성이며 특정 벤더 검증 근거가 아니다.
- 통계 산출 자체는 S-CPU, 엔진 summary 경로와 GPU kernel은 E-CPU, 대규모 부하 측정은 Q-CPU 소유다. 이 화면은 받은 값을 표시만 한다.
- 비용 효율·모듈 예산 추천 UI는 자료 확인 전이라 만들지 않았다(P08-B/C 후속).
- 현재 결과 표시는 모델 기반 실험이며 게임 영점·자동 DEF 전환 검증과는 구분한다.

## 5. 보존

원본 계정 DB·세션·캐시, 5180/5181 서버, EXE·바로가기, 다른 worktree를 변경하지 않았다. 새 검증 결과는 자기 작업공간의 git 제외 `artifacts/ui/single-deck-stats/`에만 남겼다. 원격 push와 새 워커 생성은 하지 않았다.
