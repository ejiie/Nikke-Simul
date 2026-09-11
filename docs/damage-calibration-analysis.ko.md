# S3 피해 로그 독립 분석 — 2026-09-11

기준: `a0738accb16500e52621811fac0dac7259cb7f76`. 시작 HEAD `3583cabb0dda10c7cb4686fbcbf69e55003a9235`에서 `git merge --ff-only a0738accb16500e52621811fac0dac7259cb7f76` 성공. 지시 문서 `Director/docs/integrated-validation-dispatch.ko.md`를 UTF-8로 끝까지 읽고 공통/S3 절을 수행했다. README, P04, 엔진/API/UI 계약과 실제 DTO·피해 계산·발사 모델·UI adapter를 대조했다. 상위 및 저장소에서 적용 AGENTS.md는 발견되지 않았다.

분석 도구·전용 테스트 결과 커밋: **`c95eeff`** (`feat(analysis): add independent S3 damage log calibration checks`). 이 보고서는 후속 문서 커밋이다. 제품 엔진/API/UI·다른 작업공간·계정·스냅샷·과거 artifacts를 편집하지 않았다. 새 워커, push, 배포, 자동 보정, 추천, MC는 수행하지 않았다.

## 산출물과 입력 계약

- `tools/damage-calibration/analyze.py`: 표준 라이브러리만 사용하는 읽기 전용 CLI. 기본 출력은 자기 작업공간 `artifacts/s3/<UTC>-<uuid>/analysis.json`; 매 실행 새 폴더를 만들며 외부 작업공간 출력 경로를 거부한다.
- `tools/damage-calibration/test_analyze.py`: 별도의 합성 기대값과 손상 입력 테스트 18개.
- native `SkillReplayResult.damageLog`, 실제 `SavedSkillReplay.result.damageLog`, API export `{exportSchemaVersion:1, collectionStatus, replay:{result:{damageLog}}}` 세 구조를 명시적으로 지원한다. `res.hits`를 가정하지 않는다. 통합 기준 UI adapter는 `res.hits`를 기대하는 문제가 있으며 수정 소유자는 U3다.
- API wrapper 메타데이터는 입력 ID·규칙·snapshot 식별자를 그대로 보고서에 보존한다. 입력 원문 hash와 도구 hash, 실행 HEAD도 기록한다. 입력은 재저장하지 않는다. 개인정보를 포함할 수 있는 분석 출력은 ignored artifacts에만 남는다.
- `schemaVersion != 1`은 `unsupported_version`; export 미지원 버전은 `invalid_input`. 미수집 null/과거 누락, complete 0행, 명시적 truncated, 완전성 필드 불명확, 행 수/누적/합계 불일치를 구별한다. 잘린 로그의 부분 집계는 보고하되 정상 완료로 반환하지 않는다. CLI 종료 0은 수집 로그의 내부 검사가 통과했다는 뜻이며 게임 정확도 판정이 아니다. 미수집·잘림·미지원·손상은 종료 2다.
- 숫자 kind `2=NormalHit, 3=DirectSkillHit, 4=AdditionalHit`를 사용한다. non-null shotId distinct는 원인 발사 참조 수다. 직접 스킬의 null shotId는 새 발사가 아니며 추가타/펠릿이 동일 shotId를 공유해도 발사를 중복 집계하지 않는다. `normalShotsWithHits`는 피해 로그에 나타난 평타 발사만 세므로 `memberShots`와 별도 표시한다. 명중 없는 발사는 피해 로그만으로 복원할 수 없다. 명중/발사 비율을 명중률이라고 부르지 않는다.
- chargeRatioRaw(10000=100%), nullable fullCharge/actual/effectiveChargeFrames, hit.crit/core/fullBurst와 ownBurstEffectActive를 서로 독립인 조건으로 묶는다. 자체 버스트 구간을 팀 구간으로 만들어내지 않는다.

