# E-BUG-1 엔진 — 수동 풀차지(UP형) 발사 모션 딜레이

2026-10-02. 엔진 구현·합성 회귀 검증 완료. Backend wire/저장·UI·독립 QA·원본 배포 완료와 구분한다. 리뷰(astra-6) 전이며 통과 전까지 Director에 최종 통과를 올리지 않는다.

## 근거·기준·보존

Director의 `alice-manual-charge-delay-2026-10-02.ko.md`와 `workflow-implement-review.ko.md`를 UTF-8로 끝까지 읽고 E-BUG-1만 수행했다. 시작 HEAD `1a86ec9`, tracked 변경 없음, 기존 untracked `package-lock.json` 1개. `git merge 2487bbd`로 일반 merge했고 **fast-forward, 충돌 0**이다. F2-E(방어력 자동 전환) 등 이전 엔진 커밋은 모두 보존된다.

변경 파일은 `src/Nikke.Engine/**`, 엔진 tests(`tests/Nikke.Core.Tests/**`), 이 문서뿐이다. Core 산술·Backend·UI·QA 파일은 수정하지 않았다. `package-lock.json`은 커밋하지 않는다. push·배포·새 worker 없음. 실제 사용자 실행 경로(`C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe`), 5180/5181, 원본 계정 DB·세션·캐시·EXE는 조회·변경·종료하지 않았다.

비교 실험에서 원본 `data/local`은 **공개 표 12개 파일만 이름으로 지정해 읽기**(`game-catalog.json`, `calculation/*`, `runtime/*`)하고 해시를 전후로 확인했다(변경 0). `accounts.db`·`sessions`·캐시는 열지 않았다. 이 PC의 전역 dotnet에는 global.json이 요구하는 SDK 10.0.400이 없어 원본 저장소의 프로젝트 로컬 `.tools/dotnet`(10.0.400) **실행 파일만** 호출했고, 홈·NuGet 캐시는 이 worktree의 `.tools`로 지정했다.

## 원인과 기각 가설

버그: UP형 차지 무기(앨리스)를 수동 풀차지로 쓰면 발사 간격이 자체 버스트(차지 시간 단축) 중 2F까지 줄었다. `TryFireCharge`의 수동 풀차지 분기가 재클릭 간격만 넣고 spotFirst를 넣지 않았다.

| 경로 | 발사 후 시퀀스 | 변경 |
|---|---|---|
| `IsOnlyFullCharge`(DOWN_Charge: 리버렐리오·네온 VE) | rate gate만 | **현행 유지** |
| `MaintainFireStanceSec > 0` | spotFirst + maintain | 현행 유지 |
| 자동 UP형 | spotLast + spotFirst | 현행 유지(아래 점검) |
| 수동 톡톡이 | spotFirst + 재클릭 | 현행 유지 |
| **수동 풀차지 UP형** | ~~재클릭만~~ → **spotFirst + 재클릭** | **변경** |

**기각 가설(포트폴리오 기록, 삭제하지 않음):** "수동 풀차지는 조준을 유지하므로 발당 spotFirst를 지불하지 않는다." 구 코드 주석과 `ControlMode.Manual` 설명이 이 가설이었다. 근거는 사용자가 수동 풀차지를 "조준 유지"로 이해한 것이었으나, 2026-10-02 사용자 설명(앨리스는 마우스를 누르고 있어도 발사되지 않고 **손을 떼야 발사**된다)과 피해 로그(221F → 223F → 225F → 227F …)에 의해 기각됐다. 수동 풀차지 = [발사(마우스 뗌) → 재조준 → 재클릭 → 차지]이며 톡톡이와 차이는 발사 시점(풀차지 도달 후)뿐이다. 반례 재현: 자체 버스트로 차지가 1F가 되면 구 규칙은 발사 간격이 재클릭 1F + 차지 1F = 2F로 붕괴했다(구 코드에서 실패하는 단위 테스트 참조). 구 코드 소스에는 주석으로 같은 기각 사유를 남겼다.

## 변경

- `Legacy/FiringModel.cs`, `Skills/SkillFiringModel.cs`(두 복사본, 실행 경로는 각각 `WeaponReplay`·`SkillReplay`): 수동 UP형 분기를 `else if (Style == Tap)` / `else`(풀차지)로 나누던 것을 하나로 합쳐 **`_spotFirstLeft = _spotFirstFrames; _reclickLeft = SampleReclickFrames();`**. 톡톡이와 풀차지가 같은 시퀀스를 공유하고, 차이는 발사 조건(`tap`이면 차지 게이트 없음)에만 남는다. enum 설명 주석도 새 규칙으로 정정.
- `Skills/SkillDefinitions.cs`·`Skills/SkillReplay.cs`: shot 추적 이벤트에 `SkillTrace.ShotIntervalFrames`(int?) 추가. 같은 캐릭터의 직전 shot과의 프레임 차이이며 첫 발과 shot이 아닌 이벤트는 null이다. 계산 경로·RNG·피해에는 영향이 없다(추적은 Trace 켜짐 + TraceLimit 안에서만 기록).
- 버전 상향(결과가 바뀌므로 fingerprint·캐시 키가 분리된다 — `PreparedCompute.RulesVersion`/`ImplementationVersion`이 이 상수를 사용):

