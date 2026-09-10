# P03-C1~C6 연결 보강 완료

2026-09-10. [계획](p03-connection-plan.ko.md)의 6단계를 구현하고 검증했다. **P04에서 사용할 실행 연결부가 준비된 상태**다. 실제 게이지 누적·버스트 단계 자격·시전자 선택을 포함한 자동 사이클은 아직 구현하지 않았다.

## 구현 결과

| 단계 | 완료 내용 |
|---|---|
| C1 입력·출처 | 공식 character/role/정제 weapon의 단계·지연·지속시간·게이지 값 대조. ConfigBattle KV와 기존 게이지 파생 표 대조. 모두 불일치·누락 시 준비 실패. 원천 hash와 raw 단위를 catalog에 보존 |
| C2 실행 이벤트 | 발사·탄 소비·평타 명중·직접 스킬 타격·추가타·재장전·시전·쿨다운·풀버스트 이벤트를 `ICombatEventSink`로 전달. 상세 기록과 독립적으로 전투 끝까지 전달 |
| C3 쿨다운 | `ISkillBattleControl.GetCooldown/TryCast` 연결. 기존 1/300초 deadline이 유일한 상태. 변경 전/후 시각과 요청/실제 적용량 기록. 미준비·중복 시전·잘못된 호출 단계 구분 |
| C4 풀버스트 | 지정 시간표와 `ISkillBattleDriver`가 공통 진입·종료 함수를 사용. 중복 진입/종료 방지. 전체 지속시간과 원인 시전·버스트 단계 전달. 무기 모드와 풀버스트 만료 분리 |
| C5 회귀 | 새 연결 검사 11개 추가. 기존 스킬 25개·무기 7개 및 계산 검사 유지. 최종 공격력 대상 정렬 검사 보강. 원천 불일치/누락·교체 무기 미확인 표시 검사 추가 |
| C6 인계 | 정수화 3후보의 변경 전/후 180초 결과 및 전체 실행 이벤트 대조. 새 저장 4개·이전 저장 3개 API 재조회. 데스크톱 배포 폴더의 백엔드 갱신 및 계정 스펙 보존 확인 |

## 제어기 계약

`SkillReplay.Run(..., events: sink, driver: driver)`로 연결한다. `driver`가 있으면 지정 `Casts`/`FullBurstWindows`와 혼용을 거부한다. 자동 사이클을 흉내 내는 새 시간표는 제품 경로에 추가하지 않았다. 검사 도구의 `ScheduleDriver`는 기존 지정 조건을 동일하게 전달해 두 경계를 비교하는 용도다.

프레임 내 순서는 기존 계산 순서를 유지한다.

1. 회복 tick, 만료, 관측 HP, 조건 갱신.
2. 예정된 풀버스트 종료와 종료 트리거 처리 후 `FullBurstExit` 제어 단계.
3. 주기 스킬 처리 후 `CastSkills` 제어 단계.
4. `FullBurstEntry` 제어 단계와 진입 트리거.
5. 조건 갱신, 발사·탄 소비·펠릿 피해·명중 트리거, `AfterHits` 단계.

시전 요청은 `CastSkills`, 진입 요청은 `FullBurstEntry`, 종료 요청은 `FullBurstExit`에서만 가능하다. 이벤트 콜백 안에서 전투를 재진입시키는 변경 요청은 `WrongPhase`로 거부한다. 콜백은 같은 전투 스레드에서 동기 호출되며, 제어기가 이벤트를 모아 정해진 단계에서 명령을 내린다. 이벤트 처리 예외는 실행 실패로 전파한다.

`CombatEvent.Sequence`는 실행 이벤트의 연속 순번이다. `TraceId/ParentTraceId`는 상세 저장 여부와 관계없이 생성하는 기존 원인 ID다. 같은 발사에서 탄 소비가 별도 이벤트로 발생할 수 있으므로 중복 제거 키로 TraceId만 사용하지 않는다. 타격에는 발사 원인 ID·펠릿 번호·무기 shot ID·풀차지/크리/코어/풀버스트·피해량을 담는다.

쿨다운 변경은 정수 tick 단위다. `Cause=cast_started`는 시전으로 deadline을 설정한 변경이고, `Cause=effect`는 스킬 쿨감이다. 준비된 동료에 대한 음수 쿨감은 요청량이 있어도 적용량 0이 될 수 있다. 제어기는 이벤트로 별도 쿨다운 사본을 만들지 않고 `GetCooldown`을 조회한다.

