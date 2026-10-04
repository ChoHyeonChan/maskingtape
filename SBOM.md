# SBOM (소프트웨어 자재명세서)

> **규칙: 라이브러리·프레임워크·AI 모델을 하나라도 추가하면, 추가한 그 PR에서 이 표에 한 줄을 같이 넣는다.**
> 허용 라이선스: MIT, Apache-2.0, BSD, ISC · 금지: GPL·AGPL·SSPL·비상업 전용 (팀 방침 — Apache-2.0 통일 유지)
> 이 표는 대회 결과보고서 **붙임1(SBOM)** 공식 양식과 같은 컬럼이다 — 제출 때 그대로 옮긴다. 심사에 라이선스 검증 단계가 별도로 있다.
> 전이 의존성(부록 A)은 `python scripts/sbom_transitive.py --write`로 다시 만든다. lock 파일(`apps/web/package-lock.json`, `uv.lock`, `apps/desktop/pubspec.lock`)이 바뀌면 팀장이 갱신한다.

| 번호 | 라이브러리명 | 버전 | 라이선스 | 공식 저장소 URL(GitHub 등) | 사용 목적 및 주요 기능 |
|---|---|---|---|---|---|
| 1 | mcp (MCP Python SDK) | >=1.10,<2 | MIT | https://github.com/modelcontextprotocol/python-sdk | MCP 서버 프레임워크 — AI 에이전트에 비식별화 도구 노출 |
| 2 | pytest | >=8 | MIT | https://github.com/pytest-dev/pytest | (개발 도구) 코어 엔진 테스트 실행 |
| 3 | ruff | >=0.16 | MIT | https://github.com/astral-sh/ruff | (개발 도구) 파이썬 린트·코드 스타일 검사 |
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
| 16 | Ollama | 0.34.1 (결과보고서 제출 당시 0.32.15) | MIT | https://github.com/ollama/ollama | 로컬 LLM 실행 런타임 — 코어 `--llm` 이름 탐지에 사용 (**선택 의존성**: 없어도 규칙 탐지는 동작) |
| 17 | maskingtape-name-1.5b (AI 모델, 우리가 학습) | v3, Q4_K_M GGUF (상세는 부록 C-1) | Apache-2.0 | https://huggingface.co/StayAlive1/maskingtape-name-1.5b | 이름(인명) 문맥 판단용 **기본 모델**. Qwen2.5-1.5B-Instruct를 합성 데이터로 파인튜닝(#458). **로컬 실행 전용, 외부 API 호출 없음** |
| 18 | FastAPI | >=0.116,<1 | MIT | https://github.com/fastapi/fastapi | API 서버 프레임워크 — 웹·데스크톱 공용 REST 엔드포인트 제공 |
| 19 | Uvicorn | >=0.35,<1 | BSD-3-Clause | https://github.com/encode/uvicorn | API 서버 실행용 ASGI 서버 |
| 20 | Pydantic | >=2.9,<3 | MIT | https://github.com/pydantic/pydantic | API 요청·응답 데이터 검증 및 OpenAPI 스키마 생성 |
| 21 | HTTPX2 | >=2,<3 | BSD-3-Clause | https://github.com/pydantic/httpx2 | (개발 도구) FastAPI/Starlette TestClient 기반 API 테스트 실행 |
| 22 | pdfjs-dist | ^6.2.108 | Apache-2.0 | https://github.com/mozilla/pdf.js | 웹 플레이그라운드 — 브라우저(클라이언트) 안에서 PDF 텍스트 추출, 파일을 서버로 보내지 않기 위함 |
| 23 | cupertino_icons | ^1.0.8 | MIT | https://github.com/flutter/packages/tree/main/third_party/packages/cupertino_icons | 데스크톱 앱 — 기본 아이콘 폰트 (Flutter 프로젝트 생성 시 포함) |
| 24 | flutter_lints | ^6.0.0 | BSD-3-Clause | https://github.com/flutter/packages/tree/main/packages/flutter_lints | (개발 도구) 데스크톱 앱 Dart 린트 규칙 모음 |
| 25 | scrubadub | >=2,<3 (실측 2.0.1) | MIT metadata / Apache-2.0 classifier | https://github.com/LeapBeyond/scrubadub | (개발 도구) bench 오픈소스 PII 도구 비교 기준선 — 로컬 실행, 발표용 정확도 대비표 생성 |
| 26 | Qwen2.5-7B-Instruct (AI 모델, 선택) | qwen2.5:7b (Q4_K_M, 상세는 부록 C-2) | Apache-2.0 | https://github.com/QwenLM/Qwen2.5 | 이전 기본 모델. `--llm-model qwen2.5:7b`로 고를 때만 쓴다. 로컬 실행 전용 |
| 27 | Qwen2.5-1.5B-Instruct (기반 모델) | Qwen/Qwen2.5-1.5B-Instruct | Apache-2.0 | https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct | (학습 도구) 17번 모델의 파인튜닝 기반 가중치. 학습할 때만 받는다 |
| 28 | PyTorch (torch) | 2.6.0+cu124 | BSD-3-Clause | https://github.com/pytorch/pytorch | (학습 도구) `training/`의 LoRA 학습·가중치 병합 |
| 29 | transformers | 5.18.0 | Apache-2.0 | https://github.com/huggingface/transformers | (학습 도구) 모델·토크나이저 로드, Trainer |
| 30 | peft | 0.21.2 | Apache-2.0 | https://github.com/huggingface/peft | (학습 도구) LoRA 어댑터 학습·병합 |
| 31 | accelerate | 1.15.0 | Apache-2.0 | https://github.com/huggingface/accelerate | (학습 도구) Trainer 실행 의존 |
| 32 | huggingface_hub | 1.33.0 | Apache-2.0 | https://github.com/huggingface/huggingface_hub | (학습 도구) 기반 모델 받기·학습한 가중치 올리기 |
| 33 | safetensors / tokenizers | 0.8.0 / 0.23.2 | Apache-2.0 | https://github.com/huggingface/safetensors · https://github.com/huggingface/tokenizers | (학습 도구) 가중치 파일 형식·토크나이저 |
| 34 | sentencepiece / protobuf | 0.2.2 / 7.36.2 | Apache-2.0 / BSD-3-Clause | https://github.com/google/sentencepiece · https://github.com/protocolbuffers/protobuf | (학습 도구) transformers 토크나이저 의존 |
| 35 | gguf (Python) | 0.19.0 | MIT | https://github.com/ggml-org/llama.cpp/tree/master/gguf-py | (학습 도구) GGUF 변환 |
| 36 | llama.cpp (변환 스크립트·llama-quantize) | b11368 | MIT | https://github.com/ggml-org/llama.cpp | (학습 도구) f16 GGUF 변환·Q4_K_M 양자화. `training/export_ollama.py`가 호출 |

