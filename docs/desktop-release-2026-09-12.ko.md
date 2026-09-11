# Director 실행본 갱신 — 2026-09-12

## 반영 범위

UI 보완 `b6c5064` 위에 기존 미커밋 버스트 UI·문서·검사기 변경 14개 파일을 `30ecab6`으로 커밋했다. 사용자 미추적 `package-lock.json`은 제외했다. 방어력 자동 전환·실게임 영점 보정·새 UI 기능·agent 완료 알림 구성은 이번 범위가 아니다.

Director에는 기본 `data/local` 데이터가 없어 기존 빌드 설정만으로 새 EXE를 시작할 수 없었다. 호스트에 선택적 `DesktopSettings.DataRoot`를 추가해 동봉 백엔드의 `NIKKE_DATA_ROOT`와 `NIKKE_GAME_CATALOG`로 전달한다. 생략하면 기존 동작을 유지한다. `scripts/desktop.ps1`은 `-DataRoot`/`-Port`를 지원하고, 외부 데이터 지정 시 필수 파일을 확인한 뒤 이미지 자료를 재생성하지 않는다. 기존 아이콘을 재사용하고 locked restore로 publish한다. 전투 계산 코드는 변경하지 않았다.

## 이번 실행 파일과 데이터

- 새 EXE: `C:/Users/user/orca/workspaces/Nikke-Simul/Director/artifacts/desktop/win-x64/Nikke Simul.exe`.
- 설정: 같은 폴더의 `desktop.settings.json`. 프로젝트는 Director, 포트는 5180, 데이터는 `C:/Users/user/Documents/GitHub/Nikke-Simul/data/local`이다.
- 최신 UI는 Director의 `apps/desktop-ui`에서 제공하며, 동봉 `backend/Nikke.Api.exe`가 백엔드를 자동 시작한다. EXE 하나만 다른 위치로 옮겨 쓰는 독립 배포본은 아니다.
- 기존 Documents/GitHub 쪽 EXE·소스는 덮어쓰지 않았다. 5181 개발/검산 서버와 그 별도 데이터도 그대로다. **5181 복사본에서 변경한 편성·전술·로그를 본 계정 DB에 자동 이식하지 않았다.** 새 실행본에서는 사용할 계정을 선택하고 해당 계정의 편성을 확인한다.
- 새 실행본은 실제 본 계정 데이터에 저장한다. 이번 검증에서는 계정/스펙/편성 저장·동기화·전투 실행 버튼을 누르지 않았다. 첫 시작 시 기존 저장소 코드가 필요한 새 스키마를 준비할 수 있다.

재빌드 예(고정 SDK가 PATH에 있거나 프로젝트 `.tools/dotnet`에 준비된 환경):

```powershell
npm run build:desktop -- -DataRoot 'C:/Users/user/Documents/GitHub/Nikke-Simul/data/local' -Port 5180
```

이번 환경에는 Director의 SDK가 없어 기존 저장소의 `.tools/dotnet/dotnet.exe`와 NuGet 캐시를 명시적으로 사용해 API/호스트를 각각 `publish -c Release -r win-x64 --self-contained true --configfile nuget.config -p:RestoreLockedMode=true`로 빌드했다. 호스트의 `ApplicationIcon`은 기존 `data/local/desktop-branding/app.ico`다. 같은 폴더의 실행 설정에 위 경로를 기록했다. 원본 이미지를 다시 다운로드하거나 원본 계정 파일을 복사하지 않았다.

## 직접 재실행한 검증

- 전체 C# 회귀: Core/Engine 113 + Sync 81 = **194 통과**, 실패/skip 0. `artifacts/director/release-20260912/csharp/*.trx`.
- UI 계약: **26 통과**. `artifacts/director/release-20260912/ui-4f92825e-840f-4448-97d8-4ff99864684a/summary.json`.
- 피해 설명 단위: **19 통과**, 실제 저장 로그 134행 대조. `artifacts/director/release-20260912/audit/unit-summary.json`.
- 통계 분석기: **22 통과**. `tools/damage-calibration/test_analyze.py` 직접 실행.
- API/호스트 self-contained publish 성공. PowerShell 구문 검사, JS 구문 검사, `git diff --check` 통과.
- 새 EXE의 `--smoke-output` 검사: 종료 코드 0, 실제 WebView2에서 카드 200개, 앱 아이콘 로드, 깨진 이미지 0. `artifacts/director/release-20260912/desktop-smoke/{desktop-smoke.json,desktop.png}`.
- 시작 전 5180 서버 없음 → EXE 자동 시작 → smoke 종료 후 5180 서버 없음 확인. 이어 일반 실행으로 홈과 솔로 레이드 탭 전환 및 간소화 버스트 설정을 실제 창에서 확인했다. 선택 계정의 편성은 비어 있어 미편성 진단이 표시됐으며 임의로 저장하지 않았다.
- 새 5180 서버의 `app.js`, `burst-tactics.js`, `damage-log.js`, `damage-log-adapter.js`, `simul.css` HTTP 원문 SHA256이 Director 파일과 모두 일치했다. Python urllib의 원문 바이트로 검증했다.
- 본 계정 DB의 connections/snapshots/accounts/solo_formations 정렬 행 SHA256은 실행 전후 동일했다. `package-lock.json` SHA256은 `2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767`로 유지됐다.

이번에는 원본 계정에 새 전투 로그를 만들지 않았다. 실제 API/브라우저의 피해 패널 및 저장/다운로드 검증은 [UI 최신 검수](ui-damage-audit-review-2026-09-11.ko.md)와 [간소화 UI 검증](damage-log-ui.ko.md)의 격리 실행 근거를 함께 사용한다. 실게임 정확도 검증 완료를 뜻하지 않는다.

## 실행본 식별

| 파일 | SHA256 |
|---|---|
| Nikke Simul.exe | `e4b16827aa0f7533ea921e7d0b002678fd06d9a525d3a76049420483a39819c2` |
| Nikke Simul.dll | `56ac37222657fe6a3d0294d1dbcde183c629abac1acac6ff5d430310cf56227d` |
| backend/Nikke.Api.dll | `d2c995e0bbabc3a0827be448c7e926929f906ae668f3bc07c114ca8f3c4b1ef7` |

재현 중 실패도 구분한다. 첫 C# 명령은 샌드박스의 Windows SDK 접근 거부 후 해당 명령만 승인받아 통과했다. 첫 UI 단위 명령은 위치 인자를 옵션 형태로 잘못 전달해 실패했고 입력 파일은 변경되지 않았으며 올바른 인자로 재실행했다. PowerShell의 텍스트 변환을 거친 HTTP hash는 모두 불일치해 폐기하고 원문 바이트 검사로 확인했다. 네이티브 좌표 클릭은 화면 전환이 확인되지 않아 성공으로 취급하지 않고 접근성 버튼으로 전환 후 화면 내용을 확인했다.
