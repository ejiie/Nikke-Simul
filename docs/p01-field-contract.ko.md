# P01 v1 입력 계약과 출처

정본 타입: `src/Nikke.Contracts/Models.cs`. JSON은 camelCase, schemaVersion 1이다. 계정+서버마다 별도 AccountId를 만들고 표시 이름 대신 원천 ID로 연결한다.

| 결과 필드 | 원천 | 정제 규칙 |
|---|---|---|
| characterId | GetUserCharacters / GetUserCharacterDetails `name_code` | 숫자·숫자 문자열을 동일한 ID 문자열로 정규화. roster/detail 집합 비교 |
| level / nativeLevel | roster `lv` / detail `lv` | 둘 다 보존. 시나리오의 레벨 정책은 수집 단계에서 적용하지 않음 |
| limitBreak / core | roster `grade` / `core` | 동기화가 반영된 로스터 값을 사용 |
| bond / skills | detail `attractive_lv`, `skill1_lv`, `skill2_lv`, `ulti_skill_lv` | 실제 값 보존. 필수 필드 부재·범위 오류는 실패 |
| equipment | detail `head/torso/arm/leg_equip_*` | tid/tier/lv/corporation_type 보존. 미장착은 tier 0 |
| equipment.lines | 각 부위 `equip_option1/2/3_id` + state_effects | 줄 1~3 유지. ID 0은 absent, 필드 없음은 unknown+검증 오류 |
| rawValue / rawUnit | function_value / function_value_type | 소수 decimal 및 원천 단위 문자열 보존 |
| normalizedValue / unit | 효과 종류와 원천 단위 | Percent는 /10000 → ratio. Integer라도 StatCritical/StatCriticalDamage/StatChargeDamage는 /10000 → ratio. 그 밖의 Integer는 integer로 보존 |
| valueTier | 고정 upstream equipment_skills 단계표 | 절댓값이 정확히 같은 단계만 채움. 음수 차지 시간의 원천 부호는 유지. 표 밖은 null+경고 |
| lockState | 현재 확인한 API 응답에는 명시 잠금 필드 없음 | present 줄은 unknown으로 시작. 사용자가 locked/unlocked/unknown 보완 |
| cubeId / cubeLevel | harmony_cube_tid / harmony_cube_lv | 현재 장착 상태만 기록. 보유 전체·장착 가능 수로 확장 해석하지 않음 |
| collectionId / level / grade / favoriteStage | favorite_item_tid / favorite_item_lv + 고정 favoriteItems 사전 | ID·레벨 원본 보존. SSR 단계는 lv+1. 미매핑은 원천을 유지하고 grade=null |
| synchroLevel / consoles | GetUserProfileOutpostInfo.outpost_info | 미공개·부재는 unknown. 개별 tid/lv 보존, 모르는 항목을 0으로 채우지 않음 |
| accountStatSources | 수집/수동 보완 | synchro 및 console:tid 단위 출처. 변하지 않은 API 값을 수동 입력으로 재분류하지 않음 |

`Integer` 비율 옵션은 실제 193명 응답 대조에서 확인했다. 기존 merger는 Integer 수치를 원형으로 남기고, upstream profile_fetch는 옵션 이름별로 퍼센트로 환산한다. 새 계약은 원천값과 의미 단위를 함께 기록해 혼동을 없앤다. 이 정규화는 대미지 히트 정수화 판정과 별개다.

원천 보관 단위는 3개 게임 API의 응답, 배치별 관측 시각, 정리한 envelope다. 로그인 응답·쿠키·인증 헤더를 RawManifest에 넣지 않는다. 로그인 세션은 별도 DPAPI 암호화 파일로 저장한다.

GameSnapshot은 현재 P01 표시·옵션·소장품 매핑에 필요한 부분집합이다. name_codes, equipment_skills, 생성된 settings의 hash와 upstream commit을 기록한다. 완전한 전투 테이블 snapshot은 P02 이후 확장한다.

합성 테스트는 `tests/Nikke.Sync.Tests/Fixtures.cs`와 `tools/data-pipeline/tests/make_fixture.py`에 있다. 실제 계정 응답·검증 보고서·DB·스크린샷은 Git에서 제외되는 `data/local` 및 `artifacts/p01`에만 저장한다.
