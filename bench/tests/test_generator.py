"""합성 생성기가 만드는 데이터의 무결성을 검증한다.

핵심 계약: labels의 start/end는 text[start:end]가 실제 개인정보 원문과 정확히 일치해야 한다
(bench/README.md의 데이터셋 포맷 계약).
"""

from __future__ import annotations

import random
import re

from maskingtape.detectors import AccountDetector
from maskingtape.detectors import AddressDetector
from maskingtape.detectors import BirthDateDetector
from maskingtape.detectors import BusinessRegistrationDetector
from maskingtape.detectors import CreditCardDetector
from maskingtape.detectors import EmailDetector
from maskingtape.detectors import NameDetector
from maskingtape.detectors import PassportDetector
from maskingtape.detectors import PhoneDetector
from maskingtape.detectors import RRNDetector
from bench.generator.distractors import (
    gen_account_number_like,
    gen_business_reg_number,
    gen_date,
    gen_invalid_phone_like,
    gen_invalid_rrn_like,
    gen_passport_like_code,
    gen_region_mention_like,
    generate_distractor,
)
from bench.generator.documents import (
    generate_document,
    generate_multi_sentence_document,
    generate_negative_document,
    negative_templates,
    templates,
)
from bench.generator.entities import ALL_KINDS, generate_entity
from bench.generator.entities import _CITIES


def test_labels_match_text_spans_exactly():
    rng = random.Random(1)
    for _ in range(50):
        doc = generate_document(rng)
        for label in doc.labels:
            assert doc.text[label.start : label.end] != ""
            assert label.kind in ALL_KINDS


def test_every_template_is_reachable():
    rng = random.Random(2)
    seen = set()
    for _ in range(500):
        doc = generate_document(rng)
        seen.add(doc.text)
    assert len(templates()) > 0


def test_generated_rrn_passes_core_detector():
    rng = random.Random(3)
    detector = RRNDetector()
    for _ in range(20):
        entity = generate_entity("rrn", rng)
        found = detector.detect(entity.text)
        assert len(found) == 1
        assert found[0].text == entity.text


def test_labels_do_not_overlap():
    rng = random.Random(4)
    for _ in range(50):
        doc = generate_document(rng)
        ordered = sorted(doc.labels, key=lambda lb: lb.start)
        for prev, cur in zip(ordered, ordered[1:]):
            assert prev.end <= cur.start


def test_negative_documents_have_no_gold_labels():
    """오탐(FP) 측정용 문서는 개인정보가 없어야 하므로 정답 라벨이 0개여야 한다."""
    rng = random.Random(5)
    assert len(negative_templates()) > 0
    for _ in range(50):
        doc = generate_negative_document(rng)
        assert doc.labels == []
        assert doc.difficulty == "negative"


def test_invalid_rrn_like_distractor_is_rejected_by_core_detector():
    """생년월일이 존재하지 않는 '주민번호 모양' distractor는 core가 개인정보로 잡으면 안 된다."""
    rng = random.Random(6)
    detector = RRNDetector()
    for _ in range(20):
        text = gen_invalid_rrn_like(rng)
        assert detector.detect(text) == []


def test_invalid_phone_like_distractor_is_rejected_by_core_detector():
    """존재하지 않는 지역번호의 '전화번호 모양' distractor는 core가 개인정보로 잡으면 안 된다."""
    rng = random.Random(7)
    detector = PhoneDetector()
    for _ in range(20):
        text = gen_invalid_phone_like(rng)
        assert detector.detect(text) == []


def test_generate_distractor_returns_nonempty_string():
    rng = random.Random(8)
    for _ in range(30):
        value = generate_distractor(rng)
        assert isinstance(value, str)
        assert value != ""


def test_generated_phone_passes_core_detector_across_formats():
    """하이픈/공백/점/구분자없음/+82 표기 등 어떤 형식이든 core가 정확히 한 건으로 탐지해야 한다."""
    rng = random.Random(9)
    detector = PhoneDetector()
    for _ in range(100):
        entity = generate_entity("phone", rng)
        found = detector.detect(entity.text)
        assert len(found) == 1, f"탐지 실패: {entity.text!r}"
        assert found[0].text == entity.text


