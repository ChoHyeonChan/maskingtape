# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""주소 조각 사이 여러 칸 공백·구로 시작하는 주소(#492) 테스트 — 모든 주소는 합성 예시다."""

import pytest

from maskingtape import Pipeline
from maskingtape.detectors import AddressDetector

TAB, LF, CR, NBSP, IDEO_SPACE = chr(9), chr(10), chr(13), chr(0xA0), chr(0x3000)


def assert_masked(text: str, value: str) -> None:
    start = text.index(value)
    end = start + len(value)
    masked = Pipeline().anonymize(text).text
    assert masked[start:end] == "*" * (end - start), masked


# ── 조각 사이 여러 칸 공백 ──────────────────────────────────────────


@pytest.mark.parametrize(
    "value",
    [
        "서울특별시  강남구  테헤란로  123",  # 조각마다 두 칸
        "서울특별시 강남구 테헤란로  123",  # 번지 앞만 두 칸
        "서울특별시   강남구 역삼동    123-4",  # 세 칸·네 칸
        "성남시  분당구 정자동 45-6",  # 시/도 없이 시로 시작
        "서울  강남구  테헤란로 123",  # 축약형
        "서울특별시" + TAB + "강남구" + TAB + "테헤란로" + TAB + "123",
        "서울특별시" + TAB + TAB + "강남구 테헤란로 123",
        "경기도 성남시  분당구 판교로 456,  101동  1203호",  # 건물 동·호까지
        "서울특별시 강남구" + CR + LF + "테헤란로 123 101동 1203호",  # 윈도 줄바꿈
        "서울특별시 강남구 " + LF + "테헤란로 123",  # 공백 + 줄바꿈
        "서울특별시 강남구" + LF + "  테헤란로 123",  # 줄바꿈 + 들여쓰기
    ],
)
def test_wide_spaces_between_address_parts(value):
    assert_masked("주소: " + value + " 입니다", value)


def test_n_ga_dong_followed_by_a_road():
    # "종로1가" 같은 N가 동 뒤에 도로명·번지가 오면 도로명부터 새던 표기(#66형 부분 유출)
    value = "서울특별시 종로구 종로1가 새솔로 12 101동 1203호"
    assert_masked("주소: " + value, value)


def test_wide_spaces_keep_positions_in_the_original():
    text = "주소 서울특별시  강남구  테헤란로  123 연락처 없음"
    [found] = AddressDetector().detect(text)
    assert text[found.start : found.end] == found.text == "서울특별시  강남구  테헤란로  123"


def test_positions_after_many_collapsed_spaces():
    # 줄일 자리가 여러 번 나온 뒤의 주소도 원문 위치로 정확히 되돌린다(경계만 저장하고 이진 탐색)
    crlf = CR + LF
    lines = [
        "이름  홍길동",
        "주소  서울특별시  강남구",
        "테헤란로  123",
        "",
        "배송지:   부산광역시 해운대구  우동  1408-1",
    ]
    text = crlf.join(lines + ["비고 없음"])
    expected = ["서울특별시  강남구" + crlf + "테헤란로  123", "부산광역시 해운대구  우동  1408-1"]
    found = AddressDetector().detect(text)
    assert [text[d.start : d.end] for d in found] == [d.text for d in found] == expected


@pytest.mark.parametrize("separator", [LF * 2, chr(0x2029) * 2, chr(0x2028) * 2])
def test_separate_paragraphs_are_not_joined(separator):
    # 빈 줄·문단 구분 문자 너머는 다른 문단이다 — 문단을 넘어 한 주소로 잇지 않는다
    text = "근무지 서울특별시" + separator + "강남구청 앞 3번 출구"
    assert all(separator not in d.text for d in AddressDetector().detect(text))


# ── 구로 시작하는 주소 ──────────────────────────────────────────────


@pytest.mark.parametrize(
    "value",
    [
        "강남구 테헤란로 123",
        "마포구 상암동 1601",
        "중구 새솔로 110",
        "해운대구 우동 1408-1",
        "강남구 역삼동 123-4",
        "강남구 가온동 새솔로 12 101동 1203호",  # 동과 번지 사이에 도로명
        "북구 가온읍 솔내리 12",  # 일반구 아래 읍·리
        "강남구 역삼동 가온아파트 101동 1203호",  # 번지 없이 건물·동호
    ],
)
@pytest.mark.parametrize("cue", ["주소: ", "배송지 ", "거주지: ", "사업장 소재지 "])
def test_address_starting_with_gu_after_an_address_cue(cue, value):
    assert_masked(cue + value + "입니다", value)


@pytest.mark.parametrize(
    "text",
    [
        "연구 교육동에서 만나자",
        "지역구 의원 3명이 참석했다",
        "강남구에서 만나요",
        "구로구청 민원실 안내",
        "탐구 학습동 운영 시간",
        "우리 지역구 동네 3곳",
        # 통계·보고서 문장: '구' 낱말 + 동/리로 끝나는 낱말 + 숫자(#492 독립 검증)
        "인구 이동 1.2%p 증가",
        "연구 활동 3, 4단계로 나눈다",
        "지역구 관리 2026 계획을 세웠다",
        "가구 수리 3 건 접수",
        "인구 이동 3,000명",
        "연구 활동 3명이 참여",
    ],
)
def test_gu_words_without_an_address_cue_are_not_addresses(text):
    assert AddressDetector().detect(text) == []


@pytest.mark.parametrize(
    "text",
    [
        "거주 인구 이동 현황을 보면 수도권 집중이 뚜렷하다.",
        "위치 기반 연구 활동 3건을 수행했다.",
        "이사 후 자택 가구 정리 3개 버림",
        "IP 주소 추적 도구 작동 3회",
        "거주 지역별 인구 변동 1.5%",
    ],
)
def test_two_letter_gu_words_after_an_address_cue_are_not_addresses(text):
    # 두 글자 구는 중구·동구·서구·남구·북구뿐이다. 단서가 있어도 인구·연구·가구·도구를 구로 읽지 않는다
    assert AddressDetector().detect(text) == []
