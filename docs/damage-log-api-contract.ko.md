# B1 damage log / burst tactic 외부 계약 및 진행 기록

기준: `e6935857c35caac198c649e744132d7391721ecb`. 엔진 계약은 커밋 `d7ce350`의 `docs/damage-log-engine-contract.ko.md` 전체를 읽고 반영했다. 해당 계약은 구현/검증 전 문서이며, Backend에는 다른 담당 브랜치를 병합하거나 미커밋 엔진 파일을 복사하지 않았다.

**현재 상태: 저장·내보내기·tactic 초안 저장과 입력 검증 구현. 새 엔진 실행 통합 미완료.** 아래 로그 fixture는 계약 형태의 합성이며 실제 실행에서 수집한 로그나 실게임 관측이 아니다. E1 구현 통합 후 실제 생성→저장→HTTP 조회/내보내기 검증이 필요하다.

## 로그 요청·저장·조회

- 실행 요청 위치는 `POST /api/runtime/skill-replays`의 `conditions.damageLog={characterId:"5004"}`다. 미지정/null은 미수집, 빈 객체는 E1 기본 앨리스 선택이다. 현재 엔진 타입에 해당 기능이 없으면 HTTP 409로 거부하여 조용히 무시되는 것을 막는다.
- 엔진 연결 후 `RunSkills`가 실제 `SkillReplay.Run` 반환값을 한 번 직렬화하여 기존 `dataRoot/skill-replays/{id}.json`에 저장한다. `SkillReplayArchive`는 같은 ID 덮어쓰기를 거부하고 고유 임시 파일을 flush한 후 이동한다. 조회/내보내기는 엔진을 실행하지 않는다.
- `GET /api/runtime/skill-replays/{id}` 및 `/export.json`: 저장 JSON 원문. 후자는 다운로드다. 현재 runtime catalog가 없어도 조회 가능하며 알 수 없는 필드, 구 규칙, null, 숫자 표현 및 배열 순서를 보존한다.
- `GET .../{id}/damage-log` 및 `/damage-log/export.json`: `{exportSchemaVersion:1, collectionStatus, replay}`. `replay`는 전체 원본 결과이며 메타데이터·지원 상태·입력·정책을 포함한다. `result.damageLog`가 없거나 null이면 `collectionStatus="not_collected"`; 비어 있는 수집 로그의 `status="complete", totalDamage=0, entries=[]`와 구별한다. 비어 있는 과거 로그를 새로 만들어 넣지 않는다.
- `GET .../{id}/damage-log/export.csv`: UTF-8, CRLF, CSV 인용 규칙. 첫 행은 header, 둘째 행은 `recordType=metadata`, 이후 `recordType=hit`이다. 0건/미수집에도 메타데이터 행이 있다. 열은 `recordType,frame,seconds,hitId,shotId,damage,cumulativeDamage,entryJson,metadataJson`이다.
- `metadataJson`은 JSON export envelope에서 `entries`만 제외한 값이다. 계정/게임/계산/runtime 스냅샷 ID, 규칙, 입력 조건, tactic, 로그 schema·상태·완전성·요약 합계가 남는다. `entryJson`은 피해 행 전체를 보존하므로 차지·버프 출처/유효 시각·공격력·방어력·계수·정수화 근거를 잃지 않는다.
- CSV는 저장 배열 순서 그대로 출력한다. frame은 60 FPS 프레임, seconds는 저장된 초 값이다. hitId와 shotId를 구별하며 동일 발사 다중 명중을 합치지 않는다. null shotId는 빈 셀이다. 요약·누적 피해를 재계산/보정하지 않는다. 분석 시 metadata 행을 피해 행으로 합산하지 않는다.
- 로그 schema 1만 CSV로 해석한다. 미지원 버전은 CSV 409, JSON은 원형 보존. `kind` enum 등은 기존 Wire 직렬화 값을 유지한다. 없는 상태를 false/0으로 추측하지 않는다.
- 잘못된 replay ID는 400, 존재하지 않는 ID는 404. 저장 ID와 파일 이름이 다른 손상 결과는 정상 응답하지 않는다.

## tactic 외부 JSON v1

`BurstTacticSettings`는 B1 외부 DTO이며 E1 내부 `BurstTactic`과 별개다. 필드는 E1 계약의 camelCase 이름과 같다.

