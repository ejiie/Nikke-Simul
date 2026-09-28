# client_f32 UI 연결 (I-UI) — 단계 A

2026-09-28. **단계 A 완료: Backend `f4ab2fc` merge, 사용처 목록화, 화면 준비(mock fixture·브라우저 렌더링 검증).** 단계 B(Backend 확정 wire 연결·실제 격리 API 종단 검증)는 Director 통지 대기다. 이 문서는 구현·mock 검증 보고이며 API 종단 수용·실게임 정확성 수용·배포 보고가 아니다.

배정: [I-BE·I-UI·Q-F32 지시서](C:/Users/user/orca/workspaces/Nikke-Simul/Director/docs/client-f32-integration-assignments-2026-09-28.ko.md)의 공통 절·I-UI 절. 먼저 읽은 문서: [H-F32·H-SRC 배정](C:/Users/user/orca/workspaces/Nikke-Simul/Director/docs/hit-damage-assignments-2026-09-28.ko.md), [클라이언트 공식·사용자 결정](C:/Users/user/orca/workspaces/Nikke-Simul/Director/docs/hit-damage-client-formula.ko.md), 엔진 보고서 `C:/Users/user/orca/workspaces/Nikke-Simul/시뮬레이션-엔진-담당/docs/hit-damage-client-f32.ko.md`(특히 "후속 연결·미실행·질문"), H-SRC 보고서 `C:/Users/user/orca/workspaces/Nikke-Simul/Backend/docs/hit-damage-source-investigation.ko.md`. Director 문서는 읽기만 했다.

## 1. 기준·보존

- 시작 HEAD `abcd5b5`(자기 통계 화면 커밋), 브랜치 `UI`. 미추적 `package-lock.json`(SHA-256 `2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767`) 보존·커밋 제외.
- reset/checkout/stash 없음. 편집은 `apps/desktop-ui/**`, `apps/web/src/**`, `tests/ui/**`, 이 문서, 자기 문서 `docs/ui-damage-audit-fix.ko.md` 상단 안내 1줄뿐이다. 엔진·Backend·QA 파일, 엔진 산술은 수정하지 않았다.
- 원본 계정 DB·세션·캐시, 원본 EXE·바로가기·배포 경로, 5180/5181 서버를 읽거나 변경·종료하지 않았다. API 서버를 띄우지 않았다(단계 A는 mock만). 게임 파일·프로세스 접근 없음. 원격 push·배포·새 Run/Dispatch/하위 워커 없음.
- `apps/web/node_modules`는 테스트용으로 lockfile 그대로 `npm ci` 설치했다(Git 제외, `apps/web/package-lock.json` 변경 없음).

## 2. Backend `f4ab2fc` merge (A-1)

일반 merge 커밋(`Merge commit 'f4ab2fc' into UI`), **충돌 0**. merge 후 `git diff f4ab2fc HEAD -- src tools scripts` 빈 결과(Backend 코드 그대로), `git diff abcd5b5 <merge> -- apps` 빈 결과(자기 UI 그대로). `40078d0`·`d8be9d3`·H-SRC 문서/스크립트가 들어왔다. 엔진 H-F32(`5ced15a`)는 이 merge에 없다 — Backend worktree는 이후 `f818f3b`(5ced15a merge)로 진행 중이며 단계 B에서 받는다.

통계 화면(`abcd5b5`, compute 계약 v1 `f2327e5` 기준)과 `f4ab2fc` 계약 대조:

| 계약 변경 (`f2327e5` → `f4ab2fc`) | UI 영향 | 조치 |
|---|---|---|
| `ExecutionSelection.tuning`(optional `TuningDiagnostics`, cpu-policy-3) 추가 | 무시해도 호환. 화면은 튜닝 단계·`scope=bounded_candidates_not_global_optimum`을 아직 표시하지 않음 | 불일치 아님. 표시 여부는 별도 결정 |
| `GET /experiments/{id}/ol-candidates` (`OlCandidateCatalog`) 신설 | UI 미사용(현재 OL 후보는 수동 입력) | 불일치 아님. 후속 연결 후보 |
| 요청 예시 `targetDefense` → `enemyDefense` 정정 | UI는 이미 `enemyDefense` 전송 | 일치 |
| `IComputeAnalysis` 등록(`analysis_not_integrated` 409 해소) | UI는 409·정상 둘 다 처리 | 일치 |
| `warmup_excluded_from_statistics` 409 | 전용 문구 없음(일반 오류로 표시) | 경미. 단계 B 회귀 때 확인 |
| API가 게임 카탈로그를 `<dataRoot>/game-catalog.json`에서 읽음(`Program.cs`) | UI 무관. 원본 배포 시 데이터 루트 준비 조건 | Director 배포 단계 참고 |

`abcd5b5` 통계 화면의 모든 compute 요청은 `roundingPolicy`를 폼 값(현재 기본 `legacy_term_floor`)으로 보낸다. H-F32 통합 후 fingerprint에 정책이 들어가므로 단계 B에서 기본 `client_f32` 전환이 필요하다(4절).

## 3. 사용처 목록 (A-2) — `abcd5b5` 기준, 현재 줄 번호

| 위치 | 가정 | 단계 A 처리 / 단계 B |
|---|---|---|
| `apps/web/src/calculation.ts` 요청 `inputSchemaVersion: 2`, 저장 JSON `inputSchemaVersion: 2` | schema 2 고정 | `buildHitRequest`로 분리. 미확정 wire에선 그대로 schema 2(새 필드 미포함). 저장 JSON은 실제 요청 schema 기록 |
| `calculation.ts` `policies` 사전(3개) + 표 `정수화 후보` | 후보 3개 고정, 미지 정책은 `undefined` 표시 | `orderCandidates`·`comparisonTableHtml`: client 우선, 과거 3개 비교 후보, 미지 정책 `미해석`, 누락 정책 안내 |
| `calculation.ts` 입력 폼 | `statDamageRatio`·`defenceRatioRate` 없음 | 실험 입력 fieldset 추가(중립 1/0, 미확정 표시). wire 미확정 동안 disabled·요청 미포함 |
| `apps/desktop-ui/app.js:241` 솔로 레이드 `정수화` select 3개(기본 `legacy_term_floor`), `:60` 통계 조건 fallback | 3정책·legacy 기본 | `hit-policy.js` `policyOptions()`/`defaultPolicy()`로 생성. 미확정 동안 옵션·기본 동일(라벨만 `최종 반올림 (절반은 짝수)`) |
| `apps/desktop-ui/damage-log-adapter.js:330` `AUDIT_TERM_LABELS` B2~B5, `:604` `factors` B3~B5, `:691~696` 3정책 산식 | client 항 이름 없음(`base`는 의미가 다름) | 정책별 `termLabel`, client 필수 항 목록, `buildClientBreakdown`, client 산식 7줄 |
| `damage-log-adapter.js:546~559` 효과 축 `B3 · …`, `B4 · …` | B3/B4 이름 | client 로그에서만 `addDamageRate · …`, `damageReductionRate · …`, `B · criticalDamageRate`, `chargeDamageRate`로 변환 |
| `damage-log-adapter.js:736, 868, 947, 1136, 1237` 정책 누락 시 `final_round_even` fallback·합성 미리보기 | 과거 기본 | **단계 A 미변경**(live 로그 의미 유지). 단계 B에서 서버 기본값 확인 후 `defaultPolicy()`로 교체 |
| `apps/desktop-ui/damage-log.js:114` 카드 `B3 × B4 × B5` | 과거 항 | client 로그는 전용 카드(base·B·extra·감소·방어비율·elementRate 입력·정수화 전 곱). 과거 로그는 그대로 |
| `damage-log.js:233` 문구 `서버 E1/B1 연동 대기` | 정책 무관 | 변경 없음 |
| `single-deck-stats.js`/`compute-adapter.js` | 정책은 조건 객체 통과만 | 변경 없음. 기본값은 app.js `getConditions` 경유 |

