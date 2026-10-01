# 피해 검산 표 표시 정리 — U-FIX-7 (새 구조 첫 작업, 2026-10-01)

## 근거

배포된 F-COND-2의 알려진 표시 결함 F2-Q-6([검수 기록](combat-conditions-cleanup-assignments-2026-09-29.ko.md), QA `180f23b`): 피해 검산 표에 저장 구조의 키·서버 문자열이 그대로 보인다 — 제목의 `calculation.terms`, 단계 부제의 `effectiveAttack`/`effectiveDefense` 등 `terms[].name`, 저장된 영문 `operation`. Director 확인 위치: `apps/desktop-ui/damage-log.js` 125행(`s.name` 부제), 128행(`s.operation`), 133·160행(`calculation.terms` 문구), 135행(누락 항목 이름), 149행 "(hit 기록)".

화면 표시 원칙(사용자 확정, [요구 문서](user-requests-2026-09-29.ko.md)): 화면에는 이름. 캐릭터 코드·내부 키·함수 번호·서버 원문 금지. 유지: 타격·발사·버스트 시전 번호, replay ID, fingerprint·버전·schema, 대미지 정책 id, 조치 안내의 준비 스크립트 이름, 장치 식별 해시.

## 작업 구조

[구현·리뷰·QA 작업 구조](workflow-implement-review.ko.md)를 따른다.

- 흐름: 구현(sonnet-5.5) → 리뷰(astra-6, 차단 7항목) → 독립 QA → Director.
- 사고 수준: 구현 high로 계획했으나 **사용자가 구현 세션을 medium으로 설정**해 medium으로 진행 / **리뷰 medium** / **QA high**. 반려 후 구현은 한 단계 상향(high).
- 리뷰 결과: 통과|반려 + `파일:줄 — 항목 번호 — 이유`, 빌드·테스트 1회 결과 포함.

## 구현 (UI worktree, sonnet-5.5)

기준: 원본 `main` = Director `3d84fe4`(배포본). UI 브랜치는 `59fe22d`이므로 먼저 Director `3d84fe4`를 일반 merge한다. 소유: `apps/desktop-ui/**`, UI tests, 보고서 `docs/audit-labels-ui.ko.md`.

1. 피해 검산 표: 단계 이름은 한국어 항목명(내부 name 부제 삭제), 연산 설명은 단계별 한국어 설명(저장된 영문 operation 직출력 금지), 제목·누락 안내의 `calculation.terms`·`hit` 같은 구조 경로 삭제. 수식 기호(B, float32 등)는 허용. API·저장·`data-term`·수치·export 유지.
2. **전수 조사:** `apps/desktop-ui` 전체에서 저장·서버 데이터의 문자열 필드(name, operation, code, path, source, message, reason, type 등)를 변환 없이 화면에 넣는 모든 지점을 찾아 목록(파일:줄·필드·처리)으로 보고하고 같은 원칙으로 정리한다. 유지 번호는 그대로.
3. 실제 격리 API·브라우저 확인(원본 `data/local`·5180/5181 불변, EXE 배포 금지), 기존 회귀 유지.
4. 커밋 후 Director에 한 번 인계(확정 커밋·보고서·전수 목록·검증 결과).

## 리뷰 (UI worktree, astra-6)

Director 통지 후 구현 커밋이 확정된 상태의 UI worktree에서(파일 수정·커밋·merge 없이), [차단 7항목](workflow-implement-review.ko.md)으로 diff를 판정한다. 빌드·테스트 1회. 코드 수정·실험·종단 검증·범위 밖 요구 금지. 결과를 Director에 한 번 인계.

## QA (검수 worktree)

리뷰 통과 후 Director 통지. 대상: UI `b401421`(검수 `180f23b`에 일반 merge, 충돌 시 보고). F2-Q-6 재현 경로·전수 목록(구현 보고서 2절)의 화면 텍스트를 실제 격리 API·브라우저로 자체 검사하고 이전 F2 수용 항목 회귀. 담당 검사·mock·정답 재사용 금지. 사고 수준 QA high(표시 전용 변경, 계산 불변).

- 구현·리뷰가 하지 않은 것(QA 몫): 검산 저장 → 타격별 근거 화면 종단(실제 격리 API + Chromium), 전수 목록 표시 지점의 실제 화면 확인(전송 실패·미등록 코드·미등록 연산·자동 버스트 사유 등 예외 경로 주입 포함).
- 확인 항목: 피해 검산 표 금지어(`calculation.terms`, `effectiveAttack`, `effectiveDefense`, `multiply`, `identity`, `native +`, `checked int64`, `float32 left`, `(hit`) 0, 단계 표 전 행 한국어 설명, 미등록·누락 연산은 `저장된 연산 미확인`(추정 설명 없음), `data-term`·저장 `operation`·API·export·수치(19,462건·팀 24,007,922,311) 불변, 이전 F2 수용 항목(R4 엔진 87, DEF 6조합, 보스 43·이미지 42, 조건 wire) 회귀, `/legacy` 제외.
- 보존: 원본 `data/local`·5180/5181·원본 EXE·계정 DB 접근 금지, `package-lock.json` 비커밋, 격리 포트·별도 dataRoot만 사용.

