# F2-Q 독립 재수용 — U-FIX-3 (2026-09-29)

**최종 판정: F2-Q-1 해결·이전 375항목 회귀 통과. 전체 수용은 화면 코드 노출 1종으로 보류한다.** 저장 DEF 카드는 자동 무전환/실제 전환/legacy 고정을 올바르게 구분한다. 남은 **F2-Q-2**는 피해 로그의 공격력 근거에 `overload:5004:head:1:StatAtk` 원천 키가 일반 텍스트로 표시되는 경우다. 엔진·API 계산 실패는 관측하지 않았다.

## 이번 재검 기준과 범위

- 자기 QA `09c9d8a`에서 제품 `ad6d3f0`을 `git merge --no-edit ad6d3f0`으로 일반 merge했다. merge `e1a2c27`, 충돌 없음. 기존 이력과 미추적 `package-lock.json`을 보존했다.
- Director 지시서 전체의 최신 상태/U-FIX-3와 UI 보고서 `combat-conditions-cleanup-ui.ko.md` 7절을 읽었다. 담당 검사·mock·정답은 판정에 사용하지 않았다. 아래 검사는 모두 본인 QA 코드이며 기존 통과 결과를 복사하지 않았다.
- 공개 파일로 새 합성 계정·새 격리 dataRoot를 만들고, 자체 준비 코드에서 `prepare_combat_conditions.py`를 실행했다. 보스 43개/이미지42개는 이전 QA가 준비한 본인 공개 presentation 사본을 hash 대조하여 재사용했다. 실제 API와 Chromium을 사용했고 API 응답 대체는 없다.
- 엔진 입력/독립 Fraction·binary32 산술, 실제 공개 5인/400레벨/180초 replay, 최대 n=2·CPU worker1 실험, 브라우저를 새로 실행했다. 부하 측정이나 성능 비교가 아니다. 기존 짧은 client_f32 회귀는 명시 legacy 요청으로 구분했다.
- 본인 제품 소스는 직접 수정하지 않았다. `git diff ad6d3f0 -- src apps tools package-lock.json` 차이 0. QA 코드·본 보고서·새 Git 제외 artifacts만 변경했다.

## 새 실행 결과

아래 경로는 모두 본인 worktree `C:/Users/user/orca/workspaces/Nikke-Simul/검수/` 기준이다.

| 범위 | 결과 | 새 근거 |
|---|---|---|
| API Release 빌드 | 경고0·오류0 | `artifacts/single-deck-qa/f2-ufix3-preparation/api-build.log` |
| 자체 엔진 독립 산술 | 87/87 | `f2-ufix3-preparation/engine-audit.json`, `engine-results.json` |
| 실제 F2 API·Chromium·profile 회귀 | 261/262 | `f2-ufix3-554048887882/summary.json` |
| 실제 client_f32·통계 회귀 + 새 코드 스캔 | 108/113 | `f32-b2-44bc8203db35/summary.json` |
| 이전 통과375개 수용 항목 대조 | **375/375, 누락0** | `f2-ufix3-preparation/regression-coverage.json` |

새 물리 검사 **462개 중 456 통과, 코드 노출 관측 6개 실패**다. 6개는 별개 결함이 아니라 같은 원천 키의 F2/기존 정책/화면 폭별 반복 관측이다. 이전 375개는 엔진87·F2 178·client_f32 91·profile19를 이름으로 대조했다. 이번에는 profile 회귀를 F2 세션에 포함했으므로 공개 입력/package-lock 보존 2개 검사가 두 기존 범위의 조건을 함께 충족한다. 375라는 회귀 수용 항목 수를 서로 다른 새 검사 375건이라고 중복 집계하지 않는다.

새 본 검사 포트는 F2 최종 **58357**, client_f32 **49981**이다. API 재시작에 사용한 다른 격리 포트와 본인 PID는 로그에 남겼다. summary의 `ownApiStopped=true`, JS 예외0. 모든 완료 서버는 본인이 생성한 프로세스만 종료했다.

### F2-Q-1: 해결·수용

