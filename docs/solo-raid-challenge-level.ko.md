# 솔로 레이드 검산 레벨 고정 (UI, 2026-09-14)

사용자 승인 요청에 따라 솔로 레이드 챌린지의 **검산 레벨 입력란을 제거**하고 실행 요청의 `scenarioLevel`을 항상 400으로 보냅니다.

## 변경

- `apps/desktop-ui/app.js` `renderRaid`: 전투 조건의 `<label>검산 레벨 (선택)<input name="level" …></label>`을 삭제했습니다. hidden input이나 계정 레벨 fallback은 두지 않았습니다. 남은 안내는 기존 microcopy 끝에 한 문장(`검산 스탯은 싱크로 레벨 400 고정입니다.`)입니다.
- 같은 파일 `#replay-form` submit 처리: `scenarioLevel: form.get('level') === '' ? null : Number(form.get('level'))`를 명명 상수 `SOLO_RAID_SCENARIO_LEVEL = 400`로 바꿨습니다. 상수는 **submit 콜백 안에** 둡니다. `tests/q3/check_ui_contract.mjs`가 이 콜백 본문만 잘라 VM에서 실행하므로 모듈 수준 상수를 참조하면 그 회귀가 깨집니다(실제로 26→23으로 실패해 확인 후 수정).
- 폼의 다른 조건(시간·방어력·크리티컬·정수화·샷건 계수·코어/거리/우월 코드·직접 조작·차지 방식·버스트 전술·대미지 로그 대상)은 그대로입니다.

## 변경하지 않은 것

- 계정 관리의 스탯·육성 레벨 화면과 값.
- 범용 API의 수동 검산 기능: `GET /api/snapshots/{id}/characters/{characterId}/stats?scenarioLevel=…`와 `CalculationService`의 `scenarioLevel ?? 계정 레벨` 규칙은 그대로입니다. 이번 변경은 솔로 레이드 화면이 보내는 값만 고정합니다.
- 엔진·API·서버·계정 데이터·EXE. Director/원본 worktree도 편집하지 않았습니다.

## 검증

기준 커밋 `bdf1759`(원본/Director 기준으로 fast-forward) 위에서 실행했습니다.

| 명령 | 결과 |
|---|---|
| `python tests/ui/check_solo_raid_level.py` | 통과. 증거 `artifacts/ui/solo-raid-level/run-b799bdb0a030/`(git 제외) |
| `node tests/q3/check_ui_contract.mjs <engine result.json>` | 26/26 통과 (상수 위치 수정 전에는 3건 실패) |
| `python tools/data-pipeline/tests/check_damage_log_ui.py` | 통과, JS 오류 0 |
| `node tests/ui/damage_audit.test.mjs <saved replay> …` | 19/19 통과 |

새 회귀(`tests/ui/check_solo_raid_level.py`)는 제품 소스 문자열이 아니라 **실제 `renderRaid` submit 경로**를 브라우저에서 실행하고 가로챈 `POST /api/runtime/skill-replays` 본문을 확인합니다.

- 폼 필드 목록이 `seconds, defense, crit, rounding, pellet, core, distance, element, manualCharacter, manualStyle`뿐이고 `level`과 hidden input이 없으며 `검산 레벨` 문구가 사라졌습니다.
- 계정 스냅샷 레벨을 137로 주어도 요청은 `scenarioLevel: 400`입니다.
- 폼에 `name="level"` 입력을 강제로 주입하고 값을 777로 넣은 뒤 다시 실행해도 요청은 `scenarioLevel: 400`입니다(값을 폼에서 읽지 않는다는 근거).
- 나머지 조건이 선택대로 전달됩니다: `durationFrames 7200`, `enemyDefense 31784`, `critMode on`, `roundingPolicy nested_floor`, `pelletCoefficientPolicy per_pellet`, `core/properDistance/elementAdvantage true`, `manualCharacterId 5004`, `manualStyle tap`, `autoBurst.tactic`(schemaVersion 1), `damageLog.characterId 5004`.
- 저장 결과 렌더링까지 확인하고 JS 예외는 0입니다. 격리 정적 서버에 초상화 이미지가 없어 생기는 404 13건은 자산 경고로 분리해 기록합니다.

