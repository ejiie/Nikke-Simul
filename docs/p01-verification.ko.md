# P01 구현·검증 보고서

실행일: 2026-09-08. P01-1~P01-6의 버튼 기반 수집·정제·저장 및 원천 대조를 구현했다. P02의 C# 기초 스탯/대미지 검산이나 실게임 화면 수치 재대조를 완료했다는 의미는 아니다.

## 단계별 결과

| 단계 | 구현 결과 |
|---|---|
| P01-1 | C# 데이터 계약, 필드 출처/단위 표, 익명 합성 입력. 캐릭터 ID·4부위×3줄·원천 옵션 ID·미확인 값 보존 |
| P01-2 | C# SnapshotNormalizer. 필수 필드, 계정·서버, 로스터/상세 ID 집합, 중복 충돌, 옵션 단위·단계 검증 |
| P01-3 | SQLite 작업/연결/snapshot/current 저장, 원천 manifest/hash, transaction, 취소·중복 방지·재시작 복원, 수동 보완 revision |
| P01-4 | Playwright 직접 로그인, Windows DPAPI 세션 저장, HTTP 배치 수집, 전초기지·수집 후 로스터 확인, 재연결 |
| P01-5 | 로컬 동기화 UI, 계정/서버 선택, 진행/오류/변경 내역, 니케·장비 상세, 잠금·계정 스탯 수동 보완 |
| P01-6 | 실제 로그인 → 한국 서버 193명 수집·저장, 버튼 재동기화 성공. 실제 원천과 저장 후 9,000개 필드 대조에서 차이 0. 후속 검산 후보/지원 상태 기록 |

## 검증 기록

- 기존 저장 응답 재생: 193명, 9,000개 필드 비교, 차이 0. 원본 프로젝트에 쓰지 않고 별도 검증 저장소에서 실행했다.
- 실제 로그인 후 새 API 응답 재생: 193명, 9,000개 필드 비교, 차이 0. 개별 스킬·호감도·장비 티어/강화/제조사/ID·옵션 ID/원천 수치/단위·큐브·소장품을 저장 후 다시 읽어 대조했다.
- 실제 버튼 동기화: 최초 및 재동기화 각각 193/193명 성공. 재동기화 때 재로그인을 요구하지 않았다.
- 실제 응답 검증에는 동일한 state_effects 중복 296건이 있었고 동일 값으로 확인해 제거했다. 그 외 검증 오류·옵션 단계 불일치는 없었다. 같은 ID의 값이 달라지는 중복은 실패 처리한다.
- 최종 C# 테스트는 코어 8개 + 정제·저장 25개 = 33개 통과, Python 수집기 7개 통과, 웹 단위 4개 통과다. Release 빌드 경고·오류는 0이다. 기본 `npm test`, `npm run test:sync`, `npm run build`가 모두 exit 0으로 완료됐다. 중복 실행한 테스트는 개수에 더하지 않았다. 로그는 `artifacts/p01/final-checks.log`에 기록했다.
- 기본 `npm run dev`로 백엔드를 재시작한 뒤 연결 ready, 한국 서버 193명, 저장 revision 3, 성공 작업 3개, 활성 작업 0, 검증 오류 0을 확인했다(`restart-report.json`). 저장된 세션·snapshot이 복원됐으며 새 로그인을 요구하지 않았다.
- 격리된 검증 계정의 통합 검사 11개 통과: 요청 토큰·외부 origin 거부, 중복 클릭, 이전 snapshot 조회, 실패 시 current 유지, 취소 시 current 유지, 장비 렌더링, 잠금 저장/새로고침, 재동기화 잠금 유지, 모바일 가로 넘침 없음, 브라우저 오류 없음.
- 데스크톱 1440px / 모바일 390px 스크린샷을 직접 확인했다. 합성 데이터임을 화면에 표시했다.

주요 증거는 `artifacts/p01/live-audit-report.json`, `replay-report-v2.json`, `api-ui-report.json`, `ui-desktop.png`, `ui-mobile.png`다. 개인 데이터가 포함될 수 있어 커밋하지 않는다.