| 항목 | 이전 | 현재 |
|---|---|---|
| SkillReplay | `p03.skills.5-defense-switch` | `p03.skills.6-manual-charge-delay` |
| TeamBurstController | `p04.team.5-defense-switch` | `p04.team.6-manual-charge-delay` |
| PreparedSkillReplay | `cpu-summary.4-defense-switch` | `cpu-summary.5-manual-charge-delay` |
| WeaponReplay(평타 참조, 같은 FiringModel 사용) | `p03.weapon-reference.3-boss-conditions` | `p03.weapon-reference.4-manual-charge-delay` |

HitCalculator/StatBuffCalculator/BossConditionResolver 버전은 산술이 안 바뀌어 유지한다. 이전 버전으로 저장된 입력·결과는 `PreparedCompute` 생성자의 `engine_or_rules_version_changed` 검사로 조회만 되고 재실행되지 않는다(기존 동작). 이전 결과를 새 규칙으로 조용히 바꾸지 않는다.

## 점검: 자동 UP형이 차지 단축에서도 매 발 [spotLast + spotFirst]인가

코드상 자동 분기는 발사 직후 무조건 `_spotLastLeft`·`_spotFirstLeft`를 채우며 차지 시간과 무관하다. 단위 테스트로 확인했다: 차지 속도 99%(1F 차지)에서도 모든 발사 간격이 정확히 12 + 12 + 1 = **25F**(두 모델), 정상 차지에서는 12 + 12 + 59 = 83F. 5인 비교에서 앨리스 자동 조작 결과가 수정 전후 **seed별 완전 동일**(아래)이다. 자동 경로는 수정 대상이 아니었다.

## 부수 효과(의도·가설 구분)

- 마지막 탄을 쏜 뒤 수동 재장전 개시가 spotFirst만큼 늦어진다(순서가 재클릭 → spotLast → spotFirst → 탄 확인이라 spotFirst가 재장전 앞에 소모된다). 톡톡이가 이미 같은 동작이었고, 수동 재장전은 엄폐 전이를 넣지 않는다는 기존 사용자 확정은 건드리지 않았다. **잠정 가설**이며 실게임 재장전 개시 시점은 검증하지 않았다.
- spotFirst(앨리스 0.2s = 12F)·재클릭([0.02, 0.028]s) 값은 기존 값 그대로다. 앨리스 수동 풀차지 실측 간격이 들어오면 이 값을 대조해야 한다(trace의 `ShotIntervalFrames` 사용).

## 검증

**새 단위 테스트 21개**(`tests/Nikke.Core.Tests/ManualChargeDelayTests.cs`), 합성 fixture(실게임 관측 주장 아님). 구 코드로 되돌린 상태에서 실행하면 **10개 실패·11개 통과**로, 실패는 수동 풀차지 관련 10개 전부이고 통과 11개는 자동·DOWN_Charge·톡톡이·maintain 회귀다.

| 항목 | 기대 간격(프레임) | 모델 |
|---|---|---|
| 수동 풀차지, 정상 차지 60F | 1(재클릭) + 12(spotFirst) + 59 = **72** (구 규칙은 spotFirst 없음) | 두 모델 |
| 수동 풀차지, 자체 버스트 1F 차지 | 1 + 12 + 1 = **14** (구 2) | 두 모델 |
| 수동 풀차지 1F 차지 == 톡톡이 | 전 발 동일 14 | 두 모델 |
| 톡톡이는 차지 시간과 무관 | 14 | 두 모델 |
| 자동 UP형, 1F 차지 | 25 | 두 모델 |
| 자동 UP형, 정상 차지 | 83 | 두 모델 |
| DOWN_Charge(수동·자동) | rate gate만 6 (10발/s) | 두 모델 |
| maintain형 | spotFirst + maintain + 1 | 두 모델 |
| 도중 차지 속도 변경(`ApplyRuntime`) | 72 → 14 → 72, 어느 구간에서도 ≥ 14 | SkillFiringModel |
| 재생 수준 trace | `ShotIntervalFrames` = 프레임 차이, 첫 발 null, shot 외 null | SkillReplay |
| 재생 수준 1F 차지 수동 풀차지 == 톡톡이, 자동 25, DOWN_Charge 6 | — | SkillReplay |