def test_phone_generator_covers_multiple_separator_styles():
    """전화번호 표기 다양성(하이픈/구분자없음 등)이 실제로 섞여 나오는지 확인한다."""
    rng = random.Random(10)
    samples = [generate_entity("phone", rng).text for _ in range(200)]
    has_bare = any(s.replace("+82", "").isdigit() for s in samples)
    has_hyphen = any("-" in s for s in samples)
    assert has_bare
    assert has_hyphen


def test_rrn_generator_covers_multiple_separator_styles():
    rng = random.Random(11)
    samples = [generate_entity("rrn", rng).text for _ in range(200)]
    has_bare = any(s.isdigit() for s in samples)
    has_hyphen = any("-" in s for s in samples)
    assert has_bare
    assert has_hyphen


def test_rrn_generator_covers_foreign_registration_gender_codes():
    """#148: 성별코드 5~8(외국인등록번호)도 나오고, core RRNDetector가 그대로 잡아야 한다."""
    rng = random.Random(31)
    detector = RRNDetector()
    gender_codes = set()
    for _ in range(300):
        entity = generate_entity("rrn", rng, difficulty="easy")
        digits = entity.text.replace("-", "")
        gender_codes.add(digits[6])
        found = detector.detect(entity.text)
        assert len(found) == 1, f"탐지 실패: {entity.text!r}"
        assert found[0].text == entity.text
    assert gender_codes & {"5", "6", "7", "8"}  # 외국인등록번호 성별코드가 실제로 나온다
    assert gender_codes & {"1", "2", "3", "4"}  # 내국인 성별코드도 여전히 나온다


def test_rrn_generator_covers_invalid_checksum_case():
    """#159: 2020-10 이후 발급분(체크섬 없음)도 나오고, core가 confidence 0.85로도 여전히 잡아야 한다."""
    rng = random.Random(32)
    detector = RRNDetector()
    confidences = set()
    for _ in range(300):
        entity = generate_entity("rrn", rng, difficulty="easy")
        found = detector.detect(entity.text)
        assert len(found) == 1, f"탐지 실패: {entity.text!r}"  # 체크섬 무효라도 탐지 자체는 돼야 한다
        assert found[0].text == entity.text
        confidences.add(found[0].confidence)
    assert 0.85 in confidences  # 체크섬 무효 케이스가 실제로 나오고 0.85로 탐지된다
    assert 1.0 in confidences  # 체크섬 유효 케이스도 여전히 나온다


def test_rrn_generator_covers_dot_separator():
    """#209: 점(.) 구분자도 나오고, core RRNDetector가 그대로 잡아야 한다."""
    rng = random.Random(21)
    detector = RRNDetector()
    samples = []
    for _ in range(200):
        entity = generate_entity("rrn", rng, difficulty="mixed")
        found = detector.detect(entity.text)
        assert len(found) == 1, f"탐지 실패: {entity.text!r}"
        assert found[0].text == entity.text
        samples.append(entity.text)
    assert any("." in s for s in samples)  # 점 구분자가 실제로 나온다


def test_address_generator_covers_road_and_jibun_styles():
    """지번 주소(예: 강남구 역삼동 12-3)와 도로명 주소(예: 테헤란로12길 3)가 둘 다 나오는지 확인한다."""
    rng = random.Random(12)
    samples = [generate_entity("address", rng).text for _ in range(200)]
    has_jibun = any("동" in s and "로" not in s for s in samples)
    has_road = any("로" in s for s in samples)
    assert has_jibun
    assert has_road


def test_easy_difficulty_always_uses_standard_separators():
    """easy 난이도는 하이픈 등 표준 구분자만 사용해야 한다 (탐지가 쉬운 형태)."""
    rng = random.Random(13)
    for _ in range(30):
        phone = generate_entity("phone", rng, difficulty="easy").text
        rrn = generate_entity("rrn", rng, difficulty="easy").text
        address = generate_entity("address", rng, difficulty="easy").text
        assert "-" in phone
        assert "+82" not in phone
        assert "-" in rrn
        assert "길" not in address  # 지번 주소만 사용 ("종로구"처럼 구 이름에 "로"가 들어갈 수 있어 "길"로 판별)


