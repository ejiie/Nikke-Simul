# 전투 조건 정리·보스 선택 — F-COND-2 배정 (2026-09-29)

## 최신 상태

- **F2-E: 완료, Director 검토 수용.** 엔진 `d090641`(구현) → `1a86ec9`(기록), `e98db6a` ff 위. [보고서](C:/Users/user/orca/workspaces/Nikke-Simul/시뮬레이션-엔진-담당/docs/def-switch-engine.ko.md). 변경은 Engine·엔진 tests·보고서뿐(Api·Data·Contracts·apps 0), Backend `97ba7bf`와 충돌 없이 merge된다. Director가 `src/Nikke.Engine/DefenseMode.cs`를 읽었다: `fixed`(생략 시 기본, 구 `EnemyDefense` 재현)와 `team_damage_threshold`, 누적 ≤ 20억이면 유지, 초과시킨 타격은 이전 DEF로 계산하고 다음 타격부터 31784.
  - 엔진 보고 검증: Core/Engine 196/196(기존 174 + 신규 22). 정확히 20억 무전환, 20억+1, 같은 프레임 멤버·추가타·SG 펠릿, Frame 0, 고정 경로, 팀 합, 자동 버스트, summary·병렬·취소. 기존 5인 180초 client 1,346,863,834 / legacy 1,346,859,763 동일.
  - 결과 계약: `SkillReplayResult.Defense`·`SkillRunSummary.Defense`(Mode·InitialDefense·FinalDefense·DamageThreshold·SwitchAfterHit — Frame·HitTraceId·HitOrdinal·CharacterId·Effect·CumulativeDamage·Previous/NewDefense), trace `defense_switch`. 버전 `skills.5-defense-switch`·`team.5-defense-switch`·`cpu-summary.4-defense-switch`.
  - Backend 후속(엔진 보고): 새 요청에 자동 모드 명시·구 fixed 저장 호환, `PreparedCompute.Create`의 fixed 라벨 수정, `PreparedCompute.Run`에서 새 `result.Defense`를 Contracts·저장 DTO로 전달(현재 매핑 없음). 다중 정책 `WeaponReplay` 참조는 자동 모드를 거부하므로 SkillReplay를 써야 한다.
- **F2-B:** 진행 중. 엔진 `1a86ec9` merge 통지(2026-09-29). **F2-U:** 진행 중(mock).

## 근거

[사용자 요구 사항 R1~R8](user-requests-2026-09-29.ko.md)을 한 번에 처리한다(사용자 지시). 요구 원문·해석은 그 문서를 따른다. 보스 선택(R8)은 **표시만** 한다(사용자 선택, 2026-09-29): 이름·이미지 선택과 저장까지이며 약점·거리 등 전투 반영은 보스별 데이터가 준비되면 다음 단계에서 한다. 더미 보스 = 현재 동작.

Nikke-Local-Lab(사용자 비공개 프로젝트)의 UI·통계를 참조한다. **코드·UI를 가져와도 출처 표기를 남기지 않는다**(사용자 지시). 원격 저장소 또는 `C:/Users/user/Documents/GitHub/Nikke-Local-Lab.zip`을 읽기 전용으로 참조한다.

## 공통 기준

[client_f32 통합 지시서](client-f32-integration-assignments-2026-09-28.ko.md)의 "공통 기준·보존"을 따른다. 기준 커밋은 Director `e1ea771` 이후 HEAD(= 원본 `main`, 2026-09-29 배포본). 먼저 자기 브랜치에 일반 merge한다. **사용자가 원본 배포본을 사용 중이다** — 5180/5181·원본 경로 프로세스·원본 `data/local`을 건드리지 않는다. 완료 시 Director 터미널에 한 번 인계한다(배정 시점 handle `term_73afed41-4bf2-4551-8ed4-01c8a64e47bc`, stale이면 재조회).

## F2-E — 엔진 (R4 방어력 자동 전환)

소유: `src/Nikke.Core/**`, `src/Nikke.Engine/**`, 엔진 tests, 보고서 `docs/def-switch-engine.ko.md`.

1. 새 방어력 모드: 전투 시작 DEF 30925, **덱 팀 누적 대미지가 2,000,000,000을 초과한 뒤의 타격부터** DEF 31784. 누적은 모든 멤버·모든 대미지 종류의 확정 피해 합이다. 20억을 넘기게 만든 타격은 30925로 계산한다. 같은 프레임 여러 타격은 기존 프레임 내 처리 순서를 따른다. 이 경계 처리는 **잠정 가설**로 보고서에 남긴다(두 값·임계값은 기존 실측 근거, 경계 세부는 미확정).
2. 전환 시점(프레임·타격 ID·누적값)을 결과·trace에 남긴다. `SkillReplay`·CPU summary(`PreparedSkillReplay`) 모든 경로에 적용한다.
3. 기존 고정 DEF 경로는 비교·구 결과 재현용으로 유지한다. 규칙 버전을 올려 fingerprint·캐시가 분리되게 한다.
4. 검증: 누적이 20억 미만으로 끝나는 전투(전환 없음), 정확히 20억에 도달(전환 없음 — 초과가 아니므로), 20억을 넘는 타격 직후 전환, 같은 프레임 다중 타격, 기존 고정 DEF 결과 정확 재현, 팀 합 = 구성원 합.

