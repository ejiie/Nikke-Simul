# B-DATA-1 독립 QA — 재QA 통과 (초기 차단 이력 포함)

## 최신 판정: a050853 재QA 통과

대상 Backend `a050853`을 초기 QA `e6295ca` 위에 일반 merge했다. 충돌 없는 병합 커밋은 `7f961fe422b561c4eee33269d6dabfbd86fe190e`다. **1,682/1,682 통과, 차단 0·미판정 0.** 아래 초기 차단 2유형은 모두 해소됐다. 이번 QA는 제품 코드를 수정하지 않았다.

- **BD1-Q-1·2 원래 8개 주입:** element/weakKey 미선언 null 2개, bosses/parts/ladder/steps/diagnostics/fields 요소 null 6개 모두 실제 GET **409 `boss_attributes_invalid`**.
- **확장 및 기존 API 545/545:** 가용 보스 필드·중첩 객체의 미선언 null/키 누락, 모든 컬렉션 종류의 null 요소(빈 coreMarkers/unconfirmed도 포함), source.entries의 10개 딕셔너리 값 null, 모든 중첩 DTO의 필수 키 검증. 선언된 element/weakKey/modelPrefab/challenge.stats/levelChange/step.stats null은 200과 다른 필드 보존. 미확인 코어 선언, 그룹 0의 levelChange:null, 마지막 구간의 rangeTo:null, 실제 수치 0도 200. **전체 요청 HTTP 500 = 0**.
- **원천 340/340:** 자체 raw-wire 판독 재실행, 새 `challenge.levelChangeGroupId`까지 preset의 원값과 40개 시즌 전수 일치. ZIP/10표 hash 및 방어율 0, 시즌 41·42 unavailable, 손상 ZIP 거부·기존 출력 보존 유지.
- **계산 회귀 797/797:** 자체 하네스 산술/런타임 737건과 기존 5인 180초 4시나리오×3정책×5시드 60건, 이전 E-PREC 독립 결과와 버전 포함 전체 JSON 일치. Core/Engine/Compute/Analysis/apps 변경 없음. 실제 API의 기존 보스 목록 바이트·준비 입력/조건·입력/실행 fingerprint·기존 replay/export 및 compute 결과/통계 조회 보존.
- Release API 및 QA probe 빌드 각각 경고 0·오류 0. 실제 Chromium `/editor/` 모듈 오류 없음. 소유 서버 PID 31524/17644 종료, 격리 포트 **55727**.

**배포 조건 — 재준비 필수:** 이전 준비 파일은 새 필수 `challenge.levelChangeGroupId`가 없어 실제 API가 409로 거부했다. 같은 원천을 현재 `prepare_solo_raid_boss_attributes.py --static-data-zip <고정 ZIP> --presentation-root <배포 dataRoot>/presentation`으로 다시 준비한 파일은 200이다. 따라서 제품 Git/DLL 통합만으로 배포가 완료되지 않는다. Director가 배포할 때 해당 준비 스크립트를 실행해야 한다(기존 파일이 없더라도 준비 필요). QA는 원본 presentation에 실행하지 않았다. 과거 계산 저장 결과는 이 표시용 파일 계약과 무관하게 조회된다.

최종 증거: `artifacts/single-deck-qa/bdata1r2/evidence-index.json`, `source-audit.json`, `regression-audit.json`; 실제 API `artifacts/single-deck-qa/f2-ufix6-f28fe586f93d/`의 `summary.json`, `traffic.json`, `expanded-null-matrix.json`, `valid-wire.json`, `editor.png`와 서버 로그. 자체 새 확장 검사 `tests/single_deck_compute_qa/check_boss_static_readmission.py`는 기존 QA 8개 주입을 그대로 포함하는 실제 API 검사에 확장 행렬을 추가한다. 원천/회귀 검사도 기존 QA 코드만 사용했으며 구현·리뷰 테스트/정답은 재사용하지 않았다.

