# H-F32 — 공격력 int64 / client_f32 단일 히트

2026-09-28. **엔진/Core 독립 구현·합성 검증 완료, 원천 항 대응은 잠정, 실게임 수용·통합·배포 미완료.**

## 기준·경계

Director의 `hit-damage-assignments-2026-09-28.ko.md`, 연결된 `hit-damage-client-formula.ko.md` 전체 및 P02 정정/검증 기록을 UTF-8로 읽었다. 출발 HEAD `87099e1`과 앞선 `0d23366`/`7bd2aef`를 보존했으며 브랜치 병합·reset·checkout·stash를 하지 않았다. H-SRC 원천 조사를 대신하거나 결과를 추정해 확정하지 않았다.

수정은 본인 Core/Engine, Core/Engine 전용 테스트, 이 보고서뿐이다. 기존 untracked `package-lock.json` 보존·커밋 제외(SHA256 `2EF4178AA07DDD9AC2E4D47422038D02D8ADAADFB15586CEE6A2F1995253C767`). 계정 DB·세션·캐시·설치 게임 파일·게임 프로세스·원본 5180/5181·EXE·바로가기 및 다른 worktree를 수정하지 않았다. 새 worker/Run/Dispatch/worker_done·원격 push·배포 없음.

## 공격력 조립 및 입력 제한

`OverloadProcessor.CalculateFinalBaseStat(long, IReadOnlyDictionary<long,long>, long)`에 공격력용 정수 경로를 추가했다. dictionary key는 원천 **rate/10000의 분자**, value는 동일 비율 전체 중첩 수다. `native * rawRate * count`를 checked long으로 곱하고 몫·나머지로 사사오입한다. `numerator ± 5000` 대신 나머지 비교를 사용하므로 반올림 보정 자체가 상한에서 넘치지 않는다. 그룹별 delta를 native에 합산하고 마지막에 고정량을 더한다. 중간 곱, 그룹 수 합산, delta/총합/고정량 합산은 checked다. 중간값이 long을 넘으면 최종 나눗셈 결과가 작더라도 OverflowException으로 거부한다. 몰래 더 넓은/실수 산술로 우회하지 않는다.

`StatBuffCalculator.ApplyAttack(long, groups)`는 OL/상시/런타임 목록을 합쳐 동일 raw 비율을 그룹화한다. `AddAttackFlat(long, buffs)`는 그룹 적용 후 고정량을 checked 합산한다. 기존 `Apply(double)`/`AddFlat(double)`와 double overload는 **과거 피해 후보 및 HP·DEF·장탄**의 비교 경로로 남겼다. 장탄까지 공용 함수를 교체하면 HP·DEF·최대 장탄/탄약 보충·재장전 회귀 범위가 확대되므로 이번에는 공격력만 전환했다. 장탄 long 전환은 후속 결정 대상이다. `ReduceTimeCs` 및 엔진 차지 1/100초·프레임 순서는 변경하지 않았다.

`StatRateBuff.FromRaw(source, rawRate10000, stacks)`/`RawRate10000`로 원천 분자를 보존한다. 런타임 공격력 스킬의 `FunctionValue`는 double을 경유해 복원하지 않는다. 기존 double 비율만 있는 입력은 raw 후보를 얻은 뒤 `(double)((decimal)raw/10000) == Rate`를 **정확 비교**한다. 0.145/0.014 등 정규화된 1/10000 값은 허용하고, 0.01401·0.014의 다음 binary64 값·raw/Rate 불일치는 명시적 ArgumentException이다. 더 정밀한 값을 반올림/절삭해 채택하지 않는다. 더 높은 원천 정밀도가 확인되면 명시적 스케일 확장이 필요하다.

기존 `HitContext.StatAttack`/`Defense`/`StatFlatBuff.Amount`의 double 필드를 API 소유 영역까지 일괄 변경하지 않았다. client 진입에서 정수성·유한성을 검사해 long으로 옮기며 소수 native/DEF/고정량은 거부한다. binary64만으로 전달되는 정수는 |값|≤2^53−1을 요구하고, HitContext의 기존 수치 입력 한도 1e12도 유지한다. 클라이언트의 native 스탯 소수 처리 방식은 확인되지 않았으므로 임의 사사오입 규칙을 넣지 않았다.

`StatFlatBuff.FromInteger`/`ExactAmount` 및 효과 상태 `AttackGrant`는 시전자 원값 기준 고정 부여와 중첩 곱을 long으로 유지한다. 대상 선정 시 유효 공격력 정렬도 client 정책에서는 long을 사용한다. trace의 기존 double `Value`/`CalculationTerm`은 표시·호환용이며 long 전체 범위를 무손실로 나타내는 계약이 아니다. 미래 큰 값 fixture는 아래 typed long 진입점과 반환 필드를 사용해야 한다.