## F2-B — Backend (조건 wire·보스 목록·고정값)

소유: Api·Contracts·Data·Compute·Jobs·Storage, `tools/data-pipeline/**`, Backend tests, 보고서 `docs/combat-conditions-cleanup-backend.ko.md`.

1. 엔진 커밋 통지 후 일반 merge하고 R4 방어력 모드를 replay·compute 조건 wire에 연결한다. 새 요청의 기본은 자동 전환 모드, 기존 고정 DEF 저장본은 조용히 재해석하지 않고 그대로 재현·표시한다(F-COND-1의 `conditionCompatibility`와 같은 원칙).
2. R3·R7 고정값: 시간 180초, 샷건 계수 "발사 1회"(per_trigger). 새 요청에서 다른 값이 오면 명확한 400으로 거부할지, 서버가 고정할지 결정해 계약에 기록한다(구 저장본은 그대로 재현).
3. **R8 보스 목록 API:** 더미 보스 + 실제 솔로 레이드 보스들의 id·이름(한국어)·이미지. 이미지는 **enikk.app/soloraid**에서 가져오는 데이터 준비 스크립트(`tools/data-pipeline/`)로 Git 제외 `data/local/presentation` 쪽에 저장한다. 원본 URL·hash는 내부 manifest에만 기록하고 UI에는 출처를 표시하지 않는다. 네트워크 수집은 격리 dataRoot에서만 실행한다(원본 `data/local`에는 배포 단계에서 사용자 확인 후 실행). 선택한 보스 id는 replay·실험 메타데이터로 저장하되 **계산에 영향이 없으므로 결과 fingerprint에는 넣지 않는다**.
4. 사거리 관련 API의 `gameVerified=false` 등 미확정 표시를 사용자 검증 결과(사거리 데이터·RL 0–0 검증 완료)에 맞게 정리한다. 경계 양끝 포함 규칙은 문서에만 "확인 대기"로 둔다.
5. UI가 따를 확정 wire(보스 API·조건 필드·고정값·방어력 모드 표시)를 계약 문서에 명시하고 인계한다.

## F2-U — UI (Claude UI 담당)

소유: `apps/desktop-ui/**`, UI tests, 보고서 `docs/combat-conditions-cleanup-ui.ko.md`.

- **R1 약점 팝업:** "니케 자신의 속성이나 보스 자신의 속성이 아닙니다…" 문구 삭제(상단 경고는 유지), 속성 이름은 한국어만(작열·수냉·풍압·철갑·전격), 현재 값 표시도 한국어만.
- **R2 거리 팝업 표:** 무기군 칸 = `weapon-*.png` 이미지 + 텍스트, "적정 사거리(다수)" → "적정 사거리", 예외 캐릭터는 한글 이름만(코드 미노출 — 한글 이름은 기존 캐릭터 표시 데이터에서 찾는다), 하단 원천·sha·"실게임 검증 전" 문구 삭제, "확인 필요"·"잠정" 등 미확정 문구 삭제(경계 규칙 설명은 화면에서 빼고 문서에만).
- **R3** 시간 입력 삭제(180초 고정). **R4** 적 방어력 선택 삭제, 안내 문구를 자동 전환 설명으로 교체. **R5** 크리티컬 유지·기본값 "확률 적용". **R6** 대미지 정책 유지(확정 시 제거 예정 — 이번엔 변경 없음). **R7** 샷건 계수 삭제(발사 1회 고정).
- **R8 보스 선택:** 크리티컬·대미지 정책 **아래**에 보스 선택. Nikke-Local-Lab UI를 참조한 카드/이미지형 선택(출처 표기 없음). 기본 선택은 더미 보스. 선택은 표시·저장만 한다.
- 단일 덱 통계 화면의 같은 조건에도 같은 규칙 적용. 이전 저장본(고정 DEF·다른 시간·샷건 설정)은 저장된 값 그대로 표시한다.
- Backend wire 확정 전에는 mock으로 먼저 만들고, Director 통지 후 실제 격리 API로 연결한다(mock과 실제 구분). 1500/850/500 레이아웃, 기존 회귀 유지.

## 이후

세 담당 인계 → 독립 QA(검수) → Director 통합 → 원본 배포(사용자 확인 후, 보스 이미지 준비 스크립트 실행 포함).

## 전달 확인

지시서 커밋 `e98db6a`. 전달 직전 세 터미널 idle 확인.

| 담당 | 터미널 | 요청 ID | 착수 근거 |
|---|---|---|---|
| F2-E 엔진 | `term_5e3783c1…` (codex) | `23831e95-c79e-4cc3-a5b8-895c206b9d05` | `input_accepted`·`turn_started` |
| F2-B Backend | `term_e5d05982…` (codex) | `f8e007ca-d03f-4fd4-91a5-074774292b65` | `input_accepted`. 화면에서 Working 확인, 재전송 없음 |
| F2-U UI | `term_c322a450…` (claude) | `13210927-4553-4535-b8bf-ead12cf23c88` | `input_accepted`·`turn_started` |

검수에는 아직 배정하지 않았다. 착수 확인이며 구현 완료가 아니다.
