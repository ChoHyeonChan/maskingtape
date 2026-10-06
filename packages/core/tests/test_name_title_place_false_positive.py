# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""성씨 + 직함·지명 어미 오탐 테스트(#677) — 모든 이름과 지명은 합성(가짜)이다.

"김부장님"처럼 성씨 한 글자에 직함이 붙은 꼴은 세 글자 이름이 아니므로 직함을 가리지 않고
성씨 한 글자만 가린다. 그 뒤 나열은 이름과 똑같이 이어받는다.
"김민장"·"박도군"처럼 직함이 아닌 글자로 끝나는 실명은 그대로 이름이다.
끝 글자(시·대·구)만 보고 지명·학교로 버리면 "김민구"·"박정대" 같은 실명이 통째로 새서 그 거르기는 뺐다.
"""

import pytest

from maskingtape.detectors import NameDetector


def detections(text: str):
    return [(d.text, d.start, d.end) for d in NameDetector().detect(text)]


def names(text: str):
    return [d.text for d in NameDetector().detect(text)]


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
    "text, expected",
    [
        ("참석자: 김부장, 이서연, 박지훈", ["김", "이서연", "박지훈"]),
        ("피해자|이상무, 김민수, 박지훈", ["이", "김민수", "박지훈"]),
        ("근로자: 김박사 선수와 장민지/이준!", ["김", "장민지", "이준"]),
        ("송금인 박프로 책임 및 제갈윤/임채원)", ["박", "제갈윤", "임채원"]),
    ],
)
def test_list_after_a_surname_with_a_title_is_still_masked(text, expected):
    # 성씨만 가린 칸도 나열의 출발점이다. 빠지면 뒤 실명이 통째로 샌다
    assert names(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("작성:김민구님,이서연", ["김민구", "이서연"]),
        ("결재|박정대 과장, 이서연", ["박정대", "이서연"]),
        ("대표자: 김민수님, 이서연, 박지훈", ["김민수", "이서연", "박지훈"]),
        ("결재: 김민수 과장, 전결", ["김민수"]),
        ("대표자: 김민수님, 서울 본사", ["김민수"]),
    ],
)
def test_list_after_a_form_value_caught_by_a_suffix_cue_is_masked(text, expected):
    # 양식 라벨 뒤 값을 뒤 단서(님·과장)가 먼저 잡아도 그 값은 뒤 나열의 출발점이다
    assert sorted(names(text)) == sorted(expected)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("고객 김민구님", ["김민구"]),
        ("담당자 이성구 대리", ["이성구"]),
        ("환자 박정대님 내원", ["박정대"]),
        ("고객 최영대님", ["최영대"]),
        ("참석자: 김민구, 이서연", ["김민구", "이서연"]),
    ],
)
def test_real_name_ending_in_a_place_like_syllable_is_still_a_name(text, expected):
    assert names(text) == expected


@pytest.mark.xfail(
    strict=True,
    reason="끝 글자 거르기는 실명(김민구·박정대)을 흘려 뺐다. 지명은 더 가리는 쪽으로 두고 동결 뒤 다시 다룬다(#677)",
)
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