## float32 산식과 잠정 대응

`HitCalculator.CalculateClient(HitContext)`가 long 공격력을 조립하고, `ClientFloatDamage.Calculate(long attack, long defence, ClientDamageRates)`로 전달한다. true 피해는 defence=0. **checked long 공방차 `attack - defence`를 먼저 계산한 직후 float32로 변환**한다. 공격력·방어력을 각각 먼저 float로 바꾸지 않는다.

이후 base의 damageRatio→statDamageRatio→chargeDamageRate 곱, B의 crit→core→burst→range 누적, extra의 합·차, 감소/속성 계수 및 마지막 곱의 **각 연산 결과를 float에 저장**한다. 중간 floor가 없고 마지막은 MathF.Round(AwayFromZero) → max(1) → checked long이다. float 입력·중간값의 NaN/Inf를 거부한다. float로 표현한 long.MaxValue가 2^63으로 올라가는 경계를 고려해 최종 값 ≥2^63을 OverflowException으로 거부한다. 2^24 이상의 정수 해상도 저하는 허용한다.

| 공식 항 | 현재 client 입력 연결 | 상태 |
|---|---|---|
| damageRatio | Coefficient | 지시서의 잠정 대응 |
| statDamageRatio | 새 StatDamageRatio, 기본 1 | 원천 불명, 스킬 계수 추정 미채택 |
| chargeDamageRate | FullCharge 때 ChargeBase × (1 + ChargeMultiplierBonus) + ChargeAdd, 아니면 1 | 모든 연산 float |
| crit/core/burst/range rate | 활성일 때 1 + 해당 Bonus, 비활성 1 | 순서 고정, 각 덧셈/차 float |
| addDamageRate | 1 + AttackDamage + 활성 PierceDamage + 해당 dot/sequential/true 보너스 | parts 제외, 잠정 |
| breakRate | parts 적중 때 1 + PartsDamage, 아니면 1 | 잠정 |
| damageReductionRate | −(DamageTaken + 해당 distribution 보너스) | 잠정 |
| defenceRatioRate | 새 DefenceRatioRate, 기본 0 | 최근 기믹 입력, 원천/조건 미확정 |
| elementRate | 우월 때 1 + ElementBase + ElementBonus, 아니면 1 | 잠정 |

신규 입력은 내부 HitContext의 `StatDamageRatio`, **`DefenceRatioRate`**다. 기존 적 방어력 조건 필드는 미국식 철자 `enemyDefense` 그대로다. 새 필드의 직렬화 이름은 통상 `statDamageRatio`/`defenceRatioRate`이며 외부 wire DTO 연결은 이번에 하지 않았다.

## 기본 실행·버전·비교 후보

- HitCalculator 기본 정책 및 SkillReplayConditions 기본 RoundingPolicy=`client_f32`.
- SkillReplay, PreparedSkillReplay, 선택 피해 로그는 client 경로 사용. 명시적으로 선택한 과거 정책은 비교용으로 존중한다. 기존 저장 입력의 명시적 legacy를 몰래 바꾸지 않는다.
- WeaponReplay는 기존처럼 다중 정책 비교이며 client 후보를 추가하고 결과 사전의 첫 정책으로 둔다.
- `HitCalculator.Compare`는 과거 3개 순서를 보존하고 client를 네 번째로 추가한다. 과거 후보는 역사적 double 공격력 조립/산술을 보존하며 신규 두 배율을 소비하지 않는다. 신규 항이 비중립인 입력에서 과거 후보를 동일 공식의 정밀도만 다른 결과로 해석하면 안 된다.
- `Evaluate(context, policy)`는 선택 정책의 audit만 만든다. client 로그가 과거 후보의 9e15 정밀도 제한 때문에 실패하지 않게 했다. `Compare(..., includeClient:false)`는 소수 native/flat 등 과거 입력 검증에 사용할 명시적 비교 진입점이다. Compare의 공통 EffectiveAttack은 client 기준이며 각 과거 후보의 effectiveAttack term은 자체 기준이다.

| 항목 | 신규 값 |
|---|---|
| HitCalculator.Version / InputSchemaVersion | p02.4-client-f32 / **3** |
| StatBuffCalculator.Version | native-stat-shared-buffs-v3-attack-i64 |
| SkillReplay.Version | p03.skills.3-client-f32 |
| TeamBurstController.Version | p04.team.3-client-f32 |
| WeaponReplay.Version | p03.weapon-reference.2-client-f32 |
| PreparedSkillReplay.Version | cpu-summary.2-client-f32 |