※ **AI 모델 주의**: Qwen2.5는 **3B·72B만 비상업 제한(Qwen Research License)**이고 나머지(0.5B/**1.5B**/**7B**/14B/32B)가 Apache-2.0이다. 기본 모델은 1.5B를 학습한 17번, 선택 모델은 7B(26번)다. **3B로 바꾸지 말 것.**
※ 위 16·17·26번은 결과보고서 **붙임2(AI 모델 활용 및 라이선스 기술 명세서)**에도 반영한다(유형2 '외부 모델 파인튜닝' + 기반 모델명·라이선스·학습 데이터·가중치 공개 주소).
※ 27~36번 학습 도구는 `training/`의 학습·변환에만 쓰며 배포물(PyPI·웹·MCP·데스크톱)과 공개한 가중치 파일에 들어가지 않는다. 버전은 학습한 PC의 환경 기준(2026-10-03, #643)이다. 학습 PC의 NVIDIA CUDA 런타임은 부록 B에 적었다.

## 부록 A: 배포물별 전이 의존성

위 본표는 우리가 **직접 선언한** 의존성이다. 아래는 그 의존성이 끌어오는 패키지까지 배포물별로 모은 표다.
2026년 9월 OpenUP 오픈소스 라이선스 컨설팅은 배포에 포함되는 의존성은 전이 의존성까지 적는 것이
원칙이라고 권고했고, 같은 컨설팅에서 이 SBOM 기준으로 라이선스 충돌은 없다고 확인받았다.
배포물에 코드가 함께 실리는 제3자 소프트웨어의 고지는 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)에 있다.

<!-- sbom-transitive:begin -->
> 이 구간은 `python scripts/sbom_transitive.py --write`가 만든다. 손으로 고치지 않는다.

PyPI 코어 패키지(`maskingtape`)는 런타임 외부 의존성이 없어 표가 없다.

### A-1. 웹 데모 빌드 결과물 (npm, 방문자 브라우저로 전송)

`apps/web/package-lock.json`에서 `dependencies`로부터 이어지는 패키지다. 코드가 번들에 들어가는 것은 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)에 고지한다.

| 패키지 | 버전 | 라이선스 | 저장소 | 비고 |
|---|---|---|---|---|
| @napi-rs/canvas | 1.0.6 | MIT | https://github.com/Brooooooklyn/canvas | 경로: pdfjs-dist → @napi-rs/canvas. Node 전용 선택 의존성. 브라우저 번들에는 코드가 없다(불러오는 문자열만 있음) |
| pdfjs-dist | 6.2.108 | Apache-2.0 | https://github.com/mozilla/pdf.js | 직접 의존성(본표) |
| react | 19.2.7 | MIT | https://github.com/facebook/react | 직접 의존성(본표) |
| react-dom | 19.2.7 | MIT | https://github.com/facebook/react | 직접 의존성(본표) |
| scheduler | 0.27.0 | MIT | https://github.com/facebook/react | 경로: react-dom → scheduler |
| @napi-rs/canvas-* | 1.0.6 | MIT |  | @napi-rs/canvas의 플랫폼별 바이너리 11개. 브라우저 번들에 없음 |

### A-2. REST API 서버 (Python, 공개 데모 서버에 설치)

`uv.lock`(Vercel 배포가 쓰는 lock)에서 `maskingtape-api`로부터 이어지는 패키지다. 조건이 붙은 패키지는 그 환경에서만 설치된다.

