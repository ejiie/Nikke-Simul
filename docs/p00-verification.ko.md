# P00 검증 보고서

실행일: 2026-09-08. 상태: **P00 완료 / P01 대기**.

## 완료 조건 확인

| 조건 | 결과 |
|---|---|
| 원본 버전·선택 파일·라이선스 추적 | upstream commit 고정, C# 원본 63개 hash, DataPipeline 후보 hash, 실제 이식 파일·MIT 원문 hash 보존 |
| 빌드·테스트 골격 | .NET 10 solution, locked NuGet restore, setup/verify/web 실행 스크립트 |
| 작은 C# 계산 fixture 실행 | `finalStat=103`, `timeCs=97`, `passed=true`; 전투 엔진 연결 여부는 명시적으로 false |
| 웹 개발 화면 실행 | `127.0.0.1:5173/nikke-calc/`에서 실제 브라우저로 화면·200명 목록·계산 준비 완료 상태 확인 |
| 기존 프로젝트 보존 | 기존 소스를 수정하지 않고 별도 `.reference` 복사본으로 .NET 8 기준 테스트 실행 |
| 개인 데이터 분리 | 필요한 13개 로컬 데이터만 무시되는 참조 디렉터리에 복사. 소스 저장 대상에서 제외 |

## 환경

- Windows / PowerShell, Node.js 24.16.0, npm 11.13.0, Python 3.12.14.
- 신규 코어: SDK 10.0.400, target `net10.0`. 프로젝트 내부 `.tools/dotnet` 사용.
- 기존 C# 기준 테스트: 시스템 SDK 8.0.407, target `net8.0`. 원본 프로젝트 파일 유지.
- upstream: TypeScript 7.0.2, Vite 8.2.1, Vitest 4.1.10, jsdom 29.1.1. 고정 commit의 npm lock으로 설치.

## 실행 결과

| 검증 | 결과 | 근거 로그 (`artifacts/p00/`) |
|---|---|---|
| 새 코어 Release build | 오류 0, 경고 0 | `core-verify.log` |
| 새 코어 OL 계산 tests | 8/8 통과 | `core-verify.log` |
| 작은 계산 fixture·이식 hash | 계산 기대값 일치; C# 2파일 + LICENSE 원문 동일 | `core-verify.log` |
| 기존 C# tests, 13개 데이터 준비 후 | 170/170 통과, runner skip 0 | `legacy-with-data.log`, `legacy-with-data.trx` |
| upstream Python unittest | 163 통과 / 1 skip / 총 164 | `upstream-python-tests.log` |
| Python ↔ 웹 bridge | 49 통과 / 1 skip / 총 50 | `upstream-bridge.log` |
| upstream 기존 전투 snapshot | 29/29 통과, baseline 수정 없음 | `upstream-snapshot.log` |
| upstream 대미지 자체 검산 | 8개 번호 그룹 및 하위 사례 통과 | `upstream-damage.log` |
| upstream 캐릭터 문서 정합성 | 200명 / 완료목록 200명, OK | `upstream-doclint.log` |
| upstream 웹 최초 기본 실행 | 635 통과 / 7 실패 / 총 642; 실패는 UI 테스트 5초 시간 초과 | `upstream-web-tests.log` |
| upstream 웹 로컬 조건 재검증 | 36개 파일, 642/642 통과 | `upstream-web-local-tests.log` |
| upstream 웹 build | TypeScript·runtime 검사·Vite build 통과; runtime 25파일/200명 | `upstream-web-build.log` |
| Pages 설정 검사 | `check-pages` 통과; 배포는 수행하지 않음 | 터미널 출력 |
| 브라우저 개발 화면 | 렌더링 및 Python 엔진 준비 완료 확인 | 브라우저 상태·스크린샷 확인 |

