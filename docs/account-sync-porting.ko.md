# 계정 가져오기·동기화 이식 안내

작성: 2026-09-18. 목적: 현재 소스를 비공개 GitHub 저장소로 보존하고, 다른 프로젝트에서 계정 연결·가져오기·갱신 기능을 이식할 때 사용할 진입점을 제공한다. **이번 작업은 업로드·문서화이며 독립 라이브러리 추출이나 대상 프로젝트 이식 완료가 아니다.**

## 저장소와 브랜치

대상 저장소: `ejiie/Nikke-Simul` (비공개). 기본 브랜치는 `Director`다. 현재 각 브랜치의 작업 상태를 보존하며 이번 업로드를 위해 임의로 병합하지 않는다.

| 브랜치 | 업로드 기준 상태 |
|---|---|
| `Director` | 인수인계·작업 결정 및 이 문서. 계정 가져오기·동기화 이식의 출발점 |
| `main` | 원본 사용자 실행본에 대응하는 기존 기준 `a5ccba6` |
| `Backend` | CPU 튜닝 후속 제품·보고서 `d8be9d3` |
| `검수` | 제품 통합과 독립 검수·부하 측정 기록 `44cbe5d`. 1만 회 본측정 완료를 의미하지 않음 |
| `UI` | 별도 통계 UI 구현 `abcd5b5` |
| `시뮬레이션-엔진-담당` | CPU summary 구현·보고서 `87099e1` |
| `덱-육성-최적화-및-통계-담당` | 통계·OL 구현 및 signed 옵션 처리 `81be5d0` |

브랜치 이름이나 최신 커밋 시각만으로 제품 통합·배포 완료를 추정하지 않는다. 이후 각 브랜치가 진행되면 위 표는 업로드 시점 기록으로 취급한다. 원본 실행 경로는 계속 `C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe`다. GitHub 업로드는 해당 EXE·UI·서버의 갱신 작업이 아니다.

## 이식할 핵심 경로

현재 흐름: UI → 로컬 C# API → 동기화 작업 관리자 → Python 수집기 → 원천 응답 정제·검증 → SQLite snapshot/current 저장 → UI 조회.

| 위치 | 역할·이식 경계 |
|---|---|
| `src/Nikke.Api/Program.cs` | 계정 연결·재로그인·서버 선택·동기화·취소·snapshot 조회 라우트, DI, 로컬 접근 보호. 전투·통계 라우트까지 전부 복사할 필요는 없음 |
| `src/Nikke.Api/SyncCoordinator.cs` | 연결/작업 상태, 중복 요청, 시간 제한·취소, 정제·저장, 실패 시 기존 정상 상태 보존 |
| `src/Nikke.Api/CollectorProcess.cs` | Python subprocess 호출, JSONL 진행/오류, 취소 시 자식 프로세스 정리. 인증 메타데이터가 섞일 수 있는 stderr를 UI에 직접 노출하지 않음 |
| `tools/data-pipeline/collector.py` | Playwright 로그인, 서버/계정 선택 후보 수집, 인증된 계정의 원천 스펙 수집, 세션 암호화 |
| `tools/data-pipeline/profile_avatar_assets.py` | 수집기의 선택적 프로필 이미지 처리 의존성 |
| `src/Nikke.Contracts/Models.cs`, `ConnectionFailureNotice.cs` | 계정 연결·작업·원천·게임 카탈로그·snapshot·실패 알림 계약과 직렬화 |
| `src/Nikke.Data/SnapshotNormalizer.cs` | 원천 ID·옵션·단위·완전성 검증 및 공통 snapshot 변환 |
| `src/Nikke.Storage/SnapshotStore.cs` | SQLite, 원천 파일, snapshot/current 포인터, 작업 이력 및 중단 복구 |
| `apps/desktop-ui/app.js`, `local-lab-account.js` | 현재 계정 가져오기·동기화 UI 진입점. 대상 프로젝트 UI에는 API adapter/상태 흐름을 맞춰 이식 |
| `apps/web` | 기존 웹 UI와 관련 테스트. 현재 desktop UI와 구분 |

현재 프로젝트 참조는 순수 동기화 라이브러리로 완전히 분리돼 있지 않다. 예를 들어 `Nikke.Data.csproj`는 Contracts뿐 아니라 Core·Engine도 참조한다. 먼저 위 동기화 경로와 계약만 추출할지, 현 백엔드를 그대로 활용할지 결정해야 한다. `SyncCoordinator`의 Presentation 연계도 이미지 기능을 함께 이식할지에 따라 검토한다.

