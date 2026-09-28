# H-SRC — 단일 히트 공식 원천 조사

2026-09-28. Backend 기준 `d8be9d3`(기존 제품 커밋 `40078d0`)에서 수행한 **원천 조사 보고서**. 엔진 구현·실게임 수용·통합·배포 보고가 아니다.

배정 근거: [Director 지시서](C:/Users/user/orca/workspaces/Nikke-Simul/Director/docs/hit-damage-assignments-2026-09-28.ko.md), [사용자 공식·결정 전체](C:/Users/user/orca/workspaces/Nikke-Simul/Director/docs/hit-damage-client-formula.ko.md). 두 문서와 저장소 AGENTS.md·README.md를 UTF-8로 읽었다. Director 파일은 변경하지 않았다.

## 핵심 결과

- **`breakRate = 1 + PartsDamage`를 원천 대응으로 확정하면 안 된다.** `BreakDamage(96)`는 누아르의 저지 부위 공격 효과이고 `PartsDamage(112)`와 별개다. 현 엔진도 96을 `InterruptionTarget` 조건에서 `AttackDamage`에 넣는다. `breakRate`의 유력 후보는 저지 부위 보너스다. 현 B3와 수학적으로 같은 분해라는 것과 클라이언트 변수 의미가 같다는 것은 다르다.
- **`statDamageRatio = 스킬 대미지 계수`는 미확정이다.** 스킬 계수는 실제 `CharacterSkillTable.skill_value_data`와 `FunctionTable.function_value`에서 찾았다. 별도로 `MonsterStatEnhanceTable.level_statdamageratio`라는 훨씬 직접적인 이름의 필드도 존재한다. 이 값이 공통 피해 함수의 몬스터 공격자 스탯 배율인지, 사용자 공식의 변수인지, 단위가 무엇인지는 클라이언트 대입 경로가 필요하다. 니케→보스 피해에 보스 행의 값을 넣을 근거는 없다.
- **`defenceRatioRate` 후보 `MonsterData.DefenceRatioRatio`는 기존 디코더 스키마에 있다.** 그러나 조사한 기존 MonsterTable 두 벌에는 해당 필드가 없다. 적용 보스·조건·실제 값은 불명이다. 기존 `defence_ratio=10000`을 이 감소율로 쓰면 안 된다. 기본 0은 사용자 결정에 따른 중립 입력이며 관측값이 아니다.
- 블랑 `DamageReduction(42)`의 원천 값 **−3926**은 받는 대미지 증가 +39.26%와 부호가 맞는다. 따라서 **damageTaken 부분**의 `damageReductionRate = -DamageTaken` 대응은 유력하다. distribution까지 같은 항에 넣는 것은 고정 upstream의 모델 근거만 있고 클라이언트 연결은 미확인이다.

## 조사 범위와 근거 식별자

신뢰도는 **확인**(파일·키·값 또는 현 제품의 실제 연결 확인), **유력**(복수 근거가 의미 대응을 지지하나 클라이언트 대입 미확인), **추정**(이름/비교 모델에 근거한 후보), **불명**(후보를 선택할 근거 부족)으로 구분한다. 표의 “확인”은 게임의 실제 연산 전체를 독립 검증했다는 뜻이 아니다.

아래 경로를 표의 근거 ID로 사용한다. 전체 SHA-256·행 수·선택 예시·검색 범위는 [로컬 증거 JSON](../artifacts/hit-damage-source/evidence.json)에 저장했다. 원천 JSON 전체는 커밋하지 않는다.

