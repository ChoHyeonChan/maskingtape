# apps/api — FastAPI 백엔드

**담당: [@kitae13](https://github.com/kitae13) (부리뷰어)** · 상태: ✅ `/scan`·`/anonymize` core 연동 완료

웹 플레이그라운드·데스크톱 앱이 함께 쓰는 REST API. `packages/core`를 **래핑만** 한다 — 탐지 로직을 여기 재구현하지 않는다.

시작할 때:

1. 루트 [CLAUDE.md](../../CLAUDE.md) 필독
2. 의존성(fastapi, uvicorn 등) 추가 시 [SBOM.md](../../SBOM.md)에 한 줄씩 추가 — 라이선스 확인 필수

## 개발자 지도

API는 `packages/core`의 탐지·마스킹 엔진을 HTTP 계약으로 감싸는 얇은 계층이다. 탐지 규칙을
여기서 새로 만들지 않는다.

| 파일 | 역할 | 바꿀 때 같이 볼 것 |
|---|---|---|
| `maskingtape_api/schemas.py` | 공개 요청·응답 모델. 프론트/데스크톱이 의존하는 계약 | 이 README, `tests/test_openapi_contract.py` |
| `maskingtape_api/routers/pii.py` | `/scan`, `/anonymize` 라우터. 의존성 주입과 에러 응답만 담당 | `services/core_adapter.py`, `errors.py` |
| `maskingtape_api/services/core_adapter.py` | core `Pipeline` 호출과 API 응답 모델 변환 | core detection kind 변경, unknown kind 테스트 |
| `maskingtape_api/settings.py` | 환경변수 파싱과 런타임 기본값 | `tests/test_settings.py`, README 환경변수 표 |
| `maskingtape_api/body_limit.py` | JSON 파싱 전 요청 크기 제한 | 보안 요구사항 4번 |
| `maskingtape_api/rate_limit.py` | `/scan`·`/anonymize` 요청 제한 | 서버리스 한계 문서, rate limit 테스트 |
| `services/name_judge.py` | 웹 하이브리드 이름 판단기 Protocol | #545·#546 계약, OpenAI 연결 코드 |
| `services/openai_name_judge.py` | 웹 데모 하이브리드 모드의 유일한 상용 API 연결 지점 | 키 관리, 실패 코드, 테스트 fake |

계약 변경 순서:

1. `apps/api/README.md`에서 요청·응답 모양을 먼저 고친다.
2. `schemas.py`와 `tests/test_openapi_contract.py`를 맞춘다.
3. `core_adapter.py`와 라우터를 고친다.
4. 웹·데스크톱이 같은 계약을 쓰는지 확인한다.

원문 보호 규칙:

- 응답 `detections`에는 원문 PII 값을 싣지 않는다. 클라이언트는 자신이 가진 원문과 `start`/`end`로
  하이라이트한다.
- 에러 메시지와 로그에는 입력 `text`, 판단기 입력, 판단기 원문 응답을 넣지 않는다.
- core가 API enum에 아직 없는 새 `kind`를 내도 500을 내지 않고 문자열 그대로 통과시킨다. 그래도
  원칙적으로는 `DetectionKind`와 문서를 같은 PR에서 갱신한다.

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
$env:MASKINGTAPE_API_RATE_LIMIT_MAX_BUCKETS="10000"
$env:MASKINGTAPE_API_MAX_BODY_BYTES="1000000"
$env:MASKINGTAPE_API_HYBRID_MAX_TEXT_LENGTH="5000"
$env:MASKINGTAPE_API_HYBRID_RATE_LIMIT_REQUESTS="10"
$env:MASKINGTAPE_API_HYBRID_RATE_LIMIT_WINDOW_SECONDS="60"
# 앞단 프록시가 이 헤더를 반드시 덮어써 주는 배포에서만 설정한다(기본: 비어 있음)
# $env:MASKINGTAPE_API_TRUSTED_CLIENT_IP_HEADERS="x-vercel-forwarded-for,x-real-ip"
```

환경변수 한눈에 보기:

| 이름 | 기본값 | 역할 |
|---|---|---|
| `MASKINGTAPE_API_ENV` | `development` | 실행 환경. `production`이면 CORS 기본 허용 목록이 비어 있다 |
| `MASKINGTAPE_API_CORS_ORIGINS` | 로컬 웹 dev 서버 2개 | 쉼표로 구분한 CORS 허용 origin. 배포에서는 실제 웹 도메인만 둔다 |
| `MASKINGTAPE_API_RATE_LIMIT_REQUESTS` | `60` | 클라이언트 키별 요청 허용 횟수 |
| `MASKINGTAPE_API_RATE_LIMIT_WINDOW_SECONDS` | `60` | rate limit 시간창(초) |
| `MASKINGTAPE_API_RATE_LIMIT_MAX_BUCKETS` | `10000` | rate limit 버킷 최대 개수 |
| `MASKINGTAPE_API_MAX_BODY_BYTES` | `1000000` | JSON 파싱 전 요청 본문 최대 바이트 |
| `MASKINGTAPE_API_TRUSTED_CLIENT_IP_HEADERS` | Vercel에서만 자동 기본값 | 신뢰 프록시가 덮어쓴 IP 헤더만 지정 |
| `OPENAI_API_KEY` | 없음 | 웹 하이브리드 이름 판단기 연결 시에만 사용. 없으면 판단기를 만들지 않는다 |
| `MASKINGTAPE_API_OPENAI_MODEL` | `gpt-6-luna` | OpenAI 이름 판단기 모델 |
| `MASKINGTAPE_API_OPENAI_TIMEOUT_SECONDS` | `20` | OpenAI 이름 판단기 요청 제한 시간 |

`MASKINGTAPE_API_CORS_ORIGINS` is a comma-separated allowlist. Do not use `*`;
set the deployed web origin explicitly when the frontend domain is decided.
`MASKINGTAPE_API_RATE_LIMIT_REQUESTS` and `MASKINGTAPE_API_RATE_LIMIT_WINDOW_SECONDS`
control the in-memory per-client limit for `/scan` and `/anonymize`. Requests over
the window return 429 with `Retry-After`. This limiter is process-local: it is useful
for local/dev and low-traffic demo protection, but it is not shared across serverless
or horizontally scaled instances. `MASKINGTAPE_API_RATE_LIMIT_MAX_BUCKETS` caps the
number of tracked client buckets to avoid unbounded memory growth when many distinct
client keys are presented.
`MASKINGTAPE_API_MAX_BODY_BYTES` rejects oversized requests before JSON parsing.
The limit is enforced on the bytes actually received, not just on `Content-Length`,
so a chunked request that omits the header cannot bypass it.

`MASKINGTAPE_API_HYBRID_*`는 웹 하이브리드 모드 전용 보호 장치다. 하이브리드는 외부 이름
판단기를 호출할 수 있어 기본 `text` 상한(100,000자)보다 낮은 입력 상한(기본 5,000자)과 별도
요청 제한(기본 60초 10회)을 둔다. 이 제한을 넘으면 429가 아니라 규칙 결과로 폴백하고 응답에
`mode_used: "rule"`, `hybrid_failed: true`, `hybrid_failure_code`를 담는다.

`MASKINGTAPE_API_TRUSTED_CLIENT_IP_HEADERS` lists the headers the limiter may use to
identify a client (comma-separated). **It is empty by default and must stay empty unless
a proxy in front of the app always overwrites those headers** — otherwise a caller can
rotate the header value on every request and get a fresh bucket each time, which
disables rate limiting entirely. With no trusted header the limiter falls back to the
TCP peer address, which cannot be forged. On Vercel the platform overwrites incoming
forwarding headers to prevent IP spoofing, so the default turns on automatically there
(detected via the `VERCEL` runtime variable).

### Rate limit 운영 기록

- 현재 제한값: 클라이언트 키 1개당 60초에 60회. 61번째 `/scan` 또는 `/anonymize` 요청은
  429와 `Retry-After` 헤더로 거절된다. `/health`는 제한하지 않는다.
- 로컬 검증: `apps/api/tests/test_rate_limit.py`가 기본값 그대로 60회 허용·61회차 429,
  짧은 테스트 설정의 `/anonymize` 429, 버킷 최대 개수 10,000개 상한, 만료 버킷 제거를
  회귀 테스트한다.
- 서버리스 한계: limiter는 `create_app()`마다 생성되는 프로세스 메모리 객체다. 테스트로
  두 앱 인스턴스가 같은 클라이언트 요청을 공유 카운터로 보지 않는 것을 확인한다. 따라서
  Vercel serverless나 수평 확장 환경에서 요청이 여러 인스턴스로 분산되면 실효 한도는
  인스턴스 수만큼 느슨해질 수 있다.
- 선택(2026-09-13): 공모전 데모는 현행 인메모리 제한을 best-effort 보호로 유지한다.
  새 외부 스토어 의존성은 추가하지 않았으므로 `SBOM.md` 갱신은 없다. 트래픽이 커지거나
  실제 남용이 보이면 Vercel 플랫폼 보호를 먼저 켜고, 그 다음 외부 공유 스토어 기반
  limiter를 검토한다.

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
python -m pip install -e "packages/core[dev]"  # ruff>=0.16
python -m pip install -e "apps/api[dev]"
ruff check apps/api
python -m pytest apps/api -q
```

## 엔드포인트 개발 규칙

| 엔드포인트 | 목적 | 주의할 점 |
|---|---|---|
| `GET /health` | 로컬·배포 헬스체크 | rate limit 대상이 아니다 |
| `POST /scan` | 탐지 metadata만 반환 | `detections[].text`를 반환하지 않는다 |
| `POST /anonymize` | 비식별화된 텍스트와 사용한 탐지 metadata 반환 | `strategy`는 `mask`/`label`/`pseudonym` |

수동 확인:

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/scan \
  -H "Content-Type: application/json" \
  -d '{"text":"담당자 김민수, 연락처 010-1234-5678"}'
curl -X POST http://127.0.0.1:8000/anonymize \
  -H "Content-Type: application/json" \
  -d '{"text":"담당자 김민수, 연락처 010-1234-5678","strategy":"label"}'
```

응답 검토 기준:

- `/scan`은 탐지 목록만 돌려준다.
- `/anonymize`는 비식별화된 `text`를 돌려준다.
- 두 응답의 `detections`는 `kind`, `start`, `end`, `confidence`, `detector`만 포함한다.
- 실패 응답은 공유 에러 모양(`code`, `message`, `details`)을 따른다.

## API 계약 (v1 — 프론트·데스크톱은 이 스키마로 목업 개발 시작 가능)

공통 제약:

- 요청 `text`는 1자 이상, 100,000자 이하
- 요청 `mode`는 `rule`(기본) 또는 `hybrid`
- 서버는 입력 원문을 저장하지 않는다
- 에러 응답은 `{ "code": "...", "message": "...", "details": { ... } }` 형식을 따른다
- 성공 응답은 실제 사용 모드 `mode_used`와 하이브리드 폴백 여부(`hybrid_failed`,
  `hybrid_failure_code`)를 함께 돌려준다

`POST /scan` — 탐지 리포트만

`/scan`은 기본적으로 `packages/core`의 규칙 기반 `Pipeline.scan()`을 호출한다. `mode: "hybrid"`이면
규칙 탐지 결과를 먼저 `LabelAnonymizer`로 가린 뒤 이름 판단기(`NameJudge`)에 보내고, 판단기가
돌려준 이름을 원문 위치에서 찾아 `kind: "name"` 탐지로 합친다. 판단기가 없거나 실패하면 HTTP 200으로
규칙 결과를 돌려주되 `mode_used: "rule"`과 실패 코드를 표시한다.
FastAPI 라우터는 core를 직접 호출하지 않고 `maskingtape_api.services.core_adapter`를 통해서만 연결한다.

```json
// 요청
{ "text": "주민번호 800101-1234560 문의주세요", "mode": "rule" }
// 응답 — detections는 원문 조각(text)을 제외한 span metadata만 반환
{
  "mode_used": "rule",
  "hybrid_failed": false,
  "hybrid_failure_code": null,
  "detections": [
    { "kind": "rrn", "start": 5, "end": 19, "confidence": 1.0, "detector": "RRNDetector" }
  ]
}
```

`POST /anonymize` — 비식별화 결과

`/anonymize`도 같은 `mode` 계약을 쓴다. 하이브리드 성공 시 판단기가 더 찾은 이름까지 함께
비식별화하고, 실패 시 규칙 결과만 비식별화한다. `strategy`는 별표 마스킹(`mask`), 종류 라벨
치환(`label`), 가명 치환(`pseudonym`)을 지원한다.

```json
// 요청 — strategy: "mask"(기본), "label", "pseudonym" / mode: "rule"(기본), "hybrid"
{ "text": "주민번호 800101-1234560 문의주세요", "strategy": "mask", "mode": "rule" }
// 응답
{
  "text": "주민번호 ************** 문의주세요",
  "mode_used": "rule",
  "hybrid_failed": false,
  "hybrid_failure_code": null,
  "detections": [ /* 위와 동일 */ ]
}
```

- `kind` 값: `rrn`, `passport`, `driver_license`, `phone`, `email`, `name`, `address`, `card`, `account`, `biz_reg`, `birth_date` (11종, core에 전부 구현됨)
- `start`/`end`는 파이썬 슬라이스 규약 (`text[start:end]` == 탐지된 원문)
- `detections`는 원문 PII 값을 담는 `text` 필드를 반환하지 않는다. 클라이언트 하이라이트는 자신이 이미 가진 입력 원문과 `start`/`end`로 처리한다.
- 계약 변경은 팀장 승인 후 이 문서부터 갱신한다

### 이름 판단기 (웹 하이브리드 모드 준비, #545·#546)

`mode: "hybrid"` 요청에서만 이름 판단기를 쓴다. 기본값은 계속 `rule`이라 OpenAI 키가 없어도
기존 API와 테스트는 규칙 전용으로 동작한다.

- **약속**: `maskingtape_api/services/name_judge.py`의 `NameJudge.find_names(masked_text) -> list[str]`. 입력은 규칙으로 먼저 가린 글(`LabelAnonymizer` 결과)이다. 실패는 `NameJudgeError(code)`로 올리고, 메시지와 `code`에 원문·가린 글·모델 응답을 넣지 않는다.
- **가져다 쓸 import**:
  ```python
  from maskingtape_api.services.name_judge import NameJudge, NameJudgeError
  from maskingtape_api.services.openai_name_judge import openai_name_judge_from_env
  ```
- **성공 경로**: 규칙 탐지 결과를 먼저 `LabelAnonymizer`로 가린 뒤 판단기에 보내고, 판단기가 돌려준
  이름을 원문 위치에서 찾아 `kind: "name"` 탐지로 합친다. 겹침 처리는 core의 `resolve_overlaps`를 쓴다.
- **API 폴백**: 판단기가 없거나 실패하면 규칙 결과를 돌려주고 `mode_used: "rule"`,
  `hybrid_failed: true`, `hybrid_failure_code`를 채운다. 판단기 실패 코드는 `NameJudgeError.code`를
  그대로 쓴다. `OPENAI_API_KEY`가 없어 판단기를 만들 수 없으면 `name_judge_unavailable`을 쓴다.
- **테스트 원칙**: API 테스트는 OpenAI를 부르지 않는다. `find_names()`만 가진 fake 판단기와
  `NameJudgeError`를 던지는 fake로 규칙/하이브리드 성공/하이브리드 실패를 고정한다.
- **구현**: `services/openai_name_judge.py`의 `OpenAINameJudge`. 제품 코드에서 상용 AI API를 부르는 유일한 곳이다([CLAUDE.md](../../CLAUDE.md) §2 3번의 예외).
  - OpenAI Responses API에 가린 글만 보낸다. `store: false`, 추론 끔(`reasoning.effort: "none"`), 온도 0, JSON 스키마(strict) `{"names": [...]}`로 받는다.
  - 받은 이름 중 보낸 글에 그대로 있는 것만 돌려준다(없는 이름은 환각으로 보고 버린다).
  - 리다이렉트를 따라가지 않는다(Authorization 헤더의 키가 다른 주소로 가지 않게).
  - 상한: 입력 10,000자, 출력 512토큰, 응답 64KB.
- **환경변수**

  | 이름 | 기본값 | 설명 |
  |---|---|---|
  | `OPENAI_API_KEY` | 없음 | 없으면 판단기를 만들지 않는다(`openai_name_judge_from_env()`가 `None`). 배포에서는 Vercel Production 환경변수(Secret)에만 둔다 |
  | `MASKINGTAPE_API_OPENAI_MODEL` | `gpt-6-luna` | 2026-09-30 OpenAI 가격표 기준 가장 싼 현행 모델 |
  | `MASKINGTAPE_API_OPENAI_TIMEOUT_SECONDS` | `20` | 요청 시간 제한(초) |
  | `MASKINGTAPE_API_HYBRID_MAX_TEXT_LENGTH` | `5000` | 하이브리드 모드 입력 길이 상한. 초과 시 규칙 결과로 폴백하고 `input_too_long` |
  | `MASKINGTAPE_API_HYBRID_RATE_LIMIT_REQUESTS` | `10` | 하이브리드 모드 전용 인메모리 요청 제한 |
  | `MASKINGTAPE_API_HYBRID_RATE_LIMIT_WINDOW_SECONDS` | `60` | 하이브리드 모드 전용 요청 제한 시간창 |

- **실패 코드**: `name_judge_unavailable` `input_too_long` `timeout` `network` `auth` `rate_limited` `spend_limit` `redirect` `upstream` `http_error` `response_too_large` `bad_response` `incomplete` `refused` `empty_output` `bad_schema`
- 이 앱은 `.env` 파일을 읽지 않는다. 로컬에서 시험할 때는 키를 환경변수로 둔다. 테스트는 가짜 응답으로 돌아 OpenAI를 부르지 않는다.

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
5. **호출 빈도 제한(rate limit)**을 둔다. 공개 URL은 남용된다. 현재 API는 `/scan`·`/anonymize`에 IP별 인메모리 제한을 적용하며 초과 시 429로 거절한다. 하이브리드 모드는 별도 저한도 인메모리 제한을 두고, 초과 시 규칙 결과로 폴백한다. 단, Vercel serverless처럼 여러 인스턴스가 생길 수 있는 환경에서는 카운터가 공유되지 않아 배포 등급의 강한 제한으로 보지 않는다. **결정(2026-08-17, 재확인 2026-09-13): 공모전 데모는 현행 인메모리 제한을 best-effort 보호로 유지하고 배포를 진행한다.** 남용/비용/DoS 위험이 커지면 Vercel 플랫폼 보호 또는 외부 공유 스토어 기반 limiter로 전환한다. OpenAI 비용의 최종 안전장치는 OpenAI 프로젝트 월 사용 한도다(#546).
6. **CORS를 우리 프론트 도메인으로 제한**한다. `*` 금지.
7. **HTTPS만 허용**한다.

### 자기호스팅 하드닝

- API는 `x-forwarded-for`를 클라이언트 키로 신뢰하지 않는다. Vercel 배포에서는 `x-vercel-forwarded-for`, 일반 리버스 프록시에서는 프록시가 덮어쓴 `x-real-ip`만 사용하고, 둘 다 없으면 ASGI `request.client.host`를 쓴다.
- nginx 같은 리버스 프록시를 앞에 둘 때는 외부에서 온 `X-Forwarded-For`/`X-Real-IP`를 그대로 전달하지 말고, 프록시가 검증한 값으로 덮어쓴다.
- 요청 바디는 앱의 `MASKINGTAPE_API_MAX_BODY_BYTES`와 프록시의 `client_max_body_size`를 함께 둔다. 예: `client_max_body_size 1m;`

### UI 쪽 요구사항 (프론트와 함께)

- 화면에 **"데모용입니다. 실제 개인정보를 입력하지 마세요. 실사용은 로컬 설치를 권장합니다."** 경고를 명확히 표시한다.
- "입력 내용은 저장되지 않습니다"를 함께 안내한다(그리고 실제로 그래야 한다 — 위 2번).

### 배포판의 기능 제약

- **core의 로컬 LLM 이름 탐지(`--llm`)는 배포판에서 제외한다.** 로컬 Ollama + 7B 모델이 필요해 서버리스 환경에 올릴 수 없다. 대신 웹 데모 백엔드의 `mode: "hybrid"`에서만 OpenAI 이름 판단기를 선택적으로 쓴다. 키가 없거나 실패하면 규칙 기반 결과로 폴백한다.
- 이 제약은 오히려 우리 메시지와 맞다: **"진짜 개인정보는 로컬에서 처리하세요."**

### 미정 (구현 시 실제로 확인할 것)

- 호스팅: Vercel 단일 프로젝트 기준 설정을 둔다(정적 프론트 + Python FastAPI 함수). 배포 절차와 검증은 [docs/deployment-vercel.md](../../docs/deployment-vercel.md)를 따른다. **실제 URL 검증 전에는 완료로 보지 않는다.**
- 대안: Render·Fly.io 등 일반 컨테이너 호스팅(제약이 적음).
