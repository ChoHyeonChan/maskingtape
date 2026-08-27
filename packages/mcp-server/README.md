# packages/mcp-server — MCP 서버

**담당: [@ChoHyeonChan](https://github.com/ChoHyeonChan) (팀장)** · 상태: ✅ v1 동작 (stdio)

AI 에이전트가 한국어 데이터를 다루기 전에 거치는 **프라이버시 계층**.
`packages/core`를 import해서 MCP 도구로 **노출만** 한다 — 탐지 로직은 `tools.py`가 core를 호출할 뿐, 여기에 두지 않는다.

## 도구

| 도구 | 역할 |
|---|---|
| `scan_text(text)` | 개인정보 탐지 리포트 반환 (종류·위치·확신도 — **원문 값은 싣지 않음**) |
| `anonymize_text(text, strategy)` | 비식별화된 텍스트 반환 — `mask`(\*로 가림) / `label`([전화번호] 치환) / `pseudonym`(그럴듯한 가짜 값으로 치환) |
| `anonymize_file(path, strategy)` | 로컬 텍스트 파일을 `<이름>_masked.<확장자>`로 저장 |

**파일 접근 안전**: `anonymize_file`은 **허용 루트 안의 경로만** 읽고 쓴다(기본=서버 작업 디렉터리,
환경변수 `MASKINGTAPE_MCP_ROOT`로 재정의). 조작된 에이전트가 `~/.ssh/id_rsa` 같은 임의 경로를
넘겨도 거부한다. 심볼릭 링크·덮어쓰기·10MB 초과·비UTF-8도 막는다(`safe_file.py`).

## 설치·실행

```bash
# 레포 루트에서 (core를 먼저 설치해야 한다 — maskingtape 의존성이 로컬에서 해결됨)
pip install -e packages/core -e packages/mcp-server

maskingtape-mcp        # stdio 전송으로 서버 시작 (보통 MCP 클라이언트가 대신 띄움)
maskingtape-mcp --llm  # 하이브리드 모드 — 이름을 로컬 LLM으로 문맥 판단 (Ollama 필요)
```

## 규칙 전용 vs 하이브리드(`--llm`)

- **기본(`maskingtape-mcp`)**: 규칙 전용. Ollama 없이 어디서나 동작하는 **안전 바닥**.
- **`--llm`**: 이름을 로컬 LLM(Ollama + Qwen)으로 문맥 판단하는 하이브리드. 문맥 단서 없는
  이름("이서준 대표"의 서명 등)까지 잡는다. **로컬 Ollama가 실행 중이어야 한다.**

LLM 사용 여부를 도구 파라미터가 아닌 **서버 플래그**로 두는 이유: MCP 도구는 "에이전트가
조작된다"고 가정하므로, 마스킹 강도를 신뢰 주체(서버 세운 사람)가 정하게 한다. `--llm`인데
Ollama가 없으면 **조용히 규칙으로 강등하지 않고 명확히 에러**난다(하이브리드인 줄 알고 이름이
새는 것을 막기 위함).

## 클라이언트 등록

Claude Code:

```bash
claude mcp add maskingtape -- maskingtape-mcp          # 규칙 전용
claude mcp add maskingtape -- maskingtape-mcp --llm    # 하이브리드 (Ollama 필요)
```

Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "maskingtape": { "command": "maskingtape-mcp" }
  }
}
```

## 구조

```
maskingtape_mcp/
  tools.py    # 실제 동작 (순수 함수 — MCP 없이 테스트 가능)
  server.py   # FastMCP 등록 + 진입점 (노출만)
tests/        # 합성 데이터로만 테스트
```
