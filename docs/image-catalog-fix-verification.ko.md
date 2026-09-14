# Q-IMG 독립 회귀 준비 — 2026-09-14

**준비 완료 / Backend 확정 수정 커밋 미수신, 수정본 대기.** 현재 제품 수용 판정은 보류다. 수정 커밋을 받기 위해 polling하지 않고 이번 준비 턴을 종료한다. Backend의 확정 커밋·보고서 전달을 후속 실행 지시로 처리한다.

## 기준과 보존

- 공통 기준 및 현재 준비 시작 HEAD: `b1d37d2321a47587e5e57f94d7a0bce60775f407`. 그 아래 제품 기준은 `04a16be8cc0f84449d8b41ad9d37f53c692338df`다.
- Director의 `image-catalog-fix-assignments-2026-09-14.ko.md` 전체와 공통 경계/Q-IMG 절, README, `desktop-release-2026-09-12.ko.md`, 기존 이미지 조사 보고서를 UTF-8로 끝까지 읽었다. 앞서 확인한 적용 지침을 유지했다.
- 기존 `diagnose.py`와 `image-collection-qa-2026-09-14.ko.md` 및 b1d37d2의 artifacts는 수정하지 않았다. 기존 도구의 “FileNotFoundError 2개 기대”를 삭제해 수정본 통과로 바꾸지 않는다.
- 준비 작업은 새 `tests/image_collection_qa/` 검사 파일과 본 보고서만 소유한다. 제품·Backend 테스트·다른 작업공간은 수정하지 않았다.
- 원본 계정/DB/세션/캐시를 이번 준비에서 새로 읽거나 복사하지 않았다. 5180/5181 요청·갱신·종료, 새 서버·워커·lifecycle 생성, push/배포 없음. 기존 `package-lock.json` hash `2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767` 보존.

## 준비한 독립 검사

| 파일 | 역할 |
|---|---|
| `tests/image_collection_qa/acceptance.py` | 실제 CLI/API 실행 후 저장한 presentation·status·캐시 증거의 독립 판정기. 서버 기동/갱신 기능 없음 |
| `tests/image_collection_qa/test_acceptance.py` | 판정기가 결함을 탐지하는지 확인하는 합성/손상 입력 테스트. 사용자 데이터 미사용 |
| `tests/image_collection_qa/acceptance-cases.json` | 수정본에서 실행할 경로·진입 모드·캐시·오류·화면·보존 조건 조합표. 실행 결과가 아님 |

판정기 주요 조건:

- 성공은 unresolved 필드가 명시적으로 빈 배열이고, API status가 succeeded이며, **두 카탈로그 파일과 characters/consoles/cubes/supportDefinitions/overloadOptions가 실제 존재**해야 한다. 필드/카탈로그 누락을 정상 0으로 취급하지 않는다.
- 반복 성공 시 준비된 동일 입력 fixture의 전체 매핑 레코드와 이미지 hash를 비교한다. 정상 캐시 경로/파일 존재/manifest hash와 PNG/WEBP 시그니처를 검사한다. 전체 이미지 decode/실제 UI 표시는 후속 실행에서 별도 검사한다.
- 실패는 정확한 리소스 경로·개수, 원인 코드, cached 여부, 이전 파일 hash 보존을 검사한다. 이미지/카탈로그 문구와 각각의 숫자도 대조한다. 캐시 미보유에서 “기존 이미지는 유지”라고 주장하면 실패한다.
- 복구는 preceding partial/failed 근거가 있어야 하고, unresolved=0/succeeded로 바뀌어야 한다. revision이 제공되면 증가도 검사한다.
- 기존 “이미지 2개를 수집하지 못했습니다” 문구는 카탈로그 2건 수용 검사에서 **계속 실패**한다. 실패 기대를 없애 통과시키지 않았다.

판정기는 현재 확정된 path/error/cached 및 status/revision 계약에 맞췄다. Backend 수정본의 CLI 옵션·오류 분류 필드·문구가 확정되면 그 문서를 읽고 연결부와 정규식을 확인한다. 실제 의미가 같은 표현은 수용하되 원인·개수·캐시 유무 검증을 약화하지 않는다. 아직 존재하지 않는 인터페이스를 제품에 임의로 추가하지 않는다.

## 수정 커밋 수신 후 실행 조합

