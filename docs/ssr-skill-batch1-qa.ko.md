# S-SKILL-1 1차 묶음 독립 QA — 차단 1건

대상 엔진 `20a0609`(구현이 E-PREC 충돌을 해소하고 리뷰를 받은 HEAD). B-DATA 재QA `9ee11a7` 위 일반 merge는 충돌 없이 `b9ab40a0971e7decdfcf9bf7268af3ba6c8f6c0d`로 완료했다. 제품 코드 수정 없음. 이전 `27b99ee` 병합 시도는 Director 정정대로 `e6295ca`로 되돌렸고, 이번 판정에는 사용하지 않았다.

**독립 검사 2,171건 중 2,170 통과·1 실패. 최종 차단 SS1-Q-1.** 원천·계산·실행 거부·장탄 merge 상호작용은 통과했다. 1-tick 실측과 교체 무기 모션 실측은 지시대로 **범위 밖·미판정**이다. 기존 UI 테스트는 6/7이며, 별도 배정된 B-DATA 후속 `e21b774`의 허용 목록 갱신 문제로 구분한다.

## SS1-Q-1 — compute 실행에서 잠정 정책·관통 한계가 사라짐

Director 승인 조건은 교체 총을 사용한 모든 실행에 잠정 모션 정책과 관통 다중 타격 미모델 한계를 남기는 것이다. replay 결과는 이를 충족하지만 **compute 결과/통계는 충족하지 않는다**.

실제 격리 API에서 합성 Lv400, 무장비, 리타·블랑·누아르·스노우 화이트·맥스웰을 편성했다. `/api/compute/experiments`에 180초, client_f32, CPU 1 worker, 2회 기능 검증을 요청했다. 조건은 `casts:[{frame:30,characterId:"5012"},{frame:400,characterId:"5001"}]`이고 자동 버스트는 사용하지 않았다. 두 run 모두 정상 완료됐고 SW·맥스웰의 burstCasts가 각각 1이다. 따라서 교체 총을 실제로 사용하는 실행이다.

- 같은 캐릭터의 replay에는 `replacement_weapon` trace의 `basis:"provisional_motion_policy:provisional_no_spot_delay_full_charge_fixed_magazine"`와 `limitations`의 provisional/pierce multi-hit 설명이 있다. trace:false replay에도 limitations는 유지된다.
- compute의 batch·`/results`·`/statistics` 응답에는 **해당 정책이나 관통 한계를 전달하는 필드/문구가 없다**. 일반 gameVerified:false는 어떤 근사가 들어갔는지 설명하지 못한다.
- 위치: `src/Nikke.Engine/Skills/PreparedSkillReplay.cs`의 `SkillRunSummary` 및 `Run()` 반환(전체 SkillReplayResult의 Limitations를 버림), `src/Nikke.Data/ComputePreparation.cs`의 RunSummary 변환. 표시용 API/계약 연결이 필요하면 Director가 소유 범위를 판단해야 한다. QA는 제품을 수정하지 않았다.

기대: 요약 계산·저장·조회에서도 실제 적용한 잠정 교체 무기 정책과 단일 타격 한계를 식별할 수 있어야 한다. trace 배열 자체를 통계에 저장해야 한다는 요구는 아니다.

재현 원문: 최종 API 증거 폴더 `new-members-compute.json`에 요청·batch·2개 run·통계를 보존했다. 실패 검사명은 `compute exposes replacement provisional and pierce limitation`이다. 원본 계정/서버 없이 재현했다.

## 통과 범위

| 범위 | 독립 증거 |
|---|---|
| 원천 1,164/1,164 | 고정 manifest의 8개 공개 입력 전후 hash 확인. 제품 assembler만 호출하여 새 catalog 생성 후, 별도 HTML 판독/Fraction과 원천 JSON 직접 비교. 5명×3슬롯×10레벨의 계수·지속·트리거/단계 및 함수·중첩 스킬 전부 원문 일치 |
| 교체 설명 | SW 5초·풀차지×10·1발, 맥스웰 2초·×3·1발. 양쪽 Pierce 명시. 레벨 1~10 조립 일치. 실제 고정 설명에서 효과 줄 제거/미지 값/부분 일치 문자열 주입은 거부, 명시 None만 false |
| 실제 API 152/153 | 두 새 니케 레벨 1·5·10, 자동/수동 풀차지 12개 replay 성공. 각 burst 1발, 원천 계수·차지 배율·관통·차지 프레임 일치, 모든 로그 피해를 자체 산술로 검산. 저장/GET/export 바이트 동일. trace:false 6건도 잠정 한계 유지. 수동 tap 6건 모두 400·부분 저장 없음. 실패 1건은 SS1-Q-1 |
| 미지원 3명 | 라피:레드 후드·홍련:흑영·레드 후드 catalog의 10레벨 전부 allLevelsExecutable:false, unsupported 비어 있지 않음. 레벨 1·5·10 실제 실행 9건 모두 400, 저장 결과 증가 없음. 라피 진단은 catalog의 앞 12개와 동일 |
| 효과·키 57/57 | 고정 난수 자체 하네스. SW 정상타 30회마다 원천 추가 피해/공격 버프, 버프 300F 지속, 900F마다 skill2 직접 피해, 풀버스트 때만 0.261 크리 확률 버프 600F. 난수 .27에 대한 실제 크리 구간 정확. 맥스웰 풀버스트 버프·상위 ATK 2명 선택·단일 보스의 소환 조건 비활성. dataVersion/graph/conditions 각각의 fingerprint 분리와 무단 변경 Restore 거부 |
| E-PREC 상호작용 | 기본 무기 100발에 raw1450 장탄 버프 → **115발**, 교체 무기만 **1→0발**. 차지 속도 0/25%와 맥스웰 자체 4.48%의 정수 cs 단축을 분수 산술로 확인. FromRaw/ApplyAmmo/checked 경로 유지 |
| 기존 회귀 797/797 | E-PREC 자체 산술/런타임 입력 737건, 기존 5인 180초 4시나리오×3정책×5시드 60건. 새 10명 catalog/graph를 사용해도 Director 6d83dec와 제품이 같은 QA 6bb1be2 기준 전체 결과 JSON·규칙 버전 동일 |
| 실제 보관/분리 | 구 replay·compute 결과/통계 조회 보존. 새 catalog로 dataVersion·입력/실행 fingerprint 분리, 규칙/구현/요약 버전 유지. 실제 앱의 새 catalog 로드 pageerror 0 |

