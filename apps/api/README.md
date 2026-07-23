# apps/api — FastAPI 백엔드

**담당: 기태 ([@kitae13](https://github.com/kitae13), 부리뷰어)** · 상태: ✅ 시작 가능 (스켈레톤 머지 완료)

웹 플레이그라운드·데스크톱 앱이 함께 쓰는 REST API. `packages/core`를 **래핑만** 한다 — 탐지 로직을 여기 재구현하지 않는다.

시작할 때:

1. 루트 [CLAUDE.md](../../CLAUDE.md) 필독
2. 의존성(fastapi, uvicorn 등) 추가 시 [SBOM.md](../../SBOM.md)에 한 줄씩 추가 — 라이선스 확인 필수

## 로컬 실행

요구사항:

- Python 3.10 이상

```bash
cd apps/api
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ..\..\packages\core
python -m pip install -e ".[dev]"
```

API 서버:

```bash
python -m uvicorn maskingtape_api.main:app --reload --host 127.0.0.1 --port 8000
```

헬스체크:

```bash
curl http://127.0.0.1:8000/health
```

예상 응답:

```json
{ "status": "ok" }
```

테스트:

```bash
python -m pytest
```

## API 계약 (v1 — 프론트·데스크톱은 이 스키마로 목업 개발 시작 가능)

`POST /scan` — 탐지 리포트만

```json
// 요청
{ "text": "주민번호 800101-1234560 문의주세요" }
// 응답 — detections는 core의 Detection 타입 그대로
{
  "detections": [
    { "kind": "rrn", "start": 5, "end": 19, "text": "800101-1234560",
      "confidence": 1.0, "detector": "RRNDetector" }
  ]
}
```

`POST /anonymize` — 비식별화 결과

```json
// 요청 — strategy: "mask"(기본) 또는 "label"
{ "text": "주민번호 800101-1234560 문의주세요", "strategy": "mask" }
// 응답
{ "text": "주민번호 ************** 문의주세요", "detections": [ /* 위와 동일 */ ] }
```

- `kind` 값: `rrn`, `phone`, `email` (추가 예정: `name`, `address`)
- `start`/`end`는 파이썬 슬라이스 규약 (`text[start:end]` == 탐지된 원문)
- 계약 변경은 팀장 승인 후 이 문서부터 갱신한다
