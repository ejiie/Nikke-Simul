# U-FIX-7 — 피해 검산 표 표시 정리 (구현 보고)

지시서: Director `docs/audit-labels-assignment-2026-10-01.ko.md`. 구현 담당 sonnet-5.5(사용자 설정 medium). 기준 Director `3d84fe4`를 UI 브랜치에 일반 merge한 뒤 작업했다.

## 1. 피해 검산 표 (F2-Q-6)

| 위치 | 이전 | 이후 |
|---|---|---|
| `damage-log.js` 단계 표 이름 칸 | 한국어 이름 + 부제 `terms[].name`(`effectiveAttack` 등) | 한국어 항목명만 (부제 삭제). `data-term` 속성은 유지 |
| 단계 표 4열 | 머리글 "저장된 연산", 저장된 영문 `operation` 직출력 | 머리글 "연산 설명", 단계별 한국어 설명 (`describeStepOperation`) |
| 계산 단계 제목·누락 안내 | `calculation.terms`·`terms 배열` 문구 | "저장된 단계별 기록"·"저장된 단계별 계산 기록" |
| 누락 항목 이름 | `charge, P` 같은 키 | 한국어 항목명 (`missingLabels`; 키 `missing`은 데이터에 유지) |
| 공격력 입력 제목 | "(hit 기록)" | "(타격 기록)" |
| 알 수 없는 항목 | `기록 항목 <키>` | `기록된 계산 항목` / 설명 `저장된 연산 미확인` |
| 보조 문구 | `hit 입력 기준`, `발사 / Hit`, `(Hit #n)` | `타격 입력 기준`, `발사 / 타격`, `(타격 #n)` |

저장 데이터(`steps[].operation`, `missing`, API, export)와 수식 기호(B, float32, damageRatio 등)는 그대로다. 곱셈 단계(B3~B5)는 저장된 `multiply <값>`에서 값만 읽어 "× 값 곱함"으로 표시한다.

## 2. 전수 목록 — 저장·서버 데이터 문자열을 화면에 넣는 지점

기준: `apps/desktop-ui` 전체의 `innerHTML`/`textContent`/템플릿 삽입을 훑어, 서버·저장 문자열(name, operation, code, path, source, message, reason, status, error)이 변환 없이 들어가는지 확인했다. 파일:줄은 수정 후 기준이다.

### 수정한 지점

| 파일:줄 | 필드 | 처리 |
|---|---|---|
| `damage-log.js` 125·128 | `terms[].name`, `operation` | 이름 부제 삭제, `description`(한국어) 표시 |
| `damage-log.js` 133·135·160·149 | `calculation.terms` 문구, `missing` 키, `(hit 기록)` | 위 표 참조 |
| `damage-log-adapter.js` `termLabel` | 미등록 term name | 키 대신 `기록된 계산 항목` |
| `damage-log-adapter.js` `classifyBuffForHit` | 이유 문구 `타격 계산 입력(hit)` | `타격 계산 입력` |
| `damage-log.js` 내보내기 오류 | 서버 응답 본문 `errText` | 본문 제거, `서버 로그 내보내기 실패 (HTTP n)` |
| `damage-log.js`·`damage-log-adapter.js` (전술 저장·조회, 로그 조회 실패) | `err.message` | `errorText(err)` |
| `app.js` 98~107, 156~172, 226·239, 321 | `error.message`(전송 실패 영문 등) | `errorText(error)` — 한국어만 통과, 그 외 일반 문구 |
| `app.js` 168 | `update.message`(이미지 갱신 상태) | `koreanText` |
| `app.js` 178 | `connection.message` | `koreanText` |
| `app.js` 183·185·187·189 | `connectionFailure.message`, `c.message`, `j.message` | `koreanText` + 한국어 대체 문구 |
| `app.js` 197 | `presentation/refresh` `result.message` | `koreanText` |
| `app.js` 251 | `snapshot.issues[].message` | `koreanText` (`data-issue-path` 속성은 유지) |
| `compute-adapter.js` `describeComputeError` | 미등록 오류 코드 `오류 코드 <code>` | `알 수 없는 오류로 실패했습니다.` |
| `compute-adapter.js` 같은 함수 | `Analysis`, `snapshot`, `phase`, `hitOverrides`, `warmup`, `baselineExperimentId` | 통계 모듈·스냅샷·단계·타격 보정·예열·기준 실험 |
| `compute-adapter.js` `classifyApiFailure` | 표시용 `message` | `errorText`. 코드 판별은 원문(`serverMessage`)을 계속 사용 |
| `compute-adapter.js` 33행대 | `stageLabel` 미등록 `상태 <키>`, 배치 상태 `상태 <키>` | `상태 미확인` |
| `compute-adapter.js` | 장치 backend `기타 (<값>)` | `기타 장치` |
| `compute-adapter.js` | `probeFailures[]` 서버 문자열 | `koreanText` |
| `single-deck-stats.js` 95·118 | `attempt n`, backend 원값, `driver` | `시도 n회`, CPU/GPU/기타 장치, `드라이버` |
| `single-deck-stats.js` 237 | 응답 판정 원값 | 개선/악화/미확인 |
| `app.js` 357 (`renderBurstSummary`) | 자동 버스트 `waitingReason`·`timeline[].reason` 원문 폴백 | 미등록 사유는 `대기 사유 미확인` (리뷰 반려 1회차) |
| `combat-conditions.js` 100 | 무기군 `label` 폴백 `r.weaponType` 원값 | `무기군 미확인` (같은 유형 재점검) |
| `combat-conditions.js` 376 | 사거리 오류 `reason` 원값 | `PROFILE_REASONS` 없으면 `사유 미확인` |
| `combat-conditions.js` 242 | 오류 폴백 `error.message`/`String(error)` | `errorText` |
| `raid-conditions.js` 183 | 보스 목록 오류 `e.message` | `errorText` |
| `burst-tactics.js` 154 | `e.message` | `errorText` |
| `formation.js` 85 | `error.message` | `errorText` |
| `local-lab-adapter.js` 150 | 저장 실패 `e.message` | `errorText` |