실제 저장 실험을 브라우저에서 조회하여 카드와 `runs[].defense`를 대조했다. 응답이나 저장 결과는 바꾸지 않았다. 표시는 조회 전후 결과 DTO가 동일했고, 각 조합에서 1500/850/500 화면 가로 넘침이 없었다.

| 실제 저장 조합 | 확인한 표시 |
|---|---|
| 자동·전환 없음, n=1 | 자동30925→31784, `전환 없음 · 1회 모두 누적 20억 이하` |
| 자동·전환 없음, n=2 | `전환 없음 · 2회 모두 누적 20억 이하` |
| 자동·전환 있음, n=1 | 12.5초/750프레임, 앨리스, 누적2,013,492,851, 30925→31784 |
| 자동·전환 있음, n=2 | `2회 중 2회 전환 · 첫 결과`, 위 전환 기록 일치 |
| legacy fixed30925, n=2 | `이전 방식`, 30,925 고정, 당시 조건 |
| legacy fixed31784, n=1 | `이전 방식`, 31,784 고정, 당시 조건(2초·per_pellet) |

실행 전 예정 카드는 `20억 초과 후 다음 타격부터 전환`이라고 설명한다. 실제 전환 실험에 잘못된 `자동 20억 전환 없음` 문구는 없다. 근거는 `f2-ufix3-554048887882/ufix3-planned.json`, `ufix3-display-*.json`, `ufix3-*-1500.png`/`850.png`/`500.png`다. 스크린샷의 복구 폼 기본값1000은 실행 표본 수가 아니다. 이번 실험의 실제 n은1또는2다.

### 이전 회귀: 수용

- 엔진 독립87검사 재실행: 정확히20억은 전환 없음, +1을 만든 타격까지30925, 다음 타격부터31784. 같은 프레임 멤버·SG펠릿·추가타·frame0·과거 정책을 재검산했다.
- 새 실제 API 피해 **19,462건** 전부 독립 계산. 팀 합 **24,007,922,311** = 멤버 합 = replay = compute. 전환 frame750/hit3076/ordinal1543/앨리스/누적2,013,492,851. 제품 DEF 플래그를 기대값으로 재사용하지 않았다.
- fixed legacy 총6,573,008/멤버/effect 일치, 과거 저장 GET/export 불변, 기본값·36개 HTTP400·저장 전 거부·키 분리·보스만 변경 시 키/피해 동일을 재확인했다.
- 한국어 보스43개·실제 이미지42개, 거리/약점 팝업·미리보기·키보드/ESC·포커스·전술·레벨400·버스트·저장 복구·n1/n2 통계·client_f32 네 정책·exact 큰 정수·실제400/409를 재확인했다.
- 손상 profile min/max/element 각각 조회2종/replay/compute의 구조화409·저장 증가0, 한국어 진단·연결 유지가 통과했다. client_f32 회귀의 명시적 HTTP503/transport 주입과 n=0 표시 경계는 기존과 같은 검사이며 자연 장애나 n=0 API 표본으로 주장하지 않는다.

### F2-Q-2: 피해 로그 원천 키에 캐릭터 코드 표시 — UI 잔여 항목

**담당: F2-U(UI).** 일반 이름/배지의 `#5004` 제거, 통계 덱 목록·전술·조건 멤버·전환 캐릭터 이름 표시는 통과했다. 하지만 실제 피해 로그의 공격력 근거가 다음처럼 표시된다.

```text
최종 공격력 입력 (hit 기록)
상시 비율 · overload:5004:head:1:StatAtk +4.77%
```

