# SPDX-License-Identifier: Apache-2.0

import pytest
from pydantic import ValidationError

from maskingtape.detectors import default_detectors
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


def test_anonymize_request_accepts_pseudonym_strategy() -> None:
    request = AnonymizeRequest(text="테스트 문서입니다.", strategy="pseudonym")

    assert request.strategy == AnonymizeStrategy.PSEUDONYM


def test_detection_response_excludes_original_text() -> None:
    detection = DetectionResponse(
        kind=DetectionKind.RRN,
        start=10,
        end=24,
        confidence=1.0,
        detector="RRNDetector",
    )

    assert detection.model_dump(mode="json") == {
        "kind": "rrn",
        "start": 10,
        "end": 24,
        "confidence": 1.0,
        "detector": "RRNDetector",
    }


def test_detection_response_accepts_business_registration_kind() -> None:
    detection = DetectionResponse(
        kind=DetectionKind.BIZ_REG,
        start=0,
        end=12,
        confidence=1.0,
        detector="BusinessRegistrationDetector",
    )

    assert detection.kind == DetectionKind.BIZ_REG
    assert detection.model_dump(mode="json")["kind"] == "biz_reg"


def test_detection_response_accepts_passport_kind() -> None:
    detection = DetectionResponse(
        kind=DetectionKind.PASSPORT,
        start=0,
        end=9,
        confidence=0.9,
        detector="PassportDetector",
    )

    assert detection.kind == DetectionKind.PASSPORT
    assert detection.model_dump(mode="json")["kind"] == "passport"


def test_detection_response_passes_unknown_kind_through_as_string() -> None:
    detection = DetectionResponse(
        kind="future_kind",
        start=0,
        end=6,
        confidence=0.8,
        detector="FutureDetector",
    )

    assert detection.kind == "future_kind"
    assert detection.model_dump(mode="json")["kind"] == "future_kind"


def test_detection_kind_matches_core_default_detector_kinds() -> None:
    core_kinds = {detector.kind for detector in default_detectors()}
    api_kinds = {kind.value for kind in DetectionKind}

    assert api_kinds == core_kinds
