# Director 통합 검증 — 2026-09-11

사용자 승인: 개발 결과 통합·실제 API/엔진/저장/UI 검증·검수와 통계 작업 전달 복구. 전체 통과와 각 단계 통과를 분리한다. 원본 계정/실행 중 서버/기존 artifacts를 수정하지 않고 Director의 새 출력 및 복사 DB만 사용했다. push/배포/YOLO 설정 변경 없음.

## 최신 판정 — 통계 경계 수정 5172afe 수용

통계 `5172afeef1b447fef59baa59d41136c2118ab73e`를 Director **`38276ce239a49a5e097aa1c2783b34677fe3c156`**에 충돌 없이 병합했다. Orca 완료 보고와 실제 diff를 확인했으며, 변경은 분석기·전용 테스트·통계 문서 3개 파일에 한정된다.

Director 직접 재검증:

- `tools/damage-calibration/test_analyze.py`: **22개 통과 / 실패 0**. 기존 18개와 0·1·10800·10801 경계 4개이며, 잘못된 행도 삭제하지 않고 입력 불변을 검사한다.
- 이전에 실패했던 **동일한** `artifacts/director/live-1ef80dd69d7a41669c609180d520ec85/ui-response.json` 재검산: **종료 0, issues=[]**, 135타격·총 피해 153638004·마지막 10800프레임 모두 보존.
- 결과: `artifacts/s3/20260911T050330Z-56f275d5d8a24045be2d4e8335e406b2/analysis.json`. 입력 SHA-256은 실행 전후 모두 `9fa27ddbacd407f27764dcfa558556f1daa1339df6077a74047730f2a1780309`이며 이전 실패 입력과 같다.
- 유효 피해 행 범위 `1 <= frame <= durationFrames`가 엔진 루프와 일치한다. 전투 시작 관리 이벤트 0프레임 및 풀버스트 효과의 배타적 종료 경계와는 구분한다.

**이번에 배정한 로그·전술 UI 통합 및 후속 통계 경계 결함의 수용 검수는 완료**다. 엔진/API/UI 제품 변경이 없는 통계 수정이므로 기존 UI/C# 검증 근거를 유지하며 이번에 브라우저나 C# 회귀까지 재실행했다고 주장하지 않는다. 원본 로그와 기존 미추적 package-lock.json은 보존했다.

실게임 관측은 여전히 `not_provided`, 평균 절대/상대 오차는 null이다. 다음 단계는 관측 조건을 고정해 **발당 대미지 영점 확인 후 차지·버스트·사이클 타이밍 비교**이며, 이번 검사 통과가 실게임 정확도나 프로젝트 전체 완료를 뜻하지 않는다. 추가 구현 작업은 배정하지 않았다.

## U3 후속 수정 99dfa2f 수용 기록

UI `99dfa2fa08335b025e7ad17791070123b6a7bd52`를 Director **`a16cb9e14f186d2fece7c81551c29816e04104eb`**에 병합했다. 이전 재현에서 남은 **복원 준비 상태 및 JSON 원문 다운로드 두 문제는 해당 수용 경로에서 해결 확인**했다. 당시 UI 통합 수용은 통과했으며, 별도 통계 경계 결함은 위 최신 판정에서 종료했다. 실게임 정확도는 별도다.

| 검사 | 결과 | 근거 |
|---|---|---|
| Q3 독립 UI 경계 검사 원본 재실행 | 25 통과 / 실패 0 | `artifacts/director/u3-followup-contract/ui-f9884020-a98a-4f7a-a93a-697d5f665067/summary.json` |
| 실제 서버 전술 저장→캐시 제거→새로고침 | ready=true 시점부터 앨리스만 허용 및 wait_preferred 정확히 복원. 추가 정상화 대기 제거 | `artifacts/director/live-1ef80dd69d7a41669c609180d520ec85/ui-restored-state.json`, `summary.json` |
| 실제 UI→API→엔진→저장→로그 표시 | HTTP 200, 요청 tactic과 저장 tactic 일치, 실제 III 시전자 전원 앨리스, SVG 타격 수 일치 | 같은 실행의 `ui-request.json`, `ui-response.json`, `ui-result.png` |
| JSON 및 CSV 실제 다운로드 | 두 형식 모두 서버 응답과 바이트 일치 | 같은 실행의 `ui-export-checks.json`, `ui-download.*`, `server-export.*` |
| 실제 브라우저 전체 절차 반복 | 두 번째 실행도 통과, 1500/850/500px 가로 넘침 없음, pageerror 0 | `artifacts/director/live-e8aee993adc94315be6686319fc3e97c/summary.json` |
| 내보내기 오류 처리 | 실제 검사 완료 후 별도 합성 HTTP 503 주입: JSON/CSV 모두 오류 표시, 로컬 대체 다운로드 없음 | 같은 두 번째 summary의 `syntheticExport503NoFallback: true` |
| 실제 UI 로그 Q3 구조·누적 검산 | complete 수용, 135발/135타격, 피해 153638004 | `artifacts/director/u3-followup-log/log-8ff0ba5e0b844db484172c3da5c496b3/summary.json` |