## 전달 확인·진행

| 단계 | 담당·터미널 | 요청 ID | 결과 |
|---|---|---|---|
| 구현 배정 | Sonnet 5.5 `term_c322a450…` | `c3628d2f-4709-4cf4-880c-e21345b40376` | `turn_started` |
| 구현 인계 | — | — | 확정 UI `4622860`(`3d84fe4` ff 위), 보고서 `UI/docs/audit-labels-ui.ko.md`(2절 전수 목록: 수정 지점·변경 안 한 지점과 사유). 변경 15파일 — `apps/desktop-ui`·UI tests·UI 문서(제품 `src`·QA `tests/q3` 0). 구현 보고: `node --test tests/ui` 6/6, 저장 replay(검수 archive 읽기 전용) Chromium 렌더 금지어 0, 격리 포트 `/editor/` pageerror 0. 미실행: 검산 저장 → 근거 화면 종단(QA 몫) |
| 리뷰 배정 | astra-6 `term_cfa51db6…`(UI worktree, 파일 수정 금지) | `34a3f5d7-c5c7-4dbd-a2ff-d90a981b6fce` | `turn_started` |
| 리뷰 1차 | astra-6 | — | **반려(차단 2)**: (1) `apps/desktop-ui/app.js:357` 자동 버스트 요약 `waitingReason`·`timeline[].reason`이 미등록이면 원문 출력(`reasons[key] ?? key`), 전수 목록에도 누락 — 항목 3. (2) `apps/desktop-ui/damage-log-adapter.js:377` final의 operation이 누락·미등록이면 round로 시작하지 않는 한 "내림"으로 단정(`final_round_even` 저장 항목에서 operation 누락 시 정책과 반대 설명) — 항목 5. 비차단 없음. 리뷰어의 테스트 1회(`node --test tests/ui`)는 디렉터리 경로 진입 실패(MODULE_NOT_FOUND)로 실제 6파일 미실행 — 구현 회귀 아님, 재리뷰 시 `node --test tests/ui/*.test.mjs` 사용 |
| 재작업 | 구현 ⇄ 리뷰 직접 왕복으로 전환 | — | 반려 1회차. 사고 수준 상향(high)은 사용자 확인 |
| 직접 왕복 | 구현 `518e3ab` → 리뷰 반려 2회차(client_f32 `final`·`effectiveDefense`의 미등록 operation도 확정 설명) → 구현 `b401421` | — | 이력은 구현 보고서 6절 "리뷰 이력" |
| **리뷰 최종** | astra-6 | — | **통과(`b401421`)**, 차단 0, 테스트 1회 6파일·내부 76/76, 비차단: 기존 모듈 형식 경고. 리뷰어는 Director에 전송(입력 수락)했다고 했으나 이 세션에 도착하지 않아 Director가 리뷰 터미널 화면으로 확인. 반려 2회 이내라 Director 판단 요청 없음 |
| QA 배정 | 검수 `term_234e279b…` | (아래) | Director 확인: `3d84fe4..b401421` 제품 `src`·QA `tests/q3` 변경 0, QA 브랜치와 충돌 없음 |
| QA 배정 사고 | — | `4464b839…` | 검수 터미널의 Codex 세션이 이미 종료돼 지시문이 PowerShell 명령으로 실행됨("명령 없음" 오류, 부작용 없음). Director가 `codex resume --last`로 재개를 시도했으나 최근 세션(리뷰어 대화)을 잡아 중단. 사용자가 QA 세션을 새로 준비(GPT-6-Astra high, Full access) |
| QA 재배정 | 검수 `term_234e279b…` | `bc872612-a130-4821-b6e1-1f9ebaf61bbe` | `turn_started`. 새 대화일 수 있어 역할·이전 QA 보고서·규칙을 지시에 포함 |
| 리뷰 2·3차 | 구현 ⇄ 리뷰 직접 왕복 | — | 반려 2회(1차 `4622860`: app.js 자동 버스트 사유 원문·final 연산 단정, 2차 `518e3ab`: client_f32 final·effectiveDefense 미등록 연산 확정 설명). 구현 보고서 6절 리뷰 이력에 누적 |
| 리뷰 최종 | astra-6 → Director 1회 | — | **통과(2026-10-01)**: 확정 UI `b401421`(`3d84fe4` ff 위, `4622860`→`518e3ab`→`b401421`), 보고서 `UI/docs/audit-labels-ui.ko.md`. 차단 7항목 위반 없음. 리뷰어 테스트 1회 `node --test tests/ui/*.test.mjs` exit 0, 6/6 파일·내부 76/76. 비차단: 기존 `MODULE_TYPELESS_PACKAGE_JSON` 경고. Director 확인: 변경 15파일 모두 `apps/desktop-ui`·`tests/ui`·UI 보고서(제품 `src`·QA `tests/q3` 0), 원본 `main`=`3d84fe4` 위 fast-forward. **코드 리뷰 통과일 뿐 QA·통합·EXE 배포는 미완료.** |
| QA 배정 | 검수 worktree(Codex) | — | **대기(미전달)**: 검수 터미널 `term_234e279b…`·`term_e86b74e5…`가 Codex 세션 없이 셸 프롬프트 상태라 셸 오입력 위험으로 전달하지 않음. 사용자가 검수 세션을 연 뒤 아래 QA 절 기준으로 전달 |
| **QA 1차** | 검수 | — | **전체 수용 차단(3결함)**. 검수 `706d7fd`(UI `b401421` ff), [QA 보고서](C:/Users/user/orca/workspaces/Nikke-Simul/검수/docs/audit-labels-qa.ko.md), 증거 색인 검수 `artifacts/single-deck-qa/ufix7-preparation/evidence-index.json`. 새 검사 1025 중 1020 통과. 정상 저장본의 F2-Q-6 표시 수정은 수용, 기존 F2 회귀 전부 통과(피해 19,462건 독립 산술, 팀 24,007,922,311). QA 커밋 제품 변경 0 |
| QA 결함 | — | — | **U7-Q-1** `damage-log-adapter.js:398/401` B3~B5 operation을 접두사만 검사 — `multiply 1.25; qa_unknown_transform`을 "× 1.25 곱함", `multiply 1.25; floor_if_qa_condition`을 "곱한 뒤 내림"으로 단정(전체 문자열이 미등록이면 "저장된 연산 미확인"이어야 함). **U7-Q-2** `display-labels.js:76/112~114` → `app.js:251` 고급 진단 `issues[].message`의 `검사 필요: effectiveAttack`·`검사 필요: calculation.terms`처럼 한국어 + lowerCamelCase/점 경로가 섞인 문자열이 `CODE_LIKE`를 통과해 그대로 표시. **U7-Q-3**(기존 결함, `3d84fe4`에도 있음) damageLog 없이 만든 replay에서 `/damage-log` 조회가 실패하면 adapter가 `log:null`을 반환하는데 `damage-log.js:249`가 처리하지 않아 `:324→:594 generateGraphSvg(null)` 예외, 한국어 오류 안내 대신 빈 영역 |
| 수정 배정 | Sonnet `term_c322a450…` | (아래) | 세 결함 모두 수정, 구현 ⇄ 리뷰 직접 왕복 후 리뷰 통과 시 Director → QA 재수용 |
| **리뷰(QA 1차 수정)** | astra-6 | — | **통과(`8da098f`)**, 차단 0. U7-Q-1 B3~B5 임의 접미사·floor 유사 접미사 거부, U7-Q-2 한국어에 섞인 lowerCamelCase·점 경로 대체, U7-Q-3 로그 없는 api_error·unsupported_schema·미로드 안내 후 그래프 생성 회피. 테스트 1회 6파일·내부 78/78. 비차단: `damage-log.js:274` 조사 다듬기("로그를"→"로그가"), 기존 모듈 형식 경고. Director 확인: `b401421..8da098f` 6파일, 제품 `src`·QA `tests/q3` 0, QA `706d7fd`와 충돌 없음 |
| QA 재수용 배정 | 검수 `term_234e279b…` | (아래) | U7-Q-1~3 재검 + 회귀 |
| **QA 2차(재수용)** | 검수 | — | **전체 수용 차단(잔여 2유형)**. 검수 `f5a8057`(UI `8da098f` merge `89e903e`), QA 보고서 맨 위 재수용 절, 증거 색인 검수 `artifacts/single-deck-qa/ufix7-readmission/evidence-index.json`. 원래 U7-Q-1·2·3 최소 재현은 모두 수정 수용, 이전 1,025항목 전부 통과, 확장 포함 1,173 중 1,157 통과·16 실패. **U7-Q-3 수용**(11경로 × 7검사 77/77). F2·client_f32·통계·source·진단·엔진 회귀 전부 통과 |
| QA 잔여 | — | — | **U7-Q-1 잔여**: `damage-log-adapter.js:670/673` → `damage-log.js:103` 상단 "B3 × B4 × B5" 카드가 `buildDamageBreakdown`의 접두사 정규식으로 미등록 연산(`multiply 1.25; qa_unknown_transform` 등)의 배율을 여전히 추정 표시(단계 표는 미확인으로 정상). 끝 개행·`0x10`/`0b11` 숫자 표현도 같은 유형. **U7-Q-2 잔여**: `display-labels.js:76` 공통 판별식(deny 정규식)이 `terms[].name`, `terms[0].operation`, `cache/replays`, `runtime\catalog`, `skill1Rate` 같은 형태를 놓쳐 고급 진단·연결 실패·검산 400·장치 사유 화면에 노출 |
| Director 판단 | — | — | 결함이 매 회차 같은 두 유형의 변형으로 반복된다 — 원인은 **차단 목록(정규식)으로 내부 문자열을 골라내는 구조**. 남은 처리 방향은 사용자 확인 대기(허용 목록 구조로 1회 전환 vs 알려진 결함으로 두고 배포) |