## 실행 의존성과 안전 경계

- C#은 .NET 10, 저장은 Microsoft.Data.Sqlite이며 버전은 각 `csproj`·`packages.lock.json`을 따른다. Python 의존성은 `tools/data-pipeline/requirements.txt`의 Playwright다. 브라우저 런타임도 별도로 준비해야 한다.
- 수집기의 세션 암호화는 **Windows DPAPI**에 의존한다. 다른 OS·다른 사용자 계정으로 이식할 때 암호화·비밀 저장소 adapter를 새로 검토한다. 기존 세션 파일을 복사하는 방식으로 로그인 이식을 대신하지 않는다.
- `NIKKE_PROJECT_ROOT`, `NIKKE_DATA_ROOT`, `NIKKE_PYTHON`, `NIKKE_PORT`, `NIKKE_GAME_CATALOG`를 대상 환경에 맞춘다. 특히 Director의 기본 게임 카탈로그 경로는 projectRoot 아래이므로, 외부 dataRoot를 사용하는 대상에서는 카탈로그 경로까지 명시적으로 확인한다.
- 정제에는 버전 고정 게임 카탈로그가 필요하다. `tools/data-pipeline/prepare_catalog.py`, `scripts/sync.ps1`, `sources.lock.json`을 함께 참조한다. 현재 전체 준비 스크립트는 계산 자료 준비까지 포함하므로 최소 동기화 전용 설치기로 오인하지 않는다.
- API는 loopback/Host/Origin 검사와 쓰기 요청의 `X-Nikke-Token` 검사를 사용한다. 이 로컬 앱 보안 모델을 그대로 인터넷 공개 서버의 인증으로 사용하지 않는다.
- 실제 계정 DB·세션·인증 쿠키·수집 원천·캐시·이미지는 업로드 대상이 아니다. 새 프로젝트에서는 별도 데이터 루트와 새 로그인으로 연결한다. 원본 계정에 대한 검증 목적의 편집·재동기화는 하지 않는다.
- `THIRD_PARTY_NOTICES.md`, `third-party/`의 원문 라이선스와 출처 기록을 보존한다. 전체 프로젝트에 임의로 새 오픈소스 라이선스를 부여하지 않는다.

## API와 검증 출발점

- 최초 연결: `POST /api/connections` → 상태 조회 → 복수 서버이면 `PATCH /api/connections/{id}`. 선택 후 최초 동기화가 시작된다.
- 갱신: `POST /api/sync-jobs` → `GET /api/sync-jobs/{id}`. 취소는 `POST /api/sync-jobs/{id}/cancel`.
- 재인증: `POST /api/connections/{id}/reauth`.
- 현재 스펙: `GET /api/accounts/{id}/snapshot`; 과거 스펙: `GET /api/snapshots/{id}`.
- 회귀 진입점: `tests/Nikke.Sync.Tests`, `tools/data-pipeline/tests/test_collector.py`, `tools/data-pipeline/tests/make_fixture.py`. `NIKKE_TEST_FIXTURE`는 합성 입력 기반 검증용이며 실제 로그인 성공을 증명하지 않는다.
- 이식 후에는 로그인/서버 선택, 재인증, 중복 실행, 취소·실패 시 current 보존, 누락·충돌 거부, 재시작 복구를 우선 확인한다. 실제 계정 로그인 시험과 합성 회귀 결과를 구분해 기록한다.

상세 계약·기존 검증 범위: [동기화 설계](p01-sync-design.ko.md), [필드 계약](p01-field-contract.ko.md), [검증 보고서](p01-verification.ko.md), [구현 출처](p01-source-map.ko.md).

## 업로드 제외와 점검 범위

추적된 소스·문서·합성 테스트 및 브랜치 이력만 업로드한다. Git 제외인 `data/`, `artifacts/`, `.reference/`, `.tools/`, 빌드 산출물과 미추적 루트 `package-lock.json`은 포함하지 않는다. 업로드 전 전체 대상 브랜치의 이력에 대해 개인 데이터 경로와 대표적인 토큰·개인키·인증 문자열 패턴을 확인한다. 패턴 점검은 모든 비밀정보 부재의 완전한 보증이 아니며, 계정 원천 데이터를 새로 수집하거나 내용을 공개하는 검사는 하지 않는다.
