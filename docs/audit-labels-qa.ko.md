# U-FIX-7 QA 3차 차단 수정 재수용 — 통과 (2026-10-02)

**최종 판정: U-FIX-7 독립 QA 수용, 차단0.** 대상 UI **`42f4329`**. U7-Q-4·5 및 ESM 구문 회귀, 이전 U7-Q-1·2·3과 F2 수용 항목을 모두 통과했다. 새 실행 **1,364/1,364 통과**. 이는 격리 환경의 제품 검수 완료이며 원본 통합·EXE 배포 완료가 아니다.

## 기준·실행 독립성

- 검수 AGENTS·상태/로그·이전 QA `e98577c`, UI 보고서 6절, Director 진행 표를 확인했다. `git merge --no-edit 42f4329`로 정상 병합, 충돌0. 병합 커밋 **`79fd342539671bb94a43586d38d80971a9d6a4bc`**.
- 구현/리뷰 검사·mock·정답 및 `tests/ui/esm_syntax.test.mjs`는 실행하거나 가져오지 않았다. 기존 **검수 소유** 재현·회귀 도구를 새 격리 API·dataRoot·Chromium에서 실행했다. [새 ESM·주요 화면 검사](../tests/single_deck_compute_qa/check_ufix7_modules.py)는 독립 작성했다.
- `5243062..42f4329`의 제품 `src`·`tools` 변경0. API는 기존 검수 Release DLL을 사용하고 R4 엔진 probe를 새로 실행했다. ESM 검사는 이 worktree의 실제 JS 바이트를 `node --input-type=module --check`의 stdin에 공급했다. 제품 코드 수정0.
- 이전 허용 목록 전환에서 합의한 기대값을 유지했다. 이번에는 기존 검사 기대값을 바꾸지 않았고, 상속 속성 키와 모듈·화면 검사만 추가했다. 손상 저장 사본·API 필드 주입은 자연 발생 서버 데이터라고 주장하지 않는다.

## U7-Q-4·5 수용

| 경로 | 독립 관찰·판정 |
|---|---|
| 장치 사유 | `constructor`, `toString`, `__proto__`, `hasOwnProperty`, `valueOf`, `__defineGetter__`, `isPrototypeOf` 모두 **기타 사유**. 함수·객체 표현 없음. 정상 `gpu_unavailable`→GPU 사용 불가 유지 |
| 조건 팝업 무기군 | 같은 7키 모두 **무기군 미확인**. 함수/객체 이미지 경로와 화면 문자열 없음. 정상 SMG→기관단총, 사거리·인원·조작 유지 |
| 피해 검산 단계 이름 | 처음 5개 상속 키 모두 **기록된 계산 항목**. 원값은 `data-term`·저장 JSON에만 유지, 실제 GET 바이트 동일 |
| 미등록 조건 mode | 이전 실제 저장 사본 재현의 `qa_unknown_mode`·혼합 label 모두 미노출. 정상 거리35·약점 작열·이전 방식 적용/미적용 보존 |
| 저장 전투 조건 label | 등록 `이전 방식(고정 방어력)` 보존, `검사 필요: terms[0].operation`·`constructor`는 일반 **전투 조건**. 2초·방어력30,925 및 저장/API 바이트 보존 |

기존 U7-Q-4/5의 6개 실패를 동일 기대값으로 재실행해 모두 통과했다. 상속 키 확장 포함 허용 목록 화면 검사 **103/103**. 근거 `f2-ufix6-2b9a4aac86c3`의 `hardware-*.json/png`, `weapon-*.json/png`, `compatibility-*.json/png`, `trace.zip`. 피해 단계 이름·저장 전투 label 확장은 `f2-ufix6-aeab59956897/audit-name-*.json`, `battle-label-*.json`.

## ESM 구문·실제 앱 로드 수용

- `apps/desktop-ui/*.js` **18/18파일** ESM 구문 통과. 실패 대조군으로 `git show a92e454:apps/desktop-ui/local-lab-detail.js`의 실제 바이트를 같은 파서에 공급해 **4행 Unexpected reserved word**를 검출했다. 일반 `node --check` 결과로 대체하지 않았다. Node v24.16.0.
- 실제 격리 서버 `/editor/`가 HTTP200·`body[data-ready=true]`에 도달. JS **18개 응답 모두 worktree 바이트와 일치**, 같은 브라우저에서 18개 모듈을 실제 import해 이름 있는 import/export 연결까지 오류 없이 해석됐다. owner의 정적 import 검사 결과를 재사용하지 않았다.
- 홈·니케 관리·솔로 레이드·통계·고급 진단·가져오기 화면, 앨리스 상세의 머리/몸통/팔/다리 장비, 거리·약점 팝업, 실제 API 생성 replay의 그래프·타격 근거 표를 열었다. 이미지·DOM·trace 보존 및 주요 화면 육안 확인. 새 검사 **88/88**.
- **JavaScript 예외0·모듈 네트워크 실패0·모듈 콘솔 오류0.** 콘솔의 329개 오류는 모두 검수 합성 자료에 없는 `/editor/assets/*.png|jpg`의 HTTP404였다. module/API 오류와 구분했다(`http-error-resources.json`으로 요청 URL 전수 확인). 사용자 원본 자산을 복사하지 않았다.

근거: `f2-ufix6-aeab59956897/syntax.json`, `browser-imports.json`, `browser-load-observations.json`, `http-error-resources.json`, `main-*.png`, `local-lab-detail.png`, `trace.zip`.

## 이전 U7·허용 목록·과잉 차단

이전 예외 확장 **148/148** 통과(`f2-ufix6-ba6de4d699e8`). B3~B5 미등록 접미사·끝 개행·16진/2진 숫자는 표·카드 모두 미확인, 네 정책 정상 연산은 한국어 설명을 유지한다. 혼합 내부 경로(`terms[].name`, `terms[0].operation`, 실제 역슬래시 `runtime\catalog` 등)는 일반 안내로 바뀐다. null/빈 로그 11경로×7검사77/77, 오류 안내·그래프 복구·저장 보존 유지.

서버 실제 사용처에서 고른 등록 안내6종, 변경 이력의 알려진 이름·한국어 부위·200명, 수치1~10·180초·드라이버1.25, 거리 정수 검증, 일반 HTTP 오류 안내, 장치 해시를 다시 확인했다. 임의 서버 한국어는 등록되지 않으면 일반 문구라는 사용자 결정을 유지했다. 화면에서 만든 정상 수치·단위와 타격·발사·버스트 시전 번호, replay ID·fingerprint·버전·schema·정책 id·준비 스크립트는 보존됐다. 확인 범위의 과잉 차단0.

## 전체 회귀·최종 증거

모든 상대 근거 경로는 검수 `artifacts/single-deck-qa/` 기준이다. 최종 색인 **`ufix7-readmission4/evidence-index.json`**, 실행 귀속·DLL/lock 해시·제품 무변경 기록은 `provenance.json`. 기존 도구의 일부 제품 메타데이터와 `ufix6` 폴더 접두사는 이전 이름이지만, **아래는 모두 `42f4329` 병합 후 새 실행**이다. 이전 PASS 결과를 복사하지 않았다.

