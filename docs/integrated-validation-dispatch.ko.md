# 통합본 검증 지시 (사용자 승인 1~3 실행)

통합 기준: `a0738accb16500e52621811fac0dac7259cb7f76` (엔진 3b92101, Backend b63ad12, UI 3f9b717 포함). 기존 지시서의 통합본 미제공·e693585 기준 제한을 이 문서가 대체한다. 자기 브랜치가 이 커밋의 조상이면 미커밋 변경을 보존하고 `git merge --ff-only a0738accb16500e52621811fac0dac7259cb7f76`으로 반영한다. 실패하면 강제 reset/stash/checkout 없이 보고한다.

적용 지침, README, docs/p04-team-burst.ko.md, docs/damage-log-engine-contract.ko.md, docs/damage-log-api-contract.ko.md, docs/damage-log-ui.ko.md를 읽는다. 검수·통계는 앞선 지시가 미전달되어 작업이 수행되지 않았다. 기존 터미널은 입력 차단으로 보존했으며 이번 새 세션만 본인 작업공간의 편집 소유자다. 추가 워커를 만들지 않는다.

## 공통

- 원본 계정·스냅샷·과거 artifacts·package-lock.json을 보존한다. 다른 작업공간은 확정 결과 읽기만 가능하다. 제품 수정은 UI 지정 범위 외 금지. 관련 변경만 자기 브랜치에 커밋하고 push/배포/다른 브랜치 임의 병합 금지.
- .NET: C:/Users/user/Documents/GitHub/Nikke-Simul/.tools/dotnet/dotnet.exe. Python: C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe. 공유 NuGet cache: C:/Users/user/Documents/GitHub/Nikke-Simul/.tools/nuget-packages. DOTNET_CLI_HOME과 테스트 출력은 자기 작업공간. 권한 거부는 정식 승인 절차를 사용한다.
- 통과는 실제 실행 기록으로만 판단한다. 합성 입력의 실제 엔진/API 실행은 게임 실측이 아니다. 피해 공식·충전 196000·세 전이 지연을 근거 없이 변경하지 않는다.
- Director는 전체 빌드/C# 회귀와 격리된 실제 API/브라우저 검사 도구를 담당한다. 보고는 담당 문서에 기준/결과 커밋·명령·실제 결과·실패/미실행·잔여 결함을 남긴다.

## Q3 검수

소유: 독립 검수 스크립트/fixture/tests 및 docs/damage-log-verification.ko.md. 제품 코드는 수정하지 않는다.

1. 통합본에서 독립 검수: 로그 합계·shot/hit·180초·ON/OFF·null/0/미수집, 자체 버스트 vs 팀 풀버스트, tactic 허용/순위/III 교대/첫 시전자/대체·대기/stale/저장 복원, 구버전, 기존 충전·전이 지연. 과거 결과를 이번 통과로 인용하지 않는다.
2. 특히 실제 엔진/API DTO와 UI 어댑터를 대조한다. 초기 점검에서 UI가 `res.hits`를 기대하지만 서버는 `replay.result.damageLog.entries`를 반환하고 실행 요청에 damageLog 선택이 없으며 autoBurst legacy 옵션과 tactic을 혼용하는 문제를 Director가 발견했다. UI 담당이 수정할 예정이므로 제품을 교차 편집하지 않고 독립 재현과 수용 테스트를 작성한다.
3. 기존 검증 스크립트의 고정 artifacts 출력은 실행별 새 경로로 분리한다. 필요하면 새 q3 전용 도구를 사용해 기존 증거를 보존한다. 실제 API 검증에 필요한 데이터는 원본을 직접 수정하지 않는다.
4. 최종 고정 수정 커밋이 아직 없으면 a0738ac 재현 결과와 검수 도구를 먼저 커밋하고, 어떤 테스트가 수정본에서 재실행되어야 하는지 명시한다. 오류를 발견하고 검사 작성만으로 통합 통과를 주장하지 않는다.

## S3 통계

