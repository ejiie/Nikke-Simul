# Director 이미지 카탈로그 수정 통합·배포 — 2026-09-14

## 결과와 실행 방법

사용자의 후속 착수 승인에 따라 B-IMG 제품 수정과 Q-IMG 독립 검수를 Director에 통합하고, 이 PC의 기존 Director 배포 경로에 새 self-contained API/Windows 실행본을 배포했다. 실제 EXE의 WebView2 검사도 통과했다. 전투 엔진·피해 공식·추가 UI 기능은 이번에 수정하지 않았다.

- 실행 파일: `C:/Users/user/orca/workspaces/Nikke-Simul/Director/artifacts/desktop/win-x64/Nikke Simul.exe`를 실행한다.
- 함께 필요한 파일은 같은 폴더 및 `backend/`에 있다. EXE 한 개만 복사하는 독립 배포본이 아니다.
- `desktop.settings.json`: projectRoot는 Director, port는 5180, dataRoot는 `C:/Users/user/Documents/GitHub/Nikke-Simul/data/local`, Python은 기존 Codex runtime Python 경로다. 이전 설정을 그대로 복사했다.
- Documents/GitHub 쪽 이전 EXE는 이번 배포 대상이 아니다. 5181 개발 서버도 별개이며 종료·재시작하지 않았다.
- 자동 검증 실행은 종료 코드 0으로 끝났고, 자신이 만든 5180 백엔드도 종료됐다. 사용자는 위 EXE를 다시 실행하면 된다.

## 통합 이력과 수정 내용

Director `04a16be8cc0f84449d8b41ad9d37f53c692338df`에서 QA 결과 `d67204bcc09e0b88d5cad84538c1a6e705419918`까지 fast-forward했다. 제품 확정 커밋은 `104646006318f252f01b8d39b3424316e0a262ba`, QA의 제품·검사 통합 커밋은 `908f37f06cd3910c5d20f1a101ebaa851672ff9e`다. 배포용 제품 소스는 이 통합 상태이며, 이후 Director 변경은 배정·배포 문서와 README뿐이다.

외부 dataRoot가 API → Python CLI → account/spec helper까지 전달된다. 종전 오류의 원인은 이미지 두 장 누락이 아니라 코드 루트에서 계산 자료와 game-catalog를 찾던 카탈로그 준비 실패 두 건이었다. 이제 이미지 파일 오류와 카탈로그 준비 오류를 별도로 집계·표시하며, 캐시 사용 여부를 구분하고 복구 후 이전 오류를 지운다. UI 파일을 추가로 수정하지 않고 서버 응답 문구를 고쳤다.

제품 세부사항은 [Backend 보고서](image-catalog-fix.ko.md), 독립 수용 근거는 [Q-IMG 보고서](image-catalog-fix-verification.ko.md), 배정 당시 경계는 [배정 기록](image-catalog-fix-assignments-2026-09-14.ko.md)에 있다.

## 검수팀 결과와 Director 재검증 구분

Q-IMG가 수행한 실제 CLI 24회/API 갱신 31회/Edge 28그룹 수용 통과는 해당 보고서 및 QA 작업공간의 `artifacts/image-collection-qa/f-6fcaf1957f4e/summary.json`을 대조했다. 이 전체 행렬을 Director가 다시 실행했다고 주장하지 않는다.

Director에서 직접 수행한 결과:

- 기존 Python 이미지 테스트 3개 + 경로/오류 회귀 8개 통과.
- 독립 판정기 합성 자체 테스트 10개 통과. 이것만으로 제품 수용을 선언하지 않는다. 근거: `artifacts/image-collection-qa/oracle-f75f682f3dd045268487ccb31e69980f/`.
- C# Sync Release 81개 통과, 실패/skip 0. TRX: `artifacts/director/release-20260914/csharp/user_BOOK-UB6JGJ0BM4_2026-09-14_13_59_54_net10.0.trx`.
- API와 Desktop을 Release/win-x64/self-contained/locked restore로 각각 publish 성공. 성공한 두 publish 출력에는 경고·오류가 없었다.
- Backend의 `tests/Nikke.Sync.Tests/check_image_catalog_api.py` 수용 조건을 그대로 사용해 **이번에 publish한 `package/backend/Nikke.Api.exe`**로 CLI/API 13그룹 통과. 기본 테스트가 실행하는 비-RID DLL 경로만 로컬 검증 어댑터에서 새 EXE로 치환했으며, 실제 EXE가 한 번 실행됐는지도 assert했다. 원본 제품/테스트 코드는 변경하지 않았다.
- 위 검사는 공개 파일 복사본과 합성 HTTP 응답만 사용하고 별도 포트 62419에서 실행했다. API 최종 `succeeded`, revision 8, imageFailures/catalogFailures/cachedFailures 모두 0, availableImages 357, unresolved `[]`. 원본 공개 파일 426개 hash 변경 0. 근거: `artifacts/image-catalog-fix/4aede8c011754b93b26c184b5a5daf9b/summary.json`; 어댑터: `artifacts/director/release-20260914/verify_bundle.py`.
- 배포 경로의 실제 `Nikke Simul.exe --smoke-output ...` 종료 코드 0. 실제 WebView2 카드 200개, 브랜드 이미지 로드, 화면에 표시된 완료 이미지 중 깨진 이미지 0. 저장된 화면도 직접 확인했다. 근거: `artifacts/director/release-20260914/desktop-smoke/{desktop-smoke.json,desktop.png}`.
- 실제 EXE 실행 전후 원본 presentation 디렉터리의 **전체 447파일**, 계정 DB **8테이블의 행 내용**, 사용자 `package-lock.json` hash가 모두 동일했다. 이미지에 한정한 357개와 디렉터리 전체 447파일은 서로 다른 집계다. 근거: `artifacts/director/release-20260914/preservation-before.json`, `preservation-after.json`, `preservation.py`.
- 검증 종료 후 5180 없음, 기존 5181 health 정상 확인. 계정 편집·저장·동기화·전투 실행·원본 이미지 갱신 POST는 하지 않았다. 원본의 기존 manifest 역시 강제로 재생성하지 않았다.