| 새 실행 | 통과/전체 | 근거 폴더 |
|---|---:|---|
| 검산 표·operation·버스트·export | 210/210 | `f2-ufix6-f157d415908f` |
| 전수 예외 화면 | 37/37 | `f2-ufix6-35fab59279a9` |
| 누락 단계·로그 실패 최소 재현 | 13/13 | `f2-ufix6-f5ba176649af` |
| 기존 같은 유형 확장 | 148/148 | `f2-ufix6-ba6de4d699e8` |
| 허용 목록·상속 키 확장 | 103/103 | `f2-ufix6-2b9a4aac86c3` |
| ESM·주요 화면·추가 저장 필드 | 88/88 | `f2-ufix6-aeab59956897` |
| F2 API·Chromium·DEF6·보스·조건 | 332/332 | `f2-ufix6-626a091524e8` |
| client_f32·통계·복구 | 75/75 | `f32-b2-e290cec598be` |
| source17종·네 정책·GET/export | 155/155 | `f2-ufix6-548bd2d285bd` |
| 진단·실제400/409·손상 profile | 104/104 | `f2-ufix6-080b7d93104f` |
| 기존 F2-Q-3·4 archive | 12/12 | `f2-ufix6-045d2a40a837` |
| R4 엔진10입력·41타격 독립 산술 | 87/87 | `ufix7-readmission4/engine-audit.json` |

- 직전 QA **1,253개 모두 같은 기대값으로 통과**, 원래 실패6개 포함·누락0(`previous-qa-coverage.json`). 추가111개 = 상속 키 확장23 + 모듈·주요 화면88. 이번 회차 재시도·제외 실행0(`attempt-index.json`).
- 기존 375목록의 범위 내317/317, 456목록의 범위 내390/390, `/legacy` 제외58/66·누락0(`regression-coverage.json`).
- **19,462타격 독립 산술 오류0**, 팀24,007,922,311 = 멤버 합 = 타격 합 = replay = compute. 방어 전환750프레임·누적2,013,492,851 유지. DEF6조합·보스43/이미지42·조건 wire·fingerprint·통계 회귀 통과.
- F2-Q-6 archive 총피해749,761,509·SHA256 `2ea1762e9e743a548cf56a6bdcc7709ed50804f24a3b96340bb4c6a9afbcac87` 불변. data-term·저장 operation·표 수치·GET/JSON/CSV export 보존. 허용 식별자 위치와 화면 스캔은 새 `identifier-inventory.json`, `visible-text-inventory.json`에 기록했다.

## 보존·미판정·확정 인계

- 본인 격리 API **18개 PID 전부 종료·프로세스 부재** 확인(`owned-process-cleanup.json`). 다른 서버는 종료하지 않았다. 공개 입력 hash 및 미추적 `package-lock.json` SHA256 `2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767` 보존·비커밋. QA 도구 구문 검사·`git diff --check` 통과.
- 제품 `apps`·`src`·`tools`는 `42f4329`와 동일. 원본 `C:/Users/user/Documents/GitHub/Nikke-Simul/data/local`·계정/세션/캐시·5180/5181 미접근. 사용자 EXE `C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe` 실행·갱신 없음. 제품 수정·새 워커·push·배포 없음.
- **미판정:** 실사용자 덱·실게임 실측·GPU 실행·부하/1만회·최적성·원본 EXE 배포/실행 수용. 부하 측정 보류 유지. 검수의 통과를 원본 배포 완료로 해석하지 않는다.
- 재실행: `run_ufix7_readmission.py --readmission4 --dotnet <SDK>`, `check_ufix7_allowlist.py --expanded --dotnet <SDK>`, `check_ufix7_families.py --allowlist --dotnet <SDK>`, `check_ufix7_modules.py --dotnet <SDK>`, 기존 R4 probe→독립 산술 검사. 최종 색인 `summarize_ufix7_readmission.py --readmission4`.
- 이 보고서를 포함하는 확정 QA 커밋의 전체 SHA·통과/차단/미판정을 Director 터미널 재조회 후 **한 번 인계**한다.

---

# 이전 QA — UI 5243062, QA e98577c (역사 기록)

아래는 3차 차단 기록이다. 최신 판정은 위 재수용 절을 따른다.

**최신 판정: 전체 수용 차단.** UI `5243062`에서 이전 U7-Q-1·2의 잔여 재현과 U7-Q-3은 수용한다. 새 검사에서는 **등록 객체의 상속 속성이 표시값으로 통과하는 경로(U7-Q-4)**와 **미등록 조건 모드 원값 출력(U7-Q-5)**이 남았다. 새 실행 **1,253개 중 1,247 통과·6 실패(2유형)**. 정상 등록 안내·수치·단위·유지 번호에서 확인된 과잉 차단은 없다. 아래 두 건은 기존 코드에도 있던 경로로, 이번 변경이 새로 만든 회귀라고 주장하지 않는다.

## 대상·독립성·기대값 변경

- QA `f5a8057`에서 `git merge --no-edit 5243062`, 충돌 0. 병합 커밋 **`e01ec8fca306772799fc750c60bc435171966cff`**. 검수 AGENTS·Git 상태/로그, UI 보고서 6절, Director 진행 표를 읽었다.
- 새 격리 API·dataRoot·Chromium으로 **검수 소유** 도구만 실행했다. [허용 목록 화면 검사](../tests/single_deck_compute_qa/check_ufix7_allowlist.py)는 독립 작성했다. 구현/리뷰 검사·mock·정답 및 등록 목록 생성기는 실행하거나 가져오지 않았다.
- 정상 안내 대조군은 UI 테스트나 생성 목록에서 추출하지 않고 제품 서버의 실제 사용처 `SnapshotNormalizer.cs`, `CalculationService.cs`, `CharacterEditService.cs`, `SyncCoordinator.cs`, `collector.py`에서 골랐다. 소스에 존재하는지도 검사했다.
- 사용자 결정으로 **미등록 한국어 문장도 일반 문구로 대체**해야 한다. 이전 QA가 임의 작성한 문장 4개(`앨리스의 머리 장비를 확인하세요.`, `배율 3.5배…`, `GPU를…`, `LV.5…`)의 허용 기대를 일반 안내 기대로 변경했다. 정상 수치·단위 보존을 이 임의 서버 문장과 혼동하지 않고 실제 UI·등록 문구에서 별도 검사했다. 이미지 상태 대체 안내 2개도 새 상태별 문구로 기대값을 갱신했다. 이 6개는 동일 기대값의 회귀 통과로 포장하지 않는다.
- `8da098f..5243062`의 엔진/API `src`·`tools`·기존 QA 코드 변경 0. 검수 Release API DLL 사용, R4 probe 새 실행. 제품 `apps`·`src`·`tools`는 `5243062`와 동일하게 유지했다. 실제 제공 JS와 API projectRoot는 기존 QA 경로 검사로 재확인했다.

