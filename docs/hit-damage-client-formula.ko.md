# 단일 히트 대미지 — 클라이언트 분석 공식

작성: 2026-09-27. 갱신: 2026-09-28 사용자 결정 반영. 상태: **정보·결정 기록 완료 / 코드·테스트·배포 미변경 / 실측 대조 전**.

## 출처와 신뢰 범위

사용자가 게임 클라이언트 분석(클뜯)으로 확인한 **대미지 한 틱** 계산식을 2026-09-27 대화에서 전달했다. Director는 클라이언트 바이너리·게임 프로세스를 직접 분석하지 않았고 아래 식을 독립 검증하지 않았다. 클라이언트 버전, 클래스·메서드 이름, 각 변수의 자료형과 원천 필드는 아직 기록되지 않았다.

이 공식은 기존 [P02 데이터팩 조사](p02-verification.ko.md)에서 찾지 못한 정수화 위치·연산 순서에 대한 **클라이언트 유래 근거**다. 실게임 관측 대조를 대신하지 않으며, 확인 전 결과는 계속 provisional로 둔다.

## 전달받은 공식 (원문 그대로)

```text
base = (attack − defence)
       × damageRatio × statDamageRatio × chargeDamageRate

B = float32(1)
criticalDamageRate, coreDamageRate, burstDamageRate, bonusRangeRate 순서로:
    B = float32(B + float32(rate − 1))

extra = breakRate + addDamageRate − 1

candidate = max(1, round(
    base × B × extra
    × (1 − damageReductionRate)
    × (1 − defenceRatioRate)
    × elementRate
))
```

## 사용자 결정 — 2026-09-28

1. **대미지 경로는 `float32`, 공격력 조립은 `long`.** 공격력(기본값 + 버프 그룹별 반올림 + 고정 부여)은 부호 있는 `long` 정수 경로로 계산하고, 그 이후 `base`·`B`·`extra`·감소/속성 배율·최종 곱은 `float32`로 재현한다. `long` → `float32` 변환 지점과 곱셈 순서는 위 공식의 표기 순서를 기본으로 하며, 클라이언트 확인 결과가 다르면 그것을 따른다.
2. **최종 `round`의 기본은 사사오입(0.5는 0에서 먼 쪽, `MidpointRounding.AwayFromZero`).** 현재 p02.3 `final_round_even`의 ToEven과 다르다. 실측 대조에서 오차가 지속적으로 발생하면 ToEven·`(long)(x + 0.5)` 등 다른 방식을 **실험 후보**로 비교한다. 실험 후보를 근거 없이 기본값으로 바꾸지 않는다.
3. **`defenceRatioRate`는 추가 필수.** 사용자 확인: 최근 업데이트 이후 생긴 기믹이다. 입력 기본값은 0(효과 없음)으로 두되, 어떤 보스·조건에서 어느 값이 적용되는지는 원천 조사 대상이다.
4. **`statDamageRatio`는 조사 대상.** 사용자 추정은 "스킬 대미지 계수"이며 확정이 아니다. 이 추정이 맞으면 현재 `Coefficient`에 대응시킨 `damageRatio`의 의미도 함께 재확인해야 한다. 조사 전에는 기본값 1로 두고 추정값을 계산에 넣지 않는다.

`float32` 재현에서 약 16,777,216(2^24) 이상 값의 정수 해상도 저하는 게임 동작의 재현이며 오류로 취급하지 않는다. 반대로 `long` 공격력 조립의 overflow와 최종 정수 변환의 범위 초과는 탐지해야 한다.

## 현재 구현(`HitCalculator` p02.3)과의 대응

현재 구현: `src/Nikke.Core/Combat/HitCalculator.cs`. 대응은 Director의 해석이며, 이름이 같아 보여도 원천 필드 확인 전에는 동일 항으로 확정하지 않는다.

| 공식 항 | 현재 구현 | 판정 |
|---|---|---|
| `attack − defence` | `attack − defense` (true 대미지는 DEF 0) | 대응 |
| `damageRatio` | `Coefficient` | 대응 |
| `statDamageRatio` | 없음 | **누락** — 사용자 추정: 스킬 대미지 계수. 조사 대상 |
| `chargeDamageRate` | `charge = base × (1 + 배율 증가분) + 가산` | 대응 |
| `B` (crit→core→burst→range, `float32` 누적) | `1 + Σbonus` (double, distance→burst→crit→core) | **정밀도·누적 순서 다름** |
| `extra = breakRate + addDamageRate − 1` | B3 = `1 + attackDamage + pierce + parts + dot + sequential + true` | 합산 구조 유사. `breakRate`와 parts 대응 미확인 |
| `1 − damageReductionRate` | B4 = `1 + damageTaken + distribution` | 받는 대미지 증가가 음수 reduction이면 동등. distribution 위치 미확인 |
| `1 − defenceRatioRate` | 없음 | **누락** — 최근 업데이트 기믹, 추가 필수(결정 3) |
| `elementRate` | B5 | 대응 |
| `max(1, round(…))` | `final_round_even`: 마지막 ToEven 반올림, 최소 1 | 구조 대응. tie 처리는 사사오입을 기본으로 결정(결정 2) — 구현 변경 필요 |

