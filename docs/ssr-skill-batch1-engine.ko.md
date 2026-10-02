# S-SKILL-1 — SSR 스킬 조립 1차 묶음 (엔진)

2026-10-03. **1차 커밋 = 스노우 화이트·맥스웰 조립 완료**, 나머지는 지원 상태 표대로 미지원이다. Backend wire/저장·UI·독립 QA·원본 배포 완료와 구분한다. 실게임 실측 검증 전이다.

## 근거·기준·보존

Director의 `skill-precision-assignments-2026-10-03.ko.md`('근거'·'공통'·S-SKILL-1)와 `workflow-implement-review.ko.md`, 참조된 `user-decisions-2026-10-03.ko.md`를 UTF-8로 끝까지 읽고 S-SKILL-1만 수행했다. 시작 HEAD `d932716`(E-BUG-1), Director `e96b147`을 일반 merge(fast-forward, 충돌 0). 기존 untracked `package-lock.json` 1개는 커밋 제외. push·배포·새 worker 없음.

**소유 경로:** 지시서에 별도 소유 목록이 없어 P03(5인 스킬 조립)과 같은 범위를 썼다 — `src/Nikke.Engine/**`, 엔진 tests, 원천→catalog 파이프라인 `tools/data-pipeline/prepare_runtime.py`와 그 Python 테스트, 이 보고서. Data adapter(`RuntimeReplayService`)·Backend·UI·API는 수정하지 않았다(새 필드는 기존 `Loadout()`의 `Deserialize<SkillDefinition>`가 그대로 읽는다).

**원본 접근:** 원본 `data/local`은 공개 표 10개만 읽기 전용 사용(`game-catalog.json`, `calculation/*`) — 전후 hash 동일, `accounts.db`·세션·캐시·presentation·5180/5181·원본 EXE 미접근. 복사본은 이 worktree의 gitignore `artifacts/s-skill-1/data/public/` 안에만 있다. 새 runtime catalog는 원본이 아니라 이 worktree의 `data/local/runtime`에 만들었다(원본 catalog 불변). 파이프라인이 읽는 고정 원천은 아래 hash를 파이프라인이 매번 검증한다(`.reference/*` 4개 파일은 원본 저장소의 reference checkout에서 이 worktree `.reference/`로 읽기 전용 복사).

| 공개 표 (원본 `data/local` 기준) | SHA-256 |
|---|---|
| `game-catalog.json` | `debc8bd372919effb82324c408e2df3c338865173e86b3e344dff208de4b2714` |
| `calculation/current.json` | `ee0a00573b29350591eee26b8204f3e24a23d629071a512853425518265024f6` |
| `calculation/5fec7706…071f/collection.json` | `6ae3df677f8fa4ac910853611e682d54741e42a66db82e64b0546b6720f32f31` |
| `…/cube_base_table.json` | `c9bacbbb779e3869067b2772bd003eb34d2cafb60b1b1bd5eabdcc254fd3c370` |
| `…/cube_effect_table.json` | `5b0231b2103a124e9585631462d5ccfa21d8ce389f68cbb9fc6ddf9213b1fda4` |
| `…/equip_stat_table.json` | `165ff077b0da6f291ff31233fb7d914ece28bc9007414c19a3e3e505557c9dc0` |
| `…/name_codes.json` | `cda0d9666324db1facc3870528bbe0539ec61460b319fe526a06e0bc7867f73f` |
| `…/parsed_nikke.json` | `f93844f04631d0bfe2c14d839dd67f8bc39fc7d2b6301f78a671f0f785cbb7b9` |
| `…/roledata_clean.json` | `c5c4eee8afc23666dc51d06864ab74c1b00e56ce406a545fc05777c8c2b03f4a` |
| `…/stat_table.csv` | `2b8a0b3ad1c42566043f4330e5207d944d88185883c2f8ddd626b3356bddb879` |

(`5fec7706…071f` = `5fec7706b9176fbbef92f04ada1ffab3730f9e058112ac0e4d9e84a5916d071f`. E-BUG-1 때 기록한 같은 파일의 hash와 일치한다.)

