# UI 피해 검산 표시 수정 — Opus 5 인계

사용자 요청: 발당 피해 검산 패널의 잘못된 산식, 이름 없는 `효과 + ...%`, 비정상적으로 큰 퍼센트를 수정하고 효과명과 수치를 점검한다. 담당은 기존 UI 작업공간의 Claude Opus 5, effort high, bypass permissions 세션이다. 이 문서는 작업 범위이며 완료 증거가 아니다.

## 작업 위치와 보존 경계

- 작업공간: `C:/Users/user/orca/workspaces/Nikke-Simul/UI`. 기존 워커 handle `term_818b41f3-3b0b-475f-83cc-db252fb90e38`.
- 현재 UI HEAD `99dfa2f`, Director HEAD `77b3ccecd352a592ddc9f8e0bbf09bf03a730085`. 시작 시 적용 AGENTS.md/README/관련 계약과 git status를 확인한다. 안전한 경우 자신의 UI 브랜치만 위 Director 기준으로 `git merge --ff-only`한다. 충돌/사용자 변경 시 강제 reset/stash/checkout하지 말고 보고한다. 기존 untracked package-lock.json을 보존한다.
- Director에는 검증 완료·미커밋 버스트 설정 단순화 변경이 있다. 이를 복사하거나 덮어쓰지 않는다. 특히 `app.js`, `burst-tactics.js`, `tests/q3/check_ui_contract.mjs`, `check_integrated_live.py`, 기존 `check_damage_log_ui.py`, 기존 `docs/damage-log-ui.ko.md`, README는 이번 워커 편집 대상에서 제외한다. 현재 UI 규칙은 Director의 `docs/damage-log-ui.ko.md` 상단을 읽기 전용으로 참조한다. 제거된 버스트 옵션을 되살리지 않는다.
- 편집 소유: `apps/desktop-ui/damage-log.js`, `damage-log-adapter.js`의 피해 로그 표시/변환 부분, 필요한 최소 전용 스타일, 새 전용 테스트 파일과 `docs/ui-damage-audit-fix.ko.md`. 어댑터의 버스트 DTO 변환은 유지한다. 불가피하게 제외 파일 변경이 필요하면 파일과 이유를 보고한다.
- 엔진/Core/API/DB 원본과 기존 저장 로그는 수정하지 않는다. UI 표시를 맞추려고 실제 피해를 재계산해 원본 결과를 대체하지 않는다. 원본 계정·현재 5181 서버·타 worktree·기존 artifacts를 변경하지 않는다. 자신의 새 artifacts에서 합성 fixture나 읽기 전용 실제 로그로 검증한다. push/배포/.exe 빌드, 추가 워커 생성은 범위 밖이다.

## 사용자 재현과 확인한 원인

첨부 원본: `C:/Users/user/AppData/Local/Temp/orca-paste-1789134506948-66a38d2a-cb05-4cfb-a96e-dbf80ae1056e.png` (읽어서 확인).
화면: 타격 #14900, 발사 #14899, 49.95초, 기초 공격력 144863, 버프 적용 공격력 337831, 방어력 30925. 버프 목록에 누아르 공격력 +1719100%, 블랑 효과 +13166685%, 효과 +16577073%, 앨리스 효과 +1000%, 누아르 효과 +400% 등 표시. 스크린샷만으로 원본 effect 값/단위를 확정하지 말 것.

확인된 코드:

- `damage-log-adapter.js`: effect.type 1/61 이외 대부분을 '효과'로 표시하고 effect.value를 그대로 전달한다. source는 `니케 #ID`, basis/stacks는 화면 의미에 반영하지 않는다.
- `damage-log.js`: 모든 activeBuff 값에 `Math.round(value * 100)%`를 붙인다. 고정 공격력/HP/시간/정수 상태 값도 퍼센트로 오표시할 수 있다. 잔여 0이나 알 수 없는 지속시간을 상시로 표시할 위험도 확인한다.
- `src/Nikke.Engine/Skills/SkillReplay.cs`: type 1 시전자 기반 부여는 `native_caster_flat_at_application`, type 61 시전자 차지시간 부여는 `caster_charge_centiseconds`, type 2는 `caster_final_max_hp_at_application` 등으로 값과 basis를 다르게 저장한다. raw를 무조건 10000으로 나누는 것도 잘못이다.
- `src/Nikke.Engine/Skills/SkillDefinitions.cs`: SkillEffectView에는 Source/Target/FunctionId/GroupId/Type/Value/Stacks/ExpiresAt/Basis가 있다. `DamageLog.cs`의 snapshot 및 실제 직렬화 필드도 읽는다.
- `src/Nikke.Core/Combat/HitCalculator.cs`: P=(effectiveAttack-effectiveDefense)*coefficient*charge. 거리/풀버스트/크리/코어는 같은 가산 보너스 묶음이다. legacy_term_floor는 floor(P)와 floor(P*각 보너스)의 합 B2, 이후 B3/B4/B5를 곱하고 최종 내림한다. final_round_even/nested_floor는 정수화 위치가 다르다. UI의 '크리배율 × 코어배율 × 풀버스트배율 후 정수화'는 실제 구현과 불일치한다. 최소 피해/방어 무시/비풀차지 경로도 확인한다.