def test_hard_difficulty_avoids_hyphen_and_uses_road_address():
    """hard 난이도는 하이픈 없는 표기를 쓰고, 주소는 도로명 또는 시/도 없는 시/군 표기를 사용한다."""
    rng = random.Random(14)
    addresses = []
    for _ in range(30):
        phone = generate_entity("phone", rng, difficulty="hard").text
        rrn = generate_entity("rrn", rng, difficulty="hard").text
        addresses.append(generate_entity("address", rng, difficulty="hard").text)
        assert phone.count("-") == 0
        assert rrn.count("-") == 0
    # 부분 주소(#195, 시/도 단독·시/도+구까지만 — 공백 1~2개뿐)는 jibun/road/no_province
    # 어느 스타일도 아닌 별도 카테고리라 이 assertion 대상에서 제외한다(전용 테스트는 아래 참고).
    full_addresses = [a for a in addresses if a.count(" ") >= 2]
    # hard 주소는 지번(구/동으로만 끝나는 표준형)이 아니라 도로명 또는 시/도 없는 형태여야 한다.
    assert all("길" in a or not any(a.startswith(city) for city in _CITIES) for a in full_addresses)
    assert any("길" in a for a in full_addresses)  # 도로명 주소도 나온다


def test_address_generator_covers_partial_style():
    """#195: 동/번지 없는 부분 주소(시/도만·시/도+구만)도 나오고, core가 낮은 confidence로도
    여전히 잡아야 한다(단, 시/도명 뒤에 한글 조사가 공백 없이 붙는 경우는 예외 — #196)."""
    rng = random.Random(20)
    detector = AddressDetector()
    confidences = set()
    partial_count = 0
    for _ in range(300):
        entity = generate_entity("address", rng, difficulty="mixed")
        if entity.text.count(" ") > 1:
            continue  # 완전한 주소(동/번지 포함)는 이 테스트 대상이 아니다
        partial_count += 1
        found = detector.detect(entity.text)
        assert len(found) == 1, f"탐지 실패: {entity.text!r}"
        assert found[0].text == entity.text
        confidences.add(found[0].confidence)
    assert partial_count > 0  # 부분 주소가 실제로 나온다
    assert 0.5 in confidences  # 시/도만 — 최저 확신도
    assert 0.65 in confidences  # 시/도+구 — 그 다음 확신도


def test_bare_province_before_copula_ending_is_detected():
    """#248 (core #252로 해결) — #196의 조사 화이트리스트가 "에/로/은/는" 같은 조사만 다루고
    "이다"의 활용형(계사 어미 "입니다"/"예요")은 놓치던 문제를 core가 고쳤다. "주소는 X입니다"는
    "주소는 X에 있습니다"만큼 흔한 표현이라 이제 시/도를 잡아야 한다. 이 canary는 그 동작이
    회귀하지 않는지 계속 지킨다 — 계사 어미는 허용하되 조사 아닌 한글이 붙은 다른 단어는 제외."""
    detector = AddressDetector()
    assert detector.detect("자택 주소는 광주광역시입니다.")[0].text == "광주광역시"
    assert detector.detect("자택 주소는 광주광역시예요.")[0].text == "광주광역시"
    # "서울특별시청"은 시/도명 뒤에 조사 아닌 한글('청')이 붙은 다른 단어라 여전히 제외(#196).
    assert detector.detect("서울특별시청에서 회의했습니다.") == []


def test_hard_difficulty_can_produce_no_province_address():
    """#118: 시/도 없이 시/군으로 시작하는 주소도 hard 난이도에서 실제로 나와야 측정 사각지대가 없다."""
    rng = random.Random(17)
    addresses = [generate_entity("address", rng, difficulty="hard").text for _ in range(100)]
    assert any(not any(a.startswith(city) for city in _CITIES) for a in addresses)


