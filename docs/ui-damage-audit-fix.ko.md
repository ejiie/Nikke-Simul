# 발당 피해 검산 패널 표시 수정 (UI, 2026-09-11)

범위: `docs/ui-damage-audit-handoff-2026-09-11.ko.md`(Director 작업공간, 미커밋 인계 문서)의 UI 표시 수정만 다룬다. 엔진·Core·API·DB 원본과 저장 로그, 버스트 설정 UI(`app.js`, `burst-tactics.js`)는 바꾸지 않았다. 피해를 UI에서 다시 계산해 저장값을 대체하지 않는다. 화면은 저장된 `calculation.terms`, `hit`, `buffs` 원값을 해석해 보여 줄 뿐이다.

기준: UI 브랜치를 Director `77b3cce`로 fast-forward한 뒤 작업했다. 편집 파일은 `apps/desktop-ui/damage-log-adapter.js`(피해 로그 표시·변환 부분, 버스트 DTO 변환 유지), `apps/desktop-ui/damage-log.js`, `apps/desktop-ui/simul.css`(검산 패널 전용 규칙), 새 테스트 `tests/ui/`, 이 문서다.

## 1. 확인한 원인

| 증상(사용자 화면) | 원인 |
|---|---|
| `누아르 공격력 증가 +1719100%` | type 1 `native_caster_flat_at_application`의 value는 시전자 기초 공격력 기준 **고정 공격력**(17191)인데 UI가 모든 value에 `×100 %`를 붙였다 |
| `블랑 효과 +13166685%`, `효과 +16577073%` | type 2 HealCharacter의 value는 **초당 HP 회복량**(131666.853, 165770.7264)이다 |
| `효과 +1000%`, `효과 +400%` | type 54 StatPenetration 원값 10, type 14 StatAmmo(Integer) 탄 수 4 |
| 대부분 `효과`로 표시 | 어댑터가 type 1/61 외에는 이름을 매핑하지 않았다 |
| `크리 1.62x × 코어 × 풀버스트 1.5x` 산식 | 엔진은 거리·풀버스트·크리·코어 보너스를 **더하는** 가산 묶음(B2)으로 계산한다. 곱 표기는 실제 구현과 다르다 |
| 차지 배율·계수 등 fallback | 값이 없으면 0/1 또는 `Math.max(1, …)`로 정상값처럼 채웠다 |

수정 전 코드(`77b3cce`)를 같은 저장 로그로 브라우저에서 열어 재현했다: `니케 #5009: 공격력 증가 +1719100% (상시)`, `니케 #5008: 효과 +16577073% (잔여 443F)`, `니케 #5009: 효과 +400%`, 합성 경계 입력의 `차지속도 증가 +1200%`(caster_charge_centiseconds 12). 증거: 아래 6절 before 스크린샷.

## 2. type·basis → 이름·단위 근거