| ID | 읽은 자료 | 고정·검증 범위 |
|---|---|---|
| S1 | `C:/Users/user/Documents/GitHub/Nikke-Dmg-Simulator/Database/raw/staticdata/mpk/FunctionTable.json` | 19,459행, SHA-256 `b4455eb80b2a61bc484a38332200e5839e8e25f48600221db5e6d9f489dded26` |
| S2 | 같은 `mpk/CharacterSkillTable.json` | 4,387행, `04435b2531e89629a104549d5525d86418be961de8c879587652afe4159794ff` |
| S3 | 같은 `mpk/CharacterTable.json` | `1ecda453c02b3f62629a3b39837bc7dfac7213b670ac5b81f28267783c6ff1e3` |
| S4 | 같은 `sd_bin_json/ConfigBattleTable_kv.json` | 139개 상수, `3df23223908b740c7bf8e66ea4f9f0871559f947c4179a45cb181650b14a41e2` |
| S5 | `C:/NIKKE/NIKKE/game/nikke_Data/StreamingAssets/sd.bin`의 ZIP 목록과 `ConfigBattleTable.json`만 | pack `9168a3b96edecd5067b32e7d15903e9c67f485a2d201ef3fde9219e3557ef3a7`; ConfigBattle 전체 KV가 S4와 일치. 테이블 version `0.0.1`은 게임 클라이언트 버전이 아님 |
| S6 | `C:/Users/user/Documents/GitHub/Nikke-Simul/data/local/runtime/30b3b0be42d2c6da1ea982304f38688762656e7ef82308e1024598252e4d7dc8/catalog.json` | 내용 SHA-256 = 디렉터리 ID, 5캐릭터·329함수·20 characterSkills. 기존 카탈로그만 읽음 |
| S7 | `C:/Users/user/Documents/GitHub/Nikke-Dmg-Simulator/Database/raw/blabla_roledata.json` | 계정 스냅샷이 아닌 공개 캐릭터 roster. 기존 P03 hash `8568963a75d971cf97489be79bf6f81829bf4e20fdccc74ed10b28159c304348` 일치. 필요한 공통 스탯/shot만 인용 |
| S8 | `C:/Users/user/Documents/GitHub/Nikke-Simul/.reference/nikke-calc/calculator/damage.py` 및 `data/parsed_nikke.json`, `collection.json` | HEAD `b4f440594d9d88840305e5a5897584549a0264dc`, 추적 diff 없음. damage.py hash `0c145eede842d01a3401cdb23d08e5b3ba8eec9f8545c7a7db915a6e5b204590` |
| S9 | 기존 `OfficialSkillEnums.cs`, `DataPipeline/crawler/memorypack_decode.py`, `Docs/VERIFICATION_LOG.md` | 모두 `C:/Users/user/Documents/GitHub/Nikke-Dmg-Simulator` 아래. 읽기만 했고 디코더를 실행/수정하지 않음. decoder hash `96a8721562826fca61a97389b7515289321dec01a1307dca123a3240b2df0811` |
| S10 | 기존 `mpk/MonsterTable.json`, `season40_probe/mpk/MonsterTable.json`, `mpk/MonsterPartsTable.json`, `mpk/StateEffectTable.json`, `decoded/ElementTable.json`, season40 FunctionTable | 2,043/2,064개 몬스터 행, 669개 parts 행. 두 MonsterTable 모두 `defence_ratio_ratio` 필드가 없음. 기존 시즌40 자료를 읽었으며 새 수집은 아님 |
| S11 | 기존 `mpk/MonsterStatEnhanceTable.json`, `decoded/MonsterStatEnhanceTable.json`, `decoded/CharacterStatTable.json`, `decoded/CharacterStatEnhanceTable.json` | monster 두 벌 각각 30,671행. 타입/값 불일치 상세는 아래 절 |
| S12 | Backend `src/Nikke.Core/Combat/HitCalculator.cs`, `src/Nikke.Data/CalculationService.cs`, `src/Nikke.Engine/Skills/SkillReplay.cs` | 현 입력·효과 연결의 읽기 전용 대조. 클라이언트 원본으로 취급하지 않음 |

