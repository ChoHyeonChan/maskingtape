# apps/api — FastAPI 백엔드

**담당: 기태 ([@kitae13](https://github.com/kitae13), 부리뷰어)** · 상태: ✅ `/scan`·`/anonymize` core 연동 완료

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
# Windows: .venv\Scripts\activate / macOS·Linux: source .venv/bin/activate
python -m pip install -e ../../packages/core
python -m pip install -e ".[dev]"
```

API 서버:

```bash
python -m uvicorn maskingtape_api.main:app --reload --host 127.0.0.1 --port 8000
```

Development environment variables:

```powershell
$env:MASKINGTAPE_API_ENV="development"
$env:MASKINGTAPE_API_CORS_ORIGINS="http://localhost:5173,http://127.0.0.1:5173"
$env:MASKINGTAPE_API_RATE_LIMIT_REQUESTS="60"
$env:MASKINGTAPE_API_RATE_LIMIT_WINDOW_SECONDS="60"
```

`MASKINGTAPE_API_CORS_ORIGINS` is a comma-separated allowlist. Do not use `*`;
set the deployed web origin explicitly when the frontend domain is decided.
`MASKINGTAPE_API_RATE_LIMIT_REQUESTS` and `MASKINGTAPE_API_RATE_LIMIT_WINDOW_SECONDS`
control the in-memory per-client limit for `/scan` and `/anonymize`. Requests over
the window return 429 with `Retry-After`.

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

CI에서 루트 기준 실행:

```bash
python -m pip install -e packages/core
python -m pip install -e "apps/api[dev]"
python -m pytest apps/api -q
```

## API 계약 (v1 — 프론트·데스크톱은 이 스키마로 목업 개발 시작 가능)

공통 제약:

- 요청 `text`는 1자 이상, 100,000자 이하
- 서버는 입력 원문을 저장하지 않는다
- 에러 응답은 `{ "code": "...", "message": "...", "details": { ... } }` 형식을 따른다

`POST /scan` — 탐지 리포트만

현재 `/scan`은 `packages/core`의 규칙 기반 `Pipeline.scan()`을 호출한다. LLM 탐지는 사용하지 않는다.
FastAPI 라우터는 core를 직접 호출하지 않고 `maskingtape_api.services.core_adapter`를 통해서만 연결한다.

```json
// 요청
{ "text": "주민번호 800101-1234560 문의주세요" }
// 응답 — detections는 원문 조각(text)을 제외한 span metadata만 반환
{
  "detections": [
    { "kind": "rrn", "start": 5, "end": 19, "confidence": 1.0, "detector": "RRNDetector" }
  ]
}
```

`POST /anonymize` — 비식별화 결과

현재 `/anonymize`는 `packages/core`의 규칙 기반 `Pipeline.anonymize()`를 호출한다. `strategy`는 별표 마스킹(`mask`)과 종류 라벨 치환(`label`)을 지원한다.

```json
// 요청 — strategy: "mask"(기본) 또는 "label"
{ "text": "주민번호 800101-1234560 문의주세요", "strategy": "mask" }
// 응답
{ "text": "주민번호 ************** 문의주세요", "detections": [ /* 위와 동일 */ ] }
```

- `kind` 값: `rrn`, `passport`, `phone`, `email`, `name`, `address`, `card`, `account`, `biz_reg` (core에 전부 구현됨)
- `start`/`end`는 파이썬 슬라이스 규약 (`text[start:end]` == 탐지된 원문)
- `detections`는 원문 PII 값을 담는 `text` 필드를 반환하지 않는다. 클라이언트 하이라이트는 자신이 이미 가진 입력 원문과 `start`/`end`로 처리한다.
- 계약 변경은 팀장 승인 후 이 문서부터 갱신한다

## 🔒 배포 시 보안 요구사항 (필수 — 구현할 때부터 지킬 것)

**결정(2026-07-23): 웹 데모를 API 서버까지 포함해 배포한다.** 그러면 이 API가 **남의 개인정보를 실제로 받는 서버**가 된다. 우리 제품은 개인정보 보호 도구라, 여기서 정보가 새면 제품 자체가 부정된다. 아래는 선택이 아니라 요구사항이다.

### 반드시 지킬 것

1. **입력 텍스트를 로그에 남기지 않는다.** 접근 로그·에러 로그·트레이스백 어디에도 `text` 본문이 들어가면 안 된다. 예외 발생 시에도 길이·종류만 기록한다.
   ```python
   # ✗ logger.error(f"처리 실패: {text}")
   # ✓ logger.error(f"처리 실패: 입력 {len(text)}자")
   ```
2. **저장하지 않는다(stateless).** 요청 내용을 DB·파일·캐시에 쓰지 않는다. 처리 후 메모리에서 끝난다.
3. **응답에 원문을 불필요하게 담지 않는다.** `/anonymize`는 비식별화된 텍스트를 돌려주는 게 목적이다. 디버그 필드로 원문을 반환하지 않고, `/scan`·`/anonymize`의 `detections`에도 원문 PII 조각을 넣지 않는다.
4. **입력 크기 상한**을 둔다(예: 100KB). 초과 시 413으로 거절 — 비용·자원 보호.
5. **호출 빈도 제한(rate limit)**을 둔다. 공개 URL은 남용된다. 현재 API는 `/scan`·`/anonymize`에 IP별 인메모리 제한을 적용하며 초과 시 429로 거절한다. 다중 인스턴스 배포에서는 플랫폼/WAF 제한도 함께 둔다.
6. **CORS를 우리 프론트 도메인으로 제한**한다. `*` 금지.
7. **HTTPS만 허용**한다.

### UI 쪽 요구사항 (프론트와 함께)

- 화면에 **"데모용입니다. 실제 개인정보를 입력하지 마세요. 실사용은 로컬 설치를 권장합니다."** 경고를 명확히 표시한다.
- "입력 내용은 저장되지 않습니다"를 함께 안내한다(그리고 실제로 그래야 한다 — 위 2번).

### 배포판의 기능 제약

- **LLM 이름 탐지(`--llm`)는 배포판에서 제외한다.** 로컬 Ollama + 7B 모델이 필요해 서버리스 환경에 올릴 수 없다. 배포판은 **규칙 기반 탐지만** 제공하고, "문맥 판단 LLM 기능은 로컬 설치 시 사용 가능"이라고 안내한다.
- 이 제약은 오히려 우리 메시지와 맞다: **"진짜 개인정보는 로컬에서 처리하세요."**

### 미정 (구현 시 실제로 확인할 것)

- 호스팅: Vercel 유력(정적 프론트 + Python 서버리스 함수). **단, Vercel의 Python 런타임에서 `packages/core`를 함께 배포하는 방법은 문서를 확인하고 실제로 배포해봐야 한다 — 기억이나 추측으로 진행하지 말 것.**
- 대안: Render·Fly.io 등 일반 컨테이너 호스팅(제약이 적음).