근거 순서: 엔진이 값을 저장하는 방식(`src/Nikke.Engine/Skills/SkillReplay.cs` `AddEffect`, `Damage`, `SyncGun`, `MaxHp`) → 공식 FunctionType wire 값(기존 C# `OfficialSkillEnums.cs` 미러, `docs/p03-skill-runtime.ko.md` 64행이 참조) → 기존 한국어 표시명(`tools/data-pipeline/spec_presentation_assets.py` OPTIONS) → 단위 규칙(`docs/p03-skill-runtime.ko.md` 27행: StatChargeDamage/StatCriticalDamage는 Integer라도 /10000, StatAmmo Integer는 탄 수). 이름은 부호 없는 명사로 두고 부호는 값에 붙인다(음수에 `+-` 없음).

| type | 공식 키 | 표시명 | 엔진 저장 값(AddEffect) | 표시 | 이 타격 피해 반영 판정 |
|---|---|---|---|---|---|
| 1 | StatAtk | 공격력 | native_*: Rate / 시전자 기준 타인 부여: `native_caster_flat_at_application` 고정 공격력 | `+14.42%` / `공격력(고정) +17,191` | `hit.runtimeAttackBuffs`·`hit.attackFlatBuffs`에 같은 출처 키(`skill:{source}:{functionId}`)가 있을 때만 반영 |
| 2 | HealCharacter | HP 지속 회복 | `caster_final_max_hp_at_application`: 1초 tick당 HP | `초당 HP +165,770.7264` | 피해 산식 항 아님 |
| 8 | StatAccuracyCircle | 명중률 | -Rate(원천 음수 = 버프) | `+7.49%` | 명중 판정용 |
| 11 | StatChargeDamage | 차지 대미지 | Rate | `+7%` | 풀차지 타격만 차지 배율 가산항 |
| 14 | StatAmmo | 최대 장탄 수 | Integer: 탄 수 / Percent: Rate | `+4발` / `+45.17%` | 탄약 흐름 |
| 42 | DamageReduction | 적 받는 대미지(대상 boss) | -Rate | `+39.26%` | 대상이 boss면 B4 |
| 51 | StatCriticalDamage | 크리티컬 대미지 | Rate | `+12.46%` | 크리티컬 타격만 가산 묶음 |
| 54 | StatPenetration | 관통 | FunctionValue 원값 | `원값 10` | `hit.pierce`만, `pierceDamage≠0`일 때만 B3 |
| 61 | StatChargeTime | 차지 속도 / 차지 시간 | native_*: -Rate / `caster_charge_centiseconds`: 1/100초 고정 단축 | `+80.15%` / `-0.12초` | 차지 시간·발사 흐름 |
| 62 | DrainHpBuff | 흡혈 | Rate | `%` | 회복 |
| 94 | StatHpHeal | 최대 HP | Rate(`MaxHp`의 비율 버프로 사용) | `%` | 생존 |
| 96 | BreakDamage | 저지 대미지 | Rate | `%` | `conditions.interruptionTarget=true`일 때만 B3 |
| 0, 5, 40 | None, AllAmmo, Immortal | 상태 표식, 탄약 무제한, 불사 | FunctionValue 원값 | `원값 N` | 상태 |
| 그 외 | — | `미해석 효과 (type N)` | — | `원값 N` + basis | 반영 여부 미확인 |

- 예상과 다른 basis면 %를 붙이지 않고 `원값`과 basis를 그대로 보인다.
- 스택: value는 스택당 값이다. `스택당 +12.46% × 2 = +24.92%`처럼 총량을 한 번만 곱한다.
- 지속시간: `expiresAt`은 배타적 종료 프레임. null은 `만료 없음(전투 지속·조건 해제 시 제거)`, 필드 부재는 `지속시간 미제공`, 타격 프레임 이상이면 `만료 프레임 경과 · 기록 확인 필요`. 프레임이 정확값이고 초는 반올림한 참고값이다.
- 출처: 편성 표시명이 있으면 `누아르 (#5009)`, 없거나 이름이 ID와 같으면 `니케 #5009`. 저장 replay의 `inputs[].skills.slots`에서 직접 함수 ID를 찾으면 `스킬 1 · 함수 227110701`, 못 찾으면 `함수 119111002 · 슬롯 미확인(하위 스킬·연결 함수)`. 슬롯명을 추측하지 않는다. `burstCastId`가 있으면 버스트 시전 이벤트 ID를 덧붙인다.
- type 14 한계: 로그 스냅샷에 function value type이 없다. 엔진은 Integer를 원값(정수), Percent를 원값/10000으로 저장하므로 정수 value를 탄 수로 표시하고 `값 유형 미기록 · 정수 원값을 탄 수로 표시`를 함께 적는다. 현재 로컬 카탈로그의 type 14 함수 30개(Integer 10, Percent 20)에는 원값이 10000의 배수인 Percent가 없어 이 표시와 충돌하지 않았다.

## 3. 산식 수정 근거

`src/Nikke.Core/Combat/HitCalculator.cs` `Compare`:

- `P = (effectiveAttack − effectiveDefense) × coefficient × charge`, `charge = fullCharge ? base × (1 + multiplierBonus) + add : 1`.
- 방어력 ≥ 공격력이면 정책과 무관하게 `minimum` 1(가산 묶음·B3~B5 없음).
- `legacy_term_floor`: `B2 = ⌊P⌋ + Σ⌊P × bonus⌋`(거리·풀버스트·크리·코어), `최종 = ⌊B2 × B3 × B4 × B5⌋`.
- `nested_floor`: 같은 B2, B3·B4·B5를 곱할 때마다 내림.
- `final_round_even`: `B2 = P × (1 + Σbonus)`, 최종 반올림(동률 짝수), 최소 1.

패널은 이 정책별 식과 저장된 terms 표(단계·입력·결과·저장 연산 문자열)를 그대로 보인다. 카드: 기초/최종 공격력, 방어력, 공방차(`P.before`), 계수, 차지 배율(풀차지 식 또는 `풀차지 아님 → 1`), P, 가산 보너스 묶음(`1 + 합`과 항목별 적용/미적용), B3×B4×B5(`multiply` 연산 문자열의 인자), 정책, 최종 피해와 저장 `damage` 일치 여부. terms가 없거나 일부 항목이 빠지면 `미제공`과 `누락된 계산 항목: …`을 표시하고 0/1로 채우지 않는다. 합성 미리보기(object 형태 terms)는 헤드라인 카드만 채우고 단계 검산 불가를 밝힌다.

실제 계산기로 만든 합성 경계 입력(`tests/ui/fixtures/hit-calculator-cases.json`, `HitCalculator.Compare p02.3`) 크리+코어+풀버스트+적정거리: legacy B2 = 654085 + 196225 + 327042 + 408541 + 654085 = 2239978, 최종 4460732. 삭제한 곱 표기로 계산하면 이 값과 달라진다(단위 테스트에서 불일치 단언).

"현재 활성 효과"와 "이 타격 피해 계산 반영"을 분리했다. 엔진 계약(`docs/damage-log-engine-contract.ko.md` 15행)대로 버프 목록에는 산식에 쓰이지 않는 효과도 있으므로 판정은 `hit`/`calculation`으로만 한다. 그룹: 반영 / 조건 미충족으로 미반영 / 피해 산식 항 아님 / 반영 여부 미확인. 최종 공격력 입력은 `hit.attackBuffs`(상시 비율), `runtimeAttackBuffs`, `attackFlatBuffs`를 출처 키와 함께 따로 나열한다.

## 4. 예시: 원값 → 표시

실제 저장 로그(사용자 스크린샷과 다른 실행)에서 확인한 대응이다.

| 원값 (type, value, basis) | 수정 전 | 수정 후 |
|---|---|---|
| 1, 17191, native_caster_flat_at_application | `공격력 증가 +1719100%` | `공격력(고정) +17,191` · 반영: 최종 공격력 고정 가산 |
| 2, 165770.72639999999, caster_final_max_hp_at_application | `효과 +16577073%` | `HP 지속 회복 초당 HP +165,770.7264` · 피해 산식 항 아님 |
| 54, 10, native_caster | `효과 +1000%` | `관통 원값 10` · 관통 판정만 활성 · 관통 대미지 보너스 0 |
| 14, 4, native_recipient | `효과 +400%` | `최대 장탄 수 +4발` |
| 61, 0.8015, native_caster | `차지속도 증가 +80%` | `차지 속도 +80.15%` · 피해 산식 항 아님 |
| 42, 0.3926, native_recipient, target boss | `효과 +39%` | `적 받는 대미지 +39.26%` · 반영: B4 |
| 51, 0.1246 (크리 아님) | `효과 +12%` | `크리티컬 대미지 +12.46%` · 미반영: 크리티컬 아님 |
| 96, 0.1672, interruptionTarget=false | `효과 +17%` | `저지 대미지 +16.72%` · 미반영: 저지 대상 조건 꺼짐 |

## 5. 실행한 검증

| 명령 | 결과 |
|---|---|
| `node tests/ui/damage_audit.test.mjs <saved replay> artifacts/ui/damage-audit/unit-final` | 16/16 통과. 단위 변환, type+basis, 출처 이름/ID fallback, 소수·음수·0·null·미해석 type, 지속시간 상시/잔여/만료/미제공, 스택 1회 곱, HTML escape, 가산 묶음, 정수화 3정책, 비풀차지·최소 피해·누락 terms, 합성 미리보기. 읽기 전용 실제 저장 로그 134행 전체에서 최종 단계 = 저장 damage, legacy B2 = 내림 항 합 |
| `node tests/q3/check_ui_contract.mjs <engine example result.json>` | 25/25 통과 (Q3 계약 회귀, 제외 파일 미수정) |
| `python tools/data-pipeline/tests/check_damage_log_ui.py` | 통과 (합성 HTTP + 실제 엔진 fixture 183행, 1500/850/500px, JS 오류 0) |
| `python tests/ui/check_damage_audit_browser.py --real-replay <saved replay> --live …` | 통과. 아래 세 종류를 분리해 기록 |

브라우저 검증 종류(Edge headless):

- **합성 HTTP + 실제 저장 replay**: Director `artifacts/director/live-a751d113203748f5886aa7fabaf88679/ui-response.json`을 읽기 전용으로 route 응답에 사용. 풀버스트·버프 14건 타격.
- **합성 HTTP + 합성 경계**: 실제 계산기 terms 3건(legacy 크리+코어+풀버스트, nested 비풀차지, final_round_even 최소 피해)과 합성 버프 10종(미해석 type 999 포함).
- **실제 로컬 API**: 이 worktree에서 Release 빌드한 `Nikke.Api`를 임의 포트로 실행. Director 격리 복사본(`artifacts/b2/integration-bfe7311e…/data`)을 파일 복사한 **새 사본**을 데이터 루트로 사용, 크리 항상 적용으로 180초 실행. 크리+풀버스트 타격의 표시값을 응답 terms와 대조. 원본 복사본 `accounts.db`/`-wal` 해시 전후 동일. 사용자의 5181 서버와 원본 계정은 건드리지 않았다.

각 시나리오에서 카드(최종 공격력·공방차·P·방어력·최종 피해·정책)와 terms 표의 모든 결과값을 저장 원값과 수치 비교, 효과 행 수 = 버프 스냅샷 수, `+-`/NaN/undefined 없음, 회복을 %로 표시하지 않음을 검사했다. 1500/850/500px에서 문서·패널 가로 넘침 0(terms 표는 자체 가로 스크롤 영역 안), JS 예외 0.

증거(모두 git 제외 `artifacts/`): 최종 실행 `artifacts/ui/damage-audit/run-3fa47e7e41cd/summary.json`(5개 시나리오 통과, 실제 로컬 API는 157행 중 크리+풀버스트 타격 #15509, 최종 14,620,619 일치)과 `*-before-1500.png`(수정 전 코드), `*-after-{1500,850,500}.png`, `live-after-*.png`, `live-response.json`. summary의 `commit`은 기준 HEAD `77b3cce`, `dirty: true`는 이 커밋으로 들어간 미커밋 변경을 검증했다는 뜻이다. 단위 결과 `artifacts/ui/damage-audit/unit-final/unit-summary.json`. 합성 경계 fixture 생성기는 커밋하지 않은 임시 C# 콘솔(`HitCalculator.Compare` 호출)이며 출력만 `tests/ui/fixtures/`에 넣었다. 계정 원본 JSON·스크린샷은 커밋하지 않았다.

## 6. 미확인 범위와 잔여 위험

- 사용자 스크린샷의 실행(타격 #14900)은 로그가 없어 재생하지 못했다. 같은 type/basis 조합을 다른 실제 로그 두 개(저장 replay, 새 로컬 API 실행)와 합성 경계로 확인했다.
- type 14의 Integer/Percent 구분 필드가 로그에 없다(2절). 중첩 CharacterSkill·연결 함수의 슬롯은 저장 inputs에 그래프가 없어 함수 ID로만 표시한다. 둘 다 로그 스키마 한계이며, 필요하면 엔진/백엔드가 스냅샷에 function value type과 루트 슬롯을 추가해야 한다(이번 범위 밖, 코드 변경 없음).
- 엔진 계산 자체의 결함은 발견하지 못했다. 확인한 모든 행에서 terms 최종값 = 저장 damage였다. 정수화 정책·스냅샷 시점이 실게임과 맞는지는 기존과 같이 실측 전 잠정이다.
- 기존 `docs/damage-log-ui.ko.md`(편집 제외 파일)의 31행 "실제 필드 및 계산 근거 명시 매핑"은 필드 매핑만 다루고 검산 패널의 산식·효과 단위 규칙은 없다. 검산 패널 표시 규칙은 이 문서가 기준이며, Director가 해당 문서를 갱신할 때 이 문서를 링크하면 된다.
- 합성 미리보기(명시적 Mock)는 엔진 형태의 공격력 효과만 만들며 hit 입력 목록과 연결되지 않아 `반영 여부 미확인`으로 보인다. 실제 로그 검산 용도가 아니다.
