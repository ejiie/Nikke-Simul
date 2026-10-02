# 버그 E-BUG-1 — 수동 풀차지(UP형 차지 무기) 발사 모션 딜레이 누락 (2026-10-02)

## 사용자 보고

리타·블랑·앨리스·누아르·모더니아 덱에서 앨리스를 수동 "풀차지"로 설정하고 피해 로그를 보면, **자체 버스트 동안 한 발 뒤 다음 발이 0.03~0.04초 뒤에** 나간다(로그 예: 221F → 223F → 225F → 227F … 2프레임 간격 풀차지 연속).

사용자 설명(게임 조작 기준):

- **리버렐리오·네온: 비전 아이** 같은 무기는 마우스를 꾹 누르고 있으면 자동으로 풀차지 공격을 하고, 풀차지 외에는 공격하지 않는다.
- **앨리스**는 마우스를 누르고 있으면 발사되지 않는다. **손을 떼야 발사**된다. 따라서 수동 풀차지는 [발사(마우스 뗌) → 다시 누름]의 반복이며 **톡톡이와 같은 메커니즘**이다.
- 앨리스를 수동 조작하지 않으면(자동) 딜레이가 **두 번** 적용된다.

## 원인 (Director 코드 확인)

`src/Nikke.Engine/Legacy/FiringModel.cs` `TryFireCharge()` 발사 후 시퀀스:

| 경로 | 현재 처리 | 사용자 설명과 비교 |
|---|---|---|
| `IsOnlyFullCharge`(DOWN_Charge, 리버렐리오·네온 VE) | rate gate만 | 일치(누르고 있으면 풀차지 자동 발사) |
| `MaintainFireStanceSec > 0` | spotFirst + maintain | 해당 없음 |
| 자동(Auto) UP형 | spotLast + spotFirst (엄폐 복귀 → 재조준) | 일치("딜레이 두 번") — 자체 버스트 중에도 적용되는지 확인 필요 |
| 수동 톡톡이 | spotFirst + 재클릭 | 일치 |
| **수동 풀차지 UP형(앨리스)** | **재클릭 간격만**("조준 유지 — 발당 spotFirst 미지불") | **불일치** — 손을 떼야 발사되므로 톡톡이처럼 spotFirst + 재클릭이 매 발 들어가야 함 |

자체 버스트로 차지 시간이 거의 0이 되면, 현재 경로에서는 발사 간격이 재클릭 간격(약 1F) + 차지 1F 수준까지 줄어 로그의 2F 간격과 일치한다. 기존 주석의 "조준 유지(발당 spotFirst 미지불)" 가설은 이번 사용자 설명으로 **기각**된다(포트폴리오 방향에 따라 기각 가설로 보존).

## 수정 방향 (배정 전 초안)

1. UP형(비 `IsOnlyFullCharge`) 차지 무기의 **수동 풀차지 발사 후 시퀀스를 톡톡이와 같은 [spotFirst + 재클릭]**으로 바꾼다. 차이는 발사 시점(풀차지 도달 후 발사)뿐이다.
2. `IsOnlyFullCharge` 무기(누르고 있으면 자동 풀차지)는 현행 유지.
3. 자동 조작 UP형의 [spotLast + spotFirst]가 자체 버스트 등 차지 시간 단축 상황에서도 매 발 적용되는지 확인한다.
4. 회귀: 기존 앨리스 풀차지 결과·통계·OL 비교의 수치가 바뀐다 → 엔진 규칙 버전 상향, fingerprint·캐시 분리, 이전 결과는 조회만. 바뀐 발수·피해·버스트 게이지(발수 감소로 게이지 충전도 달라짐)를 전후 비교로 보고.
5. 실측 대조: 앨리스 수동 풀차지 발사 간격(평시·자체 버스트)을 실게임 기록과 비교할 수 있게 trace에 발사 간격을 남긴다. 실측 값이 들어오면 spotFirst·재클릭 값을 확인한다(가설 기록).

## 진행

