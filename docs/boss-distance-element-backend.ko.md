# F-COND-B — 보스 거리·약점 Backend (2026-09-28)

**후속 B-FIX-2:** 최초 인계 후 독립 QA가 malformed runtime의 누락값 처리 결함을 발견했다. 아래 최초 검증은 정상 카탈로그 범위의 역사 기록이며, 결함 수정·추가 검증은 문서 마지막 절을 따른다. Backend 수정 완료와 독립 재수용·원본 배포는 구분한다.

## 완료 범위

기준 Director `cd004f1`을 Backend `74ca24f` 위로 일반 fast-forward merge했다. 기존 작업 이력과 미추적 root package-lock.json을 보존했다. 카탈로그·읽기 전용 API를 먼저 구현했고, **Director 통지 후** 엔진 `f374c1d`(구현 f9ce075, 기준 merge d21895b 포함)를 일반 fast-forward merge했다. 충돌0. Backend 연결·격리 API 검증 완료이며 UI·독립 QA·원본 배포 완료 선언은 아니다.

## 원천과 카탈로그 준비

기존 공개 `Nikke-Dmg-Simulator/Database/raw/blabla_roledata.json`, `docs/p03-source-manifest.json`의 sourceRoles 항목을 사용한다. SHA256 `8568963a75d971cf97489be79bf6f81829bf4e20fdccc74ed10b28159c304348`. 파일 hash를 source version으로 고정하고 불일치하면 재검토 없이 다시 고정하지 않는다. 네트워크·재수집·게임 실행 파일·프로세스 접근 없이 기존 파일만 읽는다.

`prepare_runtime.py`는 runtime의 `combatProfiles`에 공개 roster 192명의 ID/name/weaponType/bonusrange_min/max/element와 출처를 추가한다. `prepare_combat_conditions.py`는 기존 runtime graph를 그대로 둔 채 같은 확장만 수행하는 독립 명령이다. 명시 `--runtime-root`가 필요하며 새 hash 디렉터리와 current 포인터를 만든다. 이전 catalog는 보존하고 반복 실행 결과는 동일하다.

```powershell
python tools/data-pipeline/prepare_combat_conditions.py --runtime-root '<준비할 격리 dataRoot>/runtime' --source-roster '<기존 공개 blabla_roledata.json>'
```

이 명령은 계정/세션/캐시를 읽지 않는다. 이번 실행은 Backend artifacts에 복사한 공개 runtime에만 적용했다. 현재 사용 중인 원본 dataRoot에는 실행하지 않는다. 추후 Director 배포 시 기존 배포 runtime에도 준비 단계가 필요하며, 코드 merge만으로 Git 제외 카탈로그가 바뀌지 않는다.

| 무기군 | 다수 사거리 | 인원 | 예외 |
|---|---|---:|---|
| AR | 25–45 | 35 | 없음 |
| MG | 35–55 | 24 | 없음 |
| RL | 0–0 | 41 | 보너스 없음·확인 필요 |
| SG | 0–25 | 26 | 없음 |
| SMG | 15–35 | 30 | 없음 |
| SR | 45–100 | 35 | 5042 Harran(하란), 25–45, Electronic 1명 |

이 표의 수치는 실제 profiles를 그룹화한 결과다. 코드에 범위/예외 캐릭터를 하드코딩하지 않는다. `isTypical`은 최다 인원 구간(동률이면 min/max 순), 나머지 실제 캐릭터는 exceptions다. 계산에는 무기군 대표값이 아닌 캐릭터 값을 사용한다. RL0–0 보너스 없음, 양끝 포함·일반 공격 전용은 사용자 배정의 잠정 실험 규칙이며 실게임 정확성 수용이 아니다.

## UI 읽기 전용 API 확정

`GET /api/runtime/combat-conditions` → `runtimeDataId,schemaVersion:1,source,weaponRanges,elements,rangeRule,gameVerified:false`.

- source: 상대 source path, sha256, `version:"sha256:<hash>"`, 공개 origin, locale.
- weaponRanges: `weaponType,characterCount,ranges,exceptions,rangeBonusAvailable,diagnostics`. ranges는 `min,max,count,isTypical,characterIds`; exceptions는 아래 멤버 profile.
- elements 값은 `Fire,Water,Wind,Iron,Electronic`. 각각 `value,iconUrl`; 기존 `/editor/assets/ui/code-{fire,water,wind,iron,electric}.png`다. Electronic의 이미지명만 electric이며 wire 값을 Electric으로 바꾸지 않는다.
- profiles가 없는 옛 runtime은 HTTP409 `combat_profile_catalog_missing`이다. 무기군 표로 값을 추정하거나 원천을 자동 재수집하지 않는다.

