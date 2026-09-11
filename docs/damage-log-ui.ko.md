# 앨리스 발당 피해 로그 및 버스트 전술 설정 UI 연동·결함 수정 보고서 (U3)

## 현재 UI: 버스트 설정 단순화 (2026-09-11, Director 후속 변경)

사용자 지정 스크린샷의 단계별 카드만 설정으로 남긴다. 참여 체크, 위/아래 순서 변경, 첫 시전자 표시, 빠른 설정 3개와 서버 저장을 유지한다. 별도 III 순환 모드·첫 시전자 선택·쿨다운 대기 정책, 중복 빠른 우선순위, 버스트 사용 안 함/1회 실행/시작 시점 입력은 제거했다. 사격 조작·차지 방식 및 실제 피해/버스트 기록은 유지한다.

- I/II는 체크된 후보의 표시 우선순위를 사용한다. III는 체크된 후보를 표시 순서대로 순환하고 그중 첫 번째를 첫 시전자로 지정한다. 준비되지 않으면 다음 사용 가능한 허용 니케를 선택한다(`next_ready`).
- 화면 로드·서버 복원·저장 시 `normalizeVisibleBurstTactics`가 위 규칙으로 UI 모델을 정규화한다. 과거의 숨은 순환 부분집합·별도 첫 시전자·`wait_preferred`는 현재 편집 화면의 실행 설정으로 유지하지 않는다. 복원만으로 서버에 PUT하지는 않으며, 이후 사용자가 변경/저장할 때 단순화된 설정을 저장한다.
- 모든 III 후보를 해제하면 첫 시전자는 없고 불완전 설정 진단을 표시한다. 제외 니케를 몰래 발동시키지 않는다.
- 실행은 `conditions.autoBurst = { tactic }`, `casts = []`, `fullBurstWindows = []`로 통일한다. 엔진/API의 기존 지정 시전·일반 DTO 기능은 삭제하지 않았다.
- 회차 홀짝만으로 성공/대체 여부를 추정하던 결과 판정을 제거하고 실제 버스트 시전자·시각을 기록으로 표시한다.

근거: `apps/desktop-ui/app.js`, `apps/desktop-ui/burst-tactics.js`. 아래 U3 보고서는 **변경 이전의 수용 이력**이며, DTO 원형 보존 설명은 범용 `damage-log-adapter.js`의 계약에 해당한다. 현재 편집 화면의 조작·정규화 규칙은 이 절을 우선한다.

검증: `tests/q3/check_ui_contract.mjs`의 26개 검사 통과(숨은 기존 옵션 정규화, 제외/순서/빈 III, 늦은 서버 응답 방어 포함). 증거: `artifacts/director/compact-burst/ui-0fc5bff4-4e49-40fd-ba32-22d1286acba3/summary.json`.

`check_integrated_live.py`의 실제 API/Edge 검증도 통과했다. 편성 순서 프리셋에서 누아르 첫 시전자, 앨리스만 사용 후 누아르 재허용·순서 이동·제외, 제거한 입력 부재, 서버 저장→브라우저 캐시 삭제→복원→180초 실행, III 앨리스 단독 발동, JSON/CSV 원문 다운로드, 1500/850/500px 무넘침, JS 오류 0을 확인했다. 합성 503 주입 시 거짓 성공 다운로드가 없는 것도 별도 확인했다. 증거: `artifacts/director/live-a751d113203748f5886aa7fabaf88679/summary.json` 및 `ui-before.png`, `ui-request.json`, `ui-response.json`. 이 실행은 기준 HEAD `77b3cce` 위의 이번 미커밋 UI 변경을 검증한 것이며, 보고서의 commit 필드만으로 미커밋 변경을 식별할 수는 없다.

검사는 비사용 중인 격리 복사본 `artifacts/b2/integration-bfe7311e79a24060abb9c7161f21e7ac/data`에서 수행했다. 원본 계정 4개 테이블 논리 해시는 실행 전후 같고, 사용자 사용 중인 5181 서버의 계정 복사본은 건드리지 않았다. 실행 파일 재배포나 실게임 정확도 검증은 이번 변경에 포함하지 않는다.

