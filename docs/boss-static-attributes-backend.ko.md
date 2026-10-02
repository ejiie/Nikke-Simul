# B-DATA-1 — 솔로 레이드 보스 StaticData 정적 속성 (표시·데이터 준비 전용)

Backend worktree, Director `e96b147`(배포본 `a03c5a9` + 문서)을 자기 브랜치에 일반 merge한 위에서 수행했다. 지시서: [skill-precision-assignments-2026-10-03.ko.md](C:/Users/user/orca/workspaces/Nikke-Simul/Director/docs/skill-precision-assignments-2026-10-03.ko.md) B-DATA-1. 작업 구조는 [workflow-implement-review.ko.md](C:/Users/user/orca/workspaces/Nikke-Simul/Director/docs/workflow-implement-review.ko.md).

**준비 스크립트 + 읽기 API + 테스트 완료.** 보스 선택은 계산·fingerprint·튜닝 키·저장 결과에 **반영하지 않는다**(표시·데이터 준비만). 원본 배포·UI 화면·독립 QA 완료를 뜻하지 않는다. 동적 패턴(행동 트리·보스 함수·타임라인·거리 변화)은 범위 밖이다.

## 핵심 결과 (Director 판단이 필요한 것 먼저)

1. **시즌 41·42는 만들 수 없다.** 로컬에 있는 StaticData 사본 3벌 중 가장 최신(바탕 화면 `StaticData.zip`, 내부 표 시각 2026-08-12)의 `SoloRaidManagerTable`도 시즌 **40까지**다(41행, 시즌 19 중복 1행). 시즌 41·42는 카탈로그에 `status:"unavailable"`, `reason:"static_data_season_missing"`로 남기고 `complete:false`다. 추정하지 않았다. 채우려면 **최신 StaticData를 새로 받아야** 하며, legacy 문서 기준 라이브 서버 fetch는 사용자 명시 go-ahead 없이 실행하지 않는 정책이라 하지 않았다(Director/사용자 결정 요청).
2. **방어율(`defence_ratio_ratio`)은 레거시 사본(6/11·7/8 팩, 7/23 probe)에 수록되지 않았다.** Director 확인(2026-10-02): 공개 저장소 EpinelPS/EpinelPS 커밋 `17eb33f`(2026-09-23)의 `EpinelPS/Data/JsonStaticData.cs` `MonsterRecord`에 `int DefenceRatioRatio`가 `AttackRatio` 바로 뒤에 있어 최신 팩에서 **필드명은 확인됐다**. 레거시 decoded `MonsterTable`에는 이 필드가 없으므로 그 원천 기준 방어율은 **"현 원천 미수록(최신 팩 필드명 확인됨)"**이며 추정하지 않는다. 단위(/10000 여부)·적용 조건·적용 보스는 미확인이다.
   - **Director 판단 필요(원천 범위):** 이 구현은 사용자가 바탕 화면에 둔 `StaticData.zip`(내부 표 시각 2026-08-12, `MonsterTable` 33 members, `defence_ratio_ratio` 포함)을 **읽기 전용으로 디코드**해 시즌 1~40 보스의 값이 전부 0임을 확인했다(다운로드·fetch 없음, 로컬 파일 읽기만). Director 메모의 "최신 팩 재디코드는 사용자 승인 뒤 별도 작업"과 범위가 겹친다. 이 값(0)을 카탈로그에 유지할지, `defenceRatioRate`를 null + "현 원천 미수록"으로 되돌릴지는 Director가 결정한다. 되돌리는 변경은 스크립트 한 곳(`defenceRatioRate` 출력)과 테스트·API 검사의 해당 단언만이다. 어느 쪽이든 이 값은 계산에 쓰이지 않는다.
