# SPDX-License-Identifier: Apache-2.0

from maskingtape.types import Detection
from maskingtape.pipeline import AnonymizeResult

from maskingtape_api.schemas import AnonymizeStrategy, DetectionKind
from maskingtape_api.services.core_adapter import CoreEngineAdapter, CoreEngineError


class FakePipeline:
    def scan(self, text: str) -> list[Detection]:
        return [
            Detection(
                kind="email",
                start=0,
                end=len(text),
                text=text,
                confidence=1.0,
                detector="FakeDetector",
            )
        ]

    def anonymize(self, text: str) -> AnonymizeResult:
        detections = self.scan(text)
        return AnonymizeResult(text="*" * len(text), detections=detections)


class FailingPipeline:
    def scan(self, text: str) -> list[Detection]:
        raise ValueError("boom")

    def anonymize(self, text: str) -> AnonymizeResult:
        raise ValueError("boom")


class PassportPipeline:
    def scan(self, text: str) -> list[Detection]:
        return [
            Detection(
                kind="passport",
                start=0,
                end=len(text),
                text=text,
                confidence=1.0,
                detector="PassportDetector",
            )
        ]

    def anonymize(self, text: str) -> AnonymizeResult:
        detections = self.scan(text)
        return AnonymizeResult(text="*" * len(text), detections=detections)


def test_core_adapter_accepts_injected_pipeline() -> None:
    result = CoreEngineAdapter(pipeline=FakePipeline()).scan("sample@example.com")

    assert len(result.detections) == 1
    assert result.detections[0].kind == DetectionKind.EMAIL
    assert result.detections[0].detector == "FakeDetector"


def test_core_adapter_accepts_all_default_core_kinds() -> None:
    result = CoreEngineAdapter(pipeline=PassportPipeline()).scan("M12345678")

    assert result.detections[0].kind == DetectionKind.PASSPORT


def test_core_adapter_anonymize_masks_detected_spans() -> None:
    text = "sample@example.com"

    result = CoreEngineAdapter(pipeline=FakePipeline()).anonymize(text, AnonymizeStrategy.MASK)

    assert result.text == "*" * len(text)
    assert len(result.detections) == 1
    assert result.detections[0].kind == DetectionKind.EMAIL


def test_core_adapter_anonymize_supports_label_strategy() -> None:
    text = "sample@example.com"

    result = CoreEngineAdapter(pipeline=FakePipeline()).anonymize(text, AnonymizeStrategy.LABEL)

    assert text not in result.text
    assert result.text.startswith("[")
    assert result.text.endswith("]")


def test_core_adapter_wraps_pipeline_errors() -> None:
    try:
        CoreEngineAdapter(pipeline=FailingPipeline()).scan("합성 텍스트")
    except CoreEngineError as exc:
        assert isinstance(exc.__cause__, ValueError)
    else:
        raise AssertionError("CoreEngineError was not raised")


def test_core_adapter_wraps_anonymize_errors() -> None:
    try:
        CoreEngineAdapter(pipeline=FailingPipeline()).anonymize(
            "synthetic text",
            AnonymizeStrategy.MASK,
        )
    except CoreEngineError as exc:
        assert isinstance(exc.__cause__, ValueError)
    else:
        raise AssertionError("CoreEngineError was not raised")
