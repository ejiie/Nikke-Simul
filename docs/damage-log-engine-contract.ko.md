# E1 damage log / burst tactic 엔진 계약

기준 `e6935857c35caac198c649e744132d7391721ecb`. 이 문서는 엔진 내부 public DTO 계약이다. 외부 HTTP/저장 JSON 이름·스키마는 B1 소유이며 아래 camelCase 예시는 엔진 직렬화 예시다. 첫 계약 커밋 시점에는 구현/검증 전이다.

## 선택 피해 로그 v1

`SkillReplayConditions.DamageLog: DamageLogOptions`는 null이면 미수집, 객체이면 수집한다. `CharacterId` 기본값은 문자열 `5004`, 편성 밖 ID는 거부한다. `SkillReplayResult.DamageLog: DamageLogSummary`는 미수집/과거 결과에서 null이다. 수집한 실제 0 피해는 non-null 요약의 `TotalDamage=0`, `Entries=[]`로 구별한다.

`DamageLogSummary` public 필드: `SchemaVersion=1`, `CharacterId`, `Status="complete"`, `Truncated=false`, `TruncationReason=null`, `EventCount`, `TotalDamage`, `Entries`. 일반 trace/timeline 한도와 독립이며 10800프레임(180초) 전체 피해를 보존한다. 성공 결과에는 행 제한을 적용하지 않는다. 처리 실패를 잘린 정상 결과로 반환하지 않는다.

`DamageLogEntry`: `HitId`(실행 trace ID, 전체 실행 내 유일), `ParentId`, `ShotId`(발사 trace ID, 직접 스킬이면 null), `PelletIndex`(0부터, 직접 스킬/탄 소비 트리거이면 null), `Frame`, `Seconds=Frame/60d`, `Source`, `Target`, `Effect`, `Kind`(CombatEventKind), `SkillId`, `FunctionId`, `Damage`, `CumulativeDamage`(선택 캐릭터 전체 피해 순서 누적), `WeaponShotId`, `ChargeRatioRaw`(10000=100%), `FullCharge`, `EffectiveChargeFrames`(발사 당시 실효 풀차지 목표), `ActualChargeFrames`(발사 당시 누적), `Shot`(ShotEventData), `OwnBurstEffectActive`, `OwnBurstCastId`, `Hit`(HitContext), `Calculation`(선택된 DamageBreakdown), `Buffs`(DamageBuffSnapshot 목록).

차지 필드는 차지 평타에서만 값이 있고 다른 피해에서는 null이다. 추가타의 `ShotId`는 원인 발사이며 새로운 발사가 아니다. `Shot`도 원인 발사 상태이며 추가타의 차지 상태를 의미하지 않는다. `Hit`에는 확정 시점의 크리·코어·팀 풀버스트·공격력 원값/출처별 비율/고정량·방어력·계수·모든 피해 축을 보존한다. `Calculation.Terms`에 실효 공격력/방어력/차지 배율/단계별 반올림이 있다. 기존 p02.3의 비풀차지 피해 배율 1 정책을 유지하며 로그 차지 비율을 피해/게이지에 새로 곱하지 않는다.

`DamageBuffSnapshot`: `Effect`(SkillEffectView), `AppliedAtFrame`(마지막 적용/갱신), `EventId`, `BurstCastId`(명시적 burst 본체/연결 함수에서 유래한 경우에만 ID). `Effect.ExpiresAt`은 배타적 종료, null은 엔진의 무기한/조건 효과다. 피해 대상에게 적용 중인 효과와 보스 디버프를 보존한다. 상시 버프 출처는 Hit의 목록, 수동 시간 버프의 유효 구간은 Conditions.Combat.AttackBuffWindows에 남는다. 실제 산식에 쓰이지 않는 효과도 목록에 있을 수 있으며 적용 축은 Hit/Calculation으로 판별한다.

자체 버스트 활성은 해당 시전자의 명시적 burst에서 생성되어 아직 남아 있는 효과/무기모드/보호막이다. 단순 쿨다운, 요청된 팀 풀버스트 기간, 풀버스트 진입 패시브는 자체 버스트 활성으로 간주하지 않는다. 즉시 직접 피해만 있는 버스트는 지속 활성 상태를 만들지 않는다. 팀 상태는 `Hit.FullBurst`와 독립이다. 실게임 버프 아이콘의 의미까지 확정하는 필드가 아니다.

