# F-COND-E — 보스 거리·약점 속성 엔진

2026-09-28. 엔진 독립 구현·합성 회귀 검증 완료. Backend 원천/카탈로그·wire·UI·통합 수용·원본 배포는 후속이다.

## 기준과 보존

Director의 `boss-distance-element-assignments-2026-09-28.ko.md` 전체와 참조 지시서의 공통 기준을 UTF-8로 읽었다. 시작 HEAD `5ced15a`, tracked 변경 없음, untracked package-lock.json 1개였다. 사용자 지정 기준 **cd004f1**을 `git merge --no-ff cd004f1`로 일반 merge한 결과는 **d21895b**, 충돌 0. 이전 H-F32·CPU 엔진 커밋을 보존했다.

기존 package-lock.json SHA256 `2EF4178AA07DDD9AC2E4D47422038D02D8ADAADFB15586CEE6A2F1995253C767` 유지·커밋 제외. 본 변경은 Engine 및 Core/Engine 전용 tests와 이 문서뿐이다. merge로 받은 타 담당 파일을 추가 수정하지 않았다. Core의 단일 히트 수동 bool 입력·client_f32 산술·공격력 long·차지/버스트 규칙도 변경하지 않았다.

원본 사용자는 현재 배포본을 사용 중이다. 원본 계정·캐시·DB·세션·EXE·바로가기·5180/5181·실행 중인 배포 프로세스는 변경/종료하지 않았다. 새 서버·worker·Run·Dispatch·worker_done·push·배포 없음. 실제 사용자 실행 경로는 계속 `C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe`다.

## Backend 연결용 내부 계약

`Nikke.Engine.WeaponReplayConditions`에 추가:

| C# 필드 | Web JSON 이름 | 의미 |
|---|---|---|
| int? BossDistance | bossDistance | 정수 0–100 또는 null(미설정) |
| string BossWeakElement | bossWeakElement | Fire/Water/Wind/Iron/**Electronic** 중 하나 또는 null(없음), 대소문자 구분 |

`WeaponReplayMember`에 nullable `int? BonusRangeMin`, `int? BonusRangeMax`, `string Element`를 추가했다(Web JSON `bonusRangeMin`, `bonusRangeMax`, `element`). SkillReplayMember에서는 **member.Weapon** 안에 넣는다. 값은 Backend가 원천 카탈로그에서 채우며 엔진은 원천 파일을 읽지 않는다. 예:

```csharp
var weaponMember = existingMember with {
    BonusRangeMin = 25, BonusRangeMax = 45, Element = "Fire"
};
var combat = new WeaponReplayConditions {
    BossDistance = 35, BossWeakElement = "Fire"
    // ProperDistance/ElementAdvantage 및 Legacy* 필드는 설정하지 않는다.
};
```

외부 API/Contracts DTO·저장 변환·UI wire 이름 확정은 Backend 소유다. 위는 엔진 내부 확정 계약이다.

## 판정과 호환

`BossConditionResolver.Validate/Resolve`를 신규 제공했다. 실행 시작 때 멤버별 판정을 한 번 계산해 SkillReplay actor에 보관하고, WeaponReplay 및 PreparedSkillReplay에도 동일하게 연결했다.

- 거리 보너스: 캐릭터 `min ≤ distance ≤ max`, **양끝 포함(잠정)**. 일반 공격(normal)에만 적용한다. 무기군 평균/대표값으로 대체하지 않는다. 무기 교체 중에도 지시서대로 입력된 캐릭터 사거리를 쓴다.
- RL의 캐릭터 값이 0–0이면 거리0도 보너스 없음. 이 규칙은 `Resolve`에서 검사했으며, 기존 엔진의 RL 전투 미지원 제한을 해제하지 않았다. UI의 데이터 확인 필요 표시는 Backend/UI 후속이다.
- 속성: 멤버 Element가 보스의 BossWeakElement와 **직접 같은지**만 비교한다. 상성 순환표를 사용하지 않으며 평타·직접 스킬/추가타 모두 적용한다.
- 해당 보스 조건이 null이면 보너스 없음. 쓰지 않는 metadata는 없어도 된다. 거리 지정 때 사거리 누락/범위 이상 또는 약점 지정 때 멤버 속성 불명/잘못된 값은 실행/준비 전에 ArgumentException으로 거부한다. 오류 식별자는 `member_bonus_range_unknown`, `member_bonus_range_invalid`, `member_element_unknown_or_invalid`와 CharacterId다. 추정으로 false를 채우지 않는다.
- bossDistance는 int?이므로 JSON 25.5는 JsonException. 범위 밖은 `boss_distance_out_of_range`, 잘못된 약점 문자열은 `boss_weak_element_invalid`다.

이전 bool의 CLR `ProperDistance`/`ElementAdvantage` 사용법과 기존 JSON `properDistance`/`elementAdvantage`는 유지한다. **명시 false와 미지정의 구분**을 위해 내부 nullable backing을 쓰며 JSON은 `LegacyProperDistance`/`LegacyElementAdvantage`라는 nullable C# 접근자가 이전 JSON 이름으로 입출력한다. bool 편의 접근자는 JsonIgnore다. 이전 false도 저장/역직렬화·prepared 깊은 복사에서 보존된다.

새 필드 setter 호출/JSON 필드 존재는 `BossFieldsSpecified`(JsonIgnore)로 추적한다. 새 조건과 이전 bool의 동시 지정은 **false도 포함해 오류** `boss_conditions_mixed_with_legacy`다. 원형 입력에 새 필드가 명시 null이고 이전 bool이 있어도 혼용으로 거부한다. 기존 bool 모드는 예전처럼 전원 적용하며, 거리의 normal 제한도 같다. 레거시 모드 표시 판단에는 Legacy*의 HasValue를 사용할 수 있다.

새 조건 직렬화 시 미지정 Legacy*와 null 보스 필드는 생략한다. 새 거리/약점을 모두 null로 둔 입력은 깊은 복사 후 필드 존재 표시가 없어질 수 있으나 이전 bool도 없고 모든 보너스가 false여서 계산 의미는 같다. **혼용 검증은 null 필드를 생략하는 직렬화 전에 원형 입력에 실행**해야 한다. Backend가 새 객체를 만들 때 이전 bool을 기본 false로 동시에 채우지 말아야 한다. 기존 bool 객체에서 명시적으로 새 모드로 바꿀 때는 Legacy*를 null로 지우거나 새 객체를 만든다. 저장 이력의 UI 모드 표시는 Backend wire에서 보존할 사항이다.

## 버전과 캐시

| 항목 | 신규 버전 |
|---|---|
| BossConditionResolver | boss-distance-element.1-inclusive |
| SkillReplay | p03.skills.4-boss-conditions |
| TeamBurstController | p04.team.4-boss-conditions |
| WeaponReplay | p03.weapon-reference.3-boss-conditions |
| PreparedSkillReplay | cpu-summary.3-boss-conditions |

HitCalculator `p02.4-client-f32`/schema3는 유지한다(수동 단일 히트 이번 범위 밖). 기준 Backend의 PreparedCompute가 이 엔진 상수로 rules/summary 버전을 구성하므로 신규 실행 식별자가 달라진다. 새 조건과 멤버 metadata를 fingerprint에 포함하는지 Backend 종단 확인은 별도 필요하다.

## 실제 검증

Release **174/174 통과, 실패0, skip0**, 최종 빌드 출력 경고 없음. 기존 Core/Engine 147개에 새 조건 테스트 27개를 더했다. `artifacts/boss-conditions/final/conditions.trx` Counters executed=174/passed=174. 최초 실행은 173통과/1실패였고, 신규 테스트가 damage trace에 없는 FunctionId로 필터한 문제를 Effect 키로 수정했다. 제품 결함을 숨기거나 검사를 제외한 것이 아니며 최종 전체 재실행했다.

- min−1/min/max/max+1(24/25/45/46), 전체 유효 한계0/100, RL0–0, SR45–100과 예외25–45를 각각 검증.
- 5속성 각각의 같은/다른 값, normal/skill, 미설정·약점 없음, 사용하는 metadata만 필수인 조건, 불명/잘못된 사거리·속성 오류.
- 범위 밖 거리·소수 JSON·잘못된 문자열, bool false + 새 조건, 새 명시 null + 이전 true까지 혼용 거부. 이전 bool JSON 왕복·새 JSON에 이전 bool 생략 확인.
- 섞인 합성 덱: 같은 native100에서 거리35/약점Fire일 때 AR 범위25–45·Fire는 히트143, 다른 범위45–100·Water는100. 이전 전원 bool true 모드는 둘 다143. 팀 합=개인 합, summary=상세 replay, WeaponReplay client 합 동일, 같은 prepared 객체 병렬4회 일치.
- 직접 스킬 계수1은 Fire 우월만 적용해110, 일반 공격은 거리도 적용해143. 새 거리 판정이 스킬로 새지 않음을 로그 Hit로 확인.
- 기존 5인180초 합성 bool 조건 replay가 기준과 정확히 같음: client 팀 **1346863834**, legacy_term_floor **1346859763**, 풀버스트9회. 구성원 client 피해 `[302652598,302652598,136253442,302652598,302652598]`, legacy `[302651627,302651627,136253255,302651627,302651627]`, shots/hits `[1948,1948,187,1948,1948]`. 직전 H-F32 기록과 동일하다.

전투 증거: `artifacts/hit-f32/1cb518a46b9a431692f15ffa6a2c754a/replay.json`(client), `d8f4945523e7441eb0f1d2bacee68079/replay.json`(legacy). 합성 공개 fixture이며 실제 계정·실게임 관측 검증이 아니다.

실행 명령:

```powershell
$env:DOTNET_CLI_HOME=Join-Path $PWD '.tools/dotnet-home'
$env:NUGET_PACKAGES=Join-Path $PWD '.tools/nuget-packages'
$env:DOTNET_CLI_TELEMETRY_OPTOUT='1'
& 'C:/Users/user/Documents/GitHub/Nikke-Simul/.tools/dotnet/dotnet.exe' test tests/Nikke.Core.Tests/Nikke.Core.Tests.csproj -c Release --no-restore --logger 'trx;LogFileName=conditions.trx' --results-directory artifacts/boss-conditions/final
```

SDK 실행 파일은 읽기 전용 재사용했고 출력/테스트/캐시는 본인 worktree다. 원본 배포 프로세스를 조회·종료하지 않았다.

## Backend/UI/Director 후속 및 미실행

1. Backend가 각 멤버 metadata 및 새 조건을 채우고 새 요청에서 이전 bool을 생략해야 한다. 이전 저장 bool은 명시 레거시로 표시하고 그대로 재현한다. null 양쪽을 새 요청의 명시 모드로 표시/보존하는 wire 처리는 Backend/UI 소유다.
2. **추가 연결 주의:** 기준 `src/Nikke.Data/ComputeOverloadCatalog.cs`의 `IncElementDmg` 유효 후보 판단이 여전히 `combat.ElementAdvantage` 단일 bool을 읽는다. 새 모드에서는 멤버 속성=보스 약점 판정으로 바꿔야 한다. 엔진만 연결하고 이 경로를 남기면 실제 우월 멤버의 OL 옵션 후보가 무효로 분류될 수 있다. 본인 소유 밖이므로 수정하지 않았다.
3. 원천 카탈로그·속성 이미지·무기군 표·예외 목록·wire/API/Storage/OL 연동·UI 팝업·브라우저·외부 fingerprint/복구·독립 QA는 미실행. RL 전체 전투 지원은 계속 미지원이며 0–0 해석/양끝 포함은 실험 후보이지 실측 확정이 아니다.
4. 원본 main 추가 통합·빌드·EXE/설정/UI 배포·원본 실행 검증은 Director 후속이며 현재 배포 사용 환경에 손대지 않았다.

## 확정 커밋·인계

확정 코드 커밋은 생성 후 기록한다. 지시된 Director 기존 터미널을 재조회하고 커밋/절대 보고서 경로/검증/후속 의존성을 한 번 전달한다.