3. **레벨이 전투 중 바뀐다는 근거를 찾았다(보고 대상).** 챌린지 preset의 `Monster_stage_lv_change_group = 904`(시즌 1~40 전부)가 `MonsterStageLvChangeTable`의 9행을 가리킨다: 구간 [0, 4억]·…·[16억+1, 20억]은 레벨 390, [20억+1 이상]은 레벨 400. `MonsterStatEnhanceTable`(group 230000)의 방어력은 레벨 390 = **30925**, 레벨 400 = **31784**로, 사용자 R4와 엔진 `team_damage_threshold`(20억 초과 시 30925 → 31784)와 **정확히 일치**한다. 열 이름은 미확인이라 신뢰도는 `유력`이다.
4. 보스 식별은 이름·위치 추정이 아니라 exact join이다. 시즌 1~39는 legacy 7월 카탈로그(`solo_raid_challenge_catalog.json`)의 보스 monster ID와 **39/39 일치**, 시즌 40이 새로 추가됐다. 시즌 1~40의 `Monster_image`가 검토된 한국어 이름 manifest의 `expectedSourceId`와 모두 일치해 기존 `solo-raid-<시즌>` ID와 연결된다.

## 원천 (읽기 전용, 모두 Git 제외·재배포 금지 자료)

| 자료 | 위치 | SHA-256 | 용도 |
|---|---|---|---|
| StaticData 사본(채택) | `C:/Users/user/Desktop/StaticData.zip` | `925762cd3ef56601916b2e2ae58f929d4dd389055b0d8bcd2176e9abd9b29e69` (17,176,616 B, 내부 표 시각 2026-08-12) | 본 카탈로그의 유일한 입력 |
| legacy 7월 카탈로그 | `Nikke-Dmg-Simulator/Database/raw/staticdata/assembled/solo_raid_challenge_catalog.json` | `377a11723d77…2ed39` | 교차 검증만(보스 monster ID 39개) |
| legacy 7월 조립본 | 같은 폴더 `raid/solo_raid_boss.json` | `148c53abae87…b6f6` | 교차 검증만(코어 분류·속성) |
| 이름 manifest(저장소) | `tools/data-pipeline/manifests/solo-raid-korean-names.manifest.json` | — | 시즌 범위 1~42, 이미지 ID 대조 |

사본 3벌 비교: legacy `StaticData.zip`(7/8판, 시즌 ≤39), `season40_probe`(7/23판, ≤40, 방어율 필드 없음), 바탕 화면(8/12판, ≤40, 방어율 필드 있음). 채택은 8/12판이다. 입력 표 10개의 SHA-256·레코드 수는 카탈로그 `source.entries`에 저장된다. 스키마(MemoryPack 멤버 순서)는 legacy 디코더에서 옮겼고 레코드마다 멤버 수·버퍼 끝을 강제하므로 클라이언트 변경 시 필드가 밀리지 않고 실패한다. 스키마 지문은 카탈로그 `source.schemaFingerprint`.

`ElementTable`(8 members)과 `MonsterStageLvChangeTable`(10 members)은 legacy에 정식 스키마가 없어 와이어에서 복원했다(5/486행 모두 버퍼 끝까지 정확히 소비). 두 표의 멤버 이름은 내용 기반 이름이며 후자는 위치 이름이다.

## 필드 표 (원천·단위·신뢰도)

신뢰도: **확인**(표 값 직접 + 구조 검증) / **유력**(복수 근거, 의미 대응 미확정) / **미확인**.

