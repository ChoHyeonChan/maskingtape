# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from maskingtape import Pipeline
from maskingtape.anonymizers import (
    LabelAnonymizer,
    MaskAnonymizer,
    PseudonymAnonymizer,
)
from maskingtape.overlaps import resolve_overlaps
from maskingtape.pipeline import AnonymizeResult
from maskingtape.types import Detection

from maskingtape_api.schemas import (
    AnonymizeResponse,
    AnonymizeStrategy,
    DetectionResponse,
    ProcessingMode,
    ScanResponse,
)
from maskingtape_api.services.name_judge import NameJudge, NameJudgeError


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

    def scan(
        self,
        text: str,
        mode: ProcessingMode = ProcessingMode.RULE,
        name_judge: NameJudge | None = None,
        hybrid_failure_code: str | None = None,
    ) -> ScanResponse:
        """Run core detection and return the public API response model."""
        try:
            run = _detections_for_mode(
                text,
                self._pipeline.scan(text),
                mode,
                name_judge,
                hybrid_failure_code,
            )
            return ScanResponse(
                detections=[_to_detection_response(detection) for detection in run.detections],
                mode_used=run.mode_used,
                hybrid_failed=run.hybrid_failed,
                hybrid_failure_code=run.hybrid_failure_code,
            )
        except Exception as exc:
            raise CoreEngineError("core scan failed") from exc

    def anonymize(
        self,
        text: str,
        strategy: AnonymizeStrategy = AnonymizeStrategy.MASK,
        mode: ProcessingMode = ProcessingMode.RULE,
        name_judge: NameJudge | None = None,
        hybrid_failure_code: str | None = None,
    ) -> AnonymizeResponse:
        """Run core anonymization and return the public API response model."""
        try:
            pipeline = self._pipeline if strategy == AnonymizeStrategy.MASK else _pipeline_for_strategy(strategy)
            run = _detections_for_mode(
                text,
                pipeline.scan(text),
                mode,
                name_judge,
                hybrid_failure_code,
            )
            return AnonymizeResponse(
                text=_anonymizer_for_strategy(strategy).apply(text, run.detections),
                detections=[_to_detection_response(detection) for detection in run.detections],
                mode_used=run.mode_used,
                hybrid_failed=run.hybrid_failed,
                hybrid_failure_code=run.hybrid_failure_code,
            )
        except Exception as exc:
            raise CoreEngineError("core anonymize failed") from exc


@lru_cache(maxsize=1)
def get_core_adapter() -> CoreEngineAdapter:
    """Return the shared rule-based core adapter for API requests."""
    return CoreEngineAdapter()


def _pipeline_for_strategy(strategy: AnonymizeStrategy) -> Pipeline:
    return Pipeline(anonymizer=_anonymizer_for_strategy(strategy))


def _anonymizer_for_strategy(strategy: AnonymizeStrategy):
    if strategy == AnonymizeStrategy.LABEL:
        return LabelAnonymizer()
    if strategy == AnonymizeStrategy.PSEUDONYM:
        return PseudonymAnonymizer()
    return MaskAnonymizer()


def _to_detection_response(detection: Detection) -> DetectionResponse:
    return DetectionResponse(
        kind=detection.kind,
        start=detection.start,
        end=detection.end,
        confidence=detection.confidence,
        detector=detection.detector,
    )


@dataclass(frozen=True)
class _DetectionRun:
    detections: list[Detection]
    mode_used: ProcessingMode = ProcessingMode.RULE
    hybrid_failed: bool = False
    hybrid_failure_code: str | None = None


def _detections_for_mode(
    text: str,
    rule_detections: list[Detection],
    mode: ProcessingMode,
    name_judge: NameJudge | None,
    hybrid_failure_code: str | None,
) -> _DetectionRun:
    if mode == ProcessingMode.RULE:
        return _DetectionRun(detections=rule_detections)
    if hybrid_failure_code:
        return _hybrid_fallback(rule_detections, hybrid_failure_code)
    if name_judge is None:
        return _hybrid_fallback(rule_detections, "name_judge_unavailable")

    try:
        masked_text = LabelAnonymizer().apply(text, rule_detections)
        judge_detections = _name_detections_from_judge(
            text,
            name_judge.find_names(masked_text),
            name_judge.__class__.__name__,
        )
    except NameJudgeError as exc:
        return _hybrid_fallback(rule_detections, exc.code)

    return _DetectionRun(
        detections=resolve_overlaps([*rule_detections, *judge_detections], text),
        mode_used=ProcessingMode.HYBRID,
    )


def _hybrid_fallback(
    rule_detections: list[Detection],
    code: str,
) -> _DetectionRun:
    return _DetectionRun(
        detections=rule_detections,
        mode_used=ProcessingMode.RULE,
        hybrid_failed=True,
        hybrid_failure_code=code,
    )


def _name_detections_from_judge(
    text: str,
    names: list[str],
    detector_name: str,
) -> list[Detection]:
    detections: list[Detection] = []
    for name in dict.fromkeys(name.strip() for name in names):
        if not name or "[" in name or "]" in name:
            continue
        start = 0
        while (index := text.find(name, start)) != -1:
            end = index + len(name)
            detections.append(
                Detection(
                    kind="name",
                    start=index,
                    end=end,
                    text=text[index:end],
                    confidence=0.9,
                    detector=detector_name,
                )
            )
            start = end
    return detections
