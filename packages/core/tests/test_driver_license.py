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
