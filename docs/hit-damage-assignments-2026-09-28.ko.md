# 단일 히트 client_f32 구현·원천 조사 배정 — 2026-09-28

## 최신 상태 — 2026-09-28

- **H-SRC: 원천 조사 완료, Director 검토 수용.** [H-SRC 보고서](C:/Users/user/orca/workspaces/Nikke-Simul/Backend/docs/hit-damage-source-investigation.ko.md)(Backend `f4ab2fc`), 조사 스크립트 `tools/data-pipeline/investigate_hit_sources.py`, 증거 Backend `artifacts/hit-damage-source/evidence.json`(Git 제외). Director가 보고서 전문과 커밋 범위(보고서·스크립트 2파일, `src`/`apps` 변경 0)를 확인했다. 조사 스크립트 재실행은 하지 않았다. 결과 요약은 [클라이언트 공식 기록](hit-damage-client-formula.ko.md)의 H-SRC 절. 이는 읽기 전용 원천 조사 수용이며 실게임 대응 확정·실측 대조가 아니다. 클라이언트 질문 8개는 사용자 답변 대기.
- **H-SRC → H-F32 영향:** 잠정 `breakRate = 1 + PartsDamage`는 의미 대응이 틀릴 가능성이 높으나 `extra`가 합이므로 **수치는 동일**하다. 진행 중인 H-F32를 중단하지 않고, 저지 입력 신설·96 중복 제거는 클라이언트 확인 후 별도 후속으로 둔다. `statDamageRatio` 1, `defenceRatioRate` 0 기본값은 조사 결과와 일치한다.
- **H-F32: 엔진 독립 구현 완료, Director 검토 수용(당시 미통합 — 이후 2026-09-28 Director 통합). 2026-09-28 독립 QA 단계 A 통과 — [Q-F32 보고서](C:/Users/user/orca/workspaces/Nikke-Simul/검수/docs/client-f32-qa.ko.md)(검수 `cdca644`).** [H-F32 보고서](C:/Users/user/orca/workspaces/Nikke-Simul/시뮬레이션-엔진-담당/docs/hit-damage-client-f32.ko.md)(엔진 브랜치 `53b3d10`/`5ced15a`). Director가 `ClientFloatDamage`·`HitCalculator`·`OverloadProcessor`·`StatBuffCalculator` diff와 보고서 전문을 읽었다. 테스트 재실행은 하지 않았고, numpy로 전체 float32 경로 예시 4개를 따로 계산해 엔진 oracle 값(330000000, 366999968 등)과 일치를 확인했다.
  - 구현: checked `long` 공격력 그룹 조립(raw rate/10000 보존, 나머지 비교 사사오입, 음수 포함), 공방차 `long` 계산 후 float32 전환, 각 연산 float32 저장, `MathF.Round(AwayFromZero)`·`max(1)`·checked long. `StatDamageRatio`(1)/`DefenceRatioRate`(0) 입력 추가. `SkillReplay`/`PreparedSkillReplay` 기본 `client_f32`, 과거 후보 3개는 비교용 보존. HitCalculator `p02.4-client-f32`, InputSchemaVersion 3, 엔진·summary 규칙 버전 상승.
  - 엔진 보고 검증: Core/Engine Release 147/147, 독립 Python struct binary32 golden 10개 중간값 비트·피해 일치. 합성 5인 180초(DEF 30925): 팀 1,346,859,763 → 1,346,863,834(+4,071). 원인은 항별 floor 제거·최종 사사오입(예 172687.5 → 172688). 발수·명중·풀버스트 9회 동일. 합성 입력이며 실게임 수용 아님.
  - 동작 변화: 소수 native/DEF/고정량과 1/10000보다 정밀한 공격력 비율은 절삭 없이 **명시 거부**한다. 장탄·HP·DEF 조립은 기존 double 유지(장탄 전환 안 함).
  - 알려진 통합 영향: 로컬 API `/api/calculations/hit`가 schema 상수를 비교하므로 **기존 schema2 요청은 통합 시 거부**된다. API/Contracts/UI의 schema3·새 입력 연결, compute fingerprint·캐시 분리(Backend CPU 튜닝·통계 결과와 혼합 금지)가 필요하다. 1만회 측정(Q-CPU-10K)은 이 전환 후 기준으로 다시 잡아야 한다.
  - H-SRC 차이: break/parts 잠정 분해는 수치 동일, 의미 수정은 후속.
