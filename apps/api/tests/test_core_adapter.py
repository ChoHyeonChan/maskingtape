# SPDX-License-Identifier: Apache-2.0

from maskingtape.types import Detection

from maskingtape_api.schemas import DetectionKind
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


class FailingPipeline:
    def scan(self, text: str) -> list[Detection]:
        raise ValueError("boom")


def test_core_adapter_accepts_injected_pipeline() -> None:
    result = CoreEngineAdapter(pipeline=FakePipeline()).scan("sample@example.com")

    assert len(result.detections) == 1
    assert result.detections[0].kind == DetectionKind.EMAIL
    assert result.detections[0].detector == "FakeDetector"


def test_core_adapter_wraps_pipeline_errors() -> None:
    try:
        CoreEngineAdapter(pipeline=FailingPipeline()).scan("합성 텍스트")
    except CoreEngineError as exc:
        assert isinstance(exc.__cause__, ValueError)
    else:
        raise AssertionError("CoreEngineError was not raised")