| 패키지 | 버전 | 라이선스 | 저장소 | 비고 |
|---|---|---|---|---|
| annotated-doc | 0.0.5 | MIT | https://github.com/fastapi/annotated-doc | 경로: fastapi → annotated-doc |
| annotated-types | 0.8.0 | MIT | https://github.com/annotated-types/annotated-types | 경로: pydantic → annotated-types |
| anyio | 4.14.2 | MIT | https://github.com/agronholm/anyio | 경로: fastapi → starlette → anyio |
| click | 8.4.2 | BSD-3-Clause | https://github.com/pallets/click/ | 경로: uvicorn → click |
| colorama | 0.4.6 | BSD | https://github.com/tartley/colorama | 경로: uvicorn → click → colorama. 조건: `sys_platform == 'win32'` |
| exceptiongroup | 1.3.1 | MIT | https://github.com/agronholm/exceptiongroup | 경로: fastapi → starlette → anyio → exceptiongroup. 조건: `python_full_version < '3.11'` |
| fastapi | 0.141.1 | MIT | https://github.com/fastapi/fastapi | 직접 의존성(본표) |
| h11 | 0.16.0 | MIT | https://github.com/python-hyper/h11 | 경로: uvicorn → h11 |
| idna | 3.18 | BSD-3-Clause | https://github.com/kjd/idna | 경로: fastapi → starlette → anyio → idna |
| pydantic | 2.13.4 | MIT | https://github.com/pydantic/pydantic | 직접 의존성(본표) |
| pydantic-core | 2.46.4 | MIT | https://github.com/pydantic/pydantic/tree/main/pydantic-core | 경로: pydantic → pydantic-core |
| starlette | 1.6.0 | BSD-3-Clause | https://github.com/Kludex/starlette | 경로: fastapi → starlette |
| typing-extensions | 4.16.0 | PSF-2.0 | https://github.com/python/typing_extensions | 경로: fastapi → typing-extensions |
| typing-inspection | 0.4.3 | MIT | https://github.com/pydantic/typing-inspection | 경로: fastapi → typing-inspection |
| uvicorn | 0.52.1 | BSD-3-Clause | https://github.com/Kludex/uvicorn | 직접 의존성(본표) |

### A-3. MCP 서버 (Python, 소스로 배포, 사용자가 설치할 때 받음)

표를 만든 환경(Python 3.13.2, Windows)의 설치본 기준이다. 조건이 붙은 패키지는 운영체제나 파이썬 버전에 따라 설치 여부가 달라진다.

| 패키지 | 버전 | 라이선스 | 저장소 | 비고 |
|---|---|---|---|---|
| annotated-types | 0.8.0 | MIT | https://github.com/annotated-types/annotated-types | 경로: maskingtape-mcp → mcp → pydantic → annotated-types |
| anyio | 4.15.1 | MIT | https://github.com/agronholm/anyio | 경로: maskingtape-mcp → mcp → anyio |
| attrs | 26.1.0 | MIT | https://github.com/python-attrs/attrs | 경로: maskingtape-mcp → mcp → jsonschema → attrs |
| certifi | 2026.7.22 | MPL-2.0 | https://github.com/certifi/python-certifi | 경로: maskingtape-mcp → mcp → httpx → certifi |
| cffi | 2.1.1 | MIT-0 | https://github.com/python-cffi/cffi | 경로: maskingtape-mcp → mcp → pyjwt → cryptography → cffi. 조건: `platform_python_implementation != "PyPy"` |
| click | 8.5.0 | BSD-3-Clause | https://github.com/pallets/click/ | 경로: maskingtape-mcp → mcp → uvicorn → click |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause | https://github.com/pyca/cryptography/ | 경로: maskingtape-mcp → mcp → pyjwt → cryptography. 조건: `extra == "crypto"` |
| exceptiongroup | - | - |  | 이 환경에 설치되지 않음. 조건: `python_version < "3.11"` |
| h11 | 0.16.0 | MIT | https://github.com/python-hyper/h11 | 경로: maskingtape-mcp → mcp → uvicorn → h11 |
| httpcore | 1.0.9 | BSD-3-Clause | https://github.com/encode/httpcore | 경로: maskingtape-mcp → mcp → httpx → httpcore |
| httpx | 0.28.1 | BSD-3-Clause | https://github.com/encode/httpx | 경로: maskingtape-mcp → mcp → httpx |
| httpx-sse | 0.4.3 | MIT | https://github.com/florimondmanca/httpx-sse | 경로: maskingtape-mcp → mcp → httpx-sse |
| idna | 3.20 | BSD-3-Clause | https://github.com/kjd/idna | 경로: maskingtape-mcp → mcp → anyio → idna |
| jsonschema | 4.26.0 | MIT | https://github.com/python-jsonschema/jsonschema | 경로: maskingtape-mcp → mcp → jsonschema |
| jsonschema-specifications | 2025.9.1 | MIT | https://github.com/python-jsonschema/jsonschema-specifications | 경로: maskingtape-mcp → mcp → jsonschema → jsonschema-specifications |
| mcp | 1.30.0 | MIT | https://github.com/modelcontextprotocol/python-sdk | 직접 의존성 |
| pycparser | 3.0 | BSD-3-Clause | https://github.com/eliben/pycparser | 경로: maskingtape-mcp → mcp → pyjwt → cryptography → cffi → pycparser. 조건: `implementation_name != "PyPy"` |
| pydantic | 2.13.5 | MIT | https://github.com/pydantic/pydantic | 경로: maskingtape-mcp → mcp → pydantic. 조건: `python_version < "3.14"` |
| pydantic-core | 2.46.5 | MIT | https://github.com/pydantic/pydantic/tree/main/pydantic-core | 경로: maskingtape-mcp → mcp → pydantic → pydantic-core |
| pydantic-settings | 2.15.0 | MIT | https://github.com/pydantic/pydantic-settings | 경로: maskingtape-mcp → mcp → pydantic-settings |
| pyjwt | 2.15.1 | MIT | https://github.com/jpadilla/pyjwt | 경로: maskingtape-mcp → mcp → pyjwt |
| python-dotenv | 1.2.4 | BSD-3-Clause | https://github.com/theskumar/python-dotenv | 경로: maskingtape-mcp → mcp → pydantic-settings → python-dotenv |
| python-multipart | 0.0.32 | Apache-2.0 | https://github.com/Kludex/python-multipart | 경로: maskingtape-mcp → mcp → python-multipart |
| pywin32 | 312 | PSF-2.0 | https://github.com/mhammond/pywin32 | 경로: maskingtape-mcp → mcp → pywin32. 조건: `sys_platform == "win32" and python_version < "3.14"` |
| referencing | 0.37.0 | MIT | https://github.com/python-jsonschema/referencing | 경로: maskingtape-mcp → mcp → jsonschema → referencing |
| rpds-py | 2026.6.3 | MIT | https://github.com/crate-py/rpds | 경로: maskingtape-mcp → mcp → jsonschema → rpds-py |
| sse-starlette | 3.5.0 | BSD-3-Clause | https://github.com/sysid/sse-starlette | 경로: maskingtape-mcp → mcp → sse-starlette |
| starlette | 1.7.0 | BSD-3-Clause | https://github.com/Kludex/starlette | 경로: maskingtape-mcp → mcp → starlette. 조건: `python_version < "3.14"` |
| typing-extensions | 4.16.0 | PSF-2.0 | https://github.com/python/typing_extensions | 경로: maskingtape-mcp → mcp → typing-extensions |
| typing-inspection | 0.4.4 | MIT | https://github.com/pydantic/typing-inspection | 경로: maskingtape-mcp → mcp → typing-inspection |
| uvicorn | 0.54.0 | BSD-3-Clause | https://github.com/Kludex/uvicorn | 경로: maskingtape-mcp → mcp → uvicorn. 조건: `sys_platform != "emscripten"` |

