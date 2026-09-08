# P00 웹 실행 진입점

현재 웹은 `sources.lock.json`으로 고정한 Moris-kr/nikke-calc의 `site/`를 원본 위치에서 실행한다.
`npm run dev`는 `scripts/web.ps1`을 통해 이 화면을 연다. UI 소스를 이 폴더로 이식하고
새 C# API와 연결하는 작업은 P01~P05에서 수행한다.

이 단계의 웹 계산은 upstream Python/Pyodide 참조 엔진이다. 새로운 정밀 엔진의 결과가 아니다.
로컬 실행은 upstream 운영자의 프로필 프록시·공유·접속자 수 서비스를 사용하지 않는다.

개발 URL: http://127.0.0.1:5173/nikke-calc/
