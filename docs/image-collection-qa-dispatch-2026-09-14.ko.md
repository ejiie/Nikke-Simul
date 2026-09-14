# 이미지 2개 수집 실패 — 검수 담당 지시

사용자 승인: 이미지 수집 경고를 검수팀에 조사하도록 배정. 목표는 원인 조사·재현·수정 소유자 제안이며 제품 수정이나 배포를 배정한 것은 아니다.

## 기준과 작업 위치

- 본인 작업공간: `C:/Users/user/orca/workspaces/Nikke-Simul/검수`.
- 기준 커밋: Director `04a16be8cc0f84449d8b41ad9d37f53c692338df`.
- 적용 AGENTS.md, README, `docs/desktop-release-2026-09-12.ko.md`, `docs/desktop-ui-migration.ko.md`를 먼저 읽는다. 본인 상태·최근 기록을 확인하고 기존 변경과 package-lock.json을 보존한다. 안전한 조상 관계일 때 본인 브랜치만 기준 커밋으로 fast-forward할 수 있다. 충돌 시 reset/stash/강제 checkout으로 우회하지 말고 보고한다.
- 과거 Q3의 UI 실패는 후속 수정 및 Director 재검수로 해소됐다. 오래된 Q3 최종 메시지를 현재 미해결 목록으로 재사용하지 않는다.

## 조사 대상

사용자 경고: `이미지 2개를 수집하지 못했습니다. 다시 시도하세요.`

원본 스크린샷: `C:/Users/user/AppData/Local/Temp/orca-paste-1789141871788-4a5eeca5-e0ef-4db8-b2b1-ead18196a3e3.png`. 없으면 위 문구를 근거로 조사하고 이미지 열람을 가장하지 않는다.

- 현재 배포 EXE는 Director `artifacts/desktop/win-x64/Nikke Simul.exe`. 설정은 같은 폴더의 desktop.settings.json이다. 먼저 실제 파일/현재 실행 서버를 확인한다.
- 2026-09-12 배포 설정: 코드 Director, 포트 5180, 데이터 `C:/Users/user/Documents/GitHub/Nikke-Simul/data/local`.
- 5181은 별도 검산 복사본 서버였으며 본 계정 데이터와 혼동하지 않는다. 포트가 현재도 살아 있다고 가정하지 않는다.
- 읽기 대상: `src/Nikke.Api/PresentationService.cs`, `tools/data-pipeline/presentation_assets.py` 및 연결 이미지 준비 도구, `apps/desktop-ui/app.js`의 경고 표시 경로, 실제 presentation 캐시/manifest/상태.
- 이전 실행 검사의 '깨진 이미지 0'은 당시 화면에 표시된 이미지 검사다. 전체 수집 성공이나 이번 경고가 거짓이라는 증거가 아니다.

## 수행 범위와 수용 조건

1. 경고의 생성 경로와 '2개'의 집계 기준을 추적한다. 실패한 두 항목의 니케/리소스 ID, 이미지 종류, 요청 URL, 로컬 상대 경로를 식별한다. 현재 경고가 사라졌다면 현재 상태와 과거 재현 한계를 구분한다.
2. 각 항목의 HTTP 상태·응답 유형/이미지 시그니처·캐시 존재와 무결성·ID/이름 매핑을 점검한다. 원천 부재/주소 변경/일시 네트워크 실패/파싱·매핑/캐시·표시/오래된 상태 중 무엇인지 근거로 분류한다. 원인이 확정되지 않으면 가설별 반증 조건을 남긴다.
3. 필요 시 본인 `artifacts/image-collection-qa/<unique-run>/`에 필요한 비밀정보 없는 자료만 복사하여 재현한다. 공개 이미지 URL의 제한적 조회는 허용하지만 인증·계정 수집을 하지 않는다. fixture·모의 응답·실제 원천 요청 결과를 명확히 구분한다.
4. '기존 이미지가 정상인데 미수집으로 집계됨', '실패 재시도 후 정상 복구됨', '원천에 없어 대체 이미지가 필요함'을 구별한다. 실제 재시도는 격리 복사본에서만 한다.
5. `docs/image-collection-qa-2026-09-14.ko.md`에 두 항목별 증거, 재현 명령/결과, 원인, 영향 화면, Backend·데이터/UI 중 수정 소유자, 수정 후 회귀 수용 조건을 남긴다. 독립 진단 스크립트/테스트가 필요하면 본인 전용 경로에서 작성 가능하다. 제품 코드는 수정하지 않는다.
6. 조사 산출물만 관련 커밋으로 제출한다. '조사 완료'와 '제품 결함 수정 완료'는 구분한다. 미확인 항목은 확인 불가 이유와 필요한 최소 추가 정보까지 보고한다.

## 보존 경계

원본 계정 DB·세션·캐시·이미지·manifest, Director/다른 worktree, 기존 artifacts, 실행 EXE와 서버를 수정·종료하지 않는다. 사용자 서버의 이미지 갱신 POST, 동기화, 편성 저장, 계정 편집을 호출하지 않는다. 테스트용 다운로드도 원본 캐시 경로에 저장하지 않는다. 쿠키/토큰/개인정보를 콘솔·커밋·공개 링크에 노출하지 않는다. 새 워커·제품 구현 배정·push·배포·전역 승인 설정 변경 금지. 필요한 정상 도구 승인은 제품의 승인 절차를 사용하고 우회하지 않는다.

## 완료 전달

이번은 기존 터미널에 대한 일반 작업 전달이며 Run/Task/Dispatch를 만들지 않았다. `worker_done`이나 과거 lifecycle ID를 임의로 사용하지 않는다.

최종 보고 작성 후 Director의 현재 agent 터미널을 `terminal list --worktree 'path:C:/Users/user/orca/workspaces/Nikke-Simul/Director' --json`으로 재확인한다. 배정 시 Director는 `term_f54735fc-6293-41b3-ae3a-984fd0d5b42a`이며 셸 터미널과 구분한다. 같은 세션임을 확인한 후 Orca CLI `terminal send --terminal <Director handle> --text '[검수 완료: 이미지 수집] 결과 커밋 / 보고서 절대 경로 / 확인된 원인 또는 미확인 / 수정 담당 / 남은 조건' --enter --wait-submit 10 --json`으로 요약을 한 번 전달한다. 구체적인 요약으로 자리표시자를 바꾼다. 실행 파일은 `C:/Users/user/AppData/Local/Programs/orca/resources/bin/orca.exe`를 사용하고 지침을 먼저 읽는다.

accepted는 전달 접수이지 Director의 검수 통과가 아니다. 무응답만으로 재전송하지 않는다. 핸들이 불명확하거나 전달이 불가하면 최종 보고에 실패/미확인 상태를 기록하고 임의의 터미널로 보내지 않는다. 전송 후 본인 최종 응답으로 같은 결과와 전달 영수증을 남기고 대기한다.

## 배정 영수증

2026-09-14 기존 Q3 워커에게 한 번 전달했다. 작업공간 ID는 `07c470de-0a43-4d90-9eb6-240a5de9258c::C:/Users/user/orca/workspaces/Nikke-Simul/검수`, 터미널은 `term_30f7a75f-412b-4f2f-9bd3-863c417a5e7e`다. 요청 `441a0be8-8f0c-497d-9a4c-7f945c5f6fc9`에서 `accepted=true`, `input_accepted`, `turn_started`를 확인했다. 이는 조사 착수 증거이며 조사 완료나 원인 확정이 아니다. 새 워커/Run/Task/Dispatch를 생성하지 않았으며 다른 담당에게 구현을 중복 배정하지 않았다.