| 분류 | 조합/수용 조건 | 현재 상태 |
|---|---|---|
| 정상 경로 | 기본 dataRoot / 코드 data 없음+외부 dataRoot × initial/update-index/refresh × 캐시 없음/있음 = **12조합**, 각각 반복 실행 | 준비, 수정본 미실행 |
| 실패 종류 | calculation/current 누락, 버전별 cube_effect_table 누락, game-catalog 누락, 두 카탈로그 의존 누락, 이미지 HTTP 404, 비PNG/WEBP 응답, 카탈로그+이미지 혼합 × 캐시 없음/있음 = **14조합** | 준비, 수정본 미실행 |
| 복구 | 각 오류 이후 격리 입력만 정상화→실제 API 갱신→unresolved=0/status=succeeded/revision 증가 | 준비, 수정본 미실행 |
| 화면 | 격리 서버 문구=화면 문구, 캐시 보유 실패 시 콘솔/큐브/장비/소장품 정상 decode, 미보유 시 잘못된 보존 문구 없음, 복구 후 이전 경고 교체 | 준비, 미실행 |
| 보존/기존 회귀 | 원본 공개 자료를 쓸 때 전후 hash, 3개 기존 presentation 테스트, 정상 ID/이름/경로/hash/형식 | 계획, 이번에 재실행하지 않음 |

실행 방법은 확정 수정본의 인터페이스 확인 후 연결한다. 실제 제품 CLI·API 프로세스를 실행하고 네트워크만 합성 응답으로 격리할 계획이며, mock 원천을 실제 CDN 정상 증거로 표현하지 않는다. 데이터/출력/임시 디렉터리는 새 UUID artifacts에 두고, API는 사용자 5180/5181과 다른 임의 포트만 쓴다. fixture에는 DB/인증 세션을 복제하지 않는다. 필요 시 API가 새 비개인 테스트 DB를 자체 초기화하도록 한다. 테스트가 직접 시작한 PID만 정리한다.

정상 기본 dataRoot 검사는 본인 artifacts의 코드 복사본에서 실행하여 실제 작업공간이나 Director에 기본 데이터를 만들지 않는다. 복사 제품 파일은 확정 커밋 바이트/hash를 유지한다. 외부 dataRoot 검사에서는 코드 측 data/local이 없는지 먼저 검증한다.

## 이번 실제 실행

```powershell
$taskImagePython = 'C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$env:PYTHONIOENCODING = 'utf-8'
& $taskImagePython tests/image_collection_qa/test_acceptance.py
& $taskImagePython tests/image_collection_qa/acceptance.py --help
```

- 최종 **10개 통과 / 실패 0 / 오류 0, 종료 0**. CLI help 종료 0.
- 증거: `artifacts/image-collection-qa/oracle-8d7b1c3cf3624d1ca52d7fddd59dd70d/{summary.json,tests.log}`. 예비 9개 실행도 `oracle-a46e88f2d9f1408b93920bd411a0b63c/`에 보존했다.
- 합성 입력에 대한 판정기 자체 테스트다. PNG 테스트 데이터는 **시그니처만 가진 합성 바이트**이며 실제 정상 이미지 decode 증거가 아니다.
- `fixedCommitReceived=false`를 증거에 명시했다. 이번에는 수정 CLI/API·브라우저·실제 갱신·C# 빌드·기존 3개 제품 회귀를 실행하지 않았다. 이전 조사 결과를 수정본 통과로 인용하지 않는다.

후속 실제 산출물을 판정할 때의 명령 형태:

```powershell
# 성공 판정: 실제 격리 CLI/API 실행에서 얻은 파일을 제공
& $taskImagePython tests/image_collection_qa/acceptance.py --presentation-dir '<새 실행 presentation>' --status-json '<실제 API status.json>' --before-json '<동일 fixture 실행 전 capture 결과>'
# 오류 주입 판정: 예상 path/cached 목록을 명시적으로 추가
& $taskImagePython tests/image_collection_qa/acceptance.py --presentation-dir '<오류 실행 presentation>' --status-json '<실제 API status.json>' --expected-failures '<expected-failures.json>' --before-json '<실행 전 capture 결과>'
```

`capture()`의 before는 해당 격리 실행 전에 수집한다. 원본이나 과거 다른 실행의 스냅샷을 끼워 넣지 않는다. expected-failures 모드 성공은 **오류 보고 동작 수용**이지 제품 전체 성공이 아니다.

## 후속 전달·수용 보류

Backend 확정 커밋을 수신하면 SHA/변경 범위를 확인하고 본인 준비 커밋을 보존한다. 가능하면 FF, 준비 커밋으로 분기했다면 충돌 없는 일반 merge로 통합한다. 충돌은 자동 덮어쓰지 않고 Director에 보고한다. 그 후 위 실제 CLI/API/화면 검증 결과를 성공/실패/미실행으로 나눠 결과 커밋·보고서와 함께 Director에 한 번 전달한다.

이번 전달은 **독립 회귀 준비 완료 / 수정본 대기** 보고다. 수정 구현·통합 수용·EXE 배포 완료를 선언하지 않는다. 일반 agent 터미널의 현재 세션을 list/read로 확인한 뒤 한 번 전달하고, 영수증은 새 artifacts 파일로 남긴다. 무응답 재전송·무한 대기는 하지 않는다.
