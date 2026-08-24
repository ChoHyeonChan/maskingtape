# SPDX-License-Identifier: Apache-2.0

"""파일 입출력 안전장치 — MCP 도구 전용.

MCP 도구는 **AI 에이전트가 호출**한다. 에이전트는 사용자가 준 문서나 웹 내용에 영향을
받을 수 있으므로(프롬프트 인젝션), 도구 쪽에서 파일 접근을 좁게 잡아 둔다.

막는 것:
1. **작업 디렉터리 밖 경로** — 조작된 에이전트가 `~/.ssh/id_rsa` 같은 임의 경로를 넘겨
   민감 파일을 읽거나 사본을 만들지 못하도록, 허용 루트(기본=서버 작업 디렉터리,
   환경변수 `MASKINGTAPE_MCP_ROOT`로 재정의) 안으로만 읽기·쓰기를 허용한다. 경로는
   `resolve()`로 `..`·심볼릭을 정규화한 뒤 검사해 우회를 막는다.
2. **심볼릭 링크** — `문서.txt`가 실은 `~/.ssh/id_rsa`를 가리킬 수 있다. 읽기·쓰기 모두 거부.
3. **덮어쓰기** — 결과 파일이 이미 있으면 배타 생성(`x` 모드)으로 실패시킨다.
   존재 확인 후 쓰기 사이의 경합(TOCTOU)에도 기존 파일이 날아가지 않는다.
4. **거대 파일** — 상한을 넘으면 읽지 않는다(메모리 고갈 방지).
5. **바이너리·비UTF-8** — 조용히 깨진 결과를 저장하지 않고 명확히 실패한다.
"""

from __future__ import annotations

import os
from pathlib import Path

MAX_FILE_BYTES = 10 * 1024 * 1024  # 10MB


def _allowed_root(root: Path | None) -> Path:
    """파일 접근을 허용하는 루트 디렉터리(정규화된 절대경로).

    기본은 서버의 작업 디렉터리(cwd), 환경변수 `MASKINGTAPE_MCP_ROOT`로 재정의한다.
    테스트는 root 인자를 직접 넘겨 임시 디렉터리로 좁힌다.
    """
    if root is not None:
        return root.resolve()
    return Path(os.environ.get("MASKINGTAPE_MCP_ROOT") or Path.cwd()).resolve()


def _ensure_within_root(path: Path, root: Path | None) -> None:
    """path(정규화 후)가 허용 루트 안에 있는지 검증한다 — 밖이면 거부.

    resolve()로 `..`·심볼릭을 정규화한 뒤 검사하므로 경로 조작 우회를 막는다.
    """
    base = _allowed_root(root)
    if not path.resolve().is_relative_to(base):
        raise ValueError(
            f"허용된 작업 디렉터리 밖의 경로는 처리하지 않습니다: {path} "
            f"(MASKINGTAPE_MCP_ROOT로 허용 범위를 지정할 수 있습니다)"
        )


def read_text_file(
    path: str, max_bytes: int = MAX_FILE_BYTES, root: Path | None = None
) -> tuple[Path, str]:
    """검증을 통과한 텍스트 파일을 읽어 (경로, 내용)을 돌려준다."""
    src = Path(path)

    # is_file()은 링크를 따라가므로 링크 검사를 먼저 한다
    if src.is_symlink():
        raise ValueError(f"심볼릭 링크는 처리하지 않습니다(실제 대상이 무엇인지 보장할 수 없음): {path}")
    # 허용 루트 밖(임의 경로)이면 거부 — 부모 심볼릭·`..` 우회는 resolve()로 정규화해 막는다
    _ensure_within_root(src, root)
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


def write_masked_copy(src: Path, text: str, root: Path | None = None) -> Path:
    """`<이름>_masked.<확장자>`로 저장한다. 이미 있으면 덮어쓰지 않고 실패한다."""
    dst = src.with_name(f"{src.stem}_masked{src.suffix}")

    # 출력도 허용 루트 안이어야 한다(입력이 루트 안이면 사본도 같은 폴더라 통상 안전하나 방어적으로 검사)
    _ensure_within_root(dst, root)
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
