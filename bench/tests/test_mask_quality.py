"""mask_quality.py의 유출(leak) 판정과 구조 보존(길이) 검증 로직을 확인한다."""

from __future__ import annotations

import random
import re
from collections.abc import Sequence

from maskingtape.anonymizers import LabelAnonymizer, PseudonymAnonymizer
from maskingtape.anonymizers.base import Anonymizer
from maskingtape.detectors import CreditCardDetector, PhoneDetector, RRNDetector
from maskingtape.detectors.financial.creditcard import _luhn_ok
from maskingtape.detectors.identity.rrn import _checksum_ok
from maskingtape.pipeline import Pipeline
from maskingtape.types import Detection

from bench.evaluators.mask_quality import evaluate_mask_quality, format_mask_quality_report
from bench.generator.entities import generate_entity


class _HalfMaskAnonymizer(Anonymizer):
    """테스트 전용 — 탐지된 구간의 앞 절반만 마스킹해 '경계가 어긋난 부분 유출' 상황을 흉내낸다."""

    def apply(self, text: str, detections: Sequence[Detection]) -> str:
        for d in sorted(detections, key=lambda d: d.start, reverse=True):
            half = (d.end - d.start) // 2
            masked = "*" * half + text[d.start + half : d.end]
            text = text[: d.start] + masked + text[d.end :]
        return text


def test_no_leak_when_pii_is_correctly_masked():
    """core가 실제로 탐지·마스킹하는 phone은 원문이 결과에 남으면 안 된다."""
    rows = [{"text": "010-1234-5678로 연락주세요.", "labels": [{"kind": "phone", "start": 0, "end": 13}]}]
    result = evaluate_mask_quality(rows, Pipeline())
    assert result.leak_count == 0
    assert result.full_leak_count == 0
    assert result.partial_leak_count == 0
    assert result.gold_pii_count == 1


def test_leak_detected_when_kind_has_no_detector_yet():
    """core에 탐지기가 없는 종류는 마스킹이 전혀 안 되므로 완전 유출로 잡혀야 한다.

    core는 gold label의 kind 문자열이 아니라 텍스트 내용만 보고 탐지하므로, kind 이름만
    바꿔서는 "탐지기가 없다"는 상황을 흉내낼 수 없다 (core에 이름 탐지기가 생기면 어떤
    kind로 라벨링하든 "김민준"은 실제로 탐지·마스킹된다). 그래서 detectors=[]인 파이프라인을
    직접 만들어 core의 현재 탐지기 구성과 완전히 무관하게 "탐지기가 없는 경우" 자체를 재현한다.
    """
    rows = [{"text": "김민준님 안녕하세요.", "labels": [{"kind": "name", "start": 0, "end": 3}]}]
    result = evaluate_mask_quality(rows, Pipeline(detectors=[]))
    assert result.leak_count == 1
    assert result.full_leak_count == 1
    assert result.partial_leak_count == 0
    assert result.leaks[0].kind == "name"
    assert result.leaks[0].value == "김민준"
    assert result.leaks[0].exposed_ratio == 1.0
    assert not result.leaks[0].is_partial


def test_partial_leak_when_boundary_masking_is_incomplete():
    """탐지는 됐지만 구간의 일부만 가려지면(경계 오류) 부분 유출로 구분돼야 한다."""
    rows = [{"text": "010-1234-5678로 연락주세요.", "labels": [{"kind": "phone", "start": 0, "end": 13}]}]
    result = evaluate_mask_quality(rows, Pipeline(anonymizer=_HalfMaskAnonymizer()))
    assert result.leak_count == 1
    assert result.full_leak_count == 0
    assert result.partial_leak_count == 1
    assert 0 < result.leaks[0].exposed_ratio < 1.0
    assert result.leaks[0].is_partial


def test_leak_rate_is_zero_when_no_gold_pii():
    result = evaluate_mask_quality([{"text": "회의는 내일입니다.", "labels": []}], Pipeline())
    assert result.leak_rate == 0.0
    assert result.gold_pii_count == 0


def test_length_preserved_rate_full_when_all_lengths_match():
    rows = [{"text": "010-1234-5678로 연락주세요.", "labels": [{"kind": "phone", "start": 0, "end": 13}]}]
    result = evaluate_mask_quality(rows, Pipeline())
    assert result.length_mismatch_count == 0
    assert result.length_preserved_rate == 1.0


def test_format_mask_quality_report_is_readable():
    rows = [
        {"text": "010-1234-5678로 연락주세요.", "labels": [{"kind": "phone", "start": 0, "end": 13}]},
        {"text": "김민준님 안녕하세요.", "labels": [{"kind": "name", "start": 0, "end": 3}]},
    ]
    result = evaluate_mask_quality(rows, Pipeline(detectors=[]))
    report = format_mask_quality_report(result)
    assert "유출" in report
    assert "name" in report


