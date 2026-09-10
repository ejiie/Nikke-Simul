# Windows 실행 파일 UI 이식 — 2026-09-09

사용자 지정 `ejiie/Nikke-Local-Lab`의 관리 UI를 이식했다. 계산 엔진은 이 프로젝트의 P01~P03 구현을 사용한다. 원본 화면은 HTML/CSS/JS이며 원본 실행 파일도 WinForms/WebView2 창으로 이를 표시한다. 같은 기술로 Windows `.exe`를 만들고 창에서 로컬 C# API를 자동 기동한다.

## 가져온 기능과 출처

원본 저장소: https://github.com/ejiie/Nikke-Local-Lab — 고정 커밋 `c05fc1c392a523b9e17ebe0cbd4811bed9c19adb`.

| 기능 | 원본 → 현재 위치 | 처리 |
|---|---|---|
| 전체 스타일 | `src/NikkeLocalLab.Admin.Api/wwwroot/editor/editor.css` → `apps/desktop-ui/editor.css` | 바이트 그대로. 기존 카드 비율, 색상, 헤더, 상세 탭, 장비 행 스타일 유지 |
| 홈·메뉴·도감·필터·상세 탭 뼈대 | 원본 `index.html` → `apps/desktop-ui/index.html` | 해당 화면 구조 재사용, 데이터/API 연결을 현재 서비스로 교체 |
| 캐릭터 카드, 아이콘 배열, 돌파 별·코어 배지 | 원본 `editor.js` → `apps/desktop-ui/cards.js` | 렌더러 이식. Lab UUID 대신 현재 캐릭터 ID 사용, 실제 수집 레벨 표시, 미확인 성장을 0으로 표시하지 않음 |
| 실행 파일 창 | `tools/NikkeLocalLab.ControlCenter.Desktop/Program.cs` → `src/Nikke.Desktop/Program.cs` | WinForms/WebView2 구조·크기·로딩 화면 재사용. 이 PC의 백엔드 기동·종료 및 DPI 대응 구현 |
| CDN 경로 계산·분류 아이콘 목록 | `scripts/materialize-nll-phase-d-presentation-assets.ps1` → `tools/data-pipeline/presentation_assets.py` | 공개 리소스 경로 알고리즘을 Python으로 이식. 다운로드·캐시·검증·ZIP 매핑 추가 |
| 계정 연결·자동 수집·정제·저장·수동 보완 | 현재 프로젝트 P01 → 새 `app.js` 연결 | 기존 세션·스냅샷 계약 유지. 이미지 갱신도 수집 성공 후 별도 백엔드 작업으로 실행 |
| 최종 스탯 | 현재 프로젝트 P02 C# 계산 API | Local Lab 상세의 HP·공격력·방어력 표시로 연결. 이전 웹 계산 UI 연결은 제거 |
| 5인 스킬 시뮬레이션·결과 저장 | 현재 프로젝트 P03 | 솔로 레이드 검산 화면 추가. 구성원별 평타·각 효과의 대미지 저장 |

출처 hash는 `sources.lock.json`, `docs/desktop-source-manifest.json`에 기록했다. 원본 CSS 수정 없이 필요한 연결 스타일과 작은 화면 메뉴 보정은 `simul.css`에 둔다.

원본 Local Lab의 PostgreSQL, 관리자 시작 코드, 특정 PC·관리자 계정 검사, 원본 게임 실행·설치본 변경, 재화 조작 및 profile revision API는 이식하지 않았다. 계정 설정은 싱크로·리사이클 룸·공통 큐브를, 니케 상세는 레벨·호감도·돌파·코어·스킬·장비·OL·소장품·장착 큐브 편집을 제공한다. 저장은 기존 SQLite 스냅샷 계약을 사용한다. [편집 범위와 기능별 출처](desktop-spec-editor.ko.md).

## 이미지

사용자 제공 `character-growth-images-20260908.zip`에는 캐릭터 PNG 199개와 UI 이미지 3개가 있다. manifest의 파일 크기·SHA-256과 PNG 시그니처를 전부 검사한 뒤 로컬에 가져왔다.

- 블라블라 공개 목록: 200명.
- ZIP 이름이 단일 캐릭터로 정확히 연결된 이미지: 197명.
- ZIP 누락·동명이인 때문에 블라블라 캐릭터별 리소스로 직접 수집: 3명. 드레이크: 그레이트 빌런, 별개 ID의 사쿠라 2명. 이름만으로 중복을 임의 선택하지 않는다.
- 사용하지 않는 ZIP 초상화 2개도 원본 보존을 위해 로컬에 남긴다.
- 캐릭터별 클래스·버스트·속성·무기 정보는 공개 `character/ko/nikke_list_v2.json`을 사용한다. 모든 버스트 단계인 레드 후드는 `AllStep → 5`로 매핑한다.
- 클래스 3종, 버스트 4종, 속성 5종, 무기 6종 및 화면용 이미지를 블라블라에서 수집했다. UI 이미지는 돌파·코어 3종을 포함해 25개이며 총 로컬 PNG는 227개다.
- 한계돌파는 별 3개의 채움 상태, 코어 강화는 `evolve.png` 위에 `1..6 / MAX` 텍스트를 얹는다. 숫자별 이미지가 따로 있는 것은 아니다.

