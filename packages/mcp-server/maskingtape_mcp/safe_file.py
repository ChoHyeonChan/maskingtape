"""파일 입출력 안전장치 — MCP 도구 전용.

MCP 도구는 **AI 에이전트가 호출**한다. 에이전트는 사용자가 준 문서나 웹 내용에 영향을
받을 수 있으므로(프롬프트 인젝션), 도구 쪽에서 파일 접근을 좁게 잡아 둔다.

막는 것:
1. **심볼릭 링크** — `문서.txt`가 실은 `~/.ssh/id_rsa`를 가리킬 수 있다. 읽기·쓰기 모두 거부.
2. **덮어쓰기** — 결과 파일이 이미 있으면 배타 생성(`x` 모드)으로 실패시킨다.
   존재 확인 후 쓰기 사이의 경합(TOCTOU)에도 기존 파일이 날아가지 않는다.
3. **거대 파일** — 상한을 넘으면 읽지 않는다(메모리 고갈 방지).
4. **바이너리·비UTF-8** — 조용히 깨진 결과를 저장하지 않고 명확히 실패한다.
"""

from __future__ import annotations

from pathlib import Path

MAX_FILE_BYTES = 10 * 1024 * 1024  # 10MB


def read_text_file(path: str, max_bytes: int = MAX_FILE_BYTES) -> tuple[Path, str]:
    """검증을 통과한 텍스트 파일을 읽어 (경로, 내용)을 돌려준다."""
    src = Path(path)

    # is_file()은 링크를 따라가므로 링크 검사를 먼저 한다
    if src.is_symlink():
        raise ValueError(f"심볼릭 링크는 처리하지 않습니다(실제 대상이 무엇인지 보장할 수 없음): {path}")
    if not src.is_file():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

    size = src.stat().st_size
    if size > max_bytes:
        raise ValueError(f"파일이 너무 큽니다({size} bytes, 상한 {max_bytes} bytes)")

    try:
        return src, src.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"UTF-8로 읽을 수 없는 파일입니다: {path} (텍스트 파일인지, 인코딩이 UTF-8인지 확인하세요)"
        ) from exc


def write_masked_copy(src: Path, text: str) -> Path:
    """`<이름>_masked.<확장자>`로 저장한다. 이미 있으면 덮어쓰지 않고 실패한다."""
    dst = src.with_name(f"{src.stem}_masked{src.suffix}")

    if dst.is_symlink():
        raise ValueError(f"출력 경로가 심볼릭 링크입니다(덮어쓰기 위험): {dst}")

    try:
        # "x" = 배타 생성. 이미 있으면 FileExistsError — 존재 확인과 쓰기 사이의 경합에도 안전하다.
        with open(dst, "x", encoding="utf-8") as file:
            file.write(text)
    except FileExistsError as exc:
        raise FileExistsError(
            f"결과 파일이 이미 있어 덮어쓰지 않았습니다: {dst} (기존 파일을 옮기거나 지운 뒤 다시 실행하세요)"
        ) from exc

    return dst