### A-4. 데스크톱 앱 (Dart·Flutter, 소스로 배포, 빌드할 때 받음)

`apps/desktop/pubspec.lock` 전체다. 전이 의존성에는 `flutter_test`·`flutter_lints`가 끌어오는 개발용 패키지도 섞여 있다. 라이선스는 pub.dev가 각 패키지의 LICENSE에서 판별한 값이다. pub.dev가 놓친 것은 그 버전의 LICENSE를 직접 열어 확인한 값으로 바꿨다(vector_math).

| 패키지 | 버전 | 라이선스 | 저장소 | 비고 |
|---|---|---|---|---|
| async | 2.13.1 | BSD-3-Clause | https://github.com/dart-lang/core/tree/main/pkgs/async | 전이 |
| boolean_selector | 2.1.2 | BSD-3-Clause | https://github.com/dart-lang/tools/tree/main/pkgs/boolean_selector | 전이 |
| characters | 1.4.1 | BSD-3-Clause | https://github.com/dart-lang/core/tree/main/pkgs/characters | 전이 |
| clock | 1.1.2 | Apache-2.0 | https://github.com/dart-lang/tools/tree/main/pkgs/clock | 전이 |
| collection | 1.19.1 | BSD-3-Clause | https://github.com/dart-lang/core/tree/main/pkgs/collection | 전이 |
| cp949_codec | 1.0.2 | BSD-3-Clause | https://github.com/letyletylety/cp949_codec | 직접(런타임) |
| cross_file | 0.3.5+4 | BSD-3-Clause | https://github.com/flutter/packages/tree/main/packages/cross_file | 전이 |
| cupertino_icons | 1.0.9 | MIT | https://github.com/flutter/packages/tree/main/third_party/packages/cupertino_icons | 직접(런타임) |
| desktop_drop | 0.7.1 | Apache-2.0 | https://github.com/MixinNetwork/flutter-plugins/tree/main/packages/desktop_drop | 직접(런타임) |
| fake_async | 1.3.3 | Apache-2.0 | https://github.com/dart-lang/test/tree/master/pkgs/fake_async | 전이 |
| file_selector | 1.1.0 | BSD-3-Clause | https://github.com/flutter/packages/tree/main/packages/file_selector/file_selector | 직접(런타임) |
| file_selector_android | 0.5.2+8 | Apache-2.0 AND BSD-3-Clause | https://github.com/flutter/packages/tree/main/packages/file_selector/file_selector_android | 전이 |
| file_selector_ios | 0.5.3+5 | BSD-3-Clause | https://github.com/flutter/packages/tree/main/packages/file_selector/file_selector_ios | 전이 |
| file_selector_linux | 0.9.4 | BSD-3-Clause | https://github.com/flutter/packages/tree/main/packages/file_selector/file_selector_linux | 전이 |
| file_selector_macos | 0.9.5 | BSD-3-Clause | https://github.com/flutter/packages/tree/main/packages/file_selector/file_selector_macos | 전이 |
| file_selector_platform_interface | 2.7.0 | BSD-3-Clause | https://github.com/flutter/packages/tree/main/packages/file_selector/file_selector_platform_interface | 전이 |
| file_selector_web | 0.9.5 | BSD-3-Clause | https://github.com/flutter/packages/tree/main/packages/file_selector/file_selector_web | 전이 |
| file_selector_windows | 0.9.3+5 | BSD-3-Clause | https://github.com/flutter/packages/tree/main/packages/file_selector/file_selector_windows | 전이 |
| flutter | 0.0.0 | BSD-3-Clause | https://github.com/flutter/flutter | 직접(런타임). Flutter SDK에 포함 |
| flutter_lints | 6.0.0 | BSD-3-Clause | https://github.com/flutter/packages/tree/main/packages/flutter_lints | 직접(개발) |
| flutter_test | 0.0.0 | BSD-3-Clause | https://github.com/flutter/flutter | 직접(개발). Flutter SDK에 포함 |
| flutter_web_plugins | 0.0.0 | BSD-3-Clause | https://github.com/flutter/flutter | 전이. Flutter SDK에 포함 |
| http | 1.6.0 | BSD-3-Clause | https://github.com/dart-lang/http/tree/master/pkgs/http | 전이 |
| http_parser | 4.1.2 | BSD-3-Clause | https://github.com/dart-lang/http/tree/master/pkgs/http_parser | 전이 |
| leak_tracker | 11.0.2 | BSD-3-Clause | https://github.com/dart-lang/leak_tracker/tree/main/pkgs/leak_tracker | 전이 |
| leak_tracker_flutter_testing | 3.0.10 | BSD-3-Clause | https://github.com/dart-lang/leak_tracker/tree/main/pkgs/leak_tracker_flutter_testing | 전이 |
| leak_tracker_testing | 3.0.2 | BSD-3-Clause | https://github.com/dart-lang/leak_tracker/tree/main/pkgs/leak_tracker_testing | 전이 |
| lints | 6.1.0 | BSD-3-Clause | https://github.com/dart-lang/core/tree/main/pkgs/lints | 전이 |
| matcher | 0.12.19 | BSD-3-Clause | https://github.com/dart-lang/test/tree/master/pkgs/matcher | 전이 |
| material_color_utilities | 0.13.0 | Apache-2.0 | https://github.com/material-foundation/material-color-utilities/tree/main/dart | 전이 |
| meta | 1.18.0 | BSD-3-Clause | https://github.com/dart-lang/sdk/tree/main/pkg/meta | 전이 |
| path | 1.9.1 | BSD-3-Clause | https://github.com/dart-lang/core/tree/main/pkgs/path | 전이 |
| plugin_platform_interface | 2.1.8 | BSD-3-Clause | https://github.com/flutter/packages/tree/main/packages/plugin_platform_interface | 전이 |
| sky_engine | 0.0.0 | BSD-3-Clause | https://github.com/flutter/flutter | 전이. Flutter SDK에 포함 |
| source_span | 1.10.2 | BSD-3-Clause | https://github.com/dart-lang/tools/tree/main/pkgs/source_span | 전이 |
| stack_trace | 1.12.1 | BSD-3-Clause | https://github.com/dart-lang/tools/tree/main/pkgs/stack_trace | 전이 |
| stream_channel | 2.1.4 | BSD-3-Clause | https://github.com/dart-lang/tools/tree/main/pkgs/stream_channel | 전이 |
| string_scanner | 1.4.1 | BSD-3-Clause | https://github.com/dart-lang/tools/tree/main/pkgs/string_scanner | 전이 |
| term_glyph | 1.2.2 | BSD-3-Clause | https://github.com/dart-lang/tools/tree/main/pkgs/term_glyph | 전이 |
| test_api | 0.7.11 | BSD-3-Clause | https://github.com/dart-lang/test/tree/master/pkgs/test_api | 전이 |
| typed_data | 1.4.0 | BSD-3-Clause | https://github.com/dart-lang/core/tree/main/pkgs/typed_data | 전이 |
| universal_platform | 1.1.0 | MIT | https://github.com/gskinnerTeam/flutter-universal-platform | 전이 |
| vector_math | 2.2.0 | BSD-3-Clause AND Zlib | https://github.com/google/vector_math.dart | 전이 |
| vm_service | 15.2.0 | BSD-3-Clause | https://github.com/dart-lang/sdk/tree/main/pkg/vm_service | 전이 |
| web | 1.1.1 | BSD-3-Clause | https://github.com/dart-lang/web | 전이 |

