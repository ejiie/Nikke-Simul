# E-BUG-1 독립 QA — 수동 풀차지 UP형 발사 지연

2026-10-02, 검수 worktree / 브랜치 `검수`. 대상 `d93271610603e227b50665815881449d8bcadc9c`(구현 `9bb28ea`), 비교 기준 Director `2487bbd`, 이전 QA `8705d17`.

**최종 판정: 통과 — 1,588/1,588, 차단 0.** 이전 수용 1,364개를 모두 새 실행에 매핑했고 전부 통과했다. 아래 수치는 구현 보고서의 결과 파일을 가져온 것이 아니라 검수 소유 하네스의 출력이다.

## 범위와 독립성

- AGENTS.md, Director 버그 문서·작업 구조, 엔진 보고서를 읽었다. `git merge --no-edit d932716`은 fast-forward, 충돌 0. QA 시작 제품 소스는 `2487bbd`와 같음을 `git diff -- src apps tools`로 확인하고 구 API 빌드를 격리 보관했다.
- 제품 `src/**`, `apps/**`, `tools/**` 수정 0. 구현·리뷰의 검사 코드, 하네스, mock, 결과·정답 파일을 읽거나 실행·복제하지 않았다. 새 `ChargeProbe` 및 Python 검사는 이번에 독립 작성했고, 회귀는 검수 소유의 기존 최소 재현을 사용했다.
- 공개 원본 표 12개만 이름으로 지정해 읽고 SHA-256 전후를 대조했다. 복사본은 `artifacts/single-deck-qa/ebug1/public-copy/`. 계정은 새 합성 SQLite DB로 만들었다. 원본 accounts.db·세션·캐시·presentation·5180/5181·EXE는 접근·변경하지 않았다.
- 실제 사용자 실행 경로는 계속 `C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe`다. 이번 결과는 격리 QA이며 원본 통합·빌드·배포·실행 검증이 아니다. push·새 워커 없음. 미추적 package-lock.json 보존, 커밋 제외.

## 1. 프레임 산술·발사 모델 — 통과

`ChargeProbe`는 동일한 공개 제품 타입을 구·신 DLL에 각각 연결하되, 예상 프레임은 별도 Python 정수 산술로 계산한다. 53개 입력 각각 2,400프레임에서 `FiringModel`과 `SkillFiringModel`의 Fired·풀차지 여부·잔탄·재장전·명중원 상태 전체가 일치했다. 조준 0/5/12F, 원시 차지 1/10/100cs, 고정 재클릭 1/3F의 경계 및 99% 차지 단축을 포함했다.

조준 시간을 A, 양자화된 유효 차지를 C, 재클릭을 R이라고 할 때, A>0이면 조준 마지막 프레임에 차지 1F가 선시작한다. 따라서 첫 발 = `A + max(1, C−1)`, 탄이 남은 연속 발 간격 = `R + A + max(1, C−1)`이다. A=0 경계는 선시작 없이 `R+C`다. 발사 프레임 배열 전체를 이 식과 비교했다.

| 독립 제어 입력 | 새 수동 풀차지 간격 | 새 자동 간격 |
|---|---:|---:|
| A=12F, C=60F, R=1F | 72F | spotLast 12 + spotFirst 12 + 59 = 83F |
| A=12F, C=1F, R=1F | 14F | 12 + 12 + 1 = 25F |

구 엔진의 C=1F 수동 풀차지는 2F였고 새 엔진은 모든 연속 발이 14F였다. 별도로 실제 앨리스 스킬이 작동하는 20개 시드에서 탄이 남은 **3,513개 연속 발 간격**을 `12F + 재클릭 1~2F + 저장된 실제 차지 프레임−1`과 검산했다. 평시·자체 버스트 모두 포함, 위반 0. 탄 0 뒤 강제 재장전 간격은 이 식의 적용 대상에서 분리했다.

새 trace의 같은 캐릭터 직전 shot과 현재 shot 프레임 차가 ShotIntervalFrames와 일치했다. 첫 shot·shot 외 이벤트는 null/미기록이다. 실제 API 4,000개 trace 및 하네스의 각 사격 방식 trace를 검사했다. trace OFF 및 제한 7건으로 바꿔도 같은 시드의 피해는 같았다. 구 저장본에 새 필드를 덧씌우지 않는다.

## 2. 변경 대상 밖 경로 — 통과

DOWN_Charge·maintain·자동·톡톡이는 구·신 두 모델에서 2,400프레임의 상태 배열이 정확히 같았다. 재장전까지 포함하도록 합성 탄창 7발을 사용했다. 공개 표의 리버렐리오(5156), 네온: 비전 아이(5170), 자세 유지 무기 6명(5148·5169·5105·5124·5095·5143)도 자동/수동 각각 비교했다. 이는 엔진 타이밍 검사이며, 현재 5인만 지원하는 API에 이 캐릭터들이 지원된다는 판정은 아니다.

