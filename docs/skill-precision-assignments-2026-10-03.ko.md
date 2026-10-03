# 스킬 조립·계산 정밀도 후속 배정 (2026-10-03)

## 근거

[2026-10-03 사용자 결정](user-decisions-2026-10-03.ko.md): (1) SSR 니케 우선, '묑카엘' 계정 전투력 높은 순으로 스킬 조립 시작, (2) "B는 float32, 곱은 double" 구조 추가와 그 외 정밀도 작업, (3) 통계는 대미지 확정 뒤. 공격력 버프 반올림은 사용자 확인으로 **115**(100 × 14.5% → 14.5 → 15, 사사오입)가 맞다 — 현재 `long` 공격력 조립과 일치.

## 공통

[작업 구조](workflow-implement-review.ko.md)를 따른다: 구현(sonnet-5.5) ⇄ 리뷰(astra-6) 직접 왕복 → 리뷰 최종 통과만 Director → 독립 QA → Director 통합·배포. 차단 7항목, 반려 2회 초과 시 Director. 원본 `data/local`은 공개 게임 데이터 표(`game-catalog.json`·`calculation/*`·`runtime/*`)만 hash 전후 기록 조건으로 읽기 허용, `accounts.db`·세션·캐시·presentation·5180/5181·원본 EXE 불변. 미추적 `package-lock.json` 커밋 금지, push·배포·새 워커 금지. 기준 커밋: Director `e48ffd6` 이후 HEAD(= 배포본 `a03c5a9` + 문서). 먼저 자기 브랜치에 일반 merge한다. 모듈 구문은 `node --input-type=module --check`로 확인한다(UI 변경 시).

## S-SKILL-1 — SSR 스킬 조립 1차 (엔진 worktree)