def test_no_leak_with_label_strategy():
    """label 전략([전화번호] 치환)도 mask와 똑같이 원문이 안 남아야 한다."""
    rows = [{"text": "010-1234-5678로 연락주세요.", "labels": [{"kind": "phone", "start": 0, "end": 13}]}]
    result = evaluate_mask_quality(rows, Pipeline(anonymizer=LabelAnonymizer()), strategy="label")
    assert result.leak_count == 0
    assert result.length_mismatch_count == 1  # "[전화번호]"는 원문과 길이가 다름 — 정상


def test_no_leak_with_pseudonym_strategy():
    """pseudonym 전략(그럴듯한 가짜 값 치환)도 원문이 안 남아야 한다."""
    rows = [{"text": "010-1234-5678로 연락주세요.", "labels": [{"kind": "phone", "start": 0, "end": 13}]}]
    result = evaluate_mask_quality(rows, Pipeline(anonymizer=PseudonymAnonymizer(seed=1)), strategy="pseudonym")
    assert result.leak_count == 0


def test_format_mask_quality_report_shows_strategy_and_adjusts_length_note():
    rows = [{"text": "010-1234-5678로 연락주세요.", "labels": [{"kind": "phone", "start": 0, "end": 13}]}]
    result = evaluate_mask_quality(rows, Pipeline(anonymizer=LabelAnonymizer()), strategy="label")
    report = format_mask_quality_report(result)
    assert "label" in report
    assert "버그 의심" not in report  # label은 길이가 달라지는 게 정상이므로 버그 신호로 오해하면 안 됨


def test_pseudonym_generated_rrn_never_passes_real_checksum():
    """pseudonym.py의 보안 설계 — 가짜 주민번호가 실제 체크섬을 통과하면 안 된다(회귀 방지)."""
    rng = random.Random(20)
    detector = RRNDetector()
    for seed in range(30):
        entity = generate_entity("rrn", rng, difficulty="easy")
        detections = detector.detect(entity.text)
        assert len(detections) == 1
        fake_text = PseudonymAnonymizer(seed=seed).apply(entity.text, detections)
        digits = "".join(c for c in fake_text if c.isdigit())
        assert len(digits) == 13
        assert not _checksum_ok(digits), f"가짜 주민번호가 진짜 체크섬을 통과함: {fake_text!r}"


def test_pseudonym_generated_card_never_passes_real_luhn():
    """pseudonym.py의 보안 설계 — 가짜 카드번호가 실제 Luhn 체크섬을 통과하면 안 된다(회귀 방지)."""
    rng = random.Random(21)
    detector = CreditCardDetector()
    for seed in range(30):
        entity = generate_entity("card", rng, difficulty="easy")
        detections = detector.detect(entity.text)
        assert len(detections) == 1
        fake_text = PseudonymAnonymizer(seed=seed).apply(entity.text, detections)
        digits = "".join(c for c in fake_text if c.isdigit())
        assert len(digits) == 16
        assert not _luhn_ok(digits), f"가짜 카드번호가 진짜 Luhn을 통과함: {fake_text!r}"


_FAKE_PHONE_RE = re.compile(r"010-\d{4}-\d{4}")


def test_pseudonym_gives_same_fake_value_to_identical_repeated_value():
    """#166: pseudonym은 표기가 완전히 같은 반복 값에 같은 가명을 배정해야 한다(문맥 일관성)."""
    text = "자택 번호는 010-1234-5678이고, 직장 번호는 010-1234-5678 입니다."
    detections = PhoneDetector().detect(text)
    assert len(detections) == 2
    result = PseudonymAnonymizer(seed=1).apply(text, detections)
    fake_phones = _FAKE_PHONE_RE.findall(result)
    assert len(fake_phones) == 2
    assert fake_phones[0] == fake_phones[1]


def test_pseudonym_splits_identical_real_value_with_different_formatting():
    """#166: 알려진 한계 — label.py의 #164와 동일한 근본 원인. pseudonym도 (kind, Detection.text)
    로 "같은 개체"를 판별해서, 같은 실제 번호라도 표기(하이픈 유무 등)가 다르면 서로 다른
    가명 두 개를 받는다 — docstring이 약속하는 "그 사람이라는 문맥이 유지된다"가 깨진다.
    core가 표기 정규화 후 비교하도록 고치면 이 테스트가 깨져서 알 수 있다(현재 동작 고정용).
    """
    text = "자택 번호는 010-1234-5678이고, 직장 번호는 01012345678 입니다."
    detections = PhoneDetector().detect(text)
    assert len(detections) == 2
    result = PseudonymAnonymizer(seed=1).apply(text, detections)
    fake_phones = _FAKE_PHONE_RE.findall(result)
    assert len(fake_phones) == 2
    assert fake_phones[0] != fake_phones[1]
