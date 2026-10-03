# S-SKILL-1 재QA — Director 범위 정정 반영 최종 통과

## Director 범위 정정 반영 최종 판정

2026-10-04 Director가 QA `6fc4481`의 기존 증거를 확인하고 이번 건의 수용 범위를 정정했다. **제품 `79a0830a1afc46bbbaf8d62239a6b05e0a4f8982`(엔진 대상 `849f81b`, E-PREC·B-DATA 통합 포함) 최종 판정은 통과, 차단 0건**이다. 새 실험·전체 재실행·제품 수정 없이 아래 기존 증거로 재판정했다.

- **SS1-Q-1 수용:** 구현 수정 지시 범위는 results·statistics였다. QA 재배정에서 batch 상태까지 넓게 쓴 것은 Director 문구 오류로 정정됐으며, **이번 건에 한해 BatchStatus를 수용 기준에서 제외한다. 선례로 적용하지 않는다.** results의 각 run·페이지와 statistics에 잠정 교체 무기 정책/관통 한계 식별자가 전달되고, 저장·서버 재시작 후 재조회되는 기존 실제 API 증거로 수용한다.
- **구 statistics 원시 바이트 2건:** 수정 전 바이너리끼리도 재현되는 `members` 키 순서 차이로, Director 판단에 따라 **비차단 후속**이다. 값·필드·저장 payload 보존은 통과지만, **원시 바이트 보존 통과로 표기하지 않는다.** 구 batch/results GET 및 실제 제공되는 replay/export 4경로의 바이트 동일, 구 resume 409 및 새 요약 버전/fingerprint 분리는 앞선 증거 그대로다.
- **BD1-F-Q-1 수용:** 생성기 218개 일치·Node UI 7/7·ESM 18/18 통과. E-PREC 797/797, S-SKILL 원천 1,164/1,164 및 효과/키/장탄 57/57, B-DATA 실제 API 545/545 회귀 증거도 유지한다.
- 원 검사 기록 **2,767건 중 2,764 통과·3 실패**는 수정하지 않는다. 실패 중 batch 1개는 정정된 수용 범위 밖, statistics 원시 바이트 2개는 기존 특성에 따른 비차단 후속이다. 이를 재실행으로 통과시킨 것으로 집계하지 않는다.
- **배포 후 잔여 한계:** BatchStatus의 한계 전달과 UI의 compute 한계 표시는 후속 과제로 남긴다. 현재 UI가 compute 한계를 표시한다고 주장하지 않는다. 교체 무기 잠정 모션·관통 다중 타격 미모델·1-tick/모션 실측 미판정도 유지한다. B-DATA 표시 파일 재준비 등 기존 배포 조건은 유효하며, 이 판정은 원본 배포 완료를 뜻하지 않는다.

아래는 **Director 범위 정정 전 `6fc4481`의 재QA 판정 이력**이다. 최종 수용 여부는 위 절을 따른다.

## 범위 정정 전 재QA 판정 이력

2026-10-04. 대상 엔진 `849f81b`(`f77b336` 수정·`3a0f9a5` Director 통합·허용 목록 재생성)을 검수 `25e8210` 위 일반 merge했다. 병합 커밋 **79a0830a1afc46bbbaf8d62239a6b05e0a4f8982**, 충돌 0. Director `0f6dea1`이 조상에 포함된다. 제품 코드 수정 없음.

**최종: SS1-Q-1 잔여 차단 1건(batch 상태 응답), BD1-F-Q-1 해소.** 독립 검사 **2,767건 중 2,764 통과·3 실패**다. 실패는 batch 한계 누락 1개와 구 statistics 원시 바이트 비교 2개이며, 후자는 수정 전 바이너리끼리도 재현되는 기존 키 순서 특성이다. 이를 새 계산/저장 회귀로 분류하지 않는다. 표준 UI **7/7**, 생성기 **218개 일치**, ESM **18/18** 별도 통과. 실측 1-tick·모션은 앞선 지시대로 범위 밖·미판정이다.

## SS1-Q-1 — results·statistics는 해소, batch 상태에는 아직 없음

원래 독립 QA `new-members-compute.json`과 편성·조건이 같은지 프로그램으로 대조한 뒤 실행했다. 리타·블랑·누아르·스노우 화이트·맥스웰, Lv400, 무장비, client_f32, 180초, crit off, `casts=[{frame:30,characterId:"5012"},{frame:400,characterId:"5001"}]`, CPU 1 worker·2회 기능 검증이다.

새 실험 `ac0c0ca290694485b20554208e144d80`은 2회 모두 completed, 팀 피해 **207,342,139**, 두 교체 무기 캐릭터의 burstCasts가 각각 1이다.

