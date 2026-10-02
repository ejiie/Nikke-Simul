# E-PREC-1 — 계산 정밀도 후속 (엔진, 통계 worktree 임시 소유)

2026-10-03 배정([지시서](C:/Users/user/orca/workspaces/Nikke-Simul/Director/docs/skill-precision-assignments-2026-10-03.ko.md) E-PREC-1). 기준: Director `e96b147`을 일반 merge(fast-forward)한 뒤 작업. 구현 Sonnet 5.5(high), 리뷰 astra-6, 흐름은 [작업 구조](C:/Users/user/orca/workspaces/Nikke-Simul/Director/docs/workflow-implement-review.ko.md)를 따른다. **구현 완료·리뷰 대기 상태이며 QA·통합·배포 보고가 아니다.** push·배포·새 워커 없음, 원본 `accounts.db`·세션·캐시·presentation·5180/5181·EXE 접근 없음.

## 요구 대조표

| # | 요구 | 상태 | 구현 위치 |
|---|---|---|---|
| 1 | `client_f32_dprod` 비교 정책(기본 불변) | 완료 | `ClientFloatDamage.CalculateDoubleProduct`, `HitCalculator.CalculateClientDoubleProduct/Evaluate/Calculate`, `IsClientPolicy` |
| 2 | true damage는 방어율 미적용 | 완료(client 계열 2개 정책) — 아래 "열린 질문" 참조 | `HitCalculator.PrepareClient` |
| 3 | 저지(96)·파츠(112) 분리, 96 중복 제거 | 완료 | `HitContext.InterruptionTarget/InterruptionDamage`, `PrepareClient`, `SkillReplay.Damage` |
| 4 | 장탄 조립 `long` 전환 | 완료 | `StatBuffCalculator.ApplyAmmo`, `SkillReplay.SyncGun`, `WeaponReplay` |
| 5 | 기존 5인(리타·블랑·앨리스·누아르·모더니아) 180초 전후 비교 — 결과 변경 항목(2·3·4), 1은 기존 결과 동일 | 완료(공개 표 + 합성 스탯, 계정 접근 없음) | 아래 "전후 비교 A" |

## 1. `client_f32_dprod` 후보 정의

기본 정책 `client_f32`는 바꾸지 않았다(`HitCalculator.DefaultPolicy`, `SkillReplayConditions` 기본값 그대로). `client_f32_dprod`는 **`Calculate`/`Evaluate`/`SkillReplay`의 명시 선택으로만** 쓰이며, `HitCalculator.Compare`의 후보 목록(4개)·`HitWire.Policies`·`WeaponReplay` 비교 정책·UI에는 노출하지 않았다.

| 단계 | `client_f32` | `client_f32_dprod` |
|---|---|---|
| 공격력·방어력 | `long` 조립, checked | 같음 |
| 공방차 | `long` 뺄셈 후 `(float)` 변환 | `long` 뺄셈 후 **정확한 binary64**(2^53 초과 시 거부). float 변환 없음 |
| rate 입력(damageRatio·statDamageRatio·charge·crit/core/burst/range·break·add·reduction·defenceRatio·element) | float32 값 | **같은 float32 값**(binary64로 정확히 widening) |
| B | float32 누적(crit→core→burst→range, 각 `rate−1` 더함) | **같음(float32)** |
| extra = break + add − 1 | float32 | **같음(float32)** |
| 감소 `1−reduction`, 방어율 `1−defenceRatio` | float32 | **같음(float32)** |
| base = diff × damageRatio × statDamageRatio × charge | float32 좌→우 | **binary64** 좌→우 |
| 곱 base × B × extra × reduction × defenceFactor × element | float32 좌→우 | **binary64** 좌→우 |
| 최종 | `MathF.Round` away-from-zero → max(1) → checked `long` | `Math.Round` away-from-zero → max(1) → checked `long`(≥2^63 거부) |

해석 근거: C#에서 float 피연산자와 double 누적이 섞이면 float이 정확히 double로 승격되므로, "B는 float32, 곱셈 사슬은 double"의 **최소 변경** 해석은 rate 피연산자 값은 그대로 두고 누적 정밀도만 바꾸는 것이다. extra·reduction·방어율 항 자체를 double로 다시 계산하는 변형은 별도 후보가 되며 이번에 만들지 않았다(1-tick 대조 결과에 따라 후속). 감사 term 이름은 `client_f32`와 같고 operation 문구에 자료형을 적었다.