`GET /api/snapshots/{id}/combat-conditions?characterIds=5011,5008,5004,5009,5044` → `runtimeDataId,snapshotId,members`. 저장 snapshot에 있는 중복 없는 1~5명만 허용하며 요청 순서를 유지한다. 이 조회는 전투 지원 캐릭터를 확대하지 않는다.

멤버 profile: `characterId,name,weaponType,bonusRangeMin,bonusRangeMax,element,rangeBonusAvailable,diagnostic`. name은 공개 원천 영문명이며 UI는 ID로 기존 한국어 이름과 연결할 수 있다. RL0–0은 `rangeBonusAvailable:false,diagnostic:"rl_zero_range_no_bonus_unverified"`. 누락된 ID나 자료는 명시 오류이며 default 범위/속성을 만들지 않는다.

## 엔진 연결 전 검증

Python 파이프라인 신규4 tests 통과: 원천 범위·SR/RL 보존, 누락/소수/잘못된 속성 거부, hash불일치 거부, immutable/idempotent 확장·graph 보존. 최초 Sync 회귀101 tests 통과(기존99+카탈로그2). 기록 `artifacts/boss-conditions-catalog-tests.log`, `artifacts/boss-conditions/catalog-tests/`.

격리 API stage A `artifacts/boss-conditions/api/618613defe4549b7a66adfd26ef3b631/summary.json`: passed, 포트53025. 새 합성 계정·공개12파일+원천 roster hash 보존. catalog192명/6무기군/SR예외/RL, 덱별 순서·소유 검사, 기존 bool replay 저장/조회 및 snapshot불변 통과. 새 runtime ID `9c98c91c6df670a35c9a2da0446961a61141cb5be19ca9718e608120608e71cd`.

120프레임/5인/400/DEF30925/crit off/기존 두 bool true의 전환 전 합성 기준은 총 **1,586,529**, 멤버 순서 5011/5008/5004/5009/5044에 따라 306289/180378/249173/632940/217749다. 장시간 부하나 실측이 아니다. 첫 API 시도 d01540a1은 새 API 빌드 완료 전에 시작해 route 오류로 실패했고 통과에 포함하지 않는다. 해당 본인 프로세스는 종료했다.

## 보존 경계

실제 사용자 실행 파일은 `C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe`. 이번 작업은 Backend 격리 검증이며 원본 EXE/설정/바로가기/계정/세션/캐시/5180/5181 프로세스를 변경하지 않는다. 원본 배포·실게임·UI 독립 수용은 별도다. package-lock.json SHA256 `2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767` 보존·커밋제외, push/새 Run/Dispatch/하위 워커 없음. 완료 시 Director에만 터미널 재조회 후 한 번 인계한다.

## 조건 wire·과거 표시 확정

솔로 replay `POST /api/runtime/skill-replays`, compute `POST /api/compute/experiments`의 `conditions.combat` 안에 다음을 사용한다. 상세 계약도 [single-deck-compute-contract.ko.md](single-deck-compute-contract.ko.md)의 F-COND-B 절에 있다.

```json
{"bossDistance":35,"bossWeakElement":"Fire"}
```

거리: 정수0–100 또는 null. 약점: Fire/Water/Wind/Iron/Electronic 또는 null. 둘 다 없음도 **새 모드로 저장하려면 두 필드를 명시 null**로 보낸다. 새 요청에서 `properDistance`/`elementAdvantage`를 넣지 않는다. false 또는 새 필드 null도 혼용 거부 대상이다. 과거 bool 요청은 값 그대로 전원 적용 경로로 실행한다. 미지원 철자/소수/범위/혼용은 HTTP400이다. 단일 hit API의 수동 bool 입력은 변경하지 않았다.

새 saved replay 최상위 및 compute의 `BatchStatus.input`에 `conditionCompatibility`를 저장한다:

```json
{"mode":"per_member","label":"보스 거리·약점(멤버별)","legacyProperDistance":false,"legacyElementAdvantage":false,"bossDistance":35,"bossWeakElement":"Fire"}
```

과거 조건은 `mode:"legacy_global",label:"이전 방식(전원 적용)"`이고 legacy 두 bool을 실제 값으로 보존한다. UI는 label/mode로 표시하고, 다시 실행 시 새 모드에서는 boss 두 값만, 과거 모드에서는 legacy 두 값을 기존 JSON 이름으로 보낸다. **compatibility 객체를 combat 안에 그대로 합치지 않는다.** 두 boss 값 null도 mode=per_member를 저장하므로 엔진의 null 생략 직렬화 뒤 구 모드로 오인하지 않는다.