| 필드 | 원천 | 단위 | 신뢰도 | 비고 |
|---|---|---|---|---|
| 속성 | `MonsterTable.element_id`(보스 monster) → `ElementTable.icon` | 속성 ID, 앱 어휘 Fire/Water/Wind/Iron/Electronic | 확인 | element_id가 정확히 1개일 때만 채움(그렇지 않으면 null + unconfirmed). 시즌 1~40 모두 1개 |
| 약점 속성 | `ElementTable.weak_element_id` | 속성 ID | 유력 | 필드 이름 + 알려진 상성(불→바람→철→전기→물→불)이 일치. 계산 미반영 |
| 챌린지 레벨 | `SoloRaidPresetTable`(Difficulty_type=2).`Monster_stage_lv` / `Character_lv` | 레벨 | 확인 | 전 시즌 390 / 싱크로 400 |
| 일반 난이도 레벨 사다리 | 같은 표(Difficulty_type=1) | 레벨 | 확인 | 전 시즌 7단계(45·85·120·145·175·185·200) |
| 레벨 변경 | `MonsterStageLvChangeTable`(group=`Monster_stage_lv_change_group`) | 구간(누적 피해 후보) → 레벨 | 유력 | 위 핵심 결과 3. 마지막 단계 `range_to=0`은 "상한 없음"으로 읽어 `rangeTo:null`(유력). 마지막 열(7000001 등)은 미확인이라 노출하지 않음 |
| 레벨별 HP·공격·방어 | `MonsterStatEnhanceTable[group=monster.statenhance_id, lv]` | 정수 원값 | 확인 | 전 시즌 group 230000. 예: 390 = HP 5,866,372,929 / ATK 111,269 / DEF 30,925, 400 = 6,083,218,659 / 114,344 / 31,784 |
| 방어력 | 위 `defence` + `MonsterTable.defence_ratio`(전 시즌 10000) + 파츠별 `defence_ratio` | 표 원값(비율 /10000 후보) | 확인(원값) / **미확인(합성)** | 레벨 방어와 비율의 곱 규칙은 확정하지 않아 곱하지 않는다. 파츠 비율에 0·10000·46000이 있다 |
| 방어율 | `MonsterTable.defence_ratio_ratio` | 원값(단위 미확인) | 레거시 사본: **현 원천 미수록**(필드명은 EpinelPS `17eb33f`로 확인). 8/12판 바탕 화면 사본: 필드·값 확인, 단위·적용 미확인 | 시즌 1~40 전부 0(8/12판). 사본 원천 범위는 핵심 결과 2 참고 |
| HP 배율 | `MonsterTable.hp_ratio` | 원값 | 확인 | 시즌 33만 15000, 나머지 10000. HP에 곱하지 않음 |
| 파츠 구성 | `MonsterPartsTable[monster_model_id]` | 파츠 행 1~23개 | 확인 | `partsType`은 **원값 정수만** 제공한다. legacy의 이름 표(Head/Weapon_01…)는 공개 enum 대조를 하지 않아 노출하지 않음 |
| 코어 구성 | 파츠의 `weapon_object`/`parts_object`/`parts_skin` collider 이름에 `core` 포함 | 파츠 ID | 유력 | 아래 표 |

코어 분류(시즌 1~40): 별도 파츠 16, 메인 바디 부착 1(시즌 39), **미확인 23**. 미확인은 "코어 collider를 가진 파츠가 없음"일 뿐이며 legacy가 하던 "코어 = 몸통 기본 약점" 추정은 하지 않는다(`core.kind:"unconfirmed"`, unconfirmed에 `core_position`). legacy 조립본의 코어 분류와 시즌 1~39 전부 같은 분류다(legacy가 monster를 휴리스틱으로 골랐던 시즌 11·18·22·24~26·30·32·34~36·39의 monster ID와 시즌 32 파츠 수 9→10, 시즌 16 파츠 0→12 차이는 exact join으로 바로잡힌 결과다).

## 준비 명령과 읽기 API

```powershell
python tools/data-pipeline/prepare_solo_raid_boss_attributes.py --static-data-zip <StaticData.zip> --presentation-root <dataRoot>/presentation
```

- 입력 zip은 읽기만 하고(전후 hash 확인) 네트워크 접근이 없다. 출력 `solo-raid-boss-attributes.json`은 지정한 presentation root에 `.pending` 후 교체로 쓴다. 디코딩한 표 자체는 저장하지 않는다.
- 실행 결과(이번 격리 산출물 `artifacts/bdata1/presentation/`): `{"bosses":42,"available":40,"unavailable":[41,42],"complete":false}`.
- `GET /api/presentation/solo-raid-bosses/attributes`: wire·실패 코드는 [계약 문서](single-deck-compute-contract.ko.md)의 "보스 정적 속성" 절. 기존 `/api/presentation/solo-raid-bosses` wire는 바꾸지 않았다. 카탈로그 미준비 시 `bosses:[]` + `boss_attributes_not_prepared`, 손상 시 409.
- UI·계산 변경 없음. Git 제외 카탈로그는 merge만으로 원본에 반영되지 않으며 배포 시 원본 presentation에 별도 준비가 필요하다.

## 지시서 항목 대조