기존 `check_damage_log_ui.py`의 합성 HTTP/실제 엔진 fixture 브라우저 회귀도 통과했다(`artifacts/ui/verification/summary.json`, 앨리스 183타격, JS 예외 0). 격리 환경에는 일부 초상화/장식 이미지가 없어 404와 대체 이미지가 나타났으므로 이미지 완전성 검증을 뜻하지 않는다. 현재 5181 서버에서 변경된 JS를 제공하는 것까지 HTTP 200으로 확인했다.

---

2026-09-11. UI 담당(U3) 통합 결함 수정 및 실 fixture 검증 완료 보고서.
소유: `apps/desktop-ui`, UI 전용 테스트(`tools/data-pipeline/tests/check_damage_log_ui.py`), 본 문서 `docs/damage-log-ui.ko.md`.
통합 기준 커밋: `a0738accb16500e52621811fac0dac7259cb7f76` (엔진 `3b92101`, Backend `b63ad12`, UI `3f9b717` 포함).
대조 계약: Backend `bf19679`(`docs/damage-log-api-contract.ko.md`), Engine `908047f`(`docs/damage-log-engine-contract.ko.md`), Q3 검수 재현 `514daf4`(`docs/damage-log-verification.ko.md`).

---

## 1. 개요 및 U3 결함 수정 범위

Director의 통합 점검 및 Q3 검수(`514daf4`), 그리고 실 브라우저 통합 검사(`live-bf97c1ce`, `live-c1ff4cf9`, `live-d6131ccb`)에서 확인된 계약 결함 및 실연동 잔여 이슈를 전면 분석하여, `apps/desktop-ui` 전반의 어댑터 및 컴포넌트 로직을 E1/B2/B1 계약에 완벽히 정렬했습니다.

### U3 주요 결함 수정 요약
1. **실행 요청 `conditions.damageLog` 누락 및 legacy 혼용 해소**:
   - 시뮬레이션 실행 요청(`POST /api/runtime/skill-replays`)에 사용자가 선택한 대상 니케(`conditions.damageLog = { characterId }`)를 명시적으로 주입.
   - 명시 `tactic` 사용 시 서버/엔진에서 400 거부(ArgumentException)를 유발하던 legacy `burst3Rotation` 및 `unavailablePolicy` 혼용을 제거하고 `burst3Rotation: []`, `unavailablePolicy: 'next_ready'`로 안전하게 규격화.
2. **서버 응답 Envelope 및 상태 매핑 완전화**:
   - 과거 `res.hits` 가정을 제거하고, 실제 Backend envelope인 `res.replay.result.damageLog` 및 직접 실행 결과 `saved.result.damageLog`를 파싱.
   - `collectionStatus`와 `schemaVersion`/`complete`/`0(no_damage)`/`truncated`/`uncollected`/`unsupported_schema`/`api_error`를 명확히 구분.
   - API 통신 오류 시 uncollected로 침묵하지 않고 `api_error`로 명시적 상태 반환.
3. **버스트 전술 DTO 왕복 및 검증 무결성 확보**:
   - `burst3Rotation`의 임의 부분집합 및 순환 순서를 DTO 왕복 시 100% 보존.
   - `firstBurst3CharacterId = null`인 경우 빈 값(기본값)으로 서버 및 UI 간 무결하게 왕복 보존.
   - 우선순위 고정 모드(`stage3Mode: priority_only`)에서 1순위와 다른 첫 시전자를 지정할 경우 조용히 대체하지 않고 `priority_only_mismatch` 검증 오류를 진단하고 DTO 변환 시 명시적 거부.
