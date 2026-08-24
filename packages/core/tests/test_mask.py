# SPDX-License-Identifier: Apache-2.0

"""마스킹 익명화기(MaskAnonymizer) 테스트 — 합성 데이터만 사용."""

from maskingtape.anonymizers import MaskAnonymizer
from maskingtape.types import Detection


def _det(start: int, end: int, kind: str = "name") -> Detection:
    # MaskAnonymizer는 start/end 구간만 쓰므로 text는 비워도 된다
    return Detection(kind=kind, start=start, end=end, text="", confidence=1.0, detector="Test")


def test_full_mask_by_default():
    # keep_head 기본값 0 — 구간 전체를 가린다
    out = MaskAnonymizer().apply("고객 김민수 님", [_det(3, 6)])
    assert out == "고객 *** 님"


def test_keep_head_preserves_leading_chars_on_long_value():
    # keep_head=2 → 긴 값은 앞 2글자만 보존 (RRN 등)
    out = MaskAnonymizer(keep_head=2).apply("주민번호 800101-1234560", [_det(5, 19, kind="rrn")])
    assert out == "주민번호 80************"


def test_keep_head_never_exposes_whole_short_value():
    # #169: keep_head=2여도 2글자 값은 절반 상한(1글자)만 보존 — 값이 통째로 남으면 안 된다
    out = MaskAnonymizer(keep_head=2).apply("고객 김민 님", [_det(3, 5)])
    assert out == "고객 김* 님"


def test_keep_head_masks_single_char_value_fully():
    # 1글자 값은 절반 상한이 0이라 완전히 가려진다
    out = MaskAnonymizer(keep_head=2).apply("등급 A 확인", [_det(3, 4)])
    assert out == "등급 * 확인"
