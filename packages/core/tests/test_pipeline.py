"""파이프라인 통합 테스트 — 합성 데이터만 사용한다."""

from maskingtape import Pipeline

SYNTHETIC = "고객 주민번호 800101-1234560 확인 부탁드립니다"


def test_anonymize_masks_rrn():
    result = Pipeline().anonymize(SYNTHETIC)
    assert "800101-1234560" not in result.text
    assert result.text.count("*") == len("800101-1234560")
    assert len(result.detections) == 1


def test_scan_reports_correct_positions():
    d = Pipeline().scan(SYNTHETIC)[0]
    assert SYNTHETIC[d.start : d.end] == d.text


def test_clean_text_untouched():
    clean = "오늘 회의는 오후 3시입니다"
    result = Pipeline().anonymize(clean)
    assert result.text == clean
    assert result.detections == []
