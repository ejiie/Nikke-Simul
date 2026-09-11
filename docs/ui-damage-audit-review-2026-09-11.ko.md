# Director 검수: b6c5064 — 보완 수용 및 통합 완료

## 최종 재검수 (2026-09-12)

보완 커밋 `b6c50649e757812ebb29ffe5ee5773576b2e6312`를 Director에 fast-forward 통합했다. 아래 최초 검수에서 지적한 장탄 단위 추정 및 누락 판정의 false 변환은 해소됐다. 근거 없는 정수 장탄 값은 단위 미확인/원값으로, 누락된 hit 판정은 미기록으로 유지한다. 이는 UI 표시 보완 수용이며 엔진 전체나 실제 게임 피해의 일치 검증 완료를 뜻하지 않는다.

- 단위 검사 19개 및 실제 저장 로그 134행 대조 통과: `artifacts/director/damage-audit-review-b6c5064/unit-summary.json`.
- 기존 간소화 버스트 UI와의 통합 계약 검사 26개 통과: `artifacts/director/audit-integrated-b6c5064/ui-ec77a9bf-e2b4-4606-b8e9-c792d07985fd/summary.json`.
- Director에서 브라우저 재검증 통과: `artifacts/ui/damage-audit/run-a57b986cac6c/summary.json`. 저장 로그 재생 1개, 합성 계산 경계 3개, 누락/false 판정 경계 4개, 격리된 실제 API 1개 시나리오. 1500/850/500px에서 검사한 카드·계산 단계·최종 피해·단위 표시 및 가로 넘침/브라우저 예외 검사에 실패 없음.
- 실제 API 검사는 별도 데이터 복사본을 사용했고 원본 보존 검사 `sourceUnchanged=true`. 기존 사용자 서버 데이터는 테스트 대상으로 변경하지 않았다.
- 통합 직전/직후 기존 미커밋 추적 파일 12개의 SHA256이 동일함을 확인했다. 기존 미추적 `package-lock.json`도 보존했다.

현재 5181 서버에서 새 adapter 제공을 GET으로 확인했다. 브라우저 강력 새로고침으로 반영 가능하며 배포용 `.exe`는 이번에 재빌드하지 않았다. 로그에 없는 장탄 단위/하위 함수의 스킬 슬롯은 여전히 미확인으로 표시하며, 엔진/API 메타데이터 보강은 별도 범위다.

## 최초 검수 기록: bced746 — 당시 조건부 미수용

제출 커밋: `bced746c8967f983bec6b93e0685c36cd7f5ee2a`. 피해 표시·단위·산식 수정 7개 파일이며 Director의 미커밋 버스트 UI/문서와 경로 중복은 없다. 아직 Director에 병합하지 않았다.

직접 실행: UI 작업공간의 `tests/ui/damage_audit.test.mjs`에 Director 실제 저장 결과 `artifacts/director/live-a751d113203748f5886aa7fabaf88679/ui-response.json`을 입력. 16개 검사 통과, 실제 134행 대조 통과. 증거 `artifacts/director/damage-audit-review-bced746/unit-summary.json`. 이는 단위/저장 로그 검사이며 이번 Director 검수에서 브라우저 검사를 재실행한 것은 아니다.

## 추가 재현 1: 장탄 단위의 정수 추정

UI 커밋의 `describeBuffSnapshot({effect:{type:14,value:1,stacks:1,basis:'native_recipient'}},60)` 결과는 `unit=ammoCount`, `valueText=+1발`이다. 단위 근거 대신 Number.isInteger(value)를 사용한다. 엔진의 Percent 10000은 Rate 1로 저장되므로 해당 값만으로 Integer 1발과 Percent 100%를 구분할 수 없다. 현재 카탈로그에 충돌 값이 없다는 검사만으로 저장 로그 전체에 적용할 계약이 되지는 않는다. 이 재현은 명시적 합성 경계이며 현재 사용자 편성의 실제 잘못된 100% 효과를 발견했다는 뜻은 아니다.

필요 조치: 저장된 함수 정의/값 유형 또는 근거가 고정된 해당 함수 매핑으로 단위를 확인한다. 그 근거가 없으면 '단위 미확인 · 원값 1'로 표시하고 발/% 중 하나를 확정하지 않는다. 엔진/API 계약 변경은 이번 범위 밖이다. Integer/Percent 구분과 근거 없는 정수·0·음수, 실제 누아르 +4/비율 효과를 테스트한다.

## 추가 재현 2: 누락 판정의 false 변환

`buildDamageBreakdown({hit:{},damage:10})` 결과에서 모든 bonuses.active=false, bonusSum=0, charge.applied=false다. 렌더러가 가산 묶음 1, 각 보너스 미적용, '풀차지 아님 → 1'로 표시한다. `classifyBuffForHit({typeId:51},{},null)`도 '크리티컬 아님'으로 제외한다. 필드가 없다는 사실은 false의 근거가 아니다.

필요 조치: 판정 필드는 명시적 true/false/미기록을 분리한다. 미기록은 null/미확인, 그에 의존한 합계와 효과 반영 여부도 미확인으로 유지한다. unknown basis/value/필수 hit 입력의 부재 때문에 증명할 수 없는 반영 판정은 확정하지 않는다. hit 자체 누락뿐 아니라 빈 hit, 개별 필드 누락/null, 명시적 false와 실제 정상 로그를 회귀 테스트한다.

두 조치는 원래 인계의 '추정 단위 금지'와 '누락값을 정상 0/1로 위장하지 않기'에 해당한다. 단위 테스트가 통과해도 위 경계가 해결될 때까지 전체 수용으로 표시하지 않는다. 기존 UI 워커에게 동일 소유권 범위의 후속 수정·검증·커밋을 요청한다. Director 기존 변경, 사용자 원본 데이터, 5181 서버는 보존한다.