## 발견·수정한 문제

1. **로그인 CORS:** 최초 구현에서 API용 X-Channel-Type 등을 브라우저 context 전체에 주입해 다른 도메인의 요청에도 붙었다. 사용자가 콘솔 오류를 보고했다. 로그인 브라우저에서 전역 헤더를 제거하고 별도 HTTP API client에만 적용했다. 회귀 테스트와 실제 재로그인·수집으로 확인했다. 브라우저 보안 설정은 완화하지 않았다.
2. **Integer 비율 옵션:** API는 StatCritical, StatCriticalDamage, StatChargeDamage의 값을 Integer로 전달한다. 종류별 의미 단위에 따라 /10000 비율로 변환하도록 수정했고 원천 단위·값은 별도로 보존했다. 실제 응답의 155개 해당 옵션 줄이 고정 단계표와 일치했다.
3. **수동 출처 오인:** 계정 스탯을 보완할 때 바뀌지 않은 API 필드를 수동 값으로 승격하지 않도록 필드별 출처를 기록했다. 새 수집에서 API가 누락된 경우 실제 수동 보완만 유지한다.
4. **SQLite 의존성:** 최초 복원에서 SQLitePCLRaw 2.1.11의 알려진 취약성 경고가 확인되어 bundle 3.0.5를 명시 고정했다. 버전·의존성은 NuGet lock에 보존한다. 참고: [공식 패키지](https://www.nuget.org/packages/SQLitePCLRaw.bundle_e_sqlite3/3.0.5), [해당 권고](https://github.com/advisories/GHSA-2m69-gcr7-jv3q).

## 범위와 남은 검증

- 원천 API와 저장값의 일치를 검증했다. 게임 클라이언트 화면의 현재 숫자와 직접 대조한 검증은 수행하지 않았다.
- 실제로 확인한 계정은 한국 서버 1개다. 다른 서버 선택 구조는 구현했지만 모든 서버의 실계정 로그인 검증을 주장하지 않는다.
- 서버의 비공개 설정·세션 만료·전송 실패는 오류 분기/합성 테스트로 검증했다. 사용자 계정 세션을 의도적으로 만료시키지는 않았다.
- 잠금 상태는 현재 응답에서 제공되지 않아 수동 보완한다. 장비 fingerprint가 바뀌면 이전 보완을 해제한다. API가 장비 인스턴스의 유일 ID를 보장하지 않으므로 관측 필드가 완전히 같은 교체까지 판별할 수 있다고 주장하지 않는다.
- GameSnapshot은 P01 매핑 부분집합이다. 모든 캐릭터의 `combatSupport`는 아직 `not_evaluated`이며, 카탈로그 매핑 성공을 전투 효과 지원으로 오인하지 않는다.
- 현재 입력 UI는 upstream 테마 일부를 재사용해 새로 작성했다. upstream의 전투 화면 전체를 C# API에 연결한 단계는 아니다.
- 로그인용 브라우저는 Microsoft Edge 우선, 설치된 Playwright Chromium을 대체 경로로 사용한다. 직접 HTTP 수집은 Playwright request context를 사용하므로 반복 수집 시 브라우저 창을 띄우지 않는다.

## 재현

```powershell
# 처음 설치하는 환경: P00 참조/SDK 준비 후
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup.ps1
npm run setup:sync
npm run build
npm run dev
# http://127.0.0.1:5180/ → 계정 연결 → 로그인 → 서버 선택 → 자동 동기화

npm test
npm run test:sync
```

개발 중인 API와 별도로 test fixture 서버를 5181 포트에 띄운 뒤 `tools/data-pipeline/tests/check_api_ui.py`를 실행한다. 검증용 fixture/데이터 경로와 실행 방법은 `tools/data-pipeline/README.md`를 따른다. 운영 데이터 폴더를 합성 테스트에 사용하지 않는다.

P00 원본 화면은 `npm run dev:reference`, 원본 빌드·테스트는 `build:reference` / `test:reference`로 실행한다. 기본 `dev` / `build`는 P01 UI/API로 전환했다.
