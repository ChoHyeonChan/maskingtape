"""가명처리 전략 테스트 — 모든 개인정보는 합성(가짜)이다.

여기 쓰는 주민등록번호·카드번호는 체크섬만 맞춘 가짜다.
"""

from maskingtape.anonymizers.pseudonym import PseudonymAnonymizer
from maskingtape.detectors.creditcard import _luhn_ok
from maskingtape.detectors.rrn import _checksum_ok
from maskingtape.types import Detection


def make(kind: str, start: int, end: int, text: str) -> Detection:
    return Detection(kind=kind, start=start, end=end, text=text, confidence=1.0, detector="T")


def anonymize(text: str, detections: list[Detection], seed: int = 0) -> str:
    return PseudonymAnonymizer(seed=seed).apply(text, detections)


def test_replaces_detected_span_with_a_different_value():
    text = "연락처 010-1234-5678"
    out = anonymize(text, [make("phone", 4, 17, "010-1234-5678")])
    assert "010-1234-5678" not in out  # 원본이 남으면 유출
    assert out.startswith("연락처 010-")  # 형식은 유지된다


def test_same_value_maps_to_same_pseudonym_within_a_call():
    # 같은 원본값은 같은 가명으로 → "그 사람"이라는 문맥이 유지된다
    text = "홍길동님, 홍길동님 확인"
    dets = [make("name", 0, 3, "홍길동"), make("name", 6, 9, "홍길동")]
    out = anonymize(text, dets)
    first = out[: out.index("님")]
    assert out.count(first) == 2  # 두 번 다 같은 가명
    assert "홍길동" not in out


def test_different_values_map_to_different_pseudonyms():
    text = "010-1111-2222 그리고 010-3333-4444"
    dets = [make("phone", 0, 13, "010-1111-2222"), make("phone", 18, 31, "010-3333-4444")]
    out = anonymize(text, dets)
    assert "010-1111-2222" not in out and "010-3333-4444" not in out


def test_different_seeds_produce_different_output():
    # 호출마다(전역 결정적 매핑 없음) 가명이 달라야 원본을 역추적할 수 없다
    text = "고객 홍길동"
    det = [make("name", 3, 6, "홍길동")]
    assert anonymize(text, det, seed=1) != anonymize(text, det, seed=2)


def test_fake_rrn_never_passes_checksum():
    """가짜 주민등록번호는 체크섬을 통과하지 않아야 한다(진짜 같은 가짜 방지)."""
    for seed in range(200):
        out = PseudonymAnonymizer(seed=seed).apply("x 800101-1234560", [make("rrn", 2, 16, "800101-1234560")])
        fake = out[2:].replace("-", "")
        assert len(fake) == 13
        assert not _checksum_ok(fake)


def test_fake_card_never_passes_luhn():
    """가짜 카드번호는 Luhn 체크섬을 통과하지 않아야 한다."""
    for seed in range(200):
        out = PseudonymAnonymizer(seed=seed).apply(
            "x 4242-4242-4242-4242", [make("card", 2, 21, "4242-4242-4242-4242")]
        )
        fake = out[2:].replace("-", "")
        assert len(fake) == 16
        assert not _luhn_ok(fake)


def test_unknown_kind_is_still_masked_not_left_in_place():
    # 생성기가 없는 종류도 반드시 가린다 — 원본을 남기면 유출이다
    out = anonymize("여권 M12345678", [make("passport", 3, 12, "M12345678")])
    assert "M12345678" not in out


def test_multiple_kinds_in_one_sentence_all_replaced():
    text = "홍길동님 010-1234-5678 hong@example.com"
    dets = [
        make("name", 0, 3, "홍길동"),
        make("phone", 5, 18, "010-1234-5678"),
        make("email", 19, 35, "hong@example.com"),
    ]
    out = anonymize(text, dets)
    for original in ("홍길동", "010-1234-5678", "hong@example.com"):
        assert original not in out
