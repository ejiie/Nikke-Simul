# P01 기능별 출처와 변경 내역

원본 버전은 P00의 `sources.lock.json`을 유지한다. 이 단계의 참고 원본 SHA-256은 `p01-source-manifest.json`에 기록한다. P00의 C# 바이트 복사 2개 파일은 수정하지 않았다.

| 구현 기능 | 가져온 근거 | P01 위치와 변경 |
|---|---|---|
| 로그인·세션·상세 배치 수집 | 기존 `DataPipeline/crawler/getFromBlaLink.py`의 브라우저 로그인 관측, 요청 헤더/로스터 확보, 배치 흐름 | `tools/data-pipeline/collector.py`. 직접 로그인, 고정 출력 경로 제거, 구조화된 진행/오류, DPAPI 세션 저장. `_secrets`와 기존 자동 비밀번호 입력은 가져오지 않음 |
| 세션으로 직접 HTTP 수집 | upstream `scraper/profile_fetch.py`, `worker/src/index.js`의 API 경로·공통 헤더·지역·세션 오류 처리 | 같은 collector의 collect 경로. Playwright request context로 10명씩 수집하고 전초기지·마지막 로스터 재확인. 작성자 Worker는 사용하지 않음 |
| C# 입력 필드 연결 | 기존 `DataPipeline/etl/blabla_merger.py`의 캐릭터·장비·콘솔·옵션 필드 관계 | `src/Nikke.Data/SnapshotNormalizer.cs`. C#으로 재작성. 부위/줄/ID 보존, missing/absent 구분, 필수 오류 검증 |
| OL 의미 단위·옵션 종류·소장품 매핑 | upstream `profile_fetch.py`, `site/src/blablalink.ts`, `data/base_stat_tables/equipment_skills.json` | Normalizer + GameSnapshot. 합산 출력과 가장 가까운 단계 보정은 사용하지 않음. Integer로 인코딩되는 비율 옵션을 명시적으로 구분 |
| 캐릭터 이름·소장품/옵션 단계 사전 | upstream `data/name_codes.json`, `site/public/settings.json`(고정 원본으로 생성), `equipment_skills.json` | `prepare_catalog.py` → Git 제외 GameSnapshot. 파일 hash와 버전을 함께 기록. 전투 전체 데이터 이식은 아님 |
| UI 색상·폰트·배경·포커스 스타일 | upstream `site/src/styles.css` 1~62줄 | `apps/web/src/upstream-theme.css`. 출처 주석 + 원문 부분 복사. 기존 MIT 고지 보존 |
| 계정 입력 화면 | upstream 가져오기/부위별 입력 UX 참고 | `apps/web/src/main.ts`, `model.ts`, `styles.css` 신규 작성. 원본 전투 UI 전체 이식이 아니라 동기화 전용 화면 |
| 계약·정제 완전성·보존 검사 | 신규 작성 | `Nikke.Contracts`, Normalizer ID 집합/중복/필수값/단위 검사 |
| 동기화 작업·API·SQLite·원천 보존·수동 보완 | 신규 작성 | `Nikke.Api`, `Nikke.Storage`. current transaction, revision, 취소/중복/재시작, 원천/game ID 불변 |
| 테스트·실제 원천 대조 | 신규 작성 | `Nikke.Sync.Tests`, Python tests, 웹 tests, `Nikke.SyncAudit`, `replay_legacy.py`, 격리 API/UI 검사 |

재사용한 UI 테마·upstream 기반 요청/매핑에는 [MIT 원문](../third-party/nikke-calc.LICENSE)과 [저작권 고지](../THIRD_PARTY_NOTICES.md)를 적용한다. 기존 로컬 C# 프로젝트에 대한 별도 배포 라이선스는 새로 추정하지 않는다.

CSV 파서·기존 WPF/Union Raid UI·클라우드 프록시는 이번에 이식하지 않았다. 계정 동기화용 SQLite 기반과 전투 표본의 대량 저장·통계 처리는 다른 단계다.
