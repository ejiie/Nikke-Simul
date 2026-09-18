# Q-CPU-SCALE: worker2/4/8 비교 실험

## 최신 결과: 실행·검산 수용, 성능 우열 미확정

QA 확정 `8871f3860c1d97411a8beba610e933584016654c`의 보고서와 `artifacts/single-deck-qa/worker-scale-ad693bd7caef/final-audit.json`을 Director가 검토했다. evidenceHashes67파일 SHA-256 직접 대조 불일치0, 제품40078d0 대비 src/apps/scripts/tools/data-pipeline 차이0. Director가 전투를 재실행한 것은 아니다.

| worker | 1천회 첫 측정 초 | 역순 측정 초 | 평균 초 |
|---|---:|---:|---:|
| 2 | 62.152701 | 56.133613 | 59.143157 |
| 4 | 40.489175 | 35.539948 | 38.014561 |
| 8 | 33.874491 | 37.563313 | 35.718902 |

실제 maxActive2/4/8,6묶음6000회 및 제외warmup192 전체검산 통과. 초기 ProjectReference DLL hash 불일치로 전투 전 중단한 근거는 별도 보존됐으며 최종은 기존 수용DLL5개를 고정했다. 모든4/8 관측이2보다 짧았으나 첫방향8/역순4로 승자가 달랐고 반복 범위/평균10.18%/13.02%/10.33%가 사전10%선을 모두 넘었다. **실행·결과 무결성은 수용, 안정적 성능우열/최적worker는 미확정**이다. 단순평균 최저8을 근거로 제품 자동정책을 변경하지 않는다.

실측10:42:36~10:47:20,배터리71→66%/Offline/SAMSUNG MODE 유지,중단조건미발동·잔여활성0. 보호프로세스조회 한계/온도·GC미수집을 유지한다. API/SQLite/UI 미포함 QA engine harness이므로 이전API61.975초 대비 개선율·메모리절감률로 사용하지 않는다. 제품Plan1/2·원본EXE·배포·push 변경 없음,15worker는 사용자 지시대로 보류. 이번 측정 예약은 완료로 해제하며 추가부하를 배정하지 않았다. 아래 착수 상태는 역사 기록이다.

## 승인과 코드 확인

2026-09-18 사용자가 worker4/8 실험을 명시 요청했다. 앞선 동일 배터리 측정 선택을 유지한다. 1만회 후속은 실제 배정 전 대화가 전환됐으며 이번에는 worker 비교를 우선한다. SIMD/프레임 건너뛰기/GPU/제품 자동정책 확대는 이번 범위가 아니다.

제품40078d0 `ExecutionPolicy.Conservative`의 기본 MaxWorkers는8이지만 명시값·가용논리CPU-1·메모리로 자원 상한을 구한다. 16논리 가용이면 메모리가 허용하는 경우 명시값에 따른 자원 상한은15다. 이는 실행 능력이나 최적성 입증이 아니다. 실제 `Plan`은[1] 또는[1,2]뿐이고 강제 worker 필드도 없으므로 MaxWorkers=4/8 API 호출은 실제4/8 실행을 보장하지 않는다. 캐시 조작으로 우회하지 않는다.

검수 기존 `PreparedCompute.Restore`/IPreparedExperiment.Run을 호출하는 **검수 전용 병렬 실행기**로 측정한다. 제품 DLL/입력/전투 규칙은 유지한다. 현재 제품 API/자동정책/저장 포함1천회61.975초와 실행 범위가 다르므로 동일 표의 직접 속도 개선율 기준으로 사용하지 않는다. worker2를 같은 실행기로 다시 측정한다.

## 단독 구간 및 소유

지시 시각10:34~10:35 KST, 배터리75% Offline/SAMSUNG MODE, Backend/엔진/통계/UI terminal0, 검수 완료 대기 상태를 조회했다. 새 구간은 **2026-09-18 10:35~10:58 KST**로 제한한다. 준비시간 포함, 자동 연장 없음. Director는 별도 빌드/부하를 하지 않는다. 관측은 완전한 외부부하0 보장이 아니다.

기존 검수 worktree `C:/Users/user/orca/workspaces/Nikke-Simul/검수`, handle `term_234e279b-927e-4118-a8fe-f90736db2e68` 하나만 사용한다. 제품40078d0/QA4c0c06a와 기존 package-lock 보존. 소유는 QA 실행기/tests/새artifacts/보고서뿐이다. 제품소스/정책/캐시/계정DB/원본 EXE/5180/5181/타worktree 편집 금지. 새worker/Run/Dispatch/lifecycle 없음.

## 실험 설계와 수용 조건