엔진 client audit(`HitCalculator.Evaluate`, `5ced15a`)의 항: `effectiveAttack`, `effectiveDefense`, `difference`, `base`, `B`, `extra`, `reduction`, `defenceRatio`, `product`, `final`. **`charge`·`elementRate`·`minimum` 항은 없다.** 따라서 UI는 chargeDamageRate·elementRate·개별 crit/core/burst/range rate를 `hit` 입력값으로만 보여 주고 "감사 항 미기록 · hit 입력 기준"이라고 표시한다(재계산해 대체하지 않음). max(1) 적용은 `product`가 0.5 미만이고 `final = 1`일 때 표시한다.

## 4. 화면 준비 (A-3)

공통: `apps/desktop-ui/hit-policy.js` 신설, web은 같은 규칙을 `apps/web/src/calculation-model.ts`에 둔다(별도 패키지). 둘 다 `CLIENT_F32_WIRE.confirmed` / `HIT_WIRE.confirmed = false`다. **false인 동안 live 요청·선택지·문구는 기존과 같다.** client 표시 경로는 mock으로만 실행한다. 단계 B에서 Backend 확정 wire에 맞춘 뒤 true로 바꾼다.

- **단일 히트 후보 표시(web):** `client_f32`를 `기본` 태그로 첫 행, 과거 3개는 `비교 후보` 태그로 유지(삭제 안 함). 엔진은 client를 네 번째로 반환하므로 UI가 순서를 정하고, 응답에 없는 정책은 안내, 모르는 정책은 `미해석`으로 남긴다.
- **새 입력:** `statDamageRatio`(중립 1, "원천 불명 · 스킬 계수는 가설"), `defenceRatioRate`(중립 0, 0~1, "최근 기믹 · 적용 보스·값 불명") 모두 `실험·미확정`. 추정값을 기본으로 채우지 않는다. 빈칸·문자·범위 밖은 오류(0/1로 대체 안 함).
- **피해 로그 항 설명(desktop):** client 산식 — long 공격력 조립 → `base = float32(공방차) × damageRatio × statDamageRatio × chargeDamageRate` → `B` crit→core→burst→range float32 누적 → `extra = breakRate + addDamageRate − 1`(잠정 대응) → `1 − damageReductionRate`(잠정) → `1 − defenceRatioRate`(실험) → elementRate → `max(1, 사사오입)`. 카드의 float32 값은 9자리 유효숫자, 단계 표는 저장 원값 그대로.
- **로그에 새 두 비율이 없으면** `미기록`으로 표시한다(중립값을 가정하지 않음).
- **큰 long:** `readWireLong`이 number/10진 문자열을 모두 받고, 2^53 초과 number 또는 문자열은 정밀도 경고와 원문을 표시한다. Backend 결정 후 한쪽으로 좁힌다.
- **과거 정책 로그 안내:** wire 확정 후에만 "비교 후보 정책 · 기본 경로는 client_f32"를 산식 위에 붙인다.

## 5. 검증 — 증거 종류 구분

모두 **mock 또는 기존 회귀**다. 실제 API 종단 검증은 하지 않았다(단계 B).

