# 이미지 카탈로그 경로 결함 — 구현·회귀 검수 배정

사용자 승인: 조사 결과에 따른 업무 배정. Backend는 제품 수정, 검수는 독립 검증을 맡는다. 일반 Orca 터미널 전달이며 신규 worker/Run/Task/Dispatch를 생성하지 않는다. 배포는 이 배정에 포함하지 않는다.

## 공통 기준과 경계

아래 기준·배정·전달 확인은 **배정 당시의 기록**이다. 이후 B-IMG `1046460`, Q-IMG `d67204b`가 완료됐고 사용자 승인으로 Director에 `d67204b`까지 fast-forward 통합했다. 후속 배포 범위와 실제 검증 결과는 [Director 배포 기록](desktop-release-2026-09-14.ko.md)을 참조한다. 당시 Backend/검수에게 금지한 원본·배포 변경 권한을 소급해 넓히는 것은 아니다.

- 제품 기준 Director `04a16be8cc0f84449d8b41ad9d37f53c692338df`, 독립 조사·도구 커밋 `b1d37d2321a47587e5e57f94d7a0bce60775f407`(04a16be의 후속). 이번 공통 작업 기준은 b1d37d2다. Director HEAD 자체는 아직 04a16be이므로 이미 병합됐다고 가정하지 않는다.
- 본인 작업공간에서 지침/README/`docs/desktop-release-2026-09-12.ko.md`/`docs/image-collection-qa-2026-09-14.ko.md`를 끝까지 읽는다. Backend는 안전한 조상 관계·미커밋 겹침 없음 확인 후 자기 브랜치만 b1d37d2로 fast-forward한다. 검수는 기존 b1d37d2 및 자기 변경을 보존한다. 강제 reset/checkout/stash, 다른 worktree 편집 금지.
- 원인: 이미지 2장 누락이 아니라 account/spec 카탈로그 준비 실패 2건. 출력은 외부 presentation이지만 helper 입력은 코드 ROOT/data/local을 읽는다. 현재 357개 캐시 이미지는 정상이며 경로 의존 파일 대조군에서 unresolved 2→0을 재현했다. 이미지 추가·캐시 삭제·계산 자료를 Director에 복제하는 방식으로 고치지 않는다.
- 원본 데이터 `C:/Users/user/Documents/GitHub/Nikke-Simul/data/local`, 사용자 5180/5181 서버·EXE·캐시·세션·기존 artifacts는 수정/갱신/종료하지 않는다. 원본은 필요한 공개 카탈로그·이미지만 읽기/복사 가능하다. DB/인증 세션을 복제하지 않는 fixture를 우선한다. API 갱신 POST는 자기 artifacts 아래 새 데이터와 별도 임의 포트 서버에서만 실행한다.
- 새 실행별 artifacts, 읽기 전후 원본 hash 검증, 비밀정보 없는 보고서를 사용한다. package-lock.json 보존. push/배포/전역 승인 설정 변경/새 워커 금지. 승인된 구현·테스트는 추가 기능 승인을 묻지 않고 수행하되 도구 권한 승인 절차는 준수한다.

## B-IMG: Backend·데이터 담당 — 즉시 구현

작업공간 `C:/Users/user/orca/workspaces/Nikke-Simul/Backend`.

소유: `src/Nikke.Api/PresentationService.cs`, 필요한 최소 Program.cs 연결, `tools/data-pipeline/presentation_assets.py`, `account_presentation_assets.py`, `spec_presentation_assets.py`, 관련 기존 빌드/준비 스크립트의 최소 호출부, Backend 전용 테스트 및 `docs/image-catalog-fix.ko.md`. `apps/desktop-ui`, 전투 엔진, QA의 `tests/image_collection_qa`와 조사 보고서는 수정하지 않는다. 공용 README 수정 필요는 보고만 한다.

1. 유효 dataRoot를 서비스→Python CLI→account/spec helper까지 명시적으로 전달한다. calculation/current.json·버전별 cube_effect_table.json·game-catalog.json은 모두 같은 유효 루트에서 읽는다. 경로 우선순위/기본값/단위를 문서화하고 종전 기본 data/local 호출과 직접 helper/build 호출 호환성을 보존한다. 기존의 output만 지정한 공개 API 호출도 검토한다. 숨은 코드 ROOT 의존으로 우회하지 않는다.
2. 실제 이미지 파일 실패와 카탈로그/메타데이터 준비 실패를 구분한다. 캐시 사용 여부와 안전한 원인 코드를 유지하고, 잘못된 '이미지 2개' 표현을 수정한다. 캐시 없는 경우에 '기존 이미지는 유지됩니다'라고 단정하지 않는다. 혼합 실패·전체 실패·복구 시 메시지와 status도 정확해야 한다. 현재 UI는 서버 문구를 표시하므로 우선 서버 응답에서 해결하며 불필요한 UI 추가는 하지 않는다.
3. 오류 때문에 기존 정상 manifest/이미지/매핑을 잃지 않도록 한다. 이전 unresolved 항목과 status가 성공 후 남지 않아야 한다. 경고만 숨기거나 누락을 정상 0으로 바꾸지 않는다.
4. 기본/외부 dataRoot, 코드 루트 데이터 부재, initial/update-index/refresh, 캐시 유무, 메타데이터 누락/HTTP 오류/비이미지 응답/혼합 실패를 단위·격리 실행으로 검증한다. 실제 제품 CLI와 API 갱신 경로를 적어도 한 번 연결하고, mock 원천을 쓴 경우 명시한다. 실제 CDN 전체 정상이라고 주장하지 않는다.
5. 최소 관련 C#/Python 회귀, API 빌드, 원본 hash 보존 결과를 남긴다. 이전 3개 이미지 회귀를 유지한다. 커밋에는 수정/테스트/전용 문서만 포함한다. 보고에는 결과 커밋, 변경 파일, 실행 명령·실제 결과·입력 경로 규칙, 미실행/한계를 포함한다.

