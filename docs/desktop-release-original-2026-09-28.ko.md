# 원본 main 및 실제 사용자 실행본 갱신 — 2026-09-28 (client_f32)

> 이후 2026-09-29에 원본 실행본이 다시 갱신됐다: [2026-09-29 원본 배포 기록](desktop-release-original-2026-09-29.ko.md). 이 문서의 client_f32 변경 내용은 그대로 유효하다.

## 현재 사용 경로

**사용자는 기존 바탕 화면 `Nikke Simul.lnk`를 실행하면 된다.** 대상은 원본 실행 파일 `C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe`이며, 바로가기 대상이 이 경로임을 배포 후 다시 확인했다. 바로가기와 경로는 변경하지 않았다. 원격 push는 하지 않았다.

## 배포 내용

사용자 승인(2026-09-28): Director 통합 후 원본 배포 2~5단계. 배포 제품은 [client_f32 통합·QA 기록](client-f32-integration-assignments-2026-09-28.ko.md)에서 독립 QA(A·B1·B2)를 통과하고 Director `6cbb2db`로 통합한 트리다(엔진 `5ced15a`, Backend `74ca24f`, UI `0e83328`, QA `1abba9b`).

사용자에게 보이는 변화:

- 단일 히트 검산·솔로 레이드 replay·단일 덱 통계의 기본 대미지 정책이 **`client_f32`**(공격력 `long` 조립 → float32 대미지 경로 → 사사오입)로 바뀌었다. 과거 3정책은 비교 후보로 남는다. 합성 5인 180초 기준 팀 합계 차이는 +0.0003%였다(실게임 정확도 판정 아님).
- 단일 히트 검산에 실험 입력 `statDamageRatio`(기본 1)·`defenceRatioRate`(기본 0)가 생겼다. 둘 다 의미 미확정 실험 항목이다.
- 기존 저장 단일 히트 입력(schema 2)은 두 필드를 1/0으로 채운 명시 변환으로 열리며 원본이 보존된다. 소수 공격력·DEF·고정 부여, 1/10000보다 정밀한 공격력 비율은 절삭 없이 오류로 거부된다.
- 이전 엔진 규칙으로 만든 단일 덱 통계 실험은 조회만 가능하고 재개할 수 없다(새 통계와 혼합되지 않음).

## 절차와 결과

1. **사전 확인:** 원본 저장소 작업 트리 깨끗(`git status` 0행). 원본 배포 경로의 프로세스 없음, 5180·5181 미사용. 떠 있던 `dotnet` 프로세스는 빌드 서버였고 종료하지 않았다.
2. **보존 사전 스냅샷:** 원본 `data/local`의 계정 DB 8개 테이블 행 내용 hash와 presentation 447파일 hash를 읽기 전용으로 기록했다(`preservation.py before`).
3. **원본 main 통합:** 원본 `main`을 `a5ccba6`에서 Director `a302931`까지 **fast-forward**(로컬). 이후 추가된 커밋은 이 배포 기록·README 등 문서뿐이며 제품 소스는 빌드 당시와 같다.
4. **백업:** 기존 실행 파일 폴더 전체(630파일, 237,864,846바이트)를 원본 `artifacts/desktop-backups/before-main-20260928/`에 복사했다. 바이너리·설정 백업이며 계정 DB 복사본이 아니다.
5. **빌드:** 원본 위치에서 공식 스크립트로 API·Desktop을 Release/win-x64 publish. 기존 데이터를 재생성하지 않도록 `-DataRoot`에 원본 `data/local`을 명시했다. 이미지 다운로드·계정 동기화 없음. 종료 코드 0.

```powershell
$env:NIKKE_PYTHON='C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
./scripts/desktop.ps1 -Action build -DataRoot 'C:/Users/user/Documents/GitHub/Nikke-Simul/data/local' -Port 5180
```

`desktop.settings.json`: projectRoot=`C:/Users/user/Documents/GitHub/Nikke-Simul`, dataRoot=`…/data/local`, port=5180, 기존 Python — 이전과 같다.

