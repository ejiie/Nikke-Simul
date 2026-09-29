# 원본 main 및 실제 사용자 실행본 갱신 — 2026-09-29 (보스 거리·약점 속성)

## 현재 사용 경로

**사용자는 기존 바탕 화면 `Nikke Simul.lnk`를 실행하면 된다.** 대상은 원본 `C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe`이며 바로가기·경로는 변경하지 않았다. 원격 push는 하지 않았다.

## 배포 내용

사용자 승인(2026-09-29, "배포 실행", 앱은 사용자가 미리 종료). 배포 제품은 [F-COND-1 배정·검수 기록](boss-distance-element-assignments-2026-09-28.ko.md)에서 독립 QA를 통과하고 Director `52ff31f`로 통합한 트리다(엔진 `f374c1d`, Backend `97ba7bf`, UI `77264bf`, QA `d71c7a2`). 이전 배포([2026-09-28 client_f32](desktop-release-original-2026-09-28.ko.md))에 이어진다.

사용자에게 보이는 변화:

- 솔로 레이드·단일 덱 통계 "전투 조건"의 적정 거리·우월 코드 체크박스가 **작은 아이콘 버튼 + 현재 값**으로 바뀌었다.
- **보스 거리 팝업**: 0–100 또는 미설정, 현재 덱 멤버별 적정 사거리와 판정, 무기군별 적정 사거리 표(예외 하란 #5042 SR 25–45, RL 0–0 "보너스 없음·확인 필요").
- **보스의 약점 속성 팝업**: 5속성 이미지 + 없음, "보스의 약점 속성 — 이 속성 니케가 우월 코드 보너스를 받습니다" 경고, 속성별 덱 멤버.
- 판정은 니케별: 거리가 자기 사거리 안(양끝 포함, 잠정)이면 평타 적정 거리, 속성이 약점과 같으면 모든 피해 우월 코드.
- 이전 체크박스 방식으로 저장된 결과는 "이전 방식(전원 적용)"으로 표시되며 그대로 재현된다. 새 규칙 버전 때문에 이전 단일 덱 통계 실험은 조회만 가능하다.

## 절차와 결과

1. **사전 확인:** 원본 배포 경로 프로세스 없음, 5180·5181 미사용, 원본 작업 트리 깨끗, 원본 `main` = `cd004f1`.
2. **보존 사전 스냅샷:** 계정 DB 8개 테이블 행 hash, presentation 447파일 hash, 사용자 미추적 `package-lock.json` hash(읽기 전용).
3. **원본 main 통합:** `cd004f1` → Director `4b4403e` **fast-forward**(로컬). 이후 추가 커밋은 이 기록 등 문서뿐이다.
4. **runtime 준비(이번 배포에만 추가된 단계):** 원본 `data/local/runtime/current.json`을 Director `artifacts/director/release-original-20260929/runtime-current-before.json`에 백업한 뒤 실행:

```powershell
python tools/data-pipeline/prepare_combat_conditions.py --runtime-root data/local/runtime --source-roster C:/Users/user/Documents/GitHub/Nikke-Dmg-Simulator/Database/raw/blabla_roledata.json
```

   결과: 새 runtime `9c98c91c6df670a35c9a2da0446961a61141cb5be19ca9718e608120608e71cd`(Backend·QA 격리 실행과 같은 ID), 192명, 원천 roster SHA256 `8568963a…c304348`. `current.json`만 새 ID를 가리키도록 바뀌었고, 기존 runtime 디렉터리 3개는 그대로 남았다(이전 current `30b3b0be…`의 catalog 내용 hash가 ID와 일치 — 불변). 네트워크·계정 접근 없음.
5. **백업:** 기존 실행 파일 폴더(636파일, 238,258,035바이트)를 원본 `artifacts/desktop-backups/before-main-20260929/`에 복사.
6. **빌드:** 원본 위치에서 `./scripts/desktop.ps1 -Action build -DataRoot '…/data/local' -Port 5180`(NIKKE_PYTHON 기존 runtime Python). 종료 코드 0, 경고·오류 출력 없음. `desktop.settings.json`은 이전과 같다.

| 원본 배포 파일 | 새 SHA256 |
|---|---|
| Nikke Simul.exe | `03f379af2c4c0c6e311b8c692e6d630356e7b9b59cfe000aaaecea33247f32fd` |
| Nikke Simul.dll | `767ef65b6c3b9f9c91e5f58f12037fb57d9189e06bbf38c10edad8a0ed2db4de` |
| backend/Nikke.Api.dll | `97c684fa9b69877bbb7eb17a68d8fc9221e092ce7cfb450be5c352f82b7dc109` |
| backend/Nikke.Engine.dll | `dca369ed076bdf80f71564e39c251abcf705294a835a63c0cc2b98ce8baca114` |
| backend/Nikke.Data.dll | `e53c79a3a8147361ba8a576ccc45966a1bc2edee420db96f3bca482193ea63dd` |

## 실제 사용 경로 검증

1. **바탕 화면 바로가기** 실행: 원본 `Nikke Simul.exe`(PID 33864)가 `backend/Nikke.Api.exe`(PID 28492)를 자식으로 시작, 5180 소유자 일치. `/api/health` projectRoot = 원본 경로.
2. `/editor/`가 제공하는 `index.html`, `app.js`, `combat-conditions.js`, `hit-policy.js`, `compute-adapter.js`, `single-deck-stats.js`, `damage-log.js`, `damage-log-adapter.js`, `burst-tactics.js`, `simul.css` 10개가 디스크와 **바이트 SHA256 일치**.
3. 새 API: `/api/runtime/combat-conditions` → runtime `9c98c91c…`, 대표 사거리 AR 25–45·MG 35–55·RL 0–0·SG 0–25·SMG 15–35·SR 45–100, 예외 SR `5042`. 실제 계정 snapshot의 멤버 프로필 조회 정상(예: 5004 SR 45–100). 계정 연결 3개 조회 정상.
4. 헤드리스 Chromium으로 솔로 레이드를 열고 두 팝업을 **열기만** 했다(ESC로 닫음, 적용·저장·검산 실행 없음, GET 외 요청 0, 페이지·콘솔 오류 0). 거리 팝업에 실제 덱 5명의 무기·사거리와 "거리 미설정", 무기군 표·하란 예외·원천 hash, 약점 팝업에 경고 문구와 속성별 실제 덱 멤버가 표시됐다. 캡처는 Git 제외 `artifacts/director/release-original-20260929/{distance,element}-dialog.png`(계정 정보 포함, 커밋하지 않음).
5. **보존 사후 비교:** 계정 DB 8개 테이블·presentation 447파일·`package-lock.json` 모두 배포 전과 **동일**. 의도한 변경은 `data/local/runtime`의 새 디렉터리 1개와 `current.json` 포인터뿐이다.

실제 WebView2 창 화면 관찰과 EXE `--smoke-output`은 수행하지 않았다. 실게임 사거리 규칙(양끝 포함·RL 0–0), 실측 대조, 성능은 범위 밖이다. 앱은 바로가기로 실행된 상태로 사용자에게 넘겼다.

참고(사용성 관찰): 거리가 미설정일 때도 슬라이더 손잡이가 50 위치에 표시된다(숫자 칸은 "미설정"). 동작 결함은 아니지만 사용자 피드백 후보로 남긴다.

## 되돌리기

앱 종료 후 (1) `artifacts/desktop-backups/before-main-20260929/`를 `artifacts/desktop/win-x64/`로 복원, (2) `data/local/runtime/current.json`을 백업본(`30b3b0be…`를 가리킴)으로 복원, (3) UI까지 되돌리려면 원본 `main`을 `cd004f1` 기준으로 맞춘다. 사용자 지시가 있을 때만 수행한다.
