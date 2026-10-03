# B-DATA-1 허용 목록 후속 독립 QA

2026-10-04. 대상 Backend `e21b774`(부모 `a050853`)을 S-SKILL QA `5895872` 위에 일반 merge했다. 충돌 없는 병합은 `020a6d2634647faf62adab9a4d83ac1a6ce7ba8d`다. 제품 코드는 수정하지 않았다.

**판정: B-DATA 후속 변경 자체는 통과. 현재 검수 통합본은 UI 필수 검사 실패로 차단 1유형(BD1-F-Q-1), 미판정 0.** 독립 원천/API 검사 905/905, 파일·명령 검사 23/25가 통과했다. 두 실패는 같은 허용 목록 불일치의 생성기 및 UI 검사다. Backend 대상 단독의 UI 7/7과 통합본의 UI 6/7을 구분한다.

## BD1-F-Q-1 — S-SKILL 통합 후 니케 이름 5개 허용 목록 누락

검수 통합본에서 아래 두 명령은 모두 종료 코드 1이다.

```powershell
node tests/ui/tools/gen_registered_messages.mjs --check
node --test tests/ui/*.test.mjs
```

`registered_messages_match_server_sources`가 실패하며 UI 테스트 파일 7개 중 6개만 통과한다. `tools/data-pipeline/prepare_runtime.py:16`에 S-SKILL이 추가한 **스노우 화이트·맥스웰·라피 : 레드 후드·홍련 : 흑영·레드 후드**가 등록돼 있지 않다. 현재 등록은 213개, 통합 소스가 요구하는 목록은 218개다. 추가 차이는 이 다섯 이름뿐이며 내부 보스 근거 메모는 포함되지 않는다.

범위 분리를 위해 `git archive`로 `e21b774`와 `020a6d2`의 추적 소스만 격리 폴더에 추출했다. `e21b774`는 생성기 `--check`와 UI **7/7** 통과, `020a6d2`는 작업 폴더와 같은 **6/7** 실패를 재현했다. 목록 재생성은 차이를 기록하기 위해 **무시된 archive 사본에서만** 실행했다. 제품 목록을 QA가 고치지 않았다.

따라서 Backend 메타데이터 이동의 새 결함은 아니지만, 현재 세 건 통합본은 필수 UI 검사 조건을 충족하지 않는다. 구현 담당의 통합 목록 갱신·리뷰·재QA가 필요하다. 앞선 S-SKILL `SS1-Q-1` 차단은 별도이며 이 보고서가 해제하지 않는다.

## 준비 산출물 및 표시 원칙

- 같은 고정 8/12 ZIP을 `a050853`과 `e21b774`의 실제 준비기에 각각 입력했다. 실행 시각만 달라지는 `preparedAt`까지 비교하기 위해 QA 호출부에서 두 모듈에 같은 시계 입력(`2026-10-04T00:00:00+00:00`)을 주입했다. 출력 후 문자열 치환이나 필드 삭제 없이 **239,710바이트 전체 동일**이다. 9개 필드 메타데이터의 모든 값·순서도 같다. 파일 SHA-256은 둘 다 `693c466eb1554554b2680ce28d6e25788df9b5556c8c96dd3ffb8b38d730fc79`다. 실제 배포 시각을 고정하라는 의미는 아니다.
- 원천 ZIP 17,176,616바이트, 읽기 전후 SHA-256 `925762cd3ef56601916b2e2ae58f929d4dd389055b0d8bcd2176e9abd9b29e69` 유지. 자체 positional raw-wire 판독 **340/340**: 40개 가용 시즌, 모든 원천 연결·수치, 필수 levelChangeGroupId, 방어율 원값 0, 시즌 41/42 unavailable, 손상 원천 거부·출력 보존을 재확인했다.
- 격리 실제 API 응답의 `fields`를 Chromium에서 실제 제공된 `display-labels.js`에 전달했다. 9개 필드의 **source/note 18개 모두 미등록**, `friendlyServerMessage`는 일반 한국어 오류, `koreanText`는 지정한 일반 한국어 대체 문구를 반환한다. API 메타데이터 자체는 그대로 보존된다. 현재 UI에 속성 API 소비 경로가 없고 정상 `/editor/` 본문에 근거 메모가 없는 것도 확인했다. 신규 정상 문구 **보스 속성 준비 필요**는 등록돼 그대로 표시된다.
- 현재 제품 UI JavaScript **18개 전부** 원본 파일 바이트를 `node --input-type=module --check` 표준입력으로 보내 ESM 구문 통과. 실제 `/editor/` 모듈 오류 0. 헤드리스 Chromium은 별도 프로필을 사용했다.

