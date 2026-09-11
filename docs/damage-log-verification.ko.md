# Q3 통합본 독립 검수

2026-09-11. **a0738ac는 통합 수용 실패다.** 엔진 및 저장소 회귀는 통과했으나 실제 wire 형식을 전달한 UI 경계 검사 25개 중 19개가 실패했다. 제품 코드는 수정하지 않았다. UI 수정 고정 커밋이 아직 이번 검수에 제공되지 않았으므로 재현 도구와 결과를 먼저 반환한다.

## 기준과 보존

- 시작 브랜치 `검수`, HEAD `3583cabb0dda10c7cb4686fbcbf69e55003a9235`.
- Director의 `docs/integrated-validation-dispatch.ko.md`를 UTF-8로 끝까지 읽고 공통 및 Q3 절을 수행했다. README와 P04·엔진·API·UI 계약 문서를 읽었다. 현재/상위 경로 및 추적 파일에서 별도 AGENTS.md는 발견되지 않았다.
- 조상 관계 확인 후 `git merge --ff-only a0738accb16500e52621811fac0dac7259cb7f76` 성공. 검사 대상 제품은 이 고정 커밋이다.
- 기존 untracked `package-lock.json`의 실행 전후 SHA-256: `2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767`. 커밋에서 제외했다.
- 계정·스냅샷·과거 artifacts를 읽거나 변경하지 않았다. 다른 작업공간은 지시서 읽기만 수행했다. 다른 브랜치 병합, 강제 reset/stash/checkout, 워커 생성, push, 배포 없음.
- 변경 소유 범위: `tests/q3/{check_ui_contract.mjs,verify_log.py,test_verify_log.py}` 및 본 문서. 기존 UI 검증기의 고정 출력 경로는 실행하지 않고 Q3 전용 UUID 출력을 사용했다.

## 실제 실행 결과

공통 증거 루트: `artifacts/q3/68467747323d47ec9e3f1990d2d2466c/` (ignored, 이 검수 작업공간). 이전 결과를 이번 통과로 인용하지 않았다.

| 실행 | 실제 결과 | 증거/의미 |
|---|---|---|
| Core/Engine Release 테스트 | 113 통과, 0 실패, 0 skip, 종료 0 | `core.log`, `core.trx`. 합성 입력으로 엔진 실제 실행 |
| Sync/Data/Storage Release 테스트 | 81 통과, 0 실패, 0 skip, 종료 0 | `sync.log`, `sync.trx`. 저장·복원·외부 DTO/내보내기 회귀 |
| Q3 독립 로그 검산 | complete, 종료 0 | `log-0617d6bdbca149ec99a06752ec2e4141/summary.json` |
| Q3 검산기 자체 테스트 | 5 테스트 통과, 종료 0 | `audit-tests.log`. 손상 입력 14종 subtest 포함 |
| 기존 B2 export assertion 자체 테스트 | 6 통과, 종료 0 | `export-assertion-tests.log`. 실제 HTTP 실행 아님 |
| 최종 Q3 UI 경계 수용 | 6 통과 / 19 실패, 종료 1 | `ui-d3ff559b-82ed-454d-8eb2-ca9cc4785fb9/summary.json` |
| Node 구문 검사 / git diff --check | 종료 0 | 제품 diff 없음 확인 |

새 엔진 예제: `engine-example-7a70bb62fac545d0bdf4ea731b5ebffb/{input,result,manifest}.json`. 실제 이번 Core 테스트가 생성했다. 10800프레임, 피해 172399, 183명중/183개 피해 관련 고유 발사, 마지막 명중 10776프레임. 독립 합계·누적·선택 멤버 총피해·ID·초 변환·계산 결과·정책이 일치하고 자체 효과/팀 풀버스트 네 조합을 확인했다. 앨리스형 충전 이벤트가 존재하며 모두 196000이다. 과거 E2와 파일 hash가 같지만 이번 실행 TRX와 생성 경로로 별도 입증한다.

예제 manifest의 `engineBaseCommit=908047f`/`backendComparedCommit=bf19679`는 생성 테스트에 고정된 과거 설명 필드다. **이번 실행 기준은 a0738ac**이며 UI summary에 실제 HEAD를 기록했다. manifest만으로 실행 커밋을 판정하지 않는다.