- 최소 재현: 공개 합성5인 중 앨리스에 head 1번 줄 StatAtk 4.77% → 실제 솔로레이드 실행 → 앨리스 타격의 `검산 근거` → `최종 공격력 입력 (hit 기록)` 확인. client_f32 및 과거 정책, 1500/850/500에서도 같은 표시다.
- 실제 응답의 내부 `source` 키는 정상 보존 대상이다. 문제로 분류한 곳은 일반 사용자가 읽는 공격력 근거의 표시 문자열이다. `apps/desktop-ui/damage-log-adapter.js:712`의 `sourceText`가 `skill:<캐릭터>:<함수>`만 이름으로 바꾸고 다른 source는 그대로 반환한다. 이 때문에 OL source의 캐릭터 코드가 보인다.
- 사용자 확인(2026-09-29): 위 원천 키 표시가 내부 키 예외인지 질문했고 **“화면에서는 이름으로 표시해야 함”**이라는 답변을 받았다. 따라서 일반 근거 문구의 OL source 노출을 **F2-Q-2 수용 차단 결함으로 확정**한다. API/저장 내부 키는 계속 보존한다. 서버 진단의 구조화 필드 경로(`combatProfiles.characters.5004.bonusRangeMin`), DOM 데이터 속성·타격/함수/replay 번호는 원래 허용 범위로 기록했다.
- 근거: `f2-ufix3-554048887882/browser-audit.png`, `summary.json`의 `U-FIX-3 no character codes browser-audit`, `f32-b2-44bc8203db35/summary.json`의 동일 원인5건. `trace.zip`과 실제 요청/응답도 보존했다. 총57개 화면 상태의 본문 스캔 중51개 통과, 위6개는 같은 원인이다.
- 수정 수용 조건: API/저장 source 및 데이터 속성은 보존하고 일반 화면의 OL 공격력 출처를 한글 이름/장비 부위/줄 설명으로 표시한다(예: 앨리스 · 머리 · 1번 줄 · 공격력). 실제 기존 저장 replay에서 새 계산 없이도 표시를 확인하고 client_f32/과거 정책·3개 폭·저장값 불변을 재검한다. QA는 제품을 직접 수정하지 않았다.

## 보존과 미판정

- 공개 입력/roster/presentation hash 불변. 미추적 `package-lock.json` SHA256 **`2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767`** 유지, 커밋 제외.
- 원본 `data/local`·계정·세션·캐시·EXE·5180/5181 미접촉, 다른 worktree 편집 없음. 사용자 실제 실행 경로는 계속 `C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe`이며 이번에는 실행/갱신하지 않았다.
- 부하/Q-CPU-10K/GPU/배포/push/새 worker/Run/Dispatch/lifecycle 수행 없음. 원본 배포 완료를 주장하지 않는다.
- 실게임 경계 가설·실사용자 덱·장시간/대량 실험·1000행 초과 DEF 설명·전환/무전환이 섞인 다수 run·모든 역사 저장 형식·미확인 캐릭터 전체 카탈로그는 이번에 확장 검증하지 않았다. 화면 코드 검사는 실제 합성5인과 하란 예외가 나오는 화면 상태를 대상으로 했다.
- 통합 근거 목록: `artifacts/single-deck-qa/f2-ufix3-preparation/evidence-index.json`. 보고서와 QA 도구의 확정 커밋을 기존 Director 터미널에 한 번 인계한다.

## 이번 재현 명령

```text
<dotnet> build src/Nikke.Api/Nikke.Api.csproj -c Release --no-restore
<dotnet> run --project tests/single_deck_compute_qa/DefenseProbe/Probe.csproj -c Release -- artifacts/single-deck-qa/f2-ufix3-preparation/engine-results.json
<python> tests/single_deck_compute_qa/check_defense_probe.py artifacts/single-deck-qa/f2-ufix3-preparation/engine-results.json
<python> tests/single_deck_compute_qa/check_f2_conditions.py --dotnet <dotnet>
<python> tests/single_deck_compute_qa/check_f32_b2.py --dotnet <dotnet> --f2-legacy-regression
```

이번 재검에서는 `--reuse` 없이 API 로그·실험·브라우저를 새로 실행했다.

---

# 이전 F2-Q 최초 판정 — 역사 기록 (제품 dae1949 / QA09c9d8a)

아래는 U-FIX-3 전의 기록이다. 현재 판정은 위 재수용 절을 따른다. 아래 F2-Q-1 차단은 이번 재검에서 해소됐다.

**최종 판정: 전체 수용 차단.** 엔진 R4 산술·API 조건/저장/키·보스 데이터는 통과했다. 통계 화면의 DEF 카드가 자동 전환 실험에도 **“자동 20억 전환 없음”**이라고 표시하는 **F2-Q-1**을 UI 담당에게 수정 요청한다. 제품 파일은 수정하지 않았다.