5인 180초에서도 톡톡이·자동은 각 20개 시드의 멤버별 피해·발수·치명타·잔탄·쿨다운·버스트·shot 프레임·저장 trace가 구·신 동일했다. 비교에서 제외한 필드는 의도적으로 바뀐 rulesVersion과 새 ShotIntervalFrames뿐이다.

## 3. 5인 180초 전후 수치·2차 영향 — 통과

합성 계정: 리타·블랑·앨리스·누아르·모더니아, Lv400, 스킬 모두 10, 장비·OL·큐브·소장품 없음, 한계돌파·코어·호감도·콘솔 0. 10,800F, 고정 DEF 30,925, final_round_even, 크리 확률 적용, 코어 ON, 앨리스 수동 풀차지. 같은 실제 API 산출 멤버 입력과 공개 skill graph에 검수 소유 RNG 시드 1~20을 주입했다. 시드는 QA 하네스 내부에서만 사용하며 실제 API/브라우저의 RNG는 바꾸지 않았다.

버스트 후보는 5명 모두, 1단계 리타, 2단계 블랑, 3단계 우선순위 앨리스·누아르·모더니아, **3단계 로테이션은 앨리스·모더니아**, unavailablePolicy=next_ready, 그 외 엔진 기본값이다.

| 지표 | 구 엔진 평균 | 새 엔진 평균 | 변화 |
|---|---:|---:|---:|
| 앨리스 발수 | 274.15 | 192.60 | −29.746% |
| 앨리스 피해 | 332,805,357.20 | 224,049,834.30 | −32.678% |
| 팀 피해 | 819,654,190.20 | 709,110,864.20 | −13.487% |
| 톡톡이 앨리스 발수 | 419.85 | 419.85 | 동일 |
| 톡톡이 앨리스 피해 | 105,837,255.10 | 105,837,255.10 | 동일 |
| 자동 앨리스 발수 | 150.80 | 150.80 | 동일 |
| 자동 앨리스 피해 | 165,400,244.35 | 165,400,244.35 | 동일 |

seed 1: 풀버스트 11회→11회, 첫 풀버스트 227F→225F. 앨리스 최소 간격 8F→19F, 중앙값 9F→20F. 구 8F×108·9F×71, 신 19F×73·20F×44도 일치했다. 장비 없는 이 계정의 자체 버스트는 1F 차지 조건이 아니므로 2F 재현은 앞 절의 제어 실험으로 검증했다.

타 멤버 평균 피해 변화: 리타 +0.238%, 블랑 +0.531%, 누아르 −0.931%, 모더니아 −0.327%. 공유 RNG 소비량과 게이지에 따른 시전 시점이 달라지는 조건이다. 이를 분리하려고 양쪽 엔진에 동일한 앨리스 시전 프레임·풀버스트 창·고정 RNG 출력·크리 OFF를 주면 **다른 4명의 전체 멤버 결과가 정확히 같았다**. 따라서 이 20개 시드·입력에서 타 멤버 변화는 RNG·타이밍의 2차 영향과 부합한다. 모든 편성·확률 분포에 대한 보장은 아니다.

비차단 문서 보완: 구현 보고서의 “Probe와 같은 전술”에는 정확한 로테이션이 없다. 최초 QA 입력은 3명 순환이어서 앨리스 발수 −27.458%, 팀 피해 −10.690%, seed 1 풀버스트 12회였다. 이를 숨기지 않고 `comparison.json`에 보존했다. 앨리스·모더니아 교대 조건의 별도 실험(`comparison-rotation2.json`)으로 보고 수치를 재현했다. 제품 결함이 아니라 재현 조건 명시의 문제다.

## 4. 버전·fingerprint·캐시·구 저장본 — 통과

| 구성 | 구 버전 | 신 버전 |
|---|---|---|
| SkillReplay | p03.skills.5-defense-switch | p03.skills.6-manual-charge-delay |
| TeamBurstController | p04.team.5-defense-switch | p04.team.6-manual-charge-delay |
| PreparedSkillReplay | cpu-summary.4-defense-switch | cpu-summary.5-manual-charge-delay |
| WeaponReplay | p03.weapon-reference.3-boss-conditions | p03.weapon-reference.4-manual-charge-delay |

동일 격리 dataRoot에서 구 API로 replay와 2회 compute를 저장하고 종료한 뒤 신 API를 실행했다. 멤버 입력·조건 동일, engineVersion·summaryVersion·rulesVersion·입력 fingerprint·실행 fingerprint는 분리됐다. tuning 캐시는 새 키 파일을 생성하고 cacheSource=miss, 기존 파일 SHA-256은 그대로였다.