| 실제 응답 | 잠정 정책·관통 한계 |
|---|---|
| `GET /api/compute/experiments/{id}` (완료 batch 상태) | **없음 — 차단 유지** |
| `GET .../{id}/results` | 두 식별자와 설명 있음, 각 run에도 보존 |
| `GET .../{id}/statistics` | 두 식별자와 설명 있음 |
| results의 1건씩 페이지 | 각 페이지에 두 항목 중복 제거, 빈 페이지에는 없음 |
| 서버 재시작 후 results/statistics | 저장한 두 항목 그대로 조회 |

두 식별자는 `replacement_weapon_provisional_motion:provisional_no_spot_delay_full_charge_fixed_magazine`, `pierce_multi_hit_not_modelled`다. 설명은 게임 미확정 잠정 모션과 교체 샷의 단일 타격 계산을 식별할 수 있다. 교체 캐릭터가 있어도 casts 없이 실제 교체 총을 쓰지 않은 실행에는 새 필드가 없다.

완료 batch JSON의 최상위 키는 `id,state,attempt,requested,valid,failed,cancelled,partial,input,execution,errorCode`이며 하위에도 두 식별자/설명이 없다. 이번 재QA 지시 (1)의 **batch·/results·/statistics** 중 batch 응답이 충족되지 않는다. `BatchResults`라는 DTO 이름과 `BatchStatus` 응답은 서로 다르다.

근거: `src/Nikke.Contracts/Compute.cs:56`의 `BatchStatus`에는 해당 필드가 없고, `src/Nikke.Api/ComputeEndpoints.cs:43`은 `jobs.Status(id)`를 그대로 반환한다. 이번 수정은 run·BatchResults·StatisticsResult에만 연결했다. UI의 전용 한계 표시 추가는 이번 범위로 요구하지 않았다.

최소 재현은 최종 API 증거의 `new-members-compute.json`과 `summary.json`에 있다. 저장 내용·호출 원문을 그대로 보존했으며 QA가 제품을 고치지 않았다.

## 버전·fingerprint·구 결과 호환

- 실제 수정 전 바이너리(`25e8210` 제품, 요약 `.6`)로 격리 root에 구 실험 2개(기존 5인·교체 캐릭터)를 생성하고 현재 `.7` 서버로 교체했다. **summaryVersion/engineVersion 모두 `cpu-summary.6-precision-1` → `cpu-summary.7-run-policies`**, 입력/실행 fingerprint 분리. rulesVersion·dataVersion·inputSchemaVersion·roundingPolicy는 동일하다.
- 구 두 실험의 **batch GET·results GET 원시 바이트 동일**, DB의 저장 run payload 문자열도 동일하다. 구 resume 2개 모두 **409 `engine_or_rules_version_changed`**. 구 결과에 새 limitation을 소급하여 붙이지 않는다.
- 구 statistics의 JSON 값은 모든 수치·필드가 동일하고 새 limitation 키가 없다. 그러나 **원시 바이트 동일은 실패**했다. `members` 객체의 키 순서가 달라진다. 예를 들어 기존 5인에서 최초 `5004,5008,5009,5044,5011` → **수정 전 바이너리 재시작만으로** `5009,5008,5044,5004,5011`이 됐다. 교체 캐릭터 구 통계에서도 같은 제어 실험이 재현됐다. 이는 기존 `ComputeAnalysis.cs:72`의 `ToImmutableDictionary` 열거 순서와 부합하며 해당 줄은 이번 수정에서 바뀌지 않았다. **바이트 보존 요구를 완전히 충족했다고 보고하지 않는다.** 신규 손실/계산 회귀는 없고, 키 순서를 고정할지는 별도 범위 판단 사항이다.
- 구 replay GET·export.json·damage-log/export.json·damage-log/export.csv **4경로 원시 바이트 동일**. compute 전용 export 경로는 기존/현재 API 모두 제공하지 않는다. 존재하지 않는 compute export를 검증한 것으로 집계하지 않았다.
- 기존 5인 새 run의 피해·발수·타수·크리·장전·버스트·방어 전환 및 통계 값 동일, 새 optional limitations 키 없음. 교체 캐릭터 전후 수치도 동일하다. 새 서버 재시작 후 notes 복원, 전체 HTTP 500=0.

## 이전 수용 항목 및 세 건 통합 회귀

