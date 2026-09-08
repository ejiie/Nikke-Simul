# P01 계정 수집기와 재현 도구

일반 사용자는 루트의 `npm run dev`로 UI를 열고 계정을 연결한다. 아래 CLI는 개발·검증용이다.

`collector.py`는 login/collect 작업을 실행하고 stdout에 schemaVersion 1 JSONL 진행 이벤트를 반환한다. 부모 C# 프로세스가 작업·취소·시간 제한을 관리한다. 세션은 Windows DPAPI로 암호화하며 채팅이나 원천 snapshot에 쿠키를 넣지 않는다. 로그인 context에는 API 헤더를 주입하지 않는다.

`prepare_catalog.py`는 P00의 고정 upstream에서 표시 이름·OL 단계·소장품 매핑과 원천 hash를 준비한다. `replay_legacy.py`는 기존 저장 파일의 게임 API 3종만 P01 envelope로 옮기며 로그인 패킷은 제외한다. 실제 계정의 원천·산출물은 Git 제외 경로에 둔다.

## 격리 통합 검증

저장소 루트 PowerShell에서 실행한다. API 인스턴스가 같은 데이터 폴더를 동시에 사용하지 못하도록 파일 잠금을 둔다.

```powershell
. ./scripts/common.ps1
Enable-ProjectEnvironment
$env:NIKKE_PROJECT_ROOT = $ProjectRoot
$env:NIKKE_PYTHON = Get-ProjectPython
$dotnet = Get-ProjectDotnet
& $env:NIKKE_PYTHON tools/data-pipeline/tests/make_fixture.py artifacts/p01/synthetic-envelope.json
& $dotnet run --project tools/Nikke.SyncAudit -c Release -- artifacts/p01/synthetic-envelope.json data/local/game-catalog.json artifacts/p01/test-store artifacts/p01/synthetic-report.json
$env:NIKKE_DATA_ROOT = Join-Path $ProjectRoot 'artifacts/p01/test-store'
$env:NIKKE_TEST_FIXTURE = Join-Path $ProjectRoot 'artifacts/p01/synthetic-envelope.json'
$env:NIKKE_PORT = '5181'
& $dotnet run --project src/Nikke.Api -c Release --no-build --no-launch-profile
```

다른 PowerShell에서:

```powershell
. ./scripts/common.ps1
& (Get-ProjectPython) tools/data-pipeline/tests/check_api_ui.py
```

테스트 종료 후 5181 검증 서버를 종료한다. 일반 UI 실행용 PowerShell에는 NIKKE_TEST_FIXTURE/NIKKE_DATA_ROOT/NIKKE_PORT 환경변수를 설정하지 않는다. 검증 서버는 실제 계정 로그인 동작을 제공하지 않는다.

Python 테스트: `python -m unittest discover -s tools/data-pipeline/tests -v`.

원천 출처와 수정 내역: `docs/p01-source-map.ko.md`. 프로필 수집기의 예외 메시지에는 요청 헤더·쿠키를 출력하지 않는다.