구 replay GET·export 원본 바이트, 구 compute results·statistics 응답 모두 보존. 구 compute `/resume`는 실제 HTTP 409와 `engine_or_rules_version_changed`로 거부됐다. 이 검사는 계정 원본·사용자 캐시와 무관한 새 합성 DB에서 수행했다. 실행 fingerprint 예: 구 `55522cc8…`, 신 `fea0a436…`; 전문은 cache-separation.json.

## 5. 실제 격리 API·브라우저 — 통과

최종 API 포트 64771, 브라우저 포트 52877, 각각 별도 합성 dataRoot. Chromium에서 `/editor/`를 열고 **직접 조작=앨리스, 차지 방식=풀차지**를 선택해 실제 POST를 보냈다. 최종 화면 검사에는 request/response interception·mock을 쓰지 않았다. 저장 GET은 실제 브라우저 응답과 같았다.

피해 로그의 전체·자체/팀 중첩·비버스트 필터에서 표시 시간의 F값을 저장 hit.frame에 대조했다. 자체 버스트 예: **230→249→268→287→306→325→345F**, 즉 19/20F. 피해 검산의 한국어·저장 피해 일치 표시도 정상, 모듈 오류 0. 화면에는 별도의 간격 열이 없고 시간 열에 초/F가 표시된다. 새 ShotIntervalFrames는 trace 필드이며 화면 간격 검증은 표시된 F값의 차로 했다.

증거: `artifacts/single-deck-qa/f2-ufix6-502eaf93dbf4/damage-self-burst.png`, `rows-self-burst.json`, `browser-replay.json`, `trace.zip`.

## 6. 이전 수용 항목 전체 회귀

기존 수용 **1,364/1,364** 통과. 이전 QA `8705d17`의 각 검사 이름·발생 순서를 새 실행과 대응했다(새 replay UUID만 정규화). F2 332, client_f32 75, source 155, 진단 104, 이전 archive 12, 검산 문구 210, 화면 37, 누락값 13, 동일 유형 확장 148, 허용 목록 103, ESM·주요 화면 88, 독립 엔진 DEF 산술 87건이다. 새 E-BUG-1 검사 224건(프레임·전후 비교 198, 실제 API 16, 실제 브라우저 10)을 합쳐 1,588건이다.

범위는 F2의 독립 피해 산술·DEF 전환·조건 팝업·과거 기록, client_f32, 통계, source 표시, 진단, U7-Q-1~5, 허용 목록·과잉 차단·상속 속성 키, 전체 ESM 로드와 주요 화면이다. 제품 코드를 바꾸지 않았으며, QA에서 발견한 이미지 로딩 대기 문제만 검수 스크립트에 수정했다. 최종 F2 332건은 대기 수정 후 전부 재실행해 통과했다.

## 증거·재현·미판정

- 집계: `artifacts/single-deck-qa/ebug1/evidence-index.json`, 이전 QA 매핑 `previous-qa-coverage.json`, 공개 표 `public-hashes-before.json`/`public-hashes-final.json`.
- 엔진: `timing-old/new.json`, `team-old/new-rotation2.json`, `probe-audit-rotation2.json`, `comparison-rotation2.json`. API·브라우저의 최종 증거 경로는 api-evidence.txt·browser-evidence.txt에 저장.
- 새 하네스: `tests/single_deck_compute_qa/ChargeProbe/`, `check_charge_probe.py`, `check_charge_api.py`, `check_charge_browser.py`, `summarize_charge_qa.py`. C# 프로젝트는 `-p:QaBinaries=<구 또는 신 API DLL 폴더>`로 독립 빌드하고 `timing <출력> <public-weapons.json>` 또는 `team <출력> <검수 API 저장 입력> <공개 runtime catalog> 5004,5044`로 실행한다. 비교 산술은 `check_charge_probe.py -rotation2`.
- Release API 빌드: 경고 0·오류 0. 구현 담당의 제품 테스트는 금지 범위이므로 실행하지 않았다.
- 시도 이력: 초기 API 요청의 traceLimit 초과, QA의 처방 시전 쿨다운 오류, 브라우저 대용량 trace 응답의 검사 도구 캐시 eviction, graph 점까지 포함한 QA selector 오류를 수정하고 최종 재실행했다. 도구 서버 재시작으로 중단된 실행도 최종 집계에서 제외했다. F2 이미지 로드 완료 전 평가 1건은 원본 로그 `f2-image-race.log`를 보존하고 명시적 로드 대기 후 재실행했다. 기대 수치에 맞추는 제품 수정은 없다.
- **미판정:** 실게임 실측과 spotFirst 절대값의 정확성, 마지막 탄 뒤 재장전 개시 시점의 실측, 부하·성능 측정, 사용자 원본 배포. 이번 QA는 사용자 확정 엔진 규칙의 구현·격리 실행을 검증한다.