## 이전 결함 재수용

| 항목 | 새 실제 API·브라우저 판정 |
|---|---|
| U7-Q-1 원래 접미사·상단 B3×B4×B5 카드 | `qa_unknown_transform`, `floor_if_qa_condition` 모두 표는 **저장된 연산 미확인**, 카드는 **미제공**. 추정 숫자 없음 |
| U7-Q-1 숫자/공백 경계 | `0x10`, `0b11`, 끝 개행 2종 모두 표·카드 미확인. 네 정책 정상 저장 단계 설명은 유지 |
| U7-Q-2 원래/잔여 혼합 문자열 | `effectiveAttack`, `effectiveDefense`, `calculation.terms`, `terms[].name`, `terms[0].operation`, `attackBuffs[0].source`, `cache/replays`, 실제 역슬래시를 포함한 `runtime\catalog`, `skill1Rate` 차단. 고급 진단 실제 DB/API·연결·검산 오류·장치 사유 확인 |
| U7-Q-3 null 로그 | 이전 전송 실패와 확장 11경로×7검사 **77/77**. 한국어 안내·JS 예외0·저장 보존·정상 그래프 복구 유지 |
| 저장 계약 | data-term·저장 operation·단계 입출력 수치·피해·GET/JSON/CSV export 보존 |

이전 확장 도구는 새 기대값 4개를 포함해 **148/148** 통과했다. 원래 차단 16검사는 전부 통과했다. 새 근거 `f2-ufix6-43854c583575`의 `factor-variant-*.json/png`, `mixed-*.json/png`, `log-*.json/png`, `trace.zip`.

## U7-Q-4 — 미등록 키가 등록 객체의 상속 속성으로 해석됨

위치: `apps/desktop-ui/display-labels.js:111` → `single-deck-stats.js:121`, `combat-conditions.js:100` → 거리 팝업. 일반 객체의 `MAP[key] ?? 일반문구` 접근은 명시 등록 키뿐 아니라 상속 속성도 반환한다.

| 실제 화면에 공급한 미등록 값 | 실제 표시 | 요구 동작 |
|---|---|---|
| 장치 `reason = constructor` | `function Object() { [native code] }` | `기타 사유` |
| 장치 `reason = toString` | `function toString() { [native code] }` | `기타 사유` |
| 장치 `reason = __proto__` | `[object Object]` | `기타 사유` |
| 무기군 `weaponType = constructor` / `__proto__` | 각각 위 함수 / 객체 표현 | `무기군 미확인` |

실제 격리 API의 hardware 응답 중 장치 사유 필드, combat-conditions 응답 중 무기군 필드만 QA가 주입했다. **프로토타입 변경이나 제품 코드 실행 주입은 하지 않았다.** 평범한 문자열 키 조회만으로 출력된다. 대조군 `gpu_unavailable`→`GPU 사용 불가`, `SMG`→`기관단총`, 임의 미등록 일반 키→한국어 일반 문구는 통과했다. 따라서 누락 원인은 상속 속성까지 포함한 조회이며, 허용 목록 등록 키와 구분해야 한다.

근거: `f2-ufix6-851c0acf394e/hardware-3.json/png`, `hardware-4.json/png`, `hardware-5.json/png`, `weapon-2.json/png`, `weapon-3.json/png`, `trace.zip`. 화면을 직접 확인했다. 장치 식별 해시·드라이버·사거리·인원은 보존됐다. **5개 실패, 같은 원인 1유형**.

## U7-Q-5 — 미등록 조건 모드가 일반 안내 뒤 괄호에 그대로 출력됨

위치: `apps/desktop-ui/combat-conditions.js:162`, `describeCompatibility`의 미등록 mode 분기. label은 허용 목록으로 처리하지만 `(${compat.mode})`는 원값이다.

1. 실제 API가 생성한 로그 포함 replay의 QA 저장 사본을 만든다.
2. `conditionCompatibility.mode = qa_unknown_mode`, `label = 검사 필요: terms[].name`을 저장한다.
3. 사본을 실제 GET→일반 검산 화면으로 연다.
4. label은 차단되지만 **알 수 없는 조건 모드 (qa_unknown_mode)**가 표시된다. 미등록 mode는 일반 한국어 안내만 보여야 한다.

정상 `per_member`의 거리35·약점 작열, `legacy_global`의 적정 거리 적용·우월 코드 미적용은 통과했다. mode는 사용자 확정 유지 번호(정책 id·schema·버전 등)에 해당하지 않는다. 저장 JSON과 API 바이트는 변하지 않았다.

근거: `f2-ufix6-851c0acf394e/compatibility-3.json/png`, `data/skill-replays/`의 해당 사본, `trace.zip`. **1개 실패, 1유형**.

## 허용 목록·과잉 차단 검사

새 허용 목록 검사 **80개 중 74 통과·6 실패**. 위 두 유형 외에는 다음 범위를 통과했다.

- **고급 진단 실제 DB/API:** 서버에서 사용하는 정확한 안내 6개 보존. 예: `스킬 레벨은 1~10입니다.`, `4부위 입력이 필요합니다.`, 로그인 세션 만료 안내. 배열/파일 경로·임의 한국어·등록 문구 뒤 내부 키·끝 개행·앞 공백은 일반 수집 안내. `data-issue-path`·DB 원문 보존.
- **최근 변경:** 계정 스탯/큐브·스펙 변경 없음·최초 수집200명, 알려진 앨리스 이름·머리 장비 표시 유지. 모르는 이름은 이름 미확인 니케, 미등록 템플릿은 일반 변경 안내. 저장 원문 보존.
- **연결 실패/검산 HTTP 400:** 등록 안내와 1~10 수치 보존, 미등록·변형 5종은 일반 안내. 서버 응답의 임의 `display:true`로 표시 허용을 우회할 수 없음. 등록 오류 코드의 한국어 180초 의미 유지.
- **장치:** 정상 등록 사유·탐지 안내, 미등록 일반 문구, 장치 해시·드라이버1.25 유지. 상속 속성 예외는 위 차단과 분리한다.
- **조건 팝업:** 0~100 정수·45–100 범위·인원과 조작 유지. 실제 입력3.5에서 `보스 거리는 0~100 사이 정수로 입력하세요.` 안내 유지. 사거리는 원래 단위 없는 수치이므로 QA가 임의로 m를 붙이지 않는다.
- **피해 로그/정상 계산 화면:** 초·프레임·퍼센트·배율·정책 id·schema, 타격·발사·버스트 시전 번호와 replay ID 보존. 기존 전수 예외 검사에서 HTTP 503 export 안내와 이미지 상태별 한국어 문구도 통과.

최초 새 검사 시도는 양성 문구 소스 목록에 `CharacterEditService.cs`를 누락하고 거리 표시를 `35m`로 오인한 QA 오류를 수정한 후 재실행했다. 해당 시도는 최종 합계에서 제외했다. 제품 실패 6개는 수정 전후 같은 화면에서 재현됐으며, 양쪽 시도 JS 예외는 0이었다.