테스트(`PrecisionFollowupTests`):

- 독립 기대값: `System.Numerics.BigInteger` 분수 산술(float32는 이진 분수라 곱이 정확)로 곱셈 사슬을 계산하고 round-half-away를 적용한 값과, B·extra 등 float32 피연산자는 테스트 안에서 별도 float 연산으로 만든 값을 사용. 2,000개 결정적 난수 케이스가 모두 일치(`Double_product_matches_an_independent_rational_oracle_on_large_hits`).
- "float32로 표현 불가" 확인: 2^24 초과 피해 중 절반 초과가 float32 비표현 정수이고, 같은 입력의 기본 정책 결과 500건은 항상 float32 표현 가능(`Default_float32_chain_only_produces_float32_representable_damage_above_2_pow_24`). 손계산 고정 케이스(공방차 700,000, 계수 25.5, B=0x40533333)에서 기본 정책은 표현 가능한 값, dprod는 비표현 값.
- 공방차 2^24+1: 기본은 16,777,216, dprod는 16,777,217. 입력 검증·true damage 규칙 공유, 리플레이 실행·damage log 정책 이름, 정책명 오타 거부.

## 2. 방어율의 true damage 예외

`PrepareClient`에서 `DamageType=="true"`이면 `defenceRatioRate`를 0f로 둔다(`1 − rate = 1`). 입력 검증(유한·범위)은 그대로 한다. 사용자 확인 예시(최종 10, 방어율 60%): 일반 4, true 10 테스트로 고정(두 client 정책 모두, `skill` 유형도 일반과 같이 4). 감사 term `defenceRatio`의 After가 true에서 1.

기존 동작과의 차이: true 타격이 `DefenceRatioRate`>1일 때 이전에는 "Negative client_f32 multiplier"로 거부됐으나 이제 무시되어 거부되지 않는다(true는 이 항을 쓰지 않으므로 의도된 결과).

## 3. 저지·파츠 분리

- `HitContext`에 `InterruptionTarget`(bool)·`InterruptionDamage`(double) 추가, 중립 기본(false/0). client 계열: `breakRate = InterruptionTarget ? 1 + InterruptionDamage : 1`, `addDamageRate`에 `Parts ? PartsDamage` 포함(순서: AttackDamage → Pierce → Parts → dot → sequential → true). 이전의 `breakRate = parts ? 1 + PartsDamage : 1`은 폐기.
- 런타임(`SkillReplay.Damage`): 96 효과 합을 `AttackDamage`에 더하던 것을 `InterruptionTarget=input.InterruptionTarget`·`InterruptionDamage`(멤버 기본값 + 96 효과 합)로 옮겼다. 중복 제거 테스트(`Runtime_96_is_no_longer_duplicated_into_attack_damage`): 저지 대상 150·hit.AttackDamage 0, 비대상 100이며 96 효과가 없는 실행과 동일.
- legacy 3정책(`legacy_term_floor`·`final_round_even`·`nested_floor`)은 이전 결과를 재현해야 하므로 interruption을 B3의 `AttackDamage` 항 안에 `(AttackDamage + interruption)`으로 더한다(이전 런타임이 `AttackDamage + 96합`을 만든 것과 binary64 연산이 동일). 3정책 모두 `AttackDamage=.7` 입력과 `AttackDamage=.2, 저지 .5` 입력의 결과가 같음을 테스트로 고정하고 `Compare` 경로도 확인했다.
- 파츠만 켠 경우 수치(`extra=1.3f`, 피해 130)는 이전과 같고, float 합산 순서가 바뀌므로 float 경계에서 최대 1 ulp 차이가 날 수 있다(런타임은 `Parts`를 설정하지 않아 영향 없음, 단일 히트 API만 해당 가능).

## 4. 장탄 `long` 조립

