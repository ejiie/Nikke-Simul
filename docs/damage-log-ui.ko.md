# 앨리스 발당 피해 로그 및 버스트 전술 설정 UI 연동 보고서 (U2)

2026-09-11. UI 담당(U2) 후속 연동 및 독립 검증 보고서.  
대상: `apps/desktop-ui` 및 UI 전용 E2E 테스트(`tools/data-pipeline/tests/check_damage_log_ui.py`), 본 문서 `docs/damage-log-ui.ko.md`.  
기준 커밋: `a78c10c` (UI baseline), 대조 계약: Backend `bf19679`(`docs/damage-log-api-contract.ko.md`), Engine `908047f`(`docs/damage-log-engine-contract.ko.md`).

---

## 1. 개요 및 변경 목적

U1 단계에서 구현된 독립 UI 컴포넌트(대미지 로그 SVG 뷰어, 버스트 전술 설정기)를 바탕으로, U2 후속 작업 지시서에 따라 백엔드 B1(`bf19679`) 및 엔진 E1(`908047f`)의 공식 계약 DTO 스펙에 1:1로 결합하고 실제 서버 영속화/조회 및 시뮬레이션 연동을 보완했습니다.

### 핵심 준수 원칙
1. **서버 DTO 규격 엄격 준수 (`schemaVersion: 1`)**:
   - UI 내부 모델(`allowlist`, `stage3Mode: alternate | priority_only`, `firstCaster`)을 서버 계약 필드(`allowedCharacterIds`, `stage1/2/3Priority`, `burst3Rotation`, `firstBurst3CharacterId`, `unavailablePolicy`)로 완전하게 양방향 매핑.
2. **서버 저장과 로컬 캐시의 명확한 상태 구분**:
   - `localStorage` 저장만으로 "서버 저장 완료"로 오표시하지 않음.
   - `PUT /api/accounts/{id}/burst-tactic` 성공 시에만 `[서버 저장 완료 (PUT v1)]` 녹색 배지 부여. 미연결/실패 시 `[로컬 임시 보존 (서버 미동기화)]`로 상태 분리.
3. **Mock 조용히 대체 금지 (Fail-loud)**:
   - API 응답 부재/404 시 조용히 mock 데이터로 덮어쓰지 않고 `로그 미수집 상태 (uncollected)` 카드를 띄우고, 사용자가 명시적으로 `[합성 Mock 미리보기 (UI 검증용)]` 버튼을 클릭할 때에만 mock을 렌더링.
4. **발사 수 vs 명중 수 구분**:
   - `uniqueShots` (발사 ID 고유 수)와 `hitCount` (실제 대미지 발생 명중 수)를 상단 지표 카드 및 표에서 분리 표시.
5. **완전한 무넘침 반응형 레이아웃**:
   - 1500px(데스크톱), 850px(태블릿), 500px(모바일) 모든 뷰포트에서 가로 스크롤 넘침(overflow) 0px 검증.

---

## 2. API 계약 및 DTO 매핑 명세

### 2.1 BurstTacticSettings (schemaVersion: 1) 양방향 매핑

| 서버 DTO 필드 (B1/E1) | UI 모델 필드 (`apps/desktop-ui`) | 매핑 규칙 및 변환 로직 |
|---|---|---|
| `schemaVersion` (number) | `tactics.version` | 항상 `1`로 고정 전송 (UI 내부 설정 버전은 v2 유지) |
| `allowedCharacterIds` (string[]) | `tactics.allowlist` (`{[id]: boolean}`) | `allowlist[id] !== false`인 편성 니케 ID 목록으로 직렬화 / 역직렬화 |
| `stage1Priority` (string[]) | `tactics.priority.stage1` | 버스트 I단계 허용 니케 중 사용자가 지정한 순위 순서 배열 |
| `stage2Priority` (string[]) | `tactics.priority.stage2` | 버스트 II단계 허용 니케 중 사용자가 지정한 순위 순서 배열 |
| `stage3Priority` (string[]) | `tactics.priority.stage3` | 버스트 III단계 허용 니케 중 사용자가 지정한 순위 순서 배열 |
| `burst3Rotation` (string[]) | `tactics.stage3Mode` | `stage3Mode === 'alternate'`일 경우 `stage3Priority` 전체 후보 배열. `priority_only`일 경우 최상위 1명(`[stage3Priority[0]]`)만 전달하여 엔진 고정 발동 유도 |
| `firstBurst3CharacterId` (string\|null) | `tactics.firstCaster` | 버스트 III 첫 발동 니케 ID (`burst3Rotation` 내 포함 여부 검증 후 할당) |
| `unavailablePolicy` (string) | `tactics.fallbackPolicy` | `'next_ready'` (사용 가능한 다음 허용 니케 발동) 또는 `'wait_preferred'` (우선 니케 쿨다운 대기) |

