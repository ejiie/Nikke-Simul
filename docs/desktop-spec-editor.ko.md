# Local Lab 스펙 편집 연결 — 2026-09-09

## 조작

- 니케 상세의 레벨·호감도·스킬 1/2/버스트 레벨을 변경한다.
- 장비 이미지를 누르면 Local Lab의 장비 선택창이 열린다. 같은 클래스·부위의 T9/T10을 선택하고 강화 0~5를 변경한다. T9는 기업 일치 여부도 지정한다.
- T10의 각 OL 줄에서 옵션과 15단계 수치를 선택한다. 옵션 없음도 선택할 수 있다. 명칭, 퍼센트 표시, 등급 색상은 Local Lab을 따른다.
- 소장품 탭에서 R/SR 소장품·캐릭터 전용 애장품과 단계, 장착 큐브·레벨을 지정한다. 큐브 레벨은 계정 공통이므로 같은 큐브를 장착한 다른 캐릭터에도 적용된다.
- 돌파와 코어는 `− [별 3개][코어 배지] +`로 이어 배치했다. SSR은 `0돌파 → 3돌파 → 1코강 → 7코강(MAX)`를 ±로 조정한다. 3돌파에 도달한 후 코어가 1 이상일 때만 배지가 나타난다. 별 클릭으로 돌파 단계도 선택할 수 있다. SR/R은 카탈로그의 돌파 상한을 적용한다.
- 변경 취소는 저장 시점으로 돌린다. 다른 니케를 보고 돌아와도 저장 전 초안을 유지한다. Save는 새 스냅샷을 만든다. 앱을 닫기 전 Save가 필요하다.

편집 중 최종 HP·공격력·방어력을 C# 계산 API로 미리 계산한다. 입력이 맞지 않으면 이유를 표시하고 저장을 거절한다. 전투력은 새로 추정하지 않고 **수집 전투력**으로 표시하며, 도감 정렬도 수집 전투력 순서를 유지한다.

## 데이터·계산 규칙

- 원본 API 응답과 이전 스냅샷은 유지한다. 편집한 캐릭터에는 `buildSource=manual`, 바뀐 OL 줄에는 `source=manual`을 기록한다.
- 수정한 OL 줄의 API 옵션 ID·원본 수치·잠금 상태를 새 수치의 관측 근거인 것처럼 재사용하지 않는다. 변경하지 않은 줄의 원본 정보는 유지한다.
- 장비 지문을 재계산하고, 그 장비의 이전 지문에 묶인 잠금 보완값은 해제한다.
- 스냅샷 ID로 저장 충돌을 확인한다. 다른 저장·동기화가 먼저 완료되면 오래된 스펙이 최신 값을 덮어쓰지 못한다.
- 다시 **내 스펙 동기화**를 수행하면 실제 수집값이 현재 스펙을 대체한다. 로컬 편집 스냅샷은 이력에 남는다.
- OL 공증은 버프다. 네이티브 공격력과 시전자 기준 공격력 공증의 기준값에 넣지 않는다. 차지 속도·명중률 옵션은 UI에서는 양의 크기로, 계산 계약에서는 기존 부호로 유지한다. 계산식은 이번 UI 작업에서 변경하지 않았다.
- 호감도는 돌파·코어 ±나 다른 입력을 변경해도 자동으로 낮추지 않는다. 입력·저장 상한은 일반 30, 필그림 또는 오버스펙 40이다. 기존 프로젝트의 클라이언트 추출 `CharacterTable.json`의 `corporation_sub_type`을 사용하며, 출처 hash와 매핑은 `catalog/character-growth.json`에 보관한다. 현재 공개 목록 200명 중 194명이 추출 자료와 매칭된다. 비필그림의 하위 유형 자료가 없으면 일반형이라고 추정하지 않고 상한 미확인으로 두며, 편집 안전 범위 0~40만 적용한다. 라피: 레드 후드는 엘리시온이지만 subtype 1이므로 40을 유지한다.
- 스탯 계산 자료나 스킬 효과 구현이 부족한 캐릭터의 기존 미완료 상태를 유지한다. 편집 지원이 전체 캐릭터의 전투 시뮬레이션 지원을 뜻하지 않는다.

## 기능별 출처