4. **실API 비동기 복원 준비 경쟁(Race Condition) 및 allowlist 빈 편성 노출 방지**:
   - 페이지 새로고침 시 `document.body.dataset.ready='true'`가 편성 로드(`formation.load`) 및 전술 동기화(`tacticsManager.syncFromServer`)보다 먼저 노출되어, 비행 중 빈 편성 스냅샷에서 `allowlist: {}`가 로컬 캐시에 저장되고 체크박스가 일시적으로 모두 `checked` 상태로 노출되던 비동기 경쟁 해소.
   - `refresh()` 실행 시 즉시 `ready='false'` 설정 후 `formation.load()` 완료로 5인 편성 확정 -> `tacticsManager.syncFromServer()` 실행 -> `raid` 탭 렌더링 완료 후 최종 `ready='true'` 설정 보장.
   - `burst-tactics.js`의 `syncFromServer`에 `members.length === 0` 가드를 추가하고, `fromServerTacticDto`에서 `allowedCharacterIds` 및 참조 ID 기반으로 빈 편성 상태에서도 허용/제외 상태가 유지되도록 보강.
   - `loadLocalTactics`에서 `priority_only` 모드의 단일 버스트 III 회전 시 제외 대상이 `true`로 기본값 전이되지 않도록 방어.
5. **실제 필드 및 계산 근거 명시 매핑**:
   - numeric `kind` (2=NormalHit, 3=DirectSkillHit, 4=AdditionalHit), `source`, `hitId`/nullable `shotId`, raw `chargeRatioRaw / 10000`, nullable `fullCharge`/`effectiveChargeFrames`/`actualChargeFrames`, `hit.crit`/`core`/`fullBurst`, `ownBurstEffectActive` 매핑.
   - 자체 버스트 활성 구간을 하드코딩 `startFrame + 600`으로 생성하지 않고 실제 `ownBurstEffectActive`가 활성화된 타격들로부터 정밀 구간 도출.
   - 직접 스킬만 있는 로그(`shotId: null`)에서 발사 수를 0으로 정확히 계산 (`uniqueShots` 식 개선).
   - "명중/발사 비율을 명중률로 표시하지 않는다(펠릿/추가타로 100% 초과 가능)" 원칙에 따라 `183회 발사 / 183회 명중` 형태로 표시.
6. **서버 응답 원본 Blob 다운로드 보장 (JSON 및 CSV exact bytes)**:
   - CSV 내보내기는 서버의 RFC 4180 원본 바이트 일치를 유지(Director `exactBytes: True` 통과).
   - JSON 내보내기에서 기존 `api()` 파싱 후 `JSON.stringify(res, null, 2)` 클라이언트 측 재직렬화로 인해 서버 원본 바이트와 불일치하던 결함을 해소.
   - 서버의 HTTP 응답 원본 `res.blob()`을 직접 `downloadBlob`으로 다운로드하여 서버 바이트 100% 보존.
   - 서버 내보내기 실패 시 로컬 합성 성공으로 마스킹하지 않고 명시적 에러 상태 보고.

---

## 2. API 계약 및 DTO 매핑 상세 명세

### 2.1 실행 요청 (`POST /api/runtime/skill-replays`)
```json
{
  "snapshotId": "acc-snap-01",
  "characterIds": ["5011", "5008", "5009", "5004", "5044"],
  "conditions": {
    "damageLog": {
      "characterId": "5004"
    },
    "autoBurst": {
      "tactic": {
        "schemaVersion": 1,
        "allowedCharacterIds": ["5011", "5008", "5009", "5004", "5044"],
        "stage1Priority": ["5011"],
        "stage2Priority": ["5008"],
        "stage3Priority": ["5004", "5009", "5044"],
        "burst3Rotation": ["5004", "5009", "5044"],
        "firstBurst3CharacterId": "5004",
        "unavailablePolicy": "next_ready"
      },
      "burst3Rotation": [],
      "unavailablePolicy": "next_ready"
    }
  }
}
```

### 2.2 BurstTacticSettings (schemaVersion: 1) 양방향 DTO 매핑

