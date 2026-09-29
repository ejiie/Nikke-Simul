# 전투 조건 정리·보스 선택 — F-COND-2 배정 (2026-09-29)

## 최신 상태

- **F2-E: 완료, Director 검토 수용.** 엔진 `d090641`(구현) → `1a86ec9`(기록), `e98db6a` ff 위. [보고서](C:/Users/user/orca/workspaces/Nikke-Simul/시뮬레이션-엔진-담당/docs/def-switch-engine.ko.md). 변경은 Engine·엔진 tests·보고서뿐(Api·Data·Contracts·apps 0), Backend `97ba7bf`와 충돌 없이 merge된다. Director가 `src/Nikke.Engine/DefenseMode.cs`를 읽었다: `fixed`(생략 시 기본, 구 `EnemyDefense` 재현)와 `team_damage_threshold`, 누적 ≤ 20억이면 유지, 초과시킨 타격은 이전 DEF로 계산하고 다음 타격부터 31784.
  - 엔진 보고 검증: Core/Engine 196/196(기존 174 + 신규 22). 정확히 20억 무전환, 20억+1, 같은 프레임 멤버·추가타·SG 펠릿, Frame 0, 고정 경로, 팀 합, 자동 버스트, summary·병렬·취소. 기존 5인 180초 client 1,346,863,834 / legacy 1,346,859,763 동일.
  - 결과 계약: `SkillReplayResult.Defense`·`SkillRunSummary.Defense`(Mode·InitialDefense·FinalDefense·DamageThreshold·SwitchAfterHit — Frame·HitTraceId·HitOrdinal·CharacterId·Effect·CumulativeDamage·Previous/NewDefense), trace `defense_switch`. 버전 `skills.5-defense-switch`·`team.5-defense-switch`·`cpu-summary.4-defense-switch`.
  - Backend 후속(엔진 보고): 새 요청에 자동 모드 명시·구 fixed 저장 호환, `PreparedCompute.Create`의 fixed 라벨 수정, `PreparedCompute.Run`에서 새 `result.Defense`를 Contracts·저장 DTO로 전달(현재 매핑 없음). 다중 정책 `WeaponReplay` 참조는 자동 모드를 거부하므로 SkillReplay를 써야 한다.
- **F2-B: 차단(환경).** Backend Codex 세션이 `git merge`에서 `cannot lock ref 'ORIG_HEAD'`(워크트리 git 메타데이터 `C:/Users/user/Documents/GitHub/Nikke-Simul/.git/worktrees/…` 쓰기 권한 거부)로 실패하고 `orca` 명령도 찾지 못했다. HEAD `97ba7bf` 그대로, 미추적 보고서 초안 `docs/combat-conditions-cleanup-backend.ko.md`만 작성. Director 확인: 잔여 `.lock` 파일은 없다 — 세션 권한(샌드박스) 문제로 판단. 같은 날 엔진·UI 세션은 정상 커밋. Director가 상태 확인용으로 보낸 `/status`가 Git Bash 경로 변환으로 `C:/Program Files/Git/status`로 들어가는 실수가 있었고, 정정 메시지(`7a1d2902…`)로 무시·대기를 지시했다. 해결 방법 사용자 확인 대기. → **해소(2026-09-29):** 사용자가 해당 Codex 세션 권한을 Full access로 변경. Director 재지시(`b2cf524d…`, Orca CLI 전체 경로 사용 안내) 후 Backend가 `e98db6a`·엔진 `1a86ec9`를 merge(ff, HEAD `1a86ec9`)하고 F2-B 구현을 재개했다.
  - 추가 지시(사용자 요구, 요청 `0916794b…`): 보스 목록 API의 표시 이름은 **한국어**. 한국어 원천에서 가져오고 영문 번역·추측 금지, 한국어 이름이 없으면 누락 사유를 보고서·API 진단에 명시(영문으로 조용히 대체 금지). 영문 이름·ID는 내부 manifest에만.
