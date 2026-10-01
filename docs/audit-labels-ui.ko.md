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
| `app.js` 98~107, 156~172, 226·239, 321 | `error.message`(전송 실패 영문 등) | `errorText(error)` — 등록 문구만 통과, 그 외 일반 문구 (QA 2차 차단 후 허용 목록) |
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

공용 helper는 `display-labels.js`의 `errorText(error)`·`koreanText(raw, fallback)`·`friendlyServerMessage`·`reasonLabel`·`describeChange`다. **허용 목록 방식**(QA 2차 차단 후 구조 전환, 6절)이다: 서버·저장 문자열은 (a) 매핑된 코드, (b) `registered-messages.js`에 등록된 정확한 한국어 문구(서버·수집기 소스의 리터럴에서 `tests/ui/tools/gen_registered_messages.mjs`로 생성)일 때만 화면에 나오고, 그 외는 내용과 무관하게 일반 한국어 문구다. `CODE_LIKE` 같은 차단 정규식은 제거했다. UI가 직접 만든 한국어 오류는 `displayError`(`display: true`)로 표시한다.

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

### 반려 2회차 (astra-6, 커밋 518e3ab)

- `damage-log-adapter.js:379·374` — client_f32의 `final`·`effectiveDefense`가 operation이 비어 있지 않기만 하면 미등록 값(`weird`)도 확정 설명. → `final`·`effectiveDefense`는 엔진이 쓰는 등록 연산 문자열과 정확히 일치할 때만 설명하고(정책으로 추정하지 않음), 그 외 모든 단계도 `KNOWN_OPERATIONS`(HitCalculator 등록 연산) 안의 값일 때만 단계별 설명을 쓴다. 미등록·누락은 `저장된 연산 미확인`.
- 테스트: `u_fix_7_missing_operation_is_unknown_not_guessed`에 client_f32의 미등록 `final`·`effectiveDefense`, 전 단계 이름 × (미등록/누락) 케이스, 등록 연산의 정상 설명 추가. `node --test tests/ui/*.test.mjs` 6/6 통과.

### QA 1차 차단 (독립 QA, 커밋 b401421)

- **U7-Q-1** `damage-log-adapter.js` B3~B5 — 접두사만 검사해 `multiply 1.25; qa_unknown_transform`을 `× 1.25 곱함`, `multiply 1.25; floor_if_qa_condition`을 `곱한 뒤 내림`으로 단정. → 전체 문자열이 `multiply <값>` 또는 `multiply <값>; floor`(엔진 등록 형태)와 정확히 일치할 때만 설명하고 그 외는 `저장된 연산 미확인`. 다른 단계는 이미 `KNOWN_OPERATIONS`/`final`/`effectiveDefense`의 정확 일치 검사이며 접두사 검사는 남아 있지 않다.
- **U7-Q-2** `display-labels.js` `CODE_LIKE` — `검사 필요: effectiveAttack`, `검사 필요: calculation.terms`처럼 한국어와 lowerCamelCase·점 경로가 섞이면 통과. → lowerCamelCase(`\b[a-z]+[A-Z]\w*`)와 점 경로(`\w+\.[A-Za-z_]\w*`)를 코드 형태에 추가. 섞인 문장은 `koreanText`/`friendlyServerMessage`/`reasonLabel`에서 한국어 대체 문구로 바뀐다. 정상 한국어 문장(`3.5배`, `LV.5` 등)은 통과하도록 확인.
- **U7-Q-3** (기존 결함) `damage-log.js` — 로그 없음(`api_error`·`unsupported_schema`·미로드)에서 `log:null`로 `generateGraphSvg(null)` 예외. → 로그가 없고 `no_damage`가 아니면 상태별 한국어 안내(`피해 로그를 불러오지 못했습니다` 등)를 표시하고 그래프 생성을 건너뛴다. Mock 미리보기 버튼은 미수집 상태에서만 표시.
- 테스트(QA 재현과 같은 입력): `damage_audit` — 위 두 접미사·유사 변형의 B3~B5; `display_labels` — 혼합 문자열 5종과 정상 문장, 전송 실패(`TypeError: Failed to fetch`, HTTP 500) 시 viewer가 예외 없이 한국어 안내를 렌더하고 원문·그래프가 없음. `node --test tests/ui/*.test.mjs` 6/6 통과.
- 전수 목록 보정: `damage-log.js` 로그 조회 실패 행은 `errorText`에 더해 위 안내 화면까지 이어지도록 수정.