| 파이프라인 고정 원천 (`docs/p03-source-manifest.json`) | SHA-256 |
|---|---|
| `Nikke-Dmg-Simulator/Database/raw/staticdata/assembled/skill_chains.json` | `8b47a4a0122cf2bc00332bff11a1f81fc82680066eb809677452d941dfaebe30` |
| `Nikke-Dmg-Simulator/Database/raw/blabla_roledata.json` (7/1판, 스킬 설명·skill_type 이름) | `8568963a75d971cf97489be79bf6f81829bf4e20fdccc74ed10b28159c304348` |
| `.reference/legacy-simulator/Database/processed/roledata_clean.json` | `c5c4eee8afc23666dc51d06864ab74c1b00e56ce406a545fc05777c8c2b03f4a` |
| `.reference/nikke-calc/data/{name_codes,parsed_nikke}.json`, `parsed_skills.json` | `cda0d966…`, `f93844f0…`, `9419f8d62423b5fc9f76b6fade40a4818a1fbdddbda3022c6a8757d51fd68b9d` |

## 대상 선정

Director 추출 목록(`ssr-by-cp.json`, '묑카엘' 계정 전투력 순, 이미 있는 5명 제외) 상위 5명 중:

| 순서 | ID·이름 | 처리 |
|---|---|---|
| 1 | #5012 스노우 화이트 | **조립 완료** |
| 2 | #5129 라피 : 레드 후드 | catalog 포함, **미지원**(아래) |
| 3 | #5001 맥스웰 | **조립 완료** |
| 4 | #5105 홍련 : 흑영 | catalog 포함, **미지원**. 원천 7월판 — 최신 게임 수치와 다름(상향), 원천 갱신 후 재고정 필요 |
| 5 | #5175 신데렐라 : 크리스탈 웨이브 | **원천 없음 — 조립하지 않음.** 고정 원천 3종(`skill_chains.json` 192명, `roledata_clean.json`, `blabla_roledata.json`)에 모두 없다. 원천 갱신(사용자 StaticData 재생성) 후 후속 묶음 |
| (대체) | #5101 레드 후드 | Director 판단(2026-10-03)으로 5번째 자리를 전투력 다음 순서 #5101로 대체. catalog 포함, **미지원** |

**원천 버전 주의(Director 알림 2026-10-03):** 최신 roledata(2026-10-02, 202명, Director artifacts에만 있고 아직 고정 전)와 비교하면 #5105는 밸런스 변경으로 수치가 올랐다(skill1 계수 3개·burst 계수 1개 약 +13%, 예: skill1 lv10 250.47 → 283.03, burst lv10 150.12 → 169.63). 스노우 화이트·라피 : 레드 후드·맥스웰·레드 후드는 설명 문구만 바뀌고 수치·무기 변화 없음. 이번 작업은 고정 원천(7월판)을 쓰며 새 파일은 사용하지 않았다. 계수는 코드에 하드코딩하지 않고 모두 원천에서 읽으므로(`prepare_runtime.py`의 `TARGETS`와 원천 hash만 갱신) 원천 교체 후 재고정만으로 갱신된다.

## 지원 상태 표

판정은 인터프리터 자체의 `SkillReplay.CheckSupport`를 레벨 1~10 × 슬롯 3개 전부에 돌린 결과다(진단은 `GET /api/runtime/catalog`의 `allLevelsExecutable`과 동일 경로). 미지원 캐릭터는 실행 시 `미지원 공식 스킬: …`로 **거부**되며 부분 결과를 만들지 않는다. 근거 ID = `skill_chains.json`의 function/skill ID.

