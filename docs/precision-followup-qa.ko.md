# E-PREC-1 독립 QA

대상 `2b16883`(구현 `c7b6c83`). Director 시작 최신 `3b19b4c`을 일반 merge한 뒤 대상 커밋을 일반 merge: `ca0e0960879445131c805413d181a58704ee5219`, 충돌 0. 지시서: `docs/skill-precision-assignments-2026-10-03.ko.md`.

**통과 — 1,106/1,106, 제품 차단 0.** 독립 산술 1,003, 5인 비교 76, 실제 격리 API 27. 아래 두 문서 정정점은 비차단으로 Director에 인계한다. 실게임 1-tick 대조·기본 정책 변경·원본 배포 판정은 아니다.

## 독립성·보존

제품 소스만 읽고 새 QA `PrecisionProbe`와 분수 기대값을 작성했다. 구현·리뷰의 테스트·하네스·mock·결과/정답 파일은 사용하지 않았다. 기존 검수의 Fraction binary32 함수와 격리 서버/합성 계정 도구만 재사용했다. 구 비교 DLL은 병합 전 검수 빌드에서 보관했다. 해당 제품 소스는 Director `e96b147`/`3b19b4c`와 같았고 버전도 구 E-BUG-1 버전임을 확인했다.

원본 공개 표 12개(`game-catalog.json`, calculation/current 및 해당 표, runtime/current 및 catalog)만 읽어 검수 artifacts에 복사했고 전후 SHA-256 동일. 계정은 새 합성 DB다. 원본 accounts.db·세션·캐시·presentation·5180/5181·사용자 EXE 접근/변경 없음. package-lock.json hash `2ef4178a…53c767` 보존·커밋 제외. 제품 수정·push·배포·새 워커 없음. 실제 사용자 실행 파일 경로는 계속 `C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe`다.

## 1. 후보 산술·기본값

Python Fraction으로 binary32(24비트)와 binary64(53비트)의 최근접·짝수 반올림을 따로 구현했다. B는 crit→core→burst→range 순서로 매 차감/합산마다 binary32에 저장한다. extra, 감소, 방어율 항도 binary32로 만든다. dprod의 정수 공방차와 base 내부 곱, 이후 곱 사슬은 **각 단계 binary64에 반올림**하고 마지막에 사사오입·max(1)·long을 적용했다. 무한 정밀도 곱 한 번으로 대신 계산하지 않았다.

737개 독립 입력에 양 정책·중간값·예외·이전 기본값 비교를 붙인 1,003검사 통과. 2^24 주변, 양/음 반정수, 음 공방차의 최소 1, 2^53 정확 정수 경계, 최종 signed-long 한계 및 장탄 checked 경계를 포함했다. dprod 결과 중 **161개는 float32로 표현 불가능한 정수**였다. 2^24+1의 공방차는 client_f32=16,777,216 / dprod=16,777,217. 기존 client_f32 직접 계산 264건은 구 DLL 결과 전체와 동일했다. 기본 정책 상수·Compare의 기존 4후보·UI 선택지는 바뀌지 않았다.

## 2. 방어율·저지·파츠

- 일반/skill, 피해 10·방어율 60% → client 두 정책 4. true → 10. 0·1·1.5도 비교했다. true의 방어율은 쓰이지 않는다. legacy 3정책은 원래 방어율 항을 모델링하지 않아 일반/true 모두 10이며, Director가 승인한 기존 의미 보존과 일치한다.
- 저지 여부×파츠 여부×5정책을 독립 계산했다. 공격 피해 증가 .2, 파츠 .3, 저지 .5의 100 기본 피해는 둘 다 켜면 200이다. client 경로는 break에 저지, add에 파츠가 들어간다.
- 자체 합성 FunctionType 96을 시작 프레임부터 활성화했다. 히트의 AttackDamage는 .2로 유지되고 InterruptionDamage만 .5가 된다. 저지 타깃일 때 150→200, 비타깃은 효과 활성/미활성 모두 150. 중복 가산 없음. legacy에서도 의도한 합산 결과가 같다.
- 파츠 검사는 HitContext.Parts/PartsDamage의 계산 경로다. 이번 커밋에 FunctionType 112의 스킬 조립 지원 추가는 없으며, 이를 지원 완료로 확대 판정하지 않는다.

## 3. 장탄 long 조립

기본값과 raw/10000 비율을 Fraction으로 곱하고 **같은 비율 그룹의 스택 수를 합친 뒤** 사사오입했다. 100×14.5%는 +15 → 115, −0.5는 −1, 같은 .5% 두 항은 묶어서 +1이며 각 항을 반올림해 +2하지 않는다. 그룹 분할·음수·90개 추가 정수 입력·long 최대값/overflow를 검사했다. 소수 격자 밖 `.14501` 및 raw와 rate 불일치도 거부한다.

실제 SkillReplay에 type 14 원천 정수 1450·50·−50을 넣어 최대 장탄 115·101·99를 확인했다. 평타 WeaponReplay 호출부도 같은 ApplyAmmo를 쓰며, 연결 변경 외 타이밍/피해 로직 변화는 없다. 회복량·재장전 비율의 반올림은 이번 소유 범위 밖으로 유지됐다.

