# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""성씨 + 직함·지명 어미 오탐 테스트(#677) — 모든 이름과 지명은 합성(가짜)이다.

"김부장님"처럼 성씨 한 글자에 직함이 붙은 꼴은 세 글자 이름이 아니므로 직함을 가리지 않고
성씨 한 글자만 가린다. "김포시"·"김포대"처럼 지명·학교 어미로 끝나는 세 글자는 이름이 아니다.
"김민장"·"박도군"처럼 직함이 아닌 글자로 끝나는 실명은 그대로 이름이다.
"""

import pytest

from maskingtape.detectors import NameDetector


def detections(text: str):
    return [(d.text, d.start, d.end) for d in NameDetector().detect(text)]


@pytest.mark.parametrize(
    "text, surname_index",
    [
        ("고객 김부장님 확인 부탁드립니다.", 3),
        ("담당자 김과장님께 전달했습니다.", 4),
        ("고객 박사장님이 오셨습니다.", 3),
        ("신청자 이대리 확인", 4),
    ],
)
def test_surname_with_a_title_masks_only_the_surname(text, surname_index):
    found = detections(text)
    assert len(found) == 1
    surname, start, end = found[0]
    assert surname == text[surname_index]
    assert (start, end) == (surname_index, surname_index + 1)


@pytest.mark.parametrize(
    "text",
    [
        "담당자 김포시 문의",
        "담당자 김포대 학생",
    ],
)
def test_surname_with_a_place_or_school_ending_is_not_a_name(text):
    assert detections(text) == []


def test_real_name_ending_in_a_title_like_syllable_is_still_a_name():
    # 직함 낱말로 끝나지만 직함이 성씨 뒤에 바로 붙은 꼴이 아닌 실명은 그대로 이름이다
    assert "김민장" in [name for name, _, _ in detections("담당자 김민장 확인")]


def test_real_name_ending_in_gun_is_still_a_name():
    assert "박도군" in [name for name, _, _ in detections("환자 박도군 내원 예정")]
