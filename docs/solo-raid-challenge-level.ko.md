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

## 후속 필요 (이번 소유 범위 밖)

- `tools/data-pipeline/tests/check_integrated_live.py:115`와 `tools/data-pipeline/tests/check_p04_ui.py:28`이 `[name="level"]`을 채웁니다. 입력란이 사라졌으므로 두 검사는 이 상태에서 실패합니다. 두 파일은 Director 소유라 수정하지 않았습니다. 통합 시 해당 줄을 지우면 됩니다(요청 `scenarioLevel`은 UI가 400으로 보냅니다).
- 배포(원본 main 통합·실행 파일 갱신·실제 사용자 실행 경로 확인)는 `AGENTS.md`에 따라 Director가 수행합니다. 이 커밋만으로 배포 완료가 아닙니다.