## 검수 범위별 판정

| 항목 | 이번 근거 및 판정 |
|---|---|
| 180초·합계·shot/hit | 독립 Node/Python 감사와 DamageLogTests 통과. 펠릿·추가타는 동일 원인 발사, 직접 스킬 shotId=null이라는 합성 테스트 포함. Python의 shots는 피해와 연결된 고유 발사 수이며 전체 발수/명중률과 동일시하지 않음 |
| ON/OFF·trace 제한·난수 | 이번 실행의 DamageLogTests, BurstTacticTests, EngineIntegrationExampleTests 통과. 피해·발수·잔탄·난수 소비·팀 타임라인 비교 |
| null/0/미수집·구버전 | 엔진 JSON·저장소/내보내기 회귀와 Q3 감사 통과. UI의 실제 complete zero는 미수집으로 잘못 분류 |
| 자체 버스트 vs 팀 풀버스트 | 이번 엔진 회귀의 독립 네 조합 및 만료 경계 통과. Q3 감사도 실제 결과의 네 조합 확인. UI는 실제 로그를 읽지 못해 필드 수용 검사 실패 |
| 허용·순위·III 교대·첫 시전자·대체/대기 | 이번 BurstTacticTests 통과. 제외자의 게이지 기여/시전 제외, 순환 밖 대체, 우선 슬롯 전진, 만료 시 유지 포함 |
| stale·저장 복원 | 이번 Sync 테스트 통과. UI stale ID 진단은 통과하나 부분집합/null 복원 및 늦은 GET 응답의 최신 상태 보존 실패 |
| 기존 196000 및 세 전이 지연 | 이번 TeamBurstTests/BurstTacticTests 통과. 자동/수동 56000×35000/10000, 기본 1~10/1~10/28, 원천 max 18/24/36 합성 검증 포함. 게임 실측/정책 변경 아님 |
| API DTO ↔ UI | 실제 생성 native result를 계약상의 SavedSkillReplay/내보내기 envelope로 감싼 **합성 경계 입력**. 실제 API 요청/응답 수집이라고 주장하지 않음 |

Q3 검산기는 native result, SavedSkillReplay, damage-log envelope를 받는다. 누락/null은 damage=null의 not_collected, 실제 0은 complete_zero, 미지원 schema/잘림은 별도 상태로 반환하고 CLI가 종료 1로 완전 수용을 거부한다. 게임 산식 정답이나 관측 오차를 추정하지 않는다. 14종 변형은 중복 hitId, 잘못된 source, 행 누락, 초/프레임 오류, 누적/요약/멤버 합계 오류, 추가타의 새 shot, 직접 스킬 shot, null→false 손실, 계산 결과 불일치, 문자열 kind, NaN을 탐지한다.

## 수용 실패 및 수정본 재실행 항목

아래 번호는 결함 묶음이며 19개 실패 테스트가 19개의 독립 원인이라는 의미는 아니다. 각 실제/기대값은 최종 UI summary에 보존했다.