```json
{"schemaVersion":1,"allowedCharacterIds":["i","ii","5004"],"stage1Priority":["i"],"stage2Priority":["ii"],"stage3Priority":["5004"],"burst3Rotation":["5004"],"firstBurst3CharacterId":null,"unavailablePolicy":"next_ready"}
```

`i`, `ii`는 합성 예시 ID이며 실제 요청에서는 현재 편성 ID를 사용한다. 허용 목록과 우선순위는 별개다. 각 단계 우선순위는 허용 후보의 정확한 순열, III 순환은 허용 III의 비어 있지 않은 부분집합, 첫 시전자는 순환 내 ID다. 중복/null 목록/편성 밖 ID/미지원 단계/다른 단계 후보/알 수 없는 버전·정책은 400이다.

- `PUT /api/accounts/{id}/burst-tactic` body: `{snapshotId, formationSlots:[5칸 문자열 또는 null], tactic:객체 또는 null}`.
- 응답: `{saved, stale:false, executionStatus, issues}`. `saved`는 `{accountId,snapshotId,formationSlots,tactic,savedAt}`다. null tactic은 `legacy`. 단계 누락은 `draft_incomplete`, `issues=["missing_stage_1", ...]`로 **초안 저장만** 허용한다. 완전한 후보 목록도 스킬 지원/실행 검증 전이므로 `requires_execution_validation`이다.
- 저장 시 현재 스냅샷 ID와 편성 5칸이 요청과 같아야 한다. 변경되었으면 409. 저장소는 계정 FK를 가진 별도 `solo_burst_tactics` 테이블이며 기존 계정/편성 payload를 수정하지 않는다.
- `GET /api/accounts/{id}/burst-tactic`: `{saved,stale,executionStatus}`. 미저장은 saved=null/legacy. 저장 이후 스냅샷 또는 편성이 달라지면 stale=true, 명시 tactic이면 executionStatus=stale. 저장된 설정은 임의 삭제하거나 새 편성에 재작성하지 않는다.
- 실행 시 저장 설정을 몰래 주입하지 않는다. 호출자가 복원한 설정을 `conditions.autoBurst.tactic`에 명시한다. E1 타입에 Tactic이 없으면 409. 통합 후에는 E1의 실제 실행 검증이 최종 판정하며, 저장 성공 자체가 실행 가능함을 뜻하지 않는다.
- tactic=null은 기존 `burst3Rotation`, `unavailablePolicy`, 불완전 편성 대기 의미를 보존한다. 명시 tactic과 legacy 순환/정책 혼용 거부는 E1 실행 검증 대상이다.
- III 순환은 E1 계약대로 성공한 III 시전 직후 **우선 슬롯에서 한 칸** 전진한다. 대체 시전자와 무관하며 대기·만료는 전진시키지 않는다. 제외 니케의 대체 시전 금지, 기존 지연/max 정책 및 앨리스 196000 충전은 E1 담당 실행 회귀다. B1은 이 동작을 재구현하지 않았다.

## 검증 및 잔여 의존성

SDK: 기존 로컬 .NET 10.0.400 사용. 쓰기 출력은 Backend의 bin/obj/.tools 및 고유 임시 테스트 폴더다. 원본 계정·기존 artifacts는 사용/변경하지 않았다. 기존 untracked `package-lock.json` 보존. 새 에이전트/Orca Run/Dispatch 생성 없음.

실행 명령의 `<dotnet>`은 `C:/Users/user/Documents/GitHub/Nikke-Simul/.tools/dotnet/dotnet.exe`다. `DOTNET_CLI_HOME`은 Backend `.tools/dotnet-home`, `NUGET_PACKAGES`는 기존 `.tools/nuget-packages` 캐시를 사용했다.