### 2.2 서버 영속화 API 엔드포인트 연동
- **저장 (`PUT /api/accounts/{id}/burst-tactic`)**:
  - 페이로드: `{ snapshotId, formationSlots, tactic: toServerTacticDto(...) }`
  - 응답에 따라 `saved`, `draft_incomplete`, `stale` 상태 배지 실시간 갱신.
- **조회/복원 (`GET /api/accounts/{id}/burst-tactic`)**:
  - 계정 전환 또는 페이지 로드 시 서버에 저장된 전술 DTO를 수신하여 `fromServerTacticDto`로 UI 폼 컨트롤(체크박스, 순위, 드롭다운)에 즉시 복원.
- **시뮬레이션 실행 요청 연동 (`POST /api/runtime/skill-replays`)**:
  - `request.conditions.autoBurst.tactic` 필드에 B1/E1 규격의 `toServerTacticDto` 결과 객체를 그대로 주입하여 엔진이 전술에 따라 사이클을 시뮬레이션하도록 연결.

---

## 3. UI 컴포넌트 세부 보완 내용

### 3.1 버스트 전술 설정기 (`apps/desktop-ui/burst-tactics.js`)
1. **서버 동기화 상태 배지**:
   - `서버 저장 완료 (PUT v1)`: 서버 영속화 성공 상태.
   - `서버 저장 중…`: 네트워크 통신 진행 중.
   - `초안 저장 (단계 미완성)`: 일부 단계 니케 누락 또는 전원 제외 상태로 저장됨.
   - `편성 변경 불일치 (Stale)`: 서버 저장 당시의 편성과 현재 편성이 불일치함.
   - `로컬 임시 보존 (서버 미동기화)`: 오프라인이거나 서버 저장 실패 시 로컬 캐시로 안전 보존.
2. **수동 서버 저장 버튼**:
   - `[서버에 저장]` 버튼을 헤더 툴바에 추가하여 자동 저장 외에도 명시적 서버 영속화 가능.
3. **Stale ID 감지 및 정리**:
   - 편성에서 제외된 니케가 전술 설정에 잔존할 경우 `[제외된 니케 설정 정리 (N명)]` 버튼 제공 및 원클릭 제거.

### 3.2 대미지 로그 뷰어 (`apps/desktop-ui/damage-log.js`)
1. **수집 상태 진단 및 명시적 Mock 경계**:
   - 서버에서 로그가 아직 수집되지 않은 경우(`uncollected`), 빈 화면이나 자동 mock 대신:
     - *"아직 이 검산에 대한 시간별 타격 로그가 수집되지 않았습니다."* 안내 카드 노출.
     - `[합성 Mock 미리보기 (UI 검증용)]` 버튼을 명시적으로 노출하여 개발/검증 목적의 fixture 열람을 사용자 동의 하에만 렌더링.
   - 피해량이 0인 경우(`no_damage`): 피해 없음 전용 안내 카드 노출.
2. **발사 수 vs 명중 수 분리 표시**:
   - 지표 카드: **"발사 N회 / 명중 M회 (명중률 K%)"** 형식으로 명확히 구분.
   - 단일 발사에 복수 타격이 발생하는 샷건 펠릿 및 관통/추가타 메커니즘을 왜곡 없이 표현.
3. **구간 시각화 및 계산 근거**:
   - 앨리스 자체 버스트 10초 활성 구간(호박색 밴드)과 팀 풀버스트 10초 구간(시안색 밴드)의 중첩 시각화.
   - 타격 클릭 시 [계산 근거 보기] 패널(기초 ATK, 버프 ATK, DEF, 공방차, 배율, 정수화 정책, 유효 버프 목록) 지원.

---

## 4. 검증 결과 및 증거

### 4.1 UI 독립 E2E 브라우저 검증
- **테스트 스크립트**: `tools/data-pipeline/tests/check_damage_log_ui.py`
- **테스트 환경**: Python Playwright Edge (Chromium 기반 헤드리스 브라우저), 격리 로컬 웹서버, Mock REST API 라우트.
- **실행 명령**:
  ```powershell
  python tools/data-pipeline/tests/check_damage_log_ui.py
  ```
- **실행 결과**: 정상 종료 (Exit Code 0).

### 4.2 생성된 검증 결과 요약 (`artifacts/ui/verification/summary.json`)
```json
{
  "tacticPayloadVerified": true,
  "comparisonRows": 5,
  "uncollectedNoticeVerified": true,
  "aliceHitCount": 253,
  "shotHitDistinctionVerified": true,
  "success": true,
  "widthsChecked": [
    1500,
    850,
    500
  ],
  "jsErrorsCount": 0,
  "serverTacticContractVerified": true,
  "uncollectedVsMockSeparated": true,
  "maxSecondsLimit": 180
}
```

### 4.3 세부 검증 항목별 판정표