Backend에는 `.reference`가 없어 **원본 저장소의 고정 reference를 읽기 전용으로 사용**했다. 원본 `game-catalog.json`도 `Moris-kr/nikke-calc@b4f440…` 출처를 확인했다. 공개 검색에서 변수명 조합에 대한 직접 설명은 찾지 못했다. 검색 불발을 “존재하지 않음”의 증거로 쓰지 않는다.

공개 1차 코드 자료는 converter 작성자의 [Monster.cs](https://github.com/SharpnelXu/nikke-mpk-json-converter/blob/c02571f68766840054b0f640a21fd9941ba35a95/NikkeMpkConverter/model/Monster.cs), [Skills.cs](https://github.com/SharpnelXu/nikke-mpk-json-converter/blob/c02571f68766840054b0f640a21fd9941ba35a95/NikkeMpkConverter/model/Skills.cs), [CharacterShotTable.cs](https://github.com/SharpnelXu/nikke-mpk-json-converter/blob/c02571f68766840054b0f640a21fd9941ba35a95/NikkeMpkConverter/model/CharacterShotTable.cs)를 커밋 고정으로 확인했다. 이 자료는 정적 필드/enum 선언이며 실제 피해 함수 구현이 아니다. 브라우징 도구의 raw fetch 실패 후 HTTPS로 같은 고정 파일을 읽어 자기 artifacts에만 보관했다. 공개 파일 5개의 hash는 증거 JSON에 있다. 게임 실행 파일·기존 dump.cs·디컴파일 도구는 열거나 실행하지 않았다.

## 항별 대응표

비율 표기 `raw / 10000`은 해당 키의 기존 정규화와 설명 값이 함께 맞는 경우에만 사용한다. `function_value_type=1(Integer)`여도 StatChargeDamage 등 효과 단위가 1/10000인 사례가 있으므로 모든 Integer를 고정 대미지로 해석하지 않는다.

| 공식 항 | 원천 후보·키·예시 | 신뢰도와 의미 한계 | 현 HitContext / 중립·일반 기본값 |
|---|---|---|---|
| `damageRatio` | S7 앨리스 `roster.5004.shot.damage=6904` → 0.6904; S2 누아르 skill ID `1271310`, type 1, `skill_value_data[0]={type:2,value:35164}` → 3.5164; S1 모더니아 `226011001`, type 75, value 305 → 0.0305 | **값 확인 / 변수 대응 유력**. 무기·스킬별 타격 계수 후보. CharacterSkill의 배열 위치 의미는 skill_type별로 다르며 일괄 첫 항 적용은 금지 | `Coefficient` 기본 1. 현재는 정규화한 타격 계수와 일반 공격 배율 증가가 이미 합쳐질 수 있음 |
| `statDamageRatio` | S11 `MonsterStatEnhanceTable.level_statdamageratio`; ID `331250`, group `331000`, lv 250, raw **250917**. 다른 후보는 S1 type 165 `NormalDamageRatioChange`, ID `710501011`, value 157(1.57%); 사용자 후보는 스킬 계수 | **필드 존재 확인 / 공식 대응 불명**. 몬스터 스탯 배율, 일반 공격 계수 보정, 스킬 계수 중 무엇인지 이름만으로 결정 불가. 250917의 배율 단위도 별도 확인 필요 | 현 입력 없음. 새 중립값 **1 유지**. `Coefficient`에 든 스킬 계수/일반 공격 증가를 다시 곱하지 않음 |
| `chargeDamageRate` | S7 shot `full_charge_damage=35000` → 3.5; S1 앨리스 `119111003`, type 11, value_type 1, value 700 → +0.07. S8 `_factor4`, collection `charge_dmg_mag_pct` | **원천·현 식 확인 / 클라이언트 항 대응 유력**. 사용자 확정 차지식과 일치; 부분 차지 보간은 이번 조사로 확정하지 않음 | FullCharge일 때 `ChargeBase*(1+ChargeMultiplierBonus)+ChargeAdd`, 비활성 1. 기본 ChargeBase 1, 증가분 0 |
| `breakRate` | S1 `BreakDamage=96`, 누아르 `127131002=2323`(SG 조건), `127131004=1936`(같은 스쿼드 조건). S6/S8 이름 `intercept_dmg_pct` | **저지 효과 의미 확인 / breakRate 대응 유력**. `PartsDamage=112`와 다른 효과. 파츠 적중 여부만으로 활성화하면 의미가 달라짐 | 전용 입력 없음. 현 런타임은 `InterruptionTarget` 시 96을 `AttackDamage`에 합침. 중립 rate 1 |
| `addDamageRate` | S1 `AddDamage=95`, `235220102=700` → +0.07; parts 112, pierce 149, dot 169, true 160, sequential 212의 조건부 증가 후보. S8 `_factor5` | **효과 값 확인 / 합산 항 유력**, 내부 각 타입의 정확한 gate와 누적 규칙은 미확인 | `1+AttackDamage+활성 PartsDamage/PierceDamage/DotDamage/SequentialDamage/TrueDamage` 후보. 중립 1, 각 증가분 0. 저지 96 중복 제외 필요 |
| `damageReductionRate` | S1 블랑 `127031004`, type 42, target 3(AllMonster), value **−3926**, 10초 → `1-(-.3926)=1.3926`. 분배 증가 후보 type 145는 아래 참조 | **부호·효과 확인 / DamageTaken 대응 유력**. 분배의 합산 위치는 **추정** | 현 `DamageTaken=+.3926`; 잠정 `-(DamageTaken+조건부 DistributionDamage)`. 중립 0. 아군 생존용 받피감은 대상이 달라 자동 적용 금지 |
| `defenceRatioRate` | S9 `MonsterData.defence_ratio_ratio:int` (`AttackRatio` 다음). S10의 기존 JSON에는 미포함 | **스키마 존재 확인 / 적용·단위·보스 값 불명** | 현 입력 없음, 사용자 결정 기본 **0**. 기존 `Defense`, `defence_ratio`와 분리 |
| `elementRate` | S4/S5 `ElementBonusDamage=1000`; S7 element, S1 `IncElementDmg=80`, 예 `400070102=848`; S8 `_factor7` | **값 확인 / 대응 유력**. 우월 판정이 먼저이며 type179 등 예외는 미확인 | 우월이면 `1+ElementBase(.1)+ElementBonus`, 아니면 1; 증가분 기본 0 |
| `criticalDamageRate` | S3/S7 `critical_damage=15000` → 1.5; S1 `StatCriticalDamage=51`, 예 `203220101=1949` → +.1949. `critical_ratio=1500`은 확률이므로 별개 | **값 확인 / 대응 유력** | 활성 `1+CritBonus`, 기본 CritBonus .5; 비활성 rate 1 |
| `coreDamageRate` | S7 `shot.core_damage_rate=20000` → 2.0; S1 `CoreShotDamageChange=87`, 예 `245010102=5033` → +.5033. S4/S5 전역 `core_damge_rate=25000`도 별도로 존재 | **무기 값 확인 / 대응 유력**. 전역 2.5로 일괄 덮어쓸 근거 없음. type88의 별도 축은 이 구 FunctionTable에 행이 없음 | 활성 `1+CoreBonus`, 일반 기본 CoreBonus 1; 비활성 1. 무기별 기본값 우선 여부는 클라이언트 확인 |
| `burstDamageRate` | S4/S5 `burst_damage_step_crash=15000`, step01/02/03=10000; S8 `_factor3`의 Full Burst +.5 | **값 확인 / 대응 유력**. 이름이 유사한 burst skill damage 증가와 풀버스트 시간 보너스를 구분 | FullBurst 활성 `1+BurstBonus(.5)`, 비활성 1 |
| `bonusRangeRate` | S4/S5 `BonusRangeRate=13000`; S3/S7 `bonusrange_min/max`(앨리스 45/100); S1 type162 `BonusRangeDamageChange`, ID `1999804=1500` | **값 확인 / 대응 유력**. type162 값은 변화분인지 교체값인지 미확인. 일반 공격·변경 무기·스킬별 적용 gate 필요 | ProperDistance 활성 `1+DistanceBonus(.3)`, 비활성 1 |

### `damageRatio`와 `statDamageRatio`를 구별해야 하는 이유

S12 `CalculationService.cs:183`는 현재 `Coefficient = basic.multiplier / 100 * (1 + NormalAttackMultiplier)`로 만든다. S8 `_factor1`도 무기/스킬 계수 선택 후 일반 공격일 때만 별도의 증가율을 곱한다. 따라서 **현 Coefficient 자체가 이미 복합 값**이다. 새 필드를 넣는다는 이유만으로 같은 증가분을 `statDamageRatio`에 또 넣으면 중복이다.

반면 S11에는 스킬 테이블과 독립된 `level_statdamageratio`가 있다. 공개 Monster.cs의 `MonsterStatEnhanceData.LevelStatDamageRatio`는 `int`, JSON명 `level_statdamageratio`, MemoryPackOrder 6이다. 공개 CharacterStat/CharacterStatEnhance에는 대응되는 damage 필드를 찾지 못했고, 기존 CharacterStatTable 64,800행의 키에도 없다. 이 차이는 **공통 함수가 몬스터 발사 대미지와 니케 발사 대미지를 모두 받으며 공격자 스탯 배율을 별도로 전달한다**는 가설과 양립한다. 아직 가설이다. 방어 대상 보스의 stat 행을 플레이어 공격 배율로 사용해서는 안 된다.

S11의 동일 ID `331250`은 `mpk`에서 `level_statdamageratio=250917`, `decoded`에서 `Level_statdamageratio=0.0`이다. `decoded`는 30,671행 모두 0.0이지만 `mpk`에는 1·10000·12000 등 여러 값이 있다. 공개 int 선언과 대조할 때 구 decoded 0.0을 신뢰할 수 없으며, 원인은 타입 해석/변환 차이 후보로만 남긴다. 이번 작업은 재디코딩하지 않았고 어느 배율을 제품에 넣지도 않았다. 두 hash는 각각 `9c61e73edcdc96fcb52af3339001005f1fc2fe8b55a95cdf68119677912eedef`, `f725eab8f924e1293b1ad792189c8fb1ec25fa3cfa21d85cfcea7f9989d32ed5`이다.

### `defenceRatioRate` 보스·조건·값 조사 결과

S9 decoder의 206–212행과 기존 VERIFICATION_LOG의 2026-08-20 절은 client `150.6.9`용 MonsterData에 `DefenceRatioRatio:int`가 추가되어 33 members가 됐다고 기록한다. **이 버전은 기존 조사 기록의 버전이며, 사용자가 전달한 공식의 클라이언트 버전과 동일하다고 확인한 것은 아니다.** 공개 converter의 이번 고정 Monster.cs에는 해당 추가 필드가 없어서 공개 스키마도 시점 차이가 있다.

S10 구 MonsterTable 2,043행, season40 MonsterTable 2,064행 모두 해당 키가 없다. 예를 들어 구 `11200101`의 `defence_ratio=10000`은 확인되지만 새 감소율 값의 대용이 아니다. S5 sd.bin은 5개 JSON 테이블만 포함하고 MonsterTable이 없어 이 누락을 보충하지 못한다. 기존 assembled raid catalog도 확인했으나 `defence_ratio_ratio` 키는 없었다. 이번 범위에서 **적용 보스: 불명 / 발동 조건: 불명 / 실값: 불명 / 단위: 불명**이다. 후보를 좁힌 성과와 값 확정 실패를 구분한다. 새 데이터팩 수집·게임 바이너리 확인은 수행하지 않았다.

## 특수 대미지·증가 효과의 위치

직접 피해를 발생시키는 효과와 이미 발생한 피해의 배율을 바꾸는 효과를 구분한다. 아래 “항”은 현재 모델 및 후보이지 클라이언트 명령어 추적 결과가 아니다.

| 종류 | 원천 증거 | 공식 항 후보 / 현 입력 / 신뢰도 |
|---|---|---|
| damageTaken | S1 type42 블랑 −3926, S12 AddEffect에서 `-f.Rate`로 +.3926 저장 | `(1-damageReductionRate)` / DamageTaken / **유력**. 공격 대상에게 적용된 효과만 소비 |
| distribution | S1 type145 `ShareDamageIncrease`, ID `150030101=2246` → +.2246; S8 `_factor6`가 split_dmg를 received_dmg와 합산 | reduction에 음수 증가분으로 합침 / DistributionDamage / **추정**. 분배 피해를 만드는 type135 등과 증가효과 145를 혼동하지 않음 |
| parts | S1 type112 `PartsDamage`, `104030101=1669` → +.1669; S8 `_factor5`의 part_dmg | addDamageRate의 조건부 가산 / PartsDamage + Parts / **유력**. `breakRate`와 동일시할 근거 없음; S4 FunctionDamageForParts=0도 산식 위치를 확정하지 않음 |
| pierce | S1 type149 `PenetrationDamage`, `204310102=800` → +.08; 관통 활성 type54 `StatPenetration`은 별도 | addDamageRate / PierceDamage + Pierce / **유력**. 관통 활성 자체와 관통 피해 증가량을 구분 |
| dot | S1 type169 `DurationDamageRatio`, `228410104=301` → +.0301; type202 DurationDamage는 별도 피해 생성 후보 | addDamageRate / DotDamage + DamageType dot / **유력**. tick별 계수·snapshot timing은 미확인 |
| sequential | S1 type212 `InstantSequentialAttackDamageRatio`, `247120106=9360` → +.9360; S8 `_factor5` | addDamageRate / SequentialDamage / **유력**. type178 FullCountDamageRatio 예 `151130102=1511301`은 value_type 1의 참조 ID 후보이므로 배율로 /10000하면 안 됨 |
| true(방어 무시) | S1 type64 `DefIgnoreDamage`는 피해 생성, type160 `DefIgnoreDamageRatio` `214225103=2117`은 증가효과 후보; S8 `_factor2`가 DEF를 0, `_factor5`가 증가율 가산 | 공방차의 defence=0 + addDamageRate의 증가분 / TrueDamage + DamageType true / **유력**. 새 defenceRatioRate까지 무시하는지는 **불명** |
| 저지 부위 | S1 96 누아르 2323/1936, S8 intercept_dmg_pct, S12 InterruptionTarget | breakRate / 현재는 AttackDamage에 임시 합침 / **유력**. 파츠 112와 별개 |

type194 `DmgReductionExcludingBreakCol`의 `2000035=8000`, type207 `StatDefNoneBreakCol`의 `2000168=36000`도 있다. 이 명칭은 저지 충돌체와 일반 방어/감소가 분기될 가능성을 뒷받침하지만, 이들을 새 `defenceRatioRate`라고 확정하거나 특정 보스에 연결할 근거는 없다.

## H-F32 잠정 대응과의 차이·후속 연결

1. **break/parts 분해 수정 후보:** 저지 전용 증가를 breakRate, parts를 addDamageRate에 남기는 해석이 원천과 더 잘 맞는다. 현재 96은 이미 AttackDamage에 포함되므로 분리할 때 그 기여를 빼지 않으면 두 번 적용된다. `HitContext`에는 별도 저지 플래그·저지 증가량이 없으므로 정확한 계약/런타임 연결은 후속 작업이다. 본 조사에서 엔진을 변경하지 않았다.
2. **statDamageRatio 1 유지:** 스킬 계수라고 확정하지 않는다. Coefficient에 합쳐진 일반 공격 증가를 별도 필드로 분리할지, 몬스터 공격자용 스탯 배율인지 먼저 확인한다. H-F32의 `damageRatio=Coefficient`는 당장 기존 입력 보존을 위한 잠정 해석이다.
3. **defenceRatioRate 0 유지:** 입력 추가는 사용자 결정대로 가능하나 카탈로그 보스 자동 채움은 불가하다. 원천 키/단위/보스 선택 및 snapshot schema/version을 확정한 뒤 Backend/API/Contracts/UI 연결 여부를 정해야 한다.
4. **damageTaken 부호는 지지, distribution은 미확정:** `-(DamageTaken+distribution)` 전체를 확인된 클라이언트 식이라고 표현하지 않는다.
5. **core 전역값 교체 금지:** ConfigBattle의 2.5와 무기별 2.0의 적용 우선순위를 확인하기 전 현 무기 값을 보존한다. 일반 공격/스킬/교체 무기 조건도 별도 유지한다.

## 사용자가 클라이언트 코드에서 확인할 구체적 질문

아래 이름은 이미 확인한 정적 필드/enum 또는 사용자가 전달한 지역변수다. 실제 클래스·메서드 이름을 임의로 만들지 않았다.

1. **공식 출처:** 게임 버전, 피해 함수의 클래스·메서드/오버로드와 호출자(니케→몬스터, 몬스터→니케)를 알려 주세요. 각 호출자가 넘기는 `damageRatio`, `statDamageRatio`의 대입 우변을 각각 확인해 주세요. `CharacterShotData.Damage`, `CharacterSkill.skill_value_data`, `FunctionValue` 중 어느 것이 어디로 가는지 필요합니다.
2. **statDamageRatio:** `MonsterStatEnhanceData.LevelStatDamageRatio` / `level_statdamageratio`가 이 변수에 들어가나요? 공격자/피격자 어느 쪽 스탯인지, 니케 공격의 기본은 1인지, `/10000` 등 단위 변환과 레벨/모드 보정이 어디서 일어나는지 확인해 주세요. 이름이 같은 필드가 무관하다면 실제 원천을 요청합니다.
3. **일반 공격 증가:** `NormalDamageRatioChange(165)` 및 NormalAttackMultiplier가 `damageRatio`에 곱해지는지, `statDamageRatio`를 바꾸는지 확인해 주세요. 스킬 계수/교체 무기/샷건 펠릿 계수와 결합하는 순서도 필요합니다. 같은 스킬 계수를 두 변수 모두에 넣는 경로인지 반드시 구별해야 합니다.
4. **defenceRatioRate:** `MonsterData.DefenceRatioRatio`가 직접 원천인가요? `DefenceRatio` 및 `LevelDefence`와 다른 값인지, 실제 적용 보스/Monster ID 하나와 raw 값, 정규화 분모, 발동·해제 조건, 본체/파츠/저지/true 대미지별 적용 여부를 확인해 주세요. 단순 DEF 감소나 type42/194를 이 항으로 옮겨도 되는지는 아직 알 수 없습니다.
5. **breakRate:** `BreakDamage(96)` 누적값이 저지 충돌체 판정일 때만 `1+값`으로 들어가나요? `PartsDamage(112)`는 addDamageRate인가요? 일반 파츠·저지 부위·둘 다 해당하는 히트 각각의 gate와 중립값을 확인해 주세요.
6. **addDamageRate:** AddDamage(95), PartsDamage(112), PenetrationDamage(149), DurationDamageRatio(169), InstantSequentialAttackDamageRatio(212), DefIgnoreDamageRatio(160)가 같은 합에 들어가는지, type별로 value_type과 raw 단위를 어떻게 처리하는지 확인해 주세요. 공격 버프와 피격 디버프의 대상을 함께 구분해야 합니다.
7. **reduction와 분배:** DamageReduction(42) raw 음수를 그대로 reduction 합에 더하나요? ShareDamageIncrease(145)는 reduction에서 빼는지, addDamageRate 또는 별도 항인지 확인해 주세요. 클램프/상한, reduction >1 및 음수 허용 여부도 필요합니다.
8. **기본 rate 우선순위:** `critical_damage`, shot `core_damage_rate`, ConfigBattle `core_damge_rate`, `burst_damage_step_crash`, `BonusRangeRate`, `ElementBonusDamage` 중 어떤 값을 사용하며 type87/88/162/179로 어떻게 보정하나요? rate 초기화와 `rate-1`의 자료형 및 비활성 1 처리도 확인해 주세요.

클라이언트 코드 추가 확인은 위 질문으로 남겼다. 이 질문에 답이 없어도 이번 H-SRC의 “확인 가능한 원천과 미확정 경계 보고”는 완료할 수 있으나, 공식 전체 대응 확정은 후속 단계다.

## 검증·재현·보존

조사 도구: [investigate_hit_sources.py](../tools/data-pipeline/investigate_hit_sources.py). allowlist의 기존 JSON/텍스트만 읽고 결과는 Backend `artifacts/hit-damage-source/evidence.json`에 쓴다. 원천 코드 실행/디코딩/HTTP 수집/계정 API 호출 기능은 없다. 공개 스키마 사본은 선택 입력이므로 없으면 해당 자료를 생략한다. 이번 공개 사본은 위 커밋 URL을 별도로 HTTPS 조회하여 확보했다.

```powershell
$env:PYTHONIOENCODING='utf-8'
python tools/data-pipeline/investigate_hit_sources.py
git diff --check
git diff d8be9d3 -- src apps
Get-FileHash package-lock.json
```

- 13개 기존 테이블 조사 완료. upstream HEAD/추적 diff 검사 통과, runtime 내용 hash 검증 통과, 설치 sd.bin ConfigBattle과 기존 KV 전체 일치.
- 조사 중 읽은 **36개 파일 재해시, 변경 0개**. 이 수치는 읽은 파일의 안정성 검사이며, 읽지 않은 계정 DB/캐시의 전수 해시 검사를 했다는 뜻이 아니다.
- 미추적 `package-lock.json` SHA-256 `2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767` 보존·커밋 제외. 기존 완료 커밋을 reset/checkout/stash로 밀어내지 않았다.
- 제품 `src/**`, UI, 엔진 테스트를 수정하지 않았다. 산술 구현이 없으므로 제품 회귀·합성 산술 fixture는 **이번 작업에서 미실행**. 기존 18개 실측의 새 공식 대조도 **미실행**, 새로운 실제 게임 관측도 **미실행**. 위 조사 성공은 실게임 피해 정확성 수용이 아니다.
- 원본 계정 DB·세션·캐시 접근/복제/초기화/편집/동기화 없음. 게임 프로세스 접근·후킹·실행 파일 디컴파일·데이터 재수집 없음. 5180/5181 서버 및 EXE 변경/실행/종료 없음. 새 Run/Dispatch/하위 워커/worker_done 없음. 원격 push 없음.
- 실제 사용자 실행 경로는 계속 `C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe`이며 바탕 화면 바로가기와 배포 설정을 변경하지 않았다. 이번 보고서의 검증 범위는 원천 조사와 파일 보존이다. 원본 통합·빌드·배포·실행 검증은 수행하지 않았다.

완료 커밋은 Director 인계 메시지에 확정 hash로 전달한다. 해당 터미널을 재조회한 뒤 커밋·보고서 절대 경로·검증 결과·위 미완료 질문을 한 번 전달하고, 무응답 재전송하지 않는다.