## 9ee11a7 수용 항목 회귀

실제 API **565/565**는 기존 자체 B-DATA 545개 행렬과 이번 브라우저 20개 검사를 합친 값이다. 구현·리뷰 하네스나 정답은 사용하지 않았다. 사용자 명시 요청에 따라 표준 Node UI 테스트와 생성기는 별도로 실행했다.

- BD1-Q-1·2 원래 8개 주입 모두 409. 모든 중첩 수치 strict, 미선언 null/키 누락, 컬렉션·딕셔너리 null 요소 거부, 선언된 null·실제 0 보존, 전체 HTTP 500 = 0.
- 이전 준비 파일 409, 재준비 파일 200 유지. 기존 보스 목록 응답 바이트, 준비 계산 입력·조건·입력/실행 fingerprint, 기존 replay/export 및 compute 결과/통계 조회 보존. 표시 파일이 손상돼도 계산 입력·기존 보스 목록은 변하지 않는다.
- 이번 API 전후 비교는 **동일한 S-SKILL 통합 바이너리에서 표시 파일 도입 전후**를 비교했다. 기존 5인 180초 replay 및 CPU compute/통계 동일을 확인했다. `a050853 → e21b774` 및 `5895872 → 020a6d2`에는 C# 변경이 없다. Director `6d83dec` 대비 737개 독립 산술 + 기존 5인 60개 결과 전체 일치는 직전 S-SKILL QA `5895872`의 797/797 증거를 유지한다. 이번에 그 797개를 다시 실행한 것으로 집계하지 않았다.
- 격리 포트 **52255**, 소유 API PID **32624/21944** 종료 확인. 원본 data/local을 추가로 읽지 않고 기존 공개 표 QA 사본을 재사용했다. 원본 계정·세션·캐시·presentation·5180/5181·EXE 접근/변경 없음. 공개 입력과 미추적 package-lock hash 보존, package-lock 커밋·push·배포·새 워커·부하 측정 없음.

**배포 조건 유지:** a050853 이전 속성 파일은 필수 `challenge.levelChangeGroupId`가 없어 409다. Director 배포 시 고정 ZIP으로 `prepare_solo_raid_boss_attributes.py --static-data-zip <ZIP> --presentation-root <배포 dataRoot>/presentation` 실행이 필요하다. 이미 a050853 형식으로 재준비했다면 이번 메타데이터 이동만으로 재준비할 필요는 없다. QA는 원본 presentation에 실행하지 않았다. 사용자 실행 경로는 원본 `C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe`이며, 이 보고서는 원본 배포 완료를 뜻하지 않는다.

## 재현 자료

- 자체 검사: `tests/single_deck_compute_qa/check_boss_metadata_followup.py`, `check_boss_metadata_api.py`; 기존 자체 `check_boss_static_source.py`, `check_boss_static_api.py`, `check_boss_static_readmission.py` 재사용.
- 파일·명령 증거: `artifacts/single-deck-qa/bdata1r3/evidence-index.json`, `followup-audit.json`, `source-audit.json`, `target/integrated-registry-delta.json`, `target/integrated-generator-check.log`, `target/integrated-ui-tests.log`.
- 실제 API: `artifacts/single-deck-qa/f2-ufix6-1212802ab5e6/summary.json`, `traffic.json`, `expanded-null-matrix.json`, `actual-browser-metadata.json`, `editor.png` 및 API 로그.
- 앞으로 백엔드 QA에서도 `node --test tests/ui/*.test.mjs`를 필수 회귀 항목으로 유지한다.
