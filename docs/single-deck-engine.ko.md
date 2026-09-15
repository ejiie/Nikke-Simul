# 단일 덱 CPU/GPU 엔진 작업

기준 `a5ccba6663241e61783b509fc69098ad3c9ecef2`. 시작 `3b92101`은 기준의 조상이므로 ff-only 반영했고 기존 package-lock.json을 보존했다. 다른 작업공간/원본 데이터/캐시/EXE/5180/5181은 변경하지 않는다.

## Backend 호출 계약 (선행 제공)

B-CPU `f2327e5`의 `docs/single-deck-compute-contract.ko.md`와 `src/Nikke.Contracts/Compute.cs`를 읽었다. 외부 DTO/route는 그 계약을 따른다. 엔진은 Contracts/Data/Jobs를 참조하지 않는다.

`Nikke.Engine.Skills.PreparedSkillReplay.Create(IReadOnlyList<SkillReplayMember>, SkillGraph, SkillReplayConditions)`로 입력을 한 번 깊은 복사·검증한다. 준비 객체의 입력은 외부에 노출하지 않는다. summary 기록 수준은 DamageLog=null, Combat.Trace=false, AutoBurst.TimelineLimit=0으로 정규화한다. 호출자는 최종 기록 수준을 입력 fingerprint에 포함한다. HP/스킬/무기/OL/택틱/고정 DEF 및 duration 수치는 바꾸지 않는다. 계정 스탯/싱크로 400 준비는 Backend 소유다.

`prepared.Run(CancellationToken cancellationToken = default)`은 새 전투 상태 및 seed를 지정하지 않은 per-run RNG를 생성한다. 동일 준비 객체의 여러 Run 호출을 Backend의 bounded worker가 병렬 실행할 수 있다. 전투 내부는 순차이며 프레임 순서를 유지한다. 취소는 프레임 경계에서 OperationCanceledException, 잘못된 입력/실행은 예외로 반환하며 부분 전투를 정상 0 표본으로 반환하지 않는다. JSON 직렬화·계정 조회·준비는 per-run 경로에 없다.

반환 `SkillRunSummary`: `ImplementationVersion="cpu-summary.1"`, `RulesVersion`, `TeamDamage`, `Members`(편성 순서), `FullBursts`(실제 진입 횟수), `ElapsedMilliseconds`(전투 실행, 준비 시간 제외). `SkillRunMemberSummary`: `CharacterId`, `Damage`, `Shots`, `Hits`, `CriticalHits`, `Reloads`, `BurstCasts`. Reloads는 기존 ReloadCompleted 내부 이벤트 수, Hits는 기존 평타 명중 수(직접 스킬/추가타는 포함하지 않음), CriticalHits는 기존 모든 피해 경로의 크리 수다. Backend MemberRunSummary에 같은 이름/단위로 매핑하며 run/attempt/index/실험/fingerprint/backend/phase는 Backend가 붙인다.

단일 히트 `HitCalculator.Calculate(HitContext, string roundingPolicy)`는 지정 정책 하나의 double 피해만 반환하며 기존 유효성/산술 순서를 유지한다. 기존 Compare는 audit 기준으로 남긴다. 실행 시 상세 damage log가 필요한 대상에는 기존 Calculation 근거를 보존한다.

GPU primitive 검사는 전체 전투 backend 승격 근거가 아니다. 동일 5인 full battle kernel/정확성/전송 포함 benchmark가 완료되지 않은 동안 GPU는 eligible=false/not_implemented, auto 선택 금지다. 강제 GPU 요청 거부와 CPU fallback 표기는 Backend가 담당한다.

이 선행 문서 커밋 시점에는 구현/측정 검증 중이다. 최종 결과는 아래에 별도 기록한다.
