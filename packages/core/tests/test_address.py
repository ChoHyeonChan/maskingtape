"""주소 탐지기 테스트 — 모든 주소는 합성(가짜)이다."""

from maskingtape.detectors.address import AddressDetector


def detect(text: str):
    return AddressDetector().detect(text)


def test_detects_full_address_with_high_confidence():
    found = detect("배송지: 서울특별시 강남구 역삼동 123-4 로 보내주세요")
    assert len(found) == 1
    assert found[0].kind == "address"
    assert found[0].text == "서울특별시 강남구 역삼동 123-4"
    assert found[0].confidence == 1.0


def test_detects_address_without_bunji_with_lower_confidence():
    found = detect("고향은 부산광역시 수영구 광안동 입니다")
    assert len(found) == 1
    assert found[0].confidence == 0.8


def test_detects_province_only_with_lowest_confidence():
    found = detect("경기도 출신입니다")
    assert len(found) == 1
    assert found[0].confidence == 0.5


def test_does_not_match_province_name_as_part_of_another_word():
    # "서울특별시청"은 주소가 아니라 기관명 — 시/도명이 다른 단어의 일부일 뿐이면 잡지 않는다
    assert detect("서울특별시청 홈페이지 공지") == []


def test_rejects_text_without_province():
    assert detect("강남 어딘가에서 만나요") == []


def test_bunji_does_not_swallow_part_of_a_longer_number():
    """번지 뒤에 숫자가 더 이어지면 번지가 아니다.

    삼키면 주소 구간이 뒤따르는 주민등록번호·전화번호와 겹쳐 그 번호의 탐지를 방해한다.
    """
    found = detect("서울특별시 강남구 역삼동 800101-1234560")
    assert len(found) == 1
    assert found[0].text == "서울특별시 강남구 역삼동"  # 숫자를 포함하지 않는다

    found = detect("부산광역시 해운대구 우동 010-9876-5432")
    assert found[0].text == "부산광역시 해운대구 우동"


def test_bunji_with_ho_still_matches():
    found = detect("대전광역시 유성구 봉명동 12-3 호에 거주")
    assert found[0].text == "대전광역시 유성구 봉명동 12-3 호"
