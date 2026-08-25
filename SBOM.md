# SBOM (소프트웨어 자재명세서)

> **규칙: 라이브러리·프레임워크·AI 모델을 하나라도 추가하면, 추가한 그 PR에서 이 표에 한 줄을 같이 넣는다.**
> 허용 라이선스: MIT, Apache-2.0, BSD, ISC · 금지: GPL·AGPL·SSPL·비상업 전용 (팀 방침 — Apache-2.0 통일 유지)
> 이 표는 대회 결과보고서 **붙임1(SBOM)** 공식 양식과 같은 컬럼이다 — 제출 때 그대로 옮긴다. 심사에 라이선스 검증 단계가 별도로 있다.

| 번호 | 라이브러리명 | 버전 | 라이선스 | 공식 저장소 URL(GitHub 등) | 사용 목적 및 주요 기능 |
|---|---|---|---|---|---|
| 1 | mcp (MCP Python SDK) | >=1.10,<2 | MIT | https://github.com/modelcontextprotocol/python-sdk | MCP 서버 프레임워크 — AI 에이전트에 비식별화 도구 노출 |
| 2 | pytest | >=8 | MIT | https://github.com/pytest-dev/pytest | (개발 도구) 코어 엔진 테스트 실행 |
| 3 | ruff | >=0.4 | MIT | https://github.com/astral-sh/ruff | (개발 도구) 파이썬 린트·코드 스타일 검사 |
| 4 | desktop_drop | ^0.7.1 | Apache-2.0 | https://github.com/MixinNetwork/flutter-plugins | 데스크톱 앱 — OS 파일 드래그&드롭 수신 (Flutter 플러그인) |
| 5 | react / react-dom | 19.2.7 | MIT | https://github.com/facebook/react | 웹 플레이그라운드 UI 렌더링 |
| 6 | vite | 8.1.5 | MIT | https://github.com/vitejs/vite | (개발 도구) 웹 플레이그라운드 빌드·개발 서버 |
| 7 | @vitejs/plugin-react | 6.0.3 | MIT | https://github.com/vitejs/vite-plugin-react | (개발 도구) Vite에서 React JSX 처리 |
| 8 | typescript | 7.0.2 | Apache-2.0 | https://github.com/microsoft/TypeScript | (개발 도구) 웹 플레이그라운드 타입 검사 |
| 9 | vitest | 4.1.10 | MIT | https://github.com/vitest-dev/vitest | (개발 도구) 웹 플레이그라운드 테스트 실행 |
| 10 | @testing-library/react | 16.3.2 | MIT | https://github.com/testing-library/react-testing-library | (개발 도구) 컴포넌트 테스트 |
| 11 | @testing-library/jest-dom | 6.9.1 | MIT | https://github.com/testing-library/jest-dom | (개발 도구) 테스트용 DOM 매처 |
| 12 | jsdom | 29.1.1 | MIT | https://github.com/jsdom/jsdom | (개발 도구) 테스트용 가상 브라우저(DOM) 환경 |
| 13 | @types/node, @types/react, @types/react-dom | 26.1.1 / 19.2.17 / 19.2.3 | MIT | https://github.com/DefinitelyTyped/DefinitelyTyped | (개발 도구) TypeScript 타입 선언 |
| 14 | cp949_codec | ^1.0.2 | BSD-3-Clause | https://github.com/letyletylety/cp949_codec | 데스크톱 앱 — CP949(EUC-KR) 텍스트 파일 읽기 폴백 (순수 Dart) |
| 15 | file_selector | ^1.1.0 | BSD-3-Clause | https://github.com/flutter/packages/tree/main/packages/file_selector/file_selector | 데스크톱 앱 — OS 파일 선택 대화상자 (Flutter 공식 플러그인) |
| 16 | Ollama | 0.32.1 | MIT | https://github.com/ollama/ollama | 로컬 LLM 실행 런타임 — 코어 `--llm` 이름 탐지에 사용 (**선택 의존성**: 없어도 규칙 탐지는 동작) |
| 17 | Qwen2.5-7B-Instruct (AI 모델) | qwen2.5:7b | Apache-2.0 | https://github.com/QwenLM/Qwen2.5 | 이름(인명) 문맥 판단용 오픈웨이트 모델 — **로컬 실행 전용, 외부 API 호출 없음** |
| 18 | FastAPI | >=0.116,<1 | MIT | https://github.com/fastapi/fastapi | API 서버 프레임워크 — 웹·데스크톱 공용 REST 엔드포인트 제공 |
| 19 | Uvicorn | >=0.35,<1 | BSD-3-Clause | https://github.com/encode/uvicorn | API 서버 실행용 ASGI 서버 |
| 20 | Pydantic | >=2.9,<3 | MIT | https://github.com/pydantic/pydantic | API 요청·응답 데이터 검증 및 OpenAPI 스키마 생성 |
| 21 | HTTPX2 | >=2,<3 | BSD-3-Clause | https://github.com/pydantic/httpx2 | (개발 도구) FastAPI/Starlette TestClient 기반 API 테스트 실행 |
| 22 | pdfjs-dist | ^6.2.108 | Apache-2.0 | https://github.com/mozilla/pdf.js | 웹 플레이그라운드 — 브라우저(클라이언트) 안에서 PDF 텍스트 추출, 파일을 서버로 보내지 않기 위함 |