- 작업 구조: [구현·리뷰·QA](workflow-implement-review.ko.md). 엔진 규칙·수치 변경이므로 **구현 xhigh / 리뷰 medium / QA xhigh**.
- 세션(2026-10-02 사용자 실행): 엔진 worktree 구현 Sonnet 5.5 `term_1fba2b21…`(**high** — 계획 xhigh보다 한 단계 낮게 실행됨, 사용자 세션 설정 존중), 리뷰 astra-6 `term_ec372feb…`(medium, Full access). 구현 ⇄ 리뷰 직접 왕복, 리뷰 통과 시 Director → QA.
- 기준: Director `2487bbd`(현재 Director HEAD, 엔진 `1a86ec9` 포함)를 엔진 브랜치에 일반 merge한 뒤 작업. 소유: `src/Nikke.Core/**`, `src/Nikke.Engine/**`, 엔진 tests, 보고서 `docs/manual-charge-delay-engine.ko.md`.
- **리뷰 1차 반려(코드 아님, 2026-10-02):** 구현이 5인 비교를 위해 원본 `data/local`의 공개 표 12개(`game-catalog.json`, `calculation/*`, `runtime/*`)를 읽기 전용으로 복사해 합성 계정 비교를 돌림(hash 전후 동일, `accounts.db`·세션·캐시 미접근, 보고서 `d758867`에 기록). 리뷰가 차단 2번(원본 `data/local` 접근 금지)으로 반려하고 구현이 Director 판단을 요청.
- **Director 판단: 사후 승인.** 공개 표의 읽기 전용 사용은 H-SRC·I-BE·QA에서 hash 확인 조건으로 반복 수용한 관행이며 차단 2번의 취지(계정·캐시 보호, 변경 금지)를 어기지 않는다. 5인 비교 수치는 증거로 유효. 조건: 복사본이 자기 worktree 밖(시스템 임시 폴더 등)에 있으면 자기 artifacts로 옮기거나 삭제, 사용 파일 목록·hash를 보고서에 유지. 규칙 문구를 [작업 구조](workflow-implement-review.ko.md) 차단 2번에 명시했다.
- **리뷰 최종: 통과.** 엔진 `d932716`(구현 `9bb28ea`, 이후 보고서만), [엔진 보고서](C:/Users/user/orca/workspaces/Nikke-Simul/시뮬레이션-엔진-담당/docs/manual-charge-delay-engine.ko.md). 두 발사 모델(`FiringModel`·`SkillFiringModel`)의 수동 UP형에 spotFirst + 재클릭, 다른 경로 유지, trace `ShotIntervalFrames`, 규칙·구현 버전 4개 상향과 PreparedCompute fingerprint 연결, 구 버전 재실행 거부. Release Core/Engine 217/217. Director 확인: 변경 12파일 모두 Engine·엔진 tests·보고서(Api·Data·Contracts·apps·UI/QA tests 0), QA `8705d17`과 충돌 없음.
  - 전후(합성 5인 180초, seed 1~20 평균, 앨리스 수동 풀차지): 앨리스 발수 274.1 → 192.6(−29.7%), 앨리스 피해 3.328e8 → 2.241e8(−32.7%), **팀 총 피해 8.197e8 → 7.091e8(−13.5%)**, 풀버스트 11회 불변, 앨리스 발사 간격 중앙값 9F → 20F(자체 버스트 8~9F → 19~20F, 정상 차지 80/81F → 91/92F). 톡톡이·자동 경로는 20 seed 완전 동일.
  - 부수 효과(잠정 가설): 마지막 탄 뒤 수동 재장전 개시가 spotFirst만큼 늦어짐. spotFirst(앨리스 0.2s = 12F)·재클릭([0.02, 0.028]s)은 기존 값 — 실측 간격이 들어오면 `ShotIntervalFrames`로 대조.
- **QA 배정(2026-10-02):** 검수 `term_234e279b…`(현재 세션 high — 계획 xhigh).
- **QA 최종: 통과, 차단 0.** 검수 `dc8cb46`(엔진 `d932716` ff), [QA 보고서](C:/Users/user/orca/workspaces/Nikke-Simul/검수/docs/manual-charge-delay-qa.ko.md), 증거 색인 검수 `artifacts/single-deck-qa/ebug1/evidence-index.json`. 1,588/1,588(이전 수용 1,364 전부 포함). 53입력 × 2,400F 두 발사 모델 상태 일치, 실제 앨리스 연속 발 3,513건 위반 0, trace 간격 = 실제 프레임 차, DOWN_Charge·maintain·자동·톡톡이 전후 동일. 5인 180초(seed 1~20) 독립 재현: 앨리스 발수 −29.746%, 피해 −32.678%, **팀 819,654,190.20 → 709,110,864.20(−13.487%)**, 풀버스트 11 불변. 다른 멤버 −0.931~+0.531%는 통제 조건에서 사라져 RNG·게이지 시점 2차 영향. 규칙 4개 상향·fingerprint·튜닝 캐시 분리, 구 결과 GET·export 바이트 보존, 구 `/resume` 409. 실제 Chromium 피해 로그 230→249→268→…F(19/20F) 표시 = 저장값. 공개 표 12개 hash 불변.
  - 비차단 문서 보완: 전후 비교의 정확한 버스트 조건은 3단계 로테이션 [앨리스·모더니아]. 3명 순환 조건에서는 팀 −10.690%(QA 보고서에 별도 보존).
  - 미판정: 실게임 실측, 마지막 탄 뒤 재장전 개시 시점.
- **Director 통합:** `dab9fbf`(`--no-ff`, 제품 트리 = QA `dc8cb46`, U-FIX-7 `2487bbd` 포함). Release 빌드 경고 0·오류 0, .NET 468/468(Analysis 41·Sync 164·Compute 46·Core 217), UI 7/7. 원본 배포는 U-FIX-7과 함께 사용자 확인 후 → **2026-10-02 원본 배포 완료**([배포 기록](desktop-release-original-2026-10-02.ko.md)).