1. 이 문서 전체와 기존 load1000 보고서/PreparedCompute·병렬계약을 읽는다. 이전 합성 prepared 입력을 검수 artifact에서 읽기 전용 재사용 가능하나 원본 사용자 계정 복제는 금지한다. snapshot/물리입력/data/engine/rules/tactic/DLL hash를 고정한다. 같은 공개5인400/180초/DEF30925/sample crit 조건이다. 고정seed·전투규칙·정수화·버스트·MG처리 변경 금지.
2. Release 전용 harness를 작성하고 smoke/취소/카운터 검증 후 빌드 작업이 끝난 상태에서 시작한다. 준비 객체1회/private input, run별상태·RNG는 제품 경로를 사용한다. Parallel.ForEachAsync의 MaxDegreeOfParallelism을2/4/8로 지정하고 실제 동시활성 호출 수를 계측해 요청값과 구분한다. 작업 수가2개뿐인 시험으로4/8 포화를 주장하지 않는다. 각 run 고유ID/index/phase=pilot, 실패와취소·정상0 분리.
3. 측정 전에 새 preregistration 파일에 순서 **2→4→8→8→4→2**, 각 묶음 완전전투1000회(총6000), 각 묶음 직전 동일32회 warmup(집계 제외), 중단조건과 범위를 고정한다. 같은 프로세스/입력/코드/수집·출력 방법을 유지한다. 순서 양방향은 편향 완화일 뿐 완전한 발열/JIT 통제를 입증하지 않는다. 각 묶음은 다른 묶음 종료 후 실행하며 동시 benchmark 금지.
4. 모든 후보가 같은 경로를 사용하도록 하고, 측정 시 run 결과는 지정 index 배열에 저장한다. 파일직렬화/독립 검산은 측정 후 수행하고 시간을 분리한다. 준비/워밍업/실제 전체1000회 벽시계/출력 시간을 각각 기록한다. 결과를 버리거나 병렬 태스크 생성 시간만 재지 않는다. 제품 API·SQLite·UI 경로를 포함하지 않은 **엔진 summary+QA 병렬harness** 결과로 명시한다.
5. 유효1000/1000,index0..999중복누락0/팀=5인/음수카운터0/입력불변을 확인하고 모든 결과 보존. 팀·5인평균/SD/CI와 출력checksum을 남긴다. 확률실행 checksum이 다른 것은 즉시 오류가 아니며, 독립 결과 통계 검산과 분포동등성 미판정을 분리한다. 좋은결과가 나올 때만 중단/재실행하여 순위 선택하지 않는다. 두 반복을 각각 보고하고 편차가 크거나 순서별 승자가 바뀌면 우열 미확정.
6. 전체 elapsed초/run/s, 실제 동시호출max, CPU사용·working set/private bytes/가용메모리·디스크·배터리·전원·외부부하를 동일 낮은 빈도로 수집. 제품자원 정책을 참고해 사전 메모리상한을 기록하고 실행중 적용한다. 온도/GC 등 미수집은null+사유. 필요시 기존 telemetry를 재사용하되 보호프로세스조회 한계를 유지한다. thread/core 고정·우선순위/전원설정 변경 없음.
7. 기존 중단기준 유지:10:58,배터리30%이하/불명,AC/전원모드변경,잠금/관측gap20초초과,가용메모리256MiB미만/자기private사전상한초과/디스크1GiB미만,외부전체CPU35%초과5초간격3회 또는 별도계산0.10코어초과2회,결과불일치 시 cooperative취소 후 모든 자기작업 종료확인/부분보존. 사전 smoke 실측상 전체예약 내 종료 여유가 없으면6000을 몰래축소하지 말고 미완료와 남은시간 보고. 원본/다른프로세스 강제종료 금지.
8. 완료 후 보고서 `docs/cpu-worker-scaling.ko.md` 및 확정 QA커밋/실제2·4·8 각2반복 측정표/근거/보존hash/제한·미판정을 현재 Director `term_6e774787-1510-4736-872a-8b9be666e2b0`에 한 번 전달하고 대기한다. 4/8이 유리해도 제품자동정책 적용/배포/GitHub push는 별도 단계다. 1만/5만·worker15/16·GPU/OL/새최적화는 이번에 실행하지 않는다.

## 전달 상태

기존 QA worktree `07c470de-0a43-4d90-9eb6-240a5de9258c::C:/Users/user/orca/workspaces/Nikke-Simul/검수`, handle `term_234e279b-927e-4118-a8fe-f90736db2e68`에 한 번 전달했다. 요청 `ea71ebd1-5633-485b-81ac-d45642f53bf0`는 accepted=true/input_accepted/turn_started, runtime `5dba61c3-6dac-47aa-86ae-224121c0a4f7`다. 실제 비교 완료·순위 수용은 아직 아니다.
