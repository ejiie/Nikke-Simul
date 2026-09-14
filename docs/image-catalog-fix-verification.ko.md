# Q-IMG 독립 회귀 검수 — 2026-09-14

**최종 판정: Q-IMG 수용 통과.** Backend 확정 제품 커밋 `104646006318f252f01b8d39b3424316e0a262ba`를 독립 검증했다. 실제 CLI 24회, API 갱신 31회와 격리 브라우저를 포함한 28개 검사 그룹 모두 통과했다. 이 판정은 EXE 재배포 완료를 의미하지 않는다.

## 수정본 통합과 실제 결과

기존 조사 `b1d37d2321a47587e5e57f94d7a0bce60775f407`와 준비 커밋 `f3ceb847a7f739d41f55a3ba0afdbec377850172`를 보존했다. Backend와 분기된 상태를 확인하고 충돌 없는 일반 merge로 통합했다. 검증 HEAD는 `908f37f06cd3910c5d20f1a101ebaa851672ff9e`다. 확정 제품 커밋 대비 src/apps/tools/scripts 차이는 없다. Backend 보고와 지시서 전체를 UTF-8로 읽었으며, 아래 결과는 Backend 수치를 인용한 것이 아니라 검수 작업공간에서 새로 실행한 결과다.

| 독립 실행 | 결과 | 근거 (본 작업공간 상대 경로) |
|---|---|---|
| 기본/외부 dataRoot × initial/update-index/refresh × 캐시 유무, 각각 2회 | 12조합 / CLI 24회 통과 | `artifacts/image-collection-qa/f-6fcaf1957f4e/cli/` |
| 실제 API 정상, 오류 7종 × 캐시 유무 + 각 복구, 캐시 없는 전체 실패 + 복구 | 16그룹 / 갱신 31회 통과 | 같은 실행 `summary.json`, `api-cases/`, `api-total-failure.json` |
| 실제 Edge 페이지의 API 문구 반영 | 정상·실패·복구 캡처 31개, JS 예외 0 | 같은 실행 `browser-*.png` |
| 기존 Python 이미지 회귀 / 추가 경로·오류 회귀 | 3/3, 8/8 통과 | `artifacts/image-collection-qa/regression-d53e5e9351ab44beafc92383ef54cda0/python-existing.log`, `python-paths.log` |
| C# Sync | 81 통과 / 실패·skip 0 | 같은 regression 실행 `sync.log`, `sync.trx` |
| API Release 빌드 | 경고 0 / 오류 0 | `artifacts/image-collection-qa/build-d2eb754b389c47e1a9bd27d660a6b466/build.log` |
| 독립 판정기 자체 회귀 | 10 통과 | `artifacts/image-collection-qa/oracle-14dfff016f664992b44a5e8d98a7f41d/summary.json` |

주 근거 `f-6fcaf1957f4e/summary.json`의 최종 status는 passed, 28개 그룹 passed=true, 실행 종료 0이다. 저장된 API 결과를 다시 대조한 `independent-final-audit.json`에서도 실패 시 availableImages 유무에 따른 partial/failed와 복구 후 성공·실패 집계 0을 확인했다. TRX SHA-256은 `05c5fe500e26a3e8f9a71c391cfc101ec5269c2303e73facc91226c45ff49e13`이다.

### 경로·오류·보존 수용 근거

