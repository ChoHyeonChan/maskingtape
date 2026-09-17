# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""소스 파일의 저작권·라이선스 헤더가 빠졌는지 검사한다(#437).

2026년 9월 OpenUP 오픈소스 라이선스 컨설팅 권고에 따라, 우리가 작성한 모든 소스 파일
맨 위에 아래 두 줄을 둔다. 언어마다 주석 기호만 다르다.

    SPDX-FileCopyrightText: 2026 The maskingtape Authors
    SPDX-License-Identifier: Apache-2.0

동작 원리:
1. `git ls-files`로 추적 중인 파일만 본다. 빌드 산출물과 node_modules는 자연히 빠진다.
2. 검사 대상 확장자 파일의 앞 HEAD_LINES줄 안에 저작권 태그와 라이선스 줄이 모두 있는지 본다.
3. 빠진 파일이 있으면 목록과 붙여 넣을 헤더를 출력하고 1로 끝난다. CI는 이것으로 실패한다.

사용: python scripts/check_license_headers.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path, PurePosixPath

COPYRIGHT_TAG = "SPDX-FileCopyrightText:"
COPYRIGHT_HOLDER = "2026 The maskingtape Authors"
LICENSE_LINE = "SPDX-License-Identifier: Apache-2.0"

# 셔뱅, 인코딩 선언, HTML doctype 뒤에 헤더가 와도 되도록 맨 앞 몇 줄을 본다.
HEAD_LINES = 5

# 확장자별 주석 모양(여는 기호, 닫는 기호). 누락 안내에 그대로 보여 준다.
COMMENT_STYLE = {
    ".py": ("# ", ""),
    ".ts": ("// ", ""),
    ".tsx": ("// ", ""),
    ".dart": ("// ", ""),
    ".css": ("/* ", " */"),
    ".html": ("<!-- ", " -->"),
}

# 우리가 작성하지 않은 파일. apps/desktop/windows/는 `flutter create`가 만든 플랫폼 템플릿이다.
EXCLUDED_PREFIXES = ("apps/desktop/windows/",)

REPO_ROOT = Path(__file__).resolve().parent.parent


def is_target(path: str) -> bool:
    """검사 대상인지 판정한다. path는 git이 주는 저장소 기준 경로('/' 구분)다."""
    return PurePosixPath(path).suffix in COMMENT_STYLE and not path.startswith(EXCLUDED_PREFIXES)


def has_header(text: str) -> bool:
    """맨 앞 HEAD_LINES줄 안에 저작권 태그와 Apache-2.0 라이선스 줄이 모두 있으면 True."""
    head = text.splitlines()[:HEAD_LINES]
    has_copyright = any(COPYRIGHT_TAG in line for line in head)
    has_license = any(LICENSE_LINE in line for line in head)
    return has_copyright and has_license


def expected_header(suffix: str) -> str:
    """헤더가 빠진 파일에 붙여 넣을 두 줄을 확장자에 맞는 주석으로 만든다."""
    start, end = COMMENT_STYLE[suffix]
    return (
        f"{start}{COPYRIGHT_TAG} {COPYRIGHT_HOLDER}{end}\n"
        f"{start}{LICENSE_LINE}{end}"
    )


def tracked_files(root: Path) -> list[str]:
    """git이 추적하는 파일 목록. -z를 써서 한글 경로도 따옴표 없이 그대로 받는다."""
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True
    )
    return [path for path in result.stdout.decode("utf-8").split("\0") if path]


def find_missing(root: Path) -> list[str]:
    """헤더가 빠진 대상 파일의 경로 목록을 돌려준다."""
    missing = []
    for rel in tracked_files(root):
        if not is_target(rel):
            continue
        path = root / rel
        if not path.is_file():
            continue  # 작업 트리에서 지웠지만 아직 커밋하지 않은 파일
        if not has_header(path.read_text(encoding="utf-8", errors="replace")):
            missing.append(rel)
    return missing


def main() -> int:
    # Windows 콘솔(cp949)에서 안내 문구 때문에 죽지 않게 한다.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")

    missing = find_missing(REPO_ROOT)
    if not missing:
        print("라이선스 헤더: 모든 대상 파일에 있음")
        return 0

    print(f"라이선스 헤더가 빠진 파일 {len(missing)}개:", file=sys.stderr)
    for rel in missing:
        print(f"  {rel}", file=sys.stderr)
    print("\n파일 맨 위에 아래 두 줄을 넣으세요 (CONTRIBUTING.md 「라이선스 규칙」).", file=sys.stderr)
    for suffix in sorted({PurePosixPath(rel).suffix for rel in missing}):
        print(f"\n[{suffix}]\n{expected_header(suffix)}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
