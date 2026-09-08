# Nikke-Simul

Solo Raid의 대미지 시뮬레이션, 비중복 5덱 선정, 장비별 육성 효율 분석을 위한 프로젝트입니다.

**현재 P00 완료:** 원본 버전·출처 고정, C# 계산 fixture, 기준 테스트, 로컬 참조 웹 화면. 새 C# 전투 엔진과 웹 연결은 아직 구현하지 않았습니다.

## 실행

Windows PowerShell에서 저장소 루트를 작업 디렉터리로 사용합니다. Git, Node.js/npm, Python 3가 필요합니다. 검증 환경은 Node 24.16.0, npm 11.13.0, Python 3.12.14입니다.

```powershell
# 최초 설치: 고정 upstream checkout, 로컬 .NET SDK, npm/NuGet 의존성
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup.ps1

# 새 C# 코어: Release 빌드 + 테스트 + 계산 fixture + 이식 파일 hash 검증
npm test

# upstream 참조 UI 실행
npm run dev

# upstream 웹 테스트 / 배포용 파일 빌드
npm run test:web
npm run build
```

개발 화면: [로컬 계산기](http://127.0.0.1:5173/nikke-calc/). 이 화면은 고정한 nikke-calc의 Python/Pyodide 엔진을 사용합니다. 개인 스펙 fetch와 새 C# 백엔드 연결은 P01 이후 작업입니다. 로컬 실행에서는 upstream 작성자의 프로필 프록시·공유 API 설정을 비활성화합니다. Pyodide 등의 외부 런타임 리소스 로딩에는 네트워크가 필요할 수 있습니다.

.NET SDK 10.0.400은 `.tools/dotnet`에 설치하며 시스템 설치를 변경하지 않습니다. 이미 해당 SDK를 설치했다면 setup에 `-SkipSdk`를 사용할 수 있습니다. Python 경로를 자동으로 찾지 못하면 `$env:NIKKE_PYTHON`에 Python 실행 파일의 절대 경로를 지정합니다.

## 원본과 결과물

- [기능별 출처표](docs/source-map.ko.md): 실제 이식, 참조 실행, 후속 이식 후보 구분.
- [P00 검증 보고서](docs/p00-verification.ko.md): 최초 실패·재검증·skip과 재현 명령.
- [구현 계획](docs/implementation-plan.ko.md): P00~P09 순서와 완료 조건.
- [설계 초안](docs/architecture-draft.ko.md): 계산·통계·최적화 원칙.
- [원본 버전 및 이식 hash](sources.lock.json), [라이선스 고지](THIRD_PARTY_NOTICES.md).

실제 코드 이식은 기존 C#의 `OverloadProcessor`와 필요한 `OverloadOptionDto` 두 파일입니다. 신규 fixture는 계정 데이터 없이 실행됩니다. 전체 기초 스탯·차지·히트 대미지 이식은 P02에서 진행합니다.

`.reference`의 원본 checkout, `.tools`의 SDK·캐시, `artifacts`의 검증 로그, `data`의 개인 데이터는 Git에서 제외합니다. 기존 C# 기준 테스트는 별도 복사본으로 실행하며 준비·재현 방법은 검증 보고서에 있습니다. 원본의 미커밋 변경을 새 프로젝트에 일괄 반영하지 않습니다.