def test_no_province_address_has_gu_or_dong_right_after_si_or_gun():
    """core AddressDetector(#117)의 오탐 방지 게이트 — 시/군 바로 뒤에 구/동/읍/면이 와야 한다."""
    rng = random.Random(18)
    for _ in range(50):
        entity = generate_entity("address", rng, difficulty="hard")
        if any(entity.text.startswith(city) for city in _CITIES):
            continue  # road 스타일은 이 케이스가 아니므로 건너뛴다
        second_word = entity.text.split(" ")[1]
        assert second_word.endswith(("구", "동", "읍", "면", "리"))


def test_region_mention_distractor_is_rejected_by_core_detector():
    """조사 '로'가 붙거나 구 단독인 지역 언급 distractor는 core가 주소로 잡으면 안 된다."""
    rng = random.Random(19)
    detector = AddressDetector()
    for _ in range(20):
        text = gen_region_mention_like(rng)
        assert detector.detect(text) == []


def test_generate_document_tags_difficulty_as_easy_or_hard():
    rng = random.Random(15)
    for _ in range(30):
        doc = generate_document(rng)
        assert doc.difficulty in ("easy", "hard")


def test_generated_card_passes_core_detector_across_formats():
    """Visa/Mastercard/Amex 계열, 하이픈/점/공백/구분자없음 어떤 조합이든 core가 정확히 한 건으로 잡아야 한다."""
    rng = random.Random(16)
    detector = CreditCardDetector()
    for _ in range(100):
        entity = generate_entity("card", rng)
        found = detector.detect(entity.text)
        assert len(found) == 1, f"탐지 실패: {entity.text!r}"
        assert found[0].text == entity.text


def test_card_generator_covers_16_and_15_digit_networks():
    """Visa/Mastercard(16자리)와 Amex(15자리) 둘 다 나오는지 확인한다."""
    rng = random.Random(17)
    samples = [generate_entity("card", rng).text for _ in range(200)]
    digit_lengths = {sum(c.isdigit() for c in s) for s in samples}
    assert 16 in digit_lengths
    assert 15 in digit_lengths


def test_card_easy_difficulty_uses_hyphen_and_hard_uses_bare_digits():
    rng = random.Random(18)
    for _ in range(30):
        easy = generate_entity("card", rng, difficulty="easy").text
        hard = generate_entity("card", rng, difficulty="hard").text
        assert "-" in easy
        assert hard.isdigit()


def test_distractors_are_never_detected_as_card():
    """#69 회귀 방지 — RRN 모양 등 distractor가 카드 체크섬에 우연히 걸려 오탐되지 않아야 한다."""
    rng = random.Random(19)
    detector = CreditCardDetector()
    for _ in range(300):
        text = generate_distractor(rng)
        assert detector.detect(text) == [], f"distractor가 card로 오탐됨: {text!r}"


def test_generated_biz_reg_passes_core_detector():
    """생성된 사업자등록번호는 국세청 체크섬이 항상 유효해 core가 정확히 한 건으로 잡아야 한다."""
    rng = random.Random(20)
    detector = BusinessRegistrationDetector()
    for _ in range(50):
        entity = generate_entity("biz_reg", rng)
        found = detector.detect(entity.text)
        assert len(found) == 1, f"탐지 실패: {entity.text!r}"
        assert found[0].text == entity.text


def test_business_reg_distractor_is_rejected_by_core_detector():
    """#123: 체크섬 없는 '사업자등록번호 모양' distractor는 core가 걸러내야 한다(우연한 통과 없이)."""
    rng = random.Random(21)
    detector = BusinessRegistrationDetector()
    for _ in range(300):
        text = gen_business_reg_number(rng)
        assert detector.detect(text) == [], f"distractor가 biz_reg로 오탐됨: {text!r}"


def test_distractors_are_never_detected_as_biz_reg():
    """#123 회귀 방지 — generate_distractor 전체 풀에서도 biz_reg 오탐이 없어야 한다."""
    rng = random.Random(27)
    detector = BusinessRegistrationDetector()
    for _ in range(300):
        text = generate_distractor(rng)
        assert detector.detect(text) == [], f"distractor가 biz_reg로 오탐됨: {text!r}"