- 기본 루트는 새 artifacts 아래 제품 Python 3개 파일을 byte/hash 동일하게 복사한 코드의 data/local에서 검사했다. 외부 루트는 코드 data/local 부재를 확인했다. 실제 API에도 별도 외부 dataRoot를 전달했다. 두 카탈로그가 생성되고 반복 실행에서 매핑이 유지됐다.
- calculation/current.json 누락, 버전별 cube_effect_table.json 누락, game-catalog.json 누락, 두 의존성 누락, 이미지 HTTP 404, HTML 비이미지 응답, 이미지+두 카탈로그 혼합을 캐시 있음/없음 각각 검사했다. 정확한 path/kind/code/cached/집계 및 문구를 대조했다.
- 원래 두 실패는 account-presentation.json 및 spec-presentation.json으로 재현했다. 화면에는 `카탈로그 준비 2건 실패. 실패 항목 중 2건은 기존 캐시를 사용합니다.`가 표시됐다. 이미지 2장으로 오분류하지 않는다. 혼합은 이미지 파일 1개·카탈로그 2건, 캐시 없는 조건은 사용할 캐시가 없다는 문구다.
- 캐시 보유 실패 시 기존 manifest와 이미지 hash를 보존했고, 모든 오류는 격리 입력 복원 후 unresolved=[]/succeeded로 복구됐다. 캐시 없는 전체 index HTTP 실패는 failed/availableImages=0/cachedFailures=0, 복구 최종 revision=31이다.
- 정상 캐시 이미지 **357개**의 전체 SHA-256/형식을 확인하고 Pillow로 실제 이미지를 검증했다. 콘솔·큐브·장비·소장품 및 OL의 전체 매핑 레코드(ID·이름·경로 포함)를 원본과 비교했다.
- 완전 빈 캐시의 최종 생성 수는 **355개**다. 공개 캐릭터 200명과 초상화 200개는 모두 생성됐다. 원본에는 현재 캐릭터 매핑에서 참조하지 않는 ZIP 초상화 2개(`fadbe56e-d9a3-435f-9b6f-415422b7e634.png`, `987dd0fc-fe95-4f98-a16d-8867dea6022a.png`)가 추가로 있다. 빈 fixture는 ZIP을 가져오지 않으므로 이 둘은 생성 대상이 아니다. 캐시 보유 조건에서는 357개가 유지됐으며, 이 수 차이는 unresolved 누락을 숨긴 결과가 아니다.

### 브라우저 확인과 범위

실제 API 포트 **58774**에 Edge headless로 접속했다. status API를 mock하지 않았으며 실제 프런트엔드 polling이 서버 문구를 표시하는지 검사했다. `browser-both-True.png`와 복구 캡처를 직접 확인했다. 캐시 보유 두 카탈로그 실패 중 실제 `mountAccountCards` 렌더러에 비개인 빈 계정 fixture를 전달하여 콘솔 9개·큐브 16개를 decode했다. 실제 presentation API의 장비·소장품 경로 각 1개도 함께 decode하여 총 27개 모두 성공했다. 장비·소장품은 검수용 갤러리이며 실제 계정 편집 흐름 전체를 실행한 것은 아니다.

추가 읽기 전용 렌더링 도구 `inspect_browser.py`의 최종 캡처는 `artifacts/image-collection-qa/visual-c8b634c2fba2/cache-renderer.png`, 이미지별 자연 크기·경로는 같은 폴더 `summary.json`이다. 직접 그림을 열어 정상 표시를 확인했다. 이 추가 캡처는 갱신과 병행한 이미지 표시 근거이고 특정 실패 상태의 문구 판정에는 주 실행 캡처를 사용한다. 첫 보조 캡처의 검수 라벨 속성 오타는 도구에서 displayName으로 수정하여 다시 캡처했다.

주 페이지 상단 app-icon.jpg가 깨져 보이는 것은 manifest에 없는 정적 로고를 격리 fixture에 복사하지 않았기 때문이다. 원본 파일 존재와 UI의 해당 경로를 확인했다. 제품 캐시 이미지 실패나 새 UI 회귀로 집계하지 않는다. 실제 계정 값, 게임 수치 실측, 전체 UI 상호작용 및 실제 CDN 전체 가용성은 이번 검증 대상이 아니다.

### 격리·원본 불변

`run_fixed.py`는 원본 공개 카탈로그/manifest/그 이미지와 계산 current·큐브 표만 새 실행 경로에 복사했다. **공개 파일 426개 전후 SHA-256 변경 0**이며 `f-6fcaf1957f4e/source-hashes.json`에 기록했다. 원본 계정 DB·인증 세션은 복제하지 않았다. API는 새 비개인 DB를 자기 artifacts에 생성했다.

