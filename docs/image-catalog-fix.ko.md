# B-IMG 이미지 카탈로그 경로·실패 집계 수정

기준 `b1d37d2321a47587e5e57f94d7a0bce60775f407`. 시작 Backend `b63ad12`의 조상 관계와 미커밋 겹침 없음을 확인하고 자기 브랜치만 fast-forward했다. 기존 `package-lock.json` 보존. 지시서 전체, README, 실행본 갱신 문서, 독립 이미지 조사 보고서를 UTF-8로 읽었다.

## 제품 변경

- `PresentationService`는 유효 dataRoot를 Python `--data-root`에 명시한다. Program은 API의 `NIKKE_DATA_ROOT` 적용값을 전달한다. 기존 3인자 서비스 생성도 output 부모를 dataRoot로 사용해 호환된다.
- Python main/build와 account/spec prepare/직접 CLI가 같은 루트를 전달한다. account의 `calculation/current.json`과 해당 버전 `cube_effect_table.json`, spec의 `game-catalog.json`을 코드 ROOT에서 찾지 않는다.
- 카탈로그 helper는 새 이미지/메타데이터를 메모리에 준비하고 전체 카탈로그 투영이 성공한 뒤 게시한다. 실패하면 기존 카탈로그와 미게시 교체 파일을 보존한다. 검증된 기존 파일은 갱신 실패 시 fallback으로 사용하되 실패를 숨기지 않는다. base index도 행 투영 성공 전에 기존 index를 교체하지 않는다.
- 일반 이미지와 helper 오류에 `kind=image|catalog`, 안전한 `code`, 예외 유형 `error`, `cached`, HTTP 실패의 숫자 `httpStatus`를 기록한다. 절대 입력 경로/예외 메시지/인증 정보는 API 원인 코드에 넣지 않는다. 기존 공개 원천 URL은 자산 manifest에 유지한다.
- `failureSummary`는 `imageFailures`, `catalogFailures`, `cachedFailures`, `availableImages`를 구분한다. 수치는 파일 개수/준비 실패 건수이며 초상화 수나 니케 수가 아니다. helper가 필수 입력에서 중단되면 그 준비 실패를 기록하며 미시도 리소스를 실패 이미지로 만들어 세지 않는다.
- status는 unresolved가 없으면 succeeded, 실패가 있으면서 사용 가능한 이미지가 있으면 partial, 실패하고 사용 가능한 이미지가 없으면 failed다. 원문/형식을 확인할 수 없는 자식 프로세스 실패는 안전한 process_failed와 캐시 확인 불가 문구를 사용한다.
- 서버 메시지 예: `카탈로그 준비 2건 실패. 실패 항목 중 2건은 기존 캐시를 사용합니다.` / `이미지 파일 1개 · 카탈로그 준비 2건 실패.`. 캐시가 없으면 `실패 항목에 사용할 캐시가 없습니다.`. “이미지 2개”로 카탈로그를 세거나 무조건 기존 이미지 유지라고 단정하지 않는다.
- status 응답에 현재 실행의 unresolved/failureSummary를 제공한다. 새 실행 시작과 성공 후 이전 오류를 지운다. prepare 성공 시 helper와 상위 manifest의 이전 unresolved도 남기지 않는다. 일반 프로세스 실패 시 기존 정상 manifest를 지우지 않는다.

## 경로·호환 계약

Python 입력 루트 우선순위:

1. 명시 `data_root` / CLI `--data-root`
2. 환경 `NIKKE_DATA_ROOT`
3. output만 지정하면 `Path(output).parent` (통상 `<dataRoot>/presentation`)
4. 둘 다 없으면 기존 코드 ROOT의 `data/local`

입력 루트는 절대 경로로 정규화한다. output은 명시 값이 우선이며, 생략하면 유효 dataRoot의 `presentation`이다. 입력과 출력은 별도로 지정할 수 있다. output만 지정한 공개 `build(output, ...)`/`prepare(output)` 호출도 외부 출력의 부모를 입력 루트로 사용한다. 임의 output 디렉터리와 별도 입력 디렉터리를 쓰려면 `data_root`를 명시한다. 올바른 입력이 없으면 코드 루트로 몰래 재시도하지 않는다.

