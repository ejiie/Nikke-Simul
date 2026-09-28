# F-COND-Q 단계 1 — 독립 API 검수 (2026-09-28)

## 판정

**정상 공개 runtime의 API 경로 수용 통과, 단계 1 전체 수용은 불명 사거리 처리 결함 1건으로 보류.** 본 검사83/83, 추가 검사11/12(합계94/95). 엔진 경계 probe1253개와 실제 피해 로그2087히트 검산은 해당 검사 내부 사례 수이며95건에 중복 합산하지 않는다. 단계2 브라우저는 Director 통지 대기, Q-CPU-10K·부하·배포 보류.

Backend `796eec3bd4c6852c8dba7618c2b8584c142ad4c1`를 `1abba9b`에서 일반 merge했으며 ancestry가 이어져 fast-forward됐다. 기존 QA 이력과 미추적 package-lock 보존. Director 지시서 전체(기본값·최신 상태·F-COND-Q), Backend 보고서 전체 및 compute 계약 F-COND-B 절을 읽었다. Backend/엔진 검사 스크립트·테스트·golden·정답을 실행/import/기대값으로 사용하지 않았다. 제품 수정 없음.

## 독립 기준과 격리

- 자체 `check_boss_conditions.py`, `check_conditions_supplement.py`, `ConditionBoundary`만 작성했다. 공개 roster 원문을 직접 그룹화하고 캐릭터별 min/max/속성으로 기대값을 생성한다. 지정된 제품 준비 도구 `prepare_combat_conditions.py`는 **검사 대상 데이터 준비용**으로 실행하며 그 집계 함수를 기대값 생성에 쓰지 않는다.
- roster는 `docs/p03-source-manifest.json`의 공개 `Nikke-Dmg-Simulator/Database/raw/blabla_roledata.json`, SHA256 **8568963a75d971cf97489be79bf6f81829bf4e20fdccc74ed10b28159c304348**. 추가 수집/네트워크/게임 파일 접근 없음.
- 공개12파일은 자기 기존 `load1000-3db71912a601/data` allowlist에서만 복사했다. 새 계정DB·합성5인(리타/블랑/앨리스/누아르/모더니아), OL 후보용 각자 T10머리·공격력1줄을 생성했다. 원본 계정/세션/캐시 복제 없음.
- 기존 자기 Q-F32 B1/B2 API Release DLL을 `artifacts/single-deck-qa/cond-stage1/baseline-api/`에 보관한 뒤 새 API를 빌드했다. **같은 새 합성 계정으로 전환 전 API를 직접 실행**해 baseline을 얻었다. Backend 보고 숫자를 정답으로 대입하지 않는다. 이전 summary2와 새 summary3는 실제 응답에서 확인했다.
- 새 API 및 자체 boundary probe Release 빌드는 각각 경고0/오류0. 증거 `cond-stage1/api-build.log`, `boundary-build.log`, `baseline-dll-hashes.json`.
- 피해 기대값은 기존 자기 Fraction→binary32 독립 산술로 계산했다. 각 로그의 거리/속성 bool을 그대로 믿지 않고 roster와 조건에서 재계산하여 덮어쓴 뒤 피해를 구했다. 다른 공격력·스킬 입력은 로그에 기록된 값을 소비하므로 스킬 계수 원천 전체 정확성까지 독립 입증한다는 뜻은 아니다.

## 정상 runtime 수용 결과

