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


@pytest.mark.parametrize(
    "text",
    [
        "발신: 홍보팀",
        "손해 배상.",
        "정신적 손해 배상!",
        "피고인 진술",
        "피해자 진술서",
        "배우자 공제 대상",
        "투숙객 안내문",
        "정부의 책임이 크다.",
        "오늘자 기사.",
        "주문자 우대 혜택이 있습니다",
    ],
)
def test_review_false_positives_from_new_cues_are_not_names(text):
    assert names(text) == []


def test_form_label_with_a_person_name_still_counts_after_the_org_rule():
    # 대조군: 발신 칸에 사람 이름이 오면 기관 규칙이 막지 않는다
    assert "김민수" in names("발신: 김민수")


@pytest.mark.parametrize(
    "text, name",
    [
        # 기존 직함 앞의 두 글자 이름 + 의·가는 전처럼 이름째 가린다(#603 리뷰 회귀)
        ("담당자 이준의 팀장", "이준"),
        ("이준가 대리로 승진했다", "이준"),
        ("김민의 과장", "김민"),
        ("최한의 부장님", "최한"),
        ("정민가 부장님께 서류를 전달했습니다.", "정민"),
        # 기존 앞 단서가 있으면 #603 직함 앞이어도 전처럼 가린다
        ("고객 김민의 선임", "김민"),
        ("담당자: 이준가 수석으로", "이준"),
        # #603 정지어는 #603 단서 뒤에서만 거른다. 기존 단서 옆이면 전처럼 이름으로 본다
        ("공제 씨", "공제"),
        ("고객 우대", "우대"),
        ("담당자 우대", "우대"),
        ("진술 씨가", "진술"),
    ],
)
def test_names_masked_before_the_review_fix_are_still_masked(text, name):
    start = text.index(name)
    spans = [(d.start, d.end) for d in NameDetector().detect(text)]
    assert any(s <= start and start + len(name) <= e for s, e in spans), spans