- 최초 `test --no-restore`: assets 없음 NETSDK1004. 최초 restore: 사용자 NuGet.Config 읽기 권한 거부. 권한 승인 후 로컬 캐시 `restore --locked-mode --source <기존 캐시> -p:NuGetAudit=false` 성공. 최초 테스트 코드의 raw-string 컴파일 오류 1건을 수정했다.
- `<dotnet> test tests/Nikke.Sync.Tests/Nikke.Sync.Tests.csproj -c Release --no-restore`: **71 통과, 실패 0, skip 0**. 기존 57 + 신규 14. 불변 저장·재시작·미수집/0 구분·legacy 기본값·CSV 순서/단위/합계/문화권·후보 거부·stale·계정 격리 검증. E1 모양의 합성 fixture를 포함하며 새 엔진 통합 통과를 뜻하지 않는다.
- `<dotnet> build src/Nikke.Api/Nikke.Api.csproj -c Release --no-restore`: 성공, 경고 0/오류 0.
- `<python> tests/Nikke.Sync.Tests/check_damage_log_api.py --dotnet <dotnet>`: **HTTP/저장 6개 검증 그룹 통과, 종료 코드 0**. 원문 조회/다운로드 일치, JSON/CSV 순서·단위·합계·메타데이터, 구버전 미수집/현재 catalog 독립, ID 400/404, 미통합 기능 409, tactic 저장/복원·후보 거부·편성 변경 stale을 검증했다. `<python>`은 `C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`다. PATH의 python/py는 사용할 수 없었다. 첫 HTTP 실행은 assertion 이후 테스트 SQLite 연결 미종료로 임시 DB 정리에 실패했으며, 명시 close 수정 후 재실행 성공했다. 고유 임시 DB/합성 runtime/합성 로그만 사용했다.
- `git diff --check`: 통과 (LF→CRLF 안내만 존재).

검증 중 E1 구현 `0eda677269f17f4ddf943017bd7f1eb44edb6170`이 제공되어 커밋된 DamageLog DTO와 계약을 읽기 전용 확인했다. 지시서의 다른 브랜치 병합 금지 및 Director 통합 소유권에 따라 Backend에는 가져오지 않았다.

미완료: E1 `d7ce350`/`0eda677`의 Director 통합, 실제 180초 로그 생성/합계/완전성/ON-OFF·RNG 검증, 실제 tactic 실행·저장·재실행 일치, UI 실연동. 현재 코드의 기능 존재 확인은 통합 완료 증거가 아니다. 발당 피해→사격 시간→버스트 사이클의 실게임 관측 비교는 미실행이다. CSV 파일이 만들어진다는 사실로 피해 공식 정확도를 주장하지 않는다.

## 변경 파일과 결과 커밋

- API: `src/Nikke.Api/Program.cs`
- 외부 DTO: `src/Nikke.Contracts/BurstTacticSettings.cs`
- Data: `RuntimeReplayService.Skills.cs`, `SkillReplayArchive.cs`, `DamageLogExport.cs`, `BurstTacticValidation.cs`
- Storage: `SnapshotStore.cs`, `SnapshotStore.BurstTactics.cs`
- 저장/API 테스트: `StorageTests.cs`, `SkillReplayArchiveTests.cs`, `DamageLogContractTests.cs`, `check_damage_log_api.py`
- 본 문서. Engine/Core/UI 및 공용 프로젝트 파일·README·기존 종합 문서 수정 없음.

구현·검증 결과 커밋: `0d49352` (`feat(backend): preserve replay logs and store versioned burst tactics`). 이 후속 문서 변경은 결과 ID만 기록하며 코드 변경이나 추가 통과 주장이 없다. Director는 B1 결과와 E1 커밋을 통합한 뒤 위 미완료 실행 검증을 수행해야 한다.

## B2 후속 대조 — 2026-09-11

시작 HEAD `bf19679`, 미커밋은 기존 `package-lock.json`만 있었다. 후속 지시서 전체/공통 경계/B2 절을 읽었다. E1 `908047f`의 `BurstTactic`, `DamageLog`, `SkillDefinitions`, `SkillReplay` 피해 확정/결과 생성, `TeamBurstController` 실행 검증·선택 경로와 UI `a78c10c`의 adapter, 전략 편집 모델, 실행 요청 및 문서를 `git show`로 대조했다. 다른 브랜치 병합·cherry-pick 및 다른 작업공간 수정 없음.

### 확인한 연결과 Backend 보완

`conditions.damageLog`와 `conditions.autoBurst.tactic`는 실제 E1 public property와 이름·타입이 일치한다. 통합 후 Wire의 camelCase/대소문자 무시 역직렬화 → `SkillReplay.Run` → 실제 확정 피해의 `DamageLogEntry`/`DamageLogSummary` → `SavedSkillReplay.Result` → 원문 archive 저장 흐름이다. 추가 실행이나 피해 재계산은 없다. E1가 확정 피해에 사용한 `Calculation` 및 실제 `Hit`, `Shot`, 버프 목록이 전체 entry JSON으로 보존된다. **코드 대조 결과이며 통합 실행 통과가 아니다.**