- **후속 배정:** 통합 연결(I-BE·I-UI)과 독립 QA(Q-F32) — [지시서](client-f32-integration-assignments-2026-09-28.ko.md). 2026-09-28 **모두 수용 완료**(QA `1abba9b`), Director 통합 완료, 원본 배포 전.

## 승인과 근거

2026-09-28 사용자가 다음 두 작업의 배정을 승인했다. 근거는 [클라이언트 분석 공식·사용자 결정](hit-damage-client-formula.ko.md)이다. 반드시 그 문서 전체를 먼저 읽는다. 관련 이력: [P02 정정·09-18 결정](p02-buff-correction.ko.md), [P02 검증](p02-verification.ko.md).

- **H-F32 (엔진 담당):** `HitCalculator`에 `client_f32` policy 구현. 공격력 조립 `long`, 대미지 경로 `float32`, 최종 반올림 사사오입.
- **H-SRC (Backend 담당):** `statDamageRatio`·`damageRatio`·`defenceRatioRate`·`breakRate` 등 공식 항의 원천 조사.

이 문서는 지시와 수용 조건이다. 구현·검수·배포 완료 보고가 아니다. 두 작업은 독립으로 착수한다. H-SRC 결과가 나오기 전 H-F32는 아래의 잠정 대응과 중립 기본값으로 구현하며, 조사 결과 반영은 후속 작업이다.

## 공통 기준·보존

- Director 문서는 `C:/Users/user/orca/workspaces/Nikke-Simul/Director/docs/`에서 읽기 전용으로 읽는다. Director worktree를 편집하지 않는다.
- 본인 worktree만 편집한다. 먼저 `git status`/`git log`로 현재 상태를 확인하고, 자기 완료 커밋과 기존 변경을 보존한다. reset/checkout/stash로 밀어내지 않는다. 미추적 `package-lock.json`은 보존·커밋 제외.
- 원본 계정 DB·세션·캐시를 복제·초기화·동기화·수정하지 않는다. 원본 EXE·바로가기·배포 경로와 5180/5181 서버를 변경·종료하지 않는다. 필요한 서버·결과는 자기 artifacts와 격리 포트만 사용한다.
- 게임 실행 파일 디컴파일·게임 프로세스 접근·후킹·새 데이터팩 수집은 하지 않는다. 클라이언트 코드 확인이 필요하면 **사용자에게 물어볼 구체적 질문**으로 보고한다. 사용자의 추정을 확정 사실로 기록하지 않는다.
- 원격 push, 배포, 새 Orca Run/Dispatch/하위 워커 생성, `worker_done` 사용 금지. 전역 권한·관리자·샌드박스 설정 변경 금지.
- 합성 산술 fixture, 기존 실측 대조, 실제 게임 관측을 구분해 보고한다. 테스트 통과를 실게임 정확성 수용으로 표현하지 않는다.
- 완료 시 Director 터미널을 `terminal list --worktree 'path:C:/Users/user/orca/workspaces/Nikke-Simul/Director' --json`으로 재확인한 뒤, 확정 커밋·보고서 절대 경로·검증 결과·미완료/질문을 `terminal send --terminal <handle> --text '<요약>' --enter --wait-submit 10 --json`으로 **한 번** 전달한다. 배정 시점 Director handle은 `term_73afed41-4bf2-4551-8ed4-01c8a64e47bc`. stale이면 재조회하고 임의 셸에 보내지 않는다. 무응답 재전송 금지.

## H-F32 — 시뮬레이션 엔진 담당

worktree: `C:/Users/user/orca/workspaces/Nikke-Simul/시뮬레이션-엔진-담당` (브랜치 `시뮬레이션-엔진-담당`, 기준 `87099e1`, 구현 `0d23366` 포함).

소유: `src/Nikke.Core/**`(Stats·Combat), `src/Nikke.Engine/**`, 엔진/Core 전용 tests, 자기 보고서 `docs/hit-damage-client-f32.ko.md`. API/Contracts wire·Storage·Analysis·UI·QA 파일은 수정하지 않는다. 그쪽 연결이 필요하면 필요한 변경과 근거를 보고한다.