- **F2-B: 완료, Director 검토 수용.** Backend `aa1b71e`(`e98db6a`·엔진 `1a86ec9` ff 위), [보고서](C:/Users/user/orca/workspaces/Nikke-Simul/Backend/docs/combat-conditions-cleanup-backend.ko.md), 확정 wire는 [compute 계약](C:/Users/user/orca/workspaces/Nikke-Simul/Backend/docs/single-deck-compute-contract.ko.md) 마지막 F2-B 절. Director 확인: Core/Engine/Analysis/apps/QA 변경 0, UI `889b679`·QA와 충돌 없이 merge된다.
  - wire: 새 skill-replay/compute POST는 최상위 `conditionProfile`(생략 = `solo_raid`), 기본 `durationFrames` 10800·`per_trigger`·`defenseMode=team_damage_threshold`·`enemyDefense` 30925·`critMode=sample`. 시간·샷건·모드의 다른 명시값은 400. 구 조건은 `conditionProfile=legacy`로 당시 시간·샷건·크리·고정 DEF 재현. `battleConditions` 저장, 구 결과 표시는 `/battle-conditions` GET. replay `result.defense`·compute `runs[].defense`에 전환 정보 저장. weapon-reference 자동 모드는 400.
  - 보스: `GET /api/presentation/solo-raid-bosses` → `schemaVersion`·`defaultBossId`·`bosses(id, name, imageUrl, season)`·`diagnostics`·`complete`. 선택은 최상위 `bossId`, 결과 replay `boss`·compute `input.boss`, 피해·fingerprint·튜닝 키 영향 0. 이미지 URL은 불투명 ID. 준비 명령 `tools/data-pipeline/prepare_solo_raid_bosses.py --presentation-root <dataRoot>/presentation`.
  - **한국어 이름: 더미 + 9시즌만 표시.** 확보한 이름(한국어 원천 원문): 41 리버렐리오 바디, 40 사치스러운 거미, 39 아일랜드 이터, 38 애니힐리오, 37 울트라(수냉솔레), 36 에고비스타, 35 크리스탈 챔버, 29 마더 웨일, 1 마더 웨일. **나머지 33시즌(2~28, 30~34, 42)은 한국어 이름을 찾지 못해 `korean_name_unavailable`로 제외**(`complete=false`). 번역·영어 대체 없음.
  - 사거리 catalog `gameVerified=true`(사용자 확인 범위), RL 진단 `rl_zero_range_no_bonus`.
  - Backend 보고 검증: Release 경고 0/오류 0, .NET 447/447, Python 4/4. 실제 격리 API: 합성 임계 초과(frame 1133·hit 3804·누적 2,001,052,869)에서 초과 타격 30925·다음 31784, replay = compute 전환 정보. 보스만 다른 두 실험의 피해·키 동일·캐시 재사용. 구 bool replay 1,586,529 유지, 구 JSON GET/export 바이트 보존, 오류 17종 400·저장 0, B-FIX-2 105/105 회귀.
- **B-FIX-3 배정(2026-09-29, F2-B 담당, 사용자 지시):** (1) 37시즌 표시 이름에서 "(수냉솔레)" 제외 → "울트라". (2) 한국어 이름이 없는 33시즌을 **웹 검색**(공식 한국 공지·나무위키 등 한국어 공개 자료, 사용자 승인)으로 찾는다. 원천 페이지로 시즌·보스 대응을 확인하고 원문 표기 그대로, 번역·추측·영어 대체 금지. 원천 URL·확인 시각은 내부 manifest에만(UI 출처 표시 없음). 못 찾은 시즌은 `korean_name_unavailable` 유지, 원천 간 불일치는 둘 다 기록하고 채택 근거 명시. 목록 데이터만 바뀌므로 UI 변경은 필요 없다. 전달 `term_e5d05982…` 요청 `dc220bd2-e18f-45fb-83d8-22ada6adcef6`, accepted=true·`input_accepted`.
- **B-FIX-3: 완료, Director 검토 수용.** Backend `b977e77`(`aa1b71e` 직계), [보고서](C:/Users/user/orca/workspaces/Nikke-Simul/Backend/docs/solo-raid-boss-korean-names-backend.ko.md). 변경은 `tools/data-pipeline`(준비 스크립트·테스트·내부 manifest)·Backend 테스트·문서뿐(`src`·`apps` 0). API wire 불변: 목록 43개(더미 + 시즌 1~42), 제외 0, `complete: true`.
  - 원천 URL·확인 시각·다른 표기·채택 이유는 내부 manifest(`tools/data-pipeline/manifests/solo-raid-korean-names.manifest.json`)에만. 37 → "울트라", 35 "크리스탈 체임버"(시즌 대응표 원문 채택, "챔버"는 내부 기록), 5 "화이트 스미스"(한국어 기사 별칭), 표기 차이 2/4/5/25/32/33/34/35/37 기록. **42 "앨트루이아"는 사용자가 Backend 세션에 직접 확정**했으며 웹 대응 확인을 주장하지 않는다.
  - 확정 목록: 1 마더 웨일, 2 블랙스미스, 3 하베스터, 4 알트아이젠, 5 화이트 스미스, 6 모더니아, 7 울트라, 8 토커티브, 9 마테리얼 H, 10 크리스탈 체임버, 11 스톰브링어, 12 니힐리스타, 13 인디빌리아, 14 그레이브 디거, 15 황금 크라켄, 16 미러 컨테이너, 17 거대 질량체, 18 랜드 이터, 19 베히모스, 20 백빙룡, 21 모더니아, 22 마테리얼 H, 23 거대 질량체 Q, 24 검은 뱀, 25 글러트니, 26 프로비던스, 27 환영 크라켄, 28 지즈, 29 마더 웨일, 30 차가운 심판자, 31 퀸 001, 32 알트아이젠, 33 온리 원, 34 앨트루이아, 35 크리스탈 체임버, 36 에고비스타, 37 울트라, 38 애니힐리오, 39 아일랜드 이터, 40 사치스러운 거미, 41 리버렐리오 바디, 42 앨트루이아.
  - Backend 보고 검증: Python 6/6, 격리 API 목록 43·제외 0·이미지 42개 HTTP 바이트/hash 일치·내부 manifest 경로 404. 원본 `data/local` 불변. 배포 시 새 준비 스크립트 실행 필요.
  - 통합·QA 기준은 UI 2단계 커밋에 `b977e77`을 합친 트리로 한다. UI에 `b977e77` merge·격리 목록 재준비(43개) 통지 — 요청 `35e71556…`, `input_accepted`(UI는 사용 한도 대기 후 자동 재개해 작업 중이던 턴에 전달).