CLI/API 프로세스와 이미지 렌더러는 실제 제품을 사용했다. 자식 Python urllib 응답만 공개 원본 이미지 바이트 및 합성 HTTP/HTML로 격리했고, 미등록 URL은 차단했다. 실제 CDN 요청 0, 사용자 서버 요청 0이다. 따라서 live CDN 통과를 주장하지 않는다.

자기 서버 PID만 종료했으며 최종 58774 listener가 없다. 5181은 시작·종료 확인 모두 PID 26896으로 유지됐다. 5180은 이번 실행 시작부터 listener가 없었고 본 검수가 종료한 것이 아니다. EXE SHA-256 `e4b16827aa0f7533ea921e7d0b002678fd06d9a525d3a76049420483a39819c2`, 기존 untracked package-lock.json SHA-256 `2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767`도 유지됐다. 다른 작업공간·제품·Backend 테스트 수정, 캐시 원본 갱신, 새 워커/lifecycle, push/배포 없음.

### 실행 명령과 실패 이력

```powershell
$taskImagePython = 'C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$taskImageDotnet = 'C:/Users/user/Documents/GitHub/Nikke-Simul/.tools/dotnet/dotnet.exe'
$env:PYTHONIOENCODING = 'utf-8'
& $taskImagePython -m unittest discover -s tools/data-pipeline/tests -p test_presentation_assets.py -v
& $taskImagePython -m unittest discover -s tools/data-pipeline/tests -p test_image_catalog_paths.py -v
& $taskImageDotnet test tests/Nikke.Sync.Tests/Nikke.Sync.Tests.csproj -c Release --no-restore --logger trx --results-directory '<새 regression 경로>'
& $taskImageDotnet build src/Nikke.Api/Nikke.Api.csproj -c Release -p:RestoreLockedMode=true -p:RestoreConfigFile=nuget.config
& $taskImagePython tests/image_collection_qa/test_acceptance.py
& $taskImagePython tests/image_collection_qa/run_fixed.py --source-data 'C:/Users/user/Documents/GitHub/Nikke-Simul/data/local' --dotnet $taskImageDotnet
# 위 격리 API가 실행 중일 때만 사용하는 읽기 전용 보조 검사
& $taskImagePython tests/image_collection_qa/inspect_browser.py --port '<격리 포트>'
```

DOTNET_CLI_HOME은 본인 `.tools/dotnet-home`, NuGet은 기존 캐시를 사용했다. 회귀 TEMP/TMP는 새 artifacts다. 최초 긴 UUID/설명형 케이스 경로 실행 `fixed-a2f67a4db2b94cbe8c3661dfbcaec694`은 Windows 긴 경로 때문에 임시 이미지 게시·fixture 복사에서 실패했다. 검수 러너 프로세스만 정리하고 짧은 UUID/숫자 케이스 경로로 도구를 수정하여 전체 조합을 새 경로에서 재실행했다. 실패 artifacts는 보존했고 수용 통과 수에 포함하지 않았다. 제품 변경은 하지 않았다.

### 최종 전달과 미완료

Q-IMG 지정 수용 조건의 미완료 항목과 발견된 제품 차단 결함은 없다. 실제 CDN 전체 검증·사용자 계정 실측·EXE 재배포는 미실행이며 범위 밖이다. 아래 준비 기록의 '수정본 대기'는 과거 상태다. 최종 결과 커밋은 이 보고서와 QA 도구만 포함한 커밋이며, Director에게 해당 SHA와 본 보고서 절대 경로를 일반 터미널로 한 번 전달한다. 접수 영수증은 새 artifacts에 보존한다. Director 통합·배포 판정은 별도다.

---

## 준비 단계 기록 (f3ceb847, 수정 커밋 수신 전)

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