1. **공격력 조립 `long`.** `OverloadProcessor.CalculateFinalBaseStat`·`StatBuffCalculator` 등 공격력 조립을 부호 있는 `long` 정수 경로로 전환한다. `기본값 + Σ round(기본값 × 동일 버프율 × 개수)` 그룹 규칙·사사오입·고정 부여 순서를 유지한다. 원천 1/10000 비율은 정수로 보존하고 더 정밀한 입력을 조용히 자르지 않는다. 위험 연산에 `checked`. 장탄 조립은 09-18 결정 범위이나 이번 작업에서 함께 바꿀지 여부는 영향 범위를 보고한 뒤 결정한다(무단 확대 금지). 차지 시간 1/100초 정수 연산은 보존한다.
2. **`client_f32` policy.** 공식 표기 순서대로 각 연산 결과를 명시적 `float` 캐스트로 보관한다.
   - `base = (float)(attack − defence) × damageRatio × statDamageRatio × chargeDamageRate` (`long` 차이를 `float32`로 변환하는 지점을 보고서에 명시).
   - `B = 1f`; crit → core → burst → range 순서로 `B = (float)(B + (float)(rate − 1))`. 비활성 조건의 rate는 1.
   - `extra = breakRate + addDamageRate − 1`.
   - `candidate = max(1, MathF.Round(base × B × extra × (1 − damageReductionRate) × (1 − defenceRatioRate) × elementRate, MidpointRounding.AwayFromZero))`.
   - 비유한값(NaN/Inf)과 최종 `long` 변환 범위 초과는 예외로 탐지한다. 2^24 이상의 `float32` 정수 해상도 저하는 재현 대상이지 오류가 아니다.
3. **잠정 항 대응** (H-SRC 결과 전, 보고서에 잠정으로 표시): `damageRatio` = 현 `Coefficient`; `statDamageRatio` 입력 추가, 기본 1; crit/core/burst/range rate = `1 + CritBonus/CoreBonus/BurstBonus/DistanceBonus`; `addDamageRate` = 현 B3에서 parts를 뺀 값, `breakRate` = `1 + PartsDamage`(parts 적중 시) — 현 B3와 합이 같음; `damageReductionRate` = `−(DamageTaken + distribution)`; `defenceRatioRate` 입력 추가, 기본 0(필수 항, 최근 업데이트 기믹); `elementRate` = 현 B5. true 대미지의 DEF 0 처리는 유지한다.
4. **기본 경로 전환.** 정밀 실행(`SkillReplay`와 CPU summary용 `PreparedSkillReplay` 등 엔진 런타임 전 경로)의 기본 policy를 `client_f32`로 전환하고 기존 `legacy_term_floor`/`final_round_even`/`nested_floor`는 비교 후보로 유지한다. `HitCalculator.Version`/rules version을 올려 버전 기반 캐시·결과가 섞이지 않게 한다. 입력 계약(`InputSchemaVersion`) 변경 필요 여부와 API/UI 영향은 보고한다.
5. **검증.**
   - 14.5% 경계(기본 100·0.145·1개 → 115), 동일 비율 그룹·중첩(0.014×2 → 103), 서로 다른 비율(0.014·0.013 → 102), 음수 효과, `checked` overflow 탐지.
   - `float32` B 누적: 제품 코드와 독립인 기대값(예: numpy `float32` 또는 손계산 bit 표현)으로 대조. 참고 합성값: rates 1.5/2.0/1.5/1.3 → B `3.2999999523`. 
   - 사사오입 경계(x.5 → 0에서 먼 쪽), `max(1)`, `defenceRatioRate` 0/양수, `statDamageRatio` 1/≠1, NaN/Inf·범위 초과 탐지.
   - 기존 회귀 전체와 기준 replay(기존 5인 180초 입력)의 전환 전후 팀·니케별 피해 차이를 보고한다. 차이 발생 자체를 실패로 보지 않되 원인을 설명한다.
6. SW 단일 타격 검사는 이번 범위가 아니다. 단, 새 경로에서 `long` 조립 overflow·`float32` 비유한값·최종 변환 범위를 검사할 수 있는 fixture 진입점을 남긴다.

완료 조건: 확정 커밋, 보고서, 위 검증 결과(합성/기존 실측/미실행 구분), 잠정 대응 목록, API/Contracts/UI/Backend 후속 필요 사항을 Director에 한 번 인계.

## H-SRC — Backend 담당 (원천 조사)

worktree: `C:/Users/user/orca/workspaces/Nikke-Simul/Backend` (브랜치 `Backend`, 기준 `d8be9d3`, 제품 `40078d0`).

