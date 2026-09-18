# Q-LOAD-1000 배터리 전원 독립 검수 — 2026-09-18

**판정: 승인된 배터리 단독 구간의 pilot1000/1000 정상 완료, 전체 결과·저장·독립 통계 검산 통과.** 정상0/실패/취소는 모두0, attempt1, partial=false다. calibration20은 별도 exploration 실험이며 pilot에 섞지 않았다. 분포동등성·최적 동시성·자동 추천·게임 정확도·AC/다른 PC 성능 수용은 아니다.

## 기준과 보존

Director `single-deck-load-window-2026-09-18.ko.md` 전체와 기존 QA 보고서의 분포 gate/순차 부하 계획을 읽었다. 최초 승인 구간은 **10:02~10:30 KST**, 연장 없이 수행했다. 시작 HEAD **606b5685c237446616efd909339c58b28508182e**, 제품 **40078d06a3d236ec7de5987d6be3c96d2a34ec86**, 보고서d8be9d3을 포함한 기존 이력을 보존했다. 제품 파일 수정 없음. QA 실행기/오프라인 분석/보고서만 추가했다.

원본 `data/local`의 허용 공개 game-catalog/calculation/runtime **12파일만** 읽어 새 격리 dataRoot로 복사했다. 원본 계정DB/세션/presentation 캐시/EXE/5180/5181 접근·갱신·복제·종료 없음. 새로운 합성 계정으로 리타5011·블랑5008·앨리스5004·누아르5009·모더니아5044, 400, 180초, 고정DEF30925, 저장 합성 택틱, sample crit 조건을 설정했다. 실제 사용자 장비 덱 검수는 아니다.

물리 입력 fingerprint **f9cfbd31c4e250690a804b7fac2a7f1ab71d30c3c9bb0324fab74b2c1c57a70e**, engine=cpu-summary.1, rules/data 버전·합성 snapshot canonical SHA·tactic SHA·실제 Nikke DLL build hash는 `final-audit.json`의 fixedFingerprints에 고정했다. calibration/pilot의 물리 입력은 같고 phase/실험 ID는 다르다. 새 캐시에서 cpu-policy-3 auto/MaxWorkers=2로 시작했으며 과거 공유부하 캐시를 복사하지 않았다.

원본 공개12 SHA-256 변경0, 합성 snapshot 불변, package-lock SHA-256 **2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767** 보존·커밋제외. 자기 서버PID23768만 종료했고 종료 후 존재하지 않음을 확인했다. 타 worktree 편집·다른 모델 터미널 입력·새 worker/Run/Dispatch/lifecycle·배포/push 없음. 사용자 실제 EXE 경로는 AGENTS.md의 원본 `C:/Users/user/Documents/GitHub/Nikke-Simul/artifacts/desktop/win-x64/Nikke Simul.exe`이며 이번에는 실행/배포하지 않았다.

## 준비·승인 구간·실측 시간

착수 시각10:03:56 KST. Release 빌드는15.80초, 경고0/오류0이며 `--disable-build-servers -p:UseSharedCompilation=false`로 완료한 뒤 측정했다. 빌드 근거 `artifacts/single-deck-qa/load-build-826089773ea1443cb0e73a115cd7a6e8/build.log`. 준비/실행기 작성 시간도 승인 구간을 소비했다.

측정 실행기 시작 **10:09:46.247**, 종료 **10:11:02.038 KST**. 사용자 사전 관측95%와 구별하여 본 측정 시작은 **배터리89%**, 종료 **88%**다. 준비 중10:06에는92%였다. Offline, SAMSUNG MODE GUID ab6534a3-bc02-4c44-94d1-a8535b2eb070, batterySaver=0 유지. 전원 구성표·모드·우선순위·드라이버 설정은 바꾸지 않았다.

| 항목 | calibration20 | pilot1000 |
|---|---:|---:|
| ID | 9f93b26b941c4c3a99e43ba54e63a1ef | 29801ff8e26c4e328c2560f1c81d5d40 |
| phase | exploration | pilot |
| 요청 시작 KST | 10:09:52.146 | 10:09:58.344 |
| 완료 관측 KST | 10:09:57.984 | 10:11:00.319 |
| 요청→완료 관측 전체 wall | **5.839초** | **61.975초** |
| 준비 | 308.756ms | 21.543ms |
| 선택 | measured / cache miss / worker2 | cache_reused / worker2 |
| 새 튜닝 | 1044.518ms | 없음: 현 구간 calibration 캐시 |
| 전체 wall 기준 정상 run/s | 3.425 | **16.135** |

calibration warmup1회486.367ms 완료, worker1 후보2회405.946ms, worker2 후보2회149.423ms 완료. CPU1/2만의 제한 탐색이며 최적 worker 수용이 아니다. pilot 응답에 재현되는 tuning.elapsedMilliseconds=1044.518은 **원래 calibration 측정 증거**이며 새 튜닝 시간으로 다시 더하지 않는다. 현재 pilot 준비시간만 새 값이다.

