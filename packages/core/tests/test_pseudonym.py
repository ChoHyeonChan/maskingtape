# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""가명처리 전략 테스트 — 모든 개인정보는 합성(가짜)이다.

여기 쓰는 주민등록번호·카드번호는 체크섬만 맞춘 가짜다.
"""

import re

import pytest

from maskingtape.anonymizers.pseudonym import PseudonymAnonymizer
from maskingtape.detectors.financial.creditcard import _luhn_ok
from maskingtape.detectors.identity.rrn import _checksum_ok
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


def test_overlapping_detections_passed_directly_leave_no_raw_text():
    # 겹친 탐지를 apply에 바로 넘기면 위치가 밀려 원문 꼬리가 남았다(#494)
    text = "연락처 010-1234-5678 끝"
    outer = make("phone", 4, 17, "010-1234-5678")
    inner = Detection(kind="name", start=13, end=14, text="5", confidence=0.5, detector="T")
    out = anonymize(text, [outer, inner])
    assert re.fullmatch(r"연락처 010-\d{4}-\d{4} 끝", out), out


def test_pseudonym_never_equals_the_original():
    # 가명 어휘 안의 흔한 이름이 원본이면 예전엔 1/400 확률로 자기 자신이 나왔다(#494).
    # 가명이 원본과 같으면 원본이 그대로 남은 것과 같다
    text = "고객 김서준"
    det = [make("name", 3, 6, "김서준")]
    for seed in range(2000):
        assert "김서준" not in anonymize(text, det, seed=seed)


@pytest.mark.parametrize(
    ("text", "kind", "original"),
    [("담당자 임하", "name", "임하"), ("주소 대구광역시", "address", "대구광역시")],
)
def test_pseudonym_does_not_contain_the_original(text, kind, original):
    # 원본이 가명 안에 그대로 들어가도 원본이 드러난다: "임하" → "임하은",
    # 시/도만 탐지된 "대구광역시" → "대구광역시 서초구 …"(#494)
    start = text.index(original)
    det = [make(kind, start, start + len(original), original)]
    for seed in range(300):
        assert original not in anonymize(text, det, seed=seed)


def test_different_people_get_different_pseudonyms():
    # 서로 다른 사람이 같은 가명을 받으면 "그 사람" 문맥이 섞인다. 10명이면 약 11%였다(#494)
    names = "홍길동 이몽룡 성춘향 변학도 심학규 허생원 전우치 박씨녀 옥단춘 배비장".split()
    text = " ".join(names)
    dets = [make("name", 4 * i, 4 * i + 3, name) for i, name in enumerate(names)]
    for seed in range(300):
        assert len(set(anonymize(text, dets, seed=seed).split(" "))) == len(names)
