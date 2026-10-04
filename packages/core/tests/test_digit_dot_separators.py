# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""숫자 사이 점 닮은꼴 구분자 테스트(#636·#639). 모든 번호는 합성(가짜)이다.

가운뎃점(·)과 눈으로 구분이 안 되는 점 문자로 번호를 나누면 전화·계좌·카드·운전면허·
사업자등록번호가 통째로 샜다. 탐지기마다 구분자를 넓히는 대신 입력 정규화에서 숫자 사이의
점 닮은꼴을 하이픈으로 읽은 글을 따로 만들어 규칙 탐지기로 한 번 더 훑는다. 숫자 사이만 바꾸므로
"서울·경기"처럼 낱말을 잇는 가운뎃점은 그대로다.
"""

import unicodedata

import pytest

from maskingtape import Pipeline
from maskingtape.detectors import Detector
from maskingtape.normalize import normalize
from maskingtape.types import Detection

# 숫자 사이에서 하이픈으로 읽는 점 닮은꼴(코드값으로 적는다. 눈으로는 서로 구분이 안 된다)
DOT_LIKES = [
    0x00B7, 0x0387, 0x318D, 0x2027,  # 가운뎃점, 그리스 아노 텔레이아, 아래아 자모, 하이픈 점
    0x30FB, 0xFF65, 0x2022, 0x2219, 0x22C5, 0x2024, 0xFE52, 0x2981, 0x25CF, 0x00B8, 0x02D9,  # #631
    0x119E, 0x25E6, 0x3002, 0x2E31, 0xA78F, 0x00B0,  # #639
]

# (텍스트 틀, 가려야 할 값 틀, 종류) — {s} 자리에 구분자가 들어간다
NUMBERS = [
    ("휴대폰 {v}", "010{s}1234{s}5678", "phone"),
    ("전화 {v}", "02{s}555{s}1234", "phone"),
    ("계좌 {v}", "110{s}123{s}456789", "account"),
    ("카드 {v}", "4111{s}1111{s}1111{s}1111", "card"),
    ("면허 {v}", "11{s}12{s}123456{s}12", "driver_license"),
    ("사업자등록번호 {v}", "123{s}45{s}67891", "biz_reg"),
    ("주민번호 {v}", "800101{s}1234560", "rrn"),
    ("생년월일 {v}", "1980{s}01{s}01", "birth_date"),
]


def scan(text: str) -> list[tuple[str, str]]:
    return [(d.kind, text[d.start : d.end]) for d in Pipeline().scan(text)]


@pytest.mark.parametrize("code", DOT_LIKES, ids=lambda c: f"U+{c:04X}")
@pytest.mark.parametrize("template, value, kind", NUMBERS, ids=[n[2] + str(i) for i, n in enumerate(NUMBERS)])
def test_numbers_split_by_dot_likes_are_masked_whole(template, value, kind, code):
    v = value.format(s=chr(code))
    text = template.format(v=v)
    # 번호 전체를 같은 종류 하나로 잡는다(하이픈으로 쓴 같은 번호와 같다)
    assert scan(text) == [(kind, v)], (text, scan(text))
    start = text.index(v)
    assert Pipeline().anonymize(text).text[start:] == "*" * len(v)


@pytest.mark.parametrize("sep", [" · ", "· ", " ·", " • "])
def test_dot_with_a_space_around_is_read_like_a_spaced_hyphen(sep):
    # "010 - 1234 - 5678"을 이미 잡으므로 같은 꼴의 점도 잡는다
    v = f"010{sep}1234{sep}5678"
    assert scan(f"연락처 {v}") == [("phone", v)]


def test_hyphenated_text_turns_only_dots_between_digits_into_hyphens():
    raw = "서울·경기 지역, 연락처 010·1234·5678, 김민수·이서연"
    prepared = normalize(raw)
    # 정리본은 그대로 두고, 하이픈으로 읽은 글을 따로 만든다
    assert prepared.text == raw
    assert prepared.hyphenated == "서울·경기 지역, 연락처 010-1234-5678, 김민수·이서연"
    assert len(prepared.hyphenated) == len(raw)  # 한 글자를 한 글자로 바꿔 위치가 그대로다


@pytest.mark.parametrize(
    "raw",
    ["A·B", "가·1", "1·가", "36.5°C", "● 1번 항목", "1 ·· 2", "1.5·", "서울·경기"],
)
def test_dots_not_between_digits_are_left_alone(raw):
    prepared = normalize(raw)
    assert prepared.text == raw
    assert prepared.hyphenated is None


EN_DASH, HANGUL_DASH, THIN_SPACE, FILLER, DOT = chr(0x2013), chr(0x3161), chr(0x2009), chr(0x3164), chr(0xB7)


def fullwidth_digits(text: str) -> str:
    return "".join(chr(ord(c) + 0xFEE0) if c.isdigit() else c for c in text)


def nfd(text: str) -> str:
    return unicodedata.normalize("NFD", text)


@pytest.mark.parametrize(
    "text, value",
    [
        # 정리본에서만 찾던 번호(대시 변형·전각 숫자·얇은 공백·자모 분해 라벨) 바로 옆에 "숫자·숫자"가
        # 붙은 꼴. 정리본의 점까지 하이픈으로 바꾸면 하이픈이 번호에 들러붙어 운전면허·계좌·생년월일·
        # 주소 탐지기가 놓쳤다(독립 검증에서 찾은 회귀). 정리본은 그대로 두므로 main처럼 가린다.
        ("면허 11" + EN_DASH + "12" + EN_DASH + "123456" + EN_DASH + "12" + DOT + "1종보통",
         "11" + EN_DASH + "12" + EN_DASH + "123456" + EN_DASH + "12"),
        ("운전면허 " + fullwidth_digits("11-12-123456-12") + DOT + "2종보통", fullwidth_digits("11-12-123456-12")),
        ("면허 2024" + DOT + "11" + HANGUL_DASH + "12" + HANGUL_DASH + "123456" + HANGUL_DASH + "12",
         "11" + HANGUL_DASH + "12" + HANGUL_DASH + "123456" + HANGUL_DASH + "12"),
        ("입금계좌 110" + EN_DASH + "123" + EN_DASH + "456789" + DOT + "1002" + EN_DASH + "345" + EN_DASH + "678901",
         "110" + EN_DASH + "123" + EN_DASH + "456789"),
        (nfd("입금계좌") + ": 3333-01-1234567" + DOT + "2024.10.03", "3333-01-1234567"),
        ("계좌 110" + THIN_SPACE + "123" + THIN_SPACE + "456789" + DOT + "50000원",
         "110" + THIN_SPACE + "123" + THIN_SPACE + "456789"),
        (nfd("생년월일") + " 19800101" + DOT + "19820202", "19800101"),
        (nfd("서울특별시 강남구 역삼동") + " 123-4" + DOT + "123-5번지", "123-4"),
        ("서울특별시" + FILLER + "강남구" + FILLER + "테헤란로" + FILLER + "123" + DOT + "010-1234-5678",
         "테헤란로" + FILLER + "123"),
    ],
)
def test_numbers_found_only_in_the_cleaned_text_are_still_masked_next_to_digit_dots(text, value):
    start = text.index(value)
    masked = Pipeline().anonymize(text).text
    assert masked[start : start + len(value)] == "*" * len(value), masked


class _SeeingDetector(Detector):
    kind = "name"

    def __init__(self, calls_model: bool) -> None:
        self.calls_model = calls_model
        self.seen: list[str] = []

    def detect(self, text: str) -> list[Detection]:
        self.seen.append(text)
        return []


def test_only_rule_detectors_read_the_hyphenated_text():
    # 로컬 LLM에 가는 문장은 그대로다 — 번호 표기는 이름 판단에 쓸모가 없다
    model, rule = _SeeingDetector(calls_model=True), _SeeingDetector(calls_model=False)
    Pipeline(detectors=[model, rule]).scan("3·1절에 김민수 씨가")
    assert model.seen == ["3·1절에 김민수 씨가"]
    assert rule.seen == ["3·1절에 김민수 씨가", "3-1절에 김민수 씨가"]


def test_dot_next_to_removed_characters_is_still_read():
    # 폭 없는 공백이 끼면 정규화가 글자 수를 바꾸는 길로 간다 — 그 길에서도 숫자 사이로 본다
    v = "010" + chr(0x200B) + "·1234·5678"
    assert scan(f"전화 {v}") == [("phone", v)]


@pytest.mark.parametrize(
    "text",
    [
        "3·1절 기념식",
        "6·25 전쟁과 4·19 혁명",
        "2019·2020·2021년 실적",
        "1·2·3위 시상",
        "10·20·30대 고객",
        "제3·4조에 따라",
        "체온 36°5 측정",
    ],
)
def test_digit_lists_and_event_names_are_not_detected(text):
    assert scan(text) == []
