# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""PDF에서 글자를 뽑아 표준출력(UTF-8)으로 낸다 — 데스크톱 앱이 PDF 파일을 처리할 때 부른다.

앱은 이 파일을 Flutter 에셋으로 싣고, `python -B -X utf8 - <PDF 경로>`를 띄워 이 코드를 표준입력으로
넘긴다(`lib/services/pdf_text_extractor.dart`). 코드를 `-c` 인자로 넘기지 않는 이유: 여러 줄·따옴표가 든
인자는 Windows 명령줄 인용 규칙을 타서 쉽게 깨진다. 설치판은 동봉 Python에 pypdf를 함께 묶는다
(`installer/build.py`). 개인정보 탐지는 하지 않는다 — 뽑은 글자는 앱이 core CLI에 넘긴다.

PDF에는 문단이 없고 화면의 줄만 있다. 그대로 두면 폭이 차서 꺾인 자리마다 줄이 끊기고(「실제 사」/「람과」),
단어 중간에서 꺾인 이름·이메일은 탐지기가 조각으로 보고 놓친다. 그래서 오른쪽 여백까지 찬 줄과 그 바로 아래
이어지는 줄을 다시 잇는다(`reflow`). 판단이 서지 않으면 원래 줄바꿈을 그대로 둔다.