| 명령 | 증거 종류 | 결과 |
|---|---|---|
| `python tests/ui/fixtures/make_client_f32_mock.py` | UI mock 생성 | `tests/ui/fixtures/client-f32-mock.json`. Python struct binary32로 엔진 보고서의 연산 순서를 따라 계산한 **UI fixture**(엔진 출력·API 응답·게임 관측 아님). 과거 3후보는 기존 실제 `HitCalculator.Compare` p02.3 fixture 복사. 6 case: 기본 4개 + `defenceRatioRate 0.25` + `statDamageRatio 2`. 예: 크리+코어+풀버스트+거리 client 4,460,740 / legacy 4,460,732 / round-even 4,460,739 / nested 4,460,730 |
| `node tests/ui/client_f32_mock.test.mjs` | mock 단위 | 13/13 통과: 후보 순서·역할·누락, wire 미확정 시 select 불변, 실험 입력 중립·엄격 파싱, long number/문자열, 항 읽기(누락 0, 최종=저장), 산식·실험 라벨, 비율 변형, 비율 누락→`미기록`, max(1), 2^53 초과 문자열, 효과 축 이름, 과거 로그 불변 |
| `npx vitest run` (apps/web) + `npx tsc --noEmit` | mock 단위 + 타입 | 10/10 통과(기존 7 + client 3), tsc 오류 0 |
| `python tests/ui/check_client_f32_mock_browser.py` | mock 브라우저(Chromium) | 통과 `artifacts/ui/client-f32-mock/run-*/report.json`, 4시나리오 × 1500/850/500px = 12. client 카드·단계 10항·실험 라벨·축 이름·web 후보 순서·비교 태그·max(1)·0.25 입력, wire 미확정 시 fieldset disabled·비교 태그 없음, 가로 넘침 0, JS 오류 0 |
| `node tests/ui/damage_audit.test.mjs <Director 저장 replay>` | 기존 회귀(읽기 전용 실제 저장 로그) | 19/19 통과 |
| `python tests/ui/check_damage_audit_browser.py --real-replay <같은 파일>` | 기존 회귀(합성 HTTP + 저장 replay, `--live` 미사용) | 통과 `artifacts/ui/damage-audit/run-72f580eac124`. 저장 replay SHA-256 전후 동일 `2dd1f740…abd7f` |
| `python tests/ui/check_solo_raid_level.py` | 기존 회귀(합성 HTTP) | 통과, 레벨 400 유지·select 값 전달 |
| `node tests/ui/single_deck_stats.test.mjs`, `python tests/ui/check_single_deck_stats_browser.py` | 기존 회귀(합성 fixture) | 통과 |

## 6. 단계 B 작업 목록 (Director 통지 후)

1. Backend 확정 커밋 merge → 확정 `HitRequest` schema 3 규격으로 `buildHitRequest` 교체, 두 flag true.
2. v2 요청의 명시적 v2→v3 변환 표시(원본 schema·변환 사실), 제약 위반 오류(소수 공격력·DEF·고정 부여, 1/10000보다 정밀한 비율) 문구를 Backend 오류 코드에 맞춰 표시. mock의 `provisionalErrors`는 임시 형태다.
3. 피해 로그 fallback 5곳을 서버 기본 정책 확인 후 교체. 통계 화면 기본 정책 `client_f32`와 fingerprint 분리 확인.
4. 실제 격리 API·브라우저: v3 요청, 네 후보, 새 입력, 오류 메시지, 피해 로그 client 항, 통계 화면·레벨 400·버스트 UI 회귀. EXE 배포 안 함.

## 7. Backend(I-BE)에 필요한 wire 결정 — Director 경유

- 큰 `long`(effectiveAttack·final 등) JSON 표현: number인지 문자열인지. UI는 둘 다 받게 준비했다.
- `HitRequest` schema 3 필드 이름·위치(`input.statDamageRatio`/`input.defenceRatioRate`인지), `RawRate10000`/`ExactAmount` 노출 여부, v2 변환 표시 필드 이름.
- 응답의 네 후보 순서·선택 정책 표시 필드, 오류 응답 형태(코드·메시지).
- (엔진 소유 참고) client audit에 `charge`·`element` 항이 없어 UI는 hit 입력으로만 표시한다. 필요 시 엔진 항 추가 여부는 Director 판단.

## 8. 미실행·한계

- 실제 API 종단(단계 B), EXE 빌드·배포, 원본 실행 경로 확인은 하지 않았다. 현재 사용자 실행 경로 `C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe`에는 이 변경이 반영되지 않았다.
- mock 값은 UI 표시 검증용이며 엔진 출력과의 일치는 단계 B 실제 API로 확인한다. 테스트 통과는 실게임 정확성 수용이 아니다.
- Backend 전체 빌드·테스트는 이번 범위에서 돌리지 않았다(merge로 Backend 코드는 `f4ab2fc`와 동일).