계정 대표 이미지는 `Game/GetUserProfileBasicInfo.basic_info.icon_id`를 수집한다. 공식 `character/character_avatar_map.json`의 ID → `resource_id`·`costume_index` 매핑과 블라블라 `getAvatar`/`SM_CHARACTER_URL`의 `character/si/si_c{resource:03}_{costume:02}_s.png` 경로를 따른다. `profile_team`의 첫 캐릭터를 대표 이미지로 추정하지 않는다. 수집 성공 후 `AccountConnection.profileIconId/avatarPath`를 갱신하고, 공식 PNG·URL·해시는 로컬 `assets/account-avatars/`, `catalog/account-avatar-<id>.json`에 캐시한다. 계정 목록·계정 설정에서 같은 얼굴 이미지를 사용한다.

| 기능 | 출처 | 현재 파일 |
|---|---|---|
| 장비 선택창·강화·OL 종류/수치 선택·스킬·소장품 렌더러 | Nikke-Local-Lab `editor.js`, 고정 커밋 `c05fc1c392a523b9e17ebe0cbd4811bed9c19adb` | `apps/desktop-ui/local-lab-detail.js` |
| 옵션 명칭·정확한 수치 표시·색상 | Local Lab RuntimeMaterializer 및 상세 렌더러 | 위 렌더러, `spec_presentation_assets.py` |
| 전체 화면 스타일 | 같은 커밋의 `editor.css`, 바이트 보존 | `apps/desktop-ui/editor.css` |
| 장비 이름·클래스·부위·이미지 ID | 공식 블라블라 `equip/ItemEquipTable-ko.json` | `tools/data-pipeline/spec_presentation_assets.py` |
| 장비 이미지 | 공식 블라블라 `icon/equip/{resource_id}.png` | 로컬 `data/local/presentation/assets/equipment/` |
| 소장품·애장품 이미지 및 표시 자료 | 공식 블라블라 `favorite_rare_map`, `favorite_<tid>`, `icon/favoriteitem/` | 로컬 `data/local/presentation/assets/collections/` |
| OL 15단계 값 | 기존 고정 P01 `game-catalog.json`의 `optionSteps` | `spec_presentation_assets.py` |
| 별·코어 이미지 | 사용자 제공 블라블라 ZIP | 기존 `assets/ui/star-*.png`, `evolve.png` |
| 붙인 성장 ± 조작, UI와 저장 계약 연결 | 이번 작업에서 작성 | `apps/desktop-ui/local-lab-adapter.js`, `app.js`, `simul.css` |
| 입력 검증·계산 미리보기·스냅샷 저장 연결 | 이번 작업 + 기존 P01 저장소/P02 계산 서비스 | `CharacterEditService.cs`, API `Program.cs` |

공식 캐시에는 장비 120종, 소장품·애장품 33종, 이미지 105개를 보관했다. 장비 선택창은 Local Lab과 같이 T9/T10을 제공하며, 이미 수집된 낮은 티어의 표시도 지원한다. 원본 URL과 SHA-256은 `spec-presentation.json`에 남긴다. 다운로드 파일은 Git에 포함하지 않는다. `build:desktop`과 이미지 준비/갱신 과정에 이 자료 준비를 연결했다.

## 검증

- `CharacterEditTests`: 성장/스킬 범위, OL 부호·합법 수치·중복·T9 금지, 소장품 무기/애장품 조건, 공통 큐브, 원본 보존, 오래된 요청 거절.
- `StorageTests`: 실제 SQLite에 새 편집 스냅샷 저장, 과거 이력 보존, 저장 충돌, 이후 API 수집값 반영.
- `check_spec_editor.py`: **분리된 복제 DB/5186 포트**에서 실제 장비 선택·15단계 값·성장 경계·스킬·소장품·큐브 변경, 저장 후 재접속, 니케 간 초안 유지 확인. 실사용 DB는 편집하지 않았다.
- `check_account_ui.py`: 기존 콘솔 9개·큐브 16개, Save 요청 형식, 별/코어의 인접 배치 유지.
- 1500/850/500px에서 가로 넘침 없음. 브라우저 스크립트 오류·실패 요청·깨진 이미지 없음. 증거는 Git 제외 `artifacts/desktop/spec-editor-ui/`.
- 전체 C# 111개·Python 14개 통과, 원본 코드 해시 보존 확인. 갱신한 EXE의 실제 WebView2에서 카드 200개·깨진 이미지 0, 기존 5인 상세와 레이드 검산 저장도 확인했다.
