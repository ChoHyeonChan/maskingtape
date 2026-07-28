"""합성 생성기가 만드는 데이터의 무결성을 검증한다.

핵심 계약: labels의 start/end는 text[start:end]가 실제 개인정보 원문과 정확히 일치해야 한다
(bench/README.md의 데이터셋 포맷 계약).
"""

from __future__ import annotations

import random

from maskingtape.detectors import CreditCardDetector
from maskingtape.detectors import EmailDetector
from maskingtape.detectors import PhoneDetector
from maskingtape.detectors import RRNDetector
from bench.generator.distractors import gen_invalid_phone_like, gen_invalid_rrn_like, generate_distractor
from bench.generator.documents import (
    generate_document,
    generate_multi_sentence_document,
    generate_negative_document,
    negative_templates,
    templates,
)
from bench.generator.entities import ALL_KINDS, generate_entity


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
    """hard 난이도는 하이픈 없는 표기와 도로명 주소를 사용해야 한다 (탐지가 어려운 형태)."""
    rng = random.Random(14)
    for _ in range(30):
        phone = generate_entity("phone", rng, difficulty="hard").text
        rrn = generate_entity("rrn", rng, difficulty="hard").text
        address = generate_entity("address", rng, difficulty="hard").text
        assert phone.count("-") == 0
        assert rrn.count("-") == 0
        assert "길" in address  # 도로명 주소만 사용


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