## 최종 회귀·보존·인계

모든 아래 상대 경로는 검수 `artifacts/single-deck-qa/` 기준이다. 최종 색인 **`ufix7-allowlist/evidence-index.json`**, 실행 귀속·제품 무변경·DLL/lock 해시는 `provenance.json`. 일부 기존 도구의 `b401421`/`59fe22d` 메타데이터·`ufix6` 폴더 접두사는 남아 있지만 **옛 PASS 결과를 재사용하지 않았으며 모두 `5243062` 병합 후 새 실행**했다.

| 새 실행 | 통과/전체 | 근거 폴더 |
|---|---:|---|
| 기존 검산·operation·버스트·export | 210/210 | `f2-ufix6-3bd7d155377d` |
| 전수 예외 화면 | 37/37 | `f2-ufix6-fca15d7fd532` |
| 누락 단계·로그 실패 최소 재현 | 13/13 | `f2-ufix6-dea7e0d2f78b` |
| 이전 같은 유형 확장 | 148/148 | `f2-ufix6-43854c583575` |
| 새 허용 목록 화면·정상 대조군 | 74/80 | `f2-ufix6-851c0acf394e` |
| F2 API·Chromium·DEF6·보스·조건 | 332/332 | `f2-ufix6-af96ab54e427` |
| client_f32·통계·복구 | 75/75 | `f32-b2-6d94ac451202` |
| source17종·네 정책·GET/export | 155/155 | `f2-ufix6-c7b60018de6f` |
| 진단·실제400/409·손상 profile | 104/104 | `f2-ufix6-668abea89a26` |
| 기존 F2-Q-3·4 archive | 12/12 | `f2-ufix6-f80e1dc40e6d` |
| R4 엔진10입력·41타격 독립 산술 | 87/87 | `ufix7-allowlist/engine-audit.json` |

- 직전 QA의 **1,173개 의무를 모두 새 실행에 대응**, 누락0. 동일 기대1,167개와 앞서 밝힌 의도적 변경6개를 구분한다(`previous-qa-coverage.json`). 원래 차단16개 전부 통과. 기존 375목록의 범위 내317/317, 456목록의 범위 내390/390, `/legacy` 제외58/66·누락0(`regression-coverage.json`).
- **19,462타격 독립 산술 오류0**, 팀24,007,922,311 = 멤버 합 = 타격 합 = replay = compute. DEF 전환750프레임·누적2,013,492,851 유지. DEF6·보스43/이미지42·조건 wire·fingerprint·통계 회귀 통과.
- F2-Q-6 archive 총피해749,761,509·SHA256 `2ea1762e9e743a548cf56a6bdcc7709ed50804f24a3b96340bb4c6a9afbcac87` 불변. 허용 식별자 위치·화면 스캔은 새 `identifier-inventory.json`, `visible-text-inventory.json`에 보존했다.
- 본인 격리 API **18개 PID(재시도 포함)** 종료·프로세스 부재 확인(`owned-process-cleanup.json`). 공개 입력 hash와 미추적 `package-lock.json` SHA256 `2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767` 보존·비커밋. QA 도구 구문 검사·`git diff --check` 통과.
- 원본 `C:/Users/user/Documents/GitHub/Nikke-Simul/data/local`·계정/세션/캐시·5180/5181 미접근. 사용자 EXE `C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe` 실행·갱신 없음. 제품 수정·새 워커·push·배포 없음.
- **미판정:** 실사용자 덱·실게임 실측·GPU 실행·부하/1만회·최적성·원본 EXE 배포/실행 수용. 부하 측정 보류 유지.
- 재실행: `run_ufix7_readmission.py --allowlist --dotnet <SDK>`, `check_ufix7_families.py --allowlist --dotnet <SDK>`, `check_ufix7_allowlist.py --dotnet <SDK>`, 기존 R4 probe→독립 산술 검사. 색인 `summarize_ufix7_readmission.py --allowlist`. `--allowlist` 없는 이전 기대값도 보존했다.
- 이 보고서를 포함하는 확정 QA 커밋·통과/차단/미판정을 Director 터미널 재조회 후 **한 번 인계**한다. 원본 배포 완료 보고가 아니다.

---

# 이전 재수용 QA — UI 8da098f, QA f5a8057 (역사 기록)

아래는 2차 판정이다. 최신 판정은 위 허용 목록 전환 절을 따른다.

**최종 판정: 전체 수용 차단.** UI `8da098f`에서 기존 U7-Q-1·2·3의 최소 재현은 모두 수정 수용한다. 다만 같은 유형 확장 검사에서 **상단 카드의 미등록 연산 배율 추정(U7-Q-1 잔여)**과 **한국어 문장에 섞인 배열 경로 등 내부 식별자 노출(U7-Q-2 잔여)**이 남았다. U7-Q-3은 확장 경로까지 수용한다. 새 실행 **1,173개 중 1,157 통과·16 실패(잔여 결함 2유형)**. 제품 코드 수정 0.

## 재수용 기준·실행

- QA `706d7fd`에서 `git merge --no-edit 8da098f` 실행, 충돌 0. 병합 커밋 **`89e903e3d20cb3112916781c4573650f76b4cbc6`**. 검수 AGENTS·Git 상태와 UI 보고서 6절·Director 지시서 진행 표를 다시 읽었다.
- 이전 **검수 소유** 최소 재현·회귀 도구를 새 격리 dataRoot/API/Chromium에서 재실행했다. [확장 검사](../tests/single_deck_compute_qa/check_ufix7_families.py)는 이번에 독립 작성했다. 구현·리뷰 검사, mock, 정답은 가져오거나 실행하지 않았다.
- 네 정책의 실제 POST→저장→GET→타격 근거 화면, 새 합성 DB의 issues→실제 snapshot API→고급 진단, QA가 작성한 전송/HTTP/필드 주입을 구분했다. 손상 operation·혼합 메시지는 자연 발생 사례로 주장하지 않는다.
- UI 표시 변경이며 `b401421..8da098f`의 `src`·`tools`·기존 독립 QA 도구 변경 0. API는 이전 QA가 빌드한 검수 Release DLL을 사용했고 R4 엔진 probe는 새 실행했다. `/api/health.projectRoot`·실제 제공 JS와 검수 worktree의 일치를 기존 검사에서 재확인했다. 제품 `apps`·`src`·`tools`는 검사 후에도 `8da098f`와 동일하다.

## 기존 최소 재현 수용