발견·수정한 Backend 결함:

1. 저장한 불완전 초안을 GET하면 실행 검증 대기 상태로 바뀌던 문제: GET에서도 `draft_incomplete`와 `issues`를 복원한다. stale이면 저장 상태를 유지하며 stale을 우선 표시한다. catalog 없이도 초안 단계 누락을 알 수 있다. 완전한 후보 목록도 실제 스킬 시전 가능 여부를 확정하지 않으므로 `requires_execution_validation`이다.
2. 대소문자 무시 역직렬화와 대소문자 구별 capability guard가 불일치하던 문제: 같은 규칙으로 필드를 찾고 중복 표기/잘못된 객체·배열 타입/잘못된 JSON 값을 400 ArgumentException으로 처리한다. 실제 engine property 부재는 여전히 409다.
3. UI 사설 모델이 무시되던 문제: `autoBurst.tactics`(복수)는 400으로 거부하고 `autoBurst.tactic`을 안내한다. 외부 `BurstTacticSettings`의 알 수 없는 속성도 400으로 거부하여 `{version:2,allowlist:...}`가 빈 초안으로 저장되지 않는다.
4. 계산 자료가 고정 `root/data/local/calculation`을 읽던 격리 결함: `dataRoot/calculation`으로 통일했다. 기본 실행 경로는 같고 `NIKKE_DATA_ROOT` 지정 실행은 DB·runtime·계산 자료를 같은 복사본에서 사용한다.

### U2에 필요한 매핑과 의미 제약

| UI a78c10c 모델 | 서버/E1 v1 매핑 및 검증 |
|---|---|
| `version:2` | UI 내부 버전이다. 서버 tactic은 `schemaVersion:1`; 날짜 문자열 로그 버전과도 다르다. |
| `allowlist: {id:boolean}` | 현재 편성의 허용된 ID만 `allowedCharacterIds`에 명시. 제외 ID는 우선순위·순환에서도 제외하되 다른 편성에 남은 stale 설정을 몰래 정리하지 않는다. |
| `priority.stage1/2/3` | 순서를 유지하며 허용 ID로 걸러 `stage1Priority`, `stage2Priority`, `stage3Priority`에 대응. 각 목록은 해당 단계 허용 후보의 정확한 순열이다. |
| `stage3Mode=alternate` | 허용 III 순서 → `burst3Rotation`; `firstCaster` → `firstBurst3CharacterId`(순환 내 ID 또는 null). 순환은 2명 전용이 아니다. |
| `stage3Mode=priority_only` | 고정 우선 후보를 단일 원소 `burst3Rotation=[stage3Priority[0]]`로 표현할 수 있다. `firstCaster`가 이 후보와 다르면 그대로 표현할 수 없으므로 수정 요청/실행 차단이 필요하다. **첫 회만 다른 후보를 사용한 뒤 우선순위로 복귀하는 정책은 v1에 없다.** 임의로 첫 시전자를 버리거나 영구 우선으로 바꾸지 않는다. |
| `fallbackPolicy` | tactic 내부 `unavailablePolicy`, 문자열 `next_ready`/`wait_preferred` 그대로. |
| 기존 autoBurst `burst3Rotation`, `unavailablePolicy` | 명시 tactic 사용 시 외부 legacy 순환은 빈 배열, 외부 정책은 `next_ready`(또는 둘 다 생략). tactic과 비기본 legacy 옵션 혼용은 실행 400. |
| `localStorage` 저장 | 서버 PUT `{snapshotId,formationSlots,tactic}` 성공을 확인한 뒤 GET의 `saved.tactic`을 복원. 다음 실행에 `conditions.autoBurst.tactic=saved.tactic` 명시. 자동 주입 없음. snapshotId는 현재 계정 스냅샷, formationSlots는 순서/빈칸 포함 현재 5칸이다. |