| 원본 배포 파일 | 이전 SHA256 | 새 SHA256 |
|---|---|---|
| Nikke Simul.exe | `37095189…0de02214` | `3dc843e2ff5c52ea1c4b2af7c0f49ed08ac1887ef39428d0ceb9de23bada410d` |
| Nikke Simul.dll | `141ccc94…dedede2fc4` | `e86fb69094dd2a6cf5bb47eaba1ccac7d7143c1121c658a69fafdc177f9d73e1` |
| backend/Nikke.Api.dll | `f9b45f95…d55c07555` | `718e66c5ad93464c15d9e3dece641a1835466071500ee022e99714bc433619ba` |
| backend/Nikke.Core.dll | — | `68da9c30ff03725bb01ef15fc9623eeb8882090481f89281a6871d085901c736` |
| backend/Nikke.Engine.dll | — | `8883bdf439bc14ee67c1909d0d9519f59f9c31d2a0a4e2608810628e68a767eb` |

이전 hash 전체는 백업 폴더의 파일로 재계산할 수 있다.

## 실제 사용 경로 검증

1. **바탕 화면 바로가기**를 일반 실행했다. 원본 `Nikke Simul.exe`(PID 26748)가 같은 폴더의 `backend/Nikke.Api.exe`(PID 27720)를 자식으로 시작했고 5180 소유자가 그 백엔드였다. PID는 검증 당시 식별자다.
2. `/api/health`: status ok, projectRoot = 원본 경로, singleHitCalculator·desktopUi true.
3. 5180이 `/editor/`로 제공하는 `index.html`, `app.js`, `hit-policy.js`, `compute-adapter.js`, `single-deck-stats.js`, `damage-log.js`, `damage-log-adapter.js`, `burst-tactics.js`, `simul.css` 9개가 원본 디스크 파일과 **응답 원본 바이트 SHA256 일치**. 제공 중인 `hit-policy.js`는 `CLIENT_F32_WIRE.confirmed: true`.
4. 읽기 전용 GET: bootstrap(계정 연결 3·작업 이력 7), 현재 계정 snapshot(캐릭터 200), presentation status, compute hardware 정상 응답.
5. 헤드리스 Chromium으로 5180 `/editor/`를 로드만 했다(클릭·저장·전투 실행 없음): 페이지·콘솔 오류 0, 모듈의 기본 정책 `client_f32`, 홈 화면에 계정 카드와 "단일 덱 통계" 탭 표시. 캡처는 Git 제외 `artifacts/director/release-original-20260928/editor-headless.png`(계정 이름 포함, 커밋하지 않음).
6. **보존 사후 비교:** 계정 DB 8개 테이블과 presentation 447파일 hash가 배포 전과 **완전히 동일**(`preservation-after.json` identical=true). 사용자 미추적 `package-lock.json` hash도 동일.

검증자는 계정·편성·버스트 저장, 동기화, 전투 실행, 단일 히트 저장, 통계 실험 생성을 하지 않았다. 실제 WebView2 창의 화면 관찰(computer-use)과 EXE `--smoke-output` 검사는 이번에 수행하지 않았다 — 실제 창에서의 확인은 사용자 사용 보고로 이어진다. 실게임 대미지 정확도, 실측 18점 대조, GPU, 부하 성능은 이번 배포 검증 범위가 아니다.

마지막으로 바로가기에서 실행한 앱은 사용자가 바로 쓸 수 있도록 열어 두었다.

## 되돌리기

문제가 있으면 앱을 종료한 뒤 `artifacts/desktop-backups/before-main-20260928/`의 내용을 `artifacts/desktop/win-x64/`로 복원하면 이전 EXE·백엔드로 돌아간다. 단 API는 projectRoot의 `apps/desktop-ui`를 제공하므로 UI까지 되돌리려면 원본 `main`의 소스도 `a5ccba6` 기준으로 맞춰야 한다(AGENTS.md 참조). 되돌리기는 사용자 지시가 있을 때만 수행한다.