### A-5. 개발 도구 (배포물에 포함되지 않음)

npm 개발 의존성 163개: MIT 114 · Apache-2.0 25 · MPL-2.0 12 · ISC 3 · BSD-2-Clause 2 · BSD-3-Clause 2 · MIT-0 2 · 0BSD 1 · BlueOak-1.0.0 1 · CC0-1.0 1

Python 개발 도구(pytest·ruff·httpx2와 그 전이, Python 3.13.2, Windows) 17개: MIT 7 · - 3 · BSD-3-Clause 3 · Apache-2.0 OR BSD-2-Clause 1 · BSD 1 · BSD-2-Clause 1 · PSF-2.0 1

설치되지 않아 확인하지 못한 패키지: exceptiongroup, httpx2-jsfetch, tomli

### A-6. 팀 허용 목록(MIT·Apache-2.0·BSD·ISC와 그 변형) 밖 라이선스

각 항목의 판단 근거는 아래 부록 B에 있다.

| 패키지 | 버전 | 라이선스 | 저장소 | 비고 |
|---|---|---|---|---|
| typing-extensions | 4.16.0 | PSF-2.0 | https://github.com/python/typing_extensions | REST API 서버. 경로: fastapi → typing-extensions |
| certifi | 2026.7.22 | MPL-2.0 | https://github.com/certifi/python-certifi | MCP 서버. 경로: maskingtape-mcp → mcp → httpx → certifi |
| pywin32 | 312 | PSF-2.0 | https://github.com/mhammond/pywin32 | MCP 서버. 경로: maskingtape-mcp → mcp → pywin32. 조건: `sys_platform == "win32" and python_version < "3.14"` |
| typing-extensions | 4.16.0 | PSF-2.0 | https://github.com/python/typing_extensions | MCP 서버. 경로: maskingtape-mcp → mcp → typing-extensions |
| vector_math | 2.2.0 | BSD-3-Clause AND Zlib | https://github.com/google/vector_math.dart | 데스크톱 앱. 전이 |
| lightningcss | 1.33.0 | MPL-2.0 |  | 개발 도구(npm). 경로: vite → lightningcss |
| lightningcss-android-arm64 | 1.33.0 | MPL-2.0 |  | 개발 도구(npm). 경로: vite → lightningcss → lightningcss-android-arm64 |
| lightningcss-darwin-arm64 | 1.33.0 | MPL-2.0 |  | 개발 도구(npm). 경로: vite → lightningcss → lightningcss-darwin-arm64 |
| lightningcss-darwin-x64 | 1.33.0 | MPL-2.0 |  | 개발 도구(npm). 경로: vite → lightningcss → lightningcss-darwin-x64 |
| lightningcss-freebsd-x64 | 1.33.0 | MPL-2.0 |  | 개발 도구(npm). 경로: vite → lightningcss → lightningcss-freebsd-x64 |
| lightningcss-linux-arm-gnueabihf | 1.33.0 | MPL-2.0 |  | 개발 도구(npm). 경로: vite → lightningcss → lightningcss-linux-arm-gnueabihf |
| lightningcss-linux-arm64-gnu | 1.33.0 | MPL-2.0 |  | 개발 도구(npm). 경로: vite → lightningcss → lightningcss-linux-arm64-gnu |
| lightningcss-linux-arm64-musl | 1.33.0 | MPL-2.0 |  | 개발 도구(npm). 경로: vite → lightningcss → lightningcss-linux-arm64-musl |
| lightningcss-linux-x64-gnu | 1.33.0 | MPL-2.0 |  | 개발 도구(npm). 경로: vite → lightningcss → lightningcss-linux-x64-gnu |
| lightningcss-linux-x64-musl | 1.33.0 | MPL-2.0 |  | 개발 도구(npm). 경로: vite → lightningcss → lightningcss-linux-x64-musl |
| lightningcss-win32-arm64-msvc | 1.33.0 | MPL-2.0 |  | 개발 도구(npm). 경로: vite → lightningcss → lightningcss-win32-arm64-msvc |
| lightningcss-win32-x64-msvc | 1.33.0 | MPL-2.0 |  | 개발 도구(npm). 경로: vite → lightningcss → lightningcss-win32-x64-msvc |
| lru-cache | 11.5.2 | BlueOak-1.0.0 |  | 개발 도구(npm). 경로: jsdom → lru-cache |
| mdn-data | 2.27.1 | CC0-1.0 |  | 개발 도구(npm). 경로: jsdom → css-tree → mdn-data |
| typing-extensions | 4.16.0 | PSF-2.0 | https://github.com/python/typing_extensions | 개발 도구(Python). 직접 의존성. 조건: `python_version < "3.13"` |
<!-- sbom-transitive:end -->