1. **실행 요청 누락/혼용** (`app.js` submit callback): API에 전달되는 실제 callback 요청에서 `conditions.damageLog`가 undefined. 명시 tactic과 함께 legacy `burst3Rotation` 3개가 전송된다. next_ready/wait_preferred 두 경우 모두 수용 실패. 엔진 회귀는 이 혼용을 거부함을 확인한다. 선택 대상 로그 포함 및 legacy 빈 배열/기본 정책이 필요하다.
2. **로그 스키마 불일치** (`damage-log-adapter.js` fetchDamageLog): `res.replay.result.damageLog.entries`, 직접 `saved.result.damageLog`가 모두 uncollected. numeric kind/source/chargeRatioRaw/hit flags를 검사하는 테스트는 입력 행 도달 단계에서 실패하므로 그 이후 매핑 항목을 통과로 세지 않는다.
3. **상태 손실**: complete zero → uncollected, truncated 플래그 소실, schema 999 → uncollected, HTTP 500 모사 오류 → uncollected. legacy/null과 다른 대상의 미수집 테스트는 통과하지만 모든 입력을 미수집 처리하는 현 결함 때문에 이 둘만으로 대상 선택 구현이 정확하다고 결론 내리지 않는다.
4. **전술 의미 손실**: III 순환 순서/부분집합/우선순위 첫 원소가 아닌 단일 순환이 원래 우선순위 전체 또는 첫 원소로 변경된다. `firstBurst3CharacterId=null`이 5004로 변경된다. priority_only+다른 첫 시전자를 진단/거부하지 않고 5004로 대체한다. 일반 DTO 왕복/내부 wait 정책 보존은 통과.
5. **저장 복원 손실**: 서버 조회 helper에 전달한 유효 부분집합 `[5044]`, first=null이 `[5004]`, first=5004로 변한다. 실제 HTTP/DB가 아니라 실제 helper에 합성 GET 응답을 전달한 재현이다.
6. **비동기 복원 경쟁** (`burst-tactics.js`): 실제 manager에서 지연 Promise로 이전 GET을 보류하고 계정 B 전환/새 firstCaster=5044 편집 후 해제하면 5004로 덮어쓴다. 두 독립 수용 테스트 실패. DOM 렌더링은 null container로 생략했으며 상태 전이만 실행했다.
7. **직접 스킬만 있는 로그 발수 오표시** (`damage-log.js`): 실제 `uniqueShots` 식을 추출해 shotId=null 2행에 실행하면 0발 대신 2발. 이 테스트는 현재 식의 위치에 의존하므로 구조 변경 때 harness를 조정해야 한다.

코드 읽기로 추가 확인한 제한: JSON 다운로드는 `api`로 파싱한 값을 JSON.stringify하여 바이트 원문을 보존하지 않으며, export 오류 시 사설 fallback으로 바뀐다. 실제 다운로드/메타데이터·원문 보존 및 자체 구간 렌더링은 Director의 API/브라우저 검사에서 추가 확인해야 한다. 이 항목을 이번 동적 재현 통과/실패 개수에 넣지 않았다.

수정본 고정 후 위 25개를 **전부** 재실행한다. 이미 통과한 6개도 유지돼야 하며 실패를 예상 실패로 바꾸거나 예외를 삼켜 성공시키면 안 된다. adapter의 상태 명칭이 바뀌면 의미를 유지하여 assertion을 조정한다. submit callback/uniqueShots 구조 변경은 harness 위치를 갱신하되 요청 생성식을 테스트에 재구현하지 않는다. 실제 UI에서 다른 대상 선택, null 차지 필드/직접 스킬·추가타 표시, 계산 terms/buffs 원문, 다운로드 JSON/CSV, 편성/계정/스냅샷 변경·새로고침은 브라우저로 추가 확인한다.

## 재현 명령

저장소 루트 PowerShell. 아래는 이번 실행 명령과 같은 테스트·환경이며 `$taskQ3Run`은 매번 새 UUID를 사용한다. stdout/stderr를 각 실행의 log로 보존했다. Core 종료 후 Sync를 실행해 같은 빌드 산출물의 동시 쓰기를 피한다.

```powershell
$taskQ3Dotnet = 'C:/Users/user/Documents/GitHub/Nikke-Simul/.tools/dotnet/dotnet.exe'
$taskQ3Python = 'C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$taskQ3Run = Join-Path $PWD ('artifacts/q3/' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $taskQ3Run | Out-Null
$env:DOTNET_CLI_HOME = Join-Path $PWD '.tools/dotnet-home'
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$env:NUGET_PACKAGES = 'C:/Users/user/Documents/GitHub/Nikke-Simul/.tools/nuget-packages'
$env:NIKKE_E2_EXAMPLE_ROOT = $taskQ3Run
& $taskQ3Dotnet test tests/Nikke.Core.Tests/Nikke.Core.Tests.csproj -c Release -p:RestoreLockedMode=true -p:RestoreConfigFile=nuget.config --logger 'trx;LogFileName=core.trx' --results-directory $taskQ3Run
$taskQ3Temp = Join-Path $taskQ3Run 'temp'
New-Item -ItemType Directory -Path $taskQ3Temp | Out-Null
$env:TEMP = $taskQ3Temp
$env:TMP = $taskQ3Temp
& $taskQ3Dotnet test tests/Nikke.Sync.Tests/Nikke.Sync.Tests.csproj -c Release -p:RestoreLockedMode=true -p:RestoreConfigFile=nuget.config --logger 'trx;LogFileName=sync.trx' --results-directory $taskQ3Run
$taskQ3Result = (Get-ChildItem -Path (Join-Path $taskQ3Run 'engine-example-*/result.json')).FullName
& $taskQ3Python tests/q3/test_verify_log.py
& $taskQ3Python tests/q3/verify_log.py $taskQ3Result --output-root $taskQ3Run
& $taskQ3Python tests/Nikke.Sync.Tests/test_damage_log_integration.py
node tests/q3/check_ui_contract.mjs $taskQ3Result $taskQ3Run
# a0738ac에서 마지막 명령 종료 1: 통합 수용 실패를 의도대로 보고한다.
node --check tests/q3/check_ui_contract.mjs
git diff --check
```