- **F2-U 2단계: 완료, Director 검토 수용.** UI `92aef7b`(Backend `aa1b71e` merge) → `bcdd73a`(`b977e77` merge, 충돌 0) → `dae1949`, 보고서 6절. Director 확인: 변경은 `apps/desktop-ui`·UI tests·UI 문서(제품 `src`·QA `tests/q3` 0), 앱 코드에 "Local-Lab" 표기 0, 엔진 `1a86ec9`·Backend `aa1b71e`·`b977e77` 포함, QA 브랜치와 충돌 없이 merge된다.
  - R4: 새 요청은 `conditionProfile`·`enemyDefense`·`defenseMode` 미전송(solo_raid 기본), 결과 카드에 `battleConditions`(구 기록은 `/battle-conditions`), `result.defense` 전환 표시(시작→최종 DEF·시각·캐릭터·누적, 전환 없음·fixed 구분). R8: 한국어 보스 목록(더미 기본·최신 시즌 순), 두 POST 최상위 `bossId`, `diagnostics`가 있을 때만 "일부 보스 이름 준비 중".
  - 발견·수정: 실제 저장 replay는 조건이 `result.conditions`에 있어 조건 줄에서 크리티컬이 빠지던 문제(1단계 mock 가정) 수정.
  - 출처 삭제: 고급 진단 "화면: Nikke-Local-Lab", `cards.js`·`local-lab-detail.js`·`local-lab-account.js`·`local-lab-adapter.js` 첫 줄 주석, `simul.css` 주석 2곳. 파일·함수 이름 유지.
  - UI 보고 실제 격리 API + Chromium(`b977e77` 기준): 보스 43개·제외 0·이미지 42, 한국어 이름 카드, 기본 replay 요청 필드·저장 boss, 합성 100배 공격으로 실제 전환(488프레임 블랑 누적 2,000,645,839) 표시, legacy 프로필 → 이전 방식 고정 방어력 표시, 통계 카드, 1500/850/500 넘침 0·JS 오류 0. 기존 회귀 통과.
- **F2-Q 배정(2026-09-29):** 기준 UI `dae1949`(엔진·Backend·보스 이름 모두 포함). 사용자가 검수 Codex 세션을 **xhigh**로 전환(R4 경계 포함이라 세션 전체 xhigh). 범위:
  1. R4 경계(독립 산술·자체 검사): 누적 < 20억 무전환, 정확히 20억 무전환, 20억 초과 타격은 30925·다음 타격부터 31784, 같은 프레임 멤버·추가타·SG 펠릿 순서, 전환 기록(frame·hit·캐릭터·누적)과 replay = compute 일치, 기존 고정 DEF·legacy 프로필 결과 정확 재현, 팀 합 = 구성원 합.
  2. 조건 wire: 새 요청 기본값(180초·per_trigger·자동 DEF·크리 sample), 다른 명시값 400, `conditionProfile=legacy` 재현, `battleConditions` 저장·`/battle-conditions` 조회, 구 결과 GET/export 바이트 보존, fingerprint·튜닝 키 분리.
  3. 보스: 한국어 목록 43개·제외 0·이미지, `bossId` 저장, 보스만 다른 실험의 피해·키 동일, UI·API 응답에 출처·영문명·원본 ID 미노출.
  4. 화면 R1~R8(실제 격리 API + 브라우저): 약점 팝업 문구·한국어 속성, 거리 표(아이콘·한글 예외·미확정 문구 없음), 시간·방어력·샷건 입력 없음, 크리 기본 확률 적용, 보스 카드 선택, 전환 표시, 이전 기록 표시, 앱 화면의 Nikke-Local-Lab 표기 없음, 1500/850/500, 기존 회귀(F-COND-1·client_f32·통계).
  - 담당 검사 스크립트·mock·정답 재사용 금지, 격리 dataRoot에서 `prepare_combat_conditions.py`·`prepare_solo_raid_bosses.py` 준비, 원본 `data/local`·5180/5181 불변, 부하·Q-CPU-10K 보류. 전달 `term_234e279b…` 요청 `bd88c4e2-87ff-4436-a7b7-923a68c62fb3`, accepted=true·`input_accepted`·`turn_started`(지시서 `a16005f`).