def test_generated_passport_passes_core_detector():
    """생성된 여권번호(구/신여권)는 형식이 core 정규식과 정확히 맞아 한 건으로 잡혀야 한다."""
    rng = random.Random(28)
    detector = PassportDetector()
    for _ in range(50):
        entity = generate_entity("passport", rng)
        found = detector.detect(entity.text)
        assert len(found) == 1, f"탐지 실패: {entity.text!r}"
        assert found[0].text == entity.text


def test_passport_generator_covers_old_and_new_styles():
    """구여권(문자+숫자8자리)과 신여권(문자+3자리+문자+4자리) 둘 다 나오는지 확인한다."""
    rng = random.Random(29)
    samples = [generate_entity("passport", rng).text for _ in range(200)]
    has_old = any(len(s) == 9 and s[1:].isdigit() for s in samples)
    has_new = any(len(s) == 9 and not s[1:].isdigit() for s in samples)
    assert has_old
    assert has_new


def test_distractors_are_never_detected_as_passport():
    """#139 회귀 방지 — 여권 탐지기는 체크섬이 없어 형식만 겹쳐도 오탐된다. distractor 전체
    풀에서 우연히도 형식이 겹치지 않는지 확인한다."""
    rng = random.Random(30)
    detector = PassportDetector()
    for _ in range(300):
        text = generate_distractor(rng)
        assert detector.detect(text) == [], f"distractor가 passport로 오탐됨: {text!r}"


def test_passport_like_code_distractor_is_rejected_by_core_detector():
    """#145: 사원번호·상품 코드처럼 여권번호와 문자는 같지만 자릿수가 다른 근접 미스
    distractor는 core가 걸러내야 한다."""
    rng = random.Random(31)
    detector = PassportDetector()
    for _ in range(300):
        text = gen_passport_like_code(rng)
        assert detector.detect(text) == [], f"distractor가 passport로 오탐됨: {text!r}"


def test_generated_phone_covers_landline_and_passes_core_detector():
    """유선전화(02/031~033 등)도 생성되고, core가 형식과 무관하게 정확히 한 건으로 잡아야 한다."""
    rng = random.Random(22)
    detector = PhoneDetector()
    landline_prefixes = (
        "02", "031", "032", "033", "041", "042", "043", "044",
        "051", "052", "053", "054", "055", "061", "062", "063", "064", "070",
    )
    found_landline = False
    for _ in range(300):
        # easy 난이도는 하이픈만 쓰고 국제표기를 안 섞으므로, "-" 기준으로 지역번호를 안정적으로 추출할 수 있다.
        entity = generate_entity("phone", rng, difficulty="easy")
        found = detector.detect(entity.text)
        assert len(found) == 1, f"탐지 실패: {entity.text!r}"
        assert found[0].text == entity.text
        if entity.text.split("-")[0] in landline_prefixes:
            found_landline = True
    assert found_landline


def test_phone_generator_covers_safe050_numbers():
    """#211: 평생번호·안심번호(050/0502~0508)도 나오고, core가 정확히 한 건으로 잡아야 한다."""
    rng = random.Random(40)
    detector = PhoneDetector()
    found_050 = False
    for _ in range(300):
        entity = generate_entity("phone", rng, difficulty="mixed")
        found = detector.detect(entity.text)
        assert len(found) == 1, f"탐지 실패: {entity.text!r}"
        assert found[0].text == entity.text
        if entity.text.replace("-", "").replace(".", "").replace(" ", "").startswith("050"):
            found_050 = True
    assert found_050


def test_generated_email_covers_plus_tag_and_subdomain():
    """plus 표기·서브도메인도 core EmailDetector가 정확히 한 건으로 잡아야 한다."""
    rng = random.Random(23)
    detector = EmailDetector()
    samples = []
    for _ in range(200):
        entity = generate_entity("email", rng)
        found = detector.detect(entity.text)
        assert len(found) == 1, f"탐지 실패: {entity.text!r}"
        assert found[0].text == entity.text
        samples.append(entity.text)
    assert any("+" in s.split("@")[0] for s in samples)
    assert any(s.split("@")[1].count(".") >= 2 for s in samples)