`build`의 기존 위치 인자들은 유지하고 마지막 optional `data_root`만 추가했다. helper는 `prepare(output=None, data_root=None, refresh=False)`이며, 직접 실행 시 `--data-root`, `--output`, `--refresh`를 받는다. prepare-presentation.ps1은 `-DataRoot`, `-Output`을 추가 전달한다. 기본 desktop 빌드의 무인자 helper 호출은 기존 data/local 동작을 유지하며, 외부 DataRoot 빌드는 종전처럼 기존 자산을 재생성하지 않는다. UI/EXE 빌드·배포 코드는 수정하지 않았다.

initial: 없는 자산만 가져온다. update-index: 공개 index를 갱신하고 검증된 이미지/helper 캐시는 재사용한다. refresh: index·이미지·helper 메타데이터도 갱신하며 검증된 캐시가 있으면 실패 시 유지하고 오류를 기록한다. 메타데이터 투영 실패 시 해당 helper 교체 묶음은 게시하지 않는다. 파일 게시 자체는 기존 파일별 atomic replace이며 여러 파일의 디스크 장애까지 원자적 DB 트랜잭션으로 묶은 것은 아니다.

CLI는 JSON receipt를 출력한다. 정상/부분 결과는 기존처럼 종료 0, 전체 준비 중단은 종료 1이며 분류된 receipt도 남긴다. API는 비정상 종료여도 유효 partial/failed receipt가 있으면 이를 표시한다. receipt가 없거나 파싱 불가하면 process_failed다. 직접 helper의 실패는 종전처럼 비정상 종료한다.

카탈로그 ID·이름·이미지 경로와 OL 단위를 변경하지 않는다. `legalValues.unscaledValue=round(비율×10000)`, `decimalScale=4`, 표시 unitLabel `%`와 기존 부호를 보존했다.

## 검증 방식·보존 경계

Backend 전용 `tests/Nikke.Sync.Tests/check_image_catalog_api.py`는 원본의 공개 presentation manifest/그 manifest가 가리키는 자산·공개 index/성장 캐시/이미지 ZIP manifest, 공개 game-catalog 및 계산 current/cube table만 새 UUID 경로에 복사한다. **원본 accounts.db·인증·세션은 읽거나 복제하지 않는다.** 격리 API가 자기 출력 아래 새 DB를 만든다.

child Python의 urllib만 격리 `sitecustomize.py`로 대체하여 공개 URL→복사한 자산 바이트를 반환한다. 오류는 synthetic HTTP 503 또는 HTML 비이미지 응답이다. 제품 CLI/prepare/API 갱신 경로는 실제 코드이며 **실제 CDN 전체 가용성을 검증한 것이 아니다**. 모든 서버는 5180/5181 이외 임의 포트에서 시작하고 본 테스트가 만든 process만 종료한다. 사용자 EXE·캐시·5180·5181에 갱신/종료 요청을 하지 않는다.

실행 파일/경로:

- Python: `C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`
- dotnet: `C:/Users/user/Documents/GitHub/Nikke-Simul/.tools/dotnet/dotnet.exe` (10.0.400)
- `DOTNET_CLI_HOME`: Backend `.tools/dotnet-home`; 기존 NuGet 캐시 사용.
- 단위 테스트 TEMP/TMP와 API/CLI 출력: Backend `artifacts/image-catalog-fix/<실행별 UUID>/`.

```powershell
& '<python>' -m unittest discover -s tools/data-pipeline/tests -p test_presentation_assets.py -v
& '<python>' -m unittest discover -s tools/data-pipeline/tests -p test_image_catalog_paths.py -v
& '<dotnet>' test tests/Nikke.Sync.Tests/Nikke.Sync.Tests.csproj -c Release --no-restore --logger trx --results-directory '<실행별 경로>'
& '<dotnet>' build src/Nikke.Api/Nikke.Api.csproj -c Release --no-restore
& '<python>' tests/Nikke.Sync.Tests/check_image_catalog_api.py --source-data 'C:/Users/user/Documents/GitHub/Nikke-Simul/data/local' --dotnet '<dotnet>'
```

