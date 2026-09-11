# Nikke-Simul

Solo Raid의 대미지 시뮬레이션, 비중복 5덱 선정, 장비별 육성 효율 분석을 위한 프로젝트입니다.

[니케 PvE 전투·육성 조사](docs/nikke-pve-combat-growth-research.ko.md): 무기·버스트·스탯·장비·큐브·소장품·레이드 시스템과 현재 구현의 차이를 정리했습니다. 확인일 2026-09-09.

**Windows 실행 파일 UI:** Nikke-Local-Lab의 화면·카드·상세 탭과 WinForms/WebView2 창을 이식했습니다. [이식 범위·이미지 출처·실행 방법](docs/desktop-ui-migration.ko.md).

**2026-09-12 Director 실행본:** 간소화 버스트 설정과 피해 설명 수정이 반영된 실행 파일은 현재 작업공간의 `artifacts/desktop/win-x64/Nikke Simul.exe`입니다. 기존 본 계정 데이터 경로를 실행 설정으로 연결하며, 이전 실행 파일과 5181 검산용 데이터는 덮어쓰지 않았습니다. [빌드·실행 검증 및 사용 안내](docs/desktop-release-2026-09-12.ko.md).

**스펙 편집:** 상세 화면에서 장비·OL·스킬·성장·소장품·큐브를 변경하고 Save로 저장합니다. 공식 장비 이미지와 Local Lab 선택 UI를 사용하며, 별 3개와 코어 배지를 붙여 ±로 조정합니다. [편집·저장 범위와 출처](docs/desktop-spec-editor.ko.md).

**현재 전투 구현:** 리타·블랑·누아르·앨리스·모더니아의 스킬 효과와 팀 게이지 기반 자동 버스트 사이클을 실행합니다. UI는 참여 체크·단계별 순서·빠른 설정으로 단순화했으며, III는 체크된 순서대로 순환합니다. 기존 지정 시전/풀버스트 모드는 엔진/API에 비교용으로 유지하지만 UI에서는 제거했습니다. [버스트 UI 현재 규칙](docs/damage-log-ui.ko.md) · [P04 규칙·미검증 범위](docs/p04-team-burst.ko.md) · [P03 스킬 구현 범위](docs/p03-skill-runtime.ko.md) · [틱 대미지 측정 조건](docs/p03-measurement-guide.ko.md). 보스 기믹과 실게임 정확도는 별도 미완료 항목입니다.

**피해 로그·버스트 전략 통합 수용 통과:** 선택 니케의 실제 명중 로그, 버스트 참여자·단계별 우선순위·III 순환/첫 시전자 설정, 저장·JSON/CSV 내보내기를 통합했습니다. 실제 API·브라우저에서 서버 전술 복원→실행→로그 표시와 원본 다운로드를 검증했고, 통계 검사기의 종료 프레임 경계 수정도 22개 회귀 및 기존 실패 로그 재검산을 통과했습니다. 실게임 발당 영점·사이클 정확도 검증은 별도 미완료입니다. 수용 범위·근거·실패 이력은 [통합 검증 기록](docs/integration-verification-2026-09-11.ko.md)을 참조하세요.

**현재 P02 단일 히트 검산 구현 완료:** P01 계정 동기화에 최종 스탯 표시·확정 차지식·정수화 후보 비교·실측 입력·검산 JSON 저장을 연결했습니다. OL과 스킬 공증은 버프 적용 전 스탯을 기준으로 함께 계산합니다. [버프 처리 정정·검증](docs/p02-buff-correction.ko.md). 히트 정수화는 실측 판정 대기 중입니다.

## 실행

Windows PowerShell에서 저장소 루트를 작업 디렉터리로 사용합니다. Git, Node.js/npm, Python 3가 필요합니다. 검증 환경은 Node 24.16.0, npm 11.13.0, Python 3.12.14입니다.

```powershell
# 최초 설치: 고정 upstream checkout, 로컬 .NET SDK, npm/NuGet 의존성
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup.ps1

# 동기화 UI·Python 의존성·고정 매핑 준비
npm run setup:sync
npm run build

# 전체 C# Release 빌드·테스트·계산 fixture·원본 hash 검사
npm test

# 이미지 준비 (첨부 ZIP을 처음 가져올 때)
npm run prepare:images -- -Zip 'C:/Users/user/Downloads/character-growth-images-20260908.zip'

# Windows 실행 파일 빌드 후 실행
npm run dev

# 빌드만: artifacts/desktop/win-x64/Nikke Simul.exe
npm run build:desktop

# API만 켜는 개발 모드
npm run dev:sync

# P01 정제·저장·수집기·웹 테스트
npm run test:sync
# P01 웹 테스트만
npm run test:web

# P00 원본 Python 전투 계산기 (별도 참조)
npm run dev:reference
```

