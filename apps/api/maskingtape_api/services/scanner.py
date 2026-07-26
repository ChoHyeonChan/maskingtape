# SPDX-License-Identifier: Apache-2.0

from functools import lru_cache

from maskingtape import Pipeline
from maskingtape.types import Detection

from maskingtape_api.schemas import DetectionResponse


@lru_cache(maxsize=1)
def get_pipeline() -> Pipeline:
    """Return the shared rule-based core pipeline for API requests."""
    return Pipeline()


def scan_text(text: str) -> list[DetectionResponse]:
    """Run core detection and convert results into API response models."""
    return [_to_detection_response(detection) for detection in get_pipeline().scan(text)]


def _to_detection_response(detection: Detection) -> DetectionResponse:
    return DetectionResponse(
        kind=detection.kind,
        start=detection.start,
        end=detection.end,
        text=detection.text,
        confidence=detection.confidence,
        detector=detection.detector,
    )
