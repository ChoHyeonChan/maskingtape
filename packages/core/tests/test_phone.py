"""전화번호 탐지기 테스트 — 모든 번호는 합성(가짜)이다."""

from maskingtape.detectors.phone import PhoneDetector


def detect(text: str):
    return PhoneDetector().detect(text)


def test_detects_mobile_with_hyphen():
    found = detect("연락처는 010-1234-5678 입니다")
    assert len(found) == 1
    assert found[0].kind == "phone"
    assert found[0].text == "010-1234-5678"
    assert found[0].confidence == 1.0


def test_detects_bare_mobile_with_lower_confidence():
    # 구분자 없는 숫자열은 다른 번호일 수도 있으니 확신도만 낮춘다
    found = detect("01012345678")
    assert len(found) == 1
    assert found[0].confidence < 1.0


def test_detects_international_format():
    found = detect("+82-10-1234-5678 로 전화주세요")
    assert len(found) == 1


def test_detects_seoul_landline():
    found = detect("사무실 02-123-4567")
    assert len(found) == 1


def test_detects_internet_phone():
    found = detect("070-1234-5678")
    assert len(found) == 1


def test_rejects_non_phone_numbers():
    # 전화번호 형태가 아닌 숫자열은 잡지 않는다
    assert detect("가격은 1234-5678원") == []
    assert detect("주문번호 20260718") == []