| 검증 항목 | 검증 절차 및 기대값 | 결과 | 비고 |
|---|---|:---:|---|
| **180초 상한 제한** | `seconds` input의 `max="180"` 및 초기값 180 확인 | **통과** | 초과 입력 차단 및 마이크로카피 안내 |
| **전술 프리셋 및 상태** | `[앨리스 우선]` 클릭 시 앨리스 1순위, 교대 순환 설정 확인 | **통과** | 체크박스, 순환 셀렉트 정상 반영 |
| **서버 저장 연동 (PUT)** | `[서버에 저장]` 클릭 시 `PUT /burst-tactic`으로 `schemaVersion: 1` DTO 전송 확인 | **통과** | B1 계약 필드 완벽 일치, 녹색 배지 확인 |
| **서버 복원 연동 (GET)** | 홈 탭 이동 후 레이드 탭 복귀 시 서버 저장 설정 복원 확인 | **통과** | 첫 시전자 5004, alternate 모드 복원 |
| **실행 요청 DTO 주입** | `POST /skill-replays` 호출 시 `conditions.autoBurst.tactic`에 DTO 포함 확인 | **통과** | `allowedCharacterIds`, `burst3Rotation` 등 확인 |
| **타임라인 대조 뷰** | 시뮬레이션 결과 수신 후 5개 회차별 설정 대조 판정 표 노출 확인 | **통과** | `comparisonRows: 5` 확인 |
| **미수집 vs Mock 분리** | 서버 로그 미제공 시 uncollected 경고 카드 노출 및 [합성 Mock 미리보기] 버튼 클릭 시에만 fixture 로드 | **통과** | 조용히 대체하지 않고 명시적 분리 완료 |
| **발사/명중 수 분리** | 요약 지표 카드에서 발사 횟수와 명중 횟수 분리 표시 확인 | **통과** | `shotHitDistinctionVerified: true` |
| **자체/팀 버스트 밴드** | `.band-self-burst` 및 `.band-team-burst` SVG 밴드 렌더링 확인 | **통과** | 앨리스 10초 자체 버스트 구간 정확히 표기 |
| **계산 근거 패널** | 발당 [근거 보기] 클릭 시 ATK, DEF, 공방차, 배율, 유효 버프 패널 토글 확인 | **통과** | 계산 근거 상세 표시 |
| **Stale 니케 감지/정리** | 편성 제외 니케 포함 시 `#btn-clean-stale` 노출 및 클릭 후 정상 정리 확인 | **통과** | 정리 후 버튼 소멸 확인 |
| **반응형 3단 폭 검증** | 1500px, 850px, 500px 뷰포트에서 가로 스크롤 넘침(horizontal overflow) 검사 | **통과** | 3개 해상도 모두 overflow 0px 확인 |
| **JS 콘솔 에러** | 전체 시나리오 실행 중 페이지 JavaScript Runtime Error 0건 확인 | **통과** | `jsErrorsCount: 0` |

---

## 5. 검증 구분 및 통합 의존성 보고

### 5.1 검증 수준 구분
- **UI 독립 E2E 브라우저 검증 (통과)**:
  - Playwright Edge를 이용한 렌더링, 이벤트 핸들링, 양방향 DTO 직렬화/역직렬화, 반응형 레이아웃, 상태 배지 전환 전 과정이 자체 테스트 환경에서 100% 통과했습니다.
- **합성 Mock Fixture 검증 (통과)**:
  - 앨리스 발당 대미지, 자체 버스트 구간, 크리티컬/코어 배율, 계산 근거 패널의 렌더링을 합성 fixture를 통해 완전히 검증했습니다.
- **실제 API 통합본 연동 (의존 중 - Pending Integration)**:
  - Backend(`bf19679`)와 Engine(`908047f`)의 실제 서버 프로세스가 배포된 통합 환경에서의 종단간(E2E) 호출은 현재 Director의 통합 빌드 및 통합 브랜치 제공을 대기하고 있습니다.
- **실게임 관측값 대조 (미실행 - Pending Game Capture)**:
  - 게임 클라이언트 실측 관측값 대조는 S2 담당 및 실측 캡처 데이터 제공 시까지 잠정 정확도 배지를 유지합니다.

### 5.2 Director 및 타 담당에게 필요한 사항
1. **Director**:
   - Backend `bf19679`, Engine `908047f`, UI `UI` 브랜치 변경사항을 통합 브랜치로 병합.
   - 실제 백엔드 서버(`dotnet run` 또는 Node API)와 엔진 라이브러리가 연결된 통합 실행 환경 제공.
2. **Backend (B2)**:
   - `PUT/GET /api/accounts/{id}/burst-tactic` 엔드포인트 및 `conditions.autoBurst.tactic` 처리 파이프라인 활성화.
   - `GET /api/runtime/skill-replays/{id}/damage-log` 엔드포인트의 실제 엔진 데이터 반환 지원.