## 관측값 매칭과 오차

관측 JSON 형식 예시(아래는 합성 입력이며 실측 파일이 아님):

```json
{"schemaVersion":1,"evidence":"synthetic_test","entries":[{"hitId":80,"damage":1000}]}
```

hitId는 **동일 replay에서 사람이 명시적으로 연결한 ID**로 사용한다. 서로 다른 실행의 trace ID나 영상에서 자동 추정한 ID를 그대로 매칭하지 않는다. ID 없이 연결하려면 frame/source/target/kind/effect/pelletIndex 여섯 필드를 모두 제공해야 하며 완전 일치만 허용한다. ID와 함께 조건 필드를 제공하면 그 조건도 일치해야 한다. 동일 frame의 복수 후보나 관측 중복은 ambiguous로 분리하며 최근접 시각/행 순서로 임의 짝짓지 않는다. 다른 frame rate의 실측을 사용할 때는 분석 전에 시간 기준과 대상을 명시적으로 정렬해야 한다.

매칭된 수치 쌍에 대해 signedError=simulation−observation, absoluteError=절댓값, relativeError=signedError/observation, absoluteRelativeError=절대 오차/observation을 계산한다. 상대 오차는 비율 단위이며 ×100해야 %다. 평균은 실제 매칭 수치 쌍만 사용한다. 상대 평균에서는 0 관측을 제외하고 해당 건수를 따로 기록한다.

관측 없음은 `not_provided`와 null 평균이다. 관측 파일의 빈 배열도 평균 null이다. 미매칭 관측, 피해값 null/누락, 애매한 매칭, 수치 관측이 없는 시뮬레이션 hitId를 각각 보고한다. 관측 0은 절대 오차를 계산하지만 분모 0의 상대 오차는 null이다. 양쪽 0의 정확 일치도 상대 오차를 0으로 만들지 않는다. 합성 테스트에는 315 대 300의 절대 오차 15/상대 오차 0.05, 315 대 315의 정확 일치, 0 관측·미매칭·누락·중복이 포함된다.

## 독립 피해 검산의 범위

제품 C# 계산기를 호출하거나 calculation.damage를 정답으로 복사하지 않는다. 기록된 HitContext에서 공격력 원값·동일 비율 버프 그룹별 반올림·고정 버프·방어력·차지·가산 crit/core/fullBurst/distance·B3/B4/B5를 별도의 Python 산술로 계산한다. `legacy_term_floor`, `final_round_even`, `nested_floor`를 구별한다. 비풀차지는 기존 피해 배율 1을 유지한다. 자체 버스트는 그룹 조건이며 공증 등 실제 피해 영향은 기록된 HitContext를 통해 계산한다.

검산 대상은 **로그에 기록된 입력의 산술 일관성**이다. HitContext 생성, 버프 선택/수명, 게임 원천 값, 명중/크리 난수의 정확성은 이 계산으로 독립 입증되지 않는다. native result에는 hitRulesVersion이 없어 고정 계약 p02.3 가정과 그 출처를 보고서에 명시한다. SavedSkillReplay의 hitRulesVersion이 다르면 `formula_unavailable`로 표시하고 현재 식으로 덮어 계산하지 않는다. IEEE double의 경계 반올림까지 모든 게임 입력에서 일치함을 주장하지 않는다.

## 확정 예제와 새 실행 결과

읽기 전용 원본:
`C:/Users/user/orca/workspaces/Nikke-Simul/시뮬레이션-엔진-담당/artifacts/e2/79301e0197c84a8195b553adad062de9/engine-example-c7c29fe7eb3a4fcfa3c218c7d02d36c9/`

manifest에는 자체 hash가 없으므로 `docs/damage-log-engine-contract.ko.md`에 확정된 아래 SHA-256과 세 파일을 비교했다. manifest의 evidence/gameVerified, 기간·행 수·피해·마지막 명중·풀버스트 수·규칙을 result와 대조했다. hash 일치 및 manifest 대조 통과.