기존 저장 파일은 덮어쓰지 않는다. old/new 모두 다음 읽기 API로 모드를 확인할 수 있다:

- `GET /api/runtime/skill-replays/{id}/condition-compatibility`
- `GET /api/compute/experiments/{id}/condition-compatibility`

이 조회는 저장된 원형 조건에서 표시 정보만 반환한다. 기존 replay GET/JSON export는 여전히 당시 파일 그대로이며 새 계산을 하지 않는다. 구 compute 결과도 조회 가능하고, 이전 엔진 버전의 resume 거부는 기존 버전 분리 규칙대로 유지한다. 같은 bool 조건을 새 실험으로 실행하는 경로는 재현 가능하다. SavedBurstTactic 자체에는 전투 거리·속성 조건을 저장하는 필드가 없으므로 전술 객체에 임의 마이그레이션 필드를 추가하지 않았다.

## 엔진·compute 연결

RuntimeReplayService의 skill/weapon replay 및 PrepareCompute가 `WeaponReplayMember.BonusRangeMin/Max/Element`를 원천 profile에서 채운다. 새 거리/약점을 사용하는데 old runtime에 profiles가 없으면 409 자료 준비 오류다. metadata가 필요 없는 과거 bool은 old catalog에서도 계속 실행 가능하다. 현재 자료는 검증된 전체 profile을 제공하고, 누락값을 추정하지 않는다.

엔진 rules는 `p03.skills.4-boss-conditions`, `p04.team.4-boss-conditions`, summary는 `cpu-summary.3-boss-conditions`; Backend rules에도 `boss-distance-element.1-inclusive`를 추가했다. fingerprint는 boss 두 값, mode 표시 메타데이터, 멤버별 사거리·속성, 원천 runtime ID를 포함한다. 모두 null인 새 모드와 필드 없는 과거 모드도 구분하고, 저장 복구 때 재계산 fingerprint를 검사한다. 두 모드는 피해가 같아도 기록이 섞이지 않는다.

`ComputeOverloadCatalog`의 IncElementDmg 후보는 새 모드에서 해당 멤버의 Element=BossWeakElement일 때만 유효하다. 전역 bool을 사용하는 과거 모드는 그대로 유지한다. 이 변경은 후보 생성 Data adapter만 수정했으며 Analysis 산술은 수정하지 않았다.

## 최종 검증·근거

전체 솔루션 최종 Release 빌드 경고0/오류0(45.73초). .NET **372/372** 통과, 실패0/skip0: Backend **157**(Sync112+Compute45), Core/Engine174, Analysis41. Python catalog4+기존 runtime6 = **10/10** 통과. 근거 `artifacts/boss-conditions-final-build.log`, `artifacts/boss-conditions-final-tests.log`, `artifacts/boss-conditions/final-tests/*.trx`. 엔진 tests는 merge 원본 그대로 재실행했고 Backend가 고치지 않았다. 앞선 통합371개 통과 후 typed 엔진과 raw 후보 분류의 Combat/combat 대소문자 처리 일치를 보강하고 회귀1개를 추가해 최종 재검증했다.

신규 회귀는 원천 집계·누락 거부, 원형 JSON의 false/null 혼용 거부, old 표시, 약점 일치 후보, boss 값/멤버 사거리/명시 미설정 mode의 fingerprint·튜닝 키 구별 및 준비 입력 복구를 포함한다. raw 필드 원형 검사를 역직렬화 전에 수행하고 typed 직접 준비도 엔진 Validate로 검사해 명시 null이 직렬화 중 사라지는 혼용 우회를 막았다.

최종 실제 통합 API `artifacts/boss-conditions/api/f1f1bc44f3a746efa3ae5ba26e9e3450/summary.json`: **passed**, 격리 포트63300. 새 합성 계정2개(기본 replay용·OL용), 공개 자료12파일+roster1개 총13개 source hash 변경0. 본인 API 프로세스만 종료했다. UI·게임 실행 없이 HTTP와 영속 응답을 확인했다. 앞선 `739c76704b5a4764b44e474d338fd9db`(포트52983)도 통과했으며 최종 실행은 Combat 대소문자 입력의 null 모드·OL 분류까지 추가 확인했다. 결과/fingerprint는 앞선 실행과 같고 표본 수를 합산하지 않는다.

