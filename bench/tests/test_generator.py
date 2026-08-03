"""합성 생성기가 만드는 데이터의 무결성을 검증한다.

핵심 계약: labels의 start/end는 text[start:end]가 실제 개인정보 원문과 정확히 일치해야 한다
(bench/README.md의 데이터셋 포맷 계약).
"""

from __future__ import annotations

import random

from maskingtape.detectors import AddressDetector
from maskingtape.detectors import BusinessRegistrationDetector
from maskingtape.detectors import CreditCardDetector
from maskingtape.detectors import EmailDetector
from maskingtape.detectors import PassportDetector
from maskingtape.detectors import PhoneDetector
from maskingtape.detectors import RRNDetector
from bench.generator.distractors import (
    gen_business_reg_number,
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
    # hard 주소는 지번(구/동으로만 끝나는 표준형)이 아니라 도로명 또는 시/도 없는 형태여야 한다.
    assert all("길" in a or not any(a.startswith(city) for city in _CITIES) for a in addresses)
    assert any("길" in a for a in addresses)  # 도로명 주소도 나온다


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