로그 감사의 종료 0은 구조/불변식 수용이지 게임 정확도나 전체 통합 수용이 아니다. 전체 solution/API 실행 빌드 및 계정 복사본을 사용하는 실제 HTTP/브라우저 통합 검사는 Director 담당으로 **이번 Q3에서는 미실행**이다. 실게임 관측값 대조도 미실행이다.

## 실패 시도·근거 hash

초기 읽기 명령 하나에 PowerShell 미지원 brace expansion을 써 parser error가 났으며 경로를 각각 지정해 다시 읽었다. 제품/테스트 실패가 아니다. Python unittest의 stderr는 Windows PowerShell 리다이렉션에서 NativeCommandError 장식으로 기록됐지만 실제 실행 결과는 OK/종료 0이었다. Node는 제품 package.json의 module type 미지정 경고를 냈다. package.json/package-lock은 이를 없애기 위해 수정하지 않았다.

첫 UI 검사(22개 중 16 실패) 증거 `ui-2c8f41a8-8dac-4112-8f62-a9c74c4b645e/`도 보존했다. 비동기·직접 스킬 발수 테스트 추가 후 위 최종 25개를 새 UUID에 실행했다.

SHA-256은 동일 증거 루트 `evidence-hashes.json`에도 있다.

| 파일 | SHA-256 |
|---|---|
| core.trx | `9cec6424d702ecb69ad7292fc714eeea6c9f0db037bc82b8f7505db732cd5afe` |
| sync.trx | `55eb1747331cdc6b4ee3bd49ce20c1b2c47fdb4ececaebf8008fdeaa34d4e316` |
| 새 input.json | `e14a48955bdbc42f15b6e361ef2ab54a5dc66b5c3df46484346b5a3d2cf40f9b` |
| 새 result.json | `461f3e0e9a2038c3891753eb34635f7ed48c5c3dd661287928a305889f8e7114` |
| 새 manifest.json | `dce19030539f74bf0f80b275d5c82befc9956567b7ec87737dca87fe83baf184` |
| 최종 UI summary.json | `c7f0b267034d4ef93eba19fcbe4d0e6cc10b8aa1c111ed5a414fa31608e92196` |
| 독립 로그 summary.json | `5aa61056d286da838a3450a356cfcca3dc175f4d2546b5afeb535443f6af4826` |

결과 커밋은 아래 후속 기록에 명시한다. 수정본 통합 및 실제 API/브라우저 재검사가 끝나기 전에는 제품 전체 검수 통과를 선언하지 않는다.

## 결과 커밋

검수 도구·테스트·재현 보고 결과: `514daf4` (`test(q3): reproduce integrated damage log and tactic boundary failures`), 제품 기준 `a0738accb16500e52621811fac0dac7259cb7f76`. 이 뒤 문서 커밋은 결과 ID만 추가하며 제품이나 검증 도구 변경은 없다. 최종 `git diff --cached --check` 및 기준 대비 `src`/`apps` diff 없음 확인. 원본 `package-lock.json`만 기존 미추적 상태로 남았다. 미완료는 U3 수정 고정본에서 25개 수용 검사 재실행, Director의 실제 API/브라우저 통합, 실게임 관측 대조다.