※ **AI 모델 주의**: Qwen2.5는 **3B·72B만 비상업 제한(Qwen Research License)**이고 나머지(0.5B/1.5B/**7B**/14B/32B)가 Apache-2.0이다. OSI 인증 라이선스 요건 때문에 **7B를 쓴다 — 3B로 바꾸지 말 것.**
※ 위 16·17번은 결과보고서 **붙임2(AI 모델 활용 및 라이선스 기술 명세서)**에도 반영한다(유형1 '외부 모델 그대로' + 기반 모델명·라이선스 기재).

## 부록: 전이 의존성 (직접 추가하지 않았으나 함께 설치되는 것)

위 표는 우리가 **직접 선언한** 의존성이다. 그중 `mcp`가 HTTP 통신을 위해 끌어오는 하위 의존성은 아래와 같다(설치본 메타데이터 실측, 2026-08-25 기준).

| 패키지 | 버전 | 라이선스 | 경로 |
|---|---|---|---|
| httpx | 0.28.1 | BSD-3-Clause | mcp → httpx |
| httpcore | 1.0.9 | BSD-3-Clause | mcp → httpx → httpcore |
| anyio | 4.14.2 | MIT | mcp → httpx → anyio |
| h11 | 0.16.0 | MIT | mcp → httpx → httpcore → h11 |
| idna | 3.18 | BSD-3-Clause | mcp → httpx → idna |
| **certifi** | **2026.6.17** | **MPL-2.0** | mcp → httpx → certifi |

**certifi(MPL-2.0)에 대한 판단** — 팀 허용목록(MIT/Apache-2.0/BSD/ISC) 밖이라 명시해 둔다.

- **직접 의존이 아니다.** 우리 코드는 certifi를 import하지 않는다. HTTP 클라이언트(httpx)가 TLS 루트 인증서 번들로 쓰는 전이 의존이다.
- **MPL-2.0은 OSI 승인 라이선스**이며 **파일 단위(file-level) 카피레프트**다. 원본 파일을 수정하지 않고 그대로 재배포하는 한, 우리 코드(Apache-2.0)에 라이선스 전파 의무가 발생하지 않는다(MPL-2.0 §3.3 — Larger Work를 다른 라이선스로 배포 가능).
- **우리는 certifi를 수정하지 않는다.** 수정 없이 pip 의존성으로 설치될 뿐이므로 소스 공개 의무(MPL-2.0 §3.2)의 대상이 아니다.
- 결론: **재배포 형태상 의무 없음.** 다만 전체 의존성 트리를 엄격 스캔하는 검증에서는 노출되므로 위와 같이 근거를 남긴다.
