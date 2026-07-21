"""mask_quality.py의 유출(leak) 판정과 구조 보존(길이) 검증 로직을 확인한다."""

from __future__ import annotations

from maskingtape.pipeline import Pipeline

from bench.mask_quality import evaluate_mask_quality, format_mask_quality_report


def test_no_leak_when_pii_is_correctly_masked():
    """core가 실제로 탐지·마스킹하는 phone은 원문이 결과에 남으면 안 된다."""
    rows = [{"text": "010-1234-5678로 연락주세요.", "labels": [{"kind": "phone", "start": 0, "end": 13}]}]
    result = evaluate_mask_quality(rows, Pipeline())
    assert result.leak_count == 0
    assert result.gold_pii_count == 1


def test_leak_detected_when_kind_has_no_detector_yet():
    """core에 아직 탐지기가 없는 name은 마스킹이 전혀 안 되므로 유출로 잡혀야 한다."""
    rows = [{"text": "김민준님 안녕하세요.", "labels": [{"kind": "name", "start": 0, "end": 3}]}]
    result = evaluate_mask_quality(rows, Pipeline())
    assert result.leak_count == 1
    assert result.leaks[0].kind == "name"
    assert result.leaks[0].value == "김민준"


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
    result = evaluate_mask_quality(rows, Pipeline())
    report = format_mask_quality_report(result)
    assert "유출" in report
    assert "name" in report
