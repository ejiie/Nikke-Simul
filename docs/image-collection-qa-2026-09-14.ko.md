# 이미지 2개 수집 실패 독립 검수 — 2026-09-14

**조사 완료, 제품 수정·배포는 미수행.** 경고의 두 항목은 니케 초상화 2장이 아니라 **계정 이미지 카탈로그와 스펙 이미지 카탈로그 준비 작업 2건**이다. 외부 `dataRoot`를 사용하는 배포에서 Python 하위 준비기가 코드 루트의 `data/local`을 읽어 `FileNotFoundError`가 발생한다. 기존 이미지·카탈로그는 정상이며 그대로 제공된다. 단순 재시도나 대체 이미지 추가가 해결책인 상황이 아니다.

## 기준·현재 상태·보존

- 시작 HEAD `c212cb75c1d6039182e0aa80beda5acc9dc40ff8`. 조상 확인 후 본인 `검수` 브랜치를 `04a16be8cc0f84449d8b41ad9d37f53c692338df`로 `git merge --ff-only` 성공.
- Director 지시서 전체, README, 실행본 갱신·UI 이식 문서를 UTF-8로 읽었다. 적용 경로/추적 파일에서 별도 AGENTS.md는 발견되지 않았다. 과거 Q3 UI 실패는 후속 통합으로 해소된 것으로 취급하며 이번 미해결 목록에 포함하지 않는다.
- 원본 스크린샷 파일이 존재해 실제 열람했다. 확인 문구: `이미지 2개를 수집하지 못했습니다. 다시 시도하세요.` 별도 계정 화면이나 사용자 정보는 복사하지 않았다.
- 배포 EXE: `C:/Users/user/orca/workspaces/Nikke-Simul/Director/artifacts/desktop/win-x64/Nikke Simul.exe`. SHA-256 `e4b16827aa0f7533ea921e7d0b002678fd06d9a525d3a76049420483a39819c2`로 배포 문서와 일치.
- 실제 `desktop.settings.json`: projectRoot=Director, port=5180, dataRoot=`C:/Users/user/Documents/GitHub/Nikke-Simul/data/local`. Python은 지시된 고정 런타임.
- 5180 PID 34332는 Director 동봉 `backend/Nikke.Api.exe`; 5181 PID 26896은 별도 dotnet 프로세스다. 시작/최종 확인 모두 같은 포트·PID를 유지했다. 5181의 데이터를 본 계정으로 사용하거나 복사하지 않았다.
- GET 확인: 5180 status=`partial`, revision=2, 동일 경고. 5181 status=`idle`, revision=0. 현재 경고가 사라진 상태가 아니다.
- 원본 계정 DB·세션은 읽거나 수정하지 않았다. 원본 캐시/이미지/manifest 422개 파일과 복사한 공개 계산 의존 파일 3개의 전후 SHA-256 일치. 네트워크 갱신 POST·계정 수집·동기화·서버 종료 없음. 제품/다른 작업공간 수정·새 워커·lifecycle 생성·push·배포 없음.
- 기존 미추적 `package-lock.json` SHA-256은 `2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767`로 유지, 커밋 제외.

## 두 실패 항목

실제 본 계정 데이터 경로의 `presentation/presentation.json`과 5180 `GET /api/presentation` 모두 다음 **두 레코드만** 가진다. 각 레코드의 `cached=true`는 기존 카탈로그 보존 상태다.

| 실패 항목 / 로컬 상대 경로 | 개별 니케·리소스 ID / 실패 요청 URL | 실제 실패 지점 | 기존 캐시·영향 |
|---|---|---|---|
| `presentation/account-presentation.json` | 단일 니케 ID 없음. 콘솔 9종·큐브 16종의 집계 카탈로그. 실패 URL 없음: 로컬 파일 읽기 예외 | `account_presentation_assets.py:33`의 `ROOT/data/local/calculation/current.json` 없음. 이어 읽을 cube_effect_table도 동일 코드 루트를 사용 | 기존 JSON 및 기록 자산 50개(이미지 25개) hash 일치. 계정 스펙의 콘솔·큐브, 니케 상세 큐브 표시/선택용 카탈로그 갱신 실패 |
| `presentation/spec-presentation.json` | 단일 니케 ID 없음. 장비/소장품·애장품 정의 153개, OL 옵션 9개 집계. 실패 URL 없음: 로컬 파일 읽기 예외 | `spec_presentation_assets.py:41`의 `ROOT/data/local/game-catalog.json` 없음. 이미지 준비 이후 OL 값 연결 중 실패 | 기존 JSON 및 기록 자산 140개(이미지 105개) hash 일치. 니케 상세 장비·소장품 이미지/선택 정의·OL 옵션 카탈로그 갱신 실패 |

