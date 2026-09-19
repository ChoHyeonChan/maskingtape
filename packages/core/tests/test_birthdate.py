# SPDX-License-Identifier: Apache-2.0

"""생년월일 탐지기 테스트 — 모든 날짜는 합성(가짜)이다."""

from maskingtape.detectors import BirthDateDetector


def detect(text: str):
    return BirthDateDetector().detect(text)


def test_detects_birthdate_after_anchor():
    found = detect("근로자 생년월일은 1999년 7월 21일이다")
    assert len(found) == 1
    assert found[0].kind == "birth_date"
    assert found[0].text == "1999년 7월 21일"
    assert found[0].confidence == 0.9


def test_detects_numeric_date_formats():
    assert detect("생년월일: 1999-07-21")[0].text == "1999-07-21"
    assert detect("생일 1999.07.21")[0].text == "1999.07.21"
    assert detect("출생일 1999/07/21")[0].text == "1999/07/21"


def test_ignores_date_without_birthdate_anchor():
    # 앵커 없는 일반 날짜(계약일·근무 개시일 등)는 잡지 않는다 — 과대탐지 방지
    assert detect("근무 개시일은 2026년 3월 1일로 한다") == []
    assert detect("계약일 2026-03-01") == []


def test_ignores_invalid_date():
    # 존재하지 않는 날짜(13월·45일)는 무작위 숫자로 보고 버린다
    assert detect("생년월일은 1999년 13월 45일") == []


def test_span_covers_date_only_not_the_anchor_label():
    # 마스킹 대상은 날짜 값 — 앵커 라벨("생년월일은")은 스팬에 포함하지 않는다
    text = "생년월일은 2001-05-09"
    found = detect(text)
    assert len(found) == 1
    assert text[found[0].start : found[0].end] == "2001-05-09"


def test_detects_two_digit_year_after_anchor():
    # #399: 서식·표에서 흔한 "YY.MM.DD" 표기 — 앵커가 있을 때만 잡는다
    assert detect("생년월일 95.03.22")[0].text == "95.03.22"
    assert detect("생년월일: 95-03-22")[0].text == "95-03-22"
    assert detect("생일 04/02/29")[0].text == "04/02/29"  # 2004년은 윤년 — 세기를 몰라도 통과


def test_two_digit_year_without_anchor_is_ignored():
    # 앵커 없는 2자리 연도는 버전·일반 숫자와 광범위하게 겹친다 — 잡으면 안 된다
    assert detect("버전 95.03.22 배포") == []
    assert detect("점검일 26.04.10") == []


def test_four_digit_year_is_not_split_into_two_digit_match():
    # "1995.03.22"에서 "95.03.22"만 잘라 잡지 않는다 — 4자리가 먼저 매칭된다
    assert detect("생년월일 1995.03.22")[0].text == "1995.03.22"


def test_two_digit_year_rejects_invalid_dates_and_trailing_digits():
    assert detect("생년월일 95.13.22") == []
    assert detect("생년월일 95.03.221") == []