- **F2-Q: 전체 수용 보류(UI 문구 1건).** 검수 `09c9d8a`(UI `dae1949` ff), [QA 보고서](C:/Users/user/orca/workspaces/Nikke-Simul/검수/docs/combat-conditions-cleanup-qa.ko.md), 근거 검수 `artifacts/single-deck-qa/f2-preparation/evidence-index.json`·`f2-2a4bc7b9cd59/` 등. QA 커밋의 제품 변경 0. **376검사 중 375 통과**(엔진 독립 산술 87/87, 실제 API + Chromium 178/179, client_f32·통계 회귀 91/91, 프로필 409 회귀 19/19), 담당 검사·mock·정답 재사용 없음.
  - R4 통과: 정확히 20억 무전환, 초과 타격 다음부터 31784, 같은 프레임 멤버·추가타·SG 펠릿·frame 0. 합성 5인 180초 19,462피해 전부 Fraction/float32 독립 검산, 팀 24,007,922,311 = replay = compute, 전환 frame 750·hit 3076·앨리스·누적 2,013,492,851. fixed legacy 6,573,008·멤버 정확 재현, 구 JSON GET/export 바이트 보존. 기본값·400 36종·키 분리·보스만 변경 시 피해·키 동일·캐시 재사용, 보스 43·한국어·이미지 42, 화면 R1~R8·1500/850/500 통과.
  - **F2-Q-1(UI):** `apps/desktop-ui/single-deck-stats.js:56` 단일 덱 통계 "DEF 정책" 카드 부제가 **`'자동 20억 전환 없음'` 고정 문자열**이라 자동 모드·실제 전환한 실험에도 그대로 표시된다(Director 코드 확인).
  - QA 자체 도구 오류(nullable raw 처리, 초기 replay/compute 택틱 적용 차이)는 원 로그를 보존한 채 QA 도구만 고쳤고 제품 결함이 아니다.
  - 미판정: 실게임 20억 경계·사거리 양끝, 실사용 덱, 원본 배포, 성능·GPU·Q-CPU-10K.
- **U-FIX-3 배정(2026-09-29, F2-U 담당):** (1) F2-Q-1 — DEF 정책 카드를 저장된 정책으로 구분 표시: 자동 모드(전환 있음이면 시점·캐릭터·누적, 없음이면 "전환 없음"), legacy 고정 DEF는 이전 방식 설명. (2) Director 추가 발견 — 같은 파일 46행 덱 목록이 **캐릭터 코드(`#5004` 등)**를 노출한다. R2의 "캐릭터 코드는 UI에 노출하지 않는다" 사용자 지시에 맞춰 제거(한글 이름만). 다른 화면에도 같은 코드 노출이 있으면 목록으로 보고하고 같은 기준으로 정리. 실제 격리 API + 브라우저로 자동 전환 있음/없음/legacy 세 경우 재확인. 이후 QA 재수용. 전달 `term_c322a450…` 요청 `7897384f-e4d3-4e47-a1df-a2b979b982ae`, accepted=true·`input_accepted`, 화면에서 작업 중 확인.
- **U-FIX-3: 완료, Director 검토 수용.** UI `ad6d3f0`(`dae1949` 후속, 새 merge 없음), 보고서 7절. Director 확인: 제품 `src`·QA `tests/q3` 변경 0, 고정 문구 "자동 20억 전환 없음" 제거, QA `09c9d8a`와 충돌 없이 merge된다.
  - F2-Q-1: DEF 카드를 저장 `battleConditions`·`defPolicy`와 `runs[].defense`로 표시 — 예정(자동 전환 설명), 자동·전환 없음("전환 없음 · N회 모두 누적 20억 이하"), 자동·전환 있음(시작→최종 DEF·시각·캐릭터·누적, 여러 회는 N회 중 K회 + 첫 결과), legacy(이전 방식 고정 DEF).
  - 캐릭터 코드 정리: 통계 덱 목록·OL 비교·피해 audit 효과 출처·사거리/속성 진단·조건 멤버 미리보기·편성/전술 요약·버스트 사이클 표·검산 결과 멤버 제목·피해 로그 대상·버스트 전술 목록 → 한글 이름 또는 "이름 미확인". 데이터 속성·내부 키·타격/발사/함수 번호·replay ID는 유지.
  - UI 보고 실제 격리 API + Chromium: 자동·전환 없음, 자동·전환 있음(1,253프레임 누아르 누적 2,000,901,314 = `runs[].defense`), legacy fixed 31,784 세 경우 카드 일치, 솔로레이드·통계 화면 텍스트의 캐릭터 코드 0건. 기존 회귀 통과.