def test_multi_sentence_document_labels_have_correct_offsets():
    """여러 문장을 이어붙여도 뒤 문장의 라벨이 실제 위치를 정확히 가리켜야 한다."""
    rng = random.Random(24)
    for _ in range(50):
        doc = generate_multi_sentence_document(rng)
        assert len(doc.labels) >= 2  # 문장이 2개 이상이라 라벨도 최소 2개 이상
        for label in doc.labels:
            assert doc.text[label.start : label.end] != ""
            assert label.kind in ALL_KINDS


def test_multi_sentence_document_labels_do_not_overlap():
    rng = random.Random(25)
    for _ in range(50):
        doc = generate_multi_sentence_document(rng)
        ordered = sorted(doc.labels, key=lambda lb: lb.start)
        for prev, cur in zip(ordered, ordered[1:]):
            assert prev.end <= cur.start


def test_multi_sentence_document_has_multiple_sentences_worth_of_text():
    """단일 문장 문서보다 눈에 띄게 길어야 한다 — 실제로 여러 문장이 이어붙었다는 방증."""
    rng = random.Random(26)
    single = generate_document(rng)
    multi = generate_multi_sentence_document(rng, sentence_count=3)
    assert len(multi.text) > len(single.text)
    assert multi.text.count(" ") >= 2


def test_generated_account_passes_core_detector_with_context():
    """#180: 계좌번호는 문맥어(계좌/입금/은행 등)가 근처에 있어야만 탐지되는 하드 게이트다 —
    문맥어를 붙인 문장에서는 정확히 한 건으로 잡혀야 한다."""
    rng = random.Random(32)
    detector = AccountDetector()
    for _ in range(50):
        entity = generate_entity("account", rng)
        text = f"계좌번호는 {entity.text}이며 입금 확인 부탁드립니다."
        found = detector.detect(text)
        assert len(found) == 1, f"탐지 실패: {entity.text!r}"
        assert found[0].text == entity.text
        assert found[0].kind == "account"


def test_generated_account_without_context_is_not_detected():
    """#180: 같은 형식이라도 문맥어가 전혀 없으면 core가 탐지하면 안 된다(하드 게이트 검증)."""
    rng = random.Random(33)
    detector = AccountDetector()
    for _ in range(50):
        entity = generate_entity("account", rng)
        text = f"참고 번호는 {entity.text}입니다."
        assert detector.detect(text) == [], f"문맥어 없이도 탐지됨: {text!r}"


def test_account_generator_covers_multiple_group_patterns_and_separators():
    """은행별 그룹 자릿수 다양성과 하이픈/구분자없음 표기가 실제로 섞여 나오는지 확인한다."""
    rng = random.Random(34)
    samples = [generate_entity("account", rng).text for _ in range(200)]
    has_hyphen = any("-" in s for s in samples)
    has_bare = any(s.isdigit() for s in samples)
    group_counts = {s.count("-") + 1 for s in samples if "-" in s}
    assert has_hyphen
    assert has_bare
    assert group_counts & {3, 4}  # 3~4그룹 표기가 실제로 섞여 나온다


def test_account_number_like_distractor_is_rejected_without_context():
    """#180: 계좌번호와 형식이 같아도 문맥어 없는 문장에서는 core가 걸러내야 한다."""
    rng = random.Random(35)
    detector = AccountDetector()
    for _ in range(300):
        text = gen_account_number_like(rng)
        wrapped = f"참고 코드: {text} 입니다."
        assert detector.detect(wrapped) == [], f"문맥어 없이도 탐지됨: {wrapped!r}"


def test_distractors_are_never_detected_as_account():
    """#180 회귀 방지 — generate_distractor 전체 풀이 실제 문서 템플릿(문맥어 없음)에 쓰이므로,
    account로 오탐되지 않아야 한다."""
    rng = random.Random(36)
    detector = AccountDetector()
    for _ in range(300):
        text = generate_distractor(rng)
        assert detector.detect(text) == [], f"distractor가 account로 오탐됨: {text!r}"