로그를 기록하려고 재실행하거나 추가 난수를 사용하지 않는다. 피해 확정에 사용한 Calculation 자체를 기록한다. 스냅샷 ID는 엔진이 만들지 않는다. B1은 기존 계정/계산/런타임 식별자, 입력 멤버, Conditions, replay RulesVersion, HitCalculator.Version 및 로그 SchemaVersion을 함께 저장/내보내야 한다.

```json
{"damageLog":{"characterId":"5004"}}
```

## 명시적 tactic v1

`TeamBurstOptions.Tactic: BurstTactic` 추가. null이면 기존 모든 의미(편성 순서, Burst3Rotation, UnavailablePolicy, 불완전 편성 대기)를 보존한다. non-null이면 기존 `Burst3Rotation`은 빈 목록이어야 하며 `UnavailablePolicy`는 기본 next_ready여야 한다. 혼용은 거부한다.

`BurstTactic`: `SchemaVersion=1`, `AllowedCharacterIds`, `Stage1Priority`, `Stage2Priority`, `Stage3Priority`, `Burst3Rotation`, `FirstBurst3CharacterId`(null이면 순환 첫 원소), `UnavailablePolicy="next_ready"`. 모든 목록은 non-null/중복 없음. 허용 ID는 현재 편성에 있어야 한다. 우선순위는 해당 단계 허용 캐릭터의 정확한 순열이며 각 단계 최소 1명, burst 본체가 시전 가능해야 한다. 순환은 III 허용 후보의 비어 있지 않은 중복 없는 부분집합이다. 첫 시전자는 순환 안에 있어야 한다. 엔진 실행은 불가능한 구성을 거부하며 초안 저장 허용 여부는 B1이 별도로 처리한다.

I→II→III 단계 순서와 기존 세 전이 delay/max 정책, 원천 게이지 모델은 바꾸지 않는다. I/II는 단계별 순위, III는 현재 순환 우선 캐릭터를 맨 앞에 놓고 나머지는 Stage3Priority 순으로 선택한다. wait_preferred는 첫 후보만 대기, next_ready는 이 순서에서 준비된 최초 후보를 사용한다. 제외 캐릭터도 사격/게이지에는 기여하지만 어떤 단계의 대체 시전자도 될 수 없다.

III 시전 성공 직후 순환 포인터를 **우선 슬롯에서 한 칸** 전진한다. 대체 캐릭터가 누구인지와 무관하다. I/II/III 대기·단계 만료·재충전은 포인터를 전진시키지 않는다. 따라서 첫 시전 전에 만료돼도 첫 시전자는 유지된다. 기존 null tactic은 windows.Count 기준으로 유지한다. 결과 TeamBurst.Options에 입력 설정 전체를 보존한다. 기존 규칙 버전 `p04.team.2/source_full_charge_v2`는 유지하고 새 정책은 Tactic.SchemaVersion으로 구분한다.

```json
{"tactic":{"schemaVersion":1,"allowedCharacterIds":["liter","blanc","5004","modernia"],"stage1Priority":["liter"],"stage2Priority":["blanc"],"stage3Priority":["5004","modernia"],"burst3Rotation":["5004","modernia"],"firstBurst3CharacterId":"5004","unavailablePolicy":"next_ready"}}
```

예시의 liter/blanc/modernia는 합성 ID다. 실제 호출은 현재 편성의 ID를 사용한다. API 필드 계약은 아직 통합되지 않았으며 UI/저장 연결 완료를 주장하지 않는다.

## E1 구현 및 실제 검증 결과 — 2026-09-11

기준 `e6935857c35caac198c649e744132d7391721ecb`로 자신의 브랜치만 fast-forward했다. 선행 계약 커밋은 `d7ce350`, 구현·단위 테스트 커밋은 `0eda677`이다. 기존 untracked `package-lock.json`은 보존했다. 다른 작업공간·계정 데이터·기존 P04 artifacts·API/Data/Storage/UI·공용 프로젝트 파일은 수정하지 않았다. 새 에이전트/Run/Dispatch, push, 배포도 수행하지 않았다.