| 서버 DTO 필드 | UI 내부 모델 (`apps/desktop-ui`) | 변환 및 보존 규칙 |
|---|---|---|
| `schemaVersion` (int) | `tactics.version` | 항상 `1` 전송 (UI 로컬 설정 v2) |
| `allowedCharacterIds` (string[]) | `tactics.allowlist` | `allowlist[id] !== false`인 편성 니케 목록 |
| `stage1/2/3Priority` (string[]) | `tactics.priority.stage1/2/3` | 각 단계별 사용자 지정 순위 배열 |
| `burst3Rotation` (string[]) | `tactics.burst3Rotation` | 부분집합 및 순환 순서 원본 보존 (`['5044', '5009']` 등) |
| `firstBurst3CharacterId` (string\|null) | `tactics.firstCaster` | 지정되지 않았거나 빈 문자열일 때 `null` 완전 보존 |
| `unavailablePolicy` (string) | `tactics.fallbackPolicy` | `'next_ready'` 또는 `'wait_preferred'` 보존 |

---

## 3. 검증 결과 및 증거

### 3.1 Q3 독립 수용 검사 전체 재실행 결과 (25/25 통과)
Q3 검수 담당이 커밋 `514daf4`에서 작성한 독립 검수 스크립트(`check_ui_contract.mjs`)를 확정 엔진 예제(`result.json`) 환경에서 직접 실행하여 **25개 검사 전원 통과**를 확인했습니다.

- **실행 명령**:
  ```powershell
  node check_ui_contract_runner.mjs .../result.json .../artifacts/ui/verification
  ```
- **검증 결과 JSON**:
  ```json
  {
    "output": "artifacts/ui/verification/ui-8b29353d-e061-48b0-b62f-84bfa9666c5c",
    "passed": 25,
    "failed": 0,
    "failures": []
  }
  ```

| 번호 | Q3 검증 항목명 | 기대 결과 | 판정 |
|:---:|---|---|:---:|
| 1 | `fresh_engine_log_sum_ids_and_180_seconds` | 180초/10800F 한도, 누적 합계, 183타격 일치 | **통과** |
| 2 | `actual_wire_envelope_is_collected` | `res.replay.result.damageLog` 수신 시 `collected` | **통과** |
| 3 | `direct_saved_result_is_collected` | 직접 실행 `saved.result.damageLog` 수신 시 `collected` | **통과** |
| 4 | `wire_hit_context_and_charge_mapping` | hitId, shotId, frame, damage, chargeRate, hit flags 매핑 | **통과** |
| 5 | `complete_zero_is_no_damage` | 대미지 0 로그 수신 시 `no_damage` 상태 분리 | **통과** |
| 6 | `null_and_legacy_are_uncollected_without_mock` | 미수집/레거시 리플레이 시 mock 대체 없이 `uncollected` | **통과** |
| 7 | `different_character_is_uncollected` | 다른 니케 로그 수신 시 `uncollected` 처리 | **통과** |
| 8 | `truncated_is_not_uncollected` | `truncated: true` 시 uncollected로 누락되지 않음 | **통과** |
| 9 | `unknown_schema_is_explicit` | 스키마 999 수신 시 `unsupported_schema` 명시적 상태 반환 | **통과** |
| 10 | `api_failure_is_not_uncollected` | HTTP 500 등 API 오류 시 `api_error` 명시적 상태 반환 | **통과** |
| 11 | `tactic_standard_roundtrip` | 기본 DTO 양방향 직렬화 일치 | **통과** |
| 12 | `tactic_rotation_order` | 순환 순서 변경 DTO 양방향 직렬화 일치 | **통과** |
| 13 | `tactic_rotation_subset` | 부분집합 순환 DTO 양방향 직렬화 일치 | **통과** |
| 14 | `tactic_single_nonpriority_rotation` | 단일 비우선 순환 DTO 양방향 직렬화 일치 | **통과** |
| 15 | `tactic_null_first_caster` | `firstBurst3CharacterId: null` 양방향 직렬화 일치 | **통과** |
| 16 | `tactic_wait_policy` | `unavailablePolicy: 'wait_preferred'` 직렬화 일치 | **통과** |
| 17 | `priority_only_conflicting_first_caster_is_rejected` | 고정 모드와 상충되는 첫 시전자 거부 및 진단 오류 | **통과** |
| 18 | `stale_id_diagnosed` | 편성 제외 니케 잔존 시 `stale` 상태 진단 | **통과** |
| 19 | `server_restore_keeps_null_and_subset` | 서버 GET 복원 시 null first caster 및 부분집합 순환 보존 | **통과** |
| 20 | `request_selects_damage_log_character` | submit 콜백이 `conditions.damageLog = { characterId: '5004' }` 생성 | **통과** |
| 21 | `request_has_no_legacy_tactic_mix_next_ready` | tactic 전송 시 legacy 옵션 충돌 부재 (next_ready) | **통과** |
| 22 | `request_has_no_legacy_tactic_mix_wait_preferred` | tactic 전송 시 legacy 옵션 충돌 부재 (wait_preferred) | **통과** |
| 23 | `direct_skill_only_UI_shot_count_is_zero` | shotId가 null인 직접 스킬 타격을 발사 수로 왜곡하지 않음 | **통과** |
| 24 | `late_server_restore_preserves_account_switch` | 계정 전환 중 도착한 이전 비동기 응답 폐기 | **통과** |
| 25 | `late_server_restore_preserves_local_edit` | 로컬 편집 중 도착한 이전 비동기 응답 폐기 | **통과** |