최종 진입점 `npm test`도 재검증했다(`core-final-verify-fixed.log`, exit 0). npm에서 시작한 PowerShell 환경에서 `Get-FileHash` 모듈을 찾지 못하는 문제를 발견해, 검증 스크립트의 SHA-256 계산을 .NET 런타임 호출로 변경했다. 앞선 실패 로그 `core-final-verify.log`도 보존했다. Codex 제한 실행 환경에서는 사용자 NuGet.Config 접근이 차단되어, 최종 빌드·테스트는 승인된 일반 사용자 권한 실행으로 확인했다. 이 환경 문제로 소스·테스트 기대값을 변경하지 않았다.

웹 재검증은 `--maxWorkers=2 --testTimeout=30000`을 사용했다. 테스트 assertion이나 upstream 소스는 수정하지 않았다. 이 호스트에서는 기본 동시 실행 조건의 최초 실패를 보존하고, 로컬 실행 스크립트에 재검증 조건을 명시했다. 새 테스트가 추가된 것처럼 중복 집계하지 않는다.

Python 및 bridge의 skip은 등록된 프리뷰 캐릭터가 없기 때문이다. 기존 C#은 데이터가 없을 때 일부 테스트가 조기 반환할 수 있어 runner의 skip 숫자만 신뢰하지 않았다. 첫 실행은 processed 데이터 11개로 170개 통과했으나, 스킬 체인·Solo Raid 보스 raw 데이터 2개를 더 준비하고 **13개 모두 존재하는 상태에서 재실행한 결과를 기준**으로 삼았다. 데이터 경로·hash는 무시되는 `legacy-data-manifest.json`에 기록했다. 이것이 모든 게임 분기나 전체 데이터 완전성을 검증했다는 뜻은 아니다.

jsdom의 canvas `getContext` 미구현 경고가 있었으며 위 웹 재검증은 통과했다. 웹 build는 약 863 kB JavaScript chunk에 대한 크기 경고가 있다. P00에서 upstream 번들을 변경하지 않았다.

## 재현

저장소 루트에서:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup.ps1
npm test
npm run test:web
npm run build
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/web.ps1 -Action check
npm run dev
```

upstream Python 기준 검증은 별도 PowerShell에서 다음과 같이 실행한다. snapshot에 `--update`를 사용하지 않는다.

```powershell
. ./scripts/common.ps1
Enable-ProjectEnvironment
$p00Python = Get-ProjectPython
$p00Reference = Assert-Reference
Push-Location $p00Reference
try {
    & $p00Python -m unittest discover -s calculator -p 'test_*.py' -v
    & $p00Python site/scripts/test-bridge.py
    & $p00Python -m calculator.damage
    & $p00Python -m context.doclint
    & $p00Python -m context.snapshot --jobs 2
} finally { Pop-Location }
```

기존 C# 재검증에는 원래 로컬 프로젝트와 SDK 8.0.407이 필요하다. 아래 준비 스크립트는 63개 소스 hash가 달라지면 멈추며, 이후 단계에서 원본이 변경되었다고 기준점을 자동 갱신하지 않는다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/prepare-legacy.ps1
$p00Root = (Get-Location).Path
Push-Location .reference/legacy-simulator
try {
    dotnet restore SimulatorEngine/Nikke.Simulator.Tests/Nikke.Simulator.Tests.csproj --configfile "$p00Root/nuget.config"
    dotnet test SimulatorEngine/Nikke.Simulator.Tests/Nikke.Simulator.Tests.csproj -c Release --no-restore
} finally { Pop-Location }
```

## P00 결과의 한계와 다음 작업

이 테스트는 **원본의 기준 상태와 새 개발 기반의 동작**을 확인한다. 두 원본의 결과가 서로 일치하거나 실게임과 일치한다고 결론 내리지 않는다. P00에서는 계정 fetch, 전체 기초 스탯/차지 이식, 히트 정수화 판정, 새 팀 버스트, SQLite 결과 저장, 반복 통계 및 추천 기능을 구현하지 않았다.

다음은 P01의 snapshot/입출력 계약과 스펙 정규화다. 이어서 P02에서 C# 기초 스탯 전체를 이식하고, 확정 차지식을 적용한 뒤 히트 정수화만 분리해 비교한다. 실제 기능별 출처와 후속 이식 후보는 [출처표](source-map.ko.md)에 기록했다.