## 기존 판단에 미치는 영향

- **정수화 후보:** 공식에 중간 floor가 없으므로 `final_round_even` 구조와 일치한다. 이 공식이 확인되면 항별 floor인 `legacy_term_floor`, 단계별 floor인 `nested_floor`는 탈락 후보가 된다. 실측 대조 전에는 후보를 삭제하지 않는다.
- **2026-09-18 `long` 고정소수점 결정 조정:** 게임이 B를 `float32`로 누적하므로 대미지 경로에 정확 산술을 적용하면 게임과 다른 값을 낸다. 2026-09-28 결정 1로 **공격력 조립만 `long`, 대미지 경로는 `float32`**로 정리했다. [P02 정정 기록](p02-buff-correction.ko.md)의 09-18 결정 중 대미지 배율·중간값 부분은 이 결정으로 대체된다.
- **SW 단일 타격 overflow 검사:** `long` 공격력 조립의 overflow, `float32` 경로의 비유한값(Inf/NaN), 최종 정수 변환 범위를 검사하는 것으로 범위를 다시 정의한다. `float32` 정밀도 손실 자체는 재현 대상이다.

### float32 누적 영향 (합성 산술 예시)

아래는 Director가 numpy `float32`로 B만 재현한 합성 계산이며 실게임 관측이 아니다. rate를 float32로 변환한 뒤 `rate − 1`을 계산했다. base를 1e8로 가정하고 double 결과와 최종 반올림 차이를 비교했다.

| crit / core / burst / range | float32 B | double B | 최종 차이 |
|---|---:|---:|---:|
| 1.5 / 2.0 / 1.5 / 1.3 | 3.2999999523 | 3.3 | −5 |
| 1.5 / 2.0 / 1.0 / 1.3 | 2.7999999523 | 2.8 | −5 |
| 1.87 / 2.0 / 1.5 / 1.3 | 3.6699998379 | 3.67 | −16 |
| 1.5 / 1.0 / 1.0 / 1.0 | 1.5 | 1.5 | 0 |

발당 정확 일치를 목표로 하면 무시할 수 없는 차이다. 피해가 클수록 절대 차이가 커진다.

## 클라이언트에서 추가 확인할 항목

1. `base`, `extra`, 최종 곱의 자료형(`float32`/`double`). 전부 `float32`이면 약 16,777,216을 넘는 피해는 정수 해상도가 떨어진다(2·4·8… 단위). 기존 큰 실측 피해값이 모두 짝수인지로 교차 확인할 수 있다.
2. 실제 곱셈 순서. 부동소수점은 결합 순서에 따라 결과가 달라진다.
3. `round` 종류: `Mathf.Round`/`Math.Round`(ToEven), AwayFromZero, `(long)(x + 0.5)` 등. 확인 전 기본은 사사오입(결정 2).
4. `attack` 조립 경로(OL·버프 적용 공격력)의 자료형과 정수화 위치, `float32`로 넘어가는 지점. 결정 1에 따라 조립은 `long`으로 구현한다.
5. `statDamageRatio`(사용자 추정: 스킬 대미지 계수)와 `damageRatio`의 실제 의미, `defenceRatioRate`를 적용하는 보스·조건과 값, `breakRate`의 의미와 기본값. damageTaken·distribution·parts·pierce·dot·sequential·true 대미지가 각각 어느 항에 들어가는지.
6. `rate`의 원래 자료형(예: `1.5f`)과 `rate − 1`의 계산 자료형.
7. 출처 기록: 클라이언트 버전, 클래스·메서드 이름.

## 후속 작업

2026-09-28 아래 1·2를 배정했다: [H-F32·H-SRC 지시서](hit-damage-assignments-2026-09-28.ko.md). 3·4는 미배정이다.

1. `HitCalculator`에 `client_f32` policy 추가: `long` 공격력 조립 → `float32` 대미지 경로 → 사사오입 `max(1, round)`. 기존 후보는 비교용으로 유지한다. `defenceRatioRate`(기본 0)는 필수로, `statDamageRatio`(기본 1)는 조사 결과 전까지 중립값 입력으로 추가한다. 입력 계약 버전 변경 여부는 구현 시 결정한다.
2. `statDamageRatio`·`damageRatio`·`defenceRatioRate` 원천 조사를 담당자에게 배정한다. 사용자 추정을 확정 사실로 전달하지 않는다.
3. 기존 실측 단일 히트와 대조해 정수화를 판정한다. 독립 검산 도구(`tools/damage-calibration/analyze.py`)에도 같은 후보를 별도 산술로 추가한다. 오차가 지속되면 반올림 방식 실험(결정 2).
4. SW 단일 타격 검사를 재정의된 범위(위 영향 절)로 수행한다.

이번 기록에서는 코드·테스트·원본 계정·캐시·서버·EXE를 변경하지 않았다.