`StatBuffCalculator.ApplyAmmo`는 `ApplyAttack`과 같은 정수 경로(`ApplyInteger`)다: 최대 장탄 = 기본 + Σ(동일 비율 그룹별 round(기본 × rate10000 × 개수 / 10000), 사사오입), 1/10000 원천 보존, checked. `SyncGun`은 스킬 장탄 함수(type 14, 비율형)를 `StatRateBuff.FromRaw`로 원천 정수에서 만들고, 정액형은 `FunctionValue×스택`의 `long` 합을 더한다. `WeaponReplay`의 장탄 두 곳(초기 장탄, 검증)도 같은 경로로 바꿨다(두 리플레이의 장탄이 달라지지 않게 하기 위한 최소 호출부 변경).

- 이전 binary64 경로는 기본 100·14.5%에서 14.499999999999998 → 14, 새 경로는 15(115)다. 테스트에 두 값을 모두 고정했다. 이전 `StatBuffCalculator.Apply`는 다른 용도를 위해 남겼다.
- 원천 점검(읽기 전용): 현재 catalog `calculation/5fec7706…`의 `cube_effect_table.json`(MaxAmmo 값 15개: 14.84·22.27·29.69)과 `collection.json`(max_ammo_pct 8개: 1.56…9.5)의 값/100이 모두 1/10000 격자 위. 두 파일 hash 전후 동일 — `cube_effect_table.json` `5b0231b2103a124e9585631462d5ccfa21d8ce389f68cbb9fc6ddf9213b1fda4`, `collection.json` `6ae3df677f8fa4ac910853611e682d54741e42a66db82e64b0546b6720f32f31`. OL 장탄 옵션은 이 점검에 포함하지 않았다(계정 스냅샷 값이므로 접근하지 않음); 1/10000 격자 밖 입력은 공격력과 같이 이제 `ArgumentException`으로 거부된다(조용한 절삭 없음).
- 범위 밖으로 둔 것: 장탄 회복 함수(type 27, `Math.Round(MaxAmmo × Rate)`, `SkillReplay.cs` 약 388행)와 `SkillFiringModel`/`FiringModel`의 재장전 비율 반올림은 "최대 장탄 조립"이 아니라 건드리지 않았다. 같은 binary64 반올림 위험이 있으므로 후속 후보로만 적는다.

## 전후 비교

### A. 리타·블랑·앨리스·누아르·모더니아 5인 180초 (공개 표 + 합성 스탯, 리뷰 반려 #5 보완)

계정 접근 없이 비교했다. 공개 표(`game-catalog.json`, `calculation/*`, `runtime/*` — 12개 파일)를 worktree `artifacts/precision-followup/five-public/public/`로 복사해 읽었고, 합성 계정(Lv400, 스킬 1·2·버스트 10, 장비·큐브·소장품·한계돌파·코어·호감도·콘솔 0)을 코드로 만들어 `RuntimeReplayService.RunSkills`로 실제 멤버 입력을 산출했다. 원본 `accounts.db`·세션·캐시·presentation·5180/5181·EXE는 열지 않았다. 공개 표 hash는 실행 전후 동일(변경 0): `game-catalog.json` `debc8bd3…2b4`, `calculation/current.json` `ee0a0057…24f6`, `runtime/current.json` `fd80fda1…91ba`, runtime `catalog.json` `9c98c91c…71cd`(전체 12개 목록은 `source-hashes-{before,after}.json`).

- **변경 전** = `e96b147`의 `src`(`git archive`로 scratchpad에 추출), **변경 후** = 이 worktree `src`. 같은 프로브(`artifacts/precision-followup/five-public/Probe.Program.cs`, Git 제외)를 두 쪽에 컴파일해 실행했다.
- 조건: 10,800F, 고정 DEF 30,925, 코어 ON, 앨리스 수동 풀차지, 크리 `sample`이지만 **시드 고정 RNG 1~5**를 `SkillReplay.Run`에 주입(결정적, 두 쪽 동일 시드), 자동 버스트 tactic(1단계 리타·2단계 블랑·3단계 앨리스·누아르·모더니아, 3단계 로테이션 앨리스·모더니아, `next_ready`). 정책 `client_f32`와 `legacy_term_floor`.
- 시나리오: ① base ② `interruptionTarget=true` ③ 5인 head OL 장탄 +14.5% ④ 장탄 +11.81%.

