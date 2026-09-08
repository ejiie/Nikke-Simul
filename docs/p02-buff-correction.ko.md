# P02 버프 처리 정정

2026-09-08. 사용자가 지적한 내용이 맞다. 초기 P02는 OL이 적용된 공격력을 스탯 원값처럼 반환했고, OL과 스킬 공증의 공통 기준을 계약에 담지 않았다. 문서에 있던 버프 규칙을 이식 경로 끝까지 확인하지 않은 구현 오류였다.

## 재조사한 원본과 오류 경로

P00 복사본에만 의존하지 않고 사용자가 지정한 `C:/Users/user/Documents/GitHub/Nikke-Dmg-Simulator`의 실제 문서와 코드를 읽었다. 조사 시점 원본의 SHA-256은 [추가 출처 기록](p02-buff-source-manifest.json)에 남긴다.

- [DESIGN.md §3.5](C:/Users/user/Documents/GitHub/Nikke-Dmg-Simulator/Docs/DESIGN.md:158): 고정 수치 합을 native로 정의한다. 159–164행은 `Final = base × (1 + Σ buff)` 및 OL·큐브/소장품 비율·런타임 스킬의 공통 버프 모델, 동일 수치의 그룹별 사사오입을 명시한다.
- [FACTS.md](C:/Users/user/Documents/GitHub/Nikke-Dmg-Simulator/Docs/FACTS.md:32), [VERIFICATION_LOG.md](C:/Users/user/Documents/GitHub/Nikke-Dmg-Simulator/Docs/VERIFICATION_LOG.md:513)에도 같은 규칙이 기록되어 있다.
- [Nikke.cs](C:/Users/user/Documents/GitHub/Nikke-Dmg-Simulator/SimulatorEngine/Nikke.Simulator.Core/Entities/Nikke.cs:212)는 HP/DEF 액세서리 비율을 먼저 적용하고 OL을 처리한다. ATK는 OL을 반영한 `FinalBaseAtk`을 278행에서 AttackContext에 넘긴다.
- [BuffAggregator.cs](C:/Users/user/Documents/GitHub/Nikke-Dmg-Simulator/SimulatorEngine/Nikke.Simulator.Engine/Buffs/BuffAggregator.cs:64)는 현재 `ctx.FinalAtk`을 스킬 공증의 기준으로 사용한다. 두 경로를 그대로 연결하면 OL 적용값에 스킬 비율을 다시 적용할 수 있다. 실제 게임의 산식이라는 근거가 아니다.
- 원본 DESIGN 166행에도 기존 두 단계 처리와 런타임 연결의 잔여 과제가 명시되어 있다. 따라서 원본의 기초 스탯 산술은 보존하되, 미완결된 버프 연결 순서까지 정답으로 복사해서는 안 된다.

초기 Nikke-Simul `CalculationService`가 이 OL 선적용을 따라 `Total.ATK`와 `HitContext.Attack`을 만들었다. 당시 런타임 스킬 공증 입력은 없었고, UI의 공격력 입력 의미도 모호했다. 기초 스탯·장비 45,360개 수치 대조는 이 연결 오류를 검사하지 않았다. 기존 보고서에서 검증 범위를 명확히 구분하지 않은 설명도 정정했다.

## 수정한 계약

```text
스탯 원값 S = 코어 적용 기초 스탯 + 장비 고정 수치 + 큐브 고정 수치 + 소장품 고정 수치
버프 목록 = OL 비율 + 액세서리 비율 효과 + 현재 유효한 스킬 비율
개념식: 공격력 = S × (1 + OL 공증 + 스킬 공증 + ...)
정수화: S + Σ동일수치그룹 round(S × (비율 × 중첩 수), AwayFromZero)
타격 공방차 = 위 공격력 − 적용 적 방어력
```

공증 목록은 **합친 뒤** 그룹화한다. 서로 다른 수치까지 하나로 뭉쳐 한 번 반올림하지 않으며, OL과 스킬을 따로 반올림한 뒤 더하지도 않는다. 공격력 증가와 B3의 공격 대미지 증가는 별개다. 차지식과 히트 정수화 후보는 유지한다.

