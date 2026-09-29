# F2-E — 덱 팀 누적 피해에 따른 방어력 자동 전환

2026-09-29. R4 엔진 구현·합성 회귀 검증 완료. Backend wire/저장·UI·독립 QA·원본 배포 완료와 구분한다.

## 근거·기준·보존

Director의 `combat-conditions-cleanup-assignments-2026-09-29.ko.md`와 `user-requests-2026-09-29.ko.md`를 UTF-8로 끝까지 읽고, 참조 지시서의 공통 기준·보존 및 F2-E만 수행했다. 사용자 R4: 한 덱의 누적 피해가 20억 이하이면 DEF 30925, 초과하면 그 이후 DEF 31784. 다섯 덱의 누적 합을 공유하지 않는다.

시작 HEAD `f374c1d`, tracked 변경 없음, 기존 untracked `package-lock.json` 1개. `git merge e98db6a`로 일반 merge했고 **fast-forward, 충돌 0**. 본인 F-COND-E·H-F32·CPU 커밋을 모두 보존했다. 새 변경은 `src/Nikke.Engine/**`, 엔진 tests, 이 문서만이다. Core 산술·타 담당 제품 코드는 수정하지 않았다.

package-lock.json SHA256 `2EF4178AA07DDD9AC2E4D47422038D02D8ADAADFB15586CEE6A2F1995253C767` 보존·커밋 제외. 원본 `data/local`·계정·캐시·EXE·바로가기·5180/5181·원본 경로 프로세스는 조회·변경·종료하지 않았다. 새 서버, 다른 worktree 편집, 새 worker/Run/Dispatch/worker_done, push, 배포 없음. 실제 사용자 실행 경로는 계속 `C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe`다.

## 확정 엔진 입력 계약

공통 `WeaponReplayConditions`에 `string DefenseMode` 추가(Web JSON `defenseMode`). `SkillReplayConditions.Combat.DefenseMode`로 전달한다.

| 모드 | 의미 |
|---|---|
| `fixed` | 기존 `EnemyDefense`를 전투 전체에 사용. 필드 생략 시 기본값으로 적용해 구 저장본 재현 유지 |
| `team_damage_threshold` | DEF 30925로 시작해 팀 확정 피해 누적이 2,000,000,000을 **초과한 타격 다음부터** 31784 |

`Nikke.Engine.DefenseMode`의 `Fixed`, `TeamDamageThreshold`, `InitialDefense`, `SwitchedDefense`, `DamageThreshold` 상수를 제공한다. 모드 null/빈 문자열/기타 값은 실행·준비 전에 `ArgumentException("defense_mode_invalid")`로 거부한다. 임계값·시작/전환 DEF의 사용자 지정 기능은 만들지 않았다.

```csharp
var conditions = existing with {
    Combat = existing.Combat with {
        DefenseMode = Nikke.Engine.DefenseMode.TeamDamageThreshold,
        EnemyDefense = 30925
    }
};
var replay = SkillReplay.Run(members, graph, conditions);
var summary = PreparedSkillReplay.Create(members, graph, conditions).Run(cancellationToken);
// replay.Defense 및 summary.Defense에 동일한 전환 기록
```

자동 모드에서 `EnemyDefense`는 실제 계산에 사용하지 않는다(시작 30925가 우선). 기존 숫자 유효성 검사는 유지하므로 유한한 범위 내 값, client_f32에서는 정수여야 한다. Backend가 새 요청에는 자동 모드를 명시하고 EnemyDefense를 30925로 정규화하는 것을 권장한다. **엔진 기본을 자동으로 바꾸지 않았다**: 필드가 없는 구 저장본의 고정 DEF 의미를 보존하기 위해서다. 새 제품 요청 기본값/표시/저장 호환 wire는 F2-B 소유다.

## 판정·전환 기록

각 `SkillReplay` 실행마다 `BattleDefense` 상태를 새로 만든다. 모든 일반 공격, 펠릿, 직접 스킬, 추가타가 공통 `Damage` 처리에서 선택한 정수화 정책으로 확정한 피해를 누적한다. 계산 → 멤버 피해 집계 → damage trace ID 부여 → 누적/전환 순서이며, 이어지는 추가타나 같은 프레임의 다른 멤버도 새 방어력을 즉시 사용한다. 전환은 한 번이며 다른 덱·반복 실행·병렬 prepared 실행과 상태를 공유하지 않는다. 고정 모드는 누적/전환을 하지 않아 기존 damage/trace 순서를 유지한다.

