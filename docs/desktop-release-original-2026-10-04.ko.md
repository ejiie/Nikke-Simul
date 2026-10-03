# 원본 main 및 실제 사용자 실행본 갱신 — 2026-10-04 (E-PREC-1 + B-DATA-1 + S-SKILL-1)

## 현재 사용 경로

**사용자는 기존 바탕 화면 `Nikke Simul.lnk`를 실행하면 된다.** 대상은 원본 `C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe`. 바로가기·경로 변경 없음. 원격 push는 이번 배포에 포함하지 않았다.

## 배포 내용

사용자 결정("배포는 세 건을 한 번에", 앱은 사용자가 미리 종료). 이전 배포: [2026-10-02](desktop-release-original-2026-10-02.ko.md). 진행 이력: [배정·진행](skill-precision-assignments-2026-10-03.ko.md).

1. **E-PREC-1 — 계산 정밀도 후속**(QA `6bb1be2`): 비교 후보 정책 `client_f32_dprod`(B float32, 곱 사슬 double) 추가 — **기본 정책은 `client_f32` 그대로**, UI 선택지 없음. 방어율 true damage 예외, 저지(96)/파츠(112) 분리와 96 중복 제거, 장탄 조립 `long`(raw/10000·사사오입·checked). 규칙·구현 버전 상향 — 이전 결과는 조회만, 이전 실험 재개 409.
2. **B-DATA-1 — 보스 정적 속성 카탈로그(표시 전용)**(QA `9ee11a7`·`25e8210`): 시즌 1~40 약점 속성·방어력 원값·방어율 원값(전부 0)·파츠·코어·레벨 변경을 읽기 API `/api/presentation/solo-raid-bosses/attributes`로 제공. 시즌 41·42는 8/12판 원천에 없어 unavailable. **계산에는 반영하지 않으며 현재 UI에 표시 화면은 없다.**
3. **S-SKILL-1 — SSR 스킬 조립 1차**(QA `047e640`, 제품 `79a0830`): **스노우 화이트·맥스웰 실행 가능**(버스트 교체 무기는 잠정 모션 정책·관통 다중 타격 미모델 — 부분 지원). 라피 : 레드 후드·홍련 : 흑영·레드 후드는 catalog에 있으나 미지원으로 실행 거부. compute 결과·통계에 잠정 정책·한계 식별자 저장, 요약 버전 `cpu-summary.7-run-policies`.

**배포 후 잔여 한계(QA·Director 판정):** compute 완료 batch 상태(`BatchStatus`)에는 한계 식별자가 없다(이번 건 한정 범위 정정), UI는 compute 한계를 표시하지 않는다, 구 statistics `members` 키 순서는 재시작마다 달라질 수 있다(값 동일, 기존 특성), 교체 무기 모션·관통·1-tick 실측 미판정, 홍련 : 흑영은 7월판 원천(최신 수치 상향 미반영).

## 절차와 결과

1. **통합:** Director `6d83dec`(E-PREC-1) → `1d01ed8`(B-DATA-1) → `0f6dea1`(B-DATA-1 허용 목록 후속) → `6a53c9c`(S-SKILL-1, 제품 트리 = QA `79a0830`). Release 빌드 경고 0·오류 0, .NET 572/572(Analysis 42·Core 252·Sync 231·Compute 47), UI 7/7, 허용 목록 생성기 218개 일치, `apps/desktop-ui/*.js` ESM 구문 전부 통과, data-pipeline Python OK.
2. **사전 확인:** 원본 배포 경로 프로세스 없음, 5180·5181 미사용, 원본 작업 트리 깨끗, 원본 `main` = `a03c5a9`.
3. **보존 사전 스냅샷:** 계정 DB 8개 테이블 행 hash, presentation 494파일 hash, `package-lock.json` hash. runtime `current.json`(`9c98c91c…`) 백업.
4. **원본 main:** `a03c5a9` → `6a53c9c` fast-forward(로컬). 이후 추가 커밋은 이 기록 등 문서뿐.
5. **runtime 준비:** `python tools/data-pipeline/prepare_runtime.py`(고정 7월판 원천, hash 검사) → 새 runtime **`2e6e8d0631f22763f3c40d1bf32b2eef5a0fe038f770fcc3904c57cd042af2f9`**(니케 10명·함수 847·캐릭터 스킬 110, combatProfiles 192명 — 이전 `9c98c91c…`와 같은 roster `8568963a…`). QA catalog ID와 같다. `current.json`만 새 ID를 가리키고 기존 runtime 디렉터리 4개는 그대로 남았다. 네트워크·계정 접근 없음.
6. **보스 속성 준비:** `python tools/data-pipeline/prepare_solo_raid_boss_attributes.py --static-data-zip C:/Users/user/Desktop/StaticData.zip --presentation-root data/local/presentation` — ZIP SHA256 `925762cd…`(읽기 전후 동일), 결과 `{"bosses":42,"available":40,"unavailable":[41,42],"complete":false}`, 새 파일 `presentation/solo-raid-boss-attributes.json`(239,717바이트) 1개.
7. **백업·빌드:** 기존 실행 파일 폴더(636파일, 238,343,691바이트) → `artifacts/desktop-backups/before-main-20261004/`. 원본 위치 `./scripts/desktop.ps1 -Action build -DataRoot '…/data/local' -Port 5180`(NIKKE_PYTHON 기존 runtime Python), 종료 코드 0, 경고·오류 출력 없음. `desktop.settings.json` 이전과 같음.

