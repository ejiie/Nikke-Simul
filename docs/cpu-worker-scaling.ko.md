# Q-CPU-SCALE 배터리 worker2/4/8 비교 — 2026-09-18

**판정: 사전6묶음 총6000회 실행·전체 결과 검산 통과. 성능 우열은 미확정.** 실제 최대 동시 호출은 요청한2/4/8과 일치했으나 방향별 가장 빠른 worker가8→4로 바뀌고 모든 worker의 반복 편차가 사전10% 기준을 넘었다. 제품 자동정책 변경·배포 수용은 아니다.

검증 기준은 QA `4c0c06ae0847c0464e35df08533aef1105092b21`, 제품 `40078d06a3d236ec7de5987d6be3c96d2a34ec86`이다. Director `cpu-worker-scaling-2026-09-18.ko.md` 전체, 기존 load1000 보고서, PreparedCompute/PreparedSkillReplay와 IPreparedExperiment 계약을 읽었다. 소유 QA 코드·문서·새 artifacts만 추가했다.

## 비교 범위와 입력

이번은 **PreparedCompute.Restore/Run 실제 엔진 summary + QA Parallel.ForEachAsync 실행기** 비교다. 제품 API/SQLite/UI 경로·자동튜닝·캐시는 포함하지 않는다. 이전 API1000회61.975초와 직접 성능 비교하지 않는다. worker2도 같은 QA 실행기로 새로 두 번 측정한다. 제품 Plan은 여전히[1] 또는[1,2]이며 MaxWorkers4/8을 실제4/8 실행으로 표시하거나 캐시를 조작하지 않았다.

검수 artifact `load1000-3db71912a601/prepared-synthetic.json`만 읽기 전용 재사용했다. 원본 사용자 계정DB/세션/캐시를 복제하지 않았다. 새 `prepared-pilot.json`은 input.phase만 exploration→pilot으로 명시 변경했고 members/graph/conditions 및 물리 fingerprint는 동일하다. 공개5인 리타/블랑/앨리스/누아르/모더니아, 400,10800프레임,DEF30925,sample crit, 저장 합성 택틱이다. 고정 seed/전투 규칙/정수화/버스트/MG 처리는 바꾸지 않았다.

물리 fingerprint `f9cfbd31c4e250690a804b7fac2a7f1ab71d30c3c9bb0324fab74b2c1c57a70e`, engine=cpu-summary.1. data/rules/snapshot/tactic 해시는 이전 자기 입력의 `source-fixed-fingerprints.json`에 보존했고 실제 새 입력 파일 SHA 및 DLL SHA는 preregistration/build-hashes에 있다. 객체는 프로세스에서 한 번 Restore하여 준비하고 각 Run은 제품의 새 전투 상태와 RunRandom을 사용한다. 모든 묶음 뒤 private PersistedInput과 파일 hash가 동일함을 검사한다.

## 빌드 고정과 실행 전 검사

최초 QA ProjectReference 빌드는 경고0/오류0였으나 이전 수용 DLL과 hash가 달라 supervisor의 실행 전 검사가 중단했다. 제품 소스 diff는 없었다. 이 실패는 `worker-scale-01122f62ad05/`에 보존하며 engine 프로세스/측정 묶음은 시작하지 않았다. hash 변화 원인을 IL 분석으로 확정하지 않고 비교에 사용하지 않았다.

최종 QA 프로젝트는 본인 기존 `src/Nikke.Api/bin/Release/net10.0/`의 수용된 Data/Engine/Core/Contracts/Analysis DLL을 읽기 전용 Reference로 고정했다. 해당5개 SHA가 앞선 수용 artifact와 모두 일치하는지 재검사했다. 제품 DLL을 덮어쓰거나 캐시 파일을 고치지 않았다. 최종 빌드2.48초, 경고0/오류0. `scale-build-9d138618f656417ea6384be78304beb7/build-pinned.log`.

전체 측정 전에 smoke64(worker2) 완전전투를 검산하고, 음수 Hits를 주입한 QA validator 거부를 확인했다. 별도 cancel-smoke32 요청은20ms 취소 토큰으로 정상0/중단호출2/미완료32/실패0, 최대동시2, 반환 후 활성0, wall20.780ms였다. 취소된 전투를 정상0 피해로 만들지 않았다. smoke 결과는 본6000 표본에 포함하지 않는다.