## 부록 B: 허용 목록 밖 라이선스에 대한 판단

부록 A-6에 모인 패키지다. 모두 **우리가 직접 선언하지 않았고, 수정하지 않고 그대로 쓴다.**

### certifi (MPL-2.0) — MCP 서버

- **직접 의존이 아니다.** 우리 코드는 certifi를 import하지 않는다. HTTP 클라이언트(httpx)가 TLS 루트 인증서 번들로 쓰는 전이 의존이다(mcp → httpx → certifi).
- **MPL-2.0은 OSI 승인 라이선스**이며 **파일 단위(file-level) 카피레프트**다. 원본 파일을 수정하지 않고 그대로 재배포하는 한, 우리 코드(Apache-2.0)에 라이선스 전파 의무가 발생하지 않는다(MPL-2.0 §3.3 — Larger Work를 다른 라이선스로 배포 가능).
- **우리는 certifi를 수정하지 않는다.** 수정 없이 pip 의존성으로 설치될 뿐이므로 소스 공개 의무(MPL-2.0 §3.2)의 대상이 아니다.
- 결론: **재배포 형태상 의무 없음.** 다만 전체 의존성 트리를 엄격 스캔하는 검증에서는 노출되므로 위와 같이 근거를 남긴다.

### typing-extensions, pywin32 (PSF-2.0) — REST API 서버, MCP 서버

- **직접 의존이 아니다.** typing-extensions는 fastapi·pydantic·mcp가, pywin32는 Windows에서 mcp가 끌어온다. 우리 코드는 둘 다 import하지 않는다.
- PSF-2.0(Python Software Foundation License 2.0)은 파이썬 자체와 같은 계열의 **퍼미시브 라이선스**다. 카피레프트 조항이 없고, 라이선스와 저작권 고지를 유지하면 사용·수정·재배포할 수 있다.
- 우리는 두 패키지를 재배포하지 않는다. REST API 서버에서는 공개 데모 서버에 설치될 뿐이고, MCP 서버는 사용자가 설치할 때 각자 받는다.
- 결론: **의무 없음.**

### vector_math (BSD-3-Clause AND Zlib) — 데스크톱 앱

