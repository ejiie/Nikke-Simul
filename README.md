# Nikke-Simul

Solo Raid의 대미지 시뮬레이션, 비중복 5덱 선정, 장비별 육성 효율 분석을 위한 프로젝트입니다.

**P03 진행 중:** 리타·블랑·누아르·앨리스·모더니아의 공식 스킬 그래프와 평타 시간축 검산 API를 연결했습니다. [진행 상황·출처](docs/p03-progress.ko.md) · [틱 대미지 측정 조건](docs/p03-measurement-guide.ko.md). 현재 시간축 실행은 평타 기준 모델이며 캐릭터 스킬 자동 실행과 실제 버스트 사이클은 후속 작업입니다.

**현재 P02 단일 히트 검산 구현 완료:** P01 계정 동기화에 최종 스탯 표시·확정 차지식·정수화 후보 비교·실측 입력·검산 JSON 저장을 연결했습니다. OL과 스킬 공증은 버프 적용 전 스탯을 기준으로 함께 계산합니다. [버프 처리 정정·검증](docs/p02-buff-correction.ko.md). 히트 정수화는 미확정이며 스킬 시간축·팀 전투는 P03 이후입니다.

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

# 실제 계정 동기화 UI/API 실행
npm run dev

# P01 정제·저장·수집기·웹 테스트
npm run test:sync
# P01 웹 테스트만
npm run test:web

# P00 원본 Python 전투 계산기 (별도 참조)
npm run dev:reference
```

개발 화면: [내 스펙 동기화](http://127.0.0.1:5180/). `계정 연결` → 열린 브라우저에서 로그인 → 필요 시 서버 선택 → 첫 동기화를 진행합니다. 이후 `내 스펙 동기화` 버튼으로 갱신합니다. 로그인·수집에는 네트워크가 필요합니다. Microsoft Edge 또는 Playwright Chromium이 필요하며, 최초 경로는 Edge를 우선 사용합니다.

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

기존 C#의 스탯 계산·테이블·관련 DTO는 바이트 그대로 보존합니다. P01 수집기·정제기는 양쪽 원본의 요청 구조·매핑을 참고해 새 계약으로 작성했고, UI는 upstream 테마 일부를 재사용했습니다. 캐릭터 선택 후 `스탯 계산`을 누르면 HP·공격력·방어력을 보여줍니다. 필요할 때 `단일 히트 검산`을 펼쳐 조건 입력 → `정수화 후보 비교`로 검산합니다. OL은 자동 적용되며 추가 스킬 공증은 `50, 30`처럼 개별 입력합니다. 스킬 계수·허용 조건은 직접 지정하며 캐릭터 스킬을 자동 적용하지 않습니다.

[P02 검증 결과·실측 안내](docs/p02-verification.ko.md) · [P02 기능별 출처](docs/p02-source-map.ko.md). 현재 고정 자료로 193명 중 160명의 스탯 입력을 계산하고, 자료가 부족한 33명은 미완료로 표시합니다. 이는 전투 효과 지원 캐릭터 수가 아닙니다.

`.reference`의 원본 checkout, `.tools`의 SDK·캐시, `artifacts`의 검증 로그, `data`의 개인 데이터는 Git에서 제외합니다. 기존 C# 기준 테스트는 별도 복사본으로 실행하며 준비·재현 방법은 검증 보고서에 있습니다. 원본의 미커밋 변경을 새 프로젝트에 일괄 반영하지 않습니다.