## 사전 설계와 중단 기준

승인 구간은 **10:35~10:58 KST**, 준비 포함·연장 없음. 사전 파일에 **2→4→8→8→4→2**, 각1000회와 직전32회 warmup을 고정했다. 각 run은 고유 묶음ID/index, attempt1, phase=pilot이며 warmup은 별도 ID/파일로 제외한다. 측정 결과는 index별 배열에 보관하고 모든 태스크 종료까지 wall을 잰다. 파일 출력/검산/Analysis는 이후 별도 시간이다. 독립 Python 검산의 ack를 받은 뒤 다음 warmup을 시작하므로 별도 검산 부하가 다음 측정에 겹치지 않는다.

smoke64의4.564초에서6192회 예상441.558초,1.5배+180초를 더한842.337초가 당시 잔여918.822초 안에 들어와 전체 계획을 시작했다.6000을 축소하거나 유리한 묶음만 다시 실행하지 않았다. 두 방향 승자가 다르거나 반복 범위/평균이10%를 넘으면 우열 미확정으로 판정하도록 사전에 정했다. 두 반복과 순서 반전은 완전한 발열/JIT 통제 또는 통계적 순위 확정을 뜻하지 않는다.

메모리 사전 한도는 물리 메모리의1/4인4,179,603,456 bytes로 제품 기본 보수 한도를 참고했고 요청8×64MiB reserve보다 충분한지 확인했다. C#은 관리메모리와 deadline/stop 파일을100ms 단위로 확인하고, supervisor는1초 전원/잠금 watchdog 및5초 telemetry를 적용한다.10:58,배터리30%/불명,AC·구성표·batterySaver 변경,잠금/관측gap20초,가용물리256MiB/디스크1GiB 미만,자기private 한도 초과,결과오류 시 cooperative 취소한다. 외부전체CPU35% 초과3회 또는 별도계산0.10코어 초과2회라는 이전 경쟁부하 기준을 유지한다. 타 프로세스를 강제 종료하지 않는다.

## 결과

최종 실행은 **10:42:36.101~10:47:20.660 KST**, 한 프로세스PID4756에서 순차 완료했다. 입력 준비 Restore는 **107.641ms**, 배터리는 실측 시작 **71%→종료66%**, Offline/SAMSUNG MODE/batterySaver0 유지. 지시 시점75%와 준비 이후71%를 구분한다. 승인 구간 내 완료했으며 중단 조건은 발동하지 않았다. 프로세스 종료코드0/활성 호출0이고 종료 후 PID가 사라졌음을 확인했다.

| 사전 순서 | 요청 worker / 실제 maxActive | 정상 n | 전체1000회 wall (초) | run/s | 프로세스 CPU초 |
|---|---:|---:|---:|---:|---:|
| 1 | 2 / 2 | 1000 | **62.153** | 16.089 | 117.766 |
| 2 | 4 / 4 | 1000 | **40.489** | 24.698 | 137.625 |
| 3 | 8 / 8 | 1000 | **33.874** | 29.521 | 170.969 |
| 4 | 8 / 8 | 1000 | **37.563** | 26.622 | 188.250 |
| 5 | 4 / 4 | 1000 | **35.540** | 28.137 | 118.641 |
| 6 | 2 / 2 | 1000 | **56.134** | 17.815 | 106.281 |

실제 최대 동시 호출은 Interlocked로 Run 진입~반환 구간을 계측했다. 이는 CPU 물리코어8개가 내내100% 포화됐다는 뜻이 아니다.1000개 실제 작업을 모두 실행/보존했으며2개 태스크만으로4/8 동시성을 주장하지 않았다.

| worker | 첫/역순 반복 wall (초) | 평균 (초) | 반복 범위/평균 |
|---|---|---:|---:|
| 2 | 62.153 / 56.134 | 59.143 | **10.18%** |
| 4 | 40.489 / 35.540 | 38.015 | **13.02%** |
| 8 | 33.874 / 37.563 | 35.719 | **10.33%** |