| 이전 결함 | `8da098f` 관찰·판정 |
|---|---|
| U7-Q-1 단계 표 | 두 원래 접미사 `qa_unknown_transform`·`floor_if_qa_condition` 모두 **저장된 연산 미확인**. 저장·data-term·수치·JSON/CSV export 불변. 최소 재현 수용, 아래 상단 카드 잔여는 차단 |
| U7-Q-2 고급 진단 | 실제 합성 DB의 `검사 필요: effectiveAttack`·`검사 필요: calculation.terms` 모두 한국어 대체 안내. 최소 재현 수용, 아래 배열 경로 잔여는 차단 |
| U7-Q-3 로그 전송 실패 | 실제 API로 만든 로그 미수집 replay의 fallback 요청만 전송 차단. 한국어 안내, JS 예외 0, 저장 불변. 수용 |

직전 QA의 **1,025개 검사 전부 새 실행에서 통과**했다. `previous-qa-coverage.json`에 이전 항목을 대응시켰다. 새 저장 사본의 무작위 replay ID를 포함하는 GET 검사 이름만 순서별로 정규화했고 실제 새 ID도 함께 기록했다. 이전 실패 5개 역시 모두 통과했다.

## 잔여 차단 근거

### U7-Q-1 잔여 — 같은 미등록 연산에서 표는 미확인, 상단 배율 카드는 숫자 단정

위치: `apps/desktop-ui/damage-log-adapter.js:670`·`:673` → `damage-log.js:103`. 단계 설명의 전체 문자열 검사는 고쳐졌지만, `buildDamageBreakdown`은 여전히 `^multiply\s+([^;\s]+)`로 앞부분만 읽는다. 따라서 UI 보고서 6절의 “접두사 검사는 남아 있지 않다”는 화면 전체에는 성립하지 않는다.

1. 실제 `nested_floor` 120프레임 로그의 검수 전용 사본을 만든다.
2. 첫 타격 B3·B4·B5의 operation만 `multiply 1.25; qa_unknown_transform`으로 바꾼다. before·after·damage는 바꾸지 않는다.
3. 실제 저장 GET을 일반 replay 경로로 열고 첫 타격 근거를 클릭한다.
4. 세 단계 설명은 **저장된 연산 미확인**, 같은 패널 상단 **B3 × B4 × B5** 카드는 **1.25 × 1.25 × 1.25**로 표시된다. `floor_if_qa_condition` 접미사도 동일하다.

카드 숫자는 별도 확정된 저장 배율이 아니라 위 미등록 operation에서 읽은 값이다. 등록되지 않은 연산에서 배율을 추정하지 않고 미확인으로 표시해야 한다. 계산/저장 피해 변조 결함은 아니다.

근거: `f2-ufix6-6b69b0dae9c5/factor-variant-0.json/png`, `factor-variant-1.json/png`, `trace.zip`. 저장 terms와 카드·단계 DOM을 함께 기록했고 실제 화면을 육안 확인했다. 사본/API 바이트 불변.

같은 계열 추가 관찰: 끝 개행 변형 두 개도 표는 미확인인데 카드에서 1.25로 해석한다. `multiply 0x10`·`multiply 0b11`은 단계와 카드가 각각 16·3으로 해석한다. 엔진의 `HitCalculator.cs:152`가 기록하는 `{factor:R}` 숫자 형태 밖의 표현까지 `Number()`가 허용하는 경계다. 이들은 별도 결함 수를 늘리지 않고 **등록 연산 전체와 숫자 표현을 일관되게 검증해야 하는 동일 유형**으로 기록했다. 주 차단은 원래 두 미등록 접미사만으로도 성립한다.

### U7-Q-2 잔여 — 배열 경로·경로 구분자·숫자 포함 내부 식별자가 한국어에 섞이면 노출

위치: `apps/desktop-ui/display-labels.js:76`의 `CODE_LIKE` → `koreanText`·`friendlyServerMessage`·`reasonLabel` 호출 화면.

새 합성 DB의 `snapshot.issues[].message`를 저장한 뒤 실제 API와 고급 진단에서 관찰했다.

| 실제 저장 message | 실제 표시 |
|---|---|
| `검사 필요: effectiveDefense` / `검사 필요: calculation.terms` | 한국어 대체 안내 — 통과 |
| `검사 필요: terms[].name` | 그대로 노출 — 실패 |
| `검사 필요: terms[0].operation` | 그대로 노출 — 실패 |
| `검사 필요: attackBuffs[0].source` | 한국어 대체 안내 — 통과 |
| `검사 필요: cache/replays` / `검사 필요: runtime\catalog` / `검사 필요: skill1Rate` | 그대로 노출 — 실패 |

배열 괄호 뒤의 점 경로는 현재 정규식에 잡히지 않는다. 동일한 `검사 필요: terms[0].operation`을 **연결 실패 안내·검산 HTTP 400 오류·장치 reason/probeFailures**에도 독립 주입했고 세 화면 모두 노출을 재현했다. `terms[].name`은 지시서가 금지한 구조 경로이며 유지 대상 번호나 수식이 아니다. 정상 한국어 문장과 `3.5배`·`GPU`·`LV.5`는 보존 통과했다.

근거: `f2-ufix6-6b69b0dae9c5/mixed-paths.json/png`, `data/accounts.db`, `mixed-connection.json`, `mixed-error.json`, `mixed-device.json`, `trace.zip`. DB 경로는 실제 API, 후자 세 화면은 QA 필드/오류 응답 주입이다.

## 확장 통과·회귀 결과

모든 경로는 검수 worktree의 `artifacts/single-deck-qa/` 기준이다. 최종 색인 **`ufix7-readmission/evidence-index.json`**. 아래는 모두 이번 제품에서 새로 실행한 결과이며, 도구의 이전 `b401421`/`59fe22d` 메타데이터·`ufix6` 폴더 접두사는 실행 귀속을 뜻하지 않는다.

| 실행 | 통과/전체 | 새 근거 폴더 |
|---|---:|---|
| 검산 표·미등록/누락 연산·버스트·export | 210/210 | `f2-ufix6-ae2573671670` |
| 전수 예외 화면·무기군·서버 원문 | 37/37 | `f2-ufix6-fb2566ec8c74` |
| 누락 단계·기존 로그 실패 최소 재현 | 13/13 | `f2-ufix6-cc9e23e62ab8` |
| 같은 유형 확장 | 132/148 | `f2-ufix6-6b69b0dae9c5` |
| F2 API·Chromium·DEF6·보스·조건 | 332/332 | `f2-ufix6-a802d51032e1` |
| client_f32·통계·복구 | 75/75 | `f32-b2-896756cc93ae` |
| source17종·네 정책·GET/export | 155/155 | `f2-ufix6-ba1535c559b2` |
| 진단·실제400/409·손상 profile | 104/104 | `f2-ufix6-10c58ecce8af` |
| 이전 F2-Q-3·4 archive | 12/12 | `f2-ufix6-64d10be5ecde` |
| R4 엔진10입력·41타격 독립 산술 | 87/87 | `ufix7-readmission/engine-audit.json` |