검증 도구는 로컬 전술 캐시를 제거하여 서버 복원을 입증하고, 준비 완료 시점의 전체 allowlist를 저장 DTO와 즉시 대조하도록 강화했다. 실API 정상 경로와 503 오류 주입은 분리했다. U3 후속에서도 C# `src` 변경은 없으며 기존 C# 회귀 194개를 이번에 재실행했다고 주장하지 않는다. 두 브라우저 실행 모두 원본 계정 논리 해시가 전후 동일하고 자체 브라우저/API는 종료했다.

### 통계 경계 결함 발견 이력 (5172afe에서 해결)

S3를 위 첫 실제 UI 저장 결과에 실행하면 종료 2, 유일한 issue는 `outside_duration`이다. 근거: `artifacts/s3/20260911T045358Z-30e6a72680e54fd38a6ad54b176ce0ea/analysis.json`. 135개 타격의 독립 계산·누적·총합에는 불일치가 없고, 마지막 타격이 정확히 **10800프레임(180초)**이다.

확인한 코드 차이: `src/Nikke.Engine/Skills/SkillReplay.cs:615`는 `frame <= C.DurationFrames`로 종료 프레임을 포함한다. 반면 `tools/damage-calibration/analyze.py:214`는 `frame >= duration`을 거부한다. Q3 검사기는 같은 로그를 수용했다. 따라서 이 실패는 UI 회귀가 아니라 통계 검사기의 엔진 종료 경계 불일치다. 해당 결과를 재실행의 다른 난수 표본으로 덮지 않고 보존했다.

다음 완료 조건: 통계 담당이 엔진 계약에 맞춰 하한/상한 검증을 정정하고 0·1·duration·duration+1 경계 회귀 및 위 실제 저장 결과 재검산을 통과시킬 것. UI/엔진 제품 코드를 이 검사 통과 목적으로 바꾸지 않는다. 게임 실측 발당 영점·차지 및 cycle 보정은 계속 별도 미완료다.

## 이전 판정 — fe96827 통합 당시의 실패 이력

UI `fe968276846d12ed1ec4b3ae1de6032a1489023e`를 Director **`055ec125ec0e712b176e6096c940f8ec6ee34dc6`**에 충돌 없이 병합했다. 당시 판정은 **구현 통합 완료 / 전체 UI 수용 미완료**였다. 아래는 99dfa2f 후속 수정 이전 기록이다.

| 검사 | 직접 확인한 결과 | 근거 |
|---|---|---|
| 수정 없는 원본 Q3 UI 경계 검사 | 25 통과 / 0 실패 | `artifacts/director/u3-contract/ui-687c5e6a-ab99-4878-95b8-d589d8962e97/summary.json` |
| 전술 PUT 및 새로고침 직후 | 서버 저장 DTO는 정상이나 ready=true 후 일시적으로 제외 니케 체크가 켜짐. 이후 정상 복원됨 | `artifacts/director/live-c1ff4cf993c245289ae2ef454e4f5a4b/ui-saved-tactic.json`, `ui-restored-state.json`, `ui-failure.png` |
| 복원 완료 후 실제 UI→API 실행 | HTTP 200, 저장 DTO 그대로 실행, 앨리스 로그 요청·SVG 타격 수 일치, III 시전자 전원 앨리스 | `artifacts/director/live-f950c5bd4ccf46098e0ca885c3089968/ui-request.json`, `ui-response.json` |
| 해당 실제 UI 실행 로그의 독립 S3 검산 | 종료 0, issues 빈 배열, 134발/134타격, 피해 152283466, 관측값 미제공 | `artifacts/s3/20260911T043513Z-aa1b74fcfc0e4d8c8e2983b2efd10357/analysis.json` |
| 실제 JSON/CSV 다운로드 원문 바이트 비교 | **JSON 실패 / CSV 통과** | `artifacts/director/live-d6131ccb376f4f7181ca169b966910fb/ui-export-checks.json`, `ui-download.*`, `server-export.*` |
| 실 API 연결 화면·상세 열기·반응형 | 그래프 타격 수 대조, 상세 열기, 1500/850/500px 가로 넘침 없음, pageerror 없음까지 진행 후 JSON 비교 실패로 종료 | 같은 실행의 `ui-result.png`, `ui-page-errors.json`, `summary.json` |