실패하면 `오류: ...` 한 줄을 표준오류로 내고 코드 1로 끝난다. 앱은 그 문구를 그대로 보여 준다.
pypdf 예외 문구에는 PDF 내용 조각이 담길 수 있어 그대로 내지 않는다.
"""

import logging
import math
import sys
import unicodedata
from dataclasses import dataclass
from itertools import pairwise

# pypdf는 깨진 파일을 만나면 경고 로그에 파일 첫 바이트 같은 내용 조각을 찍는다. 앱은 `오류:` 줄만
# 쓰지만, 내용이 표준오류로 새어 나갈 길 자체를 막는다.
logging.disable(logging.CRITICAL)

# 꺾인 줄 판정 기준 — 모두 그 줄의 글자 크기(em) 배수다.
FULL_LINE_SLACK = 2.5  # 줄 끝이 오른쪽 여백선에서 이만큼 안쪽까지 오면 「찬 줄」
MAX_LINE_GAP = 2.2  # 다음 줄과의 세로 간격이 이보다 크면 문단·표 행이 바뀐 것
MAX_X_SHIFT = 3.0  # 다음 줄 시작 x가 이보다 멀면 다른 단·칸
WORD_BREAK_GAP = 2.5  # 꺾인 줄 끝에 이만큼 이상 여백이 남았으면 띄어쓰기 자리에서 꺾인 것
# 어절 끝에 흔한 조사·어미 — 한글끼리 꺾인 자리에서 줄 끝 글자가 이것이면 띄어쓰기 자리로 본다.
WORD_FINAL = set("은는이가을를의에도와과로고며면다요")
# 낱말 첫 글자로 거의 오지 않는 글자 — 다음 줄이 이것으로 시작하면 단어 중간이다(했|습니다, 4층이|며).
NON_INITIAL = set("습며니했됐됩겠였었았")


def fail(message: str) -> None:
    sys.stderr.write(f"오류: {message}\n")
    sys.exit(1)


def em_width(ch: str) -> float:
    """글자 폭 어림값(em). 맑은 고딕으로 만든 PDF에서 실제 줄 끝과 1% 안쪽으로 맞았다.

    PDF의 글꼴 폭 표를 쓰지 않는 이유: 글꼴을 일부만 내장한 PDF는 글자와 폭이 이어지지 않는 경우가 많다.
    """
    if ch == " ":
        return 0.33
    if unicodedata.east_asian_width(ch) in "WF":
        return 1.0
    if ch.isdigit():
        return 0.55
    if ch.isalpha():
        return 0.65 if ch.isupper() else 0.5
    return 0.33


def is_hangul(ch: str) -> bool:
    return "가" <= ch <= "힣"


@dataclass
class Line:
    text: str = ""
    x0: float | None = None  # 첫 글자 x (페이지 좌표, pt)
    y: float = 0.0
    size: float = 0.0
    end: float = 0.0  # 줄 끝 x 어림값


def page_lines(page) -> tuple[str, list[Line]]:
    """쪽 글자와, 그 글자를 줄로 나눈 목록(줄마다 위치·글자 크기)을 함께 돌려준다."""
    pieces = []

    def visit(text, cm, tm, font_dict, font_size):
        # 글자 행렬 × 현재 변환 행렬 = 페이지 좌표. 크기는 가로 성분의 길이다.
        a = tm[0] * cm[0] + tm[1] * cm[2]
        b = tm[0] * cm[1] + tm[1] * cm[3]
        x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
        y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
        pieces.append((text, x, y, font_size * math.hypot(a, b)))

    text = page.extract_text(visitor_text=visit) or ""
    lines = [Line()]
    for piece, x, y, size in pieces:
        for i, segment in enumerate(piece.split("\n")):
            if i > 0:
                lines.append(Line())
            line = lines[-1]
            line.text += segment
            # 한 조각 안에서 줄이 바뀐 뒤의 글자는 위치를 모른다 — 그 줄은 잇기 대상에서 빠진다.
            if i == 0 and segment.strip() and size > 0:
                if line.x0 is None:
                    line.x0, line.y, line.size = x, y, size
                line.end = max(line.end, x + sum(em_width(c) for c in segment) * size)
    if "\n".join(line.text for line in lines) != text:
        return text, []  # 조각과 결과가 어긋나면 줄을 손대지 않는다
    return text, lines


def wraps(prev: Line, cur: Line, right: float) -> bool:
    """prev가 폭이 차서 꺾였고 cur가 그 뒷부분인가."""
    if prev.x0 is None or cur.x0 is None or not prev.text.strip() or not cur.text.strip():
        return False
    em = prev.size
    return (
        prev.end >= right - FULL_LINE_SLACK * em
        and 0 < prev.y - cur.y <= MAX_LINE_GAP * em
        and abs(cur.size - prev.size) <= 0.15 * em
        and abs(cur.x0 - prev.x0) <= MAX_X_SHIFT * em
    )


def joiner(prev: Line, after: str, right: float) -> str:
    """꺾인 자리를 이을 문자 — 띄어쓰기 자리에서 꺾였으면 공백, 단어 중간이면 빈 문자열.

    PDF에는 꺾인 자리의 공백이 남지 않아(Chrome·Word 모두 그리지 않는다) 어림한다. 한글은 단어 중간에서
    꺾는 설정(글자 단위)도 띄어쓰기 자리에서 꺾는 설정(어절 단위)도 흔하다. 붙여야 단어 중간에서 꺾인
    전화번호·이메일·이름·주소가 탐지되므로, 띄어쓰기 자리라는 단서가 없으면 붙인다.
    - 하이픈 앞뒤, 이메일 중간은 붙인다(010-|2345, 010|-2345, minsu@exam|ple.com).
    - 여백이 WORD_BREAK_GAP보다 많이 남았으면 띄어쓰기 자리다 — 글자 단위로 꺾었다면 다음 글자를 채웠을 것이다.
    - 숫자 뒤 숫자·한글은 붙인다(1234|5678, 4|층).
    - 한글끼리는 다음 줄 첫 글자가 낱말 첫 글자로 안 오는 글자면 붙이고, 줄 끝이 조사·어미면 띄운다.
    """
    if prev.text[-1:].isspace():
        return " "
    a, b = prev.text.rstrip()[-1], after.lstrip()[0]
    if a == "-" or b == "-":
        return ""
    if "@" in prev.text.rsplit(" ", 1)[-1] and (b.isascii() and (b.isalnum() or b in "._-")):
        return ""
    if right - prev.end >= WORD_BREAK_GAP * prev.size:
        return " "
    if a.isdigit() and (b.isdigit() or is_hangul(b)):
        return ""
    if is_hangul(a) and is_hangul(b):
        if b in NON_INITIAL:
            return ""
        return " " if a in WORD_FINAL else ""
    return " "


def reflow(page) -> str:
    text, lines = page_lines(page)
    known = [line for line in lines if line.x0 is not None]
    if not known or page.get("/Rotate", 0) % 360:
        return text
    # 오른쪽 여백선은 왼쪽 여백과 같다고 본다(워드·한글·브라우저 기본값). 다르면 잇지 않고 그대로 둔다.
    right = float(page.mediabox.width) - min(line.x0 for line in known)
    out = [lines[0].text]
    for prev, cur in pairwise(lines):
        if wraps(prev, cur, right):
            out[-1] = out[-1].rstrip() + joiner(prev, cur.text, right) + cur.text.lstrip()
        else:
            out.append(cur.text)
    return "\n".join(out)


def main() -> None:
    try:
        from pypdf import PdfReader
    except ImportError:
        fail("PDF를 읽는 pypdf가 없습니다 — 설치판이면 다시 설치하고, 소스로 실행 중이면 pip install pypdf")

    try:
        reader = PdfReader(sys.argv[1])
    except Exception:  # noqa: BLE001 — 머리말이 없거나 깨진 파일
        fail("PDF를 열지 못했습니다 — 손상됐거나 PDF가 아닌 파일입니다")

    if reader.is_encrypted:
        # 열기 암호 없이 권한만 잠근 PDF는 빈 암호로 풀린다. 열기 암호가 있으면 처리하지 않는다.
        try:
            unlocked = reader.decrypt("")
        except Exception:  # noqa: BLE001 — AES 등 동봉하지 않은 암호 모듈이 필요한 경우
            unlocked = False
        if not unlocked:
            fail("암호가 걸린 PDF는 처리하지 않습니다")

    try:
        pages = [reflow(page) for page in reader.pages]
    except Exception:  # noqa: BLE001
        fail("PDF에서 글자를 뽑지 못했습니다 — 손상됐거나 지원하지 않는 구성입니다")

    # 쪽 사이는 빈 줄 하나로 잇는다. 텍스트 모드 stdout은 Windows에서 \n을 \r\n으로 바꾸므로
    # 바이트로 직접 쓴다. 깨진 ToUnicode가 만든 외톨이 서로게이트는 ?로 바꾼다.
    sys.stdout.buffer.write("\n\n".join(pages).encode("utf-8", "replace"))


if __name__ == "__main__":
    main()
