# 보스 거리·약점 속성 조건 — UI (F-COND-U)

2026-09-28. **mock 단계 완료**: 솔로 레이드 전투 조건의 적정 거리·우월 코드 체크박스를 대체할 아이콘 버튼·팝업 두 개를 만들고 mock 데이터와 브라우저로 검증했다. **Backend 확정 wire 연결·실제 격리 API 검증은 Director 통지 대기**다. 이 문서는 UI 구현·mock 검증 보고이며 실제 API 종단·독립 QA·원본 배포 보고가 아니다.

배정: [F-COND-1 지시서](C:/Users/user/orca/workspaces/Nikke-Simul/Director/docs/boss-distance-element-assignments-2026-09-28.ko.md)의 "결정한 기본값"·"공통 기준"·"F-COND-U" 절. 공통 기준은 [client_f32 통합 지시서](C:/Users/user/orca/workspaces/Nikke-Simul/Director/docs/client-f32-integration-assignments-2026-09-28.ko.md)의 "공통 기준·보존"을 따른다. Director 문서는 읽기만 했다.

## 1. 기준·보존

- 시작 HEAD `0e83328`(U-FIX-1). Director `cd004f1`(원본 main, client_f32 배포본)을 일반 merge했다 — 이미 `0e83328`을 포함해 **fast-forward**, `apps` 차이 0. 미추적 `package-lock.json`(SHA-256 `2ef4178a…c767`) 보존·커밋 제외.
- 편집: `apps/desktop-ui/{combat-conditions.js(신규), app.js, single-deck-stats.js, simul.css}`, `tests/ui/{combat_conditions.test.mjs, check_combat_conditions_mock.py, fixtures/combat-ranges-mock.json}`(신규), 이 문서. 엔진·Backend·QA 파일 수정 없음. 단일 히트 검산(web `/legacy/`)은 바꾸지 않았다.
- API 서버를 띄우지 않았다. 원본 배포본 사용 중이므로 5180/5181·원본 경로 프로세스·EXE·원본 계정/캐시는 읽지도 건드리지도 않았다. 새 Run/Dispatch/워커·push·배포 없음.

## 2. 구현 (mock 단계)

### 2.1 flag와 live 보존

`combat-conditions.js`의 `COND_WIRE.confirmed = false`. **false인 동안 live 화면·요청은 기존과 같다**(체크박스 `distance`/`element`, `combat.properDistance`/`elementAdvantage` bool). 새 컨트롤·요청 필드·결과 모드 표시·통계 카드는 모두 `confirmed`일 때만 나온다. 잠정 wire 세부(경로 `GET /api/runtime/combat-ranges?snapshotId=`, 필드 `combat.bossDistance`/`combat.bossWeakElement`, 속성 철자 `Fire/Water/Wind/Iron/Electronic`, 사거리 응답 형태)는 이 파일 한 곳에만 있어 Backend 계약 확정 후 교체한다.

### 2.2 화면

| 요구 | 구현 |
|---|---|
| 체크박스 → 아이콘 버튼 + 현재 값 | 32×32 정사각형 버튼 2개(`↔` / 선택한 속성 아이콘, 없으면 `◇`)와 `적정 거리 · 35`·`적정 거리 · 미설정`, `약점 · 작열(Fire)`·`약점 · 없음` 표시. `코어 명중` 체크박스는 그대로. hidden input을 만들지 않고 상태는 컨트롤러가 가진다 |
| 거리 팝업 | `<dialog>` 모달. 슬라이더 + 숫자 입력(0–100 정수, 소수·범위 밖·문자는 오류 표시 후 적용 거부, 절삭·보정 없음) + `미설정`. 현재 덱 멤버별 판정(적정 거리 `min–max` / 범위 밖 / RL `보너스 없음(데이터 0–0, 확인 필요)` / 사거리 정보 없음)을 입력 중 실시간 갱신. 무기군별 적정 사거리 표(API 값, 인원, 예외 캐릭터). "무기군 표는 참고용, 판정은 캐릭터별 값" 안내 |
| 약점 팝업 | 제목 `보스의 약점 속성`, 강조 문구 **"보스의 약점 속성 — 이 속성 니케가 우월 코드 보너스를 받습니다."**, "니케 자신의 속성이나 보스 자신의 속성이 아닙니다 · 상성표 미사용" 설명. `code-*.png` 5속성 버튼 + `없음`, 각 버튼 아래 그 속성의 덱 멤버(`덱: 리타, 누아르` / `덱에 없음`). 클릭 즉시 설정 |
| 키보드·ESC | 버튼 Enter로 열기, 모달 포커스, ESC·취소·닫기는 **적용 없이** 닫기, 닫힌 뒤 연 버튼으로 포커스 복귀. 속성 버튼 Enter 선택 |
| 1500/850/500px | 대화상자 `min(640px, 100vw−32px)`, 500px에서 거리 입력 2열·속성 2열. 가로 넘침 0 |
| 이전 방식 표시 | `describeConditionMode`: 저장 조건에 새 필드가 있으면 `보스 거리 35 · 약점 작열(Fire) (멤버별 판정)`, bool만 있으면 **`이전 방식(전원 적용) · 적정 거리 적용 · 우월 코드 미적용`**(경고색). 재해석하지 않고 저장값 그대로 설명. 솔로 레이드 결과 카드에 표시. 컨트롤도 `legacy` 표시를 받을 수 있다(현재 UI에는 저장 조건을 폼으로 다시 여는 경로가 없어 결과 표시만 사용) |
| 단일 덱 통계 조건 | 통계 화면은 솔로 레이드 폼의 조건을 쓴다. 요청에 같은 새 필드를 넣고, 덱 카드에 `보스 거리·약점` 요약(솔로 레이드에서 변경)을 표시 |

