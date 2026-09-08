# 계정 스펙 동기화 UI

P01의 연결·동기화·스펙 확인·수동 보완 화면이다. `src/upstream-theme.css`는 고정 nikke-calc 테마의 처음 62줄을 재사용했고, 화면·API adapter는 이 프로젝트에서 작성했다. 저작권 고지는 저장소의 THIRD_PARTY_NOTICES와 MIT 원문을 따른다.

저장소 루트에서 `npm run build` 후 `npm run dev`를 실행하면 C# API가 빌드된 UI를 함께 제공한다.

- 기본 URL: http://127.0.0.1:5180/
- 웹 개발 서버만 실행: 이 폴더에서 `npm run dev` → 5174, API 요청은 5180으로 proxy.
- 원본 Python 전투 계산기: 저장소 루트의 `npm run dev:reference` → 5173/nikke-calc/.

현재 화면은 새 C# 계정 snapshot을 표시한다. C# 전투 엔진은 아직 연결하지 않았다. 합성 테스트 서버에서는 검증용 데이터 배너를 표시한다.
