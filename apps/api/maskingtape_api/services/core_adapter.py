# SPDX-License-Identifier: Apache-2.0

from functools import lru_cache
from typing import Protocol

from maskingtape import Pipeline
from maskingtape.anonymizers import LabelAnonymizer, MaskAnonymizer, PseudonymAnonymizer
from maskingtape.pipeline import AnonymizeResult
from maskingtape.types import Detection

from maskingtape_api.schemas import (
    AnonymizeResponse,
    AnonymizeStrategy,
    DetectionResponse,
    ScanResponse,
)


class CoreEngineError(RuntimeError):
    """Raised when the API adapter cannot complete a core engine call."""


class CorePipeline(Protocol):
    """Minimal core pipeline surface used by the API adapter."""

    def scan(self, text: str) -> list[Detection]:
        """Return core detections for text."""

    def anonymize(self, text: str) -> AnonymizeResult:
        """Return anonymized text and the detections used to produce it."""


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

    def anonymize(
        self,
        text: str,
        strategy: AnonymizeStrategy = AnonymizeStrategy.MASK,
    ) -> AnonymizeResponse:
        """Run core anonymization and return the public API response model."""
        try:
            pipeline = self._pipeline if strategy == AnonymizeStrategy.MASK else _pipeline_for_strategy(strategy)
            result = pipeline.anonymize(text)
            return AnonymizeResponse(
                text=result.text,
                detections=[_to_detection_response(detection) for detection in result.detections],
            )
        except Exception as exc:
            raise CoreEngineError("core anonymize failed") from exc


@lru_cache(maxsize=1)
def get_core_adapter() -> CoreEngineAdapter:
    """Return the shared rule-based core adapter for API requests."""
    return CoreEngineAdapter()


def _pipeline_for_strategy(strategy: AnonymizeStrategy) -> Pipeline:
    if strategy == AnonymizeStrategy.LABEL:
        return Pipeline(anonymizer=LabelAnonymizer())
    if strategy == AnonymizeStrategy.PSEUDONYM:
        return Pipeline(anonymizer=PseudonymAnonymizer())
    return Pipeline(anonymizer=MaskAnonymizer())


def _to_detection_response(detection: Detection) -> DetectionResponse:
    return DetectionResponse(
        kind=detection.kind,
        start=detection.start,
        end=detection.end,
        confidence=detection.confidence,
        detector=detection.detector,
    )
