# P02 기능별 출처

초기 이식의 정확한 원본 경로와 SHA-256은 `p02-source-manifest.json`에 기록한다. 버프 수정 때 실제 원본의 문서·연결 코드를 재조사한 기록은 `p02-buff-source-manifest.json` 및 [정정 기록](p02-buff-correction.ko.md)에 별도로 남긴다. 원본 프로젝트는 수정하지 않았다.

| 기능 | 출처 | 적용 위치·변경 |
|---|---|---|
| 레벨·호감도·연구실·돌파·코어·장비 계산 | 기존 C# `StatCalculator.cs`, `StatTable.cs` | `src/Nikke.Core/Stats/`에 바이트 그대로 복사. 정상 입력 연산 보존, 외부 Data adapter에서 누락을 차단 |
| 계산에 필요한 DTO | 기존 `RootDto.cs`, `CubeStatDto.cs`, `EffectType.cs` | 기존 namespace와 바이트 보존. P01 저장 계약은 별도로 유지 |
| 버프 증가분 계산 | P00에 가져온 `OverloadProcessor.cs` | 원문 유지. 새 `StatBuffCalculator`가 OL·상시 효과·런타임 스킬을 합친 후 한 번 호출 |
| 스탯 고정 수치 조립 | 기존 `Entities/Nikke.cs`, `Docs/DESIGN.md` §3.5 | `CalculationService.cs` 신규 adapter. 기본값 강제 주입 제거. OL과 비율 효과는 nativeStats에 포함하지 않고 permanentBuffs로 전달 |
| 상시·런타임 공증의 동일 기준 합산 | 사용자 지시, 기존 `Docs/DESIGN.md:158–166`, `Docs/FACTS.md`, `Docs/VERIFICATION_LOG.md:513` | 문서의 버프 계약 채택. 기존 Nikke→BuffAggregator의 두 단계 적용 경로는 재사용하지 않음. 목록 합산·출처·스택·입력 계약 v2는 신규 작성 |
| 등급별 소장품·애장품 입력 | upstream `collection.json`, `profile_fetch.py` | 원천 등급+0-based 레벨 매핑. SSR 기본값은 SR15. 스킬 교체 자동화 제외 |
| 역할·무기·평타 계수·큐브·장비 표 | P00 고정 legacy processed 자료 | 해시를 검증한 로컬 calculation 데이터셋. 평타 percent-number /100은 입력 경계 한 번만 수행 |
| 캐릭터 등급 확인 | upstream `name_codes.json`, `parsed_nikke.json` | SSR용 C# 표를 R/SR에 조용히 적용하는 것을 차단 |
| 히트 구조·항별 내림 후보 | 기존 `Combat/DamageCalculator.cs` | 신규 `HitCalculator.cs`. 차지식은 사용자 확정식으로 수정. 입력 검증, 효과 조건·항별 trace·후보 비교 추가 |
| 최종 반올림 후보·차지식 대조 | upstream `calculator/damage.py` | C# 비교 정책 신규 작성. Python 원본은 검산 도구에서만 실행. cheats 경로 사용 안 함 |
| 과거 실측 18점 | 기존 `DamageFormulaGoldenTests.cs` | `audit_p02.py`에서 관측값을 대조. 기존 상대 허용오차 테스트를 새 실게임 정확도 보증으로 사용하지 않음 |
| 기초 스탯 원본 대조 | P00 빌드 원본 `Nikke.Simulator.Core.dll` | 신규 `Nikke.CalculationAudit`. 별도 어셈블리로 동일 입력 15,120사례 대조 |
| 검산 API·화면·실측 입력·기록 내보내기·검사 | 신규 작성 | `Nikke.Api`, `apps/web/src/calculation.*`, C#/Python 검사 |

upstream MIT 고지는 `THIRD_PARTY_NOTICES.md` 및 기존 MIT 원문을 유지한다. 원본 C#의 과거 차지식, 미확인 큐브 15레벨 fallback, 소장품 등급을 잃는 연결, 원본 전투 엔진 전체는 이번에 채택하지 않았다. 효과 런타임은 P03, 실제 팀 버스트는 P04에서 구현한다.