서버 저장은 사용자 입력을 검증하고 보존하며 UI 모델을 대신 변환하지 않는다. 서버 v1은 임의의 III 부분집합 순환을 허용하므로, UI의 두 모드만으로 복원할 수 없는 설정은 일반 순환 모델로 보존하거나 편집 불가/변환 필요를 표시해야 한다. 모든 III가 들어 있다고 확대 해석하지 않는다. 완전한 tactic도 실행 시 최신 입력 멤버/스킬에 대한 E1 검증을 거친다.

상태/오류: PUT/GET `legacy`, `draft_incomplete`, `requires_execution_validation`, GET `stale`. 요청 형식·후보·단계 오류는 400, snapshot/formation 저장 충돌 및 현재 엔진 미통합은 409, 없는 계정/replay는 404. Minimal API 자체 바인딩 실패의 400은 body가 없을 수도 있으므로 UI는 HTTP 상태와 fallback 오류 문구를 처리해야 한다.

로그 어댑터 수정 필요(U2 소유):

- 서버 응답은 `res.hits`나 `replayData.damageLogs[id]`가 아니라 `res.replay.result.damageLog.entries`; 직접 실행 응답이면 `saved.result.damageLog.entries`다. a78c10c의 자동 mock fallback은 실연동 성공으로 사용할 수 없다.
- 한 실행에서 선택 대상 **한 명**만 수집한다. `?characterId=`는 저장 로그를 새 대상 로그로 만들지 않는다. 저장된 `characterId`와 UI 선택이 다르면 미수집으로 표시하고 다음 실행에 선택 대상을 명시한다. 과거 결과를 재실행 결과로 위장하지 않는다.
- `entry.source` → 캐릭터, `hitId` → 명중, non-null `shotId` distinct → 발사. `kind`는 현재 Wire enum 숫자(`NormalHit=2`, `DirectSkillHit=3`, `AdditionalHit=4`)다. 추가타를 새 발사로 세지 않는다.
- `chargeRatioRaw/10000` → 0~1 비율(퍼센트 표시는 /100); `fullCharge`, `effectiveChargeFrames`, `actualChargeFrames`의 null을 false/0으로 채우지 않는다. frame/60이 초다.
- `hit.crit`, `hit.core`, `hit.fullBurst`, `ownBurstEffectActive`를 각각 사용한다. 자체 효과 구간을 팀 진입 시각+600/900으로 만들지 않는다. `calculation.policy/terms`와 `hit`/`buffs`를 실제 검산 근거로 표시한다. 크리·코어·풀버스트를 독립 곱으로 다시 계산하지 않는다.
- JSON/CSV는 서버 내보내기를 사용하면 스냅샷·조건·버전·완전성과 전체 근거가 보존된다. `not_collected`/complete zero/truncated/알 수 없는 schema를 구분한다.

### 통합 후 실행 절차와 입력

준비 스크립트: `tests/Nikke.Sync.Tests/check_damage_log_integration.py`. **이번 Backend에는 E1 코드가 없고 Director 통합 기준도 제공되지 않아 실제 엔진 HTTP 통합 검사는 미실행이다.** capability 부재 검사를 실제 실행 지원으로 보고하지 않는다.

Director가 B2 + E1 `908047f`(후속 수정 포함)를 통합한 고정 commit에서 실행:

```powershell
& '<python>' tests/Nikke.Sync.Tests/check_damage_log_integration.py --dotnet '<dotnet>' --source-data '<준비된 dataRoot>' --request '<실행요청.json>' --expected-commit '<Director 통합 커밋>'
```

입력 dataRoot: `accounts.db`, `game-catalog.json`, hash 검증 가능한 `runtime/current.json` 및 해당 catalog, `calculation/current.json` 및 해당 계산 자료. 요청 snapshotId는 그 계정의 현재 스냅샷이고 지원된 1~5인(앨리스 및 실행 가능한 I/II/III 포함), 실제 스킬 레벨/계산 가능 스펙을 사용한다. `conditions.combat.durationFrames=10800`, `critMode="off"`, SG 포함 시 명시 pellet 정책, `roundingPolicy` 명시, `damageLog.characterId="5004"`, 완전한 `autoBurst.tactic`을 지정한다. 반복 일치를 위해 `autoBurst.stageDelayMinFrames=stageDelayMaxFrames`(예: 둘 다 1)를 지정한다. 이는 검증 입력의 결정적 조건이며 제품 기본 1~10/28/max 정책을 변경하지 않는다. casts/fullBurstWindows는 자동 모드와 혼용하지 않는다.