| 캐릭터 | 슬롯 | 효과(원천 ID) | 상태 | 비고 |
|---|---|---|---|---|
| 스노우 화이트 #5012 | skill1 Determination | 30히트마다 Damage 51.75~82.8%(222010101…)·ATK ▲(222010102…) | **지원** | 기존 `OnHitNum`(31) + Damage(75)/StatAtk(1) |
| | skill2 Seven Dwarves: V&VI (CharacterSkill 1220201…, 쿨 15초) | body 13(InstantCircle) 직접 피해 90.46~144.73%, after_use StatCritical(9) 16.31~26.1% 10초, 조건 IsBurstStepState=4(풀버스트 중) | **지원**(가설 1·3·4) | body 13 = 보스 1회 피해 |
| | burst Seven Dwarves: I (1220301…) | ChangeWeapon(7), 1발(Shots), 계수 124.87~499.5%, 교체 무기 차지 5초·풀차지 ×10·탄 1·관통 | **부분 지원**(가설 2·5) | 관통 다중 타격(몸통+파츠) 미모델 — 1타만 계산 |
| 맥스웰 #5001 | skill1 Straight Shot (2102101…) | 풀버스트 진입 시 최종 ATK 상위 2명 차지 속도 ▲·ATK ▲ | **지원** | 앨리스 패턴과 같은 기존 기능 |
| | skill2 Spark Shot (2102201…) | OnSpawnMonster + IsCheckMonster=5, StatCritical·StatCriticalDamage | **지원**(가설 4) | 보스 1체 전투에서는 조건 불충족 → 비활성 |
| | burst Pierce Shot (1102301…) | ChangeWeapon, 1발, 계수 144.85~813.42%, 차지 2초·풀차지 ×3·탄 1·관통 | **부분 지원**(가설 2·5) | 관통 다중 타격 미모델 |
| 레드 후드 #5101 | skill1 Glaring Eyes | OnUseAmmo 차지 속도 ▲ 중첩(지원), **ChargeTimeChangetoDamage(129)** | **미지원** | 129 = 100% 초과 차지 속도의 240%를 차지 피해로 환산(설명). 환산 기준·상한 의미 미확정 |
| | skill2 Wild Tooth | StatPenetration·DrainHpBuff(지원), **StatDef(15)**, **timing OnFunctionOn(21)** | **미지원** | OnFunctionOn = 다른 효과 발동 시 |
| | burst Red Wolf (AllStep→NextStep, 1470301…) | 단계별 3분기(**IsBurstStepState 1·2·3**), ChangeCoolTimeUlti(지원), **Attention(4)**, **HealVariation(52)**, body 7 지속시간(초) 교체 무기 | **미지원** | **팀 버스트 규칙 변경 필요**(AllStep 단계, 아래) |
| 라피 : 레드 후드 #5129 | skill1 Battlefield Assessment | **ChangeUseBurstSkill(180)·ChangeChangeBurstStep(181)**(편성 의존 버스트 단계 변경), **IsCheckTeamBurstNextStep(50/51)**, **IsFunctionOff(45)**, **RemoveFunctionGroup(164)**, **AddDamage(95)** | **미지원** | 편성에 버스트 I이 있는지에 따라 버스트 단계 자체가 바뀜 — 팀 버스트 규칙 필요 |
| | skill2 Attachable Projectiles | **StickyProjectile\*(182~185)**, **ProjectileExplosionDamage(184)**, **AddIncElementDmgType(179)**, timing **OnDead(40)** | **미지원** | 부착 투사체 상태기계 없음 |
| | burst Power of Inheritance | **StatExplosion(12)**, **TargetGroupid(131)**, **TimingTriggerValueChange(130)**, IsFunctionOff(45) | **미지원** | |
| 홍련 : 흑영 #5105 (**7월판**) | skill1 Fleetly Fading: Breakthrough | **CycleUse(134)**, **OnFullChargeShotNum(60)**, **OnFullChargeNum(59)**, **DamageShareInstant(135)**, body 2·21 | **미지원** | 3·6·9번째 풀차지 순환 + 분배 피해 |
| | skill2 Asura | StatAmmo·GainAmmo(지원) | **지원** | |
| | burst Fleetly Fading: Strike | StatAtk·StatChargeDamage(지원), **TargetGroupid(131)**, **TimingTriggerValueChange(130)** | **미지원** | 스킬 1의 풀차지 횟수 조건을 1·2·3회로 바꿈 |
| 신데렐라 : 크리스탈 웨이브 #5175 | — | — | **원천 없음** | 조립하지 않음 |

미지원 효과 이름은 공식 enum(`OfficialSkillEnums.cs`) 기준이다. 각 캐릭터의 원천 그래프 덤프는 `artifacts/s-skill-1/skill-trees.txt`, 게임 설명문은 `artifacts/s-skill-1/descriptions.txt`(gitignore)에 있다.

## 새 엔진 규칙(일반화, 단위 테스트 있음)

