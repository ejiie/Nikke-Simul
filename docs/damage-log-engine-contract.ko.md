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