- stage A의 기존 bool replay와 **각 멤버 결과 전체 및 총 피해1,586,529 정확 일치**. old metadata label·저장/GET도 일치.
- 새 거리35/약점Fire의 normal hit flags는 리타(true,false), 블랑(true,false), 앨리스(false,true), 누아르(false,false), 모더니아(true,true). 멤버별 원천 metadata, 저장/GET, 팀합=멤버합 확인. 새 총피해1,294,453, 모두 null은1,120,137. 이 숫자는 120프레임 합성 입력의 회귀 근거다.
- replay 소수/범위/철자/혼용7개와 compute false 혼용1개를 모두400으로 거부. 두 조건 모두null의 저장된 per_member 표시와 보너스 없음 확인.
- 각 멤버 T10 head/공증1줄인 별도 합성 snapshot에서 compute 120프레임 **정상 batch 각1회** 세조건 통과. 원소 OL 후보는 Fire 약점의 앨리스·모더니아만, 없음은0명, 과거 bool true는5명. 팀 통계 각N=1, snapshot불변, fingerprint/튜닝 키 모두 다름·cacheSource=miss.

| compute 조건 | 팀 피해 | input fingerprint |
|---|---:|---|
| 거리35·Fire | 1,508,042 | `13378a631aca1b409b42e426a82a96e9f39facea473dfd40a3a5dd0c5d7171f1` |
| 새 미설정/없음 | 1,304,192 | `4cc5bea8983ea0291da1326d3a702aebf00668fc73e61c74ed19270444a2af16` |
| 과거 전원 두 bool true | 1,847,281 | `b16b77626030f23861639b3431d54f8548ac9f55ed9869ded347ee21cb1b53f8` |

튜닝 warmup/후보 호출은 정상 표본에서 제외했다. 장시간·최적 worker·성능 비교·실게임 정확성 수용은 아니다. RL과 SR 예외는 카탈로그/엔진 합성 회귀 범위이며 RL 전체 전투 지원을 확대한 것이 아니다. 양끝 포함·RL0–0 해석은 잠정 실험 기본값이다.

```powershell
$env:DOTNET_CLI_HOME=Join-Path $PWD '.tools/dotnet-home'
& '<dotnet>' build Nikke.Simul.slnx -c Release --no-restore
& '<dotnet>' test Nikke.Simul.slnx -c Release --no-build --no-restore
python -m unittest discover -s tools/data-pipeline/tests -p test_combat_conditions.py -v
python -m unittest discover -s tools/data-pipeline/tests -p test_runtime_catalog.py -v
python tests/Nikke.Compute.Tests/check_boss_conditions_api.py --source-data '<공개 dataRoot>' --source-roster '<고정 roster>' --dotnet '<dotnet>'
# 전환 전 기준 대조는 최초 stage A summary 경로를 --baseline 인자로 추가한다.
```

UI의 mock 잠정 `/api/runtime/combat-ranges?snapshotId=`와 다르다. **확정 경로는 위 두 combat-conditions GET**이다. Director가 이 wire와 커밋을 UI에 통지한 뒤 실제 UI 연결·독립 QA를 진행해야 한다. 원본에는 아직 profile catalog/code를 반영하지 않았으며 현재 사용자 실행 환경을 유지했다.

## B-FIX-2 / F-COND-Q-1 — 불명 사거리·속성 거부

QA `53d183d`의 `boss-distance-element-qa.ko.md`와 Director B-FIX-2 배정을 읽고 Backend `796eec3` 위에서 수정했다. 엔진/UI/QA 파일은 수정하지 않았다. 정상 prepare는 해당 필드를 공급하지만 hash-valid runtime 자체의 의미 검증에 누락 방어가 없었다. 특히 non-nullable int DTO 역직렬화가 누락 min을 0으로 채웠고, max·element 누락은 InvalidDataException이 API 오류 응답으로 변환되지 않았다.

수정은 `CombatProfileCatalog`의 DTO 생성 전 필수 키·JSON 타입·범위 검증이다. missing/null/wrong_type을 구분하고 명시 정수0은 보존한다. source/characters 컨테이너와 필수 metadata도 명시적으로 검사한다. skill/weapon replay와 compute는 요청마다 한 번 검증한 catalog를 스탯 계산 전에 준비하고 같은 profile을 엔진 입력에 전달한다. 손상된 profile로 피해 계산·replay 저장·compute job 생성/결과 저장을 진행하지 않는다.

