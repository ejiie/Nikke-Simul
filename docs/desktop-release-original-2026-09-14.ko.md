# 원본 main 및 실제 사용자 실행본 갱신 — 2026-09-14

## 현재 사용 경로

**사용자는 기존 바탕 화면 `Nikke Simul.lnk`를 실행하면 된다.** 대상은 다음 원본 실행 파일이다.

`C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe`

바로가기는 이미 이 경로를 가리키므로 변경하지 않았다. Director worktree의 EXE를 정식 실행 위치로 대체하지 않는다. 이번에는 원본 로컬 main 통합뿐 아니라 원본 EXE·동봉 백엔드·실행 설정의 재빌드 및 실제 바로가기 실행까지 수행했다. 원격 push는 하지 않았다.

## 원인과 정정

앞선 작업은 Director에서만 완료 커밋 통합·배포·검증을 수행했다. 원본 main은 `e6935857c35caac198c649e744132d7391721ecb`에 남아 있었고 최신 `burst-tactics.js`, `damage-log.js`도 없었다. 원본 EXE의 설정은 원본 projectRoot를 사용했다. API는 EXE 내부가 아니라 해당 projectRoot의 `apps/desktop-ui`를 제공하므로, 사용자가 원본 폴더에서 직접 EXE를 실행해도 이전 화면이 표시됐다. 바로가기 문제로만 설명하거나 EXE 한 개 교체로 충분하다고 볼 수 없는 배포 누락이었다.

사용자 승인 후 원본 작업 상태가 깨끗하고 조상 관계임을 확인하여 main을 Director 완료 커밋 `e32ede9a017175dbc210425a53aa0205397f1e3d`까지 fast-forward했다. 그 소스를 원본 위치에서 다시 빌드했다. 이후 추가 커밋은 이 배포 기록·README·재발 방지 지침뿐이며 제품 소스는 빌드 당시와 같다.

## 빌드·백업·설정

- 원본 배포 경로를 사용하는 프로세스가 없고 5180이 비어 있음을 확인했다.
- 기존 실행 파일 폴더 전체를 원본 `artifacts/desktop-backups/before-main-20260914/`에 복사해 보존했다. 이는 바이너리/설정 백업이지 계정 DB 복사본이 아니다.
- 원본 프로젝트의 공식 `scripts/desktop.ps1`로 API와 Desktop을 각각 Release/win-x64/self-contained/locked restore publish했다. 두 publish 모두 성공했고 출력에 경고·오류가 없었다.
- 기존 자료를 재생성하지 않도록 `-DataRoot`에 원본의 준비된 `data/local`을 명시했다. 이미지 다운로드·계정 동기화를 하지 않았다.
- 생성된 `desktop.settings.json`: projectRoot=`C:/Users/user/Documents/GitHub/Nikke-Simul`, dataRoot=`C:/Users/user/Documents/GitHub/Nikke-Simul/data/local`, port=5180, Python은 기존 runtime Python이다. 설정과 EXE 모두 원본 위치에 있다.

원본 저장소를 현재 디렉터리로 한 실제 빌드 명령:

```powershell
$env:NIKKE_PYTHON='C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
./scripts/desktop.ps1 -Action build -DataRoot 'C:/Users/user/Documents/GitHub/Nikke-Simul/data/local' -Port 5180
```

| 원본 배포 파일 | SHA256 |
|---|---|
| Nikke Simul.exe | `32d1b8714e3f9b7f12dab13d188a467f2cf03dae5dad9107145318149cdee4e7` |
| Nikke Simul.dll | `8a02a3dfaee1cf4dd275f8d4c5841505ba2fde3176f4b982d44493fc0fc9aca4` |
| backend/Nikke.Api.dll | `26ce05920c1fd6973ae62c2897474a3a9dcb58da94c8858b9f2f83ec69342eb6` |

## 원본 위치에서 수행한 검증

1. C# Core/Engine 113 + Sync 81 = **194개 통과**, 실패/skip 0. 원본 소스를 직접 빌드해 실행했다. TRX는 원본 `artifacts/main-release-20260914/tests/`의 `2026-09-14_14_38_37` 및 `14_39_27` 파일이다.
2. 원본 EXE의 `--smoke-output` 실제 WebView2 검사: 종료 코드 0, 카드 200개, 브랜드 이미지 정상, 화면의 완료 이미지 중 깨진 이미지 0. 검사 후 자신이 시작한 백엔드와 함께 종료됐다.
3. 이어서 **실제 바탕 화면 바로가기**를 일반 실행했다. 원본 EXE PID 42728이 같은 원본 폴더의 `backend/Nikke.Api.exe` PID 29684를 자식으로 시작했다. 5180 `/api/health`의 projectRoot도 원본 경로로 확인했다. PID는 이 검증 당시 식별자이며 고정 설정이 아니다.
4. 5180이 제공하는 `app.js`, `burst-tactics.js`, `damage-log.js`, `damage-log-adapter.js`, `simul.css` 5개가 모두 HTTP 200이며 원본 디스크 파일과 **응답 원본 바이트 SHA256이 일치**했다. PowerShell 문자열 디코딩 후 hash로 대체하지 않았다.
5. `/api/presentation/status`에서 이번 수정의 `failureSummary`, `unresolved` 필드가 확인됐다. 기존 캐시를 사용하는 기동 상태는 idle/revision 0이었다. 이것을 실네트워크 이미지 갱신 성공으로 표현하지 않는다.
6. computer-use로 바로가기에서 열린 실제 창을 복원·관찰했고, 솔로 레이드의 간소화된 **버스트 사용 니케 및 순서 설정**, I/II/III 단계, 빠른 설정 버튼과 순서 표시가 실제 화면에 나타남을 확인했다. 검증자가 계정·편성·버스트 저장 또는 전투 실행 버튼을 누르지 않았다.
7. 빌드와 EXE 검증 전후 계정 DB 8개 테이블의 행 내용 및 presentation 디렉터리 전체 447파일 hash가 동일했다. Director의 사용자 미추적 `package-lock.json`도 보존했다. 5181은 종료·재시작하지 않았고 health 정상이다.

화면·보존 근거는 Director `artifacts/director/release-original-20260914/`에 보관했다: `desktop-smoke/{desktop-smoke.json,desktop.png}`, `shortcut-burst-screen.png`, `preservation-before.json`, `preservation-after.json`, `preservation.py`. 바로가기 화면 캡처 SHA256은 별도 원본 파일을 기준으로 확인했다. 계정 화면은 Git에 추가하지 않는다.

마지막 일반 실행 앱은 사용자가 바로 쓸 수 있도록 열어둔다. 전체 CDN 가용성과 대미지 실게임 정확도는 이번 재배포 검증 범위가 아니다. 이미지 실패·복구의 독립 수용 범위는 [Q-IMG 보고서](image-catalog-fix-verification.ko.md) 및 [앞선 제품 실행 검사](desktop-release-2026-09-14.ko.md)를 참조한다.

## 재발 방지

루트 [AGENTS.md](../AGENTS.md)에 실제 사용 경로, 원본 로컬 커밋 통합, EXE/백엔드 재빌드, 설정·UI 연결, 실제 바로가기 검증, 계정 보존까지 배포 완료 조건으로 명시했다. README의 현재 실행 안내도 원본 위치로 정정했고 앞선 Director 보고서는 역사 기록으로 표시했다. 앞으로 worktree 검증만 끝난 상태를 원본 반영 완료로 보고하지 않는다.