| 변경 | 적용 위치·출처 |
|---|---|
| 고정 스탯·상시 비율 분리 | 신규 `CalculationService` adapter 수정. `NativeStats`, `PermanentBuffs` 반환. OL은 장비 부위·줄 출처를 유지 |
| 공통 버프 계산 | 신규 `StatBuffCalculator`. 기존 `OverloadProcessor` 원문을 그대로 호출하되 먼저 모든 유효 비율·스택을 합침 |
| 타격 입력·방어력 적용 | `HitContext.StatAttack`, `AttackBuffs`, `RuntimeAttackBuffs`. `HitCalculator`가 버프 적용 공격력을 구한 뒤 방어력을 차감 |
| 수치 입력 경계 | UI 퍼센트 문자열은 소수점 이동 후 binary64로 파싱. 큐브/소장품은 decimal 비율 변환 후 double 전달. `1.4%`와 저장 비율 `0.014`가 다른 그룹으로 갈리는 문제 방지 |
| 구형 입력 혼용 차단 | API `inputSchemaVersion=2`, 규칙 `p02.2`, 스탯 규칙 `native-stat-shared-buffs-v2`. 이전 `attack` 또는 버전 없는 입력 거부 |
| 화면 정리 | 기본 계산 화면은 HP·공격력·방어력 세 값. OL 적용 전 스탯임을 표시. 단일 히트 검산은 기본 접힘, 중간 표 제거 |
| 추적 정보 보존 | API/JSON에는 고정 수치 기여·상시/수동 버프·버전·후보 trace를 유지. 내보내기 schema v2 |

HP·DEF·장탄 비율도 같은 버프 목록으로 보존한다. 단일 히트 검산은 공격력 목록을 소비하며 HP·장탄 런타임, 스킬 자동 발동·만료 이벤트는 P03 범위다. 이번 스택·만료 검사는 유효 목록의 변경을 직접 재현한 것이다.

## 검증

- 원값 100, OL 20%, 스킬 50% → **170**. 180이 나오는 중복 곱셈을 탐지한다. 방어력 160에서는 계수 1 타격이 10이어야 한다.
- 원값 100, OL 1.4%, 스킬 1.4% → **103**. 두 출처를 따로 반올림하면 102가 되므로 그룹 경계를 검사한다.
- 원값 100, OL 20%, 스킬 30% × 2중첩 → 180. 반복 계산해도 180, 스킬이 만료된 목록으로 계산하면 120, 원값은 계속 100이다.
- 원값 100, OL 20%, 스킬 50%, 적 방어력 50, 공격 대미지 증가 50% → `(170 − 50) × 1.5 = 180`. 공증과 대미지 증가의 별도 적용을 검사한다.
- 원값 DEF 113, 소장품 1.4%, OL 1.4% → 116. 십진 입력 변환과 액세서리·OL 공통 그룹을 함께 검사한다.
- 저장된 193명 중 계산 가능한 SSR 160명에 대해 네 가지 공증 조합 **640건**을 독립 Python 그룹·사사오입 계산과 대조했다. 나머지 33명은 종전과 같은 자료/등급 미지원으로 표시한다.
- `npm run build`, `npm test`, `npm run test:sync` 통과. C# **66개**, Python **7개**, 웹 단위 **7개**. Release 빌드 경고·오류 0. 바이트 보존 대상 원본 hash 일치.
- 실제 API의 구형/잘못된 입력 3종 거부, UI 흐름 9개 통과. 데스크톱 1440px·모바일 390px의 최종 스탯 화면을 직접 확인했다.
- 과거 단일 히트 18점과 합성 경계 30점 대조 유지. 실측 잔차 범위는 종전과 같다(항별 내림 0~52, 최종 반올림 0~57, 단계별 내림 0~52). 이 과거 입력은 공격력을 주어진 상수로 고정한 정수화 비교이며, 새 버프 적용이 실게임과 맞는다는 증거로 사용하지 않는다.

실제 계정 계산·UI 스크린샷·내보내기 증거는 Git 제외 `artifacts/p02-buff-fix/`에 저장했다. 초기 `artifacts/p02/`는 보존한다. 새 실게임 대미지 관측을 수행하거나 히트 정수화를 확정한 작업은 아니다.