| 시나리오 | 정책 | 시드 1~5 멤버별 피해·발수·치명타·장탄·잔탄 | 팀 피해(시드 1) |
|---|---|---|---:|
| base | `client_f32` | 5개 모두 **전후 동일** | 718,382,334 |
| base | `legacy_term_floor` | 5개 모두 동일 | 718,335,114 |
| interruptionTarget | `client_f32` / legacy | 5개 모두 동일 | 718,382,334 / 718,335,114 |
| 장탄 +14.5% | `client_f32` / legacy | 5개 모두 동일 | 772,905,797 / 772,850,811 |
| 장탄 +11.81% | `client_f32` / legacy | 5개 모두 동일 | 767,946,890 / 767,891,945 |

`client_f32`의 시드별 팀 피해: 718,382,334 · 706,999,032 · 710,967,650 · 708,935,937 · 712,395,060. 시드 1 base 멤버: 리타 71,558,406(발 3,310, 장탄 125), 블랑 44,396,700(1,782, 65), 앨리스 228,820,635(196, 11), 누아르 163,012,068(270발·2,700히트, 14), 모더니아 210,594,525(8,059, 229).

- 해석: **기존 5인의 `client_f32` 결과는 전부 불변**이다. 이 변경이 5인 경로에서 실제로 값을 바꾸지 않는 이유를 확인했다 — 2(true damage 방어율)는 런타임이 `DamageType="true"`를 만들지 않아 해당 없음; 3(저지)은 누아르 로드아웃에 96 효과가 있으나 이 편성·180초에서 `buff_on` 0회(발동 조건 미충족)라 활성되지 않아 `interruptionTarget`을 켜도 동일; 4(장탄)는 +14.5%·+11.81% OL에서 최대 장탄이 전후 동일(리타 137/134, 블랑 69/67, 앨리스·누아르·모더니아 각 시나리오 동일) — 이 네이티브 장탄 값들에서는 x.5 경계가 나오지 않아 반올림 차이가 없다. 반올림 경계 자체는 단위 테스트(100×14.5%: 114→115)가 보인다. 저지 경로의 실제 활성은 합성 런타임 테스트가 보인다.
- 관찰(이번 변경과 무관, 전후 동일): 장탄 OL을 넣은 시나리오에서 앨리스·누아르 최대 장탄이 base(11/14)보다 줄어든다(7/10). 합성 head 장비 한 줄이 들어가면서 다른 입력이 바뀌는 것으로 보이며 이 보고서의 범위가 아니다 — 필요하면 후속 점검.
- `client_f32_dprod`(변경 후만 실행 가능): 시드 1~5 모두 `client_f32`와 팀·멤버 피해 차이 0. 히트당 피해가 ~1e5 규모(float32 간격 <0.01)라 곱셈 정밀도 차이가 나타나지 않는다. 차이는 2^24 이상 큰 타격(SW 버스트급)에서 생기며 단위 테스트가 보인다.

### B. 합성 fixture 5멤버 (보조 증거)

`tools/benchmarks/engine/fixture.json`, 방어력 30,925 고정, 크리 off:

| 항목 | 변경 전(기준 `e96b147`) | 변경 후 |
|---|---:|---:|
| `client_f32` 총합 | 1,346,863,834 | 1,346,863,834 |
| `legacy_term_floor` 총합 | 1,346,859,763 | 1,346,859,763 |
| 멤버별 `client_f32`(4인 / `5004`) | 302,652,598 / 136,253,442 | 동일 |
| `client_f32_dprod` 총합 | (해당 없음) | 1,346,863,834 (멤버별도 동일) |

증거 JSON: `artifacts/precision-followup/<guid>/fixture-5member-180s.json`, `.../five-public/report-{before,after}.json`(모두 Git 제외).

## 규칙 버전·fingerprint(차단 7항목 #7)