변경 파일:

- `src/Nikke.Engine/Skills/DamageLog.cs`: 로그 public DTO와 수집/완전성 의미.
- `src/Nikke.Engine/Skills/BurstTactic.cs`: 버전 1 설정과 실행 입력 검증.
- `src/Nikke.Engine/Skills/SkillDefinitions.cs`: 선택 로그 입력/결과 필드.
- `src/Nikke.Engine/Skills/SkillReplay.cs`: 기존 피해 확정 결과 수집, 효과의 시전 출처/유효 시점, 자체 버스트 상태.
- `src/Nikke.Engine/Skills/SkillFiringModel.cs`: 발사 당시 실효/누적 차지 프레임의 읽기용 값.
- `src/Nikke.Engine/Skills/TeamBurstController.cs`: 허용 후보·단계별 순위·첫 III 시전자·순환 전진 연결.
- `tests/Nikke.Core.Tests/DamageLogTests.cs`, `tests/Nikke.Core.Tests/BurstTacticTests.cs`: 신규 합성 회귀 20개.
- 이 계약/결과 문서. Nikke.Core와 기존 단위 테스트 파일은 변경하지 않았다.

실행 환경: 고정 SDK `C:/Users/user/Documents/GitHub/Nikke-Simul/.tools/dotnet/dotnet.exe` 10.0.400을 사용했다. 기존 NuGet 패키지는 이 작업공간의 `.tools/nuget-packages`로 복사하고 로컬 CLI HOME을 사용했다. 공유 SDK/원본 패키지에 쓰는 설정은 사용하지 않았다.

실제 명령 및 결과:

```powershell
$env:DOTNET_CLI_HOME = Join-Path $PWD '.tools/dotnet-home'
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$env:NUGET_PACKAGES = Join-Path $PWD '.tools/nuget-packages'
& 'C:/Users/user/Documents/GitHub/Nikke-Simul/.tools/dotnet/dotnet.exe' test tests/Nikke.Core.Tests/Nikke.Core.Tests.csproj -c Release -p:RestoreLockedMode=true -p:RestoreConfigFile=nuget.config --logger 'console;verbosity=minimal'
# 기존 91개 통과, 실패/skip 0 (신규 테스트 추가 전 실행).
& 'C:/Users/user/Documents/GitHub/Nikke-Simul/.tools/dotnet/dotnet.exe' test tests/Nikke.Core.Tests/Nikke.Core.Tests.csproj -c Release --no-restore --logger 'console;verbosity=minimal' --logger 'trx;LogFileName=e1-engine.trx' --results-directory artifacts/e1/20260911
# 중간 검증 109개 통과, 실패/skip 0.
& 'C:/Users/user/Documents/GitHub/Nikke-Simul/.tools/dotnet/dotnet.exe' test tests/Nikke.Core.Tests/Nikke.Core.Tests.csproj -c Release --no-restore --logger 'console;verbosity=minimal' --logger 'trx;LogFileName=e1-engine.trx' --results-directory artifacts/e1/20260911/final
# 최종 111개 통과, 실패/skip 0, 실행기 보고 기간 28초.
git diff --check
# 오류 없음. Git의 LF→CRLF 안내만 출력됨.
```

최종 증거는 이 작업공간의 ignored `artifacts/e1/20260911/final/e1-engine.trx`이며 중간 결과 파일과 기존 P04 증거를 덮어쓰지 않았다. 테스트 명령은 Core/Engine/테스트 프로젝트를 Release로 빌드했고 최종 빌드 출력에 컴파일 경고·오류가 없었다. solution 전체/API/저장/브라우저 테스트를 이번 E1 작업에서 실행했다고 주장하지 않는다.

최종 TRX SHA-256: `5bb54517d5a8fb9e5c8b3db4060ae7dc423b5ee8d58a8e70fa886165a95ac7b6`.

