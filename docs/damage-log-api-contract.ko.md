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
