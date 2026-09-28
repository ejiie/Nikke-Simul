# I-BE — client_f32 Backend 통합 결과 (2026-09-28)

Backend 통합·합성 API 검증 완료. UI 연결 및 Q-F32 단계 B 독립 수용·원본 배포는 별도 단계다. **실게임 정확성 수용 보고가 아니다.** 근거는 이 worktree의 Git 제외 `artifacts/client-f32-integration/` 및 `artifacts/client-f32-*.log`에 있다.

## 범위·기준선

시작 HEAD `f4ab2fc`(H-SRC), 기존 `d8be9d3`·제품 `40078d0` 보존. 시작 status는 미추적 root `package-lock.json`뿐이었다. AGENTS/README 및 Director 배정서와 선행 문서들을 UTF-8로 읽고 공통/I-BE 절만 수행했다. 엔진 `5ced15a`를 일반 merge **`f818f3b`**로 반영했고 충돌은 없었다. Core/Engine/Analysis 산술·UI·QA 파일은 직접 수정하지 않았다.

merge 직후 기존 Backend 회귀는 Compute **34/34**, Sync **81/81** 통과했다. 최초 전체 no-restore 빌드는 7개 프로젝트의 로컬 assets 부재로 실패했고, locked restore에서 audit 도구 2개의 기존 lock이 Data→Analysis 의존성을 누락한 NU1004가 확인됐다. `tools/Nikke.SyncAudit/packages.lock.json`, `tools/connection-audit/packages.lock.json`에 기존 프로젝트 의존성만 각 7줄 갱신했다. 외부 package 버전 변경은 없다. 엔진 산술을 수정해 빌드를 맞추지 않았다. 근거: `artifacts/client-f32-baseline-{build,restore,compute,sync}.log`.

## 연결 결과와 UI 계약

정식 wire 문서는 [single-deck-compute-contract.ko.md](single-deck-compute-contract.ko.md)의 **I-BE schema 3** 절이며 DTO는 `src/Nikke.Contracts/HitCalculation.cs`다.

- `/api/calculations/hit`: schema3, 새 두 rate, client 기본 및 과거 3정책, 선택 audit. 응답은 **최상위 `candidates`, `selectedCandidate`**를 갖는 DTO다. 이전 `comparison` 응답 봉투를 읽던 UI는 새 계약으로 바꿔야 한다.
- schema2는 원본을 보존하고 (statDamageRatio=1, defenceRatioRate=0)을 적용한 명시 변환이다. 응답과 JSON 저장에 originalInput·conversion을 남긴다. 소수 ATK/DEF/고정량이나 공격력 비율의 초과 정밀도를 임의 절삭하지 않는다. 숫자 원문 검사로 decimal/binary64 파싱의 반올림·underflow도 차단한다.
- `/hit/import`는 과거 다운로드 artifact의 schema2 입력과 새 응답을 새 ID로 검산·저장한다. 전체 과거 artifact를 sourceArtifact로 보존한다. GET `/hit/{id}`는 재계산 없이 당시 저장 내용을 반환한다.
- `rawRate10000`/`exactAmount`는 출력·저장 시 십진 **문자열**이다. 입력은 문자열 또는 JS 안전 정수 number만 허용한다. rate/amount 생략 시 exact에서 표시값을 만들고, 둘 다 있으면 일치를 검사한다. `exactEffectiveAttack`과 client 후보 `exactDamage`로 큰 정수를 정확히 표시한다. 큰 정수를 처리할 수 없는 과거 후보는 `unavailable`/null과 이유를 주고 0으로 만들지 않는다.
- 두 새 rate는 실험·미확정 항목이다. statDamageRatio=스킬 계수라는 추정을 사실로 쓰지 않았고 기본 1/0을 유지한다. 과거 정책은 기존 산술과 새 rate 미적용을 명시한다. H-SRC에서 보류한 break/parts·방어비율 매핑을 이번 연결에서 해결했다고 하지 않는다.

## snapshot·공개 스탯 조사

공격력 OL 비율은 원천 `RawValue`/`RawUnit:"Percent"`와 normalized 값의 일치를 확인한 뒤 `StatRateBuff.FromRaw`로 연결한다. 원천 raw가 없는 기존/가상 OL은 decimal normalized×10000이 정확한 정수일 때만 FromRaw로 전달한다. 잘못된 단위·불일치·초과 정밀도는 오류다. 영속 snapshot 자체를 고치지 않는다.

기존 공개 자료만 조사했다. calculation ID `5fec7706b9176fbbef92f04ada1ffab3730f9e058112ac0e4d9e84a5916d071f`; 원본 계정은 열지 않았다. 새 API fixture와 `source-stat-audit.json`의 근거:

| 경로 | 관찰·계산 경로 |
|---|---|
| stat_table.csv 레벨 | StatTable가 실제 읽는 1~1000레벨, 3직군 HP/ATK/6무기 DEF **24,000셀**, 소수 0 |
| 같은 CSV 호감도 | 실제 읽는 1~40레벨 HP/ATK/DEF **360셀**, 소수 0 |
| cube_base_table.json / collection.json._stat_table | native에 직접 더하는 HP/ATK/DEF 소수 0 |
| equip_stat_table.json | 원천 HP/ATK/DEF 소수 0. 기존 장비 경로는 부위별 강화/제조사 배율 적용 뒤 round |
| StatCalculator | 돌파 기여 floor+정수 flat, 콘솔 정수, 코어 기여 round(away). native에 새 round 추가 없음 |
| 스킬 고정 공격력 | 기존 엔진의 native_caster_flat_at_application은 client 경로에서 native 정수·원천 정수 rate로 long 부여량을 계산하고 checked 스택 곱 사용. Backend에서 새 rounding 추가 없음 |

CSV 전체에는 소수 234셀이 있으나 실제 레벨/호감도 스탯 영역에는 없다. 예: row11/col43=12.72는 현재 StatTable 입력 영역 밖이다. 워크시트 메모/효과 비율을 native 소수라고 오인하지 않았다. CSV 자체의 한글은 CP949이며 숫자 열은 기존 로더의 ASCII/Latin1 판독과 동일하다. 지시서/보고서는 UTF-8로 읽고 작성했다.

합성 5인 level400, 돌파/코어/호감/콘솔0, 큐브/소장품0, 앨리스 T10 head+원천 OL 1줄에서 실제 stats API 결과:

| ID | native ATK | native DEF |
|---|---:|---:|
| 5011 리타 | 75265 | 12962 |
| 5008 블랑 | 60212 | 16558 |
| 5004 앨리스 | 96332 | 11377 |
| 5009 누아르 | 90318 | 13006 |
| 5044 모더니아 | 90318 | 11333 |

이 DEF는 캐릭터 native다. 전투 적 DEF는 별도 `conditions.combat.enemyDefense=30925`다. 조사한 공개 입력에서는 소수 native/고정량을 발견하지 못했다는 한정 결론이며 모든 실제 계정/게임 데이터의 부재 증명은 아니다. 외부 소수 입력은 명확히 거부한다. 이후 catalog에 소수 native ATK가 생기면 stats 보고서에 `client_f32:fractional_native_attack_unsupported_without_rounding_rule`도 남긴다. 스킬 부여량의 실게임 정수화 검증은 별도다.

## compute와 역사 분리

새 준비 입력은 schema3/선택 정책/summary 버전을 명시한다. 버전은 `cpu-summary.2-client-f32`, rules는 `p03.skills.3-client-f32:p04.team.3-client-f32:p02.4-client-f32:native-stat-shared-buffs-v3-attack-i64:<policy>`다. 두 rate와 raw/exact를 포함한 전체 member·graph·conditions를 canonical fingerprint로 묶고 튜닝 키에도 연결한다.

`ExperimentRequest.hitOverrides`로 5인별 두 rate/runtimeAttackBuffs/attackFlatBuffs의 합성 실험을 연결했다. 원본 snapshot 변경 없이 준비 입력에만 적용한다. 다른 override 필드는 거부한다. 구 payload 복구는 버전/schema/정책 및 fingerprint를 재검사한다. 구 버전은 `engine_or_rules_version_changed`로 재개 거부하지만 당시 결과는 계속 조회할 수 있다. 현재 엔진의 명시 과거 정책 실험도 가능하다.

Backend 테스트는 과거 버전 메타데이터 fixture의 튜닝 cache를 만들어 새 입력에서 miss가 되는지, 구 결과 조회 유지, 새 batch에 구 fingerprint 쓰기 거부, 새 통계 N=1을 검사했다. 이 fixture는 저장·캐시 경계 검증이며 과거 바이너리 산술 oracle이 아니다. 실제 API에서도 client/과거 정책/수정 입력의 fingerprint 및 튜닝 키가 각각 다르고 개별 통계가 N=1이다. OL baseline 비교는 같은 rules·schema·summary·policy 및 hitOverrides를 요구한다. Analysis 구현은 변경하지 않았다.

## 검증 결과