| 항목 | 상태 |
|---|---|
| 솔로 레이드 시즌 1~42 보스를 기존 목록 ID와 연결 | 1~40 완료(`solo-raid-<시즌>`, 이미지 ID 40/40 일치). 41·42 `static_data_season_missing` |
| 약점 속성·방어력·방어율·파츠·코어·레벨 | 위 필드 표. 확인 못 한 값은 null + 미확인 |
| 버전 고정 카탈로그를 만드는 스크립트 | `prepare_solo_raid_boss_attributes.py`(zip·표·스키마 hash 고정) |
| 읽기 API(표시용) | `GET …/attributes` |
| 원천 위치·필드·단위·신뢰도 표 | 위 표 + 카탈로그 `fields` |
| 보스 선택을 계산에 반영하지 않음 | 반영 없음. 계산·fingerprint·저장 코드 변경 0 |

## 검증

- Python: `python -m unittest discover -s tools/data-pipeline/tests -p "test_solo_raid_boss*.py"` **16/16 통과**(신규 10: 합성 MemoryPack 인코더로 exact join·속성·레벨 변경·방어율 원값·코어 미확인·시즌 누락 diagnostic·레벨 행 누락 null·다중 속성·멤버 수/버퍼 끝/표 누락/보스 후보 2개 거부·시즌 중복 관계·검토 이미지 불일치·미지 아이콘·원천 hash 변화).
- .NET(Release): Sync **171**, Core **217**, Compute **46**, Analysis **41** 전부 통과, 실패 0. 신규 Sync 테스트 3개(미준비 explicit, 미사용 시즌 null·방어율 원값, 손상 5종 거부).
- 격리 API: `python tests/Nikke.Compute.Tests/check_boss_attributes_api.py --data-root artifacts/bdata1/data --source-game artifacts/bfix3/data/game-catalog.json --dotnet <dotnet>` **passed**(동적 포트 58883): 42개 · 40 available · 41/42 unavailable · 시즌별 챌린지 레벨 390/DEF 30925/방어율 0/레벨 변경 DEF `[30925×6, 31784×3]` · 파일과 wire 일치 · 기존 보스 목록 API 불변. 계정을 만들거나 복제하지 않았고 새 dataRoot였다.
- 교차 검증(1회성, 스크립트 외): 시즌 1~39 보스 monster ID legacy 7월 exact catalog와 39/39 일치, 코어 분류 legacy와 39/39 같은 분류.

## 보존 확인

- 원본 `data/local`의 어떤 파일도 **읽지 않았다**(디렉터리 이름만 `ls`로 확인, 공개 표 hash 기록 대상 없음). `accounts.db`·세션·캐시·presentation·5180/5181·원본 EXE 접근·변경 없음.
- 읽은 외부 자료는 위 원천 표의 파일뿐이며(legacy 저장소·바탕 화면 zip, 읽기 전용) 모두 hash를 적었다. 다운로드·fetch 없음. 제품 스크립트는 legacy 디코더를 import하지 않는 자체 완결형이다. 다만 탐색 단계에서 legacy `memorypack_decode.py`를 읽기 전용으로 import했고, 그 때 legacy `DataPipeline/crawler/__pycache__/memorypack_decode.cpython-311.pyc`(Git 제외 바이트코드 캐시)가 13:33에 다시 쓰였다. 소스 파일은 수정하지 않았고, 재생성 가능한 캐시이므로 그 pyc를 삭제했다(다음 실행 시 자동 재생성). 
- `package-lock.json` 미추적 유지, SHA-256 `2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767` 전후 동일, 커밋 제외. push·배포·새 워커 없음.
- 실제 사용자 실행 경로는 계속 `C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe`이며 건드리지 않았다. 원본 통합·빌드·배포·실행 검증은 하지 않았다.

## 후속 후보 (범위 밖)

- 최신 StaticData 재fetch(사용자 go-ahead 필요) 후 시즌 41·42와 방어율 값 확인.
- `MonsterStageLvChangeTable` 열 이름·마지막 열(7000001) 의미 확인(공개 모델 대조 또는 클라이언트 코드).
- `parts_type` enum 이름 매핑 검증.
- 레벨 변경을 엔진의 DEF 전환 상수(30925/20억/31784) 대체 입력으로 쓸지는 Director/사용자 결정.

## 리뷰 이력

(비어 있음 — 리뷰 담당 인계 전)