소유: 자기 보고서 `docs/hit-damage-source-investigation.ko.md`, 조사용 읽기 전용 스크립트(`tools/data-pipeline/` 아래 새 파일 또는 자기 artifacts). 제품 코드(src/**)·UI·엔진 파일은 수정하지 않는다.

1. 공식의 각 항이 **어떤 원천 필드·테이블 값**에 대응하는지 조사한다: `damageRatio`, `statDamageRatio`(사용자 추정: 스킬 대미지 계수 — 확정 아님), `chargeDamageRate`, `breakRate`, `addDamageRate`, `damageReductionRate`, `defenceRatioRate`(최근 업데이트 기믹), `elementRate`, crit/core/burst/range rate.
2. 조사 범위: 저장소 추적 자료와 버전 고정 게임 카탈로그, 기존 디코딩 테이블(ConfigBattle·CharacterSkillTable·FunctionTable 등 P02 조사 대상), 설치 경로 데이터팩의 **읽기 전용** 확인, 고정 upstream(nikke-calc) reference, 공개 자료. 게임 파일을 수정·재수집하지 않는다. 계정 원천 데이터는 필요한 경우에도 개인 식별 정보 없이 필드 구조만 인용한다.
3. 각 항에 대해: 대응 후보 필드/값, 근거(파일·키·예시 값), 신뢰도(확인/유력/추정/불명), 현재 `HitContext`의 어느 입력과 대응하는지, 기본값을 기록한다. `statDamageRatio`와 `damageRatio`가 각각 무엇인지 구별한다. `defenceRatioRate`는 적용 보스·조건·값의 원천을 찾는다.
4. damageTaken·distribution·parts·pierce·dot·sequential·true 대미지가 공식의 어느 항에 들어가는지에 대한 근거를 정리한다.
5. 원천으로 결론이 나지 않는 항목은 **사용자가 클라이언트 코드에서 확인할 구체적 질문**(찾을 심볼·필드명·확인할 연산)으로 정리한다.
6. H-F32의 잠정 대응(위 3항)과 조사 결과가 다르면 차이를 명시한다. 엔진 코드를 직접 고치지 않는다.

완료 조건: 확정 커밋, 보고서, 항별 대응표·근거·신뢰도, 사용자 질문 목록을 Director에 한 번 인계.

## 이후 순서

H-SRC 결과로 잠정 대응을 확정·수정 → H-F32 반영 → 기존 실측 단일 히트 대조로 반올림 판정(오차 지속 시 다른 반올림 실험) → 독립 검산 도구·QA 수용 → SW 단일 타격 검사 → API/UI 연결·Director 통합·원본 배포. 각 단계는 별도 지시다.

## 전달 확인

Orca app 1.4.215, runtime `a0bed151-149f-486b-a796-53848c05acdc`. 지시서 커밋 `4fa7e16`. 이전 runtime의 handle 목록을 재사용하지 않고 `terminal list`로 재조회했다.

| 담당 | 터미널 | 요청 ID | 착수 근거 |
|---|---|---|---|
| H-F32 엔진 | 기존 `term_5e3783c1-9520-4d7b-be57-f6c74d2cf6de` (codex 세션 재개) | `cc3e0620-23c9-4b7a-97c4-5c41458ffed6` | accepted=true, `input_accepted`·`turn_started` |
| H-SRC Backend | 신규 `term_e5d05982-dabd-4b09-9242-c75d3d7b6010` (codex, GPT-6-Astra high) | `c965a78f-871b-46e9-ba02-4f09b89c441c` | accepted=true, `input_accepted`·`turn_started` |

- 엔진 터미널은 Codex 업데이트 안내에서 멈춰 있어 `2`(Skip) 한 글자만 입력한 뒤, 세션 재개·idle 확인 후 지시를 보냈다. Codex 업데이트는 하지 않았다.
- Backend worktree에는 현 runtime의 터미널이 없어 `terminal create --command codex`로 새 agent 터미널 하나를 만들었다. 새 worktree·Run/Dispatch·하위 워커는 만들지 않았다.
- 검수·UI·통계 터미널에는 보내지 않았다. 검수 담당은 Q-CPU-10K 재개 조건 대기 상태를 유지한다.

이 기록은 착수 확인이며 구현·조사 완료나 수용 통과가 아니다. 원본 EXE·계정 데이터는 변경하지 않았다.