- **직접 피해 body 2·13·15**(InstantNumber·InstantCircle·InstantArea): 기존 body 1(InstantAll)과 같이 `values[0]` 계수로 보스 1회 피해. 근거: 로스터의 `skill_type` 이름과 chain 숫자의 일치(1=InstantAll 21건, 2=InstantNumber 32건, 13=InstantCircle 10건, 15=InstantArea 3건, 7=ChangeWeapon 10건, 8=SetBuff 96건) + 설명문의 "Deals X% of final ATK as damage"가 `values[0]`/10000과 레벨별로 일치.
- **StatCritical(9):** 크리 확률에 합산(Integer 1631 = 16.31%, 기존 크리 확률 목록과 같은 단위). `CritMode=sample`에서만 의미.
- **상태 조건 IsBurstStepState(21):** 값 4(= 풀버스트 창 안)만 모델. 1~3은 팀 버스트 단계가 필요해 `status21_value`로 미지원 진단.
- **IsCheckMonster(28) / OnSpawnMonster(26):** 솔로 레이드는 적 1체이므로 임계값 ≥ 2는 항상 불충족, 몬스터 소환 이벤트는 없다. 임계값 < 2는 모호하므로 `status28_value`로 미지원 진단.
- **ChangeWeapon + 교체 무기 프로필(shots 지속):** 이 계열은 교체 무기 표가 고정 원천에 없다(`CharacterShotTable`은 StaticData.zip의 mpk에만 있고 디코드되지 않음). 대신 공개 설명문의 **Charge Time / Full Charge Damage / Max Ammunition / Additional Effect: Pierce**를 `prepare_runtime.py`의 `weapon_change_profile()`이 파싱해 body의 `weapon_change`로 catalog에 기록한다(원천 경로 포함, 레벨별 값이 다르거나 항목이 없으면 오류 — 기본값 채움 없음). 엔진은 이 body에서 별도 `SkillFiringModel`(교체 총)을 만들고 기본 총은 얼려 두었다가 지정한 발 수를 쏜 뒤 그대로 재개한다. 교체 총 발사 1발 피해는 `ChargeBase = 풀차지 배율`, 관통 플래그를 받는다. 기존 시간 기반 ChangeWeapon(모더니아)은 프로필이 없어 **기존 경로 그대로**다.
- `a.Gun` 호출처가 많아 `Actor.Gun`을 `ModeGun ?? MainGun` 속성으로 바꿨고, 최종 결과의 잔여 탄은 항상 기본 총 기준이다. 피해 로그의 차지 필드는 활성 총의 차지 여부를 따른다(기존 캐릭터는 동일).

## 가설·미확정(실측으로 확인할 것)

1. body 13/2/15는 보스 1체에 1회 피해(다중 대상·범위 위치 없음). 기존 body 1과 같은 가정.
2. 교체 무기(**잠정 모션 정책, 게임 미확정 — Director 승인 요청 중**): 시전 즉시 차지를 시작(조준 지연 0), 풀차지까지 충전, 탄창은 프로필 값 고정(기본 무기 탄창 버프 비적용), 차지 속도 버프는 교체 무기 차지 시간에도 적용. 발사 간격은 body의 RPM. 추정값이 결과에 조용히 섞이지 않도록 **교체 총을 쓴 모든 실행에 `replacement_weapon` trace(basis `provisional_motion_policy:…`)와 결과 `limitations` 문구가 붙는다.** **수동 톡톡이 조작은 교체 무기와 함께 `미지원 교체 무기 조작`으로 거부**한다(톡톡이의 의미가 미확정). 조준 지연 0과 spotLast 0은 1발 교체(스노우 화이트·맥스웰)에서 발사 시점이 최대 12F(0.2초) 달라질 뿐 풀버스트 창(10초) 안이다. 승인되지 않으면 해당 실행을 미지원으로 돌린다.
3. skill2는 쿨다운 15초가 지나면 자동 시전(기존 엔진 정책, 첫 시전은 전투 15초 후).
4. IsCheckMonster 임계값 5의 의미는 설명문("above N enemy units, excluding Nikkes")에 따른 적 수 임계값으로 해석했다.
5. **관통 다중 타격 미모델:** 사용자 관측(SW 버스트 한 발 4타: 몸통·파츠·파츠·파츠+코어)과 달리 엔진은 1타만 계산한다 → 버스트 피해가 **과소**. 파츠·코어 구성은 B-DATA-1(보스 정적 속성)·P05 후속이 필요하다.
6. 교체 무기의 charge 속도·탄·관통은 설명문 파싱 값이며 `CharacterShotTable` 대조 전이다. 관통은 `Additional Effect:` 줄이 명시적으로 `Pierce`일 때만 true, `None`일 때만 false이고, 줄이 없거나 다른 값이면 파이프라인이 오류로 멈춘다.