초기 확장 검사에서 source.entries의 임의 딕셔너리 키 제거를 DTO 필수 멤버 누락과 혼동했던 기대를 수정했다(표 이름 키는 원천에 따라 달라지므로 필수 생성자 키가 아님). 최종 재실행 증거만 위 수치에 포함한다. 딕셔너리 **값 null**과 각 값 객체의 **필수 멤버 누락**은 전부 거부됨을 검증했다.

원천 ZIP 전후 hash, 공개 표 QA 사본 hash, package-lock hash는 초기 보고서의 값 그대로다. 원본 data/local 추가 접근 없이 공개 표 QA 사본을 재사용했다. 원본 계정·세션·캐시·presentation·5180/5181·사용자 EXE 불변. push·배포·새 워커 없음. S-SKILL-1 `27b99ee`의 앞선 병합은 Director 정정대로 `e6295ca`로 되돌렸으며 이번 제품 상태와 결과에는 포함되지 않는다.

## 초기 판정 기록: 2c41185 차단

검수 대상은 Backend 확정 `2c41185`다. E-PREC-1 QA `6bb1be2` 위에 일반 merge한 제품 상태는 `0c26d1c894cd36d252cae42b54a5b1f9cd10b1e2`다. 이번 커밋에는 QA 보고서와 독립 검사만 있으며 제품 코드는 수정하지 않았다. Director 지시서 `skill-precision-assignments-2026-10-03.ko.md`와 `workflow-implement-review.ko.md`를 적용했다.

**판정: 차단 2유형(BD1-Q-1·2), 1,419검사 중 1,411 통과·8 실패.** 원천 연결·수치·해시, 기존 계산/보스 목록의 불변성은 통과했다. 새 속성 API의 미선언 null 및 컬렉션 null 처리 때문에 최종 수용하지 않는다. 검사 미판정 항목은 없다. 게임 의미가 미확정인 방어율 단위·코어 추정 신뢰도 등은 제품이 명시한 미확인 상태로 유지하며 실측 검증을 뜻하지 않는다.

## 차단 1 — BD1-Q-1: 미확인 선언 없는 속성 null을 정상 수용

근거: `src/Nikke.Data/SoloRaidBossCatalog.cs:63`, `:67`. Validate는 challenge/step의 stats-null 선언만 검사하고 `element`와 `element.weakKey`에는 같은 계약을 적용하지 않는다. 계약 문서 「보스 정적 속성」의 “선언 없는 null·키 누락·문자열 숫자는 손상으로 409” 및 작업 구조 3·5 위반이다.

실제 제품 준비기로 만든 정상 파일의 첫 보스(시즌 1)는 `unconfirmed:[]`다. 격리 `dataRoot/presentation/solo-raid-boss-attributes.json`에서 아래 중 **하나만** 바꾼 뒤 `GET /api/presentation/solo-raid-bosses/attributes`를 호출한다.

| 독립 주입 | 기대 | 실제 |
|---|---|---|
| `bosses[0].element = null`, unconfirmed 유지 | 409 `boss_attributes_invalid` | **200**, element:null 그대로 반환 |
| `bosses[0].element.weakKey = null`, unconfirmed 유지 | 409 `boss_attributes_invalid` | **200**, weakKey:null 그대로 반환 |

해당 `unconfirmed`에 각각 `element`·`weak_element`를 추가한 경우에는 200과 나머지 정보 보존을 확인했다. 선언된 null을 무조건 금지하는 수정은 수용 조건이 아니다. challenge.stats와 levelChange.steps[0].stats는 이미 선언 여부에 따라 200/409를 올바르게 구분한다.

완전한 주입 파일·응답: 최종 API 증거 폴더의 `failure-264.json`, `failure-266.json`.

## 차단 2 — BD1-Q-2: 컬렉션의 null 항목을 검증하지 않음

근거: `src/Nikke.Data/SoloRaidBossCatalog.cs:35`, `:53`, `:69`. strict 역직렬화 옵션만으로 컬렉션 요소의 null 금지는 충족되지 않는다. 이후 검증에서 요소를 바로 역참조하거나 그대로 반환한다. 손상 파일 409 계약 및 작업 구조 3·5 위반이다.