공용 helper는 `display-labels.js`의 `errorText(error)`·`koreanText(raw, fallback)`다. 규칙은 U-FIX-6과 같다: 한글이 있고 코드 형태(`snake_case`, 경로, 4자리 이상 숫자, camelCase)가 없으면 통과, 아니면 한국어 대체 문구.

### 확인했고 변경하지 않은 지점 (사유)

| 파일:줄 | 필드 | 사유 |
|---|---|---|
| `app.js` 29·178, `cards.js`, `formation.js` | `displayName`, `nickname`, 서버 라벨 | 이미 한국어 이름 |
| `app.js` 320 | `data-profile-error`(code) | 속성, 화면 비표시. 문구는 `profile.text`(한국어) |
| `combat-conditions.js` 188~214 | 무기군·속성 `label`, `m.name`, `distance.text` | 카탈로그 한국어 이름 |
| `raid-conditions.js` 98·140 | `boss.name` | 보스 이름 |
| `single-deck-stats.js` 117·125 | 장치 이름·벤더·식별 해시 | 장치 식별 해시는 유지 대상 |
| `damage-log.js` 정책 카드 | `b.policy` (`client_f32` 등) | 대미지 정책 id는 유지 대상 |
| `damage-log.js` 52~80 | `damageRatio`, `statDamageRatio`, `chargeDamageRate`, `breakRate` 등 | 수식 기호(허용) |
| `damage-log.js` 55, 245 | 타격·발사·버스트 시전 번호, replay ID | 유지 대상 |
| `burst-tactics.js` 263 | 검증 `issue.message` | 코드가 만든 한국어 문장 (code 필드는 비표시) |
| `local-lab-adapter.js` 103·116 | `rarityCode.toUpperCase()` (`SSR`) | 등급 표기 약어 |

## 3. 검증

- `node --test tests/ui/*.test.mjs`: **6 파일 모두 통과** (`damage_audit` 19항목 = 기존 18 + 신규 1, `single_deck_stats` 등). 신규 `u_fix_7_audit_table_has_no_stored_keys_or_english_operations`는 3개 정책 × 전 fixture 사례의 단계 표에서 저장 키·영문 operation·`calculation.terms`·`hit`이 없고 저장 `operation`은 데이터에 남는지 본다.
- 문구 변경에 맞춰 기대값을 고친 기존 테스트: `damage_audit` 누락 항목명(`charge` → `차지 배율`), `single_deck_stats` 오류 코드·`Analysis` 문구·장치 탐지 실패 문구, 브라우저 검사 스크립트의 같은 문구(`tests/ui/check_single_deck_stats_browser.py`, 실행은 하지 않음).
- Chromium 렌더: 검수 archive의 실제 저장 리플레이(client_f32, 읽기 전용, 파일 변경 없음)에서 서로 다른 타격 2종의 검산 패널을 `renderDamageAuditPanel`로 그려 금지어 목록(`calculation.terms`, `effectiveAttack`, `effectiveDefense`, `multiply`, `identity`, `native +`, `checked int64`, `float32 left`, `(hit`)이 없음을 확인했다. 단계 표 10행 모두 한국어 설명이다.
- 격리 API(임의 포트, 별도 dataRoot) 로드 확인: 아래 "격리 서버 확인" 참조.

