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

리뷰 통과 후 Director 통지. F2-Q-6 재현 경로·전수 목록의 화면 텍스트를 실제 격리 API·브라우저로 자체 검사하고 이전 F2 수용 항목 회귀. 담당 검사·mock·정답 재사용 금지.

## 전달 확인

(세션 준비 후 기록)
