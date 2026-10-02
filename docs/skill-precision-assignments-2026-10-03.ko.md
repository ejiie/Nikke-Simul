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

## B-DATA-1 — 보스 StaticData 속성 (Backend worktree)

- 구현: `Backend` Sonnet `term_9d9ce9f4…`, 리뷰: astra `term_ed5e9c16…`. 사고 수준: 구현 high / 리뷰 medium / QA high.
- 사용자 안내: 보스 데이터는 StaticData에 있다. 동적 패턴(행동 트리·보스 함수·타임라인·거리 변화)은 사용자가 별도로 제공하므로 **이번 범위가 아니다.**
- 할 일: 솔로 레이드 시즌 1~42 보스(기존 보스 목록 ID와 연결)의 정적 속성 — 약점 속성, 방어력, **방어율(`DefenceRatioRatio` 후보)**, 파츠·코어 구성, 레벨 — 을 StaticData에서 찾아 버전 고정 카탈로그로 준비하는 스크립트와 읽기 API(표시용). 원천 위치·필드·단위·신뢰도를 보고서에 표로 남긴다. 확인 못 한 필드는 추정하지 않고 "미확인". 보스 선택은 아직 **계산에 반영하지 않는다**(표시·데이터 준비만).
- 보고서 `docs/boss-static-attributes-backend.ko.md`.

## 이후

각 리뷰 최종 통과 → Director → 독립 QA(검수 `term_234e279b…`) → 통합·배포. 통계(크리 편차 실험 등)는 대미지 정책 확정 뒤 배정한다.