**Release 전체:** `Nikke.Core.Tests` **217/217**(기존 196 + 신규 21), `Nikke.Analysis.Tests` 41/41, `Nikke.Compute.Tests` 46/46, `Nikke.Sync.Tests` 164/164. 실패 0·skip 0. 버전 문자열을 단언하는 기존 테스트 3개(`BurstTacticTests`, `ClientFloatDamageTests`, `PreparedSkillReplayTests`)는 새 버전으로 갱신했다.

### 5인 180초 전후 비교

합성 계정(공개 표만 사용, Lv400, 장비·OL·큐브 없음) 리타·블랑·앨리스·누아르·모더니아, 10800프레임, DEF 30925 고정, `final_round_even`, 크리 표본, 코어 ON, Probe와 같은 자동 버스트 전술(앨리스 수동). 기준 = `2487bbd`(수정 전), 비교 = 이번 수정. 같은 persisted 입력을 두 엔진에 넣고 seed 1~20을 평균했다(seed가 같아도 앨리스의 재클릭 RNG 소비 수가 달라 다른 멤버의 크리 표본이 달라진다).

**앨리스 수동 풀차지(사용자 시나리오)** — 수치 변화는 의도된 것:

| 지표 | 수정 전 | 수정 후 | 변화 |
|---|---|---|---|
| 앨리스 발수 | 274.1 | 192.6 | −29.7% |
| 앨리스 피해 | 3.328e8 | 2.241e8 | −32.7% |
| 팀 총 피해 | 8.197e8 | 7.091e8 | −13.5% |
| 풀버스트 횟수 | 11 | 11 | 변화 없음 |
| 첫 풀버스트 시점(평균 프레임) | 227.3 | 228.2 | +0.9F (seed 1: 227 → 225) |
| 앨리스 최소 발사 간격 | 8F | 19F | |
| 앨리스 발사 간격 중앙값 | 9F | 20F | |

앨리스 발사 간격 분포(seed 1): 수정 전 8F×108·9F×71(자체 버스트), 80/81F(정상 차지); 수정 후 19F×73·20F×44(자체 버스트), 91/92F(정상 차지). 정상 차지에서 +11F는 spotFirst 12F − 선시작 차지 1F이다. 그 외 멤버 발수·피해는 ±1% 안(예: 리타 7.315e7 → 7.332e7, 누아르 1.633e8 → 1.618e8)으로 RNG 흐름·게이지 타이밍의 2차 영향이다. 이 합성 계정은 OL/큐브 차지 속도가 없어 자체 버스트 차지가 약 6F이므로 보고된 2F(차지 1F)는 단위 테스트(2F → 14F)가 재현한다.

**회귀(같은 seed, 수정 전후):** 톡톡이(앨리스 수동)와 자동(앨리스 자동) 모두 20개 seed에서 팀 피해·풀버스트 횟수가 **완전히 동일**, 평균 지표도 같다(톡톡이 앨리스 419.9발/1.058e8, 자동 150.8발/1.654e8).

비교 하네스는 저장소 밖(임시 폴더)에 두었고 커밋하지 않았다. 재현이 필요하면 `PreparedCompute`의 persisted 입력을 두 빌드에 넣는 방식이다.

## Backend·QA 후속(소유 밖, 수정하지 않음)

1. 새 trace 필드 `ShotIntervalFrames`가 Web JSON으로 노출되는 `SkillTrace` 직렬화에 추가된다(기본 null, 구 저장본 역직렬화 호환). 화면·저장 경계에서 표시할지는 Backend/UI 결정이다.
2. 저장된 이전 결과(특히 앨리스 수동 풀차지)는 구 규칙 값이며 조회만 된다. 새 요청은 새 버전·fingerprint로 계산된다. 앨리스 수동 풀차지를 쓰는 기존 통계·OL 비교 수치가 이 수정으로 **내려간다**(위 표). QA는 구/신 버전 결과가 섞여 비교되지 않는지 확인해야 한다.
3. 이전 버전 문자열이 남은 문서는 그 작업 당시의 역사 기록이다: `def-switch-engine.ko.md`(F2-E 버전표), `boss-distance-element-engine.ko.md`, `combat-conditions-cleanup-*.ko.md`, `single-deck-compute-contract.ko.md`의 `cpu-summary.4-defense-switch` 서술. 소유 밖이라 수정하지 않았다 — 현재 버전은 이 문서의 표를 따른다.

## 리뷰 이력

(아직 없음. 리뷰 통과 시 `통과`, 반려 시 `파일:줄 — 항목 번호 — 이유`와 수정 내용을 여기에 누적한다.)