첫 방향은8이 최저, 역순은4가 최저였다. 모든4/8 관측이2 관측보다 짧았다는 사실은 기록하지만, 사전 변동성 규칙상 안정적 우열/최적성은 확정하지 않는다.8의 CPU초가4보다 많았다는 관측도 배터리 에너지 효율 측정으로 승격하지 않는다. 온도·GC/JIT event·스케줄링 세부 계측이 없어 변동 원인을 하나로 확정할 수 없다. 좋은 시간만 선택하거나 평균만으로8 적용을 권고하지 않는다.

### 준비·warmup·출력 분리

각 묶음 직전32회 warmup을 동일 요청 worker로 완료했고 정상1000회와 다른 ID/파일에 보관했다. 입력 객체는 한 번만 준비했고 매 묶음 Restore/JIT 재시작을 하지 않았다.

| 순서 | warmup32 (초) | 결과 행 직렬화/파일쓰기 (ms) | 제품 Analysis+QA 행검사/저장 (ms) | 독립 Python 검산 (ms) |
|---|---:|---:|---:|---:|
| 1 | 2.120 | 5.496 | 73.181 | 314.569 |
| 2 | 1.290 | 3.564 | 46.129 | 206.997 |
| 3 | 2.396 | 5.146 | 69.785 | 271.394 |
| 4 | 0.892 | 15.445 | 15.312 | 257.687 |
| 5 | 1.214 | 3.280 | 14.205 | 250.334 |
| 6 | 1.695 | 3.505 | 13.949 | 252.880 |

출력 checksum 계산/측정 메타파일 쓰기도 측정 wall 밖이며 별도 개별 타이머로는 수집하지 않았다. 위 파일쓰기 열은 행 JSON 직렬화+쓰기 범위다. 전체1000회 wall은 Parallel.ForEachAsync의 모든 실제 Run과 index 배열 결과 보관, cooperative 태스크 종료까지 포함한다. 배열 초기 할당·입력 준비·warmup·후속 출력/검산과 구분하며 API/SQLite throughput으로 부르지 않는다.

### 모든 결과·통계 검산

각1000개 index0..999, 중복/누락0, 실패0/취소0/정상 피해0 표본0, attempt1,5인 순서·동일 input/backend/phase, 팀=5인 피해 정확 합계와 독립 비음수 카운터를 확인했다. Hits와 CriticalHits의 대소 제약은 두지 않았다.6000개의 고유 runId와 별도192개 warmup ID가 겹치지 않으며 모든 JSON 결과를 보존했다. warmup192개도 마지막 오프라인 전체 페이지 검사로 검산했다. smoke64와 cancel-smoke는 별도 파일이며6000/192에 포함하지 않았다.

묶음마다 실제 ComputeAnalysis가 생성한 팀·5인 n/평균/표본SD/Student 평균CI/HF7 분위수를 QA Fraction/독립 수치적분으로 검산했다. 모두 n1000/partial=false. 각 `block-N-wW-independent-audit.json` 및 `final-audit.json`의 blocks에는 팀과5인 전체 통계를 보존한다. 아래는 팀 요약이고 피해 단위다.

| 순서 / worker | 평균 | 표본SD | 평균95% CI |
|---|---:|---:|---|
| 1 / 2 | 855,720,613.996 | 4,849,606.960 | [855,419,673.161, 856,021,554.831] |
| 2 / 4 | 855,423,985.868 | 4,538,116.892 | [855,142,374.451, 855,705,597.285] |
| 3 / 8 | 855,919,337.582 | 4,668,668.970 | [855,629,624.797, 856,209,050.367] |
| 4 / 8 | 855,787,302.363 | 4,883,028.052 | [855,484,287.592, 856,090,317.134] |
| 5 / 4 | 855,738,850.549 | 4,649,697.369 | [855,450,315.040, 856,027,386.058] |
| 6 / 2 | 855,429,098.320 | 4,609,945.893 | [855,143,029.577, 855,715,167.063] |

각 행 결과의 SHA-256을 계산해 파일과 재대조했다.6개 checksum은 timing/final-audit에 원문 보존했다. 확률 전투의 checksum/표본평균이 서로 다른 것을 오류로 판정하지 않았다. 같은 분포라는 주장도 하지 않았으며 기존 Hoeffding/DKW의 사전 bounds/margins 미등록으로 분포동등성은 미판정이다.