## 4. 범위·보존

- 소유 경로만 수정: `apps/desktop-ui/**`, `tests/ui/**`, 본 보고서.
- 원본 `data/local`·5180/5181·원본 EXE·계정 DB는 접근하지 않았다(실행 중인 사용자 앱 프로세스도 종료하지 않음). `package-lock.json`은 커밋하지 않았다. push·배포·새 워커 없음.
- 엔진 계산·정책·규칙 버전·fingerprint 입력은 바뀌지 않는다(표시 전용), 따라서 규칙 버전 상향은 해당 없음.

## 5. 격리 서버 확인

- 이 worktree의 Release `Nikke.Api.dll`을 임의 포트(57802, 5180/5181 아님)에서 `NIKKE_PROJECT_ROOT`=UI worktree, `NIKKE_DATA_ROOT`=임시 폴더로 실행했다. 데이터는 검수 쪽 격리 합성 데이터(`load1000-…/data`의 `accounts.db`·카탈로그·runtime 등)의 **복사본**이며 원본 폴더는 읽기만 했다. 서버는 검증 후 종료했다.
- `/editor/`가 UI worktree의 최신 `app.js`(`koreanText` 포함)를 제공하고, 페이지가 `body[data-ready=true]`까지 로드되며 raid·고급·가져오기 탭 이동 중 JavaScript `pageerror`는 없었다. 콘솔 오류 4건은 전부 404 리소스 요청(합성 계정에 이미지 없음)이다.
- **한계:** 이 확인은 새 모듈 import/구문 오류가 없는지와 UI 제공 경로 확인이다. 실제 격리 API로 검산 결과 저장 → 타격별 근거 화면까지의 종단 확인은 하지 않았다(검산 실행에 필요한 합성 편성·리플레이 준비가 검수 하니스에 묶여 있음). 해당 경로는 위 3절의 저장 리플레이 Chromium 렌더와 단위 테스트로 대신했고, 종단 재현은 QA 몫이다.

## 6. 리뷰 이력

### 반려 1회차 (astra-6, 커밋 4622860)

1. `app.js:357` — 자동 버스트 요약의 `waitingReason`·`timeline[].reason`이 사전에 없으면 원문 출력(`reasons[key] ?? key`). → `reasonText`로 미등록은 `대기 사유 미확인`. 전수 목록(2절)에 추가.
2. `damage-log-adapter.js:377` — `final`의 operation이 없거나 미등록이면 `round`로 시작하지 않는 한 `내림`으로 단정. → 저장 연산이 없거나 `round…`/`floor`가 아니면 `저장된 연산 미확인`. 같은 유형(저장 연산을 정책으로 추정)인 `effectiveDefense`(비 client 정책·operation 없음), 보너스 항(거리·풀버스트·크리·코어: `floor`일 때만 `(내림)`), B3~B5(배율 값을 못 읽을 때)도 `저장된 연산 미확인`으로 바꿨다.
3. 같은 유형 재점검(`?? key`/`|| key` 원문 폴백, 미확인 값 추정): 전체 `apps/desktop-ui`에서 `LABELS[...] ?? 원값` 꼴을 다시 찾아 `combat-conditions.js:100`(무기군 원값 폴백)을 추가로 고쳤다. 나머지 폴백은 모두 한국어 미확인 문구다(`display-labels.js`, `compute-adapter.js`, `cards.js`, `local-lab-detail.js`, `single-deck-stats.js` 확인).
4. 테스트: `damage_audit.test.mjs`에 `u_fix_7_missing_operation_is_unknown_not_guessed` 추가(operation 없음·미등록 × final·방어·보너스·B3). `node --test tests/ui/*.test.mjs` 6/6 통과(damage_audit 20항목).
