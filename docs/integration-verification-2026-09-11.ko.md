# Director 통합 검증 — 2026-09-11

사용자 승인: 개발 결과 통합·실제 API/엔진/저장/UI 검증·검수와 통계 작업 전달 복구. 전체 통과와 각 단계 통과를 분리한다. 원본 계정/실행 중 서버/기존 artifacts를 수정하지 않고 Director의 새 출력 및 복사 DB만 사용했다. push/배포/YOLO 설정 변경 없음.

## 통합 및 전달

- 제품 기준 `a0738accb16500e52621811fac0dac7259cb7f76`: 엔진 `3b92101`, Backend `b63ad12`, UI `3f9b717`을 Director 브랜치에 충돌 없이 통합했다.
- 검수 `c212cb7` 및 통계 `a17e079` 결과 통합 커밋 `76bc02e`. 이 두 결과는 제품 코드 변경이 아니다.
- 검수·통계의 이전 세션은 실제 작업이 시작되지 않았고 Orca가 오래된 interactive prompt 대기로 감지했다. Esc 후에도 해제되지 않아 기존 세션을 종료하지 않고 같은 작업공간에 새 세션을 열었다. 기존 차단 요청을 중복 전송하지 않았다.
- Q3 터미널 `term_30f7a75f-412b-4f2f-9bd3-863c417a5e7e`, 요청 `8ebd0ab4-586b-47a4-b79d-4ac2110340a0`: accepted + turn_started 확인, 결과 c212cb7.
- S3 터미널 `term_ede55cad-1b9e-40bc-a65a-15b4e9c7a19d`, 요청 `2b9ae61b-9f5e-464e-ad14-a1fb7c2889d0`: accepted + turn_started 확인, 결과 a17e079.
- U3는 기존 UI 터미널 `term_173a227c-2b8c-4204-8152-2fe364a19793`에 요청 `e27991cd-99d6-45ad-8df4-714376ca31c7`로 전달했다. provider가 turn_started를 제공하지 않지만 후속 실제 읽기·편집을 확인했다. Q3 실패 근거 추가 전달 요청은 `408d507e-e4ff-4f1c-88ac-1b4ffd1facbe`이다.
- 작업 소유권은 `integrated-validation-dispatch.ko.md`에 기록했다. UI 외 제품 교차 편집은 지시하지 않았다. Director는 검증 인프라와 종합 문서를 소유한다.

## 이번 직접 실행 결과

| 검사 | 결과 | 근거 |
|---|---|---|
| locked restore, 전체 Release build | 성공, 빌드 경고/오류 0 | 고정 .NET 10.0.400, a0738ac |
| 전체 C# 회귀 | Engine/Core 113 + Sync 81 통과, 실패/skip 0 | `artifacts/director/integration-a0738ac-tests/*.trx` |
| export 검사기 회귀 | 7 통과 | 큰 CSV metadata 및 parser limit 복원 테스트 추가 후 재실행 |
| 격리 합성 HTTP/저장 회귀 | 7개 그룹 통과 | `artifacts/b2/http-4e1b5aef12484b3eacebcb1305e8b589/summary.json` |
| 계정 복사본 실제 180초 API 통합 | 통과 | `artifacts/director/live-8e485ccfc75c492b98bb8e62d12a4262/summary.json`, `artifacts/b2/integration-bfe7311e79a24060abb9c7161f21e7ac/summary.json` |
| 통계 도구 자체 테스트 | 18 통과 | 통합 후 Director에서 직접 실행 |
| 기존 P00 계산 smoke fixture | 통과 | Nikke.Smoke, synthetic-overload-rounding: finalStat=103, timeCs=97 |
| 검수 로그 도구 자체 테스트 | 5 통과 | 통합 후 Director에서 직접 실행 |
| 실제 API 저장 로그의 독립 검산 | 두 도구 모두 종료 0 | `artifacts/s3/20260911T031950Z-bb4e5f1d7ad348c8aecc66f30ab93b80/analysis.json`, `artifacts/director/actual-log-audit/log-cb8a2ff842c84024a451ca655b767d73/summary.json` |
| 수정 전 실제 UI→API | 실패 HTTP 400 | `artifacts/director/live-a3845ac2f29e49a997aee4a018a7ac57/{summary,ui-request,ui-response}.json` |

실제 API 조건: 저장된 5인 스펙, 시나리오 레벨 400, 180초, legacy_term_floor, 크리 OFF/코어 ON, 자동 사격, 단계 지연 1프레임 고정, 앨리스/모더니아 III 순환. 고정 지연은 재실행 비교용 입력이며 제품 기본 1~10/28/max 규칙은 바꾸지 않았다. 수동 사격에는 재클릭 난수가 있으므로 결정적 API 재실행 조건에서 제외한다. 수동/자동 로그 RNG 불변은 기존 주입 난수 엔진 테스트로 별도 검증한다.

앨리스 실제 API 로그: **179명중/179발, 피해 523142272, 마지막 명중 10713프레임**. 피해 누적·로그 합계·선택 멤버 총합 일치, 자체 효과/팀 풀버스트의 네 상태 조합 존재. 이는 계정 복사본 조건의 실제 엔진 결과이지 게임 실측 결과가 아니다. 관측 오차는 `not_provided`/null이다.

