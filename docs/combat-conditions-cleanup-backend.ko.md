# F2-B — 전투 조건 정리·보스 선택 Backend (2026-09-29)

## 완료 범위와 기준

Director `e98db6a` 및 통지받은 엔진 `1a86ec9`를 Backend `97ba7bf` 위로 차례대로 일반 fast-forward merge했다. 충돌0, 기존 커밋 보존. 엔진의 자동 DEF 전환을 SkillReplay·compute API/Contracts/저장에 연결하고 새 요청 고정값·이전 조건 재현·표시 전용 보스 선택을 구현했다. 한국어 이름 원천이 확인되지 않은 항목은 명시적으로 제외한다. **Backend 구현·격리 검증 완료이며 전체 보스 한국어 원천 확보·독립 QA·UI 실제 연결·원본 배포 완료는 아니다.**

초기 세션에서는 Git 메타데이터 쓰기 권한과 CLI/네트워크가 막혀 초안만 작성했다. Full access 재지시 후 worktree git-dir에 임시 파일 생성·삭제를 확인하고 정상 merge했다. Git 기록을 바꾸는 권한 확인 명령은 사용하지 않았다. Orca CLI는 지정된 전체 경로 `C:/Users/user/AppData/Local/Programs/orca/resources/bin/orca.exe`를 사용하며 version-matched 가이드를 읽었다. 초기 `/status` 경로 변환 오류 입력은 Director 정정대로 무시했다.

원본 `data/local`·5180/5181·실제 실행본/계정/세션/캐시를 읽거나 변경하지 않았다. 실제 사용자 경로는 계속 `C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe`다. 공개 fixture는 Backend의 이전 artifacts에서 재사용했고 계정 DB는 새 합성 입력으로 작성했다. SDK 실행 파일만 원본 `.tools/dotnet`에서 읽기 전용 재사용했다. 엔진/UI/QA 파일 수정, push, 새 Run/Dispatch/하위 워커, 배포 없음. package-lock.json SHA256 `2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767` 보존·커밋 제외.

## UI가 따를 확정 wire

전체 JSON/오류 계약: [single-deck-compute-contract.ko.md](single-deck-compute-contract.ko.md) 마지막 F2-B 절.

- `POST /api/runtime/skill-replays`, `POST /api/compute/experiments`: 최상위 `conditionProfile` 생략/`solo_raid`가 새 요청이다. combat 기본은 durationFrames=10800, pelletCoefficientPolicy=per_trigger, defenseMode=team_damage_threshold, enemyDefense=30925, critMode=sample. 시간·샷건·모드의 다른 명시값/null/잘못된 타입은400으로 거부한다. 자동 모드의 유효 정수 EnemyDefense는30925로 정규화하고 저장한다. 명시 크리·roundingPolicy 선택은 유지한다.
- 과거 조건 재실행은 최상위 `conditionProfile:"legacy"`를 명시한다. 당시 시간·샷건·크리·DEF를 보존하고 모드는fixed다. 구 저장본을 새 기본값으로 조용히 재해석하지 않는다. 신규 실행 UI에 legacy를 기본으로 넣지 않는다.
- skill replay 최상위 및 compute input에 `battleConditions`(profile,label,defenseMode,initialDefense,switchedDefense,damageThreshold,durationFrames,pelletCoefficientPolicy). 자동 label은 `덱 누적 피해에 따라 방어력 자동 전환`, fixed는 `이전 방식(고정 방어력)`. 기존 conditionCompatibility는 거리·약점 표시로 별도 유지한다.
- 구 저장본 표시용 GET `/api/runtime/skill-replays/{id}/battle-conditions`, `/api/compute/experiments/{id}/battle-conditions`. 모드 생략은fixed. 기존 replay GET/export를 재작성하지 않는다.
- 실제 전환 결과: replay `result.defense`, compute `runs[].defense`에 mode/initialDefense/finalDefense/damageThreshold/switchAfterHit. 전환이 없으면 switchAfterHit=null, 옛 compute 행에는 defense=null(미기록)일 수 있다. SwitchAfterHit는 frame/hitTraceId/hitOrdinal/characterId/effect/cumulativeDamage/previousDefense/newDefense다.
- 보스 목록: **GET `/api/presentation/solo-raid-bosses`**. schemaVersion1/defaultBossId=dummy/bosses/diagnostics/complete. bosses 원소는 id/name(한국어)/imageUrl/season. dummy는 imageUrl=null. 실제 이미지는 `/editor/assets/bosses/<불투명ID>.png`; 원본 hash를 파일명으로 노출하지 않는다.
- 선택은 두 POST의 **최상위 bossId**, 생략/null은dummy. 선택 당시 객체를 replay `boss`, compute `input.boss`로 저장한다. 미지원/제외 ID는400 `boss_id_unknown`. boss 표시 데이터와 이미지 catalog 버전은 계산 조건·fingerprint·튜닝 키에서 제외한다. 이름·이미지를 클라이언트가 임의 입력하는 계약은 아니다.

