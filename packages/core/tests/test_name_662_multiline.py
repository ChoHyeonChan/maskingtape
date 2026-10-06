# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""여러 줄 양식에서 다음 줄 라벨을 앞 줄 이름의 뒤 단서로 먹어 다음 줄 이름이 새던 문제(#662).

"참석자: 송준경⏎작성자: 문양석"에서 `작성자`가 앞 줄 `송준경`의 뒤 단서로 소비돼, `문양석`이
앞 단서를 잃고 버려졌다. 빈 줄을 하나 더 넣거나 CRLF면 잡히던 것과 결과가 같아야 한다.
"""

import pytest

from maskingtape.detectors import NameDetector


def _names(text: str) -> list[str]:
    return [text[d.start : d.end] for d in NameDetector().detect(text)]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("참석자: 송준경\n작성자: 문양석", ["송준경", "문양석"]),
        ("성명: 김민수\n담당자: 이서연", ["김민수", "이서연"]),
        ("신청자 김민수\n보호자 이서연", ["김민수", "이서연"]),
        ("참석자 송준경\n신청자 문양석", ["송준경", "문양석"]),
    ],
)
def test_next_line_label_keeps_its_name(text: str, expected: list[str]) -> None:
    assert sorted(_names(text)) == sorted(expected)


def test_two_cell_label_value_rows_are_not_a_table_header() -> None:
    # "성명 | 김민수"를 표 머리행으로 읽어 다음 줄 라벨 칸(담당자)을 이름 값으로 받으면 안 된다
    text = "성명 | 김민수\n담당자 | 이서연"
    got = _names(text)
    assert "담당자" not in got
    assert sorted(got) == ["김민수", "이서연"]


@pytest.mark.parametrize(
    "text",
    [
        "참석자: 송준경\n\n작성자: 문양석",  # 빈 줄
        "참석자: 송준경\r\n작성자: 문양석",  # CRLF
    ],
)
def test_controls_that_already_worked(text: str) -> None:
    assert sorted(_names(text)) == ["문양석", "송준경"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # 다음 줄 첫 낱말이 앞 줄 두 글자 이름의 뒤 단서 노릇을 하던 판결문 머리. 앞 줄 이름은 그대로 잡고,
        # 그 단서는 다음 줄 이름의 앞 단서로도 쓴다(#662 댓글의 회귀 우려).
        ("원고 소송대리인 변호사 한율\n피고 안호지", ["한율", "안호지"]),
        ("원고 소송대리인 변호사 신경\n피고 김경원", ["신경", "김경원"]),
    ],
)
def test_court_header_two_char_name_kept_and_next_line_found(text: str, expected: list[str]) -> None:
    assert sorted(_names(text)) == sorted(expected)


_FIRST_LABELS = ["참석자", "성명", "신청자", "고객", "담당자", "대상자"]
_SECOND_LABELS = ["작성자", "담당자", "신청자", "수령인", "수신인", "보호자", "학생", "환자", "참석자", "성명", "예금주"]


@pytest.mark.parametrize("first", _FIRST_LABELS)
@pytest.mark.parametrize("second", _SECOND_LABELS)
@pytest.mark.parametrize("sep", [": ", " "])
def test_label_grid_both_lines(first: str, second: str, sep: str) -> None:
    # 6 × 11 × 2 = 132조합. main에서는 84조합에서 둘째 줄 이름이 샜다
    text = f"{first}{sep}송준경\n{second}{sep}문양석"
    got = _names(text)
    assert "송준경" in got
    assert "문양석" in got