`data/local/presentation/`에 이미지와 매핑, 원본 URL, SHA-256, ZIP hash를 저장한다. 계정 로그인 없이 공개 CDN만 조회한다. 캐시가 있으면 오프라인에서도 표시한다. 수집 실패는 상태에 남기고 검증된 기존 캐시를 유지한다. 이미지 갱신 실패 때문에 정상 계정 스냅샷을 무효화하지 않는다. 미확인 이미지는 명시적인 대체 표시를 쓴다. 이미지·manifest·계정 데이터는 Git 제외다.

## 실행

```powershell
npm run prepare:images -- -Zip 'C:/Users/user/Downloads/character-growth-images-20260908.zip'
npm run build:desktop
# artifacts/desktop/win-x64/Nikke Simul.exe 더블클릭
# 또는 빌드 후 실행:
npm run dev
```

실행 파일과 백엔드에 .NET 런타임을 포함했다. 이 PC의 프로젝트 경로와 기존 Python·Playwright 환경은 `desktop.settings.json`에 기록한다. EXE만 이동하는 독립 배포본은 아니다. 폴더 이동 시 새 경로에서 다시 빌드한다. WebView2 Runtime은 설치되어 있어야 한다.

시작 시 같은 프로젝트의 백엔드가 이미 있으면 연결하고, 없으면 동봉한 `backend/Nikke.Api.exe`를 숨김 실행한다. 다른 프로그램이 포트를 차지하면 연결을 거절한다. 종료 시 자신이 만든 백엔드만 정리하며, 그 백엔드의 진행 중 수집 작업도 취소·정리한다. 개발 서버에 연결한 창을 닫으면 개발 서버는 유지한다. 웹 UI는 같은 프로세스의 localhost만 탐색한다.

## 검산의 현재 한계

방어력 30,925 / 31,784를 선택할 수 있고 각각 누적 20억 전·후 조건으로 표시한다. 이번 검산 전체에 선택 방어력을 고정하며 자동 전환은 아직 없다. 버스트를 지정하면 리타 → 블랑 → 선택 B3의 1회 시전과 풀버스트 구간을 조건으로 저장한다. 현재 화면은 팀 게이지·자동 사이클·최적 5덱·확률 통계·육성 추천의 완료를 의미하지 않는다. 실측 자료 대조와 기존 P03 한계는 그대로 남아 있다.

## 검증

- `npm test`: C# 111개, 기존 스탯·전투 원본 hash 및 합성 fixture (스펙 편집 반영 후).
- `npm run test:web`: 공용 계산·스펙 표시 모델 7개.
- Python `unittest discover`: 14개 통과. ZIP 경로 이탈·hash 불일치·동명이인 매핑·CDN 장애 시 캐시 보존을 포함한다.
- `tools/data-pipeline/tests/check_desktop_ui.py`: 실제 저장 계정으로 카드/검색/필터, 5인의 표시 스탯과 API 일치, 단일 히트, 5인 검산 결과 저장을 검사한다. 실계정 편집·로그인은 하지 않는다.
- 실행 파일 `--smoke-output <로컬 경로>`: 실제 WebView2 창에서 메뉴 전환·이미지와 스크린샷, 자동 시작·종료를 확인한다. 이것은 UI 실행 검사이며 실게임 대미지 검증은 아니다.

저장 계정 193명/도감 200명, 5인 × 최종 스탯 3개 API 일치, 단일 히트 검산, 버스트 1회가 지정된 30초 5인 스킬 검산을 확인했다. HTTP 실패·스크립트 오류·깨진 이미지 0. 결과는 Git 제외 `artifacts/desktop/ui/acceptance.json`, 실제 WebView2 증거는 `artifacts/desktop/acceptance/`에 있다. 백엔드 자동 시작·종료와 기존 개발 서버에 연결 후 창만 종료하는 두 경우를 모두 확인했다. 낮은 해상도에서 원본 CSS의 겹치는 미디어 규칙이 메뉴 아이콘과 글자를 동시에 숨기던 문제는 보완 스타일로 해결했다.

## 2026-09-09 상세 UI 정정

- 이전 웹 프론트 `calculation.ts` import와 데스크톱 빌드 연결을 제거했다.
- Local Lab `editor.js`의 장비·성장·스킬·소장품 렌더러를 `local-lab-detail.js`로 가져왔다. 숫자 입력의 범위 검증을 추가하고, 실제 사용 성장 컨트롤은 사용자 요청에 따라 붙인 별·코어와 ±로 연결했다. `editor.css`는 원본을 유지한다.
- 옵션 명칭은 RuntimeMaterializer의 OverloadOptionDisplayName과 동일하다. 숫자는 원본 exactValueText, 옵션 합계는 소수 둘째 자리 표시를 사용한다. 원본 카탈로그 규칙처럼 차지 속도·명중률은 양의 크기로 표시하며 계산용 부호는 바꾸지 않는다.
- `local-lab-adapter.js`는 저장 스냅샷을 원본 UI의 projection으로 변환한다. 옵션 등급은 저장된 valueTier를 사용한다. 장비 능력치는 기존 C# 계산 결과를 연결하며 강화 중복 적용을 하지 않는다.
- 임의로 추가했던 옵션 잠금 select와 계산 패널은 상세 화면에서 제거했다. 백엔드의 기존 저장값과 계산 API는 보존한다. 이후 [장비 이미지·스펙 편집 작업](desktop-spec-editor.ko.md)에서 Local Lab 컨트롤을 계산 미리보기 및 스냅샷 Save에 연결했다.