시간/샷건 오류 message는 `solo_raid_duration_fixed_10800`, `solo_raid_pellet_policy_fixed_per_trigger`. 새 모드 오류는 `solo_raid_defense_mode_requires_team_damage_threshold`, 과거 모드 오류는 `legacy_defense_mode_requires_fixed`, 미지원 profile은 `condition_profile_invalid`다. 기존400/409 및 손상 profile 진단을 유지한다.

## 엔진 후속 세 항목 연결

엔진은 구 입력 재현을 위해 DefenseMode 생략 시 fixed를 유지한다. Backend는 새 요청 경계에서만 team_damage_threshold를 명시하며 정규화 이전 JSON으로 타입/혼용을 검사한다. 저장 읽기·prepared 복원은 새 요청 정규화기를 통과하지 않는다.

`PreparedCompute.Create`의 DefPolicy는 fixed:<당시 DEF> 또는 `team_damage_threshold:30925:2000000000:31784`. 조건 전체의 defenseMode 및 skills/team5·cpu-summary4 버전이 fingerprint/캐시를 분리한다. `PreparedCompute.Run`은 엔진 summary.Defense를 Contracts.DefenseResult/DefenseTransition으로 옮긴다. nullable 추가 필드로 구 RunSummary를 계속 읽으며 DB JSON에 전환 증거를 보존한다. Analysis 산술은 수정하지 않았다.

다중 정책 WeaponReplay는 고정 DEF 참조 경로를 유지한다. 자동 모드 요청은400 `weapon_reference_requires_fixed_defense_use_skill_replay`; 자동 전투를 그 경로에서 흉내내지 않는다. 단일 hit 수동 검산도 기존 계약을 유지한다.

**경계 가설:** 팀 누적 >20억이 된 타격 자체는30925, 다음 처리 타격부터31784. ==20억은 미전환이며 같은 프레임 순서는 엔진 원본을 따른다. 실게임 확인 완료라고 주장하지 않는다.

## 보스 원천·한국어 목록·누락

준비 스크립트 `tools/data-pipeline/prepare_solo_raid_bosses.py`는 지정된 presentation root에만 공개 목록·이미지를 저장한다. enikk.app/soloraid의 실제 페이지가 호출하는 GraphQL soloRaidSummaries와 `/bosses/<monster_image>.png` 경로를 확인했고 시즌1~42를 받았다. 한국어 Accept-Language를 지정해도 요약 이름은 영어였으며 해당 GraphQL 필드에는 locale 인자가 없었다.

한국어 이름은 한국어 기사/공지 원문에서 추출하거나 한국어 공개 보스 catalog의 title 원문을 그대로 사용한다. 영문을 번역해 이름을 만들지 않았다. 원천은 다음 범위다:

- 한국어 솔로 레이드 첫 보스 기사: 마더 웨일. 같은 보스 식별의 시즌1/29에 대응.
- 한국어 이벤트 아카이브의 공식 계정 공지: 시즌41 리버렐리오 바디. 원문의 괄호 안 이름을 추출한다.
- 한국어 공개 NiDeck 보스 목록: 시즌35~40의 기존 기록 ID를 대응하고 title을 그대로 채택했다. 공개 페이지의 anonymous 읽기 API만 사용했고 로그인·개인 계정/덱 데이터를 조회하지 않았다. 테스트/Doro/중복 시즌 항목은 대상에 넣지 않았다.