| 항목 | 독립 결과 |
|---|---|
| runtime 준비 | 이전 catalog/hash/graph 보존, 새 current ID **9c98c91c6df670a35c9a2da0446961a61141cb5be19ca9718e608120608e71cd**. 재실행 동일 ID. 옛 runtime은 catalog 조회409 combat_profile_catalog_missing, 구 bool replay는 유지 |
| 원천 집계 | 192명 전체 prepared min/max/속성/무기와 원문 일치. API6무기군·모든구간·구간별ID/count·대표구간·예외 독립 집계 일치. SR 하란5042의25–45, RL41명의0–0 보존 |
| API 멤버 | 요청 역순의5인 순서·원천 필드 일치. 미보유/중복/6인400. 원소5종·출처hash·gameVerified=false·양끝포함/normal 규칙 표시 확인 |
| 경계 | 실제 지원5인 API에서 min−1/min/max/max+1 중0–100 유효값18조건 검증. 모든192명 원천의 경계·normal/비normal·SR예외·RL0–0 및 range/element unknown을 자체 C# resolver 호출1253사례로 별도 확인(엔진 tests 재사용 없음) |
| 멤버별 피해 | 거리35/Fire, 각멤버1200프레임 로그: 360/190/9/300/1228 = **2087히트**, 비normal614 포함. 거리normal만·속성일치 모든피해의 flag와 독립 binary32 피해 모두 일치 |
| 구 bool replay | 새롭게 얻은 이전 API와 새 API의 멤버 결과 전체·선택 로그 정확 일치. 합성120프레임 총1,847,281. 구 GET=export=당시 JSON, 호환조회 legacy_global/이전 방식/true값 유지, 파일hash 불변 |
| 구 bool batch | 이전 실제 정상1행과 새조건재실행의 팀1,847,281·멤버결과 정확 일치. 이전결과 원형조회 유지, resume409 engine_or_rules_version_changed. 호환조회 legacy_global |
| 명시 null | 두 boss 필드 null이면 per_member 저장/조회 유지, 보너스없음. 별도 구 bool false/false replay와 동일 피해지만 모드는다름. compute도 피해같음/입력fingerprint·튜닝키다름 확인 |
| fingerprint/cache | legacy true·null·35Fire·35Water·45Fire의5조건 fingerprint/튜닝키 모두다르고 첫miss, 같은35Fire 재요청 validated_policy_cache. source runtime 및 rules 버전 분리 |
| 통계/복구 | 각조건 정상1행, 독립 팀·멤버 통계(n/평균/분위수/컷Wilson) 대조. 튜닝은n미포함. API재시작 후5배치 원결과 그대로, 팀=멤버합. snapshot JSON 불변 |
| OL 후보 | IncElementDmg:35Fire/45Fire는앨리스·모더니아만, null/Water는0명, legacy true는5인. roster 속성에서 기대집합 생성 |
| 오류 | replay/compute 각각9조건=18회400: −1/101/소수거리, Electric/fire/빈속성, null새필드+false구bool, 실제값혼용. 자동절삭/조용한fallback 없음 |

| 새 compute 조건 | 실제 팀 피해(n1) |
|---|---:|
| 이전 bool true/true | 1,847,281 |
| 새 null/null | 1,304,192 |
| 거리35 / Fire | 1,508,042 |
| 거리35 / Water | 1,464,917 |
| 거리45 / Fire | 1,499,514 |

모두120프레임·레벨400·DEF30925·crit off·CPU worker1의 합성 기능검사다. 이전baseline1+새5조건+반복1+추가legacy-off1=정상compute8행, 튜닝호출은별도. replay도120/1200프레임만 사용했으며 성능/개선율/실사용자덱 결론을 내리지 않는다.

## F-COND-Q-1 — 누락 min을0으로 추정 (수정 담당 F-COND-B)

**최소 재현(자기 격리 runtime만):** 정상 prepared catalog 복제본에서 `combatProfiles.characters.5004.bonusRangeMin` 키 하나를 제거한다. JSON 내용의 SHA256으로 새 runtime ID를 만들어 별도 디렉터리에 저장하고 자기 current 포인터만 바꿔 API를 시작한다. 원래 정상 catalog는 편집하지 않는다.

1. `GET /api/snapshots/synthetic-compute/combat-conditions?characterIds=5004` → **200**, Alice SR `bonusRangeMin:0,bonusRangeMax:100,element:Fire`.
2. `POST /api/runtime/skill-replays`, 합성5인/400/120프레임/DEF30925/거리35·Fire → **200**, 저장ID `11e46b0fd58840acbb50c12d4f9294a0`.
3. 실제 공개 원천의 Alice 범위는45–100이다. min이 없을 때 불명 오류를 내야 하나0–100으로 조립해 계산을 허용한다.

원인: `src/Nikke.Contracts/CombatConditions.cs`의 `CombatMemberProfile`은 min/max를 non-nullable int로 받고, `src/Nikke.Data/CombatProfileCatalog.cs:21`의 Deserialize가 누락 min을0으로 만든다. 후속 검사(`min<0`, `max>100`, `min>max`)는 이0을 유효값으로 통과시킨다. 엔진 resolver의 nullable unknown 검사는 typed profile에서 이미0으로 채워진 뒤이므로 누락을 알 수 없다.

