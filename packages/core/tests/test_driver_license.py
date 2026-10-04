# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""운전면허번호 탐지기 테스트 — 모든 번호는 합성(가짜)이다."""

from maskingtape.detectors import DriverLicenseDetector


def detect(text: str):
    return DriverLicenseDetector().detect(text)


def test_detects_driver_license_with_hyphens():
    found = detect("운전면허 12-34-567890-12 확인 바랍니다")
    assert len(found) == 1
    assert found[0].kind == "driver_license"
    assert found[0].text == "12-34-567890-12"
    assert found[0].confidence == 0.85


def test_detects_region_code_boundaries():
    # 지역코드 유효값 11~26, 28 경계
    assert detect("11-23-456789-01")[0].text == "11-23-456789-01"
    assert detect("26-99-000000-00")[0].text == "26-99-000000-00"
    assert detect("28-00-111111-11")[0].text == "28-00-111111-11"


def test_rejects_invalid_region_code():
    # 지역코드가 아닌 값(10·27·29·30·99)은 잡지 않는다 — 무작위 12자리 오탐 방지
    assert detect("10-23-456789-01") == []
    assert detect("27-23-456789-01") == []
    assert detect("30-23-456789-01") == []
    assert detect("99-99-999999-99") == []


def test_does_not_swallow_part_of_a_longer_number():
    # 앞뒤에 숫자·하이픈이 더 붙으면 더 긴 번호(카드·계좌 등)의 일부 — 잡지 않는다
    assert detect("1112345678901234") == []  # 16자리
    assert detect("12-34-567890-1234") == []  # 뒤에 숫자 더


def test_detects_without_separators():
    # 구분자 없는 12자리 표기도 형식·지역코드가 맞으면 잡는다
    assert detect("발급번호 123456789012 입니다")[0].text == "123456789012"


# ── 지역 이름으로 시작하는 옛 표기(#594) ────────────────────────────
# 2014-06-01 발급분부터 숫자 지역코드로 바뀌기 전에는 앞자리에 지역 이름(시·도 줄임말)을
# 인쇄했다. 외부 데이터(KDPII)에 이 표기가 남아 있는데, 숫자 지역코드만 받던 기존 정규식은
# 통째로 놓쳤다.


def test_detects_driver_license_with_a_region_name_prefix():
    found = detect("면허번호 경기 98-800924-64입니다.")
    assert len(found) == 1
    assert found[0].kind == "driver_license"
    assert found[0].text == "경기 98-800924-64"
    assert found[0].confidence == 0.85


def test_numeric_region_code_still_works_alongside_region_name_support():
    # 대조군: 기존 숫자 지역코드 표기도 여전히 잡혀야 한다(회귀 방지)
    assert detect("면허번호 13-98-800924-64입니다.")[0].text == "13-98-800924-64"


def test_all_fifteen_region_names_are_recognized():
    for region in (
        "서울",
        "부산",
        "경기",
        "강원",
        "충북",
        "충남",
        "전북",
        "전남",
        "경북",
        "경남",
        "제주",
        "대구",
        "인천",
        "대전",
        "울산",
    ):
        text = f"운전면허 {region} 12-345678-90 확인"
        expected = f"{region} 12-345678-90"
        found = detect(text)
        assert len(found) == 1, text
        assert found[0].text == expected, text


def test_region_name_followed_by_a_phone_number_is_not_falsely_grabbed():
    # "지역 이름 + 전화번호"는 운전면허번호가 아니다 — 전화번호는 자리수가 3-4-4라 가운데
    # 연속 숫자 6개가 나올 수 없으므로 모양 자체가 안 맞아야 한다
    assert detect("경기 031-1234-5678로 연락주세요") == []
    assert detect("경기 010-1234-5678") == []


def test_region_name_followed_by_a_date_is_not_falsely_grabbed():
    assert detect("경기 2024-03-01 발급 예정") == []


def test_region_name_as_part_of_a_longer_word_is_not_falsely_grabbed():
    # "경기"가 "경기북부" 같은 더 긴 낱말의 일부면 지역 이름이 아니다
    assert detect("경기북부 12-345678-90 확인") == []