두 항목 모두 `error=FileNotFoundError, cached=true`. 현재 Director의 위 두 입력 경로가 실제로 없고, 설정상 외부 데이터 루트에는 해당 파일과 계산 버전의 `cube_effect_table.json`이 존재한다. 단일 실패 이미지 ID/URL을 임의로 지정하지 않는다.

원본 `presentation.json`의 일반 초상화/UI 자산 227개는 모두 hash·이미지 검증 통과. 두 하위 카탈로그까지 총 417개 자산 레코드의 hash가 일치했고 **이미지 357개 전부 PNG/WEBP 시그니처 및 Pillow 검증**을 통과했다. 갱신 실패와 기존 이미지 미보유는 다른 상태다.

## HTTP·시그니처·ID/이름 매핑 증거

`GET http://127.0.0.1:5180/api/presentation`은 HTTP 200, `application/json; charset=utf-8`. characters=200, unresolved=2, consoles=9, cubes=16, supportDefinitions=153, overloadOptions=9. 본문은 공개 카탈로그이며 계정 API를 호출하지 않았다.

다음은 **실패 이미지 목록이 아닌 각 카탈로그의 정상 제공 대표 표본**이다. 모두 로컬 GET HTTP 200, image/webp 또는 image/png, 시그니처/파싱 검증 성공. 4개 표본의 HTTP 바이트 hash가 해당 원본 manifest hash와 일치한다.

| 종류·ID·이름 | 로컬 요청 경로(5180) | 원본 manifest에 기록된 공개 URL | 결과 |
|---|---|---|---|
| 콘솔 1001 공용 콘솔 | `/editor/assets/consoles/common.webp` | `https://static.dotgg.gg/nikke/items/7040001.webp` | WEBP, 256×256 |
| 큐브 1000301 렐릭 어설트 큐브 | `/editor/assets/cubes/1000301.png` | `https://sg-tools-cdn.blablalink.com/vp-92/xr-59/92f08f3c5dcafe7bc9c1f1739a023fd8.png` | PNG, 256×256 |
| 장비 3110101 케블라 바이저 | `/editor/assets/equipment/icn_equipment_head_attacker_t1.png` | `https://sg-tools-cdn.blablalink.com/ja-37/dp-42/ce7fb0def1357aff11041aa12cf9d5b6.png` | PNG, 128×128 |
| 소장품 100101 R 요리 지휘관 인형 | `/editor/assets/collections/100101.png` | `https://sg-tools-cdn.blablalink.com/xq-71/qa-54/2bcc6b48c1f4a89b40eda94036008aee.png` | PNG, 256×256 |

외부 URL은 **이번에 요청하지 않았다**. 원본 URL의 현재 HTTP 상태는 미측정이며 위 상태 200은 localhost 응답이다. 현재 실패 항목에는 실패한 원천 요청 URL 자체가 없고, 오프라인 재현으로 원인을 분리할 수 있어 불필요한 전체 CDN 재수집을 하지 않았다. 원천 부재/주소 변경/일시 네트워크 장애를 이번 두 경고의 원인으로 볼 증거는 없다.

격리 복구 후 콘솔 9개·큐브 16개·supportDefinitions 153개·OL 옵션 9개의 **전체 레코드(이름/ID/이미지 경로 포함)가 원본과 동일**했다. ID/이름 매핑 오류나 새 초상화 누락으로 분류하지 않는다.

## 경고 생성 경로와 원인

1. `Program.cs:14,27`은 환경의 외부 dataRoot를 적용해 `PresentationService`의 출력 경로를 외부 `presentation`으로 설정한다.
2. `PresentationService.cs:66`은 Director의 `presentation_assets.py`에 `--output <외부 presentation>`만 전달한다. Python 하위 준비기는 `ROOT`를 스크립트가 있는 코드 루트로 설정하며, `NIKKE_DATA_ROOT`를 읽지 않는다.
3. `presentation_assets.py:209–216`은 `account.prepare(output)`, `spec.prepare(output)`를 호출한다. 두 함수는 출력·이미지 캐시에는 output을 쓰지만 계산/게임 입력에는 `ROOT/data/local/...`을 하드코딩한다. 각 예외를 카탈로그 이름의 unresolved **1건씩**으로 기록한다.
4. `PresentationService.cs:76–78`은 unresolved 배열 길이 2를 그대로 “이미지 2개”로 표현한다. 이미지 수, 카탈로그 수, 캐시를 유지한 갱신 오류가 한 집계에 섞여 있다.
5. `app.js:114–118`은 상태/리비전 변경 시 서버의 문구를 표시하고 partial에서도 저장된 presentation을 읽는다. `PresentationService.Read()`도 기존 하위 manifest를 읽어 합친다. 따라서 경고가 있어도 기존 이미지가 정상인 것은 모순이 아니다.