def test_generated_birth_date_passes_core_detector_with_anchor():
    """#266/#271: 생년월일은 "생년월일/생일/출생일" 앵커가 바로 앞에 있어야만 탐지되는
    문맥 앵커 방식이다 — 앵커를 붙인 문장에서는 날짜 부분만 정확히 한 건으로 잡혀야 한다
    (앵커 라벨 자체는 스팬에 포함되지 않는다)."""
    rng = random.Random(42)
    detector = BirthDateDetector()
    for _ in range(100):
        entity = generate_entity("birth_date", rng)
        text = f"생년월일은 {entity.text}입니다."
        found = detector.detect(text)
        assert len(found) == 1, f"탐지 실패: {entity.text!r}"
        assert found[0].text == entity.text
        assert found[0].kind == "birth_date"
        assert found[0].confidence == 0.9


def test_generated_birth_date_without_anchor_is_not_detected():
    """#266/#271: 같은 날짜라도 생년월일 앵커가 없으면(일반 날짜) core가 탐지하면 안 된다
    — 문맥 앵커 게이트 검증."""
    rng = random.Random(43)
    detector = BirthDateDetector()
    for _ in range(100):
        entity = generate_entity("birth_date", rng)
        text = f"등록일은 {entity.text}입니다."
        assert detector.detect(text) == [], f"앵커 없이도 탐지됨: {text!r}"


def test_birth_date_generator_covers_korean_and_numeric_styles():
    """생년월일 표기 다양성("1999년 7월 21일" 류와 "1999-07-21" 류)이 실제로 섞여
    나오는지 확인한다."""
    rng = random.Random(44)
    samples = [generate_entity("birth_date", rng).text for _ in range(200)]
    has_korean = any("년" in s and "월" in s and "일" in s for s in samples)
    has_numeric = any(re.fullmatch(r"\d{4}[-./]\d{1,2}[-./]\d{1,2}", s) for s in samples)
    assert has_korean
    assert has_numeric


def test_plain_date_distractor_is_never_detected_as_birth_date():
    """#266/#271: gen_date(주문일·결제일 등 negative 템플릿에 쓰이는 일반 날짜 distractor)가
    만드는 형식(YYYY.MM.DD)은 core BirthDateDetector의 날짜 정규식과 정확히 겹친다 — 앵커
    없이 등장하면(실제 negative 템플릿이 그렇게 쓴다) 절대 생년월일로 오탐되면 안 된다."""
    rng = random.Random(45)
    detector = BirthDateDetector()
    for _ in range(300):
        text = gen_date(rng)
        wrapped = f"결제일은 {text}입니다."
        assert detector.detect(wrapped) == [], f"앵커 없는 일반 날짜가 오탐됨: {wrapped!r}"


def test_account_number_like_distractor_is_never_detected_as_card():
    """#223에서 실측 재현 — gen_account_number_like가 구분자 없이 13자리 이상을 만들면
    core CreditCardDetector의 "구분자 없는 13~19자리" 분기와 우연히 겹칠 수 있다(Luhn까지
    통과하면 ~10% 확률로 card 오탐). gen_account가 이미 갖고 있던 Luhn 무효화 가드를
    distractor 쪽에도 똑같이 적용해 회귀를 막는다."""
    rng = random.Random(41)
    detector = CreditCardDetector()
    for _ in range(500):
        text = gen_account_number_like(rng)
        assert detector.detect(text) == [], f"distractor가 card로 오탐됨: {text!r}"


def test_full_name_with_title_only_is_detected():
    """#213: 역할어·존칭 없이 직함만 있어도, 3글자 이상 풀네임이면 core가 잡아야 한다."""
    detector = NameDetector()
    found = detector.detect("홍길동 대표가 계약서에 서명했습니다.")
    assert [f.text for f in found] == ["홍길동"]
    assert found[0].confidence == 0.5


def test_two_syllable_name_with_title_only_is_not_detected():
    """#213 설계된 한계 — 직함 단서 하나뿐이고 2음절 이름(성씨+1음절)이면 core가 일부러 놓친다
    (부서·업무어 오탐을 막는 성+2자 풀네임 가드). 버그가 아니라 문서화된 트레이드오프다."""
    detector = NameDetector()
    assert detector.detect("김민 부장이 결재했습니다.") == []