| 원본 배포 파일 | 새 SHA256 |
|---|---|
| Nikke Simul.exe | `b5bb5ff22bb1f7405a96fe659b7db3d7c63732aca0534b080498ed8b638a2bed` |
| Nikke Simul.dll | `e4b6a3d4f1739c8cd12a5732941a88bf6e99713812fb8bd87b6c03ce70511ca6` |
| backend/Nikke.Api.dll | `bef3d3769fae00c79370d97c0c17eca912dbb0e755415c9fd6192a72464e4cf6` |
| backend/Nikke.Engine.dll | `f306579bbde909d068a4f2f787845de8e997fb5f78116b5587a2699d03bd5a9e` |
| backend/Nikke.Core.dll | `b6be7947e9bc5baebb6bf61a25fe2896e4f9597ca6c61db7659a3faac6d982c5` |
| backend/Nikke.Data.dll | `5609322ec46975f293d89c4a6a2d0c946088d1ec1d5d83d30d322ef31cfc433c` |

## 실제 사용 경로 검증

1. **바탕 화면 바로가기** 실행: 원본 `Nikke Simul.exe`(PID 26076) → `backend/Nikke.Api.exe`(PID 6152), 5180 소유자 일치, `/api/health` projectRoot = 원본.
2. `/editor/` UI 파일 22개(js·css·index.html) 디스크와 바이트 일치.
3. `/api/runtime/catalog` = `2e6e8d06…`, 10명 중 `allLevelsExecutable` true 7명(기존 5명 + 스노우 화이트·맥스웰), false 3명(라피 : 레드 후드·홍련 : 흑영·레드 후드). 보스 목록 43개·complete true, 보스 속성 API 42개·complete false, 계정 연결 3개.
4. 헤드리스 Chromium으로 홈 → 솔로 레이드 → 단일 덱 통계를 **열기만** 했다(저장·검산·실험 없음): 페이지 오류 0, 4xx/5xx 0, GET 외 요청 0. 캡처는 Git 제외 `artifacts/director/release-original-20261004/`.
5. **보존 사후 비교:** 계정 DB 8개 테이블·기존 presentation 494파일·`package-lock.json` 모두 **동일**. 추가 파일은 예상된 `presentation/solo-raid-boss-attributes.json` 1개뿐.

실제 WebView2 창 관찰·실게임 대조는 범위 밖. 앱은 바로가기로 실행된 상태로 사용자에게 넘겼다.

## 되돌리기

앱 종료 후 `artifacts/desktop-backups/before-main-20261004/`를 `artifacts/desktop/win-x64/`로 복원하고, runtime은 `data/local/runtime/current.json`을 백업(`9c98c91c…`)으로 되돌리며, UI·코드까지 되돌리려면 원본 `main`을 `a03c5a9`로 맞춘다. 보스 속성 파일은 지워도 다른 기능에 영향이 없다. 사용자 지시가 있을 때만 수행한다.