시도 중 실패도 구분한다. 최초 `dotnet test --locked-mode`는 지원하지 않는 스위치로 실패해 `-p:RestoreLockedMode=true`로 수정했다. NuGet 사용자 설정 읽기 및 테스트 출력 DLL 쓰기는 샌드박스 권한 차단이 있었고, 승인된 권한으로 복원/빌드/테스트를 재실행하여 위 성공 결과를 얻었다. Git 메타데이터의 작업공간 외부 위치 때문에 fast-forward와 커밋도 승인된 권한을 사용했다. 강제 reset/checkout/stash는 사용하지 않았다.

검증의 의미:

- 발당 독립 합성 기대값: 공격력 100, 방어력 10, 풀차지 3.5에서 기본 315, 크리 472, 코어 630, 둘 다 787(항별 내림). 세 정수화 후보별 로그 합계/선택 계산 결과 일치도 검사했다. 부분 차지 비율을 기록하되 피해 배율 1을 유지한다.
- 자체 공증 적용 전/중/후, 팀 풀버스트 OFF/ON의 네 조합과 배타적 만료 프레임, 적용/시전 출처 보존을 확인했다. 즉시 직접 스킬의 shot/차지 null, SG 펠릿 및 추가타의 원인 발사 공유도 검사했다.
- 차속 변경 후 합성 발사 프레임 30/60/120, 재장전 fixture 1/32/63 및 탄 전/후 상태를 검사했다. 원천 발사 모델의 수치는 바꾸지 않았다.
- 180초 로그 합계=선택 니케 총피해, 마지막 구간 누락 없음, trace OFF/한도 1과 로그 불변, 2만 행을 넘는 로그 완전성, 로그 ON/OFF의 피해·발수·잔탄·이벤트·난수 소비 일치를 검사했다.
- 사용 제외 니케는 게이지에 기여하되 대체 시전에서도 제외된다. 단계별 순위, 첫 III 시전자, 순환, wait_preferred 만료 후 슬롯 유지, next_ready 대체 후 우선 슬롯 전진을 검사했다. 순환 밖 대체 시전자가 있는 합성 기대 순서는 c/d/e/d/e/d다.
- stale/중복/잘못된 단계/미지원 버전/불완전/비시전형/구·신 설정 혼용 입력을 거부한다. 기존 null tactic 실행의 의미를 보존했다.
- 기존 91개 회귀를 함께 통과했다. 새 테스트에서 기본 I→II·II→III 1~10프레임, III→풀버스트 28프레임과 원천 적용 지연 max(합성 18/24/36프레임), 종료 후 재충전을 검사했다. 기존 앨리스형 자동·수동 56000×35000/10000=196000 테스트도 포함된다.

모든 신규 전투 조건은 **엔진 내부 합성 검증**이다. 실제 계정의 공식 앨리스 그래프/저장 스냅샷으로 새 로그를 API 경유 검증하거나 게임 영상/틱을 관측한 결과가 아니다. 기존 산식 자체가 실게임과 일치한다는 증거로 해석하지 않는다.

남은 의존성과 제한:

- B1의 외부 API/저장/JSON·CSV 계약, 계정·계산·런타임 식별자 결합, 입력 매핑, 과거 미수집 결과 표시, tactic 저장/복원 통합은 미완료다. 아직 없는 upstream을 E1이 임의 확정하지 않았다.
- U1의 실제 API 연동/브라우저 검증, Q1의 독립 통합 검수, S1의 실제 로그 adapter 연결은 해당 담당 커밋 통합 후 확인해야 한다.
- 게임 대미지 정수화·차지/재장전 실측·버스트 지연/같은 프레임 순서·자체 버스트 아이콘과 엔진 효과 상태 대조는 관측 자료가 필요하다. 부분 차지 피해 보간을 새로 확정하지 않았다.
- 로그는 현재 지원하는 실제 피해 경로 전체를 담으며 미지원 보스 파츠/관통 다중 대상/적 행동을 생성하지 않는다. 무제한 정상 로그는 trace보다 메모리·저장 크기가 크므로 B1/UI는 조회/내보내기에서 이를 고려해야 한다. 임의 행 제한이나 조용한 누락은 도입하지 않았다.

E1의 엔진 구현·단위 검증은 완료했다. 제품 전체 통합 또는 실게임 검증 완료 보고는 아니다.