최종 솔루션 Release 빌드 **경고0/오류0**, 10.82초. 최종 솔루션 테스트 **329/329 통과**, 실패0/skip0: Compute42 + Sync99 = **Backend141**, Core147, Analysis41. 기존 Backend115에서 신규26을 더한 개수이며 재실행 횟수를 합산하지 않았다. 근거 `artifacts/client-f32-final-build.log`, `artifacts/client-f32-final-tests.log`, `artifacts/client-f32-integration/tests-final/*.trx`. 테스트 보강 중 fixture가 RunSummary.InputFingerprint를 Fingerprint로 잘못 쓴 컴파일 오류1개를 수정했으며 최종 통과와 구분한다.

실제 격리 API 근거: `artifacts/client-f32-integration/api/5b3f730b2b784a108951d880d88609cb/summary.json`, `api.log`, `source-hashes.json`, `source-stat-audit.json`. 동적 포트 **54516**, 새 합성 DB·dataRoot, 12개 공개 파일 allowlist만 복사. 테스트 status **passed**:

- v3 두 rate → client150/과거100, 네 후보·선택 audit·모든 과거 정책 선택, v2→v3 변환, 옛 artifact import, 저장/GET 동일성.
- exactAmount 문자열 `9007199254740993`의 정확한 공격력 보존 및 과거 후보 unavailable. ATK/DEF/flat 소수·과정밀 rate·unsafe 정수 number·overflow **6개 HTTP400**. stats API raw numerator 문자열 확인.
- 5인/400/600프레임/DEF30925/crit off, maxWorkers1, 각 **정상 batch 1회**. client 기본, legacy 명시, 두 rate+raw/exact override 세 조건. 정상 결과 팀합=5인합, 통계 각 N=1, baseline 입력 혼합400, snapshot 불변.

| 조건 | 팀 피해 | 물리 입력 fingerprint |
|---|---:|---|
| client 기본 | 13,935,720 | `2ebac4a62e75a73cebffce5a67268c698a7ebf08489599427dfb92fbb841c857` |
| legacy_term_floor 명시 | 13,935,164 | `21d6f5e258b1054c1f11355554508115e8f0c5745b5e64b600a8c2bc1db5c11d` |
| 앨리스 실험 입력 | 15,746,904 | `d64c2cf0f93bf4f86d4b7d5c686fe522bc79cda87b55b48837f7886b80b2b3ad` |

세 튜닝 키 모두 다르고 cacheSource=miss였다. 기존 cpu-policy-3의 warmup1회+후보2회는 정상 표본에서 제외하며 각 배치 정상 N은 1이다. 이 짧은 10초 전투는 180초 replay·부하·성능 비교의 대체가 아니다. 새 rate의 물리적 의미나 실게임 일치 근거로 사용하지 않는다. 프로세스는 본인이 실행한 API만 종료했다.

재현(Backend 작업 경로, .NET10/Python 필요):

```powershell
$env:DOTNET_CLI_HOME = Join-Path $PWD '.tools/dotnet-home'
& '<dotnet>' restore Nikke.Simul.slnx --locked-mode --configfile nuget.config
& '<dotnet>' build Nikke.Simul.slnx -c Release --no-restore
& '<dotnet>' test Nikke.Simul.slnx -c Release --no-build --no-restore --logger trx --results-directory artifacts/client-f32-integration/recheck
python tests/Nikke.Compute.Tests/check_client_f32_api.py --source-data '<기존 공개 catalog/calculation/runtime 자료 경로>' --dotnet '<dotnet>'
```

## 미수용·인계 경계

UI 실제 연결/브라우저, 독립 Q-F32 단계 B, 실측18점·게임 관측·SW·GPU·장시간1천/1만/5만 실행은 하지 않았다. schema2의 이미 저장된 파일들을 자동 일괄 변환하지 않으며 명시 import를 제공한다. 큰 정수의 audit/잔차/전투 합계는 기존 double 표시 한계를 유지하고 정확한 단일 히트 정수만 별도 문자열로 보존한다. UI는 새 최상위 응답/문자열 exact/네 후보/unavailable/schema3 계약에 맞게 연결해야 한다.

원본 계정 DB·세션·캐시 열기/복제/변경 없음, 공개 파일12개 원본 hash 변경0. root `package-lock.json` SHA256 `2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767` 보존·커밋제외. 원본 실제 사용 경로는 `C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe`이고 이 작업에서는 빌드·배포·실행하지 않았다. EXE/바로가기/5180/5181 서버, 다른 worktree, 원격 변경 없음. 새 Run/Dispatch/worker/worker_done 없음.

본 문서와 계약을 담은 확정 커밋을 Director 터미널 재조회 후 **한 번** 전달한다. UI·QA에 직접 보내지 않는다. Director 수신은 독립 QA나 원본 배포 완료를 뜻하지 않는다.