- 구현: `시뮬레이션-엔진-담당` Sonnet `term_1fba2b21…`(high), 리뷰: astra `term_ec372feb…`. 사고 수준: 구현 high(사용자 세션 설정) / 리뷰 medium / QA xhigh.
- 대상 순서: '묑카엘' 계정 SSR 전투력 순(Director 추출 목록 Git 제외 `artifacts/director/roster-20261003/ssr-by-cp.json`, 보유 SSR 164명). 이미 엔진에 있는 5명(앨리스·모더니아·리타·누아르·블랑)은 제외.
- **1차 묶음(전투력 상위 미구현 5명):** 스노우 화이트(#5012, 전투력 971,073, 3버·assault_rifle), 라피 : 레드 후드(#5129, 전투력 909,193, 3버·machine_gun), 맥스웰(#5001, 전투력 843,710, 3버·sniper_rifle), 홍련 : 흑영(#5105, 전투력 810,966, 3버·rocket_launcher), 신데렐라 : 크리스탈 웨이브(#5175, 전투력 802,384, 3버·machine_gun). 사용자 실측 단서가 있는 스노우 화이트를 먼저 한다.
- 원칙(P03와 같음): 원천(CharacterSkillTable·FunctionTable·무기 표)에서 스킬·효과를 조립하고, 엔진이 아직 지원하지 않는 효과 타입은 **생략하거나 추정하지 말고 "미지원"으로 명시**한다(결과 진단에 표시). 캐릭터별 지원 상태 표(스킬 1·2·버스트별 효과, 지원/부분/미지원, 근거 ID)를 보고서에 남긴다. 필요한 새 효과 타입은 일반화해 구현하고 단위 테스트를 붙인다. 계산 정책·정수화·같은 프레임 순서를 바꾸지 않는다.
- 결과가 바뀌는 범위: 새 캐릭터 추가는 기존 5인 결과를 바꾸면 안 된다(회귀: 기존 5인 180초 결과 동일). 규칙 버전은 새 효과 타입이 기존 계산에 영향이 있을 때만 올린다.
- 보고서 `docs/ssr-skill-batch1-engine.ko.md`. 묶음이 크면 캐릭터 단위 커밋으로 나눠 리뷰에 넘겨도 된다.

## E-PREC-1 — 계산 정밀도 후속 (통계 worktree, 임시 소유)

통계 작업이 대미지 확정 뒤로 미뤄져 이 짝이 비어 있으므로 맡긴다. **이번 작업에 한해** 아래 Core/Engine 파일 소유를 준다. 스킬 조립(S-SKILL-1)과 같은 파일을 건드릴 수 있으므로 변경은 최소로 하고, 겹치면 merge로 해결한다.

- 구현: `덱-육성-최적화-및-통계-담당` Sonnet `term_80f56a78…`(high), 리뷰: astra `term_69b188e0…`. 사고 수준: 구현 high / 리뷰 medium / QA xhigh.
- 소유(임시): `src/Nikke.Core/Combat/**`(HitCalculator·ClientFloatDamage), `src/Nikke.Core/Stats/**`(장탄 조립), `src/Nikke.Engine/Skills/SkillReplay.cs`의 히트 입력 구성 부분만, Core/엔진 테스트, 보고서 `docs/precision-followup-engine.ko.md`.

1. **새 비교 정책 `client_f32_dprod`**: 공격력 `long` 조립 → B는 float32 누적(현행과 같음) → **base·extra·감소·방어율·속성과의 곱셈 사슬은 double** → 최종 사사오입·max(1)·long. 근거: SW 관측 피해 3개가 모두 float32로 표현 불가능한 정수([결정 문서](user-decisions-2026-10-03.ko.md) 3-2). 기본 정책은 바꾸지 않고 **비교 후보로 추가**한다(1-tick 대조 후 사용자가 선택). base 내부(`(attack−defence) × damageRatio × statDamageRatio × charge`)와 extra 계산의 자료형도 후보 정의에 명시한다. 독립 기대값 테스트(분수 산술 + float32 B)와 "결과가 float32 표현 가능하지 않을 수 있음"을 확인하는 테스트를 넣는다.
2. **방어율(`defenceRatioRate`) true damage 예외:** true damage 타입은 `(1 − defenceRatioRate)`를 적용하지 않는다(사용자 확인: 최종 10, 방어율 60% → 일반 4, true 10). 모든 정책에 반영.
3. **저지(96)·파츠(112) 분리:** HitContext에 저지 판정·저지 증가량 입력을 추가하고 `breakRate = 1 + 저지 증가`, 파츠는 `addDamageRate` 쪽으로. 현재 런타임이 96을 `InterruptionTarget`에서 `AttackDamage`에 넣는 중복을 제거한다(H-SRC 근거). 저지 대상이 아닌 경우 결과가 바뀌지 않음을 회귀로 확인.
4. **장탄 조립 `long` 전환:** 최대 장탄 = 기본 + Σ round(기본 × 동일 비율 × 개수)를 공격력과 같은 정수 경로로(1/10000 원천 보존, 사사오입, checked). 결과가 바뀌면 규칙 버전 상향·fingerprint 분리.
5. 결과가 바뀌는 항목(2·3·4)은 기존 5인 180초 전후 비교를 보고한다. 1은 기본값 변경이 아니므로 기존 결과가 같아야 한다.
- API/UI에 새 정책 선택지·저지 입력을 노출하는 것은 이번 범위가 아니다(필요 시 후속 배정). 단일 히트 API 계약에 영향이 있으면 보고만 한다.

### E-PREC-1 진행

- **리뷰 1차 반려(`c7b6c83`, 2026-10-02):** (a) 소유 밖 연결 변경 범위 확인 없음 → Director 판단 요청, (b) 보고서 71행 — 요구 5의 기존 5인 180초 전후 비교가 다른 합성 멤버 fixture로 대체됨. 빌드·테스트 235/235, 버전·fingerprint 연결 확인. legacy 정책의 방어율 비모델링 유지는 비차단.
- **Director 판단(범위 예외 승인, 이번 작업 한정):** WeaponReplay.cs 장탄 조립 호출 2곳·client 정책 분기·버전, PreparedSkillReplay·TeamBurstController 버전 각 1줄, SkillReplay 히트 입력 외 SyncGun/정책 허용·분기·버전, 기존 `hit-damage-client-f32`·`hit-damage-client-formula`·`hit-damage-source-investigation` 문서 동기화. 조건: 연결·버전 외 동작 변경 금지, 문서는 이번 구현 사실만 반영하고 기존 기록은 정정 표시, 소유 밖 변경 목록을 보고서 표로, S-SKILL-1과의 Engine 충돌은 Director 통합 때 merge. (b) 반려는 유지 — 계정 접근 없이 공개 표/합성 스탯으로 리타·블랑·누아르·앨리스·모더니아 5인 비교 보완.
- **리뷰 최종 통과(2026-10-02):** HEAD `2b16883`(구현 `c7b6c83`), 반려 1회 해소. 5인 180초 4시나리오×기존 정책 2×seed 5 전후 일치, 공개 표 12개 hash 불변, Core 235/235, 버전·fingerprint 확인. 비차단: 보고서 "dprod 차이 0"은 base 시나리오 한정(OL .145 seed1 772,905,797 vs 772,905,689 등 차이 있음).
- **QA 배정(2026-10-02):** 검수 `term_234e279b…`, B-DATA-1과 순서대로(E-PREC-1 먼저). 착수 확인.
- **QA 최종: 통과, 1,106/1,106, 제품 차단 0.** 검수 `6bb1be2`(Director `3b19b4c` + 대상 `2b16883` 병합 `ca0e096`), [QA 보고서](C:/Users/user/orca/workspaces/Nikke-Simul/검수/docs/precision-followup-qa.ko.md), 증거 검수 `artifacts/single-deck-qa/precision1/evidence-index.json`. 독립 Fraction binary32/64 산술 1,003검사, 기본 `client_f32` 구 결과 264건 동일, dprod 결과 중 float32 비표현 정수 161건. 방어율 true 예외·96/파츠 분리·96 중복 제거·장탄 raw/10000 사사오입 checked 통과. 기존 5인 180초 40개 결과 전후 동일. 실제 API 27검사(구 결과 조회 보존, 구 resume 409, fingerprint 분리). 공개 표 12개 hash 동일.
  - 비차단 문서 정정(QA 보고서에 정확한 범위 기록): (1) "dprod 차이 0"은 base·저지 조건 한정 — OL .145 seed1 client 772,905,797 vs dprod 772,905,689(−108) 등 5시드 모두 차이, "2^24 이상에서만 차이"로 일반화 불가. (2) "dprod API 미노출"은 단일 히트 API(400)에만 맞고, replay/compute에 정책을 명시하면 실제 실행된다(승인 범위의 SkillReplay 정책 연결 결과). UI 선택지는 없다.
- **Director 통합:** `6d83dec`(`--no-ff`, 제품 트리 = QA `6bb1be2`). Release 빌드 경고 0·오류 0, .NET 486/486(Analysis 41·Sync 164·Compute 46·Core 235), UI 7/7. → **2026-10-04 원본 배포 완료**([배포 기록](desktop-release-original-2026-10-04.ko.md)).

## B-DATA-1 — 보스 StaticData 속성 (Backend worktree)

- 구현: `Backend` Sonnet `term_9d9ce9f4…`, 리뷰: astra `term_ed5e9c16…`. 사고 수준: 구현 high / 리뷰 medium / QA high.
- 사용자 안내: 보스 데이터는 StaticData에 있다. 동적 패턴(행동 트리·보스 함수·타임라인·거리 변화)은 사용자가 별도로 제공하므로 **이번 범위가 아니다.**
- 할 일: 솔로 레이드 시즌 1~42 보스(기존 보스 목록 ID와 연결)의 정적 속성 — 약점 속성, 방어력, **방어율(`DefenceRatioRatio` 후보)**, 파츠·코어 구성, 레벨 — 을 StaticData에서 찾아 버전 고정 카탈로그로 준비하는 스크립트와 읽기 API(표시용). 원천 위치·필드·단위·신뢰도를 보고서에 표로 남긴다. 확인 못 한 필드는 추정하지 않고 "미확인". 보스 선택은 아직 **계산에 반영하지 않는다**(표시·데이터 준비만).
- 보고서 `docs/boss-static-attributes-backend.ko.md`.

## D-SRC-1 — 니케 원천 갱신 (Backend worktree, B-DATA-1 뒤)

배경: 위 "원천 3종 출처 확인". #5175 이후 니케를 조립하려면 blablalink roledata 로스터를 새로 받아 `skill_chains`·`roledata_clean`을 다시 만들어야 한다. 사용자 지시 "진행"(2026-10-03).

- 구현: `Backend` Sonnet `term_9d9ce9f4…`(high), 리뷰: astra `term_ed5e9c16…`(medium), QA high. **B-DATA-1 리뷰 통과 뒤 착수**(같은 짝 직렬).
- **레거시 저장소 불변:** `C:/Users/user/Documents/GitHub/Nikke-Dmg-Simulator`에는 사용자의 미커밋 변경이 있고, Nikke-Simul `prepare-legacy.ps1`이 그 파일들의 hash를 고정 검사한다. 레거시 `Database/**`를 덮어쓰거나 그 저장소에서 Git 조작을 하지 않는다. 레거시 스크립트는 읽기/호출만 하고 출력 경로는 Nikke-Simul 쪽 Git 제외 위치(예: `artifacts/sources/<snapshot-id>/`)로 돌린다(필요하면 Nikke-Simul `tools/data-pipeline`에 래퍼 작성).
- **범위 갱신(2026-10-02):** blabla 수집·StaticData 받기·해독은 Director가 끝냈다(아래 진행). D-SRC-1은 그 산출물을 입력으로 **제품 파이프라인 반영**만 한다: EpinelPS 스키마 기반 디코드를 Nikke-Simul `tools/data-pipeline`에 자체 완결형으로 옮기고(스키마 출처·커밋 기록), 새 snapshot(`blabla-20261002`·`staticdata-20261002`) hash를 manifest에 추가, 새 원천으로 `skill_chains`·`roledata_clean` 재생성(니케 범위는 새 로스터), 기존 고정 원천 재현 유지, 니케별 diff 보고. 보스 카탈로그 시즌 41·42 채우기도 함께(B-DATA-1 후속). 아래 원래 할 일 목록 중 수집 단계는 완료된 것으로 본다.
- 할 일:
  1. blablalink 공개 roledata(`sg-tools-cdn.blablalink.com`, 로그인 불필요) 새 스냅샷 수집 → `roledata_clean` 정규화.
  2. 니케 범위를 새 로스터로 `skill_chains` 재조립. StaticData 입력은 기존 decoded 표(7/8)를 그대로 쓰고, 새 로스터 중 StaticData에 없는 니케는 "StaticData 미수록"으로 목록화(추정 금지) — 이 경우 사용자에게 StaticData 갱신을 요청한다.
  3. **기존 고정 원천과 새 원천을 나란히 둔다**: 새 snapshot id·hash를 별도 manifest 항목으로 추가하고, 기존 p02/p03 manifest·runtime catalog(`9c98c91c…`) 재현은 그대로 통과해야 한다. 기존 192명 항목이 새 원천에서 달라지면 니케별 diff를 보고(조용히 교체 금지) — 기본 원천 전환은 Director 결정.
  4. 보고서 `docs/source-refresh-backend.ko.md`: 출처 URL·수집 시각·hash·추가 니케 목록(name_code·이름·버스트 단계)·기존 대비 diff·StaticData 미수록 목록.
- 원본 `data/local`·5180/5181·원본 EXE 불변, `package-lock.json` 커밋 금지, push 금지.
- 후속: S-SKILL-1 2차 묶음(#5175 포함)은 이 결과로 원천을 고정한 뒤 배정한다.

### 진행 (2026-10-02, Director 직접)

사용자 지시: "blabla에서 정보를 가져오는 코드를 실행하여 data를 최신화. StaticData는 EpinelPS 탐색".

1. **blabla 최신화 완료:** 레거시 `getFromBlaLinkRoledata.py`를 출력 경로만 바꾼 래퍼로 실행(레거시 `Database/raw` 불변). 결과 Git 제외 `artifacts/sources/blabla-20261002/` — `blabla_roledata.json` `2e781192…`, `blabla_roledata_full.json` `5d40ffa5…`. 202/202명 수집, 실패 0.
   - 추가 10명: #3019 Aigis(SR), #5175 신데렐라 : 크리스탈 웨이브, #5176 Marciana: Marine Study, #5177 Laplace: Ultimate Hero, #5178 Maxwell: Ordinary Mechanic(2버), #5179 Queen (Makoto), #5180 Yukiko, #5181 Drake: Great Villain, #5182 Guilty: Mighty Bunny, #5183 Sin: Swift Bunny. 삭제 0.
   - 기존 184명 차이는 대부분 설명 문구. **수치·함수 변화:** #5105 홍련 : 흑영 skill1 계수 3개·burst 계수 1개 약 +13%(예: skill1 lv10 250.47 → 283.03, burst lv10 150.12 → 169.63), #5107 엘레그 계수·`skill_value_data`, #5166 `skill_value_data`, #5002·#5121·#5122·#5154 burst 함수 ID 목록, #5096 무기(shot). 
   - **1차 묶음 영향:** #5105가 구버전 수치. S-SKILL-1 구현에 고정 원천으로 계속하되 보고서에 "원천 7월판, 최신 수치와 다름" 명시·계수는 원천에서 읽는 구조 유지를 전달(대기열 입력, 답장 불필요). 나머지 4명은 문구만 차이.
2. **StaticData — EpinelPS 탐색:** `EpinelPS/EpinelPS`(C# NIKKE 사설 서버, AGPL-3.0, 최신 커밋 `17eb33f` 2026-09-23 "update to 152.8.13").
   - `EpinelPS/gameconfig.json`: 현재 StaticData 팩 `data/qa-260917-09c/566822`(2026-09-17 빌드) URL·salt 2개. 레거시 보유분은 `qa-260611-06b/536334`(6/11) → 약 3개월 뒤처짐.
   - 팩 받기·복호 방식(로비 `get-static-data-pack-info-mpk` → PBKDF2 → AES-CBC → zip `data` → AES-CTR)은 레거시 `DataPipeline/crawler/getFromNikkeStaticData.py`(NikkeTools 출처)와 같다. 레거시 스크립트로 최신 팩을 받을 수 있다.
   - **가장 큰 가치 = 표 스키마:** `EpinelPS/Data/JsonStaticData.cs`에 MemoryPack 레코드 클래스 874개(필드 순서·타입). 레거시 디코드 필드와 비교하면 Function·CharacterSkill·Character·StateEffect·SkillInfo·MonsterParts·MonsterStatEnhance는 이름 표기만 다르고 순서·개수 같음. **`MonsterRecord`에 `DefenceRatioRatio`(= 방어율 후보)가 `AttackRatio` 뒤에 새로 끼어 있다** — 레거시 위치 기반 디코더로 새 팩을 읽으면 MonsterTable 이후 필드가 밀린다. 새 팩 디코드 시 EpinelPS 스키마로 표 정의를 갱신해야 한다. B-DATA-1의 방어율 필드 근거로도 쓴다.
   - 상태: **라이브 서버에서 팩 받기는 레거시 정책상 사용자 명시 승인 후에만 실행**(복호 산출물 커밋·재배포 금지, 로컬 전용). → 사용자 승인("StaticData 받기. 그리고, 해독하여 정보 추출.") 후 실행 — 아래 3.
3. **StaticData 받기·해독 완료(2026-10-02):** 레거시 `getFromNikkeStaticData.py`를 출력 경로만 바꿔 실행 → 팩 `data/qa-260917-09c/567891`, 복호 `StaticData.zip` `00f1f611…`(17,491,305바이트), Git 제외 `artifacts/sources/staticdata-20261002/`.
   - 해독: Director 임시 디코더 `artifacts/sources/tools/decode_staticdata_epinel.py`(EpinelPS `JsonStaticData.cs` `17eb33f` 사본을 스키마로 파싱, 선언 순서·enum int32·DateTime int64, 레코드마다 멤버 수 일치·버퍼 끝 강제). 결과 `decoded/` — **8,949개 표 성공, 실패 0**, 스키마 없음 619(필드 맵 241 등 이벤트·맵 표, 전투 무관).
   - 전투 표 전부 정상: Function 21,254(기존 19,459 → 추가 1,795, `function_value` 변경 35), Character 1,996행(name_code 209 — blabla 202명 전원 포함), CharacterSkill 4,667, StateEffect 5,429, SkillInfo 9,810, CharacterShot 273, CharacterStat 75,600, Monster 2,204, MonsterParts 715, MonsterStatEnhance 35,552, MonsterSkill 5,231, WaveData 167개, SoloRaidManager 43행(**시즌 41·42 포함**), SoloRaidPreset 336.
   - **방어율 `defence_ratio_ratio`:** 몬스터 2,201개 0, 비0은 같은 이름의 테스트성 몬스터 3개(3000·11000·−1000)뿐. 솔로 레이드 보스는 전부 0 → B-DATA-1의 8/12판 값 0과 일치.
   - 이 디코더는 Director 탐색용이다. 제품 파이프라인 반영(스키마 고정·manifest·테스트)은 D-SRC-1에서 한다.

### B-DATA-1 진행

- **리뷰 최종 통과(2026-10-02):** Backend HEAD `2c41185`(구현 `cd4caba`, 문서 `403b37b`), 반려 1회(선언된 null 보존·미선언 null 거부, 중첩 수치 strict) 해소. Sync 187/0, Python 17/0. 계산 경로 변경 없음. 한계: 시즌 41·42 unavailable(8/12판 원천에 없음).
- **Director 판단(보고서 핵심 결과 2):** 바탕 화면 8/12판 StaticData 읽기 전용 디코드는 사후 수용(다운로드 없음, hash 기록). **방어율 원값 0 유지** — 9/17판에서도 솔로 레이드 보스 전부 0으로 확인. 단위·적용 조건은 계속 미확인으로 둔다. 시즌 41·42는 9/17판에 있으므로 D-SRC-1에서 새 원천 고정과 함께 채운다.
- **QA 배정(2026-10-02):** E-PREC-1 다음 순서로 같은 검수 세션.
- **QA 최종: 차단 2유형.** 검수 `e6295ca`(제품 병합 `0c26d1c` = E-PREC QA `6bb1be2` + Backend `2c41185`), [QA 보고서](C:/Users/user/orca/workspaces/Nikke-Simul/검수/docs/boss-static-attributes-qa.ko.md), 1,419검사 중 1,411 통과·8 실패.
  - **BD1-Q-1:** `unconfirmed=[]`인데 `element=null` 또는 `element.weakKey=null` 단독 주입 → GET 200(선언 없는 null은 409여야 함). `SoloRaidBossCatalog.cs:63,67`.
  - **BD1-Q-2:** 컬렉션 요소 null 주입 → `bosses[0]`·`challenge.levelChange.steps[0]` 500 NullReferenceException, `parts[0]`·`ladder[0]`·`diagnostics[0]`·`fields[0]` 200으로 null 반환(손상 입력 409 계약 위반). `SoloRaidBossCatalog.cs:35,53,69`.
  - 통과: raw-wire 판독 340/340, strict 중첩 수치 243/243, 실제 0·선언된 null 보존, 방어율 0·시즌 41/42 unavailable, 기존 보스 목록 바이트·계산 입력·fingerprint 불변, 기존 5인 60건 동일.
  - **Director 조치:** Backend 구현에 D-SRC-1보다 먼저 별도 커밋으로 수정 지시(객체·컬렉션 요소 검사 공통화, 8개 주입 + 같은 유형 회귀), 리뷰 직접 왕복 → Director → QA 재배정. 세 건 동시 배포는 이 수정 QA 통과 후.
  - **수정 리뷰 최종 통과:** Backend `a050853`(부모 `b8951ca`). element·weakKey 미선언 null 거부, `StrictGraph`가 도메인 검증 전에 전체 그래프의 non-nullable 멤버·컬렉션/딕셔너리 null 요소를 공통 거부(500 경로 제거). 회귀: 컬렉션/객체 null 12경로, 미선언 null·키 누락 29경로, 선언 null 7경로. Sync 231/231, Python 18/18. **계약 변경:** `challenge.levelChangeGroupId` 필수 — 이전 준비 파일은 409, 재준비 필요(배포 시 준비 스크립트 실행 여부 확인). D-SRC-1 미추적 파일과 분리됨.
  - **재QA 전달(2026-10-02):** 검수 착수 확인.
  - **재QA 최종: 통과, 1,682/1,682, 차단 0.** 검수 `9ee11a7`(대상 `a050853`을 `e6295ca` 위 merge `7f961fe`). 원래 8개 주입 전부 409 `boss_attributes_invalid`, 확장 null 매트릭스·`source.entries` dictionary null 포함, 실제 API 545검사 HTTP 500 0, 선언 null·실제 0 200 보존, 기존 5인 60건 동일.
  - **배포 조건(QA):** 이전 준비 파일은 409 → 배포 때 `prepare_solo_raid_boss_attributes.py --static-data-zip <고정 8/12 ZIP> --presentation-root <배포 dataRoot>/presentation` 실행 필수. Git/DLL 통합만으로 준비되지 않는다.
  - **Director 통합 `1d01ed8`**(`--no-ff`, 제품 트리 = QA `9ee11a7`). Release 빌드 경고 0·오류 0, .NET 553/553(Analysis 41·Compute 46·Sync 231·Core 235), data-pipeline Python OK. **UI 6/7 — `display_labels.test.mjs` `registered_messages_match_server_sources` 실패:** B-DATA-1 새 서버 문구 약 27개(예: "방어율", "보스 속성 준비 필요", "원값(단위 미확인)")가 `apps/desktop-ui/registered-messages.js` 허용 목록에 없음. QA는 이 Node UI 테스트를 돌리지 않았다.
  - **조치:** Backend 구현에 재생성 별도 커밋 + 내부 근거 메모(예: "사용자 R4…", "그룹 904…")가 표시 문구로 나가지 않는지 검토 지시, 리뷰 직접 왕복 → Director. 배포 전 최종 확인에 UI 7/7 포함.
  - **허용 목록 수정 리뷰 최종 통과:** Backend `e21b774`(`a050853` 바로 위). 필드 메타데이터 9개를 `tools/data-pipeline/manifests/solo-raid-boss-attribute-fields.json`으로 값 그대로 이동, 내부 source/note는 생성기 스캔 제외(회귀 테스트), 허용 목록은 "보스 속성 준비 필요" 1개 추가(총 213). 리뷰어 직접: UI 7/7, ESM 구문, 생성기 --check, Python 19/19. 현재 UI에 보스 속성 API 소비 경로 없음.
  - **QA:** S-SKILL-1 QA 뒤 착수하도록 검수 대기열에 전달(준비기 산출물 바이트 동일, UI 7/7 포함).
  - **QA 최종: 대상 단독 통과.** 검수 `25e8210`, [보고서](C:/Users/user/orca/workspaces/Nikke-Simul/검수/docs/boss-static-attributes-followup-qa.ko.md). 같은 8/12 ZIP·같은 시계 입력으로 `a050853`·`e21b774` 준비 산출물 239,710바이트 전체 동일(`693c466e…`), 근거 메모 18개 미등록·일반 문구 대체, API 565/565, `e21b774` 단독 UI 7/7. **BD1-F-Q-1(통합본 한정):** S-SKILL 통합본에서는 니케 이름 5개(스노우 화이트·맥스웰·라피 : 레드 후드·홍련 : 흑영·레드 후드)가 허용 목록에 없어 UI 6/7 — B-DATA 결함이 아니라 S-SKILL 쪽 누락.
  - **Director 통합 `0f6dea1`**(`e21b774` 직접 merge — QA 커밋은 미통과 S-SKILL을 포함하므로 사용하지 않음). 생성기 --check 213개 일치, UI 7/7, data-pipeline Python OK. BD1-F-Q-1은 엔진 구현이 SS1-Q-1 수정 때 Director `0f6dea1` merge 후 생성기로 재생성(218개 예상)하도록 추가 지시.

### S-SKILL-1 진행

- **리뷰 1차 반려 항목 5 → Director 정책 판단(2026-10-02):** 스노우 화이트·맥스웰 버스트 교체 무기 모션 값 미확정. 구현 권장 (a) **잠정 정책 승인** — 시전 즉시 차지 시작(조준 지연 0), 풀차지, 탄창은 설명문 고정값. 조건: trace·limitations에 잠정 라벨, 수동 톡톡이 미지원 거부 유지, 정책 값 한곳 정의, 보고서 가설 2에 영향(1발 발사 시점 ≤0.2초) 명시. 교체 무기 표 고정은 D-SRC-1 뒤 후속. 커밋 `fc36a09`, 보고서 `docs/ssr-skill-batch1-engine.ko.md`.
- **리뷰 최종 통과(2026-10-02):** 엔진 HEAD `27b99ee`(`dbe9b68` → `fc36a09` → `27b99ee`), 반려 1회 해소. 잠정 정책은 `ReplacementWeaponPolicy`(`SkillDefinitions.cs`) 한 곳 정의·실행부 참조·trace basis·limitations·수동 tap 거부 확인. 관통 파싱 strict(Pierce/None만, 누락·미지 값 오류). 버전 미상향 — 기존 5인 20 seed 동일. 리뷰어 직접 실행 `dbe9b68` Core/Engine 231/231·Python 43/43; 최신 Core 232·Python 44는 구현 보고치.
  - **실제 범위: 스노우 화이트·맥스웰 조립(버스트는 관통 다중 타격 미모델로 부분 지원)**, 라피 : 레드 후드·홍련 : 흑영·레드 후드는 **미지원 진단**(실행 거부). 미지원 원인: 팀 버스트 단계 규칙(AllStep·편성 의존 단계 변경·IsBurstStepState 1~3), 부착 투사체(182~185), CycleUse·DamageShareInstant, ChargeTimeChangetoDamage(129), TargetGroupid·TimingTriggerValueChange(130·131) 등. → 이 효과 묶음은 후속 엔진 확장 배정 후보(팀 버스트 규칙 우선).
- **QA:** 검수 세션이 E-PREC-1 → B-DATA-1 진행 중이라 **세 번째로 대기**. 앞선 QA 보고 후 전달(xhigh 권장).
- **QA 1차 전달 후 중단(2026-10-02):** QA가 E-PREC 통합본 위에 merge하자 `SkillReplay.cs` 장탄 조립 충돌(E-PREC 정수 장탄 vs 교체 무기 탄창 정책). QA가 직접 해소하려 해 **Director가 중단**시켰다 — 제품 코드 수정은 QA 독립성 위반. 검수 브랜치는 `e6295ca`로 복구 확인.
  - **조치:** 엔진 구현이 Director 최신 HEAD를 엔진 브랜치에 merge해 충돌 해소(기본 무기는 E-PREC 정수 장탄 경로, 교체 무기는 `ReplacementWeaponPolicy` 고정 탄창), 두 기능 회귀·기존 5인 결과 Director `6d83dec`와 동일 확인 → 리뷰(merge 해소 부분) → Director → QA 재전달.
  - **merge 해소 리뷰 최종 통과:** 엔진 `20a0609`(= `27b99ee` + Director `d1bd49d`). E-PREC `FromRaw`/`ApplyAmmo`/checked 합산 그대로 유지, 교체 무기만 고정 탄창으로 덮어씀. Release Core/Engine 251/251. 기존 5인 20 seed 저장 결과(Director 대 merge) 차이 0. 버전 6종·fingerprint 유지, 추가 상향 불필요.
  - **QA 재전달:** B-DATA-1 재QA 뒤 착수하도록 검수 대기열에 전달.
- **QA 최종: 차단 1건 SS1-Q-1.** 검수 `5895872`(대상 `20a0609`, merge `b9ab40a` 충돌 0), [QA 보고서](C:/Users/user/orca/workspaces/Nikke-Simul/검수/docs/ssr-skill-batch1-qa.ko.md), 2,171 중 2,170 통과.
  - **SS1-Q-1:** 교체 무기 잠정 정책·관통 다중 타격 미모델 한계가 replay에는 있으나 compute batch/results/statistics에는 전달되지 않는다(`PreparedSkillReplay` `SkillRunSummary`/`Run()`과 `ComputePreparation` RunSummary 변환에서 Limitations 소실). 승인 조건("교체 총을 쓴 모든 실행에 표시") 위반.
  - 통과: 원천 1,164, 실제 API 152/153, 효과·키 57, 기존 회귀 797(기존 5인 결과·규칙 버전 Director `6d83dec`과 동일), E-PREC 상호작용(기본 무기 100 + raw 1450 → 115발, 교체 무기만 1발 고정).
  - 비차단 정정: 구 catalog도 `weaponChange:null` 직렬화로 graph fingerprint가 바뀐다(`ffeafdbf…` → `313fd39a…`, 규칙·dataVersion 불변, 안전한 키 분리). 홍련 : 흑영은 무기 입력 검사, 레드 후드는 버스트 메타데이터 검사에서 먼저 400 — 보고서의 "모두 미지원 공식 스킬 문구" 표현은 부정확.
  - **Director 조치(2026-10-04):** 엔진 구현에 수정 지시(범위 예외: Engine 요약 + `src/Nikke.Data/ComputePreparation.cs` RunSummary 변환 + 최소 Contracts/API 연결, 저장 형식 변경 시 요약 버전·fingerprint 분리·구 결과 보존, 새 화면 문구는 허용 목록·UI 테스트) + 문서 정정 2건. **구현 세션이 주간 사용량 한도(10/6 10시 초기화)로 착수 직후 정지** → 사용자가 세션을 재개시켜 수정 진행 중(2026-10-04). 배포는 계속 세 건 동시.
  - **수정 리뷰 최종 통과:** 엔진 `849f81b` — `f77b336`(SS1-Q-1: compute 요약에 잠정 정책·관통 한계 전달, 범위 예외로 Engine 요약·Data·Contracts/Api·Analysis 최소 연결), `3a0f9a5`(Director `f846597` merge, B-DATA 통합 포함), `849f81b`(허용 목록 재생성 218개, 니케 이름 5개만 추가 — BD1-F-Q-1 해소). 리뷰어 직접: 생성기 --check 218, UI 7/7, ESM 18개; 본 수정 Core 252·Analysis 42·Compute 47·Sync 231.
  - **재QA 전달(2026-10-04):** 검수 착수 확인. 세 건 통합본 최종 확인을 겸한다.
- **재QA 결과(검수 `6fc4481`, merge `79a0830`):** [보고서](C:/Users/user/orca/workspaces/Nikke-Simul/검수/docs/ssr-skill-batch1-readmission-qa.ko.md) 2,767 중 2,764 통과. BD1-F-Q-1 해소(생성기 218, UI 7/7, ESM 18/18). SS1-Q-1: results·statistics·run별·재시작 후 조회 모두 정책 식별자(`replacement_weapon_provisional_motion:…`, `pierce_multi_hit_not_modelled`) 전달, 요약 버전 `cpu-summary.6-precision-1` → `.7-run-policies`, 구 실험 batch·results 원시 바이트·DB payload 동일, 구 resume 409. 세 건 통합 회귀(E-PREC 797, B-DATA 545, S-SKILL 원천 1,164) 재실행 통과. **잔여:** (a) 완료 batch 상태(`GET /api/compute/experiments/{id}`, `BatchStatus`)에는 한계 없음 → QA는 통합본 수용 보류, (b) 구 statistics `members` 키 순서가 재시작마다 달라 원시 바이트 비교 2건 실패 — 수정 전 바이너리끼리도 재현되는 기존 특성(`ComputeAnalysis.cs:72` `ToImmutableDictionary`), 값은 동일.
- **Director 판단(자문 Codex 검토 반영, 2026-10-04):** (a)는 **지시 문구 불일치에 한정한 범위 정정**으로 비차단 처리한다 — 구현 수정 지시는 "results·statistics"였고 QA 재배정 지시만 batch까지 넓게 썼다(Director 오류). 실제 결과 조회 경로(results·statistics)의 전달·저장·재조회는 충족. 단 **현재 UI는 compute 한계를 표시하지 않으므로 "사용자에게 보인다"고 하지 않는다** — batch 상태 누락과 UI 미표시는 배포 후 잔여 한계로 명시하고 후속 과제로 둔다. (b)는 신규 회귀 근거 없음, 비차단 후속(키 순서 고정)이며 "원시 바이트 보존 통과"로 보고하지 않는다. 이 수용을 선례로 일반화하지 않는다. QA에 이 근거로 **기존 증거 기준 최종 판정 재확인**을 요청(전체 재실행 불필요), 확인 후 세 건 통합·배포.

### 배포·D-SRC-1 전달

- **배포 결정(사용자, 2026-10-02):** E-PREC-1·B-DATA-1·S-SKILL-1 **세 건을 한 번에** 원본 배포한다. 세 건 QA 통과·Director 통합 후 사용자가 앱을 닫고 진행. E-PREC-1은 통합 `6d83dec`로 대기.
- **D-SRC-1 전달(2026-10-02):** B-DATA-1 리뷰 통과로 착수 조건 충족. Backend 구현 `term_9d9ce9f4…`·리뷰 `term_ed5e9c16…` 수신 확인. 입력은 Director `artifacts/sources/`의 blabla·StaticData 사본(자기 worktree로 복사 후 hash 대조). B-DATA-1 QA 중이므로 기존 코드 동작 불변, 확장은 새 경로로. 세 건 배포에는 포함하지 않는다.

### 세 건 원본 배포 (2026-10-04)

- S-SKILL-1 QA 최종 통과(검수 `047e640`, Director 범위 정정 반영) → Director 통합 `6a53c9c`(`849f81b` merge, 제품 트리 = QA `79a0830`) → **원본 배포 완료**([배포 기록](desktop-release-original-2026-10-04.ko.md)): 원본 main `a03c5a9` → `6a53c9c`, runtime `2e6e8d06…`, 보스 속성 준비 파일 추가, 바로가기 실행 검증·보존 비교 동일.
- 후속 과제: compute `BatchStatus` 한계 전달, UI의 compute 한계 표시, statistics `members` 키 순서 고정, D-SRC-1(설계 담당 경유 재개), S-SKILL-1 2차.

## 이후

각 리뷰 최종 통과 → Director → 독립 QA(검수 `term_234e279b…`) → 통합·배포. 통계(크리 편차 실험 등)는 대미지 정책 확정 뒤 배정한다.

## 전달 확인

지시서 커밋 `e96b147`. 전달 직전 여섯 터미널 모두 대기 상태 확인. 구현 3명 `input_accepted`·`turn_started`(S-SKILL-1 `term_1fba2b21…`, E-PREC-1 `term_80f56a78…`, B-DATA-1 `term_9d9ce9f4…`), 리뷰 3명 안내 전달(`term_ec372feb…`은 `input_accepted`, 나머지 둘 `turn_started`). 착수 확인이며 구현 완료가 아니다.

## 진행

- **S-SKILL-1 판단 요청(구현, 2026-10-03):** 신데렐라 : 크리스탈 웨이브(#5175)는 고정 원천 3종(`skill_chains.json` 192명·`roledata_clean.json`·`blabla_roledata.json`)에 없어 조립 불가 — 추정 금지 원칙에 따라 "원천 없음"으로 미조립. 나머지 4명은 원천 있음, 파이프라인 재현 확인(현 runtime catalog `9c98c91c…` 정확히 재현).
- **Director 판단:** 5번째 자리를 전투력 다음 순서 **#5101 레드 후드(791,834, 원천 있음, 버스트 단계 5 = 올버스트)**로 대체한다 — 전투력 순서 원칙 유지, 올버스트라 덱 구성 다양성에도 도움. **#5175는 원천 갱신 후 후속 묶음**에서 다룬다. 원천 미수록 사실은 보고서에 남긴다.
- **원천 3종 출처 확인(Director, 2026-10-03, 레거시 저장소 `Nikke-Dmg-Simulator` 생성 스크립트 추적):**

  | 원천 | 출처 | 생성 | 시점 |
|---|---|---|---|
  | `skill_chains.json` | 게임 StaticData(decoded mpk: Character·CharacterSkill·Function·StateEffect·SkillInfo·Monster 표) | `DataPipeline/crawler/staticdata_skill_chains.py` | StaticData 7/8, 산출 7/16 |
  | `blabla_roledata.json` | blablalink 공개 roledata(`sg-tools-cdn.blablalink.com`, en) | `getFromBlaLinkRoledata.py` | 7/1 |
  | `roledata_clean.json` | `blabla_roledata.json` 정규화(무기·스탯 입력) | `DataPipeline/etl/roledata_cleaner.py` | 8/19 |

  - **#5175 미수록 원인 정정:** decoded StaticData `CharacterTable`에는 #5175(와 #5176)가 **이미 있다**. `skill_chains` 조립이 니케 범위를 `blabla_roledata` 로스터(192명, 최대 #5174)로 제한해서 빠졌다. 따라서 StaticData 재생성은 필수가 아니고, **blabla roledata 갱신**(무기·스탯 입력인 `roledata_clean`도 같은 원천이라 어차피 필요) → `skill_chains`·`roledata_clean` 재생성 → Nikke-Simul 원천 manifest hash 재고정이 필요하다. 최신 니케가 7/8 이후라면 StaticData 갱신도 함께 필요하다.