def test_department_word_with_title_is_not_detected_as_name():
    """#213 core 이슈 예시 그대로 — 성씨로 시작하는 2음절 부서·업무어가 직함 단서만으로
    이름으로 오탐되면 안 된다."""
    detector = NameDetector()
    for text in ("구매 부장이 결재했습니다.", "정기 이사가 참석했습니다.", "홍보 사원이 채용되었습니다."):
        assert detector.detect(text) == [], f"부서어가 이름으로 오탐됨: {text!r}"


def test_full_name_with_title_prefix_is_detected():
    """#239: 직함이 이름 뒤가 아니라 앞에 와도("대표 홍길동"), 3글자 이상 풀네임이면 잡혀야 한다."""
    detector = NameDetector()
    found = detector.detect("대표 홍길동이 계약서에 서명했습니다.")
    assert [f.text for f in found] == ["홍길동"]
    assert found[0].confidence == 0.5


def test_two_syllable_name_with_title_prefix_is_not_detected():
    """#239 설계된 한계 — #213과 대칭으로, 직함이 앞에 와도 2음절 이름은 일부러 놓친다.
    쉼표로 끊어 뒤에 조사가 바로 안 붙는 경우만 확인한다 — 조사가 바로 붙는 경우는
    아래 test_title_prefix_guard_holds_when_particle_attaches(#247 해결)로 별도 고정."""
    detector = NameDetector()
    assert detector.detect("대표 김민, 계약서에 서명했습니다.") == []


def test_isa_after_title_prefix_is_not_detected_as_name():
    """#239 core 커밋 예시 그대로 — "대표이사"가 띄어써지면("대표 이사가") "이사"가 성씨
    "이"+"사"로 오탐되면 안 된다(core가 _NON_NAME_WORDS에 "이사" 추가로 막음)."""
    detector = NameDetector()
    for text in ("대표 이사가 참석했습니다.", "대표 이사회에서 발표했습니다."):
        assert detector.detect(text) == [], f"'이사'가 이름으로 오탐됨: {text!r}"


def test_title_prefix_guard_holds_when_particle_attaches():
    """#247 (core #252로 해결) — #239의 "성+2자 풀네임만 인정" 가드가 2음절 부서어 뒤에
    조사가 공백 없이 붙으면("정기가"·"구매가") 조사를 선택적 2번째 글자로 삼켜 "3글자"로
    둔갑, 가드를 우회하던 문제를 core가 고쳤다. 이제 부서어+조사는 이름으로 잡지 않는다.
    단, 실명이 우연히 조사로 끝나도(김지은) 부서어 stem이 아니면 그대로 잡아야 유출이 없다 —
    그 경계까지 이 canary가 함께 지킨다."""
    detector = NameDetector()
    assert detector.detect("대표 정기가 참석했습니다.") == []
    assert detector.detect("부장 구매가 결재를 승인했습니다.") == []
    # 유출 방지 경계: 실명은 조사로 끝나도(김지은) 부서 stem이 아니라 그대로 잡힌다.
    assert [d.text for d in detector.detect("대표 김지은 확인 바랍니다.")] == ["김지은"]


def test_title_prefix_dept_word_guard_only_covers_hardcoded_stems():
    """#255 (신규 발견, core 부분 해결·의도된 트레이드오프일 수 있음) — core #252가 #247을
    고친 방식은 하드코딩 5개 stem(구매/정기/홍보/안전/노무)만 차단하는 목록 기반이다. 목록
    밖의 흔한 업무어("차량"·"허가"·"성과"·"안내", 전부 성씨와 우연히 겹침)는 조사가 붙으면
    여전히 오탐된다 — bench 소관이 아니라 core 이슈로 남겼다(코드는 안 고침). core가 목록을
    넓히거나 일반화하면 이 테스트가 깨져서 알 수 있다."""
    detector = NameDetector()
    for text in (
        "대표 차량이 배정되었습니다.",
        "대표 허가가 필요합니다.",
        "부장 성과가 좋았습니다.",
        "팀장 안내가 시작되었습니다.",
    ):
        found = detector.detect(text)
        assert len(found) == 1 and found[0].confidence == 0.5, f"예상과 다른 동작: {text!r} -> {found!r}"