풀버스트 요청의 `Meaning`은 `total_duration_from_full_burst_entry`다. 모더니아의 900프레임은 전체 15초이며 추가 15초가 아니다. 원천 적용 지연 1cs와 III→풀버스트 지연을 같은 값으로 취급하지 않는다. 짧은 검사에서 사용한 28프레임 간격은 연결 경계를 검증하기 위한 명시적 fixture이며, 이번 작업에서 새로 실측 검증한 값이 아니다.

## 기록·호환

- 실행 규칙: `p03.skills.2`, 연결 계약: `p03.connection.1`.
- 새 runtime catalog: `30b3b0be42d2c6da1ea982304f38688762656e7ef82308e1024598252e4d7dc8`.
- 기존 catalog·계정 snapshot·저장 검산 파일은 유지한다. catalog schema 1에 `connectionSchemaVersion=1`, `gaugeConstants`, 캐릭터별 `burstConnection`을 추가했다.
- 새 결과의 `connection`에는 이벤트 종류별 총수, 작은 제어 타임라인, 종료 시점의 쿨다운과 풀버스트 상태가 있다. 상세 피해 로그 off/잘림과 별도로 생성한다.
- 제어 타임라인도 최대 20,000개의 별도 상한이 있고 초과하면 `timelineTruncated=true`다. 이벤트 전달·총수·최종 상태는 계속 유지한다. 이번 180초 검사는 250개로 전체 구간을 보존했다.
- 이전 `p03.skills.1` 기록은 `connection=null`로 읽는다. 과거 실행에 연결 준비 상태를 소급하여 붙이지 않는다.
- API 지원 표시에서 `connectionReady`, `burstSourceAvailable`, `gaugeFormulaStatus`, `automaticCycleReady`, `gameVerified`를 구분한다. 현재 자동 사이클과 게임 검증 상태는 false다.

## 검증 결과

| 검증 | 결과 |
|---|---|
| Core/Engine | **73개 통과**, 실패·건너뜀 0. 기존 62개 + 연결 경계 11개 |
| Data/Storage | **51개 통과**, 실패·건너뜀 0 |
| Python runtime catalog | **6개 통과** |
| 공식 5인·180초 | 3후보 모두 변경 전/후 구성원·effect별 피해·발수·탄 소비·잔탄·쿨다운 일치 |
| 지정 경로/제어기 경로 | 상세 off와 상한 3개 조건에서 전체 이벤트 스트림 SHA-256, 제어 요약, 구성원 결과 일치 |
| 이벤트 전달 | 후보별 **56,124개**, 마지막 이벤트 **10,800프레임**까지 전달. 발사 15,088회·탄 소비 14,188회·평타 명중 17,518회·추가타 8,979회 |
| 사이클 요약 | 지정 진입 9회·종료 8회. 마지막 창의 종료는 10,801프레임이므로 180초 종료 시 활성 상태가 맞음 |
| 모더니아 별도 검사 | 공식 스킬 자료로 무기 복원 901프레임, 지연하여 진입한 풀버스트 종료 929프레임을 각각 확인. 짧은 상세 trace는 잘림 없음 |
| API | 새 저장 4개·이전 저장 3개 재조회 통과. 상세/요약 연결 결과 일치, 잘못된 정수화·쿨다운 시전 거부 |
| 사용자 데이터 | 갱신 전/후 계정 snapshot 2개의 정규화 JSON hash 일치 |

180초 비교 조건은 실제 저장된 스킬 레벨, 시나리오 레벨 400, 방어력 30,925, 자동 사격, 크리 off, SG `per_trigger`, 지정 시전/풀버스트 시간표다. 피해 총합은 다음과 같으며 **변경 전 값과 정확히 일치**했다.

| 정수화 후보 | 피해 |
|---|---:|
| legacy_term_floor | 912,275,251 |
| final_round_even | 912,300,103 |
| nested_floor | 912,275,251 |

이는 연결 변경으로 계산이 변하지 않았다는 증거다. 게임에서 관측한 피해나 정수화 정답을 뜻하지 않는다. 150개 슬롯/레벨 정의의 지원 검사는 구조 검사이고, 150개 전투 구성을 모두 실측한 것이 아니다.

검증 파일은 Git에서 제외된 `artifacts/p03/connection-implementation/`에 있다: `connection-tests.trx`, `storage-data-tests.trx`, `official-180s-audit.json`, `modernia-short-trace.json`, `api/connection-api-summary.json`, `account-preservation.json`.