**추가 오류 wire:** HTTP409 `{code:"combat_profile_invalid",message,characterId,field,reason}`. 예: `characterId:"5004",field:"combatProfiles.characters.5004.bonusRangeMin",reason:"missing"`. reason은 `missing/null/wrong_type/out_of_range/unsupported_value/id_mismatch/weapon_mismatch/hash_mismatch`. 전체 catalog/source 수준 오류의 characterId는 null이다. 두 combat-conditions GET, skill/weapon replay POST, compute POST에 공통이다. 자세한 계약은 [single-deck-compute-contract.ko.md](single-deck-compute-contract.ko.md)의 B-FIX-2 절이다. UI는 기존 message 표시를 유지할 수 있다.

성공 응답·조건 필드·compatibility 표시·엔진 버전·정상 fingerprint는 변경하지 않았다. 멤버 전체 누락은 기존400 `combat_member_profile_missing:<id>`, old catalog 자료 없음은 기존409 `combat_profile_catalog_missing`를 유지한다. 자료 없는 old catalog의 metadata 불필요 bool 경로도 유지하되, 존재하는 combatProfiles가 손상된 경우 bool 요청으로 우회하지 않는다.

### 수정 전 재현과 수정 후 검증

모든 실행은 Backend artifacts의 기존 공개 fixture 파일만 복사하고 **새 합성 계정 DB**를 작성했다. 원본 data/local 및 QA dataRoot를 읽거나 수정하지 않았다. 원천 roster만 별도 공개 저장소의 기존 고정 파일을 읽었다. 실제 사용자 EXE·계정·세션·캐시·설정·바로가기·5180/5181은 그대로이며 실행한 격리 API 자식 프로세스만 종료했다.

- 수정 전 `artifacts/boss-conditions/errors/83fa831763d0460294a3bf8cde1550c7/summary.json`: min/max/element 누락 각 hash-valid catalog에서 두 GET·skill/weapon replay 12응답 재현. min 누락은 200 및 잘못된 replay 저장, max/element 누락은500 빈 응답. compute job은 수정 전에는 실행하지 않았다.
- 수정 후 `artifacts/boss-conditions/errors/fd15633cda0e43e19ee84bbabe492068/summary.json`: **21 catalog × 5 API = 105/105 HTTP409**. 세 필드 각각 누락/null/문자열↔숫자/bool/object/array/소수 검사. code·characterId·field·reason 일치, snapshot 불변, replay/compute 파일 hash 불변, experiments=0·batch_runs=0, 공개 source hash 변경0. 매 사례 별도 dataRoot/임의 포트 사용. 스크립트 `tests/Nikke.Compute.Tests/check_combat_profile_errors.py`.
- Release 전체 빌드 경고0/오류0, **408/408 .NET tests** 통과(신규36, Sync148+Compute45+Core174+Analysis41, skip0). SG min0/RL0–0/SR25–45·45–100, 누락/null/타입/범위·컨테이너 진단 검사 포함. 로그 `artifacts/boss-conditions-bfix2-build.log`, `artifacts/boss-conditions-bfix2-tests.log`, TRX `artifacts/boss-conditions/bfix2-tests/`.
- 정상 API 회귀 `artifacts/boss-conditions/api/ed5f062a108c4552b2bdd23d3a019746/summary.json`: passed, 포트60410, source hash 변경0. 192명 집계·SG/RL0·SR예외·멤버 flag·저장/GET·혼용/잘못된 사용자 조건400 유지. 최초 stage A old bool replay 전체 멤버 결과·총피해 **1,586,529** 정확 일치. 새 거리35/Fire replay1,294,453. compute 세 조건 각N=1의 총피해 **1,508,042 / 1,304,192 / 1,847,281** 및 위 표의 fingerprint 모두 동일. 모드별 캐시 분리·약점별 OL 후보도 유지.

새 검사는 Backend 결함 회귀 근거이며 독립 QA 재수용을 대신하지 않는다. Python 원천 pipeline·엔진 산술은 수정하지 않았고 이 후속 작업에서 pipeline 검사는 재실행하지 않았다. package-lock.json SHA256은 위 보존 값과 동일하며 커밋에서 제외했다. 기존 커밋 보존, 원격 push/배포/새 Run/Dispatch/하위 워커 없음. Director에 커밋·wire·근거를 한 번 인계한 뒤 QA 재수용은 Director가 연결한다.

```powershell
python tests/Nikke.Compute.Tests/check_combat_profile_errors.py --source-data '<기존 격리 공개 fixture dataRoot>' --dotnet '<dotnet>'
# --before-fix는 수정 전 DLL에서 QA 증상을 재현하는 옵션이다. 수정 DLL에는 사용하지 않는다.
```