실행 파일에서 `계정 가져오기` → `블라블라 계정 연결` → 열린 브라우저에서 로그인 → 필요 시 서버 선택 → 첫 동기화를 진행합니다. 이후 `내 스펙 동기화` 버튼으로 갱신합니다. 로그인·수집에는 네트워크가 필요합니다. Microsoft Edge 또는 Playwright Chromium, 창 표시에는 WebView2 Runtime이 필요합니다. 이 PC용 빌드는 프로젝트의 기존 데이터와 Python 경로를 사용하므로 EXE만 다른 PC로 복사하는 배포본은 아닙니다. 개발 확인 주소는 [관리 화면](http://127.0.0.1:5180/editor/)입니다.

원본 참조 계산기는 별도 5173 포트에서 Python/Pyodide로 실행됩니다. 이 원본 화면에서는 작성자의 프로필 프록시·공유 API 설정을 비활성화합니다. 새 동기화 기능은 로컬 C# API와 사용자 자신의 세션을 사용합니다.

.NET SDK 10.0.400은 `.tools/dotnet`에 설치하며 시스템 설치를 변경하지 않습니다. 이미 해당 SDK를 설치했다면 setup에 `-SkipSdk`를 사용할 수 있습니다. Python 경로를 자동으로 찾지 못하면 `$env:NIKKE_PYTHON`에 Python 실행 파일의 절대 경로를 지정합니다.

## 원본과 결과물

- [기능별 출처표](docs/source-map.ko.md): 실제 이식, 참조 실행, 후속 이식 후보 구분.
- [P00 검증 보고서](docs/p00-verification.ko.md): 최초 실패·재검증·skip과 재현 명령.
- [구현 계획](docs/implementation-plan.ko.md): P00~P09 순서와 완료 조건.
- [P01 동기화 설계](docs/p01-sync-design.ko.md): 버튼 기반 수집·정제·검증·저장 흐름과 구현 순서.
- [P01 검증 보고서](docs/p01-verification.ko.md), [필드 계약](docs/p01-field-contract.ko.md), [P01 기능 출처](docs/p01-source-map.ko.md), [P02 인계](docs/p02-handoff.ko.md).
- [설계 초안](docs/architecture-draft.ko.md): 계산·통계·최적화 원칙.
- [원본 버전 및 이식 hash](sources.lock.json), [라이선스 고지](THIRD_PARTY_NOTICES.md).

기존 C#의 스탯 계산·테이블·관련 DTO는 바이트 그대로 보존합니다. P01 수집기·정제기는 양쪽 원본의 요청 구조·매핑을 참고해 새 계약으로 작성했습니다. 현재 기본 UI는 Local Lab 화면이며 이전 upstream 테마 화면은 `/legacy/`에 보존합니다. 캐릭터를 선택하면 HP·공격력·방어력을 자동 계산합니다. 필요할 때 `단일 히트 검산`을 펼쳐 조건 입력 → `정수화 후보 비교`로 검산합니다. OL은 자동 적용되며 추가 스킬 공증은 `50, 30`처럼 개별 입력합니다. 단일 히트 도구에서는 스킬 계수·허용 조건을 직접 지정하고, 솔로 레이드 검산에서는 선택한 5인의 스킬을 실행합니다.

[P02 검증 결과·실측 안내](docs/p02-verification.ko.md) · [P02 기능별 출처](docs/p02-source-map.ko.md). 현재 고정 자료로 193명 중 160명의 스탯 입력을 계산하고, 자료가 부족한 33명은 미완료로 표시합니다. 이는 전투 효과 지원 캐릭터 수가 아닙니다.

`.reference`의 원본 checkout, `.tools`의 SDK·캐시, `artifacts`의 검증 로그, `data`의 개인 데이터는 Git에서 제외합니다. 기존 C# 기준 테스트는 별도 복사본으로 실행하며 준비·재현 방법은 검증 보고서에 있습니다. 원본의 미커밋 변경을 새 프로젝트에 일괄 반영하지 않습니다.