## 구현 요구

1. 기존 공식 자료와 런타임 의미를 따라 효과별 한국어 이름·단위를 매핑한다. 비율(%), 고정 공격력/HP, 탄 수, 시간, 스택/상태/식별자를 분리한다. 부호와 소수 정밀도를 보존하며 음수에 '+-'를 붙이지 않는다. 모르는 효과는 '미해석 효과(type ID)'와 원값/basis로 명시하고 추측으로 %를 붙이지 않는다.
2. 출처 니케 이름과 가능한 스킬/함수 식별 근거를 표시한다. 자료가 없으면 슬롯/스킬명을 지어내지 않고 functionId 등 확인 가능한 식별자를 남긴다. 시전자 기준과 수혜자 기준, 스택당/총량을 실제 엔진 적용 코드로 확인한다. 이름 매핑 실패는 명시적 ID fallback을 유지한다.
3. '현재 활성 효과'와 '이 타격의 피해 계산에 실제 반영된 항목'을 구분한다. 차지속도/탄약/보호막/회복 등을 모두 직접 피해 배율처럼 표현하지 않는다. 로그로 입증할 수 없는 기여도는 확정 표시하지 않는다.
4. 계산식과 숫자 카드를 저장된 hit/calculation.terms에 맞춰 수정한다. 가산/승산 그룹, 각 정수화 단계, 실제 최종 피해를 확인할 수 있게 한다. baseAttack/effectiveAttack/charge 등의 fallback과 null을 점검하고 미확인 값을 0/1로 정상값처럼 위장하지 않는다. 계산 근거가 없으면 미제공으로 표시한다. 큰 새 설정 UI나 불필요한 기능은 추가하지 않는다.
5. 실제 엔진 계산 자체의 문제를 발견하면 UI 임의 보정 대신 최소 재현과 근거를 별도 보고한다. 저장 JSON/CSV 원문 다운로드 동작·로그 스키마·원본 수치는 유지한다.

## 완료 조건과 증거

- 실제 SavedSkillReplay fixture에서 고정 수치/비율/HP/시간/스택 등을 확인하고, 필요하면 별도 명시적 합성 경계 fixture를 추가한다. 사용 가능 실제 로그 예: Director `artifacts/director/live-a751d113203748f5886aa7fabaf88679/ui-response.json` (읽기 전용; 사용자 스크린샷의 동일 run은 아님).
- 독립 단위 테스트: 단위별 변환, type+basis 차이, 출처 이름/ID fallback, 소수/음수/0/null/알 수 없는 type, 지속시간 상시/만료/미확인, 스택 중복 곱 방지, HTML escape, 크리+코어+풀버스트 가산 묶음, 정수화 3정책, 비풀차지/최소 피해/누락 terms.
- 실제 브라우저에서 패널 열기 및 수정 전후 화면 증거, 표시값과 원본 terms/final damage 대조. 1500/850/500px에서 가로 넘침·JS 예외 검사. 합성 HTTP와 실제 API 검증을 구분한다. 기존 UI fixture/Q3 회귀도 가능한 범위에서 실행하되 제외 파일을 테스트 통과 목적으로 변경하지 않는다.
- 새 문서에 타입/basis→이름/단위 근거, 예시 원값→표시값, 산식 수정 근거, 실행한 명령/실제 결과, 미확인 범위를 기록한다. raw JSON/이미지의 개인 데이터를 Git에 넣지 않는다.
- 자신의 관련 변경만 커밋하고 결과 커밋·파일·테스트·증거 경로·잔여 위험을 보고한다. 승인된 구현/테스트를 위해 사용자에게 재확인을 묻지 않는다. 범위 밖 권한이나 실측 부재는 보고하되 UI 표시 수정 자체를 불필요하게 멈추지 않는다.