**잠정 가설:** 20억과 같을 때는 전환하지 않고, 초과시키는 타격 자체는 DEF 30925, 그 다음 타격부터 31784다. 같은 프레임은 기존 처리 순서를 따른다. 두 DEF·임계값은 지시서의 기존 실측 근거를 따르지만 이 경계 세부를 실게임 확정으로 주장하지 않는다.

`SkillReplayResult.Defense`와 `SkillRunSummary.Defense`는 `DefenseRunSummary`다:

- `Mode`, `InitialDefense`, `FinalDefense`, `DamageThreshold`(fixed는 null).
- `SwitchAfterHit`: 전환 없으면 null, 있으면 `DefenseSwitch`.
- `DefenseSwitch`: `Frame`, `HitTraceId`, `HitOrdinal`(덱 전체 확정 타격 1부터), `CharacterId`, `Effect`, `CumulativeDamage`, `PreviousDefense`, `NewDefense`.

`HitTraceId`는 초과시킨 **damage 이벤트** ID이고, 전환 알림 이벤트 ID가 아니다. trace에는 `Kind="defense_switch"`, `ParentId=HitTraceId`, `Value=CumulativeDamage`, `Basis="team_damage_strictly_greater_next_hit"` 및 같은 구조의 `DefenseSwitch`가 남는다. 초과 타격의 Hit.Defense는 30925이며 다음 타격은 31784다. 기존 캐릭터 damage log의 Hit에도 실제 적용 DEF가 들어간다.

trace 꺼짐·TraceLimit 초과·CPU summary에서도 결과의 전환 기록은 보존된다. 전투 시작 수동 패시브의 직접 피해로 초과하면 Frame=0도 가능하다. 마지막 타격에서 초과해도 SwitchAfterHit/FinalDefense=31784를 기록하되, 그 마지막 타격은 30925로 계산했다. 타격 ID는 trace 수집 여부와 무관하게 생성돼 동일 조건의 상세/summary에서 같다.

`WeaponReplay.Run`은 여러 정수화 정책을 동시에 비교하는 평타 참조 경로라 단일 팀 누적값이 없다. 자동 모드를 조용히 고정 DEF로 계산하지 않도록 `weapon_reference_requires_fixed_defense_use_skill_replay` 오류로 거부한다. R4 전투/통계 자동 모드는 **SkillReplay/PreparedSkillReplay**를 사용해야 한다. 단일 HitCalculator 수동 검산과 기존 WeaponReplay fixed 경로는 유지한다.

## 버전·Backend 후속 계약

| 항목 | 신규 버전 |
|---|---|
| SkillReplay | `p03.skills.5-defense-switch` |
| TeamBurstController | `p04.team.5-defense-switch` |
| PreparedSkillReplay | `cpu-summary.4-defense-switch` |

HitCalculator/client_f32 산술·BossConditionResolver·WeaponReplay 고정 참조 계산 버전은 유지한다. 기준 Backend의 PreparedCompute는 위 엔진/summary 상수를 사용하고 conditions 전체를 fingerprint에 포함하므로 버전 및 모드 값이 키에 들어간다. 실제 API·캐시·저장 종단 수용은 미실행이며 F2-B/QA 후속이다.

Backend 연결 필요 사항(소유 밖이라 수정하지 않음):

1. 새 요청 `Combat.DefenseMode=team_damage_threshold`, 구 저장본 모드 생략/명시 fixed는 `EnemyDefense` 그대로 재현·표시. 외부 wire 이름/검증은 F2-B 확정 사항이며 위 이름은 엔진 내부 계약이다.
2. `src/Nikke.Data/ComputePreparation.cs`의 `PreparedCompute.Create`는 ExperimentInput에 여전히 `"fixed:" + EnemyDefense` 라벨을 채운다. 자동 모드에 맞는 라벨로 연결해야 한다.
3. 같은 파일 `PreparedCompute.Run`은 엔진 summary에서 총 피해/멤버/횟수/시간만 Contracts.RunSummary로 옮긴다. **전환 증거를 compute 결과/저장에 남기려면 새 `result.Defense`도 DTO/저장 경계로 전달**해야 한다. 엔진 내부 summary에는 이미 보존된다.
4. 솔로 레이드 replay 자동 경로를 SkillReplay로 연결하고, 평타 다중 정책 참조 요청이 자동 모드일 때 위 명시적 오류를 처리한다.