정상 준비 파일에서 아래 경로 하나를 null로 치환한 각각의 실제 요청 결과다. 컬렉션 전체가 아니라 **첫 요소**를 바꿨다.

| 주입 경로 | 기대 | 실제 |
|---|---|---|
| `bosses[0]` | 409 | **500**, NullReferenceException |
| `bosses[0].challenge.levelChange.steps[0]` | 409 | **500**, NullReferenceException |
| `bosses[0].parts[0]` | 409 | **200**, null 포함 |
| `bosses[0].ladder[0]` | 409 | **200**, null 포함 |
| `diagnostics[0]` | 409 | **200**, null 포함 |
| `fields[0]` | 409 | **200**, null 포함 |

완전한 주입 파일·응답: `failure-268.json`~`failure-273.json`; 서버 예외는 `api-net10.0.log`. 정상 파일 복원 후 API와 앱은 정상 응답했다. 이 문제로 기존 보스 목록이나 계산 API가 오염되는 현상은 발견하지 않았다.

## 통과한 범위

| 범위 | 독립 확인과 결과 |
|---|---|
| 원천 검증 340/340 | 별도 positional MemoryPack 판독기와 ZIP/CSV 판독으로 시즌→preset→wave의 target/spawn 교집합→monster/model/parts를 재조인. 시즌 1~40의 모든 출력 수치·속성·레벨 구간·파츠·코어 분류를 원값과 대조 |
| 원천 기록 | ZIP SHA·바이트 수, 사용 표 10개 각각의 SHA·바이트 수·행 수 일치. schemaFingerprint 기록 확인 |
| 0 보존 | 보스 40개 `defenceRatioRate:0` 보존. monster/parts의 원비율을 임의 적용하지 않음. 실제 API에 hp/attack/defence 및 파츠 비율 0을 주입해 그대로 반환 확인 |
| 시즌 41·42 | 채택한 8/12판 manager에 없음을 독립 판독. unavailable + static_data_season_missing, complete:false, displayable:false. 추정 속성 없음 |
| 손상 ZIP | 필수 표 제거, 뒤 바이트 추가, 잘림, 멤버 수 변경, CSV 헤더 변경 모두 거부. 기존 정상 출력 파일 바이트 보존 |
| 실제 API 274/282 | 미준비 상태의 명시적 진단, 정상 준비 파일과 wire 일치, 중첩 수치 strict 243개 모두 통과. 누락·null·문자열·소수·범위 초과를 한 필드씩 주입. 나머지 8 실패는 위 두 차단 유형 |
| 기존 목록 | 병합 전/후 `/api/presentation/solo-raid-bosses` 응답 바이트 동일. 새 속성 파일이 손상되어도 목록 동일 |
| 기존 실행/보관 | 실제 API의 180초 5인 준비 입력·조건 동일, compute 입력/실행 fingerprint 동일, 과거 replay 원본/export와 compute 결과·통계 조회 보존. 시즌 1·33·41·42 선택이 계산 준비 입력을 바꾸지 않음. 속성 파일 손상 시에도 계산 API 실행 가능 |
| 동일 시드 계산 60/60 | QA 자체 E-PREC 하네스의 기존 4시나리오 × 3정책 × 5시드, 5인 180초 결과 전체 JSON이 **버전 포함** 병합 전과 동일. 멤버 피해·발수·장탄·버스트 시간·게이지·타임라인·이벤트 수 포함 |
| 정밀도 회귀 737/737 | QA 자체 E-PREC 산술/런타임 입력을 새 바이너리로 재실행. client_f32/dprod·방어율 true 예외·96 분리·장탄 경계·overflow 거부가 이전 독립 결과와 동일 |
| 브라우저/빌드 | 실제 격리 `/editor/` Chromium 진입, pageerror 0 및 홈 렌더 확인. Release 빌드 경고 0·오류 0. 이번 변경에 UI 없음 |

B-DATA diff에는 Core/Engine/Compute/Analysis/apps 변경이 없다. API Program 변경은 새 읽기 endpoint 연결 2줄이며 기존 계산 연결은 그대로다. 규칙 버전이나 계산 fingerprint 변경은 필요하지 않은 표시 전용 변경이다.