## 검증

- **새 단위 테스트 15개**(`tests/Nikke.Core.Tests/SsrBatch1SkillTests.cs`): body 2·13·15가 body 1과 같은 피해, StatCritical이 샘플 크리 확률을 올림(0.20 난수: 15% 미크리 → +10% 크리), 풀버스트 창 안/밖의 조건 효과, 상태 21·28의 미지원 값 진단, 몬스터 임계값/소환 timing 비활성, 교체 총 정책 라벨(trace·limitations)과 수동 톡톡이 거부, 교체 무기 1발(차지 60F 뒤 `cast + 59`F, ChargeBase 10, 풀차지·관통, 이후 `weapon_restored basis=shots_spent`), 기본 총 상태 동결·탄 연속, 차지 속도 버프로 30F, 2발 교체, 프로필 없는 ChangeWeapon의 기존 경로, 프로필 검증 거부. Python 4개(`weapon_change_profile` 파싱·누락/레벨 가변 거부·**Additional Effect 명시 Pierce/None 구분과 누락·미지의 효과 거부**·AllStep 숫자 두 원천 대조).
- **Release 전체:** `Nikke.Core.Tests` **232/232**(기존 217 + 15), `Nikke.Analysis.Tests` 41/41, `Nikke.Compute.Tests` 46/46, `Nikke.Sync.Tests` 164/164. Python 데이터 파이프라인 44/44. 실패 0·skip 0.
- **기존 5인 회귀(합성 Lv400 계정, 리타·블랑·앨리스·누아르·모더니아, 180초, seed 1~20):** 수정 전(`d932716` 엔진)과 이후를 같은 persisted 입력으로 돌려 팀 피해·멤버별 발수·타수·피해·풀버스트 횟수·첫 풀버스트 시점이 **20개 seed 모두 완전히 동일**(평균 팀 피해 6.621e8, 풀버스트 12회). 새 효과 타입이 기존 5명에게 휴면 상태임을 확인한 것이다.
- **새 캐릭터 실데이터 실행(실제 runtime catalog, 합성 계정, 리타·블랑·스노우 화이트·맥스웰·앨리스, 자동 버스트):** 실행 성공, 풀버스트 4회(블랑 쿨다운 40초가 사이클을 제한 — 원 덱은 팀원의 쿨다운 감소 효과가 있어 12회), 평균 팀 피해 2.876e8. seed 1에서 스노우 화이트는 버스트마다 1발의 풀차지 관통 샷(WeaponShotId 1022002, FullBurst, 코어 가정)을 쏘고 맥스웰은 교체 샷(1010202)과 기본 풀차지 사격을 한다. 이 수치는 장비·OL 없는 합성 계정이라 사용자 관측(2.3B급)과 직접 비교하지 않는다.

## 버전·fingerprint

규칙 버전(SkillReplay·TeamBurstController·PreparedSkillReplay·WeaponReplay)은 **올리지 않았다.** 근거: 새 효과 타입은 이전에 `미지원`으로 거부되던 캐릭터에만 적용되고, 기존 5명의 결과는 위 회귀로 비트 동일하다(지시서: 새 효과 타입이 기존 계산에 영향이 있을 때만 상향). 새로 만든 runtime catalog의 ID는 `2e6e8d06…`(10명)이며 기존 배포 catalog `9c98c91c…`(5명)와 다르다 — `PreparedCompute`의 data version이 fingerprint에 들어가므로 catalog를 교체하면 기존 5인 입력의 fingerprint·캐시도 새 키로 분리된다(결과 값은 같음). 교체·배포·UI 지원 목록 표시는 Backend/QA 후속이다. 미지원 3명은 catalog에는 있고 실행은 거부되므로 UI가 `allLevelsExecutable=false`로 막는지 확인이 필요하다.

## 다음 후보 (Director 판단 필요)

