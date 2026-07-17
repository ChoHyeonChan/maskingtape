# apps/api — FastAPI 백엔드

**담당: 풀스택 (부리뷰어)** · 상태: ⏳ 스켈레톤 머지 후 시작

웹 플레이그라운드·데스크톱 앱이 함께 쓰는 REST API. `packages/core`를 **래핑만** 한다 — 탐지 로직을 여기 재구현하지 않는다.

시작할 때:

1. 루트 [CLAUDE.md](../../CLAUDE.md) 필독
2. 의존성(fastapi, uvicorn 등) 추가 시 [SBOM.md](../../SBOM.md)에 한 줄씩 추가 — 라이선스 확인 필수
3. 계획 엔드포인트: `POST /scan`(탐지 리포트), `POST /anonymize`(마스킹 결과) — 응답 스키마는 core의 `Detection` 타입 기준으로 프론트와 합의