- 네 정책의 모든 저장 단계에 임의 접두사·접미사를 붙인 표 설명은 전부 미확인 처리, 정상 원문 대조군은 설명 유지, data-term·API/저장 바이트 보존(36검사). 위 카드·숫자 경계는 별도 차단이다.
- **null/빈 로그 11경로 × 7검사 = 77/77**: 미수집, 빈 HTTP 응답, HTTP 400·404·409·500·503, 전송 실패, 미지원 schema의 내장/별도 endpoint, 정상 피해 0. 한국어 상태, 그래프 생략, 서버 영문 오류 미노출, JS 예외 0, 미수집에서만 미리보기 opt-in, 저장 보존, 이후 정상 로그 그래프 복구 통과. 요청 URL·화면·오류 배열은 각 `log-*.json/png`에 보존했다.
- 독립 Fraction 산술 **19,462타격 오류 0**, 팀 **24,007,922,311** = 멤버 합 = 타격 합 = replay = compute. 방어 전환 750프레임·누적 2,013,492,851 유지. DEF6조합·보스43개/이미지42개·조건 wire·fingerprint 회귀 통과.
- 과거 375목록의 범위 내317/317, 456목록의 범위 내390/390. 명시 제외 `/legacy` 58/66, 누락0(`regression-coverage.json`). F2-Q-6 archive 총피해749,761,509·SHA256 `2ea1762e9e743a548cf56a6bdcc7709ed50804f24a3b96340bb4c6a9afbcac87` 불변.
- 유지 번호(타격·발사·버스트 시전·replay ID), fingerprint·버전·schema·정책 id·준비 스크립트·장치 해시는 수용 범주를 유지했다. `identifier-inventory.json`, `visible-text-inventory.json`에 기존 스캔을 새로 기록했다.

재시도 두 개는 최종 합계에서 제외했다(`attempt-index.json`). 첫 시도는 정상 피해 0 안내를 QA가 `피해 0`으로 찾은 잘못을 실제 문구 `피해 기록 0`으로 수정했다. 두 번째는 첫 미수집 화면의 30초 표시 대기 초과로 중단됐으며 JS 예외는 기록되지 않았다. 원인을 단정하지 않는다. 대기를 60초로 늘리고 실패 시 화면·trace 보존을 추가한 최종 전 범위 실행에서는 모두 완료됐고, 잔여 두 유형은 세 시도에서 반복됐다.

## 보존·미판정·확정 인계

- 본인 격리 API **20개 PID(재시도 포함)** 종료 및 프로세스 부재 확인: `ufix7-readmission/owned-process-cleanup.json`. 공개 입력 hash 보존, 미추적 `package-lock.json` hash `2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767` 불변·비커밋.
- 원본 `C:/Users/user/Documents/GitHub/Nikke-Simul/data/local`·계정/세션/캐시·5180/5181에 접근하지 않았다. 사용자 EXE `C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe` 실행·갱신 없음. 새 워커·push·통합 배포·제품 수정 없음.
- **미판정:** 실사용자 덱·실게임 실측·GPU 실행·부하/1만회·최적성·원본 EXE 배포/실행 수용. 부하 측정 보류 유지.
- 재실행: [run_ufix7_readmission.py](../tests/single_deck_compute_qa/run_ufix7_readmission.py) 및 [check_ufix7_families.py](../tests/single_deck_compute_qa/check_ufix7_families.py)에 `--dotnet <.NET 10 SDK 실행 파일>` 전달. 엔진 `DefenseProbe/Probe.csproj`→`check_defense_probe.py`, 색인 [summarize_ufix7_readmission.py](../tests/single_deck_compute_qa/summarize_ufix7_readmission.py). 제품에 대한 UI 소유 테스트는 실행하지 않는다.
- 이 갱신을 포함하는 QA 확정 커밋의 전체 SHA·보고서·통과/차단/미판정을 Director 터미널 재조회 후 한 번 인계한다. 원본 배포 완료를 뜻하지 않는다.

---

# 이전 QA 기록 — UI b401421, QA 706d7fd (역사 기록)

아래는 1차 판정이다. 최신 수용·잔여 차단은 위 재수용 절을 따른다.

**판정: 기존 F2-Q-6의 정상 저장본 표시 수정은 수용하나, U-FIX-7 전체 수용은 차단한다.** 미등록 곱셈 연산 추정, 한국어에 섞인 내부 키 노출, 로그 조회 실패 시 화면 예외의 세 경로가 남았다. **새 실행 1,025개 검사 중 1,020 통과·5 실패(결함 3개)**다. 제품 코드는 수정하지 않았다.

## 기준·독립성

- 검수 브랜치의 `AGENTS.md`, 상태·로그, 이전 QA `180f23b`의 [F2-Q 보고서](combat-conditions-cleanup-qa.ko.md), Director 지시서 QA 절·진행 표, 작업 구조, UI 보고서 2절·6절을 읽었다.
- `180f23b`에서 `git merge --no-edit b401421`을 실행했다. 이미 조상 관계여서 **fast-forward**, 충돌 0. 임의의 별도 merge 커밋을 만들지 않았다. 대상 제품은 배포 기준 `3d84fe4` 위 UI `b401421`이다.
- 구현·리뷰의 검사 스크립트·mock·정답은 실행하거나 가져오지 않았다. 기존 **검수 소유** 회귀 도구와 독립 Fraction 산술을 새로 실행했고, 신규 QA 도구 3개로 예외 경로를 작성했다. UI tests는 실행하지 않았다.
- 공개 allowlist 자료로 새 합성 계정 DB·runtime을 만들었다. 기존 검수 합성 replay만 읽기 전용 원본으로 사용했다. 정상 검산은 실제 격리 API POST→저장→Chromium 근거 화면, 과거/손상 저장본은 실제 GET→동일 화면이다. 손상 사본·전송 차단·일부 API 필드/오류 응답 주입은 QA가 새로 작성했으며 자연 발생 서버 응답으로 주장하지 않는다.
- 새 Release API 빌드: **경고 0·오류 0**. PATH의 SDK는 고정 버전이 없어 기존 `.tools/dotnet/dotnet.exe` SDK로 검수 경로만 빌드했다. `/api/health.projectRoot`와 실제 제공된 JS 바이트가 검수 worktree와 일치했다.
- `180f23b..b401421`의 `src`·`tools`·독립 QA 도구 변경 0. 검사 후에도 제품 `apps`·`src`·`tools`는 `b401421`과 동일하다.

## 차단 근거

### U7-Q-1 — 미등록 B3~B5 연산을 등록된 곱셈으로 추정

위치: `apps/desktop-ui/damage-log-adapter.js:398`, `:401`. 연산 문자열 전체를 검증하지 않고 `^multiply\s+([^;\s]+)`로 앞 숫자만 읽으며, 문자열 어디든 `floor`가 있으면 내림으로 설명한다.

실제 API가 생성한 `nested_floor` 결과의 **검수 전용 저장 사본**에서 첫 타격 B3·B4·B5의 operation만 변경한 뒤 실제 GET으로 열었다.