| 파일 | SHA-256 |
|---|---|
| input.json | `e14a48955bdbc42f15b6e361ef2ab54a5dc66b5c3df46484346b5a3d2cf40f9b` |
| result.json | `461f3e0e9a2038c3891753eb34635f7ed48c5c3dd661287928a305889f8e7114` |
| manifest.json | `dce19030539f74bf0f80b275d5c82befc9956567b7ec87737dca87fe83baf184` |

통합 기준에서 **EngineIntegrationExampleTests를 새로 실행: 2 통과 / 실패 0 / skip 0, 테스트 기간 22초**, 관련 Core/Engine/test Release 빌드 성공. 새 예제 `artifacts/s3/engine-a59a2f4c30db4a55994bebb5ff2958b7/engine-example-b930d3c5bbcd452894ed33b3220084fc/`의 세 파일도 위 hash와 모두 일치했다. 전체 C# 회귀 수를 인용하거나 전체 solution/API/UI 검증을 수행했다고 주장하지 않는다.

실제 실행한 두 테스트에는 native 입력 JSON 복원→실행 결과/RNG 재현, 로그 ON/OFF 결과·발사·잔탄·팀 타임라인·난수 소비 불변, 미수집과 수집 0행 구분이 포함된다. 원본을 읽은 분석과 새로 생성한 결과 분석 모두 종료 0, 분석 issues 0이다. **두 결과 모두 합성 입력의 실제 엔진 실행이며 실게임 관측이 아니다.**

선택 캐릭터 5004: 10800프레임(180초), 183명중/183개 발사 참조, memberShots=183, shotless=0, 총 피해 **172399**. 183행 전부 Python 재계산과 로그/선택 calculation.damage가 일치했다. 누적 피해·로그 총합·member 총합·9개 팀 풀버스트 구간 합계 일치. 마지막 명중 10776프레임(179.6초), 종료까지 24프레임이다.

실제 예제의 조건별 검산(모두 풀차지 raw=10000, core=true):

| 자체 효과 | 팀 풀버스트 | crit | 명중 | 발당 피해 | 합계 |
|---|---|---|---:|---:|---:|
| ON | OFF | OFF | 4 | 980 | 3920 |
| ON | OFF | ON | 1 | 1225 | 1225 |
| ON | ON | OFF | 55 | 1225 | 67375 |
| ON | ON | ON | 16 | 1470 | 23520 |
| OFF | OFF | OFF | 57 | 630 | 35910 |
| OFF | OFF | ON | 15 | 787 | 11805 |
| OFF | ON | OFF | 28 | 787 | 22036 |
| OFF | ON | ON | 7 | 944 | 6608 |

이 예제에 core OFF/부분 차지/shotless/추가타가 있다고 주장하지 않는다. 해당 차이는 전용 합성 테스트로 검증했다. 관측 파일이 없으므로 관측 평균 절대/상대 오차는 null이고 실게임 정확도는 미판정이다.

## 발사·차지·재장전·마지막 사이클

183개 평타 발사의 인접 간격 182개를 분석했다. 간격별 건수: 31f=39, 32f=21, 40f=2, 61f=58, 62f=32, 91f=10, 92f=2, 97f=1, 121f=9, 122f=8. 각 행에 다음 발사의 actual/effectiveChargeFrames 및 간격−다음 실제 차지 프레임을 보존했다. 유효 차지 목표와 실제 누적 차지를 같은 값으로 가정하지 않는다.

탄 0 이후 다음 발사 간격 30건: 91f=10, 92f=2, 97f=1, 121f=9, 122f=8. 그 간격에서 다음 실제 차지를 뺀 잔여는 61f 또는 62f다. 이 잔여는 재장전만의 실측 시간이 아니며 재클릭/상태 전이 등이 포함될 수 있다. 탄 증가도 별도 필드로 기록한다. 명중 로그 기반이므로 명중 누락·무기 모드 전환이 있는 일반 결과에서는 연속 발사 전체라고 단정하지 않는다.