API 서비스 및 Python 세 파일의 현재 Director 파일 hash가 기준 04a16be의 본인 파일과 모두 일치한다. 이번 원인은 **외부 데이터 경로 전달 불완전 + 오류 집계 문구의 의미 손실**이다. 서비스 status는 최근 실행 결과를 메모리에 유지하므로 이 GET을 새로운 갱신 실행으로 해석하지 않는다. 다만 동일 경로 조건에서 새 격리 실행도 같은 오류를 내므로 단순 오래된 상태 표시만의 문제는 아니다.

## 독립 격리 재현·실제 결과

전용 도구: `tests/image_collection_qa/diagnose.py`. 원본의 공개 이미지·카탈로그만 UUID sandbox로 복사하고 `prepare`/`build` **실제 제품 함수**를 실행한다. 제품 파일은 변경하지 않고, 모듈의 ROOT를 테스트 프로세스 안에서 sandbox 코드 루트로 지정하여 배포와 같은 “코드 데이터 없음/외부 이미지 있음” 배치를 만든다. `urllib.request.urlopen`을 차단해 공용/인증 네트워크 모두 쓰지 않는다.

| 단계 | 실제 결과 |
|---|---|
| 하위 prepare 개별 실행 | account는 calculation/current.json, spec은 game-catalog.json의 FileNotFoundError. 기존 두 manifest hash 유지 |
| `build(include_account_assets=True)` | characters 200 / zipPortraits 197 / assets 227 / **현재와 동일한 unresolved 2개** |
| 의존성 대조군 | 공개 current.json, 해당 cube_effect_table.json, game-catalog.json 3개만 sandbox의 기대 입력 위치에 복사 |
| 동일 build 재실행 | unresolved **0개**, 실제 네트워크 시도 0, 출력 카탈로그 전체 매핑 일치 |
| 원본 보존 검사 | 원본 캐시 422개 및 공개 의존 3개 SHA-256 동일 |
| 기존 presentation 단위 테스트 | 3개 통과, 실패 0, 종료 0. ZIP hash/경로, 동명이인 리소스 매핑, CDN 실패 시 캐시 보존 포함 |

진단과 GET 도구 모두 종료 0. 위 재현은 `refresh=False`의 캐시 실행이다. 전체 `--refresh` 원천 요청이나 실제 사용자 서버의 갱신 POST를 실행한 것이 아니다. 두 하위 prepare는 상위 refresh 여부를 받지 않으므로 이번 경로 오류 분리에는 같은 실행 경로를 사용한다. 대조군의 입력 복사는 원인 검증용이며 Director 데이터 경로에 파일을 복제하는 제품 수정을 제안한 것이 아니다.

재현 명령(본인 작업공간 루트):

```powershell
$taskImagePython = 'C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$env:PYTHONIOENCODING = 'utf-8'
& $taskImagePython tests/image_collection_qa/diagnose.py --source-data 'C:/Users/user/Documents/GitHub/Nikke-Simul/data/local' --deployed-root 'C:/Users/user/orca/workspaces/Nikke-Simul/Director'
& $taskImagePython tests/image_collection_qa/read_status.py
# TEMP/TMP를 본인 실행별 artifacts 하위 test-temp로 지정한 후:
& $taskImagePython -m unittest discover -s tools/data-pipeline/tests -p test_presentation_assets.py -v
```

각 진단 실행은 `artifacts/image-collection-qa/<uuid>/`, GET은 `http-<uuid>/`를 새로 생성한다. 다른 작업공간·원본 출력 경로에는 쓰지 않는다. 기존 단위 테스트가 include_account_assets=True의 외부 dataRoot 배치를 검사하지 않으므로 기존 3개 통과만으로 이번 결함을 배제할 수 없었다.

## 수정 소유자 제안·수용 조건