| 저장 operation | 실제 표시 | 수용 조건 |
|---|---|---|
| `multiply 1.25; qa_unknown_transform` | `× 1.25 곱함` | `저장된 연산 미확인` |
| `multiply 1.25; floor_if_qa_condition` | `× 1.25 곱함 (곱한 뒤 내림)` | `저장된 연산 미확인` |

엔진이 기록하는 정상 형태는 `multiply <factor>` 또는 `multiply <factor>; floor`다(`src/Nikke.Core/Combat/HitCalculator.cs:152`). 위 접미사는 등록 연산이 아니다. 단순 `qa_unregistered_operation`·null·operation 필드 누락은 네 정책의 실제 단계 모두 미확인 처리에 통과했다. 따라서 리뷰에서 고친 일반 미등록 분기는 수용하며 **숫자로 시작하는 곱셈 연산의 나머지 문자열 검사 누락**을 차단한다. 수치·저장 내용이 변한 결함은 아니다.

근거: `f2-ufix6-1b98cf7e1459/multiply-suffix-165.json`, `multiply-suffix-175.json/png`, `trace.zip`. JSON에는 저장 terms와 DOM 각 행을 함께 기록했다. 해당 사본의 GET·전체 JSON export·피해 로그 JSON/CSV 다운로드 바이트 및 data-term·표 수치는 보존됐다.

### U7-Q-2 — 한국어와 함께 온 내부 키·두 단계 경로가 그대로 노출

위치: `apps/desktop-ui/display-labels.js:76`, `:112~114` → `apps/desktop-ui/app.js:251`.

새 합성 계정의 `snapshot.issues[].message` 두 개를 DB에 직접 저장하고, 실제 snapshot API로 고급 진단을 열었다. API 응답 교체는 없다.

| 실제 저장 message | 실제 고급 진단 표시 |
|---|---|
| `검사 필요: effectiveAttack` | 그대로 노출 |
| `검사 필요: calculation.terms` | 그대로 노출 |

`CODE_LIKE`는 lowerCamelCase의 이 예와 점이 하나인 경로를 잡지 못한다. 한글 존재만으로 원문이 통과한다. 이번 신규 `koreanText` 호출이 사용하는 공통 판별식의 한계이며, 코드·경로가 섞인 문장은 한국어 대체 안내가 필요하다. 정상 한국어 이름·허용된 수식 기호·정책 id를 금지하라는 요구가 아니다.

근거: `f2-ufix6-2e1096749b31/persisted-mixed-Korean-internal-path.json/png`, `data/accounts.db`, `trace.zip`. `data-issue-path=characters.5004.equipment.head`는 비표시 속성으로 보존되는 것을 별도 통과 확인했다. 이 결함은 화면에 보이는 message의 키 노출이다.

### U7-Q-3 — 로그 조회 전송 실패에서 한국어 안내 대신 빈 영역·JS 예외

위치: `apps/desktop-ui/damage-log-adapter.js:1048` 부근의 `api_error`/`log:null` 반환 → `damage-log.js:249`의 상태 분기 누락 → `:324` → `:594`의 `data.fullBursts` 접근.

1. 실제 API에 `damageLog`를 요청하지 않은 120프레임 legacy 검산을 저장한다(총피해 1,145,772).
2. 저장 GET을 일반 replay 화면으로 연다. 내장 로그가 없어 `/damage-log?characterId=5004`를 조회한다.
3. **이 한 요청만** Chromium에서 전송 실패로 주입한다.
4. 로그 영역이 비며 `Cannot read properties of null (reading 'fullBursts')`가 발생한다. 준비된 한국어 오류 안내는 화면에 도달하지 못한다.

실제 API 생성 결과로 재확인했으며 손상된 저장 구조만의 문제는 아니다. **이 null 분기는 배포 기준 `3d84fe4`에도 있는 기존 결함**이고 이번 변경이 새로 만든 회귀라고 주장하지 않는다. 다만 UI 전수 목록의 “로그 조회 실패 → errorText”는 종단 화면 수용을 충족하지 못한다. 저장/API 바이트와 총피해는 보존됐다.

근거: `f2-ufix6-39dfd0b57036/created-without-log.json`, `missing-log.json/png`, `trace.zip`. `missing-log.json`에 실제 차단 요청 URL·replay ID·JS 스택을 기록했다. 2개 실패는 같은 결함의 안내 누락/JS 예외다.

## 통과 범위·전수 목록 대응

아래 경로는 모두 실제 격리 페이지에서 관찰했다. `surfaces`의 특수 상태는 QA 자체 필드/오류 주입이고, 정상 실행·회귀는 실제 API 응답이다. 특정 문구만 맞는 어댑터 단위 검사로 대체하지 않았다.

| UI 보고서 2절의 지점 | 독립 확인·판정 |
|---|---|
| 검산 표 name/operation·제목·hit 문구 | 새 네 정책 POST/저장/화면 및 기존 F2-Q-6 archive에서 금지어 0. 한국어 이름/설명·허용 수식. U7-Q-1 예외는 차단 |
| 미등록 term name | `기록된 계산 항목`, `저장된 연산 미확인`; 키는 data-term에만 보존 |
| 계산 terms 전체 없음·단계 하나 누락 | 한국어 “저장된 단계별…” 및 “공방차” 안내. 내부 경로/name 노출 0 |
| 효과 분류의 hit 문구·source/function | 새 source 17종×4정책·자연 OL·이전 archive 회귀 통과 |
| JSON/CSV export 실패 | 503 응답 본문 marker 미노출, `HTTP 503` 안내. 정상 다운로드는 서버 바이트와 동일 |
| 전술 저장/로컬 저장 오류 | 전송 실패 한국어 안내. 로컬 저장 예외는 status 변경 이력으로 관찰(뒤 서버 성공 문구와 구분) |
| 로그 조회 실패 | U7-Q-3 차단 |
| app 일반 act·refresh·검산·상세 read/preview/save | 각각 전송 차단, 영문 fetch 오류 미노출·한국어 안내. 계정/캐릭터 수정 요청은 서버 도착 전에 차단 |
| 이미지 갱신 status/refresh message | 자체 marker가 한국어 대체 안내로 바뀜; 외부 이미지 수집 호출 없음 |
| connection·연결 실패·재로그인·중단 job | 각 bootstrap 상태를 별도로 열어 원문 marker 미노출·한국어 안내. 비활성 계정 카드도 확인 |
| snapshot issues message | 기존 한국어 진단 회귀 통과, 혼합 내부 키는 U7-Q-2 차단 |
| compute 미등록 오류·기존 오류 분기 | 미등록·통계 모듈 미연결·기준 입력 불일치·예열·기준 없음에서 키 미노출. 기존 실제 400/404/409 및 503/전송 장애·복구 회귀 통과 |
| 미등록 장치 stage·batch state·backend·probeFailures | `상태 미확인`·`기타 장치`·장치 탐지 한국어 안내; 장치 해시 유지 |
| attempt·driver·응답 판정 | `시도 2회`·`드라이버`, 미등록 응답 판정 `미확인`·`우열 미확정` |
| 자동 버스트 waitingReason·timeline.reason | 실제 저장 사본의 두 미등록 사유 모두 `대기 사유 미확인`, 원문 노출 0 |
| 무기군 원값 fallback | 미등록 weaponType의 실제 거리 팝업 행에서 `무기군 미확인`; data-weapon은 보존 |
| profile reason·조건 로딩·보스 목록 오류 | 미등록 reason `사유 미확인`, 전송 실패 한국어; 기존 profile 누락/손상 실제 409 및 준비 스크립트 안내 회귀 |
| formation·local-lab 저장 실패 | 실제 화면 클릭으로 각각 전송 실패 경로 통과 |
| 변경하지 않은 이름/식별자 지점 | 정상 한국어 이름, 타격·발사·버스트 시전 번호, Replay ID, fingerprint·규칙/통계 버전·schema·정책 id·준비 스크립트·장치 해시 유지 |