### QA 2차 차단·구조 전환 (독립 QA 재수용, 커밋 8da098f)

QA 재수용에서 잔여 2유형이 남았다: (1) `buildDamageBreakdown`이 접두사 정규식으로 B3~B5 배율을 읽어, 표는 미확인인데 상단 `B3 × B4 × B5` 카드는 `1.25 × 1.25 × 1.25`(끝 개행·`0x10`·`0b11` 포함)로 표시, (2) `CODE_LIKE`가 `terms[].name`, `terms[0].operation`, `cache/replays`, `runtime\catalog`, `skill1Rate` 같은 변형을 통과. 원인은 내부 문자열을 정규식 차단 목록으로 골라내는 구조여서 변형이 계속 새는 것이다. 사용자 승인(A안)에 따라 **허용 목록 방식**으로 구조를 바꿨다.

1. **서버·저장 문자열 → 허용 목록:** `friendlyServerMessage`·`koreanText`·`errorText`·`reasonLabel`은 매핑된 코드 또는 등록된 정확한 문구만 통과시키고, 한국어 문장에 내부 경로가 섞였든 아니든 등록되지 않으면 일반 문구(`요청을 처리하지 못했습니다`, `기타 사유`, 호출부 한국어 대체 문구)를 쓴다. 등록 목록은 서버 소스에서 생성(`registered-messages.js`, 212개)하며, 동기 검사가 테스트에 있다(`registered_messages_match_server_sources`). 정규식 `CODE_LIKE`와 `[가-힣]` 통과 규칙은 모두 삭제했다.
2. **새로 허용 목록으로 바꾼 표시 지점:** `app.js` 변경 이력(`describeChange` — 등록 템플릿만, 이름은 알려진 표시명일 때만, 슬롯은 `slotLabel`), 이미지 갱신 상태(`imageMessage` — 등록 문구 아니면 상태별 한국어 문구), `combat-conditions.js` 호환 모드 `label`(등록 문구만), 장치 `reason`(`reasonLabel`은 등록 사유만, 미등록은 `기타 사유`). api()가 만든 오류와 UI가 직접 던지는 한국어 오류는 `display: true`로 구분한다.
3. **배율·연산 해석:** `parseMultiplyOperation`이 `multiply <십진수>` 또는 `multiply <십진수>; floor` 전체 일치만 받는다(십진수는 `-?(0|[1-9]\d*)(\.\d+)?(E[+-]?\d+)?`). 끝 개행, `0x10`, `0b11`, 앞 0, 공백 2개, 접미사는 모두 미확인이다. 단계 표 설명과 `B3 × B4 × B5` 카드가 같은 함수를 쓰므로 일관된다(`buildDamageBreakdown`의 접두사 정규식 삭제).
4. **유지:** UI가 직접 쓰는 한국어(`3.5배`, `GPU`, `LV.5`, 이름 미확인 등), 타격·발사·버스트 시전 번호, replay ID, fingerprint·버전·schema, 정책 id, 준비 스크립트 이름, 장치 식별 해시는 허용 목록 필터를 거치지 않는다.
5. **리뷰 비차단 반영:** `damage-log.js` 조사 `로그를` → `로그가`(미수집 문구). 이전 단계에서 `logMessage`를 `koreanText`로 걸러 어댑터가 만든 한국어 안내가 가려지는 문제도 되돌렸다(어댑터 문구는 서버 문자열이 아니다).
6. **테스트:** QA 형태(`terms[].name`, `terms[0].operation`, `attackBuffs[0].source`, `cache/replays`, `runtime\catalog`, `skill1Rate`, `multiply 1.25; qa_unknown_transform`, `0x10`, 등록 문구 뒤 추가 문자열·끝 개행)를 `display_labels`(허용 목록·변경 템플릿·등록 동기)와 `damage_audit`(카드·표 일관)에 추가했다. 정상 한국어·`3.5배`·`GPU`·`LV.5` 회귀 포함. 앞 절의 `CODE_LIKE` 보강(QA 1차 U7-Q-2 수정)은 이 구조 전환으로 대체되었다. `node --test tests/ui/*.test.mjs` 6/6 통과, 격리 서버에서 페이지 로드 오류 없음.
