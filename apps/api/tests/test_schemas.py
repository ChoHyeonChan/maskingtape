# SPDX-License-Identifier: Apache-2.0

import pytest
from pydantic import ValidationError

from maskingtape_api.schemas import (
    AnonymizeRequest,
    AnonymizeStrategy,
    DetectionKind,
    DetectionResponse,
    ScanRequest,
)


def test_scan_request_accepts_text() -> None:
    request = ScanRequest(text="테스트 문서입니다.")

    assert request.text == "테스트 문서입니다."


def test_scan_request_rejects_empty_text() -> None:
    with pytest.raises(ValidationError):
        ScanRequest(text="")


def test_anonymize_request_defaults_to_mask_strategy() -> None:
    request = AnonymizeRequest(text="테스트 문서입니다.")

    assert request.strategy == AnonymizeStrategy.MASK


def test_detection_response_matches_core_detection_shape() -> None:
    detection = DetectionResponse(
        kind=DetectionKind.RRN,
        start=10,
        end=24,
        text="000000-0000000",
        confidence=1.0,
        detector="RRNDetector",
    )

    assert detection.model_dump(mode="json") == {
        "kind": "rrn",
        "start": 10,
        "end": 24,
        "text": "000000-0000000",
        "confidence": 1.0,
        "detector": "RRNDetector",
    }
