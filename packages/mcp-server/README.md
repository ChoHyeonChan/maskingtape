# packages/mcp-server — MCP 서버

**담당: 조현찬 (팀장)** · 상태: ✅ v1 동작 (stdio)

AI 에이전트가 한국어 데이터를 다루기 전에 거치는 **프라이버시 계층**.
`packages/core`를 import해서 MCP 도구로 **노출만** 한다 — 탐지 로직은 `tools.py`가 core를 호출할 뿐, 여기에 두지 않는다.

## 도구

| 도구 | 역할 |
|---|---|
| `scan_text(text)` | 개인정보 탐지 리포트 반환 (종류·위치·확신도) |
| `anonymize_text(text, strategy)` | 비식별화된 텍스트 반환 — `mask`(\*로 가림) / `label`([전화번호] 치환) |

계획: `anonymize_file`(파일 배치 처리) — 코어 v2 이후.

## 설치·실행

```bash
# 레포 루트에서 (core를 먼저 설치해야 한다 — maskingtape 의존성이 로컬에서 해결됨)
pip install -e packages/core -e packages/mcp-server

maskingtape-mcp        # stdio 전송으로 서버 시작 (보통 MCP 클라이언트가 대신 띄움)
```

## 클라이언트 등록

Claude Code:

```bash
claude mcp add maskingtape -- maskingtape-mcp
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
