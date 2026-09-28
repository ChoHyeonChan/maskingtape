# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""탐지 전에 입력 표기를 정리하고, 정리한 위치를 원문 위치로 되돌린다(#490).

눈에 같은 글자라도 다른 코드로 들어오면 규칙 탐지기가 놓친다. 전각 숫자
(`８００１０１-…`), 폭 없는 공백(U+200B)이 끼인 번호, 빼기 기호(U+2212)나 en-dash로
나눈 번호, 취소선 결합 부호가 얹힌 숫자, 자모로 분해된 한글(NFD)이 그렇다. 놓치면
그 자체로 유출이라, 탐지를 정리한 문자열에서도 하고 가리는 위치는 원문 기준으로
되돌린다. 원문은 바꾸지 않는다.

    - 하이픈 역할 문자(en-dash·em-dash·U+2212·한글 입력의 ㅡ 등) → `-`
    - 폭 있는 공백(NBSP·전각 공백, SNS에서 공백 대신 쓰는 한글 채움 문자 U+3164 등) → ` `
    - 전각 ASCII(U+FF01~FF5E) → ASCII, ASCII가 아닌 십진 숫자 → ASCII 숫자
    - 보이지 않는 문자(U+200B·U+FEFF·U+00AD·변형 선택자 등)와
      라틴·기호용 결합 부호(U+0300~036F·U+20D0~20FF 등: 취소선·밑줄·키캡) → 지운다
    - 자모로 분해된 한글 → 음절로 합친다(NFC)