## UI 제출 시점의 후속 사항

- `tools/data-pipeline/tests/check_integrated_live.py:115`와 `tools/data-pipeline/tests/check_p04_ui.py:28`이 `[name="level"]`을 채웁니다. 입력란이 사라졌으므로 두 검사는 이 상태에서 실패합니다. 두 파일은 Director 소유라 수정하지 않았습니다. 통합 시 해당 줄을 지우면 됩니다(요청 `scenarioLevel`은 UI가 400으로 보냅니다).
- 배포(원본 main 통합·실행 파일 갱신·실제 사용자 실행 경로 확인)는 `AGENTS.md`에 따라 Director가 수행합니다. 이 커밋만으로 배포 완료가 아닙니다.

## Director 통합·원본 배포 완료

- UI 확정 커밋 `75e8ae5c5454bdbc7161c11b9392cbd530bc4d00`을 Director와 원본 `C:/Users/user/Documents/GitHub/Nikke-Simul` main에 fast-forward 통합했다. 담당자의 구현 뒤 Director가 `check_solo_raid_level.py`를 별도 재실행해 통과했다(계정 137/주입 777 모두 요청 400). 근거: Director `artifacts/ui/solo-raid-level/run-e2e2c65e8c04/summary.json`.
- 위 두 기존 검사 스크립트의 level 필드 채우기를 필드 부재 assert로 바꾸고 요청 400 assert를 추가했다. `check_integrated_live.py`는 저장 결과의 모든 `appliedLevels`가 400인지도 검사한다. 두 스크립트는 이번에 구문 검증만 했으며 전체 실행 통과로 집계하지 않는다. 특히 `check_p04_ui.py`에는 과거 버스트 UI 선택자를 쓰는 별도 노후화가 남아 있어 현재 UI의 수용 검사로 사용하지 않았다.
- 원본 `artifacts/desktop-backups/before-level400/`에 기존 실행본을 백업하고, 원본 `scripts/desktop.ps1 -Action build -DataRoot C:/Users/user/Documents/GitHub/Nikke-Simul/data/local -Port 5180`으로 EXE·백엔드·설정을 재빌드했다. API/Desktop publish 모두 성공, 경고·오류 출력 없음. 계정/캐시 재생성은 하지 않았다.
- 기존 바탕 화면 바로가기로 원본 EXE(PID 18260) 및 동봉 백엔드(PID 22144)를 실행했고 5180 health의 projectRoot가 원본 경로임을 확인했다. 실제 EXE의 전투 조건 화면에서 레벨 입력란 부재와 고정 400 안내를 확인했다. PID는 당시 식별자다.
- Director의 `artifacts/director/solo-level400/check_deployed.py`는 원본 서버가 제공하는 실제 UI에서 제출 요청을 가로채 검사했다. 입력란 0개, 정상 제출 및 임의 hidden level=999 삽입 후 제출 모두 `scenarioLevel=400`; JS 예외 0. 원본 스탯 API의 읽기 전용 조회로 편성 5명의 `appliedLevel`도 모두 400임을 확인했다. 브라우저의 모든 변경 요청은 차단했으므로 원본에 검증용 전투 로그를 저장하지 않았다. 이는 저장된 전투 결과 전체 재검증과 구분한다.
- 계정 DB 8테이블과 presentation 전체 447파일 및 사용자 package-lock.json의 전후 hash 동일. 근거는 위 Director artifacts 폴더의 `deployed-summary.json`, `deployed-raid.png`, `native-level400.png`, `preservation-before.json`, `preservation-after.json`이다. 개인 계정 화면은 Git 제외다.
- 원본 EXE SHA256: `37095189856789568f4133a20b4f40bcda8509a7a8f8ddd4fb7ffdda0de02214`; 원본 backend/Nikke.Api.dll SHA256: `f9b45f95e606a6673961f00df2669135c183e6261cb2f81974d4560d55c07555`. 이후 Director 변경은 README·이 문서·검사 스크립트뿐이며 실행 제품 소스는 이 빌드와 같다. 원격 push는 하지 않는다.