- **직접 의존이 아니다.** `apps/desktop/pubspec.lock`에 전이 의존성으로 들어 있고, 우리 Dart 코드는 vector_math를 import하지 않는다.
- `LICENSE` 하나에 두 라이선스 전문이 함께 있다. Google(2015)의 BSD-3-Clause와 Andrew Magill(2013)의 zlib이다. pub.dev 태그는 BSD-3-Clause 하나뿐이라 생성기가 놓쳤다. OpenUP 사전 검증보고서(2026-10-01)가 두 라이선스로 판정해서, pub.dev에서 받은 2.2.0 아카이브를 열어 확인했다(2026-10-03, #634). 생성기는 이 결과를 `PUB_LICENSE_CHECKED`에 버전과 함께 적어 두고, lock의 버전이 바뀌면 「확인 필요」로 표시한다.
- **zlib은 OSI 승인 퍼미시브 라이선스**다(SPDX 라이선스 목록 3.29). 카피레프트 조항이 없다. 조건은 셋이다. 원작자를 속이지 않는다, 수정한 소스는 수정했다고 밝힌다, 소스를 배포할 때 고지를 지우지 않는다. 제품 문서에 출처를 적는 것은 권장이고 의무가 아니다.
- 우리는 vector_math를 수정하지 않고 소스를 재배포하지도 않는다. 데스크톱 앱은 소스로 배포되고, 빌드할 때 pub이 받아 온다.
- 결론: **의무 없음.** 설치 파일로 배포하게 되면 BSD-3-Clause의 바이너리 고지 조건이 생기므로, 앱의 라이선스 화면에 이 고지가 들어가는지 그때 확인한다.

### lightningcss 계열 (MPL-2.0), lru-cache (BlueOak-1.0.0), mdn-data (CC0-1.0) — 개발 도구

- 셋 다 웹 데모의 **빌드·테스트 도구**(vite, jsdom)가 끌어오는 패키지라 **배포물에 포함되지 않는다.** 빌드 결과물(`apps/web/dist/`)에 이 패키지들의 코드가 없다. CSS에 남는 `--lightningcss-light`·`--lightningcss-dark`는 lightningcss가 CSS를 변환하면서 붙인 변수 이름이다(2026-09-17 빌드로 확인).
- lightningcss는 빌드할 때 CSS를 변환하는 도구로만 실행된다. MPL-2.0은 파일 단위 카피레프트라, 수정 없이 도구로 쓰는 한 우리 코드에 영향이 없다.
- BlueOak-1.0.0은 배포할 때 라이선스 문구를 함께 전달하는 조건의 퍼미시브 라이선스이고, CC0-1.0은 퍼블릭 도메인 헌정이다. 둘 다 배포하지 않으므로 해당 조건이 생기지 않는다.
- 결론: **배포물 미포함, 의무 없음.**

### NVIDIA CUDA 런타임 (NVIDIA 독점 라이선스) — 학습 PC

- 본표 28번 torch의 CUDA 빌드(2.6.0+cu124)에 함께 들어 있는 NVIDIA 런타임 라이브러리다. 오픈소스가 아니다.
- 팀원의 학습 PC에서 GPU로 17번 모델을 학습할 때만 쓴다. 우리 코드는 CUDA를 직접 부르지 않고 torch를 통해 쓴다. 학습 스크립트(`training/train_lora.py`)는 CUDA GPU가 있어야 돈다.
- 배포물(PyPI·웹·MCP·데스크톱)과 공개한 가중치 파일 어디에도 들어가지 않는다. 가중치 파일은 모델의 숫자 값만 담는다.
- 대회 규정 제8조 ③항이 막는 비상업 조건 라이선스가 아니다. 학습 환경을 밝히려고 적는다.
- 결론: **배포물 미포함, 의무 없음.**

## 부록 C: AI 모델 상세
### cffi (MIT-0), cryptography (Apache-2.0 OR BSD-3-Clause) — MCP 서버

- 부록 A-6에는 없지만(생성기가 허용으로 판정), 팀 허용 목록의 표기(MIT·Apache-2.0·BSD·ISC)와 글자가 달라 근거를 남긴다(#500).
- **직접 의존이 아니다.** mcp가 `pyjwt[crypto]`로 요청한 extra를 따라 cryptography → cffi → pycparser가 설치된다. 생성기가 extra 요구사항을 따라가지 않아 이번 수정 전까지 부록 A에서 빠져 있었다.
- MIT-0은 MIT에서 "저작권·허가 고지를 사본에 포함해야 한다"는 조건까지 뺀 라이선스다(OSI 승인). MIT보다 조건이 적으므로 MIT를 허용하는 팀 기준을 그대로 만족한다.
- cryptography는 Apache-2.0과 BSD-3-Clause 중 하나를 고르는 이중 라이선스이고, 둘 다 허용 목록 안이다.
- 결론: **허용 목록 안, 의무 없음.**

## 부록 C: AI 모델 상세 (Qwen2.5-7B-Instruct)

모델 가중치는 정해진 SBOM 양식이 없어, 확인할 수 있는 정보를 모두 적는다(2026년 9월 OpenUP 컨설팅 권고).

### C-1. maskingtape-name-1.5b (기본 모델, 우리가 학습)

| 항목 | 내용 |
|---|---|
| 모델 | maskingtape-name-1.5b v3 (The maskingtape Authors). 한국어 문서에서 사람 이름만 뽑는다(#458) |
| 라이선스 | Apache-2.0 (허깅페이스 두 저장소에 LICENSE 파일) |
| 기반 모델 | Qwen/Qwen2.5-1.5B-Instruct (Alibaba Cloud Qwen 팀, Apache-2.0), 본표 27번 |
| 원본 | https://huggingface.co/StayAlive1/maskingtape-name-1.5b (병합 가중치, safetensors) · https://huggingface.co/StayAlive1/maskingtape-name-1.5b-GGUF (GGUF) |
| 받는 경로 | `ollama pull hf.co/StayAlive1/maskingtape-name-1.5b-GGUF:Q4_K_M` |
| 아키텍처 · 파라미터 | qwen2 · 1.54B |
| 양자화 | Q4_K_M (F16 GGUF도 같은 저장소에 공개) |
| 모델 파일 | `model.safetensors`(병합 가중치, 정본) `sha256:9d253a105c8590f687c3737b16af3585858aba112608513f52bf08e2e97b196b` (3,087,467,144바이트) · `maskingtape-name-1.5b-Q4_K_M.gguf` `sha256:d728d0f63ba1c5c095a7b2bb9bd6c79f375f97aa201db87b13f404889ca25ec5` (986,048,064바이트) · `maskingtape-name-1.5b-F16.gguf` `sha256:6e8ed2ca5934d92f78aa83af198bbde440bb7330bf5c8e5e65dfa92a91581846` (3,093,668,928바이트) |
| 학습 데이터 | 합성 12,000건. `training/make_dataset.py`가 bench 생성기와 직접 쓴 합성 문장으로 만들고, 같은 시드에서 그대로 재현된다. 실제 개인정보·외부 데이터셋은 쓰지 않았다 |
| 학습 설정 | LoRA r=16 · alpha 32 · dropout 0.05 · 전 선형층(q/k/v/o/gate/up/down), bf16, 2 에폭, 학습률 2e-4, 유효 배치 16, 정답 토큰에만 손실. 학습 뒤 기반 모델에 병합 |
| 학습·변환 코드 | `training/train_lora.py`, `training/export_ollama.py` (Apache-2.0) |
| 확인 환경 | 허깅페이스 API로 공개 상태(접근 제한 없음)·라이선스·파일 해시를 확인하고, Ollama 0.35.1로 받은 파일의 해시가 같음을 확인(2026-10-04) |
| 사용 방식 | 로컬 전용. 코어의 이름 탐지기가 `--llm` 옵션을 켰을 때만 `http://127.0.0.1:11434`로 호출한다(`packages/core/maskingtape/detectors/personal/name_llm.py`의 `DEFAULT_MODEL`·`DEFAULT_HOST`). 로컬이 아닌 주소는 코드에서 거부한다 |
| 재배포 | 하지 않는다. 저장소·PyPI·웹 데모 어디에도 가중치를 싣지 않고, 사용자가 Ollama로 허깅페이스에서 직접 받는다 |
| 변형 | 파인튜닝 있음. 결과보고서 붙임2의 유형2(외부 모델 파인튜닝) |

### C-2. Qwen2.5-7B-Instruct (선택 모델, 이전 기본)

| 항목 | 내용 |
|---|---|
| 모델 | Qwen2.5-7B-Instruct (Alibaba Cloud Qwen 팀) |
| 라이선스 | Apache-2.0 (Ollama 모델 매니페스트에 라이선스 전문이 들어 있음) |
| 원본 | https://huggingface.co/Qwen/Qwen2.5-7B-Instruct · https://github.com/QwenLM/Qwen2.5 |
| 받는 경로 | Ollama 라이브러리 `qwen2.5:7b` (`ollama pull qwen2.5:7b`) · https://ollama.com/library/qwen2.5 |
| 아키텍처 · 파라미터 | qwen2 · 7.6B |
| 양자화 | Q4_K_M |
| 컨텍스트 길이 | 32,768 토큰 |
| 모델 파일 | `sha256:2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730` (4,683,073,952바이트) |
| 매니페스트 config | `sha256:2f15b3218f0552c60647ce60ada83632d2c09755b16259b13e3e4458e9ae419d` |
| 확인 환경 | Ollama 0.34.1, `ollama show qwen2.5:7b`와 로컬 매니페스트로 확인(2026-09-17) |
| 사용 방식 | 로컬 전용. `--llm`과 함께 `--llm-model qwen2.5:7b`를 줄 때만 `http://127.0.0.1:11434`로 호출한다(`DEFAULT_HOST`). 로컬이 아닌 주소는 코드에서 거부한다 |
| 재배포 | 하지 않는다. 저장소·PyPI·웹 데모 어디에도 가중치를 싣지 않고, 사용자가 Ollama로 직접 받는다 |
| 변형 | 수정·미세조정 없음(이 모델 자체는 유형1 '외부 모델 그대로'로 쓴다) |

## 부록 D: 평가에 쓴 외부 데이터셋

저장소에 넣지 않고, 학습에도 쓰지 않았다. 평가 수치의 출처를 밝히려고 적는다(2026-09-29 운영사무국 답: 외부 공개 데이터셋은 SBOM에 출처와 함께 밝히고 그 라이선스를 따른다).

| 데이터셋 | 출처 | 라이선스 | 쓴 곳 |
|---|---|---|---|
| KDPII (한국어 대화 개인정보 데이터셋) | https://doi.org/10.5281/zenodo.10968609 | CC-BY-4.0 | README의 이름 하이브리드 외부 비교(test에서 500문장, 2026-10-04). 원자료와 변환본은 저장소에 싣지 않는다 |