## 기준과 경계

- Director `combat-conditions-cleanup-assignments-2026-09-29.ko.md` 전체, 요구 원문 `user-requests-2026-09-29.ko.md`, 엔진 `def-switch-engine.ko.md`, Backend 조건/한국어 보스 보고서, UI `combat-conditions-cleanup-ui.ko.md`, 공통 보존·확정 wire를 읽었다.
- 착수 HEAD `d71c7a2`에서 `git merge --no-edit dae1949` 실행: fast-forward. 자기 QA 이력과 엔진 `1a86ec9`, Backend `aa1b71e`·`b977e77`, UI `dae1949`를 모두 보존했다. 검수 변경은 `tests/single_deck_compute_qa/**`와 이 보고서뿐이다.
- 담당 테스트·검사 스크립트·mock·golden/oracle를 사용하지 않았다. 자체 C# 입력, 이전에 작성한 Fraction 기반 IEEE754 binary32 계산기, 자체 HTTP/Chromium 검사로 판정했다. 준비 스크립트 두 개는 지시대로 실행했다.
- 공개 데이터 12파일을 기존 **본인** 공개 fixture에서 복사하고 새 합성 계정/DB를 작성했다. roster는 공개 manifest의 고정 hash를 확인했다. 본인 격리 presentation에 보스 43개·이미지 42개를 새로 준비했다. 속성/무기 아이콘과 한국어 presentation도 본인의 기존 공개 자원 사본만 사용했다.
- 본 측정은 합성 입력의 소규모 기능 검사다. 최대 batch n=2, worker1. 자동 튜닝/캐시는 기능 연결만 확인했고 속도·순위·개선율을 비교하지 않았다. 1천/1만/5만 부하, GPU 실행, 추가 OL 실험은 하지 않았다.
- 원본 `data/local`, 계정·세션·캐시, 5180/5181, EXE, 다른 worktree는 건드리지 않았다. 배포/push/새 worker/Run/Dispatch/lifecycle 호출 없음. 사용자 실행 경로는 계속 `C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe`이며 이번 검수에서 실행·배포하지 않았다.
- 미추적 `package-lock.json` 보존·커밋 제외. 전후 SHA256 `2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767`. 공개 입력/roster/사용한 presentation hash 불변. 자신이 시작한 API는 모두 종료했다.

## 독립 근거와 결과

모든 경로는 `C:/Users/user/orca/workspaces/Nikke-Simul/검수/` 기준이다. artifacts는 Git 제외 파일로 현 작업공간에 보존한다.

| 범위 | 결과 | 근거 |
|---|---|---|
| 실제 API Release 빌드 | 경고 0·오류 0 | `artifacts/single-deck-qa/f2-preparation/api-build.log` |
| 자체 엔진 입력 10개·41타격 | **87/87** | `f2-preparation/engine-results.json`, `engine-audit.json` |
| F2 실제 API + Chromium | **178/179**, F2-Q-1 실패 | `artifacts/single-deck-qa/f2-2a4bc7b9cd59/summary.json` |
| 기존 client_f32·통계 회귀 | **91/91** | `artifacts/single-deck-qa/f32-b2-fc9907125f58/summary.json` |
| F-COND 손상 profile 회귀 | **19/19** | `artifacts/single-deck-qa/f2-cd6824626940/summary.json` |

전체 **376개 검사 중 375 통과, 제품 결함 1개**다. 개별 검사와 내부 hit 수를 합산해 표본 수로 부풀리지 않았다. client_f32 91개에는 기존 n=0 표시 경계 검사 1개와 명시적 HTTP503/transport 장애 주입이 포함된다. n=0 실제 API 표본이나 자연 발생 503 검증으로 주장하지 않는다. API 응답을 mock으로 대체하지 않았다.

실제 포트: F2 최종 57367(이전 수집/재개 포트는 summary와 API 로그에 기록), client_f32 63897, 손상 profile 62488. 보호 포트와 다르며 모두 본인 생성 프로세스만 종료했다.