- **F2-Q 재수용 통지(2026-09-29):** UI `ad6d3f0` 기준 F2-Q-1·캐릭터 코드 제거 재검 + F2 회귀. 전달 `term_234e279b…` 요청 `fd0a3c46-2ef5-4676-a874-fe0bc2aab232`, accepted=true·`input_accepted`·`turn_started`.
- **F2-Q 재수용: F2-Q-1 해결, 전체 수용 보류(새 결함 F2-Q-2).** 검수 `eb7c23f`(UI `ad6d3f0` merge `e1a2c27`), QA 보고서 최신 절, 근거 검수 `artifacts/single-deck-qa/f2-ufix3-preparation/evidence-index.json`·`f2-ufix3-554048887882/`·`f32-b2-44bc8203db35/`. QA 커밋의 제품 변경 0.
  - 새 검사 462 중 456 통과·6 실패(한 원인). 이전 수용 375항목 375/375 재확인. F2-Q-1: 자동 무전환·전환·legacy 30925/31784 총 6조합이 `runs[].defense`와 일치. 새 피해 19,462건 독립 산술, 팀 24,007,922,311 = replay = compute.
  - 사용자가 QA 질문에 **"화면에서는 이름으로 표시해야 함"**이라고 명시 확인했다.
  - **F2-Q-2(UI):** 앨리스 머리 1번 줄 StatAtk 4.77% replay의 타격 검산 근거에 `상시 비율 · overload:5004:head:1:StatAtk +4.77%`가 화면 텍스트로 노출(정책·폭 6관측, 한 원인). Director 확인: `apps/desktop-ui/damage-log-adapter.js`의 `sourceText`가 `skill:` 키만 이름으로 바꾸고 나머지 source 키는 원문 그대로 반환한다.
- **U-FIX-4 배정(2026-09-29, F2-U 담당):** `sourceText`가 모든 source 키 종류(overload·장비·큐브·소장품·기타)를 한글 표시로 바꾼다(예: "앨리스 · 머리 1번 줄 · 공격력"). 모르는 키 형식은 코드·원문을 보이지 말고 일반 한국어 라벨로. API·저장 source 키는 보존하고 표시 문자열만 바꾼다. 같은 유형(내부 키가 화면에 그대로 나오는 곳)을 다른 화면에서도 찾아 정리·보고. 실제 기존 저장 replay·1500/850/500·계산/저장 불변 확인. 이후 QA 재수용. 전달 `term_c322a450…` 요청 `8cef6d31-7c23-4963-bf48-e68bcf66ad22`, accepted=true·`input_accepted`.
- **U-FIX-4: 완료, Director 검토 수용.** UI `00911ce`(`ad6d3f0` 후속, 새 merge 없음), 보고서 8절. Director 확인: 제품 `src`·QA `tests/q3` 변경 0, QA `eb7c23f`와 충돌 없이 merge된다.
  - 새 `display-labels.js`의 `describeSourceKey`: overload → "앨리스 · 머리 1번 줄 · 공격력", 큐브/소장품 → "큐브 · 공격력"/"소장품 · …"(모르면 "큐브 효과"/"소장품 효과"), 장비 → "장비 · 몸통", 수동 → "직접 입력한 버프 n", function → "스킬 효과 · 함수 id", skill은 기존 이름·슬롯, 그 밖 "기타 효과". API·저장 키·데이터 속성 불변.
  - 같은 유형 정리: audit 적용 기준, 미해석 효과(type N), 통계 OL 비교 표 부위·옵션, 표본 단계 이름, 고급 진단 이슈 path.
  - 유지(UI 판단): 타격·발사·함수 번호, replay ID, fingerprint·규칙·summary 버전·schema, 대미지 정책 id, 사거리 진단 서버 원문. **"함수 id"는 내부 번호가 화면에 남는 경우라 사용자 원칙("화면에서는 이름으로")과의 부합 여부를 사용자에게 확인한다.** → **사용자 결정(2026-09-29): 함수 번호는 화면에서 지우고, 나머지(타격·발사 번호, replay ID, fingerprint·버전·schema, 정책 id)는 유지.**
  - UI 보고 실제 격리 API + Chromium: QA 재현과 같은 replay 타격 #200 "상시 비율 · 앨리스 · 머리 1번 줄 · 공격력 +4.77%", 패널의 원문 키·코드 0, 조회 전후 저장본·총피해 동일, 기존 저장 replay 파일 hash 불변. 회귀 통과.