예제는 combat.trace=false이며 connection.timeline에 재장전 완료 이벤트가 없다. timelineTruncated=false여도 미수집 trace가 완전한 재장전 이벤트 기록을 뜻하지 않는다. 따라서 재장전 완료 정확 시각, 다음 차지 시작 정확 시각, 종료 후 예상 다음 발사를 만들어내지 않는다. 로그에서 측정 가능한 발사 간격과 발사 당시 누적 차지까지만 보고한다.

마지막 팀 풀버스트는 cycle 9, caster=5004, **9668≤frame<10268**, 계획 종료도 10268. 선택 캐릭터 13명중·16170 피해로 memberDamage와 일치한다. 그 이후 **8명중·5040 피해**가 기록됐다. 전투 종료 상태는 step=1, gaugeRaw=0, waitingReason=`cooldown_stage_1`. 마지막 사이클 이후 피해를 버리거나 전투 종료를 풀버스트 종료로 간주하지 않았다.

## 재현 명령과 증거

자기 작업공간 PowerShell에서 실행한다. Python과 .NET 경로는 지시된 고정 실행 파일이다.

```powershell
$taskPython = 'C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $taskPython tools/damage-calibration/test_analyze.py
# 최종 18 통과, 실패 0

$taskE2 = 'C:/Users/user/orca/workspaces/Nikke-Simul/시뮬레이션-엔진-담당/artifacts/e2/79301e0197c84a8195b553adad062de9/engine-example-c7c29fe7eb3a4fcfa3c218c7d02d36c9/result.json'
& $taskPython tools/damage-calibration/analyze.py $taskE2 --verify-e2
# 세 hash/manifest 대조 및 분석 종료 0

$env:DOTNET_CLI_HOME = Join-Path $PWD '.tools/dotnet-home'
$env:NUGET_PACKAGES = 'C:/Users/user/Documents/GitHub/Nikke-Simul/.tools/nuget-packages'
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$taskS3Run = Join-Path $PWD ('artifacts/s3/engine-' + [guid]::NewGuid().ToString('N'))
$env:NIKKE_E2_EXAMPLE_ROOT = $taskS3Run
& 'C:/Users/user/Documents/GitHub/Nikke-Simul/.tools/dotnet/dotnet.exe' test tests/Nikke.Core.Tests/Nikke.Core.Tests.csproj -c Release --filter FullyQualifiedName~EngineIntegrationExampleTests -p:RestoreLockedMode=true --logger 'trx;LogFileName=s3-engine.trx' --results-directory $taskS3Run
# 2 통과, 실패/skip 0. 실제 실행 로그도 해당 출력 폴더 run.log로 보존.
```

Director의 확정 계정 복사본 API 결과에 적용할 CLI(입력 파일 준비 후 실행할 명령이며 이 API 호출 자체는 이번 미실행):

```powershell
& $taskPython tools/damage-calibration/analyze.py '<SavedSkillReplay 또는 damage-log export JSON 경로>'
& $taskPython tools/damage-calibration/analyze.py '<결과 JSON 경로>' --observations '<관측 JSON 경로>'
```

| 이번 증거(자기 작업공간 상대 경로) | 실제 결과 / SHA-256 |
|---|---|
| `artifacts/s3/tests-1452d6df418144449e6305ae145ed351/tests.log` | 18 통과; `d2670dc39ec29967a8f2c3bbfe153dd596e3112788ce59fbacf438be828e6b8d` |
| `artifacts/s3/20260911T031108Z-30d34238fc964dff8ecfe78c55dd6695/analysis.json` | 확정 E2 분석; `4cce537f1e9fa759376c300f909bc875518a6f99bd22193baa3d7fd0daa1a677` |
| `artifacts/s3/engine-a59a2f4c30db4a55994bebb5ff2958b7/s3-engine.trx` | 새 엔진 테스트 2 통과; `cf5de4e15429e85e4f14feadc30f3e0e04d5153a89e2c6717116fbad44d19436` |
| `artifacts/s3/20260911T031128Z-c0047584988f4b389d2162b226fba234/analysis.json` | 새 엔진 출력의 세 hash 재검증 및 분석 종료 0 |