### R4 — 독립 경계 산술/API: 통과

- 독립 C# 입력은 공격력·계수·사격 수·추가타를 직접 구성한다. 기대 피해는 제품 계산기를 호출하지 않고 Python `Fraction`의 각 연산 binary32 반올림과 정수 누적합으로 구한다. 제품이 출력한 DEF 플래그를 기대값으로 쓰지 않고 이전 타격까지의 독립 누적합으로 DEF를 선택한다.
- 누적 **1,999,999,872** 및 정확히 **2,000,000,000**에서 전환 없음.
- 같은 프레임 멤버 a=2,000,000,000 → b=1로 **2,000,000,001** 도달. b는 DEF30925, 다음 멤버 c는 DEF31784로 **141 피해**. `>`와 `>=`를 구별했다.
- SG 6펠릿: 4번째까지 정확히 20억, 5번째가 초과시키고 6번째부터 전환. 추가타, frame0 스킬, 동일 프레임 순서, 단일 전환 trace, 팀=멤버 합, replay=PreparedSkillReplay summary를 확인했다.
- fixed에서 client_f32와 과거 3정책의 단순 산술을 각각 검산했다. 자동 모드와 fixed의 실행 상태가 섞이지 않는다.
- 실제 공개 5인/레벨400/180초/거리35/약점Fire, crit off, 지연 1프레임 고정, **QA 합성 +6300% 공격력 창**의 모든 피해 **19,462건**을 독립 검산했다. 실사용자 덱이 아니다.
- 독립 팀 합 **24,007,922,311** = 구성원 합 = replay = CPU compute 2회. 전환은 **frame750 / hitTraceId3076 / hitOrdinal1543 / 앨리스5004 / 누적2,013,492,851**. 초과 타격까지30925, 다음 타격부터31784. 저장 전환 DTO 전체가 독립 값과 일치했다.
- 근거: `f2-2a4bc7b9cd59/independent-prefix-audit.json`, `crossing-{캐릭터ID}.json`, `automatic-batch.json`. API 직접 비교는 명시 replay와 같은 택틱 조건을 쓰도록 compute `useSavedTactic:false`를 지정했다. 별도 브라우저 통계는 실제 저장 택틱을 사용하는 정상 경로로 확인했다.

### 조건 wire·저장·키: 통과

- 생략 기본값 10800프레임·per_trigger·team_damage_threshold·DEF30925·crit sample. 유효 숫자로 보낸 enemyDefense는30925로 정규화한다.
- 잘못된 시간/샷건/DEF모드/타입·null·대소문자·crit·bossId·profile의 **18종×2 API=36개 HTTP400**, 계산·저장 증가 없음.
- 새 `battleConditions` 저장/GET, replay `result.defense`, compute `runs[].defense` 보존.
- 본인의 F2 이전 API DLL을 새 빌드 전에 별도 보존했다(`f2-preparation/baseline-api`, `baseline-hashes.json`). 동일 새 합성 계정으로 fixed31784/120프레임/per_pellet/crit off를 실행하고 새 API의 `conditionProfile:legacy`와 비교: **총6,573,008 및 전체 멤버·effect 정확 일치**. 이전 버전은 `p03.skills.4-boss-conditions`다.
- 이전 저장 JSON의 GET/export 바이트와 파일 hash 불변. `/battle-conditions`는 legacy/120프레임/31784를 표시하며 파일을 재작성하지 않는다.
- 자동/fixed의 input fingerprint와 튜닝 키가 다르다. 보스만 바꾼 두 자동 실험은 피해·input fingerprint·튜닝 키가 같고 두 번째는 `validated_policy_cache`를 사용한다. 근거 `keys.json`.

### R8 보스: 통과