정상 배치 시간은 낮은 빈도 status polling으로 경계를 관측했다. calibration은 queued 다음 조회에서 이미20회 완료여서 running 시작 관측은 **null**이며, 마지막 queued→완료 관측2.030초를 보수적 상한으로 사용했다. pilot 마지막 queued→완료 관측60.439초, 첫 running 관측→완료 관측58.425초다. 정확한 compute-only 타이머라고 하지 않는다. 전체 wall에는 요청 준비/탐지/스케줄링/완료 관측 지연이 포함된다.

10:09:58.331에 pilot 평가 결과를 보기 전에 `pilot-admission.json`을 저장했다. calibration 정상시간 상한의1000회 선형 예상101.511초, **1.5배 + cold overhead +180초** 여유 포함336.075초였고 승인 잔여1201.668초보다 충분히 짧았다. 배터리 예상89%는 짧은 calibration의 정수% 변화0에 기반한 입장 조건일 뿐 배터리 지속시간 보장이 아니다. 컷은 calibration 팀 중앙값855466067.5의 floor인 **855,466,067**로 확정한 뒤 새 pilot 요청을 시작했다.

## 지속 관측·중단 경계

시작/종료 Orca terminal list에서 Backend/엔진/통계/UI는 모두 terminal0. 같은 검수 worktree의 다른 모델 선택 터미널은 읽기 전용 목록 확인만 했고 작업을 보내지 않았다. 시작 전 자기 실행기 외 dotnet/msbuild/testhost/vstest/python 계산 프로세스가 없었다. 실행 중 Windows 프로세스 이름/PID/누적CPU만 수집하고 명령줄은 수집하지 않았다. 시스템 전체 CPU에서 자기 API 사용분을 뺀 부하도 함께 기록했다.

실행 전에 `preregistration.json`에 경쟁 부하 기준을 고정했다: 외부 전체 CPU가 호스트의35% 초과를5초 간격3회 지속하거나, 별도 계산 프로세스가0.10코어 초과를2회 지속하면 취소. 1초 watchdog으로10:30, 배터리30% 이하/불명, AC·전원구성표·batterySaver 변경, input desktop 잠금/조회불가, 관측 gap20초 초과를 감시했다. 가용 물리메모리256MiB 미만/자기 private bytes가 선택 메모리 한도 초과/디스크 여유1GiB 미만/제품 실패·검사 오류도 취소 사유다. 취소 시 자기 API에 cancel하고 terminal 상태와 부분 결과를 보존하도록 작성했다. 이번 실측에서는 중단 조건이 발동하지 않았으므로 부하 중 취소 지연을 새로 측정했다고 하지 않는다.

지속15회+종료1회 telemetry, 최대 간격5.063초. 수집 불가능한 보호 프로세스는203~205개여서 전체 프로세스 활동을 개별적으로 완전 증명하지는 못한다. 시스템 전체 CPU 관측은 이를 포함하며, 담당자 비활성 확인과 결합한 제한된 단독 benchmark 근거다. 모든 호스트 백그라운드 부하가0이었다는 주장은 아니다.

| 지표 | 관측 |
|---|---:|
| 장치 | i7-1360P, 물리12/논리16 |
| 전체 CPU 최대 | 32.20% |
| 외부 시스템 CPU 추정 최대 | 22.03%, 지속 중단 기준 미달 |
| 별도 계산 부하 관측 | 0 |
| API 프로세스 전체 누적CPU | 137.094 CPU초 |
| pilot를 둘러싼 CPU 샘플 차이 | 135.000 CPU초; 전후 샘플 경계 오버헤드 포함 |
| OS peak working set | 193,785,856 bytes (약184.8MiB) |
| 표본 최대 private bytes | 127,897,600 bytes (약122.0MiB) |
| 선택 메모리 한도 | 4,179,603,456 bytes; 관리메모리 정책이며 RSS 하드 상한 아님 |
| 최소 가용 물리메모리 | 5,782,069,248 bytes |
| 최소 디스크 여유 | 53,191,602,176 bytes |
| 종료 compute 저장 크기 | 5,358,350 bytes; DB/WAL/튜닝 등 포함 |
| 상태 API polling | 34회, p95 **35.36ms** |

CPU 누적 샘플은 calibration의 경우7.469 CPU초/10:09:50.303~10:10:00.422, pilot은135.000 CPU초/10:09:55.370~10:11:00.938 경계다. 경계가 겹치므로 두 수를 합산하지 않는다. 할당량/GC/온도/UI p95는 **null+미수집 사유**로 final-audit에 남겼다. API p95는 UI p95가 아니다. 장시간 thermal throttling·최대 메모리 안정성 또는 AC 성능으로 일반화하지 않는다.

