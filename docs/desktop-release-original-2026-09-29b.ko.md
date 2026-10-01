# 원본 main 및 실제 사용자 실행본 갱신 — 2026-09-29 2차 (전투 조건 정리·보스 선택)

## 현재 사용 경로

**사용자는 기존 바탕 화면 `Nikke Simul.lnk`를 실행하면 된다.** 대상은 원본 `C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe`. 바로가기·경로 변경 없음, 원격 push 없음.

## 배포 내용

사용자 지시(2026-09-29, "일단은 배포 먼저. 나도 써보면서 개선점 메모해두게"). 배포 제품은 [F-COND-2 배정·검수 기록](combat-conditions-cleanup-assignments-2026-09-29.ko.md)의 독립 QA `180f23b`(엔진 `1a86ec9`, Backend `aa1b71e`·`b977e77`, UI `59fe22d`)를 Director `89785ae`로 통합한 트리다. 이전 배포: [2026-09-29 1차](desktop-release-original-2026-09-29.ko.md).

사용자에게 보이는 변화([요구 R1~R8](user-requests-2026-09-29.ko.md)):

- 약점 팝업 설명 문장 삭제·속성 한국어만, 거리 팝업 표에 무기군 아이콘·"적정 사거리"·예외 한글 이름·미확정/출처 문구 삭제.
- 전투 조건에서 시간(180초 고정)·적 방어력·샷건 계수(발사 1회 고정) 입력 삭제, 크리티컬 기본 "확률 적용", 대미지 정책 유지.
- **방어력 자동 전환:** 30,925로 시작해 덱 누적 대미지가 20억을 넘긴 다음 타격부터 31,784. 결과·통계 카드에 전환 시점·캐릭터·누적 표시.
- **보스 선택(표시만):** 크리티컬·정책 아래 보스 카드, 더미 + 솔로 레이드 시즌 1~42 한국어 이름·이미지. 계산에는 영향 없음.
- 화면에서 캐릭터 코드·내부 출처 키·함수 번호·서버 원문 대신 한국어 이름·설명 표시. Nikke-Local-Lab 출처 표기 삭제.
- 이전 체크박스·고정 DEF·다른 시간으로 저장된 결과는 당시 조건으로 표시·재현된다.

**알려진 표시 결함(배포 후 수정 예정):** F2-Q-6 — 피해 검산 표에 `calculation.terms`, `effectiveAttack` 같은 저장 항목 이름과 영문 연산 설명이 그대로 보인다(계산 값은 정상). 수정 배정(U-FIX-7)은 사용자 지시로 배포 뒤로 미뤘다.

## 절차와 결과

1. **통합:** Director에 QA `180f23b`를 `--no-ff` merge(`89785ae`, 충돌 없음, 제품 트리 = `180f23b`). Director locked restore → Release build(경고 0·오류 0) → test **447/447**(Analysis 41, Sync 164, Compute 46, Core 196).
2. **사전 확인:** 원본 배포 경로 프로세스 없음(사용자가 앱을 닫아 둠), 5180·5181 미사용, 원본 작업 트리 깨끗, 원본 `main` = `e1ea771`.
3. **보존 사전 스냅샷:** 계정 DB 8개 테이블 행 hash, presentation 기존 449파일 hash, `package-lock.json` hash. 이번에는 보스 준비가 presentation에 새 파일을 추가하므로 "기존 파일 불변 + 추가 파일 목록"으로 비교했다(`artifacts/director/release-original-20260929b/preservation.py`).
4. **원본 main:** `e1ea771` → `89785ae` fast-forward(로컬). 이후 추가 커밋은 이 기록 등 문서뿐이다.
5. **사거리 runtime:** `prepare_combat_conditions.py`가 이전 배포 이후 바뀌지 않아 기존 runtime `9c98c91c…`를 그대로 사용했다(재실행 없음).
6. **보스 준비(이번 배포에 추가):** `tools/data-pipeline/prepare_solo_raid_bosses.py --presentation-root data/local/presentation` — enikk.app 공개 GraphQL·이미지를 받아 보스 43개(더미 + 시즌 1~42, 제외 0, complete true), 이미지 42개를 `presentation/assets/bosses/`에, 목록·내부 manifest·원천 스냅샷을 presentation 아래에 새로 썼다. 기존 파일은 덮어쓰지 않는다.
7. **백업·빌드:** 기존 실행 파일 폴더(636파일, 238,305,267바이트)를 `artifacts/desktop-backups/before-main-20260929b/`에 복사, 원본 위치에서 `./scripts/desktop.ps1 -Action build -DataRoot '…/data/local' -Port 5180`. 종료 코드 0, 경고·오류 출력 없음, `desktop.settings.json` 동일.

| 원본 배포 파일 | 새 SHA256 |
|---|---|
| Nikke Simul.exe | `43b56574908c4dc5fcae4f6f3016730a228b07cb912115aab4ecc5908e582b6a` |
| Nikke Simul.dll | `ccd0c18f492d4799a861d2bef460d16c930312663b503206e4acaca91963ece0` |
| backend/Nikke.Api.dll | `c401e4bae675dfd3fb96de1abdcf6ccebe292d5e27b00c34e542c92a065decbd` |
| backend/Nikke.Engine.dll | `c204cf9787f7f1c908d4034042ee08d7e7978889e9d61fdd7fcbc811667e09b5` |
| backend/Nikke.Data.dll | `2c77a0c039b12c7ef48f52dc9400e8e9338c6f10a37b1bd9aa391fe0de7d1969` |

## 실제 사용 경로 검증

1. **바탕 화면 바로가기** 실행: 원본 `Nikke Simul.exe`(PID 7240) → `backend/Nikke.Api.exe`(PID 21452), 5180 소유자 일치, `/api/health` projectRoot = 원본.
2. `/editor/`가 제공하는 UI 파일 19개(js·css·index.html)가 디스크와 바이트 SHA256 일치.
3. 보스 API 43개·complete true·기본 더미, 이미지 HTTP 제공 확인. 사거리 runtime `9c98c91c…`·`gameVerified` true. 계정 연결 3개 조회 정상.
4. 헤드리스 Chromium으로 솔로 레이드를 열어 전투 조건과 보스 선택 창을 **열기만** 했다(저장·검산 없음, GET 외 요청 0, 오류 0). 보스 창에 실제 시즌 이미지와 한국어 이름(앨트루이아·리버렐리오 바디·사치스러운 거미 …) 표시. 캡처는 Git 제외 `artifacts/director/release-original-20260929b/`.
5. **보존 사후 비교:** 계정 DB 8개 테이블·기존 presentation 449파일·`package-lock.json` 모두 **불변**. 추가된 presentation 파일 45개(보스 이미지 42 + 목록·manifest·원천 스냅샷)는 의도한 변경이다.

실제 WebView2 창 관찰·`--smoke-output`·실게임 대조·성능은 범위 밖. 앱은 바로가기로 실행된 상태로 사용자에게 넘겼다.

## 되돌리기

앱 종료 후 `artifacts/desktop-backups/before-main-20260929b/`를 `artifacts/desktop/win-x64/`로 복원하고, UI까지 되돌리려면 원본 `main`을 `e1ea771`로 맞춘다. 추가된 보스 파일은 이전 버전이 읽지 않으므로 남겨 둬도 된다. 사용자 지시가 있을 때만 수행한다.