- **U-FIX-5 배정(2026-09-29, F2-U 담당):** function source 표시에서 함수 번호 제거 — 스킬 이름·슬롯으로 해석되면 그 이름, 아니면 "스킬 효과"만. 다른 화면의 함수 번호 표시도 같은 기준. 나머지 내부 번호는 유지. QA는 `00911ce` 재수용 결과에 이 변경분 확인을 더해 판정한다.
  - **U-FIX-5: 완료, Director 검토 수용.** UI `1168819`(`00911ce` 후속), 보고서 9절. Director 확인: 제품 `src`·QA `tests/q3` 변경 0, `apps/desktop-ui` 전체에 "함수" 문자열 0건, QA 브랜치와 충돌 없이 merge된다. function source → 저장 스킬 슬롯으로 해석되면 "누아르 · 스킬 1", 아니면 "스킬 효과"(기록 없음 "스킬 정보 미기록"). UI 보고 실제 격리 API + Chromium: 타격 #200 "고정 가산 · 누아르 · 스킬 1 +12,717", 기존 저장 replay "고정 가산 · 누아르 · 스킬 1 +17,191"(파일 hash 불변). 부수 발견: U-FIX-3 때 주석 삽입으로 실행되지 않던 audit 단언(originText)을 분리·복구.
  - QA에 `1168819` 변경분 추가 통지(재수용 진행 중 턴에 전달).
- **F2-Q U-FIX-4/5 재수용: F2-Q-2·함수 번호 제거 수용, 전체 수용 보류(F2-Q-3~5).** 검수 `02b63fb`(UI `00911ce` merge `14eca15` → `1168819` merge `1e81ee6`), QA 보고서 최신 절, 근거 검수 `artifacts/single-deck-qa/f2-ufix5-preparation/evidence-index.json`(`identifier-inventory.json`에 유지 식별자 위치). QA 커밋 제품 변경 0.
  - 최신 576검사 중 572 통과·4 실패(아래 세 경로). 원래 375 수용 조건 충족, 새 피해 19,462건 독립 검산·팀 24,007,922,311 = replay = compute, DEF 6조합·통계 회귀 유지. source 17종 × 정책 4개 표시(QA 합성 버프 창으로 검증 — 실제 큐브·소장품 육성 효과 수용과 구분). 사용자 확정 유지 번호는 결함으로 보지 않았다.
  - **F2-Q-3(UI):** 다른 니케 로그를 요청하면 "현재 리플레이는 5004의 대미지 로그만 수집되었습니다. 5011의 로그를…"처럼 캐릭터 코드 노출(`damage-log-adapter.js` 841·923행 부근).
  - **F2-Q-4(UI):** 솔로 레이드 결과의 "저장 결과 원문"을 펼치면 `JSON.stringify(saved)`가 그대로 보여 source 키·캐릭터 코드·함수 번호가 노출(`app.js` 325행 부근).
  - **F2-Q-5(UI):** 409 `combat_profile_invalid` 안내의 "서버 원문: combat_profile_invalid: combatProfiles.characters.5004.bonusRangeMin: missing" 노출(`app.js` 318행, `single-deck-stats.js` 364행). U-FIX-2 때 의도한 서버 원문 병기였으나 최종 화면 원칙으로 재분류.
