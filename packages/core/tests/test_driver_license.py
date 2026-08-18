"""운전면허번호 탐지기 테스트 — 모든 번호는 합성(가짜)이다."""

from maskingtape.detectors import DriverLicenseDetector


def detect(text: str):
    return DriverLicenseDetector().detect(text)


def test_detects_hyphen_separated_license_number():
    found = detect("면허번호는 서울-99-123456-78 입니다")
    assert len(found) == 1
    assert found[0].kind == "driver_license"
    assert found[0].text == "서울-99-123456-78"


def test_detects_space_separated_license_number():
    found = detect("서울 99 123456 78 로 등록됨")
    assert len(found) == 1
    assert found[0].text == "서울 99 123456 78"


def test_detects_mixed_separators():
    found = detect("경기-99 123456-78")
    assert len(found) == 1
    assert found[0].text == "경기-99 123456-78"


def test_boosts_confidence_when_license_context_word_is_nearby():
    found = detect("운전면허 서울-99-123456-78")
    assert found[0].confidence == 0.9


def test_lower_confidence_without_context_word():
    found = detect("코드값 서울-99-123456-78")
    assert found[0].confidence == 0.6


def test_ignores_numbers_without_a_valid_region_name():
    # 지역명이 없는 순수 숫자열은 사업자등록번호·전화번호 등과 구분이 안 되므로 잡지 않는다
    assert detect("무명-99-123456-78") == []


def test_does_not_match_region_name_embedded_in_another_word():
    # "제주도"처럼 지역명 뒤에 다른 글자가 바로 붙으면(구분자가 아니면) 매치하지 않는다
    assert detect("제주도 99-123456-78") == []


def test_does_not_match_when_trailing_digits_extend_the_check_digits():
    # 검증번호 뒤에 숫자가 더 붙으면 더 긴 숫자열의 일부이므로 제외한다
    assert detect("서울-99-123456-789") == []


def test_covers_all_sixteen_region_names():
    regions = [
        "서울",
        "부산",
        "대구",
        "인천",
        "광주",
        "대전",
        "울산",
        "경기",
        "강원",
        "충북",
        "충남",
        "전북",
        "전남",
        "경북",
        "경남",
        "제주",
    ]
    for region in regions:
        found = detect(f"{region}-01-000001-00")
        assert len(found) == 1, f"{region} should be detected"
        assert found[0].text == f"{region}-01-000001-00"
