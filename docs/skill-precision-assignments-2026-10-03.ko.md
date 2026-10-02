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

## B-DATA-1 — 보스 StaticData 속성 (Backend worktree)

- 구현: `Backend` Sonnet `term_9d9ce9f4…`, 리뷰: astra `term_ed5e9c16…`. 사고 수준: 구현 high / 리뷰 medium / QA high.
- 사용자 안내: 보스 데이터는 StaticData에 있다. 동적 패턴(행동 트리·보스 함수·타임라인·거리 변화)은 사용자가 별도로 제공하므로 **이번 범위가 아니다.**
- 할 일: 솔로 레이드 시즌 1~42 보스(기존 보스 목록 ID와 연결)의 정적 속성 — 약점 속성, 방어력, **방어율(`DefenceRatioRatio` 후보)**, 파츠·코어 구성, 레벨 — 을 StaticData에서 찾아 버전 고정 카탈로그로 준비하는 스크립트와 읽기 API(표시용). 원천 위치·필드·단위·신뢰도를 보고서에 표로 남긴다. 확인 못 한 필드는 추정하지 않고 "미확인". 보스 선택은 아직 **계산에 반영하지 않는다**(표시·데이터 준비만).
- 보고서 `docs/boss-static-attributes-backend.ko.md`.

## D-SRC-1 — 니케 원천 갱신 (Backend worktree, B-DATA-1 뒤)

배경: 위 "원천 3종 출처 확인". #5175 이후 니케를 조립하려면 blablalink roledata 로스터를 새로 받아 `skill_chains`·`roledata_clean`을 다시 만들어야 한다. 사용자 지시 "진행"(2026-10-03).

- 구현: `Backend` Sonnet `term_9d9ce9f4…`(high), 리뷰: astra `term_ed5e9c16…`(medium), QA high. **B-DATA-1 리뷰 통과 뒤 착수**(같은 짝 직렬).
- **레거시 저장소 불변:** `C:/Users/user/Documents/GitHub/Nikke-Dmg-Simulator`에는 사용자의 미커밋 변경이 있고, Nikke-Simul `prepare-legacy.ps1`이 그 파일들의 hash를 고정 검사한다. 레거시 `Database/**`를 덮어쓰거나 그 저장소에서 Git 조작을 하지 않는다. 레거시 스크립트는 읽기/호출만 하고 출력 경로는 Nikke-Simul 쪽 Git 제외 위치(예: `artifacts/sources/<snapshot-id>/`)로 돌린다(필요하면 Nikke-Simul `tools/data-pipeline`에 래퍼 작성).
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
   - 상태: **라이브 서버에서 팩 받기는 레거시 정책상 사용자 명시 승인 후에만 실행**(복호 산출물 커밋·재배포 금지, 로컬 전용). 승인 대기.

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
