# 원본 main 및 실제 사용자 실행본 갱신 — 2026-10-02 (U-FIX-7 + E-BUG-1)

## 현재 사용 경로

**사용자는 기존 바탕 화면 `Nikke Simul.lnk`를 실행하면 된다.** 대상은 원본 `C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe`. 바로가기·경로 변경 없음. 원격 push는 이번 배포에 포함하지 않았다.

## 배포 내용

사용자 지시("배포", 앱은 사용자가 미리 종료). 새 작업 구조(구현 → 리뷰 → 독립 QA)로 처리한 두 건을 함께 배포한다. 이전 배포: [2026-09-29 2차](desktop-release-original-2026-09-29b.ko.md).

1. **U-FIX-7 — 피해 검산 표 표시·허용 목록**([진행 기록](audit-labels-assignment-2026-10-01.ko.md), QA `8705d17`, UI `42f4329`): 검산 표 단계 이름·연산 설명 한국어, 서버·저장 문자열은 등록 문구만 표시(나머지 일반 문구), 라벨 조회 own key 전용, 미등록 연산은 "저장된 연산 미확인", 로그 조회 실패 시 한국어 안내, `apps/desktop-ui` ESM 구문 테스트. 계산 값 변경 없음.
2. **E-BUG-1 — 수동 풀차지 모션 딜레이**([버그 기록](alice-manual-charge-delay-2026-10-02.ko.md), QA `dc8cb46`, 엔진 `d932716`): 손을 떼야 발사되는 UP형 차지 무기(앨리스 등)의 수동 풀차지가 매 발 [spotFirst + 재클릭]을 지불한다. 합성 5인 180초(앨리스·모더니아 3단계 로테이션) 팀 피해 −13.49%, 앨리스 발수 −29.7%, 풀버스트 횟수 불변. **엔진 규칙 버전 상향 — 이전 단일 덱 통계 실험은 조회만 가능하고 재개되지 않는다.** 이전 저장 replay는 저장 값 그대로 표시된다.

## 절차와 결과

1. **통합:** Director `2487bbd`(U-FIX-7) → `dab9fbf`(E-BUG-1), 제품 트리 = QA `dc8cb46`. Director Release 빌드 경고 0·오류 0, .NET 468/468, UI 7/7.
2. **사전 확인:** 원본 배포 경로 프로세스 없음, 5180·5181 미사용, 원본 작업 트리 깨끗, 원본 `main` = `3d84fe4`.
3. **보존 사전 스냅샷:** 계정 DB 8개 테이블 행 hash, presentation 494파일 hash, `package-lock.json` hash.
4. **원본 main:** `3d84fe4` → `ebb52b7` fast-forward(로컬). 이후 추가 커밋은 이 기록 등 문서뿐.
5. **데이터 준비:** 없음(사거리 runtime·보스 목록 준비 스크립트 변경 없음).
6. **백업·빌드:** 기존 실행 파일 폴더(636파일, 238,343,131바이트) → `artifacts/desktop-backups/before-main-20261002/`. 원본 위치 `./scripts/desktop.ps1 -Action build -DataRoot '…/data/local' -Port 5180`, 종료 코드 0, 경고·오류 출력 없음.

| 원본 배포 파일 | 새 SHA256 |
|---|---|
| Nikke Simul.exe | `109c56157ab26c4f0b6f05df1aedc237284aba1e67c38278fb65a6d373cfcc52` |
| Nikke Simul.dll | `9933848c930915ec4a58eb91744f85a31576c1aa0ad615c936e4bb80419bbd35` |
| backend/Nikke.Api.dll | `ef13e55b47fd7da26a821fb0b18ef270852eb2589cf910ad5f9759966ec8026c` |
| backend/Nikke.Engine.dll | `973dd7b802398169961395e9c25e3095f521f6d13a30a27aefdab7ac8078a9e7` |
| backend/Nikke.Core.dll | `ad5d6616254d82204cd6d99df08bea32e07c5c36b09013728494893eebc88232` |

## 실제 사용 경로 검증

1. **바탕 화면 바로가기** 실행: 원본 `Nikke Simul.exe`(PID 17912) → `backend/Nikke.Api.exe`(PID 9616), 5180 소유자 일치, `/api/health` projectRoot = 원본.
2. `/editor/` UI 파일 21개(js·css·index.html) 디스크와 바이트 SHA256 일치. 원본 `apps/desktop-ui/*.js` 전부 ESM 구문 검사(`node --input-type=module --check`) 통과.
3. 보스 43개·complete true, 계정 연결 3개 조회 정상.
4. 헤드리스 Chromium으로 홈 → 솔로 레이드 → 단일 덱 통계 → 고급 진단을 **열기만** 했다(저장·검산·실험 없음): 페이지 오류 0, JS 4xx 0, GET 외 요청 0. 캡처는 Git 제외 `artifacts/director/release-original-20261002/`.
5. **보존 사후 비교:** 계정 DB 8개 테이블·presentation 494파일·`package-lock.json` 모두 **동일**, 추가 파일 0.

실제 WebView2 창 관찰·실게임 대조(앨리스 발사 간격 실측, 마지막 탄 뒤 재장전 개시)는 범위 밖. 앱은 바로가기로 실행된 상태로 사용자에게 넘겼다.

## 되돌리기

앱 종료 후 `artifacts/desktop-backups/before-main-20261002/`를 `artifacts/desktop/win-x64/`로 복원하고, UI까지 되돌리려면 원본 `main`을 `3d84fe4`로 맞춘다. 사용자 지시가 있을 때만 수행한다.