- 확정 사용자 목록과 API 한국어 43개(더미+1~42) 일치, `complete=true`, 제외/diagnostics0. 37 울트라, 35 크리스탈 체임버, 42 앨트루이아 확인.
- 42개 실제 이미지 HTTP 바이트 = 새 격리 파일 바이트. URL은 불투명32자리 파일명. 실제 Chromium에서 42개 이미지 모두 naturalWidth>0, 카드 43개 이름이 API와 일치했다.
- API boss 객체는 id/name/imageUrl/season만 제공. 영어 보스 이름·원본 monster ID·원천 URL/hash를 노출하지 않고 내부 manifest/source 경로는404다. 공개 선택 id `solo-raid-N`은 정상 계약 식별자다.
- 더미 기본, 정책 아래 배치, 선택/키보드/ESC/포커스 복귀, replay·compute 최상위 bossId 및 저장값/화면 값 일치. 표시·저장 전용이며 계산에는 영향을 주지 않는다.
- 시즌 대응 원천을 QA가 새 웹 조사한 것은 아니다. 사용자가 확정한 목록의 데이터 전달·렌더를 검증했다. 시즌42는 사용자 확정이며 웹 대응 확인을 주장하지 않는다.

### 화면 및 기존 회귀

- R1: 삭제 대상 설명 없음, 상단 약점 경고 유지, 다섯 속성/현재값 한국어만, 실제 이미지·멤버 미리보기.
- R2: 무기군6행 아이콘+이름, “적정 사거리”, “하란:25–45”, RL0–0, 코드/영문 예외/출처/sha/잠정 문구 없음. 공개 roster로 멤버별 거리35 미리보기를 독립 대조했다.
- R3/R5/R6/R7: 시간/DEF/샷건 입력 없음, 180초/per_trigger 요청, 크리 기본 확률 적용, client_f32 기본과 과거3정책 선택 유지.
- R4 replay: 무전환·실제 초과 전환의 DEF/시각/멤버/누적 표시 일치. legacy의 당시2초/31784/per_pellet/크리끔 표시. **통계 DEF 카드 설명은 아래 결함**.
- 1500/850/500에서 폼·거리/약점/보스 팝업·전환 결과·n1/n2 통계의 가로 넘침/팝업 영역 검사 통과. 대표 스크린샷을 직접 열어 확인했다. JS 예외0, 앱 화면 Nikke-Local-Lab 표기 없음.
- 실제 client_f32 회귀91: 십진 raw 문자열·과정밀 거부·큰 홀수 exact 정수·계산 불가3후보·v2 conversion·4정책·audit·레벨400·버스트·저장/export·n1/n2 독립통계·4xx 연결 유지·네트워크 장애/복구. 기존 짧은 시나리오는 새 `--f2-legacy-regression` 옵션으로 **나가는 요청만 명시 legacy**로 바꾸어 검증했다. 새 기본값 수용과 구분한다.
- 손상 profile: min/max/element 필드 누락 각각 runtime조회/멤버조회/replay/compute **12개 구조화409**, 저장 증가0, 실제 한국어 오류·통계 연결 유지. 0채움/500 없음. 전체 이전 16종 행렬 재실행을 주장하지 않는다.
- 통계 n1·n2 화면 값과 실제 API 일치, no-baseline 표시/연결 유지, 페이지 재로드로 저장 실험 복구. screenshot의 실행 횟수 입력1000은 복구 시 폼 기본값이며 이 검사에서1000회를 실행하지 않았다.

## 차단 결함 F2-Q-1 — UI 통계 DEF 설명이 새 모드와 모순

**수정 담당: F2-U(UI). 우선순위: R4 수용 차단. 엔진/Backend 계산 결함은 관측하지 않았다.**