새 catalog ID: `2e6e8d0631f22763f3c40d1bf32b2eef5a0fe038f770fcc3904c57cd042af2f9`. 기존 5명의 character 데이터 및 기존 함수/중첩 스킬은 전부 그대로 포함된다. 참조표는 `skill_chains`·`roledata_clean` 등 7월 고정본이며 최신 9/17판으로 교체하지 않았다.

규칙 미상향은 기존 5인 결과 동일성으로 수용한다. 다만 **구 catalog를 그대로 써도 fingerprint는 달라진다**: SkillBody에 `weaponChange:null`이 직렬화되면서 graph 모양이 바뀐다. 실제 같은 요청에서 구 키 `ffeafdbf…` → `313fd39a…`; dataVersion/규칙/구현/요약 버전은 그대로다. 이는 안전하게 분리되는 변화이며 “fingerprint가 언제나 동일”하다고 보고하지 않는다. 새 catalog를 적용하면 다시 별도 키가 된다.

미지원 진단의 세부 경로도 구분한다. 홍련:흑영은 스킬 검사보다 앞선 무기 입력 검사에서 `이 검산에서 지원하는 무기 입력이 아닙니다.`, 레드 후드는 AllStep→NextStep 원천에 대해 `Invalid or conflicting burst source metadata.`로 거부된다. catalog의 실행 불가 판정과 일치하지만, 엔진 보고서의 “모두 미지원 공식 스킬: …로 거부”는 정확하지 않다. 부분 결과를 만든 사례는 없다.

## B-DATA 독립성과 검증 한계

QA HEAD와 `20a0609`의 제품 차이는 B-DATA의 API endpoint 2줄·SoloRaid 속성 DTO·BossCatalog/StrictGraph뿐이다. Engine/Core와 prepare_runtime.py는 대상 커밋과 동일하다. Director `6d83dec`와 QA `6bb1be2`는 src/apps/tools diff가 없고, 그 상태를 보관한 baseline API 및 자체 결과와 비교했다. S-SKILL 계산은 보스 속성 endpoint나 준비 파일을 사용하지 않는다.

UI `node --test tests/ui/*.test.mjs`: **6/7**. `registered_messages_match_server_sources`만 실패한다. 이는 Director가 미리 통지한 B-DATA 허용 목록 갱신 건이고 다음 QA 대기열 `e21b774`에서 확인한다. S-SKILL 제품 독립 검사 합계에는 포함하지 않았다. UI에 새 전용 “부분 지원” 배지를 추가한 것으로 판정하지 않는다. replay의 명시적 limitation은 확인했으며 compute 전달 누락은 차단했다.

## 증거·보존

- 종합: `artifacts/single-deck-qa/ssr1/evidence-index.json`; `source-audit.json`(1,164), `regression-audit.json`(797), `effects-audit.json`(57)
- 최종 실제 API: `artifacts/single-deck-qa/f2-ufix6-a80d1ba039d3/`, `summary.json`·`traffic.json`·`catalog-support.json`·새 replay 12건 및 compute 원문. 포트 **60294**, 소유 서버 PID 22268/18956/13388 종료
- 자체 검사: `check_ssr_source.py`, `check_ssr_api.py`, `check_ssr_effects.py`, `SsrProbe/`; 기존 QA PrecisionProbe 재사용. 구현·리뷰 검사/하네스/fixture/정답 미사용
- API/probe Release 빌드 각각 경고 0·오류 0. 초기 QA의 잘못된 API 진단 전체 일치 기대(실제는 앞 12개), 구 fingerprint 동일 기대, 하네스 TraceLimit 범위와 종료 프레임 포함 기대는 수정하고 최종 증거만 사용했다.

공개 원천 hash는 `source-hashes.json`의 8개 입력 전후 동일. 계산 공개 표는 앞서 원본 전후 hash를 확인한 QA 사본을 재사용했다. 원본 data/local 추가 접근 없음. 원본 accounts.db·세션·캐시·presentation·5180/5181 및 `C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe` 불변. 미추적 package-lock hash 보존·커밋 제외. push·배포·새 워커·부하 측정 없음. 1-tick/모션 실측은 수행하지 않았다.
