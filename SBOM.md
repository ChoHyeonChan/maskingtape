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

※ AI 모델(Ollama + Qwen 등 오픈웨이트)을 도입하는 시점에 모델·라이선스 행을 추가하고, 결과보고서 **붙임2(AI 모델 활용 명세서)**에도 반영한다.