## 4. 기존 5인 180초

공개 표 + 새 합성 계정에서 실제 API로 멤버 입력을 산출했다. 리타·블랑·앨리스·누아르·모더니아, Lv400, 스킬 10, 기본 장비/큐브/소장품/돌파/코어/호감도/콘솔 0, DEF 30,925 고정, 코어 ON, 앨리스 수동 풀차지, 크리 sample. 버스트 단계는 리타·블랑, 3단계 후보 3명, 로테이션 앨리스·모더니아, next_ready. 검수 RNG 시드 1~5는 C# 하네스 안에서만 사용했다.

기본·저지 대상·전원 head OL 장탄 .145·.1181의 4조건×5시드×client_f32/legacy_term_floor = **40개 전후 실행이 정확히 같았다**. 팀/멤버 피해, 발수, 치명타, 최대/잔탄, 쿨다운, 버스트 창·게이지·timeline까지 비교(규칙 버전 문자열만 제외). 실제 API 구·신 멤버 입력도 새 중립 필드 false/0의 추가 외 동일했다. 새 기본 필드를 비교 메모리에만 보충했으며 구 저장 파일은 수정하지 않았다.

| seed 1 | client_f32 구=신 | legacy 구=신 | 새 dprod |
|---|---:|---:|---:|
| 기본 | 718,382,334 | 718,335,114 | 718,382,334 |
| 저지 대상 | 718,382,334 | 718,335,114 | 718,382,334 |
| 장탄 .145 | 772,905,797 | 772,850,811 | **772,905,689** |
| 장탄 .1181 | 767,946,890 | 767,891,945 | 상세 team-audit.json |

기본 client_f32의 나머지 시드도 706,999,032 / 710,967,650 / 708,935,937 / 712,395,060으로 재현했다. 96이 활성화되지 않는 기존 5인 조건에서 저지 플래그만 켜도 결과는 그대로였다. 실제 96 활성 검증은 앞 절의 별도 합성 런타임이다.

**비차단 문서 정정 1:** 구현 보고서의 “시드 1~5 dprod 차이 0, 차이는 2^24 이상에서 생김”은 일반화하면 틀리다. 기본·저지 조건은 0이지만 .145 조건의 시드별 차이는 −108/−117/−113/−113/−111. 작은 타격도 곱 차이가 최종 반올림 경계를 넘으면 달라진다. QA는 보고서 정답을 가져오지 않고 같은 공개 입력으로 이를 독립 재현했다.

## 5. 실제 API·규칙·scope

구/신 API를 같은 격리 dataRoot에서 순차 실행했다. HitCalculator, StatBuffCalculator, SkillReplay, WeaponReplay, PreparedSkillReplay, TeamBurstController의 6버전 상향과 RulesVersion 조립을 대조했다. 구·신 입력/실행 fingerprint가 다르고, 새 dprod compute와 기본 compute도 서로 다르다.

구 replay 4개의 GET 바이트·내용, 구 compute 결과·통계, 구 단일-hit 저장값은 그대로 조회된다. 특히 구 true damage 4가 저장 조회에서는 여전히 4이고 새 요청은 10이다. 구 compute resume는 실제 HTTP 409 `engine_or_rules_version_changed`. 새로운 interruption 입력의 단일-hit API 결과는 150이다.

**비차단 문서 정정 2:** “dprod는 API로 선택할 수 없다”는 **단일-hit API에만** 맞다(실제 400). `/api/runtime/skill-replays` 및 `/api/compute/experiments`에 명시 요청하면 실제 실행되며 정책·fingerprint도 저장된다. UI 선택지 추가는 없다. Director가 승인한 SkillReplay 정책 허용·연결 변경의 결과로 분류하며 API 계약 파일을 별도로 수정한 것은 아니다. 향후 노출 범위 설명에는 이 구분이 필요하다.

변경 제품 파일 7개를 승인 범위와 대조했다. Core Combat/Stats, SkillReplay의 히트·장탄 연결·client 분기·버전, WeaponReplay의 장탄 호출/검증·client 분기·버전, PreparedSkillReplay/TeamBurstController의 버전만이다. 승인 예외 밖 동작 변경은 발견하지 못했다. API/Data/Contracts/UI 제품 파일 변경 없음. Release API 빌드 경고 0·오류 0.

## 증거·제한

`artifacts/single-deck-qa/precision1/evidence-index.json`에 최종 1,106검사·공개 표 hash·API 경로를 모았다. `math-audit.json`, `team-audit.json`, `math-old/new.jsonl`, `team-old/new.jsonl`, `cases.jsonl` 및 `expected.json`이 독립 산술·재현 근거다. QA 소스는 `tests/single_deck_compute_qa/PrecisionProbe`와 `check_precision_{math,team,api}.py`.

초기 QA 실행에서 미등록 OL 키(StatAmmo), legacy 검사를 위해 불필요하게 같이 호출한 기본 정책 예외, 새 중립 필드가 없는 구 입력의 단순 JSON 비교를 바로잡았다. 최종 기대값은 명시된 산술/계약에 따르며 제품 수정은 없다. 모든 QA API 종료 확인. 이번 보고는 실게임 공식 확정·부하 측정·원본 통합/배포를 포함하지 않는다.