---

### 3.2 UI 종단간(E2E) 브라우저 검증 결과
Playwright(Edge/Chromium) 헤드리스 브라우저 환경에서 확정 엔진 예제(`result.json`, 183타격)와 Backend REST Envelope를 주입하여 실 화면 렌더링 및 인터랙션을 검증했습니다.

- **테스트 스크립트**: `tools/data-pipeline/tests/check_damage_log_ui.py`
- **실행 명령**:
  ```powershell
  python tools/data-pipeline/tests/check_damage_log_ui.py
  ```
- **실행 결과 요약 (`artifacts/ui/verification/summary.json`)**:
  ```json
  {
    "tacticPayloadVerified": true,
    "comparisonRows": 5,
    "aliceRealHitCount": 183,
    "shotHitDistinctionVerified": true,
    "selfBandsCount": 5,
    "teamBandsCount": 5,
    "calculationAuditVerified": true,
    "uncollectedVsMockSeparated": true,
    "inBrowserUnitTestsPassed": true,
    "success": true,
    "widthsChecked": [
      1500,
      850,
      500
    ],
    "jsErrorsCount": 0,
    "serverTacticContractVerified": true,
    "realEngineFixtureVerified": true,
    "maxSecondsLimit": 180,
    "csvRfc4180Verified": true,
    "dtoRoundTripVerified": true
  }
  ```

---

## 4. 결론 및 인계 사항

1. **실API 비동기 복원 경쟁 및 JSON 원문 바이트 일치 보완 완료**:
   - `app.js`, `burst-tactics.js`, `damage-log-adapter.js`, `damage-log.js` 전반의 계약 정합성을 완료했습니다.
   - Director 브라우저 실연동 검사에서 발견된 초기 빈 편성 스냅샷의 allowlist 노출 경쟁을 `refresh()` 단계별 게이팅(`formation.load` 선행 확정 및 ready 지연)으로 해소했습니다.
   - CSV 원문 일치(`exactBytes: true`)에 이어 JSON 내보내기도 클라이언트 측 재직렬화를 제거하고 `res.blob()` 직접 다운로드로 전환하여 서버 원문 바이트 일치를 보장했습니다.
   - Q3 독립 검수 25개 테스트 전원 통과 및 Playwright E2E 렌더링/무넘침/JS에러0 검증을 재확인했습니다.
2. **타 작업공간 보존 준수**:
   - `Backend`, `시뮬레이션-엔진-담당`, `Director`, `tests/q3` 등 타 영역 파일을 일체 수정하지 않고 UI 담당 범위(`apps/desktop-ui`, `tools/data-pipeline/tests/check_damage_log_ui.py`, `docs/damage-log-ui.ko.md`) 내에서만 작업을 완료했습니다.
   - `package-lock.json`은 untracked 상태로 유지되었습니다.
3. **Director 재검수 인계**:
   - UI 브랜치 커밋을 기준으로 Director(`64ad9a5` 최신 검사기)의 실연동 통합 검증 및 독립 검수 재실행이 가능하도록 인계합니다.