- 최소 재현: 자동 모드의 실제 compute 실험 완료 → `단일 덱 통계` → `덱과 실행 조건` → `DEF 정책` 카드.
- 실제 관측: 값 `team_damage_threshold:30925:2000000000:31784` 아래 **“자동 20억 전환 없음”**. 바로 옆 전투 조건 카드는 자동 전환을 설명한다.
- 특히 `automatic-batch.json`의 두 결과는 총24,007,922,311, `runs[].defense.finalDefense=31784`, 전환frame750을 저장했는데도 같은 잘못된 문구가 나온다. 이는 단순히 이번 표본이20억 미만이라는 안내로 해석할 수 없다.
- 원인 위치: `apps/desktop-ui/single-deck-stats.js:56`의 `metricCard('DEF 정책', ..., '자동 20억 전환 없음')` 고정 문구. 실험 실행 전 fallback도 기존 고정 DEF 문구를 사용한다.
- 근거: `f2-2a4bc7b9cd59/defect-F2-Q-1.json`, `defect-F2-Q-1.png`, `trace.zip`, `summary.json`의 실패1건.
- 수정 수용 조건: 새 예정/저장 자동 모드는 자동20억 **초과 후 다음 타격 전환** 정책을 설명하고 “전환 없음/고정”으로 단정하지 않는다. 과거 fixed 저장본은 당시 고정 DEF 설명을 유지한다. 실제 자동 전환 있음·없음과 legacy fixed를 각각 실제 API+브라우저에서 재검하고 저장/조회·n1/n2 통계 회귀를 유지한다. QA는 제품을 직접 수정하지 않았다.

## QA 도구 보완과 미판정

- 초기 자체 검산기의 선택값 `rawRate10000:null` 처리 누락을 보완했다. 원래 수집한 실제 로그를 같은 제품·같은 입력으로 재검산했고 개별 prefix 오류0을 확인했다.
- 초기 replay/compute 총합 비교는 compute 기본 `useSavedTactic:true`가 저장 택틱을 주입하여 서로 다른 조건이었다. 명시 조건을 맞춘 최종 실행에서 총합/전환 모두 일치했다. 이 초기 실패는 제품 결함으로 올리지 않았다.
- 초기 복구 검사가 화면에 노출되지 않는 batch ID를 찾다가 대기 만료했다. 실제 저장ID/GET/입력 fingerprint로 확인하도록 QA 판정기를 고쳤고 최종 복구는 통과했다. 이전 시도는 `prior-attempt-*.json`에 보존한다.
- 실제 게임에서의 20억 경계 타격 순서·사거리 양끝 포함은 여전히 가설/사용자 확인 대기다. 이 보고서는 구현 계약 수용이며 게임 실측 수용이 아니다.
- 실사용자 덱, 원본 배포본 UI/EXE, 모든 역사 저장 형식, 장시간 성능, GPU/worker 최적성, Q-CPU-10K, 원본 통합/빌드/배포는 미실행·미판정이다. UI F2-Q-1 수정 확정 커밋 후 재수용이 필요하다.

## 재현 명령

작업 디렉터리는 본인 검수 worktree. Python/SDK는 세션의 기존 실행 파일을 사용한다. `<dotnet>`/`<python>`은 해당 실행 파일 절대 경로다.

```text
<dotnet> build src/Nikke.Api/Nikke.Api.csproj -c Release --no-restore
<dotnet> run --project tests/single_deck_compute_qa/DefenseProbe/Probe.csproj -c Release -- artifacts/single-deck-qa/f2-preparation/engine-results.json
<python> tests/single_deck_compute_qa/check_defense_probe.py artifacts/single-deck-qa/f2-preparation/engine-results.json
<python> tools/data-pipeline/prepare_solo_raid_bosses.py --presentation-root artifacts/single-deck-qa/f2-preparation/presentation
<python> tests/single_deck_compute_qa/check_f2_conditions.py --dotnet <dotnet>
<python> tests/single_deck_compute_qa/check_f32_b2.py --dotnet <dotnet> --f2-legacy-regression
<python> tests/single_deck_compute_qa/check_f2_profile_regression.py --dotnet <dotnet>
```

`check_f2_conditions` 내부가 새 runtime에 `prepare_combat_conditions.py`를 실행한다. F2 이전 빌드 비교에는 보존한 `f2-preparation/baseline-api`가 필요하다. 이번 최종 F2 실행은 `--reuse artifacts/single-deck-qa/f2-2a4bc7b9cd59`로 동일 제품의 기존 자체 수집 로그를 보존·재검산하면서 compute/브라우저를 새로 실행했다. 이 옵션은 다른 제품 버전으로 바뀐 후 사용하면 안 된다.

Director 기존 터미널에 이 보고서가 포함된 확정 QA 커밋과 위 판정을 한 번 인계한다. lifecycle 완료 신호는 사용하지 않는다.