버스트 게이지 모델 `source_full_charge_v2`, 택틱 schema 1, 충전/지연 규칙은 그대로다. 규칙 버전 상승은 피해 산술의 변경을 식별하기 위한 것이다.

## 검증 결과

합성 경계 + 기존 Core/Engine 전체 **147/147 통과, 실패 0, skip 0**. Release .NET SDK 10.0.400, 런타임 .NET 10.0.11, Windows x64. `artifacts/hit-f32/final-validation/final.trx`에 147 executed/passed 확인. 마지막 검증은 준비 시 소수 enemyDefense/고정 구간의 과도한 공격력 비율 정밀도 거부까지 포함한다. API/Storage/UI 전체 테스트 통과를 뜻하지 않는다.

- 100×0.145×1 → 115, −0.145 → 85, 동일 0.014×2 → 103, 서로 다른 0.014/0.013 → 102, 음수 .5 tie, 고정 부여 후순위, raw/정밀도 불일치 거부.
- long 중간 곱·그룹 합·고정량 합 overflow, long.MaxValue 고정 부여 보존. 시전자 14.5% 부여를 원값으로 계산해 자기/동료 각각 115 확인.
- 독립 기준 `tests/Nikke.Core.Tests/Fixtures/client_f32_oracle.py`: Python 표준 struct pack/unpack으로 매 연산 binary32를 재현해 10개 golden case를 생성했다. 제품 C# 함수를 호출하지 않는다. base/B/extra/최종 곱 **32-bit 패턴** 및 피해 long을 대조했다.
- 1.5/2.0/1.5/1.3 순서의 B=`0x40533333`=`3.299999952316284`. 전체 float 곱까지 적용한 base=1e8의 피해는 330000000이다. Director의 B만 float로 만든 후 double로 곱한 설명 예시 −5와 혼동하지 않는다. 1.87/2/1.5/1.3은 B=3.669999837875366, 전체 float 최종 피해 366999968.
- 공방차를 long에서 먼저 빼는 경계(16777217−16777216, 계수100 →100), 2^24+1 피해 →2^24, long.MaxValue에 가까운 두 정수의 차25 보존.
- x.5 사사오입/최소1, defenceRatioRate 0/.25/1, statDamageRatio 1/2, 음수 배율 거부, 모든 HitContext double 필드의 NaN/±Inf, float 중간 곱 Inf, 최종2^63 거부 및 바로 아래 float의 long 변환 통과.
- 기본 SkillReplay/summary/WeaponReplay/damage log client 사용, 병렬 실행, 과거 정책 회귀·기존 버스트/앨리스 차지·취소 테스트 통과. 기존 테스트 수정은 버전 기대값 갱신과 소수 통계 경계의 명시적 과거 audit 선택이다.

### 기존 5인 180초 합성 replay 전후

입력 `tools/benchmarks/engine/fixture.json`은 앞선 엔진 작업의 합성 입력이며 계정/실게임 5인 스펙이 아니다. SHA256 `e14a48955bdbc42f15b6e361ef2ab54a5dc66b5c3df46484346b5a3d2cf40f9b`. 앞선 benchmark와 같은 변환: native ATK 100000, DEF **30925 고정**, core=true, crit off, 수동 없음, I/II 지연 1프레임, III 진입 28프레임, 상세 기록 off. 생산 경로 고정 seed는 도입하지 않았다.

전환 전 제품 코드에서 먼저 실행해 기록한 기준: `artifacts/hit-f32/31718279aefe446ea9f3df36ef6ed3eb/replay.json` 및 `baseline/baseline.trx`. 전환 후 legacy 재실행 `590208c848714c7687a0a33b90e8dde4/replay.json`은 전환 전과 정확히 같다. client 결과·히트별 차이 근거는 같은 루트 `0ca14f8b3967455eb116cc76af604d2f/replay.json`.

| 합성 구성원 | 전환 전 legacy | 전환 후 client | 차이 | shots/hits (전후 동일) |
|---|---:|---:|---:|---:|
| fixture-i | 302651627 | 302652598 | +971 | 1948/1948 |
| fixture-ii | 302651627 | 302652598 | +971 | 1948/1948 |
| 5004 (앨리스형 합성) | 136253255 | 136253442 | +187 | 187/187 |
| fixture-iii | 302651627 | 302652598 | +971 | 1948/1948 |
| fixture-excluded | 302651627 | 302652598 | +971 | 1948/1948 |
| 팀 | **1346859763** | **1346863834** | **+4071** | |