소유: 독립 분석 도구·전용 테스트 및 docs/damage-calibration-analysis.ko.md. 제품 엔진/API/UI 수정 금지.

1. 실제 로그 스키마(adapter)를 읽고 관측값과 시뮬레이션의 매칭·절대/상대 오차·미매칭·누락·0분모를 분리하는 최소 도구와 합성 테스트를 구현한다. shotId 없는 스킬 피해와 추가 명중을 새 발사로 세지 않는다.
2. 먼저 엔진 확정 예제를 읽어 실제 로그를 분석한다: C:/Users/user/orca/workspaces/Nikke-Simul/시뮬레이션-엔진-담당/artifacts/e2/79301e0197c84a8195b553adad062de9/engine-example-c7c29fe7eb3a4fcfa3c218c7d02d36c9/{input,result,manifest}.json. manifest/hash를 확인하고 자기 출력은 별도로 생성한다. 이것은 합성 입력으로 실제 엔진이 생성한 결과이며 실게임 관측이 아니다.
3. 발당 피해를 차지·crit/core·자체 버스트·팀 풀버스트 조건별로 검산하고, 다음 차지/발사/재장전 간격, 마지막 사이클을 분석한다. 관측 데이터 부재는 오차 0이 아니다. 알려진 오차·정확 일치·미매칭·0 관측 테스트를 포함한다.
4. 실제 API SavedSkillReplay wrapper와 native result 모두 명시적으로 지원하고 미지원 버전/잘림을 표시한다. Director의 계정 복사본 API 결과가 생기면 같은 분석을 적용할 수 있게 CLI 입력 경로를 제공한다. 엔진 자동 보정·실전 추천·대규모 MC는 금지한다.

## U3 UI 통합 결함 수정

소유: apps/desktop-ui, UI 전용 테스트, docs/damage-log-ui.ko.md. 다른 담당 제품 파일 수정 금지.

1. 위 통합 기준으로 자기 브랜치를 안전하게 fast-forward한 후 실제 E1/B2 데이터 형식으로 어댑터를 수정한다. 실행 요청에 선택 characterId의 damageLog를 포함한다. server response는 replay.result.damageLog, 직접 결과는 saved.result.damageLog다. collectionStatus와 schemaVersion/complete/0/truncated/미수집/API 오류를 구별한다. 실제 데이터가 있어도 res.hits가 아니라는 이유로 미수집 처리하지 않는다.
2. 명시 tactic 사용 때 legacy burst3Rotation=[]와 unavailablePolicy=next_ready를 사용하거나 생략한다. 내부 tactic의 정책은 유지한다. 사용자 정책이 서버에 의해 거부되는 혼용을 제거한다.
3. DTO 왕복에서 rotation 부분집합/순서와 firstBurst3CharacterId=null을 보존한다. priority_only와 다른 첫 시전자 조합은 조용히 변경하지 말고 검증 오류 또는 정확히 표현 가능한 편집 UI를 제공한다. stale ID/계정·편성 변경 및 비동기 복원이 설정을 덮어쓰지 않게 한다.
4. 실제 numeric kind, source, hitId/nullable shotId, chargeRatioRaw/10000, nullable fullCharge/actual/effectiveChargeFrames, hit.crit/core/fullBurst, ownBurstEffectActive, calculation.terms/policy, buffs를 명시적으로 매핑한다. 자체 효과 구간을 풀버스트 시작+600으로 만들어내지 않는다. 원본 계산 근거를 보존한다. 명중/발사 비율을 명중률로 표시하지 않는다(펠릿/추가타로 100% 초과 가능).
5. JSON/CSV 다운로드는 실제 서버 내보내기 원문과 메타데이터를 보존한다. 기존의 사설 mock DTO만으로 테스트하지 말고 확정 엔진 예제 및 실제 Backend envelope를 fixture로 검증한다. 실제 브라우저/API는 Director가 병행 검증한다. 테스트·문서·작은 커밋으로 반환한다.