판정 규칙은 Director 잠정 기본값을 그대로 표시한다: 캐릭터별 `min ≤ 거리 ≤ max`(양끝 포함, 잠정), 평타만, RL 0–0은 보너스 없음·확인 필요, 미설정 = 전원 없음, 약점 = 멤버 속성 일치. UI의 멤버별 표시는 **미리보기**이며 실제 판정은 엔진이 한다. 사거리 데이터가 없는 멤버는 추정하지 않고 `사거리 정보 없음`. 멤버 속성은 사거리 응답 값을 쓰고, 없으면 presentation `elementCode`를 쓴다. presentation의 `weaponCode` 기본값(`sniper_rifle`)은 미리보기에 쓰지 않는다.

## 3. 검증 — 모두 mock

| 명령 | 증거 종류 | 결과 |
|---|---|---|
| `node tests/ui/combat_conditions.test.mjs` | mock 단위 | 8/8: flag false면 요청 필드 null(live 유지)·true면 `{bossDistance, bossWeakElement}`, 거리 엄격 파싱(−1/101/35.5/1e2/문자 거부), 경계 min−1/min/max/max+1·미설정·RL 0–0·불명, 섞인 덱 결과(in/in/no_bonus/out/in, 속성 일치), 무기군 표 6행·예외·0–0 문구, 약점 문구·아이콘 5개·덱 멤버, 요약·이전 방식 문구, escape |
| `python tests/ui/check_combat_conditions_mock.py --assets <Backend 격리 image-catalog 사본의 assets/ui>` | mock 브라우저(Chromium, 모든 `/api` 합성 HTTP, `combat-conditions.js`만 이 실행에서 `confirmed:true`로 제공, 디스크 파일은 false) | 통과 `artifacts/ui/combat-conditions-mock/run-28a261217a57`. 폼에 옛 체크박스·hidden input 없음, 아이콘 32×32 두 개, 키보드로 거리 팝업 열기, 35 입력 시 멤버 판정, 101 오류·적용 거부, 슬라이더 35 적용·포커스 복귀, 50 입력 후 ESC → 35 유지, 약점 문구·속성 이미지 로드·`덱: 리타, 누아르`, Enter로 작열 선택, 1500/850/500px 폼·두 팝업 뷰포트 안·가로 넘침 0, replay 요청 `bossDistance:35, bossWeakElement:"Fire"`·bool 없음, 결과 `per_member`, bool만 저장된 응답 → `이전 방식(전원 적용) · 적정 거리 적용 · 우월 코드 미적용`, 통계 카드 표시·통계 요청 같은 필드, JS 오류 0. 아이콘은 Backend `artifacts/image-catalog-fix/0af4c1f9…/origin/presentation/assets/ui`를 읽기 전용 제공(원본 데이터 루트 미사용) |
| `node tests/ui/{single_deck_stats,client_f32_mock,damage_audit}.test.mjs`, vitest | 기존 회귀 | 통과 (17/17, 13/13, 19/19, 13/13) |
| `check_solo_raid_level.py`(flag false: 기존 체크박스·bool 요청), `check_single_deck_stats_browser.py`, `check_client_f32_mock_browser.py`, `check_damage_audit_browser.py --real-replay <Director 저장 replay>` | 기존 회귀 | 통과. damage audit 브라우저는 첫 실행이 로컬 정적 서버 `ERR_CONNECTION_REFUSED` 콘솔 오류 1건으로 실패했고, 코드 변경 없이 2회 재실행 모두 통과 — 일시 연결 문제로 판단하나 재현 원인은 확정하지 않았다 |

mock 사거리 fixture(`tests/ui/fixtures/combat-ranges-mock.json`): 무기군 범위·인원은 Director 집계를 옮긴 값, 멤버별 값은 경계·0–0 사례를 만들기 위한 **합성 배정**이며 실제 캐릭터 데이터가 아니다.

## 4. 확정 wire 연결 시 할 일 (Director 통지 후)

1. Backend 확정 커밋 merge, 계약 문서의 조건 필드·사거리 API 경로·응답 형태·속성 철자에 맞춰 `COND_WIRE`와 `normalizeRanges`·`conditionWire` 교체 후 `confirmed:true`.
2. 이전 bool 저장본 호환 응답 형태(명시 표시 필드가 있으면 그것을 사용)와 새·옛 필드 동시 지정 오류 문구 연결.
3. 실제 격리 API·브라우저: 사거리 표·멤버 판정이 API 값과 일치, replay·통계 요청 새 필드, 결과·로그의 멤버별 적정 거리/우월 코드, 이전 방식 표시, 기존 회귀. EXE 배포 안 함.

## 5. 미실행·한계

- 실제 API 연결·종단 검증 없음(Backend wire 미확정). 사거리 경로·필드 이름은 잠정이다.
- 저장된 조건을 폼으로 다시 여는 기능은 현재 UI에 없어 "이전 방식" 표시는 결과 카드에서만 한다. 통계 화면은 실험 요청 조건을 응답에서 다시 받지 않으므로 복원 실험의 조건 모드는 표시하지 않는다(Backend가 조건을 돌려주면 연결 가능).
- 적정 거리·우월 코드 판정 규칙(양끝 포함, RL 0–0)은 Director 잠정 가설이며 실측 검증 전이다.
