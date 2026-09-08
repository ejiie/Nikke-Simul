# P00 기능별 출처와 이식 범위

기준일: 2026-09-08. **P00은 개발 기반 구축 단계이며, 기존 두 전투 엔진을 합친 단계가 아니다.**

## 원본 고정

| 원본 | 고정 기준 | 보존 방식 |
|---|---|---|
| Moris-kr/nikke-calc | `b4f440594d9d88840305e5a5897584549a0264dc` | `.reference/nikke-calc` checkout. 실행 전 HEAD와 추적 파일 변경 검사. MIT 원문 보존 |
| 로컬 Nikke-Dmg-Simulator | HEAD `c10395cc6c46caaea2c58c13d400796549a7eb17` + 선택 파일별 SHA-256 | 작업 트리가 수정 중이므로 HEAD만으로 동일성을 주장하지 않는다. C# 관련 63개 파일 hash를 기록하고 별도 복사본에서 기준 테스트 |

기계 판독 기록: [sources.lock.json](../sources.lock.json), [C# 원본 63개](legacy-source-manifest.json), [DataPipeline 후보](legacy-pipeline-candidates.json). DataPipeline 후보는 hash만 기록했고 복사·실행하지 않았다. 원본 저장소·개인 데이터는 Git에 포함하지 않는다.

## 이번에 실제 사용한 기능

| 기능 | 출처 | 새 프로젝트에서의 위치·상태 |
|---|---|---|
| OL 값 그룹별 정수화, 기본 스탯 보정, 정수 시간 감소, 정수 옵션 합산 | 기존 C# `SimulatorEngine/Nikke.Simulator.Core/Stats/OverloadProcessor.cs` | `src/Nikke.Core/Stats/OverloadProcessor.cs`에 **바이트 그대로 이식** |
| 위 계산에 필요한 옵션 DTO | 기존 C# `SimulatorEngine/Nikke.Simulator.Core/Data/Dto/OverloadOptionDto.cs` | `src/Nikke.Core/Data/Dto/OverloadOptionDto.cs`에 **바이트 그대로 이식** |
| 캐릭터·덱 입력, 타임라인 등 기존 웹 화면 | nikke-calc `site/` | `.reference/nikke-calc/site`에서 **원본 참조 실행**. `apps/web`에는 안내만 있으며 UI 이식·API 교체 전 |
| 웹에서 실행되는 기존 대미지·전투 계산 | nikke-calc `calculator/`, `site/pybridge/`, 런타임 생성 스크립트 | 원본 Python/Pyodide 엔진 그대로. 새 프로젝트의 확정 계산식 검증을 통과한 엔진이라는 의미는 아님 |
| 기존 C# 엔진 기준 테스트 | 기존 `SimulatorEngine/Nikke.Simulator.Tests` 및 Core/Engine | `.reference/legacy-simulator`의 원본 복사본에서 .NET 8로 실행. 제품 엔진으로 이식하지 않음 |
| 새 솔루션, 설치·검증·웹 실행 스크립트, hash 검사 | 신규 작성 | .NET 10 기반 solution, `scripts/`, `sources.lock.json` |
| 작은 C# 계산 실행 예제 및 8개 검증 사례 | 신규 작성 | `tools/Nikke.Smoke`, `tests/Nikke.Core.Tests`. OL 정수화 차이를 구분하는 합성 입력 사용 |

두 C# 파일은 원본 namespace도 유지한다. Core의 직접 의존성은 .NET 표준 라이브러리와 해당 DTO이며, 새 테스트는 xUnit/Test SDK를 사용한다. smoke executable과 테스트만 Core를 참조한다. 웹과 C# 사이의 호출 연결은 아직 없다.

## 후속 단계의 이식 후보와 의존 관계

아래는 **가져올 계획**이며 P00 구현 완료 항목에 포함하지 않는다. C# 경로는 기존 `SimulatorEngine/`, 웹·Python 경로는 nikke-calc 기준이다.

| 기능 | 우선 채택·참고 대상 | 의존 관계 / 이식 판단 | 단계 |
|---|---|---|---|
| 스펙 입력·fetch | `site/src/blablalink.ts`, `csv-import.ts`, `scraper/profile_fetch.py`; 기존 `DataPipeline/etl/blabla_merger.py`, `crawler/getFromBlaLinkRoledata.py` | 계정 입력 → 공통 snapshot adapter. 장비 4부위·줄·잠금 보존을 확인하고 기존 평탄화 출력 그대로 채택하지 않음. 전체 crawler/LLM 의존성 일괄 도입 안 함 | P01 |
| 기초 스탯 | C# `Nikke.Simulator.Core/Stats/StatCalculator.cs`, `StatTable.cs` 및 관련 DTO·Entities·장비/큐브/소장품 테이블 | 사용자 실게임 검증을 채택 기준으로 삼음. 기존 계산 순서·정수화와 테이블 단위를 함께 이식 | P02 |
| 히트 대미지·차지 | C# `Nikke.Simulator.Core/Combat/DamageCalculator.cs` + Python `calculator/damage.py` 대조 | Stat 계산 결과 → 히트 context. 차지는 확정식으로 수정. 히트 정수화 후보는 실측 판정 전 병행 비교 | P02 |
| 사격·장전·차지 | C# `Nikke.Simulator.Engine/FiringModel.cs`, Core `Stats/WeaponProfile.cs`; Python `calculator/timeline.py` | Engine → Core. 무기 시간·발사·탄약 상태와 조작 정책을 분리 | P03 |
| 스킬 effect 처리 | C# Engine `Skills/SkillChainLoader.cs`, `SkillTranslator.cs`, `SkillRuntime.cs`; Python `calculator/buff_manager.py` | 원천 skill chain → 명시적 effect → 실행 상태. 미지원 effect는 지원표에 노출; 조용한 무시를 제품 계약으로 계승하지 않음 | P03 |
| 팀 게이지·버스트 사이클 | 양쪽 구현·테스트를 참고해 팀 상태 전이를 신규 완성 | 게이지 이벤트·쿨다운·단계·재진입·풀버스트를 실제로 연결. UI의 버스트 순서 설정만으로 완료 처리하지 않음 | P04 |
| Solo Raid 보스 | C# Engine `Targets/BossTarget.cs`, `SoloRaidBossTable.cs`; 기존 `DataPipeline/crawler/staticdata_solo_raid.py` | 보스 원천 데이터·시간 구간·파츠·기믹 → Scenario. 정적 표적만으로 실전 추천하지 않음 | P05 |
| 스킬·보스 원천 테이블 | 기존 `DataPipeline/crawler/staticdata_skill_chains.py`, `staticdata_snapshot_manifest.py` | binary decoder 등 동반 의존성 별도 검토. 원천 snapshot 버전 고정 후 가져옴 | P01~P05 |
| 구성원·effect별 결과 | C# Engine `Metrics/MetricsCollector.cs`, `IMetricsSink.cs`와 upstream 결과 구조 참고 | 공통 RunResult/EffectResult 계약으로 새 adapter 작성. 총합 보존과 원인별 추적 검증 | P03~P06 |
| 저장·반복 실행·분포·retry | 신규 구현 | SQLite, CPU worker, seed/snapshot/engine version, 신뢰구간·꼬리 확률 추정 | P06 |
| 비중복 5덱 및 장비별 OL 육성 추천 | 신규 구현 | 검증된 Solo Raid 표본·보유 캐릭터·시도 비용/확률에 의존 | P07~P08 |
| Union Raid·GPU | 후순위 | 기존 Union Raid UI는 참고 후보. GPU 채택은 CPU 병목 측정 후 결정 | P09 |

기존 WPF 화면은 기준 소스 목록에 보존했지만 웹 제품 UI로 채택하지 않았고 P00에서 빌드하지 않았다. 기존 Union Raid UI, 계정 인증, 원천 수집 작업도 실행하지 않았다.

## 유지하는 계산 결정

- 차지: `기본 × (1 + 배율 증가분 합) + 가산 합`. 원본의 과거 식은 수정 없이 제품 기준으로 채택하지 않는다.
- 기초 스탯: C# 계산을 기준으로 이식한다. 이번 OL fixture 통과를 전체 기초 스탯 이식 완료나 실게임 재검증으로 확대 해석하지 않는다.
- 히트 정수화: 미확정. 두 원본 테스트가 각각 통과하는 사실만으로 정답을 판정하지 않는다.
- 버스트: 실제 팀 게이지와 사이클 완성이 완료 조건이다.

라이선스·저작권 보존은 [고지 문서](../THIRD_PARTY_NOTICES.md)를 따른다.