## 전체 결과·독립 통계·저장 검산

pilot API의 limit100 **전체10페이지**를 고정된 종료 상태에서 읽었다. 유효 index가 정확히0..999, runId 중복/누락0, attempt1, phase=pilot, CPU/input/5인 순서 동일, 각 팀 피해=5인 피해의 정확 합계를 확인했다. 음수 카운터 없음. Hits는 평타, CriticalHits는 전체 피해 크리라 대소 제약을 추가하지 않았다. 모든20/1000 SQLite payload를 API 각 행과 대조했고 DB integrity_check=ok, experiments2개/batch_runs1020개다. calibration runId와 pilot runId 집합은 겹치지 않는다. warmup1·후보4회는 저장 정상 표본에 없고 실패/취소를 피해0으로 넣지 않았다.

전체 유효 표본의 팀/5인 평균·표본SD·HF7 분위수·독립 수치적분 Student 평균CI 및 strict cut/Wilson을 검산했다. 아래는 반올림한 요약이며 원값/모든 CI·분위수는 `pilot-audit.json`에 있다.

| 지표 (각 n=1000) | 평균 피해 | 표본SD |
|---|---:|---:|
| 팀 | 855,537,322.320 | 4,780,695.026 |
| 리타 | 73,214,968.944 | 503,777.633 |
| 블랑 | 43,958,763.877 | 158,800.365 |
| 앨리스 | 368,539,423.225 | 3,942,280.350 |
| 누아르 | 163,143,831.221 | 646,987.455 |
| 모더니아 | 206,680,335.053 | 2,586,974.026 |

팀 평균95% CI **[855,240,657.793, 855,833,986.847]**, median855,646,502, P5=848,007,878.45, P95=863,440,555.95. 사전 컷855,466,067을 **엄격히 초과(>)**한 표본517/1000=51.7%, Wilson95% CI **[48.6022%, 54.7848%]**. 통계의 n1000/partial=false를 전체 페이지·저장 행과 대조했다.

기존36개 지표의 Hoeffding/DKW gate, family alpha0.05, 사전 bounds/평균허용폭·고정N final 설계는 유지한다. 이번 pilot에서 그 bounds/margins를 평가 후 채워 동등성 통과로 만들지 않았다. 다른 실행/backend와의 분포 동등성은 **미판정**, holdout/추천 확정은 미수용이다.

## 다음 규모 예상과 미수용

아래는 이번 배터리 pilot의 전체 wall61.975초를 단순 선형 확장한 **예상**이며 실제1만/5만 실행이 아니다. 배터리·발열·시스템 부하·저장 증가·장시간 조건이 달라질 수 있다.

| 후속 규모 | 단순 예상 | 50%+180초 계획 여유 포함 |
|---|---:|---:|
| 1만 | 619.75초, **약10.33분** | 약18.49분 |
| 5만 | 3098.77초, **약51.65분** | 약80.47분 |

이번에는1000까지만 실행했다. 남은10:30 이전 시간을 이유로1만/5만을 시작하지 않았다. 후속은 새 사용자 승인/단독 시간대/전원 조건 및 별도 final preregistration이 필요하다. GPU 전체 전투·GPU 실패후CPU retry·추가 OL/자동 holdout·브라우저·실제 사용자 덱·배포는 미실행/미수용 상태를 유지한다.

## 근거와 인계

주 근거 디렉터리: **`artifacts/single-deck-qa/load1000-3db71912a601/`**. summary/final-audit, preregistration/pilot-admission, calibration/pilot request/status/timing/pages/statistics/audit, 고정 입력/build hashes, source hashes, telemetry.jsonl, latencies, Orca 전후 상태를 보존했다. `final-audit.json`은 원본 증거 JSON의 SHA도 기록하며 온라인 실행 후 읽기 전용 SQLite 재검산까지 통과했다.

QA 도구는 `run_load_window.py`(명시 날짜/마감 고정 실행), `win_telemetry.py`(읽기 전용 Windows 관측), `summarize_load.py`(오프라인 전체 저장·통계 대조)다. 실행기를 마감 이후 자동 재사용/연장하지 않는다. 실행 뒤 보존 실패를 status에 반영하는 QA 방어 분기만 보완했으며 해당 분기는 이번 원본 hash 불변 결과에 영향을 주지 않았고 전투를 재실행하지 않았다.

확정 QA 커밋·본 보고서·완료n/실측/후속 예상·미판정을 현재 Director **term_6e774787-1510-4736-872a-8b9be666e2b0**에 일반 터미널로 한 번 전달 후 대기한다. 입력 접수·Director 통합·사용자 EXE 배포 완료는 서로 구별한다.