NFKC를 통째로 쓰지는 않는다. `①`·`²`가 숫자가 되고 `㈜`가 `(주)`가 되는 식으로 글자가
바뀌면 오탐이 늘고, 로컬 LLM에 가는 문장도 원문과 멀어진다.
"""

from __future__ import annotations

import re
import unicodedata
from array import array
from collections.abc import Sequence
from dataclasses import dataclass, replace

from maskingtape.types import Detection

_DASHES = (
    "\u2010\u2011\u2012\u2013\u2014\u2015\u2212\ufe58\ufe63\uff0d"
    "\u3161\u2043\u02d7\u30fc\u2500"
)
_SPACES = "\u00a0\u1680\u2000-\u200a\u202f\u205f\u3000\u2800\u3164\uffa0"
# 지우는 문자: 보이지 않는 서식 문자·변형 선택자·태그 문자, 그리고
# 라틴·기호용 결합 부호. 다른 문자 체계의 결합 문자(한글 자모 제외)는 건드리지 않는다.
_DROP = (
    "\u00ad\u061c\u115f\u1160\u180b-\u180f\u200b-\u200f\u202a-\u202e\u2060-\u2064"
    "\u2066-\u206f\ufe00-\ufe0f\ufeff"
    "\u0300-\u036f\u1ab0-\u1aff\u1dc0-\u1dff\u20d0-\u20ff\ufe20-\ufe2f"
    "\U0001bca0-\U0001bca3\U0001d173-\U0001d17a\U000e0000-\U000e0fff"
)
_JAMO = "\u1100-\u11ff\ua960-\ua97f\ud7b0-\ud7ff"

# 한 글자를 한 글자로 바꾸는 대상. (?![0-9])\d는 ASCII가 아닌 십진 숫자다.
_SAME_LENGTH_RE = re.compile("[" + _DASHES + _SPACES + "\uff01-\uff5e]|" + r"(?![0-9])\d")
_DROP_RE = re.compile("[" + _DROP + "]")
# 글자 수가 바뀌는 정리(지우기·자모 합치기)가 필요한 입력인지 선형으로 판정한다.
_NEEDS_MAP_RE = re.compile("[" + _DROP + _JAMO + "]")
# 글자 자체가 바뀌는 정리인지(자모를 합치거나 라틴 결합 부호를 지움). 보이지 않는 문자만
# 지우는 정리는 글자가 그대로라 로컬 LLM을 정리본에서 한 번만 돌려도 된다(pipeline.scan).
_LETTERS_CHANGE_RE = re.compile(
    "[" + _JAMO + "\u0300-\u036f\u1ab0-\u1aff\u1dc0-\u1dff\ufe20-\ufe2f]"
)


def _replace_one(char: str) -> str:
    """한 글자를 정리한 글자로 바꾼다. 지우는 문자는 빈 문자열이 된다."""
    if char.isascii() or "가" <= char <= "힣":
        return char
    if _DROP_RE.match(char):
        return ""
    if not _SAME_LENGTH_RE.match(char):
        return char
    if char in _DASHES:
        return "-"
    if 0xFF01 <= ord(char) <= 0xFF5E:
        return chr(ord(char) - 0xFEE0)
    if unicodedata.category(char) == "Nd":
        return str(unicodedata.decimal(char))
    return " "


def _continues_cluster(char: str) -> bool:
    """앞 글자와 한 묶음으로 볼 글자인가(한글 중성·종성 자모, 지우는 문자)."""
    code = ord(char)
    return 0x1160 <= code <= 0x11FF or 0xD7B0 <= code <= 0xD7FF or _DROP_RE.match(char) is not None


@dataclass(frozen=True, eq=False)
class NormalizedText:
    """탐지용 문자열과, 그 위치를 원문 위치로 되돌리는 대응표.

    starts[i]·ends[i]는 text[i]가 온 원문 구간이다. 위치가 원문과 같으면 둘 다 None이다.
    letters_changed는 자모 합치기·결합 부호 삭제로 글자 자체가 바뀌었는지다.
    """

    original: str
    text: str
    starts: Sequence[int] | None = None
    ends: Sequence[int] | None = None
    letters_changed: bool = False

    def restore(self, detection: Detection) -> Detection:
        """탐지용 문자열 기준 탐지를 원문 기준으로 되돌린다. text도 원문 조각으로 바꾼다."""
        start, end = self._to_original(detection.start, detection.end)
        return replace(detection, start=start, end=end, text=self.original[start:end])

    def _to_original(self, start: int, end: int) -> tuple[int, int]:
        if self.starts is None or self.ends is None:
            return start, end
        if start >= end:
            position = self.starts[start] if start < len(self.starts) else len(self.original)
            return position, position
        return self.starts[start], self.ends[end - 1]


def _same_length(text: str) -> str:
    """한 글자를 한 글자로만 바꾸는 정리. 위치가 원문과 같다."""
    return _SAME_LENGTH_RE.sub(lambda m: _replace_one(m.group()), text)


def normalize(text: str) -> NormalizedText:
    """탐지용으로 정리한 문자열과 원문 위치 대응표를 만든다."""
    if text.isascii():
        return NormalizedText(original=text, text=text)
    if not _NEEDS_MAP_RE.search(text):
        return NormalizedText(original=text, text=_same_length(text))
    return _normalize_with_map(text)


def _normalize_with_map(text: str) -> NormalizedText:
    """글자 수가 바뀌는 정리(문자 지우기, 자모 합치기)를 하면서 대응표를 만든다.

    지우거나 합칠 문자가 있는 자리만 앞 글자와 묶어 정리하고, 결과 글자 전부를 그 묶음의
    원문 구간에 대응시킨다. 위치는 묶음 경계에서만 넓어지므로 되돌린 구간이 원문을 덜 덮는
    일은 없다. 그 사이의 평범한 구간은 한 글자씩 대응하므로 통째로 옮긴다 — 긴 문서에 특수
    문자가 하나만 있어도 문서 전체를 한 글자씩 도는 비용을 피한다.
    """
    pieces: list[str] = []
    # 대응표는 글자 수만큼 길다. 파이썬 정수 리스트는 글자당 70바이트 넘게 들어 큰 문서에서 메모리가
    # 몇 배로 늘므로(100만 자에 약 75MB), 8바이트 정수 배열에 담는다.
    starts = array("q")
    ends = array("q")

    def add_plain(a: int, b: int) -> None:
        pieces.append(_same_length(text[a:b]))
        starts.extend(range(a, b))
        ends.extend(range(a + 1, b + 1))

    n, done = len(text), 0
    for m in _NEEDS_MAP_RE.finditer(text):
        k = m.start()
        if k < done:
            continue  # 앞 묶음에 이미 들어간 문자
        # 앞 글자에 이어지는 문자(중성·종성 자모, 지우는 문자)면 묶음은 앞 글자부터다
        i = k - 1 if k > done and _continues_cluster(text[k]) else k
        add_plain(done, i)
        j = i + 1
        while j < n and _continues_cluster(text[j]):
            j += 1
        piece = "".join(_replace_one(c) for c in text[i:j])
        if len(piece) > 1:
            piece = unicodedata.normalize("NFC", piece)
        pieces.append(piece)
        starts.extend([i] * len(piece))
        ends.extend([j] * len(piece))
        done = j
    add_plain(done, n)
    return NormalizedText(
        original=text,
        text="".join(pieces),
        starts=starts,
        ends=ends,
        letters_changed=_LETTERS_CHANGE_RE.search(text) is not None,
    )