기존 이미지 3개 회귀는 유지한다. 추가 단위 검증은 기본/외부/명시/환경 루트, 코드 루트 데이터 부재, metadata 누락 시 정상 manifest 보존, HTTP/비이미지 및 cache fallback, helper 미게시 교체, 혼합 실패·복구, 캐시 없는 전체 실패, malformed index 보존을 포함한다. 실제 CLI 검사는 initial/update-index/refresh와 직접 두 helper 호출을 포함한다. 실제 API는 두 metadata 실패·혼합 실패·미캐시 HTTP 실패·전체 캐시 부재·복구 상태를 검사한다.

## 실행 결과 및 실패 이력

최초 새 단위 검증은 6 통과/1 오류였다. 실패 레코드의 path를 두 번 전달한 TypeError를 수정한 뒤 7개 통과했고, malformed index 보존 회귀를 1개 추가했다. 기존 이미지 회귀 3개는 처음부터 통과했다.

C# Sync 회귀: **81 통과, 실패/skip 0**. 근거 `artifacts/image-catalog-fix/csharp-130c0b70e0fe471895e02f8ca7e2e909/user_BOOK-UB6JGJ0BM4_2026-09-14_10_52_19_net10.0.trx`. 이 회귀는 전투 산식 실측 검증이 아니다. API 최초 빌드 경고/오류 0.

첫 실제 CLI/API 실행: 12개 검사 그룹 통과. `artifacts/image-catalog-fix/bb3b01b0dba74f62a24152990ec4680f/summary.json`. 원본 공개 파일 **426개** 전후 SHA-256 일치, 정상 이미지 **357개** 사용 가능. 콘솔/큐브/장비/소장품 전체 매핑과 원본 manifest 이미지 hash 유지. 실제 API 복구 최종 status=succeeded, unresolved=[], imageFailures/catalogFailures/cachedFailures=0.

전체 캐시 부재 검사를 추가한 중간 실행 `0af4c1f9b79c43cabb5a2315bcbf5945`은 이전 API 바이너리와 새 CLI 종료 코드가 섞여 실패했다. 통과로 집계하지 않는다. 실패 실행에서도 원본 hash 변경은 없었다. 최종 제품 코드 재빌드 후 추가 회귀와 CLI/API 전체 검사를 다시 실행하여 아래 확정 결과를 남긴다.

최종 확정 실행(2026-09-14): 기존 Python 이미지 회귀 **3/3**, 추가 경로·실패 회귀 **8/8** 통과. 최종 API Release 재빌드 **경고 0 / 오류 0**. `git diff --check` 및 준비 PowerShell 구문 검사 통과.

최종 실제 제품 CLI/API 검사 **13개 그룹 통과**, 종료 코드 0. 근거 `artifacts/image-catalog-fix/30b43f07a1084a89953934a563209698/summary.json` 및 같은 경로 `source-hashes.json`, `cli-*.json`, `api.log`. 원본 공개 파일 **426개 변경 0**, 사용 가능 이미지 **357개**. API 캐시 없는 전체 실패와 이후 복구까지 포함하며 마지막 status=succeeded, revision=8, unresolved=[], 실패 집계 모두 0. 이 실행 전에 필수 인자를 빠뜨린 검사기 호출 1회는 argparse 종료 2로 제품 검증을 시작하지 않았으며 검사 수에 포함하지 않는다.

## 전달·남은 범위

변경 소유 파일: PresentationService.cs, Program.cs의 서비스 생성 1곳, presentation/account/spec Python 3개, prepare-presentation.ps1의 최소 CLI 전달, Backend 전용 Python 단위·CLI/API 테스트 2개, 본 문서. UI·전투 엔진·QA 독립 검사기·README 수정 없음. README 안내 변경이 필요하면 Director가 통합 시 결정한다.

확정 커밋/보고서를 기존 Director와 검수 agent 터미널에 각각 한 번 전달하고 Q-IMG 수용 조건에 따른 독립 검수를 요청한다. 입력 accepted는 검수 통과가 아니다. 브라우저 수용은 Q-IMG 담당이며 이번 Backend 검증에는 포함하지 않는다. EXE 재배포·사용자 서버 갱신은 미수행이고 이 배정의 범위 밖이다.