실패 기록도 보존: `artifacts/s3/tests-5ec0afcb560c48859152460f1b2b8b8c/tests.log`. 18개 중 CLI 테스트 1개가 CP949 부모 프로세스/UTF-8 자식 출력 차이로 오류였고, JSON 콘솔 출력을 ASCII escape로 바꾼 뒤 위 최종 18개가 통과했다. 초기 16개 통과 및 초기 예제 분석도 있었으나 최종 근거와 구별했다. `git diff --check`/staged 검사 통과(LF→CRLF 안내만).

기존 미추적 package-lock.json의 작업 전/후 SHA-256은 `2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767`로 같다. 커밋 대상에서 제외했다.

## 미완료와 후속 수용 조건

- 실제 계정 복사본의 API 생성/저장/조회·CSV·브라우저 종단 검증은 Director/Q3/U3 담당이다. 이번 wrapper 테스트는 합성 구조이며 실제 API 실행을 가장하지 않는다. 확정 API JSON 경로를 전달받으면 동일 CLI로 검산할 수 있다.
- U3 최종 제품 수정 커밋은 이번 브랜치에 반영하지 않았다. UI 수용 여부나 제품 전체 통합 통과는 판정하지 않는다.
- 실게임 관측 데이터가 없어 피해·발사·차지·재장전·버스트 시점 오차는 미검증이다. 관측 부재는 오차 0이 아니다. 다중 후보 매칭 해결과 관측 시간 기준 정렬도 관측 제공 후 필요하다.
- 196000 충전식과 세 전이 지연을 변경하지 않았다. 전체 기존 C# 회귀는 Director 소유이며 이번 실행은 예제 테스트 2개로 한정한다.
- 현재 분석은 입력 결과와 기록된 산식의 일관성 확인이다. 엔진 자동 보정, 실전 추천, 대규모 MC, 실게임 검증 완료의 근거로 사용하지 않는다.

## S3 종료 프레임 경계 결함 수정 — 2026-09-11 후속

기준 `a16cb9e14f186d2fece7c81551c29816e04104eb`. 시작 `a17e079285171def7ed81e58585f74238980758a`의 미커밋 상태는 기존 미추적 package-lock.json뿐이었다. 조상 관계 확인 후 `git merge --ff-only a16cb9e14f186d2fece7c81551c29816e04104eb` 성공. package-lock.json의 전후 hash는 위 기록과 동일하다. 이 통합본에는 UI 99dfa2f가 포함되며 실제 브라우저 수용 통과는 사용자/Director 전달 결과다. 앞 절의 U3 미반영·실제 저장 로그 입력 미제공 상태는 이 후속 기록으로 갱신한다. 이번 작업에서 브라우저나 API 서버를 재실행하지 않았다.

결함: `src/Nikke.Engine/Skills/SkillReplay.cs:615`의 전투 프레임 루프는 `for (frame=1; frame<=C.DurationFrames; frame++)`다. S3 검증기가 피해 행에 `frame < 0 || frame >= duration`을 사용하여 하한 0을 허용하고 마지막 프레임을 거부했다. **피해 로그 검증 범위는 `1 <= frame <= durationFrames`**로 수정했다. 전투 시작 관리 이벤트의 frame=0과 피해 행의 프레임 경계를 구별한다. 팀 풀버스트 효과 구간의 배타적 종료 조건을 바꾸는 수정은 아니다.