- **레드 후드 #5101:** 미지원 효과는 6종이지만 핵심은 AllStep 팀 버스트 규칙이다 — 컨트롤러는 현재 I→II→III만 허용하며(`Step 1~3, NextStep = Step+1`), 단계 지정 우선순위 전술(`stage1/2/3Priority`)도 AllStep 대상을 표현하지 못한다. 설명문상 "어느 단계로 쓰든 다음 단계로 진행"으로 읽히지만 이는 팀 버스트 규칙(가설)이라 **규칙 결정 후 별도 배정**을 권한다.
- **홍련 : 흑영:** CycleUse·TargetGroupid·TimingTriggerValueChange·분배 피해. 순환 카운터와 단계 조건 변경 의미는 설명문만으로 확정이 약하다.
- **라피 : 레드 후드:** 편성 의존 버스트 단계 변경 + 부착 투사체. 가장 크다.

## 리뷰 이력

### 1차 — 반려 (astra-6, 대상 `dbe9b68`)

- `src/Nikke.Engine/Skills/SkillReplay.cs:622` — 항목 3·5 — `ReplacementGun`이 원천/확정 규칙 없이 spotFirst/spotLast를 0으로 채우고, 624행에서 수동 톡톡이도 FullCharge로 강제한다. `CheckSupport`는 실행을 허용하므로 결과에 추정값이 들어간다.
- `tools/data-pipeline/prepare_runtime.py:127` — 항목 5 — 관통을 `Additional Effect: Pierce` 문자열 포함 여부로 산출해, 효과 항목 누락·미해석도 false(비관통)로 조용히 채운다. 누락 회귀 테스트도 필요.
- 리뷰어 확인(통과 항목): 소유 범위는 원천 catalog 조립에 필요한 파이프라인 포함으로 해석 가능, #5101 대체(Director 문서) 확인, 공개 표 hash·보관 기록 확인, 버전 미상향은 지시서 조건과 기존 5인 회귀 보고에 부합하고 catalog dataVersion·graph/conditions fingerprint 분리 경로 확인. 지정 SDK로 Release Core 231/231, Python 43/43 통과(실패/skip 0). 비차단: `SsrBatch1SkillTests.cs` 마지막 테스트는 같은 구현을 두 번 비교하므로 전후 회귀 증거는 보고서/별도 결과에 의존(반려 사유 아님).
- 구현 담당 대응(수정 커밋):
  - **결함 1:** 확정 원천이 없어(교체 무기 표 미고정, 사용자 실측 없음) 값을 확정으로 가장하지 않고 **정책을 명시적으로 드러내도록** 바꿨다. (a) 교체 총을 쓴 모든 실행에 `replacement_weapon` trace(basis `provisional_motion_policy:no_spot_delay_full_charge_fixed_magazine`)와 결과 `limitations` 문구를 추가. (b) 수동 톡톡이는 교체 무기 보유 캐릭터에서 `Validate`가 `미지원 교체 무기 조작`으로 거부(톡톡이 의미 미확정이므로 FullCharge 강제 제거 근거 확보). (c) 조준 지연 0·풀차지 정책의 **Director 승인**을 요청했다(영향: 1발 교체 무기의 발사 시점 ≤ 0.2초). 승인 전까지 결과 문구가 잠정 정책임을 밝히고, 승인되지 않으면 해당 실행을 미지원으로 돌린다.
  - **결함 2:** `Additional Effect:` 줄을 필수로 읽고 `Pierce`(true)/`None`(false)만 인정, 줄 누락·`Explosion`·`Pierce, Explosion` 등 알 수 없는 값은 `ValueError`. 회귀 테스트 `test_pierce_is_explicit_and_a_missing_or_unknown_effect_is_an_error` 추가. 현 고정 원천에서 스노우 화이트·맥스웰은 모두 `Pierce`로 명시돼 catalog id `2e6e8d06…`는 변함없다.
  - **비차단:** 같은 구현을 두 번 비교하던 마지막 테스트는 가짜 증거라 삭제하고, 전후 회귀 증거는 위 '검증'의 기존 5인 20 seed 비트 동일 결과(수정 후 재실행도 동일)에 둔다.
  - 재검증: Core 232/232, Analysis 41, Compute 46, Sync 164, Python 44/44, 기존 5인 20 seed 동일.