API는 RNG seed 입력을 받지 않는다. crit:off여도 스킬 확률 발동 때문에 서로 다른 호출 결과를 정확히 같다고 단언할 수 없다. 따라서 API에서는 준비 입력·조건·키·저장 보존 및 각 통계의 독립 산술을 확인하고, 결과 동일성은 같은 Random seed를 주입한 자체 C# 하네스 60건으로 검증했다. 초기 QA 시도의 무시드 결과 비교와 nullable 필드/배열 길이 기대는 바로잡았으며 아래 최종 증거만 판정 수치에 포함했다.

## 증거와 재현

- 종합 색인: `artifacts/single-deck-qa/bdata1/evidence-index.json`
- 원천 검사: `artifacts/single-deck-qa/bdata1/source-audit.json`
- **최종 실제 API:** `artifacts/single-deck-qa/f2-ufix6-ce0d49f3dfed/` — `summary.json`, `traffic.json`, `valid-wire.json`, 주입 실패 파일 8개, `browser.json`, `editor.png`, 병합 전/후 replay·compute 및 서버 로그. 포트 **60258**, 소유 서버 PID 32352/30324 종료 확인
- 회귀: `artifacts/single-deck-qa/bdata1/regression-audit.json`, `team-new.jsonl`, `math-new.jsonl`; 전 상태는 QA 자신의 `precision1/team-new.jsonl`·`math-new.jsonl`
- 검사 코드: `tests/single_deck_compute_qa/check_boss_static_source.py`, `check_boss_static_api.py`, `check_boss_static_regression.py`; 자체 `PrecisionProbe` 재사용. 구현·리뷰의 검사/하네스/fixture/정답은 읽거나 실행하지 않았다. 제품 준비 스크립트 자체의 호출만 했다

재실행 순서: source 검사 → Release API 빌드 및 API 검사(`--dotnet <SDK dotnet.exe>`) → 자체 PrecisionProbe를 현재 API DLL 참조로 빌드 → arithmetic 모드(cases.jsonl→bdata1/math-new.jsonl), team 모드(precision1 입력 폴더·해시 고정 runtime catalog→bdata1/team-new.jsonl, 마지막 인수 candidate) → regression 검사. API의 baseline-api는 B-DATA 병합 직전 별도 보관본이다. 모든 산출물은 Git 제외 QA artifacts에 둔다.

## 원천 및 보존

이번 B-DATA 입력 ZIP은 `C:/Users/user/Desktop/StaticData.zip`(8/12판), **17,176,616바이트**, SHA-256 `925762cd3ef56601916b2e2ae58f929d4dd389055b0d8bcd2176e9abd9b29e69`다. 원본 ZIP과 QA 사본 전후 hash 동일. source schemaFingerprint는 `b7d9ac3e51690d3dea5ec5e2606270868a114d4bb6b21f3f4b0bf65f2d6ff35a`다. 원천과 디코드 결과는 커밋/배포하지 않는다.

계산용 공개 표는 앞선 E-PREC QA에서 원본 전후 hash를 확인한 QA 사본 12개를 hash 대조 후 재사용했다. B-DATA 동안 원본 data/local을 추가로 읽지 않았다. 격리 계정은 QA 작성 합성 계정이며 원본 accounts.db·세션·캐시·presentation·5180/5181에 접근하지 않았다. 미추적 package-lock.json SHA `2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767` 보존·커밋 제외. push·배포·새 워커·부하 측정 없음.

Director가 방어율 원값 0 유지와 최신판 시즌 41·42의 후속 반영을 이미 결정했다. Backend 보고서의 “판단 필요/최신 다운로드 필요”는 당시 기록이며 현재 대기 요청으로 해석하지 않는다. 이번 QA는 9/17판 원천을 사용하지 않았다.

실제 사용자 실행 경로는 `C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe`로 유지했다. 해당 EXE와 원본 배포는 건드리지 않았으며, 본 보고서는 독립 검수 결과다.