**영향·경계:** 고정 공개 roster와 정상 prepare 도구가 만든 이번192명에는 누락이없고, 정상 입력 결과는 전부통과했다. 이것은 **유효hash를 가진 비정상 runtime**의 방어 경로 검증이며 실제 배포 runtime이 손상됐다는 주장이나 게임 데이터 문제는 아니다. 하지만 배정의 "사거리/속성 불명은 추정하지 않고 오류" 조건을 만족하지 않으므로 전체 수용은 보류한다.

동반 관측: max누락·element누락은 양 API에서500(빈응답)으로 거부됐고, 멤버전체누락은400 `combat_member_profile_missing:5004`였다. 추가검사의 해당2개 PASS는 **계산허용이없음**만 뜻하며 구조화된 불명 진단 수용이 아니다.

**수정 수용 조건:** F-COND-B가 역직렬화 전 필수 필드 존재·JSON 타입을 확인하거나 nullable/required 계약으로 누락을 보존하여 명시 오류를 반환할 것. min/max/element 누락·null·잘못된 타입은 조회/replay/compute 모두 계산·저장 전에400/409의 식별 가능한 진단으로 거부하고 값0/다른속성을 채우지 말 것. 유효 SG min0·RL0–0·SR예외·모두null조건 및 구 bool 경로는 유지할 것. 정상 고정 원천 회귀와 이최소재현으로 독립 재수용 필요. QA는 제품을 수정하지 않았다.

## 근거·재현·보존

최종 근거 루트: **`C:/Users/user/orca/workspaces/Nikke-Simul/검수/artifacts/single-deck-qa/conditions-cc81af4fb37e/`** (Git 제외).

- `summary.json`83/83, `http.json`, `catalog-api.json`, `prepare-output.json`, `resolver-cases.json`/`resolver-results.json`1253사례.
- `old-replay.json`, `new-legacy-replay.json`, `old-batch.json`, `mixed-<id>.json`2087히트, `empty-replay.json`.
- `batch-*.json`, `batch-map.json`, `ol-*.json`, `legacy-off.json`.
- `supplement-summary.json`11/12, `supplement-http.json`, `malformed-bonusRangeMin.json` 및 나머지3결함주입파일, `preservation.json`.
- malformed min runtime ID `31d3772ddf4ddabc46f25e0585f1a6396adc0b851becf341ca0c02c8d797c527`. 모든 주입 후 current를 정상9c98c91c…로 복원했다. 별도 버전 디렉터리는 재현 근거로 남긴다.

재현: 이전 QA API DLL baseline을 자기 artifacts에 보관한 상태에서 현재 API와 `ConditionBoundary.csproj`를 Release 빌드한 뒤 `python tests/single_deck_compute_qa/check_boss_conditions.py --dotnet <dotnet.exe>`, 이어 `python tests/single_deck_compute_qa/check_conditions_supplement.py --run <새근거루트> --dotnet <dotnet.exe>`. 전자는exit0, 후자는 위min누락1건으로exit1. 준비된 baseline이 없으면 다른 작업공간/원본에서 자동으로 가져오지 않는다.

본 API56881/PID14888·33592·22020, 추가API52496/PID23932·2712·14200·34300·21848 모두 자기프로세스 종료·wait 완료. 공개12파일·roster hash 불변, snapshot JSON 불변, 정상runtime포인터복원. package-lock SHA256 `2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767` 보존·커밋제외. 제품 직접수정0, 원본 data/local·계정/세션/캐시/EXE·5180/5181 접근/변경/종료 없음. 타worktree 편집·push·배포·새worker/Run/Dispatch/lifecycle 없음.

**미완료:** F-COND-Q-1 수정·재수용, UI단계2, 실게임의 양끝포함/RL0–0 가설·실측 정확성, 실제 사용자덱·부하/성능·EXE 배포. RL/SR예외의 전체전투 API 지원을 확대한 것으로 판정하지 않는다(원천/API목록+엔진경계 범위). Director에게 커밋/보고서/독립근거/조건별 판정을 한 번 전달 후 대기한다.