풀버스트 9회·crit 0도 같다. fixture-i 상세 히트 977개는 같고 971개는 +1, 앨리스형 187개는 모두 +1이다. 로그의 실제 HitContext를 과거 계산기에 다시 넣어 전환 전 개인 합계와 일치함을 확인했다. 이 입력의 공격력 버프는 .5로 정수 조립 오차가 없어, 차이는 **중간 항별 내림 제거와 최종 사사오입**으로 설명된다. 예를 들어 (100000−30925)×(1+core1+burst.5)=172687.5를 과거는 항별 내림해172687, client는172688로 만든다. 차이 자체를 회귀 실패로 판정하지 않는다. 별도 .145 fixture에서만 long 조립의 114→115 수정이 재현된다.

## 재현 명령

```powershell
python tests/Nikke.Core.Tests/Fixtures/client_f32_oracle.py
dotnet test tests/Nikke.Core.Tests/Nikke.Core.Tests.csproj -c Release --no-restore --logger 'trx;LogFileName=final.trx' --results-directory artifacts/hit-f32/verify
```

실제 dotnet은 `C:/Users/user/Documents/GitHub/Nikke-Simul/.tools/dotnet/dotnet.exe`를 읽기 전용 실행했고, DOTNET_CLI_HOME=`$PWD/.tools/dotnet-home`, NUGET_PACKAGES=`$PWD/.tools/nuget-packages`, DOTNET_CLI_TELEMETRY_OPTOUT=1을 사용했다. 재현용 다른 PC에는 저장소 SDK/복원 의존성이 먼저 필요하다. replay 테스트는 GUID별 자기 artifacts 디렉터리에 결과를 남기며 원본 데이터 루트를 읽거나 복제하지 않는다.

## 후속 연결·미실행·질문

1. **H-SRC** 결과 전에는 위 대응표가 잠정이다. statDamageRatio가 스킬 계수라는 사용자 추정을 확정하거나 보스별 defenceRatioRate를 만들어 넣지 않았다.
2. **API/Contracts/UI/Backend 소유 변경 필요:** schema3와 새 입력 두 개, optional RawRate10000/ExactAmount의 표현을 계약에 연결해야 한다. 현재 로컬 API의 `/api/calculations/hit`는 Core InputSchemaVersion 상수와 비교하므로, 기존 schema2 클라이언트는 그대로면 거부된다. 후보 3개 고정 가정·정수화 선택 목록·기본 legacy 요청·damage log B2~B5 설명을 갱신해야 한다. default 엔진 전환만으로 외부에서 명시한 legacy 요청이 client로 바뀌지는 않는다.
3. **캐시/결과 분리:** 새 engine/rules/summary/schema 버전, RoundingPolicy, StatDamageRatio, DefenceRatioRate 및 raw/정수 입력을 fingerprint에 넣고 이전 summary/GPU tuning/통계 결과와 혼합하지 않아야 한다. 계정 native 스탯이 소수이면 adapter에서 임의 절삭하지 말고 클라이언트 조립 규칙을 확인해야 한다. 큰 long을 JS number로 전달할지 문자열로 전달할지는 외부 계약 후속이다.
4. **미실행:** 기존 실측 18점의 새 정책 대조·새 게임 관측·독립 검산 도구 변경·SW 단일 타격 검사·GPU client_f32 kernel·실제 사용자 덱·API/UI 종단·배포. 지시서의 이후 별도 단계다. 이 작업의 147개 통과를 실게임 정확성 수용으로 표현하지 않는다.
5. **사용자에게 확인할 구체 질문:** 클라이언트 attack/native/flat 스탯 생성에서 소수가 들어올 경우 어느 메서드에서 어떤 정수화가 수행되는가? 각 원천 rate의 float 변환과 `1 + bonus` 구성은 정확히 어디인가? base/extra/최종 곱에도 float 저장 경계가 각각 있는가, 식 결합 순서는 전달 공식과 같은가? H-SRC의 항별 원천 질문과 별개로 산술 확인이 필요하다. 이번에는 지시된 순서·자료형으로 구현했고 게임 바이너리를 조사하지 않았다.

현재 사용자 실행 경로는 여전히 `C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe`다. 본인 worktree 구현은 그 경로의 배포가 아니며 EXE/원본 UI/backend 갱신·실행 확인은 수행하지 않았다.

## 확정 커밋·인계

코드/검증 커밋 해시는 확정 후 아래에 기록한다. Director 터미널은 지시서대로 기존 목록을 재조회하고 확정 커밋·이 보고서 절대 경로·검증·미완료를 한 번만 전달한다.