검증 조건은 앞선 API의 앨리스/모더니아 교대·코어 ON 조건과 다르다. 이번 UI는 앨리스만 사용/wait_preferred, 레벨 400, 180초, 크리 OFF, 나머지는 UI 기본값이다. 피해나 발수를 앞선 179타격 실행과 직접 비교해 회귀라고 판단하지 않는다. 이번 U3는 `src` 변경이 없으므로 C# 194개 통과는 아래 이전 실행 근거를 유지하며 이번에 재실행했다고 주장하지 않는다.

확인한 결함과 남은 조건:

1. **복원 준비 상태**: 저장 DTO의 allowedCharacterIds는 `5011,5008,5004`인데 새로고침 직후 캐시 allowlist가 `{}`이며 모든 체크가 켜지는 상태를 수집했다. 실패 화면 촬영 시에는 정상으로 복원되어 영구 저장 손실은 아니다. 빈 편성으로 복원한 값이 준비 완료 상태에 노출되는 비동기 경쟁이 의심된다. 원인 확정·수정 및 빠른 실행/편성 전환 회귀가 필요하다. 검사기는 초기 상태를 삭제하지 않고 별도 보존하며, 최종 복원이 완료되는지도 추가 대기 조건으로 구분한다.
2. **JSON 원문 다운로드**: `apps/desktop-ui/damage-log.js`는 서버 JSON을 파싱한 후 다시 직렬화한다. 실제 다운로드 바이트가 서버 export.json과 다른 것을 재현했다. JSON 의미/숫자 손실까지 확인한 것은 아니며, 원본 Blob 다운로드와 서버 실패 표시를 검증해야 한다. CSV 원문 비교는 실제로 통과했으므로 CSV 결함 확정으로 확대하지 않는다.
3. `docs/damage-log-ui.ko.md`의 "계약 결함 완전 해소"는 UI 담당의 fixture/경계 검사 범위 보고다. 위 실제 복원 경쟁 및 JSON 원문 수용 실패 때문에 전체 실연동 완료 주장으로 사용할 수 없다. UI fixture 검사는 mock HTTP를 사용하며 실제 API 검사는 Director가 별도 수행했다.
4. 게임 실측 발당 대미지 영점과 차지/사이클 정확도 검증은 여전히 미완료다. 독립 계산 검산 통과는 게임 관측과의 일치를 뜻하지 않는다.

기존 UI 담당에게 잔여 U3 수정 지시를 보냈다: 요청 `db77ddd3-d9dd-4bf3-af05-6acac5684ccb`, 추가 근거 `139a8196-2c10-4425-9f5f-661a195a93d1`. Orca input_accepted 및 후속 실제 파일 읽기/조사와 추가 프롬프트 수신을 확인했다. 후속 커밋은 이 기록 시점에 아직 통합하지 않았다. 추가 업무를 엔진/Backend/통계에 중복 배정하지 않았다.

검증 산출물은 모두 Director artifacts 안에 격리했다. 위 브라우저 실행의 원본 계정 논리 해시는 전후 동일하며 자체 API 프로세스와 브라우저는 종료했다. 기존 미추적 `package-lock.json`은 수정·추가·커밋하지 않았다.

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

## 초기 통합 시점의 남은 수용 조건 (U3 제출 전 이력)

U3 고정 커밋을 통합한 뒤 Q3의 모든 UI 경계 검사, 실제 브라우저의 전략 저장/복원/실행/로그 표시/다운로드/반응형을 재검증한다. 현재 실게임 실측 비교는 별도 미완료다. 이 문서의 초기 통합 결과만으로 전체 완료를 선언하지 않는다.

Director 검증·지시 기록 커밋: `3c6462b`。그 이후 브라우저 검증 절차에 앨리스만 사용/wait_preferred 저장→새로고침→실행, 실제 시전자·SVG 로그 수 대조, JSON/CSV 다운로드 바이트 원문 대조를 추가했다. 확장된 브라우저 절차는 Python 구문 검사만 통과했으며 U3 수정본에서의 실행은 아직 미완료다. 위 HTTP 400 재현은 확장 전 절차의 실제 결과이고, 확장 절차 통과 증거로 쓰지 않는다.

이 기록 시점의 U3는 기존 UI 작업공간에서 제품/fixture 테스트를 편집 중이며 확정 후속 커밋을 제출하지 않았다. 미커밋 UI 파일을 Director로 가져오지 않았다. 검수·통계의 새 세션은 각 결과 제출 후 보존했으며 새로운 작업이 없는 이전 차단 세션도 강제 종료하지 않았다.