| 검사 | 결과 |
|---|---|
| S-SKILL 원천 자체 판독 | **1,164/1,164**. 8개 공개 원천 전후 hash, 계수·지속·트리거·교체 프로필·strict Pierce 파싱. catalog ID `2e6e8d0631f22763f3c40d1bf32b2eef5a0fe038f770fcc3904c57cd042af2f9` 그대로 |
| S-SKILL 실제 API | **201/204**. 위 잔여 batch 1개·기존 statistics 바이트 2개 외 통과. 두 캐릭터 lv1/5/10 auto/manual, 독립 피해 산술, 저장/export, tap 거부·미지원 3명 실행 거부·부분 저장 없음, 실제 Chromium 앱 모듈 로드 정상 |
| 효과·키·E-PREC 상호작용 | **57/57**. 기본 장탄 100+raw1450→115, 교체만 1→0. 정수 차지 단축, SW 주기/버프/크리 창, 맥스웰 상위 공격력 2명, data/graph/conditions 키 분리·변조 Restore 거부 |
| E-PREC 및 기존 5인 | **797/797 재실행**. 독립 산술/런타임 737건 + 180초 4시나리오×3정책×5시드 60건, Director 6d83dec와 제품이 같은 QA 6bb1be2의 자체 결과 JSON과 정확히 동일 |
| B-DATA 통합 실제 API | **545/545 재실행**. 원래 8개 주입 409, 중첩 strict·미선언 null/키 누락·모든 컬렉션/딕셔너리 null 요소, 선언 null·실제 0, 구 준비 파일409/현 파일200, 기존 목록 바이트·계산 입력/fingerprint·replay/compute 보존. HTTP500=0 |
| BD1-F-Q-1 | 생성기 `--check` **218개 일치**, 표준 `node --test tests/ui/*.test.mjs` **7/7**, 실제 파일 바이트를 표준입력으로 전달한 `node --input-type=module --check` **18/18** |

범위 점검: `25e8210 → 79a0830`의 제품 변경은 Engine의 요약/정책 상수 2파일, Data `ComputePreparation`, Contracts `Compute`, API `ComputeEndpoints`, Analysis `ComputeAnalysis`, UI 등록 목록뿐이다. 발사·피해·장탄·스킬 실행 규칙이나 B-DATA 읽기/준비기 변경은 없다. Analysis는 동일한 run을 materialize한 뒤 한계를 모으는 연결만 추가했다. Director 승인 예외 밖의 제품 동작 변경은 찾지 못했다.

엔진 보고서 정정 2건도 반영됐다(`docs/ssr-skill-batch1-engine.ko.md:52`, `:102`): 홍련 : 흑영은 무기 입력 검사, 레드 후드는 burst metadata 검사에서 먼저 거부되며, 구 catalog도 `weaponChange:null` 직렬화 때문에 과거 graph fingerprint가 바뀐다는 설명이 있다. 이번 `.6→.7` 요약 버전 분리는 그 과거 graph 변화와 별개다.

## 증거·보존

- 종합: `artifacts/single-deck-qa/ssr1r2/evidence-index.json`; source/effects/regression audit, generator/UI/ESM 및 빌드 로그.
- S-SKILL 최종 실제 API: `artifacts/single-deck-qa/f2-ufix6-0ee1a2b13c91/`; `new-members-compute.json`, `summary.json`, `traffic.json`, `old-restart-control.json`, `old-wire-comparisons.json`, `old-wire-difference-*.json`, 전후 compute 및 export 증거.
- B-DATA: `artifacts/single-deck-qa/f2-ufix6-fbced451bee4/summary.json`, 주입 행렬·traffic. 고정 준비 파일은 앞선 독립 QA 산출물 사본을 사용했다.
- 독립 하네스 `tests/single_deck_compute_qa/check_ssr_readmission.py` 추가, 기존 자체 source/API/effects 검사에 출력 폴더·요약 버전 상향 구분을 추가했다. 최초 API 시도의 문장 검색이 `Pierce`의 대문자를 실패로 본 기대를 대소문자 무관으로 수정했다. 최종 판정은 식별자·내용을 응답별로 검사한 재실행 기준이다. 구현·리뷰 하네스/정답/응답 mock 미사용. 명시 요청한 표준 UI suite와 생성기만 공통 검사로 사용했다.

API 및 자체 probe Release 빌드 경고0·오류0. 격리 포트 **58235/58238**, 소유 API PID **14308/35228/37160/37780/28824/31892**, **37584/28416** 모두 종료. 최초 시도 포트49929의 소유 서버도 종료했다. 원본 data/local 추가 접근 없이 공개 표 QA 사본 재사용·원천 hash 보존. 원본 계정·세션·캐시·presentation·5180/5181 및 사용자 실행 EXE 불변. package-lock hash 보존·커밋 제외, push·배포·새 워커·부하 측정 없음.

통합본 최종 수용은 batch 잔여 차단 때문에 보류한다. B-DATA 배포 시 `challenge.levelChangeGroupId`를 포함하도록 표시 파일 재준비가 필요하다는 앞선 조건도 유지한다. 정식 실행 경로는 `C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe`이며 이 QA는 원본 배포 완료를 뜻하지 않는다.