- **주 담당: Backend·데이터 파이프라인.** 유효 dataRoot를 이미지 준비 CLI 및 account/spec helper까지 명시적으로 전달한다. 계산 current/table 및 game-catalog는 동일 dataRoot에서 읽게 하고, 기본 dataRoot 동작도 보존한다. Director 안에 원본 계정/계산 자료를 복제해 경로 오류를 가리는 방식은 피한다.
- **Backend + UI:** 이미지 파일 실패, 메타데이터/카탈로그 준비 실패, 기존 캐시 사용 중 갱신 실패를 구분하는 상태/문구가 필요하다. 예: “계정·스펙 이미지 카탈로그 2종을 갱신하지 못했습니다. 기존 이미지는 유지됩니다.” 실패 항목/안전한 원인 코드는 제공하되 원본 계정 정보/토큰을 노출하지 않는다. 현 UI는 서버 문구를 그대로 표시하므로 주 수정 지점은 서버 집계다.
- **데이터/아트 담당의 새 이미지·대체 이미지 작업은 현재 근거상 불필요.** 나중에 특정 리소스 HTTP 실패가 따로 확인되면 별도 배정한다.

수정 후 회귀 수용 조건:

1. 코드 루트에 data/local이 없고 외부 dataRoot만 존재하는 격리 배치에서 account/spec 생성 성공. 외부 dataRoot의 DB·기존 입력 자료 불변을 검사한다.
2. 기본 dataRoot와 외부 dataRoot 두 경우, initial/update-index/refresh 경로에서 같은 입력 루트 사용. 계정 DB 없는 공개 캐시 시험으로도 검증한다.
3. 기존 캐시 보유/미보유 각각에서 로컬 메타데이터 누락과 HTTP 오류/비이미지 응답을 따로 주입. 경고 개수·종류·원인·캐시 유지 여부가 정확해야 한다.
4. 외부 경로 정상화 후 반복 갱신에서 unresolved=0 및 status=succeeded. 오류 주입 후 복구 시 과거 partial이 남지 않아야 한다. 서버 POST는 수정 담당의 **별도 격리 서버**에서 수행한다.
5. 콘솔·큐브·장비·소장품 전체 ID/이름/경로와 PNG/WEBP/hash 유지, 대표 화면 및 HTTP 이미지 검증. 출력 캐시에 우연히 있는 파일로 입력 경로 오류가 숨지 않게 검사한다.
6. 기존 ZIP 무결성/동명이인/실패 시 캐시 보존 3개 회귀도 유지한다.

남은 범위: 제품 수정/배포 및 수정본 실제 갱신 API·브라우저 수용은 미실행이다. CDN의 현재 전체 가용성과 과거 실패 실행의 원문 traceback은 수집하지 않았다. 현재 manifest는 예외 유형만 보존한다. 경로를 올바르게 전달한 수정본에서도 재현된다면 그때 필요한 최소 추가 근거는 **격리 갱신 실행의 예외 filename/HTTP status 및 unresolved 레코드**다. 원본 계정/세션 추가 수집은 필요하지 않다.

## 증거·완료 전달

본인 작업공간 `artifacts/image-collection-qa/` 하위:

- `ade4f8d3ef6447989b6bf002976bf74a/summary.json`: 캐시 검사·실제 함수 재현·2→0 대조군. SHA-256 `fc9a0d857b383c5790f88c09e6cb1c557b73bdabeb63c1d428d7c44c48a245c4`.
- 같은 폴더 `source-hashes.json`, `mapping-and-final-preservation.json`, `existing-tests.log`, `isolated/`. mapping SHA-256 `2ab60d423b7d8739d6bbf2a1e11cd1b32920e6821bd2274a313b5f8ed0e67c5a`.
- `http-f1ba7c930327407d9af23508d8ee24aa/summary.json`: GET별 URL/status/type/시그니처·hash·ID/이름. SHA-256 `fde25dff4f416737047e3bee259559e0bedf96af15b74541d1444e3cf2c0783d`.

읽기 검색 중 잘못 가정한 파일명 `account-cards.js`가 없어 실제 `local-lab-account.js`로 확인했다. Windows PowerShell은 unittest stderr를 NativeCommandError로 꾸몄지만 테스트는 3개 OK/종료 0이다. 제품 오류나 실패 테스트로 집계하지 않는다.

일반 터미널 완료 보고는 이 보고서/도구 커밋 후 현재 Director agent handle을 다시 확인하여 **한 번만** 전송한다. `worker_done`/Run/Task/Dispatch를 사용하지 않는다. 전달 영수증은 같은 증거 루트의 `director-delivery.json`에 별도 보존하고 최종 응답에 결과 커밋·보고서 경로와 함께 남긴다. accepted는 입력 접수이며 Director 검수 통과를 의미하지 않는다.