재실행:

```powershell
./scripts/audit-p03-connection.ps1 -Baseline ./artifacts/p03/connection-review/api-audit/artifacts/p03/skill-audit-replays.json
# 실행 중인 로컬 API에 대해 새 검산 기록을 생성하고 저장 호환성을 확인:
# 프로젝트 Python으로 tools/data-pipeline/audit_p03_connections.py 실행
```

## 기능별 출처

| 기능 | 출처 | 채택 방식 |
|---|---|---|
| 스탯·OL·차지·히트 계산 | 현행 `Nikke.Core` 및 사용자 확정 사항 | 계산 코드 변경 없음. 시전자 OL로 시전자 기준 공증 부여량을 증폭하지 않음 |
| 발사·탄창·차지 진행 | 기존 P03 `SkillFiringModel`, 원본 C# `FiringModel` | 발사 모델 변경 없음. 반환된 실제 상태에서 이벤트 생성 |
| 스킬 트리거·연결 함수·쿨감 | 현행 `SkillReplay`와 고정 공식 skill graph | 기존 실행/정수 deadline 유지. 명령·조회·이벤트 경계 추가 |
| 버스트 단계·지연·지속·무기 게이지 | `skill_chains.json`, 원천 `blabla_roledata.json`, 고정 `roledata_clean.json` | 3개 자료의 해당 값 대조. raw/centisecond 단위로 보존 |
| 공통 게이지 상수 | 기존 `Database/processed/burst_gauge_table.json` 및 `sd_bin_json/ConfigBattleTable_kv.json` | 실제 상수 일치 확인 후 두 원천 hash 고정. 충전식은 미확정 유지 |
| 게이지 표 생성 경로 | 기존 `DataPipeline/crawler/getFromLocalSdBin.py` | sd.bin JSON→ConfigBattle KV 추출 경로를 읽기 전용 확인 |
| 이벤트 종류 구분 | 기존 `SimulatorEngine/Nikke.Simulator.Engine/Events/BattleEvent.cs` | 개념 참고. 원본 Combatant 의존 및 다목적 IntValue 구조는 복사하지 않음 |
| 실행 이벤트·제어기·제어 요약 | 신규 `CombatEvents.cs`, `SkillReplay` 연결부 | 이 프로젝트에서 작성 |
| 원천 대조·회귀·180초/API 감사 | `prepare_runtime.py` 확장, 신규 `BattleConnectionTests`, `tools/connection-audit`, `audit_p03_connections.py` | 이 프로젝트에서 작성. 기존 감사 도구는 출력 경로를 지정할 수 있게 확장 |

추가 원천의 정확한 경로와 SHA-256은 [P03 출처 manifest](p03-source-manifest.json)에 있다. 원본 `Nikke-Dmg-Simulator` 파일은 변경하지 않았다.

## 남은 사항과 P04 인계

- 모더니아 교체 shot **1026002**: `StaticData.zip` 안에 `CharacterShotTable.mpk`가 존재하지만 현행 디코더에는 해당 스키마가 없고 디코딩된 JSON도 없다. 기본 roledata에는 기본 shot 1026001만 있다. `unresolvedReplacementShotIds=[1026002]`로 보존했다. 게이지/범위 등 누락값을 기본 무기의 확정값으로 채우지 않는다. 기존 비교 실행기의 기본 형상 사용 한계는 그대로 명시한다.
- 공통 게이지 상수와 무기 게이지 값의 결합 방식은 `formulaStatus=unverified`다. 숫자가 확보되었다는 이유로 발사·명중·추가타 모두에 중복 충전을 구현하지 않았다. `HitEventData.GaugeEligibility=unresolved`를 P04에서 원천 규칙과 연결한다.
- 실제 단계 자격·시전자 우선순위·지연·재진입 정책·게이지 축적은 P04다. 보스 방어력 20억 경계 전환·파츠·피격·실측 대조는 P05다.
- 조건부 큐브·애장품 교체·미지원 캐릭터를 지원 완료로 승격하지 않았다. 사용자 제공 영상/틱 데이터와 대조하기 전 `gameVerified=false`를 유지한다.

2026-09-11 P04 후속: 사용자 확인에 따라 모더니아 교체 shot의 게이지 조사를 P04 선행 조건에서 제외했다. 기본 무기 복귀 후 충전하는 자동 사이클 구현과 남은 별도 무기 검증 사항은 [P04 기록](p04-team-burst.ko.md)에 정리했다.