## 배포 파일과 백업

새 파일은 먼저 `artifacts/director/release-20260914/package/`에 publish했다. 격리 API 검사를 통과한 뒤 대상 배포 경로를 사용하는 프로세스가 없음을 확인하고, 기존 폴더 전체를 `artifacts/director/release-20260914/previous-package/`에 복사한 다음 새 배포 파일로 교체했다. 스테이징·배포 파일의 아래 hash가 일치한다.

| 배포 파일 | SHA256 |
|---|---|
| Nikke Simul.exe | `34f86728ce6203956691aff16247dc448d1a326fc7a2869d48c084f41eea6dad` |
| Nikke Simul.dll | `65a1947c43bcb87b431e1f89991e5eb6a869aca4030615cb12fd1ceedf1c59ed` |
| backend/Nikke.Api.dll | `60677a3985dd7f45c54de1b70cfc555b3f87e13206e4b43d6f4ae70ff5da4e50` |

백업은 이전 실행 파일 묶음과 설정이며 계정 DB 복사본이나 소스 전체 롤백본은 아니다. 기존 파일을 삭제하지 않았다. 사용자 `package-lock.json`은 미추적 상태로 보존·커밋 제외했다(SHA256 `2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767`). 실행 산출물과 계정 화면 캡처는 Git 제외 artifacts 안에만 남겼다.

## 재현 명령 및 실패 이력

이 환경에서는 기존 저장소의 `.tools/dotnet/dotnet.exe` 및 `.tools/nuget-packages`를 사용하고, `DOTNET_CLI_HOME`은 Director `.tools/dotnet-home`으로 지정했다. publish 명령은 다음과 같다(아래 `dotnet`은 해당 고정 SDK 실행 파일).

```powershell
dotnet publish src/Nikke.Api -c Release -r win-x64 --self-contained true -o artifacts/director/release-20260914/package/backend --configfile nuget.config -p:RestoreLockedMode=true
dotnet publish src/Nikke.Desktop -c Release -r win-x64 --self-contained true -o artifacts/director/release-20260914/package --configfile nuget.config -p:RestoreLockedMode=true '-p:ApplicationIcon=C:/Users/user/Documents/GitHub/Nikke-Simul/data/local/desktop-branding/app.ico'
```

최초 비-RID API `build --no-restore`는 5181이 사용하는 출력 DLL 잠금으로 실패했다(MSB3026/3027/3021, 경고 50/오류 10). 서버를 종료하는 대신 별도 RID/배포 출력으로 전환해 성공했다. 최초 publish는 샌드박스의 NuGet.Config 접근 거부로 실패했고 해당 명령만 승인받아 재실행했다. SQLite 읽기 전용 보존 점검도 첫 샌드박스 실행에서는 DB 접근이 거부되어 같은 읽기 검사를 승인받아 재실행했다. 실패한 시도를 제품 성공 검사로 집계하지 않는다.

## 남은 범위

이번 수정의 통합·이 PC Director EXE 배포·기본 화면 확인은 완료다. 실제 전체 CDN의 현재 가용성, 사용자가 원본 계정에서 누르는 전체 이미지 갱신의 실네트워크 결과, 전투 대미지 영점/사이클 정확도는 이번 배포 검증 범위가 아니다. 실제 CDN 장애가 발생하면 이제 실패 종류와 캐시 사용 여부를 구분해 표시하는 것이 기대 동작이며, 모든 외부 요청의 성공을 보장하는 수정은 아니다.
