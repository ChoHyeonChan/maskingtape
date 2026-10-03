# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""이름 단서 어휘 누락 테스트(#603) — 모든 이름은 합성(가짜)이다.

문서·배송·법률 역할어, 이름 뒤 직함(책임·선임·수석), 편지 맺음말(귀하·드림·올림) 옆 이름이
통째로 새던 문제를 다룬다. 쌍점이 있어야만 받는 양식 라벨(작성·서명·참조 등)과 줄 끝에서만
받는 맺음말은 일반 문장에서 오탐하지 않는지도 함께 본다.
"""

import pytest

from maskingtape.detectors import NameDetector


def names(text: str) -> list[str]:
    return [d.text for d in NameDetector().detect(text)]


@pytest.mark.parametrize(
    "text, name",
    [
        ("주문자 김민수", "김민수"),
        ("구매자: 김민수", "김민수"),
        ("예약자 김민수", "김민수"),
        ("투숙객 김민수", "김민수"),
        ("받는사람: 김민수", "김민수"),
        ("받는 분: 한지민", "한지민"),
        ("보내는 사람 정유진", "정유진"),
        ("피고인 김철수는", "김철수"),
        ("채무자 김민수", "김민수"),
        ("피해자 김민수", "김민수"),
        ("신고인 김민수", "김민수"),
        ("세대주 김민수", "김민수"),
        ("배우자 김민수", "김민수"),
        ("소유자 김민수", "김민수"),
        ("운전자 김민수", "김민수"),
        ("검토자 김민수", "김민수"),
        ("승인자: 이서연", "이서연"),
        ("기안자 김민수", "김민수"),
    ],
)
def test_role_word_before_a_name_is_a_cue(text, name):
    assert name in names(text)


@pytest.mark.parametrize(
    "text, name",
    [
        ("서명: 최동훈 (인)", "최동훈"),
        ("작성: 이서연", "이서연"),
        ("발신: 김민수", "김민수"),
        ("수신: 김영수 귀하", "김영수"),
        ("참조: 박지훈", "박지훈"),
        ("결재: 박지훈", "박지훈"),
    ],
)
def test_form_label_with_a_colon_is_a_cue(text, name):
    assert name in names(text)


@pytest.mark.parametrize(
    "text, name",
    [
        ("김민수 책임님", "김민수"),
        ("김민수 선임", "김민수"),
        ("박지훈 수석님께", "박지훈"),
        ("김민수 박사", "김민수"),
        ("김민수 여사", "김민수"),
        ("김민수 어르신", "김민수"),
    ],
)
def test_title_after_a_name_is_a_cue(text, name):
    assert name in names(text)


@pytest.mark.parametrize(
    "text, name",
    [
        ("김영수 드림", "김영수"),
        ("홍길동 올림", "홍길동"),
        ("김영수 귀하\n", "김영수"),
        ("홍길동 배상.", "홍길동"),
    ],
)
def test_closing_term_at_line_end_or_before_punctuation_is_a_cue(text, name):
    assert name in names(text)


@pytest.mark.parametrize(
    "text",
    [
        "작성 완료되었습니다",
        "서명 요청이 왔습니다",
        "결재 완료 후 발송",
        "참조 문서를 확인하세요",
        "책임 있는 자세가 중요합니다",
        "박사 논문 준비 중입니다",
        "원고 작성 요령",
        "김영수 드림 행사 안내",
    ],
)
def test_ordinary_sentences_with_the_new_words_are_not_names(text):
    assert names(text) == []


@pytest.mark.parametrize(
    "text, name",
    [
        ("김민수 프로", "김민수"),
        ("김민수 기사님", "김민수"),
        ("박지훈 선수가", "박지훈"),
        ("최현진 선수", "최현진"),
    ],
)
def test_short_title_after_a_three_syllable_name_is_a_cue(text, name):
    assert name in names(text)


@pytest.mark.parametrize(
    "text",
    [
        "정보화 프로젝트 일정",
        "기사 작성 요령",
        "정보 선수단 소집",
    ],
)
def test_short_title_inside_a_longer_word_is_not_a_cue(text):
    assert names(text) == []