스크립트는 HEAD 일치·미커밋 제품 변경 없음 확인 → API 재빌드 → 원본 DB read-only backup 및 runtime/계산 자료 복사 → 격리 API 시작 → 편성/tactic 저장·GET 복원 → 실제 180초 POST → 원문/JSON/CSV 대조 → 결정적 재실행 → 로그 OFF 비교 → legacy null tactic/합성 구 replay 필드 누락 → 잘못된 실행 입력 거부 및 stale 순으로 검사한다. 출력은 자기 작업공간 `artifacts/b2/integration-{uuid}/`의 로그·복사 DB·실제 결과·summary.json이며 실패도 기록한다. 원본 connections/jobs/session/raw를 실행에 사용하지 않는다. summary의 실제 엔진 조건과 합성 역사 fixture는 별도로 명시된다. 게임 관측/산식 독립 정답 판정이 아니다.

### B2 실제 실행 기록

- `<dotnet> test tests/Nikke.Sync.Tests/Nikke.Sync.Tests.csproj -c Release --no-restore --logger trx --results-directory <실행별 경로>`: **81 통과 / 0 실패 / 0 skip**. TEMP/TMP도 Backend 실행별 경로로 설정했다. 근거: `artifacts/b2/unit-748268c9ab7a4b619db85c6ed5d84fa5/user_BOOK-UB6JGJ0BM4_2026-09-11_11_39_05_net10.0.trx`.
- 최초 샌드박스 컴파일은 obj DLL 쓰기 CS2012로 실패해 정식 권한 승인 후 재시도했다. 중간 실행은 빌드 중 추가된 plural `tactics` 테스트와 이전 Data DLL이 섞여 80 통과/1 실패였으며 최종 코드를 고정한 재빌드에서는 위 81개 모두 통과했다. 실패 기록 `artifacts/b2/unit-25d8a06b62db473f99ef78b7dc04de80/`도 보존했다.
- `<python> tests/Nikke.Sync.Tests/test_damage_log_integration.py`: **6 통과**. 합성 기대값으로 CSV 누락/잘림/메타데이터 손실/동일 frame 행 순서/seconds 오류를 탐지하고 다중 명중 2개가 발사 1개로 집계됨을 확인했다. 이는 통합 검사 assertion 자체의 독립 검증이다.
- `<python> tests/Nikke.Sync.Tests/check_damage_log_integration.py --help`: 실행 성공. 통합 runner의 실제 엔진 POST 경로는 **미실행**이다.

- `<dotnet> build src/Nikke.Api/Nikke.Api.csproj -c Release --no-restore`: **성공, 경고 0/오류 0**. 최초 샌드박스 API DLL 쓰기 CS2012 실패 후 정식 승인 재시도 결과다.
- `<python> tests/Nikke.Sync.Tests/check_damage_log_api.py --dotnet <dotnet>`: **7개 그룹 통과, 종료 코드 0**. 합성 DB/runtime/저장 로그를 사용한 실제 HTTP 검사이며 실제 엔진 로그 생성 검사는 아니다. 신규 초안 GET 복원, 사설 UI 모델·plural tactics·잘못된 conditions 거부 포함. 근거: `artifacts/b2/http-8c8b62faba02410a9019caf19004c816/summary.json`.
- `git diff --check`: 통과. B2 검증 출력은 모두 Backend 실행별 경로이며 기존 B1 및 타 담당 artifacts를 덮어쓰지 않았다.

변경 파일: `src/Nikke.Api/Program.cs`, `src/Nikke.Contracts/BurstTacticSettings.cs`, `src/Nikke.Data/{BurstTacticValidation,RuntimeReplayService.Skills}.cs`, `tests/Nikke.Sync.Tests/{DamageLogContractTests.cs,check_damage_log_api.py,check_damage_log_integration.py,test_damage_log_integration.py}`, 본 문서. Engine/Core/UI 및 기존 사용자 파일 수정 없음.

B2 결과 커밋: `7823071` (`fix(backend): validate tactic mappings and prepare engine API verification`), 기준 `bf19679`. 이 후속 문서 커밋은 결과 ID 기록만 추가한다. 실제 엔진 HTTP 통합/실게임 검증은 위 사유로 미실행이며, 사용자 변경 `package-lock.json`은 커밋하지 않았다.
