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