완료 시 확정 결과 커밋과 보고서 경로를 Director와 기존 검수 담당 양쪽에 한 번씩 전달한다. 검수에 '이 문서 Q-IMG 수용 조건으로 이 커밋을 독립 검증'이라고 명시한다. 미커밋 파일을 넘기거나 검수 결과를 대신 선언하지 않는다.

## Q-IMG: 검수 담당 — 지금 준비, 수정 커밋 수신 후 실행

작업공간 `C:/Users/user/orca/workspaces/Nikke-Simul/검수`. 소유는 `tests/image_collection_qa/`의 독립 검사와 `docs/image-catalog-fix-verification.ko.md`다. 제품 코드와 Backend 테스트를 수정하지 않는다.

1. 기존 b1d37d2 재현·원본 보존 근거를 유지하며 위 실패 종류/캐시 유무/경로 조합을 검증할 독립 수용 검사를 준비한다. 기존 진단 도구가 의도적으로 실패 상태를 기대한다면 baseline 검사와 수정본 성공 검사를 분리한다. 실패 기대값만 삭제하여 통과시키지 않는다.
2. Backend 확정 커밋이 아직 없으면 준비 결과를 '수정본 대기'로 보고하고 턴을 종료한다. 무한 polling/대기나 제품 수정은 하지 않는다. Backend 완료 메시지가 후속 실행 지시다.
3. 수정 커밋 수신 후 SHA와 변경 범위를 확인한다. 자기 작업공간에서 기존 검수 변경을 보존하며 해당 확정 커밋을 통합해 검사할 수 있다. 가능하면 FF, 별도 검수 커밋이 있어 분기됐다면 충돌 없는 일반 merge를 사용한다. 충돌 시 자동 덮어쓰기 금지·Director 보고. 다른 작업공간이나 원본 서버를 검사 용도로 변경하지 않는다.
4. 코드 루트 데이터 없음+외부 dataRoot에서 실제 수정 CLI/API로 두 카탈로그 생성과 반복 갱신 성공을 확인한다. 기본 dataRoot 회귀도 검사한다. 실제 API/실제 CLI 실행과 합성 네트워크 응답은 별도 표기한다.
5. 파일 오류·카탈로그 오류·혼합 오류, 캐시 보유/미보유에서 집계·문구·상태·이전 캐시 보존을 검증한다. 오류 후 복구가 unresolved=0/status=succeeded로 바뀌는지 확인한다. 격리 브라우저에서 서버 문구와 캐시 이미지 표시까지 확인한다.
6. 정상 캐시의 콘솔/큐브/장비/소장품 ID·이름·경로와 이미지 hash/형식 유지, 원본 불변, 기존 3개 회귀를 검증한다. 성공·실패·미실행을 나눠 Director에게 결과 커밋/보고서/수용 판정을 보낸다. 검수 통과와 EXE 재배포는 구분한다.

## 전달 경로

Orca CLI: `C:/Users/user/AppData/Local/Programs/orca/resources/bin/orca.exe`. 먼저 해당 CLI의 orca-cli 지침을 읽는다. 담당 현재 handle(배정 전 read/list 확인):

- Backend: `term_6c0c321c-15a9-4f93-8784-5a88b484ee45`.
- 검수: `term_30f7a75f-412b-4f2f-9bd3-863c417a5e7e`.
- Director: `term_f54735fc-6293-41b3-ae3a-984fd0d5b42a`.

완료 시 각 수신 worktree의 terminal list/read로 해당 agent 세션을 재확인한 뒤 `terminal send --terminal <handle> --text '<담당/결과 커밋/보고서 절대 경로/검증 결과/남은 조건>' --enter --wait-submit 10 --json`으로 한 번 전달하고 영수증을 남긴다. stale/불명확 handle은 재조회하며 임의 셸에 보내지 않는다. accepted는 접수일 뿐 수용이 아니다. 무응답 재전송 금지. worker_done/기존 lifecycle ID 사용 금지.

UI 담당과 엔진·통계 담당에는 이 결함의 구현을 중복 배정하지 않는다. UI 파일 변경이 정말 필요하면 근거와 범위를 Director에 보고하고 지정 UI 담당에게 후속 배정한다. 최종 Director 통합·EXE 갱신은 검수 결과 수신 후 별도 처리한다.

## 전달 확인

2026-09-14 두 기존 워커에게 각각 한 번 전송했다. B-IMG 요청 `a8af90e5-7d28-4a73-8ebe-85068395f5a1`, Q-IMG 요청 `eabbb5a2-2b93-490a-ac8c-4b24931eadd6` 모두 `accepted=true`, `input_accepted`, `turn_started` 확인. 구현/회귀 준비 착수 증거이며 제품 수정 완료·수정본 검수 통과는 아직 아니다.

작업공간 ID: Backend `07c470de-0a43-4d90-9eb6-240a5de9258c::C:/Users/user/orca/workspaces/Nikke-Simul/Backend`, 검수 `07c470de-0a43-4d90-9eb6-240a5de9258c::C:/Users/user/orca/workspaces/Nikke-Simul/검수`. agent handle은 위 전달 경로와 같다. 신규 워커는 만들지 않았다.
