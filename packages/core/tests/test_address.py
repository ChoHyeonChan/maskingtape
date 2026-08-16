"""주소 탐지기 테스트 — 모든 주소는 합성(가짜)이다."""

from maskingtape.detectors import AddressDetector


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


def test_detects_province_with_attached_josa():
    # #196: 시/도명 뒤에 조사가 공백 없이 붙어도(에/로/에서) 시/도만으로 주소를 잡는다 — 이전엔 통째로 미탐
    assert detect("본사는 서울특별시에 있습니다")[0].text == "서울특별시"
    assert detect("서울특별시로 발령났습니다")[0].text == "서울특별시"
    assert detect("근무지는 경기도에서 시작합니다")[0].text == "경기도"


def test_institution_name_excluded_even_with_trailing_josa():
    # "서울특별시청에"는 기관명(시청)+조사이므로 여전히 주소로 잡지 않는다 — 조사 허용이 이걸 깨면 안 됨
    assert detect("서울특별시청에 문의하세요") == []


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


# --- #68: 시/도 없이 시/군으로 시작하는 주소 (미탐지는 곧 유출) ---


def test_detects_address_starting_at_si_without_province():
    """'성남시 분당구 정자동 45-6' — 광역단체명이 없어도 통째로 잡아야 한다."""
    found = detect("배송지는 성남시 분당구 정자동 45-6 입니다")
    assert len(found) == 1
    assert found[0].text == "성남시 분당구 정자동 45-6"
    # 시/도가 없어 확신도는 province 앵커(1.0)보다 낮다
    assert found[0].confidence < 1.0


def test_detects_si_without_gu_directly_to_dong():
    # 구가 없는 작은 시는 시 뒤에 바로 동이 온다 — "김포시 사우동"
    found = detect("주소: 김포시 사우동 12-3")
    assert len(found) == 1
    assert found[0].text == "김포시 사우동 12-3"


def test_detects_gun_with_myeon():
    found = detect("양평군 양서면 으로 오세요")
    assert len(found) == 1
    assert found[0].text.startswith("양평군 양서면")


def test_si_anchor_does_not_double_detect_when_province_present():
    """시/도가 있으면 province 앵커가 통째로 잡고, 안쪽 시/군 매칭은 중복으로 버린다."""
    found = detect("경기도 성남시 분당구 정자동 45-6")
    assert len(found) == 1
    assert found[0].text == "경기도 성남시 분당구 정자동 45-6"
    assert found[0].confidence == 1.0


def test_si_anchor_rejects_region_mentions_and_common_words():
    # 조사 '로'(성남시로), 구 단독(강남구에서), 구/동으로 끝나는 일반어는 주소가 아니다
    assert detect("성남시로 이사갔어요") == []
    assert detect("강남구에서 만나요") == []
    assert detect("요구사항을 먼저 정리했다") == []
    assert detect("부산시 마케팅부 소속입니다") == []


def test_detects_province_before_copula_ending():
    # #248: "주소는 X입니다/예요"의 계사 어미도 조사처럼 허용 — 시/도만으로도 주소로 인정한다.
    assert detect("자택 주소는 광주광역시입니다.")[0].text == "광주광역시"
    assert detect("자택 주소는 광주광역시예요.")[0].text == "광주광역시"
    # 회귀: 계사가 아닌 한글이 붙으면(서울특별시청) 여전히 제외
    assert detect("서울특별시청에서 회의") == []


def test_dong_and_ho_after_comma_are_included():
    # #265: 번지와 동/호 사이에 콤마가 끼는 표기("456, 101동 1203호")는 실문서에 흔하다.
    # 콤마 뒤 동/호를 놓치면 세대를 특정하는 정보가 원문 그대로 노출된다(유출).
    got = detect("경기도 성남시 분당구 판교로 456, 101동 1203호")
    assert len(got) == 1
    assert got[0].text == "경기도 성남시 분당구 판교로 456, 101동 1203호"
    # 콤마 없는 표기도 여전히 전체를 잡는다(회귀 방지)
    assert (
        detect("경기도 성남시 분당구 판교로 456 101동 1203호")[0].text
        == "경기도 성남시 분당구 판교로 456 101동 1203호"
    )
    # 콤마 뒤가 동/호가 아니면(이름 등) 주소 구간에 삼키지 않는다
    assert detect("서울특별시 강남구 역삼동 12-3, 김철수 담당")[0].text == "서울특별시 강남구 역삼동 12-3"