`1 − defenceRatioRate (float32)` 같은 수식 자체는 지시서의 허용 범주로 판정했다. 한글 글자 존재 여부만으로 이를 실패 처리하지 않는다. 통계 미연결의 기존 정적 문장 `Backend가 Analysis 연결을 끝내면…`도 확인했지만 서버 필드 직출력은 아니므로 별도 문구 개선 의견이며 위 차단 건수에 포함하지 않는다.

## 새 실행·회귀 근거

모든 아래 상대 경로는 `C:/Users/user/orca/workspaces/Nikke-Simul/검수/artifacts/single-deck-qa/` 기준이다. Git 제외 증거이며 [검수 소유 재실행 도구](../tests/single_deck_compute_qa/check_ufix7_audit.py)와 함께 보존한다. 색인은 `ufix7-preparation/evidence-index.json`이다.

| 새 실행 | 결과 | 근거 폴더 |
|---|---:|---|
| F2 API·Chromium·DEF6·보스·조건 | 332/332 | `f2-ufix6-4f8c886ea68b` |
| 데스크톱 client_f32·통계·오류 복구 | 75/75 | `f32-b2-30c9df2275db` |
| source17종·네 정책·GET/export | 155/155 | `f2-ufix6-13254dc2adb5` |
| 기존 고급 진단·실제400/409·손상 profile | 104/104 | `f2-ufix6-4ffe89347c87` |
| 이전 F2-Q-3·4 archive | 12/12 | `f2-ufix6-aee611db561d` |
| 새 검산 표·미등록 연산·버스트 | 208/210 | `f2-ufix6-1b98cf7e1459` |
| 전수 예외 화면 | 36/37 | `f2-ufix6-2e1096749b31` |
| 누락 단계·로그 조회 실패 | 11/13 | `f2-ufix6-39dfd0b57036` |
| R4 엔진10입력·41타격 독립 산술 | 87/87 | `ufix7-preparation/engine-audit.json` |

기존 도구의 폴더 prefix와 일부 summary의 제품 메타데이터에는 `ufix6`/`59fe22d`가 남는다. **옛 결과를 복사한 것이 아니며 모두 이번 `b401421`에서 새로 실행**했다. 현재 실행 귀속은 최종 색인·Git 기준·로그·API 제공 JS 대조로 명시한다.

- 피해 **19,462건**, 독립 산술 오류 0. 팀 **24,007,922,311** = 멤버 합 = 타격 합 = replay = compute. 방어력 전환은 750프레임·앨리스·누적 2,013,492,851. 엄격한 20억 초과 후 다음 타격을 유지한다.
- DEF6조합, 보스43개·이미지42개, level400·조건 wire·fingerprint·기존 bool 저장 결과 및 과거 비교 정책 회귀 통과.
- 이전 375개 목록의 범위 내 **317/317**, 456개 목록의 범위 내 **390/390**을 새 실행에 매핑했다. 각각 58/66은 명시 제외된 `/legacy` 화면이고 누락 항목 0 (`regression-coverage.json`).
- F2-Q-6 기존 archive 총피해 **749,761,509**, SHA256 **`2ea1762e9e743a548cf56a6bdcc7709ed50804f24a3b96340bb4c6a9afbcac87`** 불변. 새/과거 각 검산 표의 data-term·입력/결과 수치, 저장 operation, 전체 GET/JSON export 및 브라우저 피해 로그 JSON/CSV가 서버와 일치한다.
- 허용 식별자의 기존 회귀 실제 위치는 `identifier-inventory.json`, 기존 화면 스캔은 `visible-text-inventory.json`에 별도 기록했다. 새 예외 검사의 차단 결과와 함께 읽어야 한다.

검수 도구 재시도는 최종 합계에서 제외했다(`attempt-index.json`). 환경의 Chromium sandbox 접근, bootstrap/health 필드 착오, 내려받기와 관찰 JSON 파일명 충돌, 허용 수식·Replay ID 위치·실제 한국어 문구 기대값, 비동기 장치 로드 대기, 강제 change 대신 실제 Tab 사용, 합성 요청의 필수 SG 계수, 사본 폴더 생성 및 DOM 재생성 대기를 바로잡았다. 강제 change로 생긴 blur 관련 예외는 실제 Tab 입력에서는 재현되지 않았다. 로그 실패 null 예외는 실제 API가 생성한 로그 미수집 결과에서 재확인했으므로 제품 결함으로 분리했다.

## 보존·미판정·인계

- 본인 API **23개 PID(재시도 포함)** 종료·프로세스 부재 확인: `ufix7-preparation/owned-process-cleanup.json`. 다른 서버는 종료하지 않았다. 공개 준비물 hash 및 미추적 `package-lock.json` SHA256 `2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767` 보존.
- 원본 `C:/Users/user/Documents/GitHub/Nikke-Simul/data/local`·계정 DB/세션/캐시·5180/5181에는 접근하지 않았다. 사용자 실행 파일 `C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe`를 실행·갱신하지 않았다. SDK 실행 파일 사용과 사용자 앱 EXE를 구분한다.
- 제품 직접 수정·push·원본 통합·배포·새 워커 없음. 계산/회귀 통과와 화면 수용 차단을 구분한다. **실사용자 덱·실게임 실측·GPU 실행·부하/1만회·최적성·원본 EXE 배포/실행 수용은 미판정**, Q-CPU-10K 보류 유지.
- 재실행: `check_ufix7_audit.py`, `check_ufix7_surfaces.py`, `check_ufix7_missing.py`, `run_ufix7_regression.py`에 `--dotnet <.NET 10 dotnet.exe 절대 경로>`를 전달한다. 기존 `check_f2_conditions.py`와 `DefenseProbe/Probe.csproj`→`check_defense_probe.py`도 이번에 실행했다. 결과 후처리는 `summarize_ufix7.py`다.
- QA 확정 커밋은 이 보고서를 포함하는 커밋이며 Director 최종 인계에 전체 SHA를 전달한다. 터미널을 재조회하고 살아 있는 에이전트를 확인한 뒤 **한 번만 인계**한다. 원본 배포 완료 보고가 아니다.