변경은 `tools/damage-calibration/analyze.py`의 경계 조건/설명, 전용 테스트의 네 경계 사례, 본 문서뿐이다. 로그 필터링·행 삭제·피해/엔진 결과 재작성은 없다. 엔진/UI/Backend/Director·원본 데이터는 편집하지 않았다.

경계 회귀는 각각 0 거부, 1 허용, duration(10800) 허용, duration+1(10801) 거부를 확인하며 모든 경우에 입력 전체 불변·행 수·피해량·마지막 프레임 보존도 검사한다. 수정 전에는 새 테스트 중 0과 duration 두 사례가 실패했고 기존 18개 및 나머지 두 경계 사례는 통과했다. 수정 후 **22개 통과, 실패 0**(기존 18개 + 경계 4개).

실제 저장 로그 읽기 전용 입력:
`C:/Users/user/orca/workspaces/Nikke-Simul/Director/artifacts/director/live-1ef80dd69d7a41669c609180d520ec85/ui-response.json`.
입력 SHA-256 `9fa27ddbacd407f27764dcfa558556f1daa1339df6077a74047730f2a1780309`는 수정 전 분석 provenance, 수정 후 분석 provenance, 재검산 후 원본 파일에서 모두 같다. Director의 기존 실패 출력 `artifacts/s3/20260911T045358Z-30e6a72680e54fd38a6ad54b176ce0ea/analysis.json`도 읽기 전용 대조했으며 유일 issue가 outside_duration임을 확인했다.

| 실제 저장 로그 재검산 | 수정 전 | 수정 후 |
|---|---|---|
| 입력 형태 / 수집 상태 | saved_skill_replay / complete | 동일 |
| 명중 수 / 총 피해 | 135 / 153638004 | 동일, 전 행 보존 |
| duration / 마지막 frame / tailFrames | 10800 / 10800 / 0 | 동일 |
| issues / CLI 종료 코드 | outside_duration / 2 | 빈 배열 / 0 |
| 독립 피해 산술 검사 | 135행 | 135행 일치 |
| 관측 비교 | not_provided, 평균 절대/상대 오차 null | 동일 |

실행 명령(자기 작업공간, 지시된 Python 사용):

```powershell
$taskPython = 'C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $taskPython tools/damage-calibration/test_analyze.py
& $taskPython tools/damage-calibration/analyze.py 'C:/Users/user/orca/workspaces/Nikke-Simul/Director/artifacts/director/live-1ef80dd69d7a41669c609180d520ec85/ui-response.json'
git diff --check
```

이번 증거는 모두 본인 작업공간의 새 artifacts 경로에 생성했다. 테스트 stdout/stderr는 Python subprocess로 tests.log에 보존했다.

- 수정 전 실제 로그 재현: `artifacts/s3/20260911T045845Z-51262e9851b54cd0a4c5ec38b47961e2/analysis.json` (종료 2).
- 수정 전 경계 회귀: `artifacts/s3/boundary-before-ae92038b35ba42f6a989e9c1b928dce2/tests.log` (20 통과 / 2 실패).
- 최종 회귀: `artifacts/s3/boundary-after-a052268a72b9484383d2e63f9ae9b519/tests.log` (22 통과 / 실패 0).
- 수정 후 실제 로그: `artifacts/s3/20260911T045932Z-6e504697137e4f44a4fc4aeeed4ba641/analysis.json` (종료 0), SHA-256 `ceeb2445eb3ba6e30d379ee7bcbf8d8973e2a288a4aaa70b13e54168f708c26a`.
- `git diff --check` 통과(LF→CRLF 안내만).

이 경계 결함의 수정·회귀·지정 로그 재검산은 완료했다. 제품 코드 수정이나 전체 C# 회귀는 범위 밖으로 실행하지 않았다. 실게임 관측 데이터는 여전히 미제공이므로 실제 게임 정확도·관측 오차 검증 완료를 주장하지 않는다.