원문 URL·원본 영문명·몬스터/한국어 원천 ID·원문과 PNG SHA256·선택 여부는 **내부 `solo-raid-bosses.manifest.json` 및 boss-sources/** 에만 있다. API 응답에는 출처/원본ID/영문명/hash 필드가 없다. 내부 파일은 정적 assets 바깥이며 HTTP 비노출을 확인했다. 참조 UI 출처 표기를 추가하지 않았다.

최종 준비 경로: `artifacts/fcond2/presentation-final/`. 실제 표시 대상은 **더미 + 9개 시즌(10카드)** 이다:

| 시즌 | 원천 한국어 표시 이름 |
|---|---|
| 41 | 리버렐리오 바디 |
| 40 | 사치스러운 거미 |
| 39 | 아일랜드 이터 |
| 38 | 애니힐리오 |
| 37 | 울트라(수냉솔레) |
| 36 | 에고비스타 |
| 35 | 크리스탈 챔버 |
| 29, 1 | 마더 웨일 |

시즌 **2~28, 30~34, 42 =33개**는 검증된 한국어 원천 매핑을 확보하지 못해 제외했다. 한국어 이름이 세상에 없다는 판정이 아니라 이번 준비 자료의 검증 범위다. API `complete:false`, 각 항목 `diagnostics:{id:solo-raid-N,season:N,code:korean_name_unavailable,displayable:false,message:한국어 이름 원천 미확인}`로 명시한다. 영어 대체/추측 번역은 없다. 이미지 실패는 boss_image_unavailable, catalog 미준비는 dummy만 + boss_catalog_not_prepared다. 이 부분은 Director 추가 지시의 명시적 누락 처리 경로이며 전체42개 한국어 완료로 보고하지 않는다.

```powershell
python tools/data-pipeline/prepare_solo_raid_bosses.py --presentation-root '<격리 dataRoot>/presentation'
```

Git 제외 파일이므로 merge만으로 배포되지 않는다. 원본 준비/배포는 Director의 별도 사용자 확인 단계다. 새 이미지는 불투명 파일명으로 저장해 기존 결과가 가리키는 이미지를 덮어쓰지 않는다. 원천 응답 자체가 실패하면 기존 공개 catalog를 교체하기 전에 실패한다. 개별 이름/이미지 미확보는 partial 목록과 진단으로 남는다.

## 사거리 표시 정리

사용자의 검증 완료 범위에 따라 combat-conditions catalog `gameVerified:true`, RL diagnostic `rl_zero_range_no_bonus`로 변경했다. rangeBonusAvailable=false 및 실제0–0 원천 값은 보존했다. 확인 범위는 캐릭터별 사거리 데이터와 RL0–0이며 전투 전체 검증을 뜻하지 않는다. 양끝 포함은 현 계산을 유지하고 이 문서·계약에서만 확인 대기로 둔다.

## 실제 검증

- 최종 Release 빌드 경고0/오류0. **.NET447/447**(Sync164+Compute46+Core196+Analysis41), 실패/skip0. 신규 Backend17개 및 통합 엔진22개 포함. 근거 `artifacts/fcond2/final-build.log`, `final-tests.log`, `final-tests/*.trx`.
- 보스 pipeline 단위 **4/4**: 한국어 원천만 표시·영문 fallback 금지·URL/hash 비노출, 이미지 실패 진단, 중복 시즌/이미지 경로 거부. `artifacts/fcond2/final-boss-tests.log`.
- 최종 실제 격리 API **passed**, 포트60672: `artifacts/boss-conditions/api/7c64553535d44ef2b137a53a80210b44/summary.json`. 새 합성 계정2개·이전 자체 공개 fixture 사용, source hash 변경0, snapshot 불변, 본인 자식 API만 종료했다. 원본/QA 계정·데이터는 재사용하지 않았다.
- 기본값 자동 모드·10800/per_trigger/sample 저장·조회, 한국어 목록10카드/33제외 진단, 실제9 이미지HTTP와 로컬 바이트/hash 일치, manifest 정적 경로404 확인. 보스 선택을 바꾼 두 실험의 피해·input fingerprint·튜닝 키 동일, 선택 메타데이터는 별개 저장; 두 번째는 validated_policy_cache 재사용.
- 자동 전환을 만드는 **공격력 가산 버프 rate=100(+10,000%) 합성 조건**(실사용 덱/실측 아님): frame1133, hitTraceId3804, hitOrdinal2011, 누아르(5009) normal_attack, 누적2,001,052,869에서 전환. 초과 타격 DEF30925 및 이후 타격31784. replay와 compute 전환 DTO/피해 동일, trace 없는 CPU summary 및 저장/조회 보존.
- 합성 자동 팀18,320,585,735 / fixed 팀18,322,249,418. 자동 fingerprint `acac04fb150d5eeee349418b78d55a686f94ec529079aceb01f0b327b585fe3d`, fixed `017305f25f19420bd172fbe70ea12f5a2d793c8f4b1b563e12377c77a881eda9` 및 튜닝 키 다름. 각 computeN=1의 기능 검사이며 성능·통계적 정확성 주장이 아니다.
- 구 bool·120프레임 명시 legacy replay 총1,586,529 및 전체 멤버 결과가 최초F-COND-B stage A와 정확 일치. 과거 형태 JSON(새 boss/battleConditions/defense 필드 없음)의 GET/export 바이트·파일 hash 불변, 표시용 endpoint는fixed/120프레임 보존. 기존 미설정/약점별 OL 후보·혼용400·이력 격리 회귀도 통과.
- 새 고정값/타입/모드·제외/미지원boss·weapon 자동 참조 **17개400**이며 replay 파일과 compute experiments/run 수 불변.
- B-FIX-2 손상 profile 회귀 **21종×5API=105/105 HTTP409**, 저장 없음, source hash 불변. `artifacts/boss-conditions/errors/afc131a67c6f4833accedac7582a6048/summary.json`. 새10800프레임 요청에서 검사했다.

최초F2 API 시도 `12ff1cc7...`는 합성 buff window 시작을0으로 써 엔진의 기존 시작≥1 제약에400으로 실패했다. 검사 입력을1..10801로 고쳤으며 제품/엔진 오류로 처리하지 않았다. 이후 `9f9455e2...`, `0f5ddb5a...`도 통과했으나 최종 근거는 위7c645535 실행이다. 마지막 실행은 불투명 이미지ID·실제HTTP·원문export까지 포함한다. 표본 수를 합산하지 않는다.

## 남은 범위·인계

확정 wire와 보고서·커밋을 Director 기존 터미널 재조회 후 한 번 인계한다. UI/QA에 직접 보내지 않는다. UI 실제 연결·독립 QA 재수용·원본 통합/빌드/이미지 준비/배포/실행 검증은 Director 후속이다. 한국어 이름33개 시즌 추가 확보, 실게임20억 경계 및 사거리 양끝 포함 확인은 미완료로 유지한다.