| 상수 | 이전 | 변경 후 |
|---|---|---|
| `HitCalculator.Version` | `p02.4-client-f32` | `p02.5-client-f32-prec1` |
| `StatBuffCalculator.Version` | `native-stat-shared-buffs-v3-attack-i64` | `native-stat-shared-buffs-v4-ammo-i64` |
| `SkillReplay.Version` | `p03.skills.6-manual-charge-delay` | `p03.skills.7-precision-1` |
| `WeaponReplay.Version` | `p03.weapon-reference.4-manual-charge-delay` | `p03.weapon-reference.5-precision-1` |
| `PreparedSkillReplay.Version` | `cpu-summary.5-manual-charge-delay` | `cpu-summary.6-precision-1` |
| `TeamBurstController.Version` | `p04.team.6-manual-charge-delay` | `p04.team.7-precision-1` |

`ComputePreparation.RulesVersion`이 SkillReplay·TeamBurst·HitCalculator·StatBuff·Boss 버전과 정책을 이어 붙이므로 fingerprint가 분리되고(기존 Compute 테스트 46개 통과), 이전 저장본은 `engine_or_rules_version_changed`로 거절된다. 정책 이름이 RulesVersion에 들어가므로 `client_f32_dprod` 결과도 기본 결과와 섞이지 않는다.

## 소유 범위 밖 변경 (Director 승인 2026-10-03)

Director가 이번 작업 한정으로 승인했다(조건: 연결·버전 외 동작 변경 금지, 문서는 이번 구현 사실만 반영하고 기존 결정·기록은 지우지 않고 정정 표시, 엔진 worktree 충돌은 Director 통합 때 merge로 해결하며 범위를 넓혀 미리 맞추지 않음). 커밋 `c7b6c83` 기준 줄:

| 파일:줄 | 변경 | 이유 |
|---|---|---|
| `src/Nikke.Engine/WeaponReplay.cs:72` | Version 상수 | 장탄 결과 변경 → 규칙 버전 상향 |
| `WeaponReplay.cs:93`, `:200` | `Apply`→`ApplyAmmo` | 최대 장탄 조립을 스킬 리플레이와 같은 `long` 경로로(두 리플레이 불일치 방지) |
| `WeaponReplay.cs:177`, `:213` | `== DefaultPolicy`→`IsClientPolicy` | 새 client 계열 정책이 같은 정수 검증 경로를 쓰도록 |
| `src/Nikke.Engine/Skills/PreparedSkillReplay.cs:18` | Version 상수 | summary 구현 버전 → fingerprint 분리 |
| `src/Nikke.Engine/Skills/TeamBurstController.cs:32` | Version 상수 | 팀 리플레이 결과 `RulesVersion` 표시·캐시 키 |
| `src/Nikke.Engine/Skills/SkillReplay.cs:11` | Version 상수 | 결과 변경 → 규칙 버전 |
| `SkillReplay.cs:91` | 정책 허용 목록에 `client_f32_dprod` | 후보 정책을 리플레이에서 선택 가능하게 |
| `SkillReplay.cs:428`, `:524` | `IsClientPolicy` 분기 | 후보 정책도 정수 공격력 경로 |
| `SkillReplay.cs:578-588` | `SyncGun` 장탄 조립을 `ApplyAmmo`로 | 항목 4 |
| `SkillReplay.cs:608-610` | 히트 입력: 96 → `InterruptionTarget/Damage` | 항목 3(소유 범위의 "히트 입력 구성") |
| `docs/hit-damage-client-f32.ko.md:35,36,38` | 표 3행 정정 표시 | addDamageRate·breakRate·defenceRatioRate 대응 변경 |
| `docs/hit-damage-client-formula.ko.md:60,79,118` | 정정 표시(취소선 + 정정문) | 96 중복·분리 완료 반영 |
| `docs/hit-damage-source-investigation.ko.md:7` | 역사 기록 주의문 | "현 엔진" 서술이 조사 시점 기준임을 표시 |

UI·API 계약(`Nikke.Contracts`)·Data 계층 파일은 수정하지 않았다.

## API/계약 영향 보고(수정 없음)

- 단일 히트 API의 입력 필드 검증은 `HitContext` 속성을 reflection으로 열거하므로 `interruptionTarget`·`interruptionDamage`가 **자동으로 허용 입력이 되고**, 응답 `input`에도 직렬화된다(스키마 3 유지, 중립 기본). 이전 저장본은 필드가 없어도 기본값으로 읽힌다. UI에는 입력 control이 없다.
- `client_f32_dprod`는 `HitWire.Policies`에 없어 API로 선택할 수 없다(요구대로 미노출). 노출 시 후속 배정이 필요하다.
- 단일 히트 응답의 `defenceRatio`·`extra` term operation 문구와 true damage 결과가 바뀐다.