- **U-FIX-6 배정(2026-09-29, F2-U 담당, 화면 표시 원칙 적용):** (1) F2-Q-3 — 현재/요청 캐릭터를 한글 이름으로 안내(Replay ID 배지는 유지). (2) F2-Q-4 — 화면의 저장 결과 원문 JSON 표시를 없앤다. API·저장·JSON/CSV 내보내기(파일)는 그대로 둔다. (3) F2-Q-5 — 한국어 진단(캐릭터 이름·필드 의미·사유·준비 안내)만 표시하고 서버 원문 문자열은 화면에서 뺀다(구조화 오류·409·저장 0·연결 유지는 보존). (4) 남은 화면 전체를 한 번 더 훑어 코드·원문 키 노출을 정리하고 목록 보고. 실제 격리 API·브라우저 확인, 원본 `data/local`·5180/5181 불변. 이후 QA 재수용.
- **U-FIX-6: 완료, Director 검토 수용.** UI `59fe22d`(`1168819` 후속), 보고서 10절. Director 확인: 제품 `src`·QA `tests/q3` 변경 0, `JSON.stringify(saved)` 화면 표시 제거, QA `02b63fb`와 충돌 없이 merge된다.
  - F2-Q-3 로그 대상 안내 한글 이름, F2-Q-4 원문 JSON 화면 블록 삭제(API·저장·내보내기 유지), F2-Q-5 서버 원문 삭제·한국어 진단만.
  - 전체 점검 추가 정리: `api()` 오류 문구 한국어화(원문은 로직용 필드로만), 통계 장치·선택 근거·CPU 대체 원인 사유 코드 33종 한국어화(모르면 "기타 사유"), `mean_ci_requires_n_at_least_2` 병기 삭제, 사거리·속성 미준비 문구의 내부 경로 삭제, 버스트 설정 경고의 코드 나열 삭제, 고급 진단 슬롯 키 한글화.
  - 유지: 타격·발사·버스트 시전 이벤트 번호, replay ID, fingerprint·버전·schema·정책 id, 조치 안내의 준비 스크립트 이름, 장치 식별 해시.
  - 범위 밖으로 남김: 기존 웹 참조 UI(`/legacy`) 단일 히트 오류 문구(데스크톱에서 연결되지 않음).
  - UI 보고 검증: 실제 격리 API + Chromium에서 보스 43·화면 코드/원문 0건(수정 전 실패 run과 대조), 손상 데이터 3경우 한국어만, 기존 저장 replay 해시 불변, 단위·Q3 26/26·vitest·브라우저 회귀 통과.
- **F2-Q 재수용 통지(2026-09-29):** UI `59fe22d` 기준 F2-Q-3~5 재검 + 화면 원칙 전체 점검 + 회귀.
- **F2-Q U-FIX-6 재수용: F2-Q-3·4·5 수용, 전체 수용 보류(F2-Q-6).** 검수 `180f23b`(UI `59fe22d` merge `dc612bd`), QA 보고서 최상단 U-FIX-6 절, 근거 검수 `artifacts/single-deck-qa/f2-ufix6-preparation/evidence-index.json`·`f2-ufix6-1213fc48923f/audit-wire-vs-visible.json`. 총 772검사 중 769 통과·3 실패(같은 F2-Q-6 경로). R4 엔진 87, DEF 6조합, 보스 43·이미지 42, 조건 wire, 피해 19,462건 독립 검산(팀 24,007,922,311, 전환 750프레임·앨리스·누적 2,013,492,851) 유지. `/legacy`는 명시 제외.
  - **F2-Q-6(UI):** 피해 검산 표에 저장 구조의 키·서버 문자열이 그대로 보인다 — 제목의 `calculation.terms`, 단계 부제의 `effectiveAttack`/`effectiveDefense` 등 `terms[].name`, 저장된 영문 `operation`. Director 확인: `apps/desktop-ui/damage-log.js` 125행(`s.name` 부제), 128행(`s.operation`), 133·160행(`calculation.terms` 문구). 같은 패턴으로 135행 누락 항목 이름, 149행 "(hit 기록)"도 있다.
