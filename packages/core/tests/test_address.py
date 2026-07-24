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


def test_detects_road_address_including_building_and_unit():
    """도로명 주소는 건물명·동·호까지 가려야 세대가 특정되지 않는다."""
    found = detect("대구광역시 월드컵로237길 49 더샵아파트 123동 1241호에 거주합니다")
    assert len(found) == 1
    assert found[0].text == "대구광역시 월드컵로237길 49 더샵아파트 123동 1241호"
    assert found[0].confidence == 1.0


def test_detects_road_address_without_building():
    found = detect("부산광역시 월드컵로179길 9 로 와주세요")
    assert found[0].text == "부산광역시 월드컵로179길 9"


def test_detects_road_address_with_spaced_branch_number():
    """가지번호는 '테헤란로 123번길'처럼 공백을 두고 쓰기도 한다."""
    found = detect("서울특별시 테헤란로 123번길 45")
    assert found[0].text == "서울특별시 테헤란로 123번길 45"


def test_building_name_may_start_with_ascii():
    found = detect("부산광역시 센텀중앙로252길 12 e편한세상아파트 111동 758호")
    assert found[0].text == "부산광역시 센텀중앙로252길 12 e편한세상아파트 111동 758호"


def test_unit_is_included_even_without_a_known_building_suffix():
    found = detect("광주광역시 동성로45길 7 123동 1241호")
    assert found[0].text == "광주광역시 동성로45길 7 123동 1241호"


def test_detects_four_level_administrative_address():
    """시/군/구는 두 단계까지 이어진다 — '수원시 영통구'에서 끊기면 동·번지가 남는다."""
    found = detect("인천광역시 수원시 영통구 매탄동 147-9로 배송해주세요")
    assert len(found) == 1
    assert found[0].text == "인천광역시 수원시 영통구 매탄동 147-9"
    assert found[0].confidence == 1.0


def test_road_address_does_not_swallow_a_following_number():
    """건물명·동·호 그룹이 뒤따르는 주민등록번호·전화번호를 삼키면 안 된다.

    삼키면 주소 구간이 그 번호와 겹쳐 번호 탐지를 방해한다 (기존 번지 규칙과 같은 이유).
    """
    found = detect("대구광역시 월드컵로237길 49 800101-1234560")
    assert found[0].text == "대구광역시 월드컵로237길 49"

    found = detect("부산광역시 센텀중앙로252길 12 더샵아파트 123동 1241호 010-9876-5432")
    assert found[0].text == "부산광역시 센텀중앙로252길 12 더샵아파트 123동 1241호"