## 열린 질문 → 해소 (Director 동의, 비차단)

- 지시서 2번 "모든 정책에 반영": legacy 3정책(`legacy_term_floor`·`final_round_even`·`nested_floor`)은 애초에 `DefenceRatioRate` 항을 계산하지 않는다(단일 히트 응답 limitations에 이미 명시). 이를 "모든 정책"에 방어율 항 자체를 새로 넣으라는 뜻으로 읽으면 legacy 결과가 바뀌므로, **방어율 항이 있는 두 client 정책에만 반영**하고 legacy는 기존 비모델링을 유지했다. Director가 2026-10-03 "legacy 방어율 비모델링 유지는 비차단 기록 동의"로 확정했다.

## 검증 결과

`dotnet`은 원본 `.tools` SDK를 worktree 로컬 `DOTNET_CLI_HOME`/`NUGET_PACKAGES`로 실행.

| 프로젝트 | 변경 전 | 변경 후 |
|---|---:|---:|
| `Nikke.Core.Tests` | 217 통과 | **235 통과**(신규 18: `PrecisionFollowupTests`) |
| `Nikke.Compute.Tests` | — | 46 통과 |
| `Nikke.Sync.Tests` | — | 164 통과 |
| `Nikke.Analysis.Tests` | — | 41 통과 |

기존 테스트 수정은 버전 문자열 단언 3곳(`ClientFloatDamageTests`·`PreparedSkillReplayTests`·`BurstTacticTests`)뿐이다.

문서 동기화: `docs/hit-damage-client-f32.ko.md`(addDamageRate·breakRate·defenceRatioRate 행)·`docs/hit-damage-client-formula.ko.md`(breakRate 서술·대응표·후속 목록)·`docs/hit-damage-source-investigation.ko.md`(역사 기록 주의문)를 본 변경과 모순되지 않게 갱신했다. 이전 `breakRate = 1 + PartsDamage` 서술은 폐기로 표시했다.

## 보존 규칙 확인

- 원본 `data/local`은 공개 표만 읽었다: 장탄 점검 `calculation/5fec7706…/{cube_effect_table,collection}.json`, 5인 비교 12개 파일(위 "전후 비교 A"). 모두 hash 전후 동일, 복사본은 worktree `artifacts/` 안(Git 제외). `accounts.db`·세션·캐시·presentation은 열지 않았다(합성 계정은 코드로 생성). 5180/5181·원본 EXE 접근 없음.
- `package-lock.json`은 미추적 상태로 두었고 커밋하지 않는다. push·배포·새 워커 없음.

## 리뷰 이력

### 1차 리뷰 — 반려 (astra-6, 커밋 `c7b6c83`)

1. 차단 #1 — 명시 소유 밖 `WeaponReplay.cs`·`PreparedSkillReplay.cs`·`TeamBurstController.cs`, `SkillReplay`의 히트 입력 외 변경, `docs/hit-damage-*.ko.md` 3개. → 리뷰어가 Director에 범위 판단을 요청했고 **Director가 2026-10-03 이번 작업 한정으로 승인**(조건은 위 "소유 범위 밖 변경" 절). 이 절에 파일·줄·이유 표를 추가했고, 문서 정정은 취소선 정정 표시로 바꿔 기존 기록을 보존했다.
2. 차단 #3·#6 — 기존 5인 180초 전후 비교 누락(합성 멤버 fixture로 대체). Director가 반려 유지·보완 지시. → 위 "전후 비교 A"로 보완: 공개 표 + 합성 스탯으로 리타·블랑·앨리스·누아르·모더니아의 실제 스킬 경로를 변경 전/후 코드에 시드 고정으로 실행, `client_f32`·legacy 모두 5개 시드·4개 시나리오 전부 동일. 모순·누락 점검으로 본 보고서의 이전 문장 "기존 5인 비교는 수행하지 않았다"를 삭제했다.

비차단 의견 기록: legacy 정책의 방어율 비모델링 유지(Director 동의), dprod의 float32 extra/감소 항 정의 명시 확인.