- **U-FIX-7 배정(2026-09-29, F2-U 담당):** 피해 검산 표를 표시용 한국어로 렌더 — 단계 이름·부제는 한국어 항목명(내부 name 부제 삭제), 연산 설명은 단계별 한국어 설명(저장된 영문 operation 직출력 금지), 제목·누락 안내의 `calculation.terms`·`hit` 같은 구조 경로 삭제. 수식 기호(B, float32 등)는 허용. API·저장·`data-term`·수치·export는 유지. **순환을 끝내기 위해** 이번에는 `apps/desktop-ui`에서 저장·서버 데이터의 문자열 필드를 그대로 화면에 넣는 모든 지점(`esc(x.name|operation|code|path|source|message…)` 류)을 전수 조사해 목록으로 보고하고 같은 기준으로 정리한다. 이후 QA 재수용.
- **F2-Q 재수용 통지(2026-09-29):** UI `00911ce` 기준 F2-Q-2 재검 + 회귀. 전달 `term_234e279b…` 요청 `2d024b4c-aaac-4890-a480-111eccc6fbab`, accepted=true·`input_accepted`·`turn_started`. 남은 내부 번호의 화면 노출은 목록으로 기록만 하고 결함 판정하지 않도록 지시(사용자 확인 대상).
- **F2-U 2단계 통지(2026-09-29):** Backend `aa1b71e` 기준 R4·R8 실제 연결 + 앱 화면·코드 주석의 Nikke-Local-Lab 출처 표기 삭제.
- (이전) 엔진 `1a86ec9` merge 통지(2026-09-29) — `term_e5d05982…` 요청 `eebad101-6fd8-4a9a-a8fb-b8203c2cf1ab`, accepted=true·`input_accepted`(작업 중 턴에 전달, 재전송 없음). **F2-U:** 진행 중.
- **F2-U 1단계: 완료, Director 검토 수용.** UI `889b679`(`e98db6a` ff 위), [보고서](C:/Users/user/orca/workspaces/Nikke-Simul/UI/docs/combat-conditions-cleanup-ui.ko.md). 변경은 `apps/desktop-ui`·UI tests·UI 문서뿐(제품 `src`·QA `tests/q3` 0). Director가 mock 캡처(전투 조건 폼·보스 선택·거리 팝업, 1500px)를 확인했다.
  - 기존 wire로 실제 연결·검증: R1(설명 문장 삭제·속성 한국어만), R2(무기군 아이콘 + 이름, "적정 사거리", 예외 한글 이름만·코드 미노출, 출처·sha·검증 전·참고용·확인 필요·잠정 문구 삭제), R3(시간 삭제·180초), R5(크리 기본 확률 적용), R6(변경 없음), R7(샷건 삭제·per_trigger). 저장 결과 카드는 저장 당시 조건 그대로 표시.
  - mock(flag false, wire 대기): R4 방어력 선택 삭제·자동 전환 안내, R8 보스 카드 선택(크리·정책 아래, 더미 기본, 대화상자 카드 격자, 표시·저장만). 실제 폼은 아직 고정 DEF 선택·보스 없음.
  - UI 보고 검증: 실제 격리 API + Chromium(조건·손상 진단·client_f32 live), mock 브라우저 R1~R8 1500/850/500 넘침 0·JS 오류 0, 단위·Q3 26/26·기존 회귀 통과.
  - 참고: 기존 코드에 Nikke-Local-Lab 출처 표기가 남아 있다 — `apps/desktop-ui/app.js` 고급 진단의 "화면: Nikke-Local-Lab" 문구, `cards.js`·`local-lab-detail.js` 첫 줄 주석, README·`desktop-ui-migration.ko.md`·`desktop-spec-editor.ko.md`. 2026-09-29 정리: README·`desktop-ui-migration.ko.md`·`desktop-spec-editor.ko.md`의 프로젝트 이름·저장소 URL·고정 커밋은 Director가 "원본 관리 UI"로 바꿨다(작업 지시 문서는 담당이 참조 위치를 찾도록 이름 유지). 앱 화면 문구와 코드 주석 삭제는 F2-U 2단계에 포함한다. 파일 이름(`local-lab-detail.js`·`local-lab-adapter.js`)은 참조 경로가 많아 이번엔 바꾸지 않는다.

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

이 배정은 기존 담당 구조로 마친다. 새 [작업 구조](workflow-implement-review.ko.md)의 사고 수준 기준은 아직 배정하지 않은 QA 단계부터 적용한다(사용자 승인, 2026-09-29): **F-COND-2 QA는 high, R4 방어력 전환 경계(20억 초과 판정·같은 프레임 순서·전환 기록) 검증은 xhigh.**

## 전달 확인

지시서 커밋 `e98db6a`. 전달 직전 세 터미널 idle 확인.

| 담당 | 터미널 | 요청 ID | 착수 근거 |
|---|---|---|---|
| F2-E 엔진 | `term_5e3783c1…` (codex) | `23831e95-c79e-4cc3-a5b8-895c206b9d05` | `input_accepted`·`turn_started` |
| F2-B Backend | `term_e5d05982…` (codex) | `f8e007ca-d03f-4fd4-91a5-074774292b65` | `input_accepted`. 화면에서 Working 확인, 재전송 없음 |
| F2-U UI | `term_c322a450…` (claude) | `13210927-4553-4535-b8bf-ead12cf23c88` | `input_accepted`·`turn_started` |

검수에는 아직 배정하지 않았다. 착수 확인이며 구현 완료가 아니다.