API 수용 항목: 저장 tactic 복원→실행, 원문 저장/GET/export.json 일치, CSV metadata/entryJson/순서/단위/합계 보존, 결정적 재실행 전체 result 일치, 로그 OFF의 멤버 피해·발수 일치, legacy null tactic, 과거 미수집 합성 사례, 잘못된 대상/중복/단계/불완전/legacy 혼용 거부, 편성 변경 stale.

원본 connections/snapshots/accounts/solo_formations 정렬 payload의 논리 SHA-256은 위 실제 API 실행 전후 모두 `71ab0093f95c51ba8a14e153d5d9e82db4b60d72c46c84f2df5f01c8a937864d`다. 검증 데이터에는 원본 세션 파일을 복사하지 않았다. 실제 UI 표시를 위해 선택 스냅샷의 raw envelope와 무결성 manifest만 추가 복사하고, 격리 DB에 합성 연결 포인터를 넣었다. 브라우저는 해당 격리 서버 외 네트워크를 차단한다.

## 실패 이력과 조치

1. 샌드박스 전체 solution restore: Windows SDK 디렉터리 접근 거부. 해당 restore/build/test 명령만 정식 승인으로 재실행했다.
2. Director 검증 도구 초기 Python comprehension 구문 오류: 단순 목록 단계로 수정했다. 제품 오류가 아니다.
3. 첫 실제 API 검증 `live-f913...`: 실제 3.5 MB 결과의 CSV metadata가 Python 기본 131072자 한도를 넘어 검사 실패. 입력 CSV 길이에 맞춰 검사 중에만 한도를 올리고 finally에서 복원하도록 수정했다. 로그를 자르지 않았다. 200000자 metadata 회귀를 추가했다.
4. 두 번째 실제 API 검증 `live-7cce...`: 수동 full_charge의 재클릭 난수 때문에 동일 입력 재실행 결과가 달랐다. 고정 stage delay/crit OFF만으로 결정적이라고 가정한 검사 조건 오류다. 자동 사격으로 변경하고 검사기에 manualCharacterId 거부 조건을 넣었다. 제품 난수를 제거하거나 기대값을 느슨하게 하지 않았다.
5. UI 격리 준비 초기 `live-5811...`/`live-f2d7...`: UI combat-powers 조회가 필요로 하는 raw envelope/manifest 미복사로 준비 실패. 필요한 두 파일만 읽기 전용 원본에서 복사하도록 도구를 보완했다.
6. 준비 후 실제 UI는 `Do not mix legacy selection options and a versioned tactic.` HTTP 400을 재현했다. Q3도 독립 경계 검사에서 누락 로그 요청·legacy 혼용·wire 불일치·상태 손실·전략 왕복 손실·늦은 복원 덮어쓰기를 재현했다. U3 수정 및 재검증 대상이며 테스트 통과로 덮지 않는다.

## 재현

고정 SDK: `C:/Users/user/Documents/GitHub/Nikke-Simul/.tools/dotnet/dotnet.exe`, Python: `C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`. DOTNET_CLI_HOME은 Director `.tools/dotnet-home`, NUGET_PACKAGES는 기존 원본 `.tools/nuget-packages`를 사용했다. 출력은 실행별 UUID를 사용한다.

```powershell
& '<python>' tools/data-pipeline/tests/check_integrated_live.py --dotnet '<dotnet>' --source-data '<원본 data/local>' --api-only
& '<python>' tools/data-pipeline/tests/check_integrated_live.py --dotnet '<dotnet>' --source-data '<원본 data/local>' --browser-data '<Director artifacts 내부 격리 data>'
& '<python>' tools/damage-calibration/analyze.py '<실제 SavedSkillReplay JSON>'
& '<python>' tests/q3/verify_log.py '<실제 SavedSkillReplay JSON>' --output-root artifacts/director/actual-log-audit
```

첫 명령은 HEAD 고정·제품 diff 없음 검사 후 API를 재빌드한다. source-data는 쓰지 않는다. browser-data는 Director artifacts 내부만 허용하며 소스 계정 DB를 직접 받지 않는다. 전체 실행에서 API 단계가 통과해도 브라우저 미실행이면 전체 UI 수용을 뜻하지 않는다.

## 남은 수용 조건

U3 고정 커밋을 통합한 뒤 Q3의 모든 UI 경계 검사, 실제 브라우저의 전략 저장/복원/실행/로그 표시/다운로드/반응형을 재검증한다. 현재 실게임 실측 비교는 별도 미완료다. 이 문서의 초기 통합 결과만으로 전체 완료를 선언하지 않는다.

Director 검증·지시 기록 커밋: `3c6462b`。그 이후 브라우저 검증 절차에 앨리스만 사용/wait_preferred 저장→새로고침→실행, 실제 시전자·SVG 로그 수 대조, JSON/CSV 다운로드 바이트 원문 대조를 추가했다. 확장된 브라우저 절차는 Python 구문 검사만 통과했으며 U3 수정본에서의 실행은 아직 미완료다. 위 HTTP 400 재현은 확장 전 절차의 실제 결과이고, 확장 절차 통과 증거로 쓰지 않는다.

이 기록 시점의 U3는 기존 UI 작업공간에서 제품/fixture 테스트를 편집 중이며 확정 후속 커밋을 제출하지 않았다. 미커밋 UI 파일을 Director로 가져오지 않았다. 검수·통계의 새 세션은 각 결과 제출 후 보존했으며 새로운 작업이 없는 이전 차단 세션도 강제 종료하지 않았다.
