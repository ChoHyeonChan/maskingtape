"""MCP 서버 진입점 — tools.py의 함수를 MCP 도구로 노출만 한다.

실행: `maskingtape-mcp` (stdio 전송 — MCP 클라이언트가 이 프로세스를 띄운다)
Claude Code 등록 예: `claude mcp add maskingtape -- maskingtape-mcp`
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from maskingtape_mcp import tools

mcp = FastMCP(
    "maskingtape",
    instructions=(
        "한국어 개인정보 비식별화 도구. 이름·전화번호·주민등록번호·이메일 등이 "
        "포함될 수 있는 한국어 텍스트를 외부로 보내거나 저장하기 전에 "
        "anonymize_text로 비식별화하고, 탐지 내역만 필요하면 scan_text를 사용한다."
    ),
)


@mcp.tool()
def scan_text(text: str) -> list[dict]:
    """한국어 텍스트에서 개인정보(주민등록번호·전화번호·이메일 등)를 탐지해
    종류·위치·확신도 리포트를 반환한다."""
    return tools.scan_text(text)


@mcp.tool()
def anonymize_text(text: str, strategy: str = "mask", numbered: bool = False) -> str:
    """한국어 텍스트의 개인정보를 비식별화한다.
    strategy="mask"는 *로 가리고, "label"은 [전화번호] 같은 라벨로 치환한다.
    numbered=True면 label에서 같은 값을 같은 번호로 유지한다([이름1] 등) —
    LLM에 넘길 때 같은 사람·번호를 문맥상 일관되게 추적할 수 있다."""
    return tools.anonymize_text(text, strategy, numbered)


@mcp.tool()
def anonymize_file(path: str, strategy: str = "mask", numbered: bool = False) -> dict:
    """로컬 텍스트 파일(UTF-8)을 비식별화해 `<이름>_masked.<확장자>`로 저장한다.
    파일을 외부로 보내기 전 통째로 가릴 때 쓴다. 입력/출력 경로와
    탐지 종류별 건수 요약을 반환한다. strategy/numbered는 anonymize_text와 동일."""
    return tools.anonymize_file(path, strategy, numbered)


def main() -> None:
    """stdio 전송으로 서버를 시작한다."""
    mcp.run()


if __name__ == "__main__":
    main()