### 지속 부하·보존 관측

시작/종료 Orca 조회에서 Backend/엔진/통계/UI terminal0, 실행 전 자기 supervisor 외 계산 프로세스0. 지속56회 telemetry, 최대 간격5.125초, 외부 계산 부하 관측0. 시스템 전체 CPU 최대49.73%, 자기 harness 사용분을 뺀 외부 CPU 최대23.36%로 사전 지속35% 기준 미달이었다. 보호 프로세스194~197개는 개별 조회 불가라 이름/PID별 완전 독점 증명이 아니며 전체 시스템 CPU 감시로 보완했다. 프로세스 명령줄/민감정보는 수집하지 않았다.

가용 물리메모리 최소6,962,364,416 bytes, 디스크 여유 최소52,702,011,392 bytes. C#에서 관측한 프로세스 lifetime peak working set은99,201,024 bytes, 측정 표본 최대 private bytes는62,324,736 bytes로 사전4,179,603,456 한도 아래였다. 관리 heap 감시를 OS RSS 하드 상한 보장으로 확대하지 않는다. 메모리/CPU/전원/배터리의 묶음별 관측은 final-audit 및 telemetry.jsonl에 있다. 온도/할당량/GC/UI 지표는 null+미수집 사유로 남겼다. 실제 부하 중 안전 중단은 발동하지 않았으며 사전 cancel-smoke와 구분한다.

## 근거와 재현

최종 근거는 **`artifacts/single-deck-qa/worker-scale-ad693bd7caef/`**, 핵심은 preregistration/admission/preparation/build-hashes/summary/harness-summary/final-audit,6묶음 rows/timing/statistics/independent-audit, warmup/smoke 결과,telemetry와 Orca 전후 조회다. 엔진 summary의6000회 실행은 한 프로세스/입력/DLL/배열 저장/출력 방식으로 수행했다. 최종 runtime의 C# 및 Python 오류0, 독립6묶음 검산6/6 통과. 처음 DLL 불일치로 중단한 준비 실행을 통과 수에 합산하지 않는다.

QA 실행기는 `tests/single_deck_compute_qa/ScaleProbe`, supervisor는 `run_worker_scaling.py`, 사후 읽기 전용 집계는 `summarize_worker_scaling.py`다. Release 빌드 전에 위 수용 API DLL이 준비돼 있어야 하며 supervisor가 그 SHA를 기준 fixture와 대조한다. 실행 날짜/10:58 마감은 코드와 사전 파일에 고정돼 있어 이후 구간 자동 재사용/연장은 하지 않는다. 재현을 위한 새 구간은 별도 지시가 필요하다.

## 보존·미수용 경계

이 PC에서8은 기본 자원 상한 값일 뿐 하드웨어 최대 worker가 아니다. 현행 자원 규칙은 가용논리CPU-1/명시 한도/메모리에 따라 달라지며 이번은2/4/8만 시험한다.15/16·전역 최적 worker·자동정책 확대·AC/다른 PC·장시간 thermal 안정성은 미판정이다. bounds/margins가 사전 등록되지 않은 Hoeffding/DKW 분포동등성 및 자동 추천도 미판정으로 유지한다.

원본 계정/세션/캐시/EXE/5180/5181·다른 worktree·package-lock을 보존했다. package-lock SHA-256 `2ef4178aa07ddd9ac2e4d47422038d02d8adaadfb15586cee6a2f1995253c767` 및 기존 합성 prepared 파일 hash 전후 동일. 이번은 이전 자기 합성 prepared artifact를 사용하여 원본 공개12파일도 다시 열지 않았다. 제품 소스40078d0 대비 src/apps/scripts/tools/data-pipeline 차이0. SIMD/프레임 건너뛰기/GPU/OL·1만/5만·배포/push·새 worker/Run/Dispatch/lifecycle 실행 없음. 같은 worktree의 다른 모델선택 터미널에 작업을 보내지 않았다. 결과는 현재 Director `term_6e774787-1510-4736-872a-8b9be666e2b0`에 확정 QA 커밋/본 보고서/측정표/근거/미판정을 한 번 인계한 뒤 대기한다.
