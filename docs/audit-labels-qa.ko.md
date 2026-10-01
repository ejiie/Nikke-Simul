# U-FIX-7 독립 QA — 차단 (2026-10-01~02)

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
