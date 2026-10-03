# SPDX-FileCopyrightText: 2026 The maskingtape Authors
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


# ── 날짜 뒤에 오는 생년월일 단서(#592) ──────────────────────────────
# 말로 할 때는 "생년월일은 …" 처럼 라벨이 앞에 오기보다 "…일생입니다"·"…에 태어났어요"·
# "…이 제 생일이에요"처럼 단서가 날짜 뒤에 붙는 어순이 더 흔하다. 기존 _BIRTHDATE_RE는
# 라벨이 앞에 올 때만 잡아서 이 표기를 통째로 놓쳤다.


def test_detects_birthdate_with_a_trailing_saeng_cue():
    found = detect("저는 1992년 10월 31일생입니다.")
    assert len(found) == 1
    assert found[0].text == "1992년 10월 31일"
    assert found[0].confidence == 0.9


def test_detects_two_digit_year_with_a_trailing_saeng_cue():
    assert detect("92년 7월 3일생이에요.")[0].text == "92년 7월 3일"


def test_detects_birthdate_with_a_trailing_born_cue():
    assert detect("막내는 2019년 4월 23일에 태어났어요.")[0].text == "2019년 4월 23일"


def test_detects_birthdate_with_a_trailing_birthday_cue():
    assert detect("1995년 6월 21일이 제 생일이에요.")[0].text == "1995년 6월 21일"


def test_leading_anchor_still_works_alongside_trailing_cue_support():
    # 대조군: 기존 앞쪽 라벨 방식도 여전히 잡혀야 한다(회귀 방지)
    assert detect("생년월일은 1995년 6월 21일이에요.")[0].text == "1995년 6월 21일"


def test_trailing_saeng_cue_does_not_match_unrelated_words_starting_with_saeng():
    # "생"으로 시작하는 낱말(생산·생활·생각·생기다·생명 등)은 생년월일 단서가 아니다 —
    # 종결 어미 화이트리스트 뒤에 한글이 더 이어지면 걸러진다
    for text in (
        "2024년 3월 1일 생산된 제품입니다.",
        "2026년 3월 1일 생활 수칙이 바뀝니다.",
        "2024년 3월 1일 생각났어요.",
        "2024년 3월 1일 생기다니 놀랍다.",
        "2024년 3월 1일 생명 연장 장치.",
    ):
        assert detect(text) == [], text