## 실제 검증

Release **196/196 통과, 실패 0, skip 0**, 빌드 출력 경고/오류 없음. 기존 174개 + 신규 `DefenseSwitchTests` 22개다. 첫 전체 실행에서 모두 통과했다. TRX: `artifacts/def-switch/first/defense-switch.trx`(Counters total/executed/passed=196). `git diff --check` 통과(CRLF 변환 안내만).

- 10억 종료·정확히 20억 종료 전환 없음(client/legacy). 정확히 20억+1에서 전환, 마지막 초과 타격도 기존 DEF.
- 같은 프레임 네 멤버에서 10억·10억·10억까지 DEF30925, 네 번째만31784. client_f32 네 번째 피해 **999,999,168**, 기존 3정책은 **999,999,141**. 차이는 기존 산술의 binary32 양자화 그대로다.
- 시작 직접 스킬·평타·추가타의 피해가 합산되고, 초과 추가타 뒤 같은 프레임 다음 멤버에 반영. 시작 패시브 초과 Frame0 기록.
- 샷건 4펠릿의 순서 중 3번째 초과, 4번째부터31784. 캐릭터 damage log 실제 DEF 확인.
- trace 비활성/1건 제한에서도 결과 및 summary 전환 기록 유지. summary=상세 replay, 팀 합=구성원 합 확인.
- 고정 DEF30925/31784 구 JSON 필드 생략 결과와 명시 fixed 결과·trace 동일. 기존 5인180초 합성 fixture는 client 팀 **1,346,863,834**, legacy **1,346,859,763**으로 그대로이며 이번에 이 두 총합을 명시 assert로 강화했다.
- 자동 버스트 경로·CPU summary 일치, prepared 취소 후 재사용·병렬4회 상태 분리, 새 덱 시작 시 누적 초기화.
- 모드 null/빈 값/미지원 오류, 평타 다중 정책 참조에서 auto 명시적 거부.

```powershell
$env:DOTNET_CLI_HOME=Join-Path $PWD '.tools/dotnet-home'
$env:NUGET_PACKAGES=Join-Path $PWD '.tools/nuget-packages'
$env:DOTNET_CLI_TELEMETRY_OPTOUT='1'
& 'C:/Users/user/Documents/GitHub/Nikke-Simul/.tools/dotnet/dotnet.exe' test tests/Nikke.Core.Tests/Nikke.Core.Tests.csproj -c Release --no-restore --logger 'trx;LogFileName=defense-switch.trx' --results-directory artifacts/def-switch/first
```

SDK 실행 파일만 읽기 전용 재사용했고 빌드/테스트/CLI home/NuGet 출력은 본인 worktree다. 합성 fixture 검증이며 원본 계정·실게임 관측을 하지 않았다. 부하·성능 수치는 측정하지 않았다. API/UI·Contracts 저장·외부 fingerprint/캐시·독립 QA·원본 통합/빌드/배포/실행 검증은 미완료 후속이다. R1~R3/R5~R8 및 다른 담당 구현은 수행하지 않았다.

## 확정 커밋·인계

확정 구현·테스트 커밋 **d090641ca120baa6f8d8178d035ee2dc01122e37**. 기준 **e98db6a** 일반 merge는 fast-forward였으며 별도 merge 커밋은 없다. 검증 근거는 위 Release 196/196 TRX다.

Director terminal list 재조회에서 `term_73afed41-4bf2-4551-8ed4-01c8a64e47bc`(Claude, 연결·쓰기 가능)를 확인했다. 이 기록 커밋 후 해당 기존 터미널에 확정 커밋·보고서 절대 경로·실제 검증·Backend 연결 의존성을 한 번 인계한다. 수신 확인은 제품 통합·배포 완료가 아니다.
