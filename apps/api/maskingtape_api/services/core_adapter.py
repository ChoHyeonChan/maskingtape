# SPDX-License-Identifier: Apache-2.0

from functools import lru_cache
from typing import Protocol

from maskingtape import Pipeline
from maskingtape.types import Detection

from maskingtape_api.schemas import DetectionResponse, ScanResponse


class CoreEngineError(RuntimeError):
    """Raised when the API adapter cannot complete a core engine call."""


class CorePipeline(Protocol):
    """Minimal core pipeline surface used by the API adapter."""

    def scan(self, text: str) -> list[Detection]:
        """Return core detections for text."""


class CoreEngineAdapter:
    """Small boundary object between FastAPI handlers and packages/core."""

    def __init__(self, pipeline: CorePipeline | None = None) -> None:
        self._pipeline = pipeline if pipeline is not None else Pipeline()

    def scan(self, text: str) -> ScanResponse:
        """Run core detection and return the public API response model."""
        try:
            detections = self._pipeline.scan(text)
            return ScanResponse(
                detections=[_to_detection_response(detection) for detection in detections]
            )
        except Exception as exc:
            raise CoreEngineError("core scan failed") from exc


@lru_cache(maxsize=1)
def get_core_adapter() -> CoreEngineAdapter:
    """Return the shared rule-based core adapter for API requests."""
    return CoreEngineAdapter()


def _to_detection_response(detection: Detection) -> DetectionResponse:
    return DetectionResponse(
        kind=detection.kind,
        start=detection.start,
        end=detection.end,
        text=detection.text,
        confidence=detection.confidence,
        detector=detection.detector,
    )
