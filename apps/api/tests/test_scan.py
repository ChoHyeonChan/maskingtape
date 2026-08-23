# SPDX-License-Identifier: Apache-2.0

from fastapi.testclient import TestClient

from maskingtape.pipeline import AnonymizeResult
from maskingtape.types import Detection
from maskingtape_api.main import create_app
from maskingtape_api.routers.pii import anonymize, scan
from maskingtape_api.schemas import AnonymizeRequest, AnonymizeStrategy, DetectionKind, ScanRequest
from maskingtape_api.services.core_adapter import CoreEngineAdapter, get_core_adapter


class UnknownKindPipeline:
    def scan(self, text: str) -> list[Detection]:
        return [
            Detection(
                kind="future_kind",
                start=0,
                end=len(text),
                text=text,
                confidence=0.8,
                detector="FutureDetector",
            )
        ]

    def anonymize(self, text: str) -> AnonymizeResult:
        return AnonymizeResult(text="*" * len(text), detections=self.scan(text))


def test_core_adapter_returns_core_detections() -> None:
    text = "고객 주민번호 800101-1234560 확인 부탁드립니다"

    detections = CoreEngineAdapter().scan(text).detections

    assert len(detections) == 1
    assert detections[0].kind == DetectionKind.RRN
    assert text[detections[0].start : detections[0].end] == "800101-1234560"
    assert "text" not in detections[0].model_dump(mode="json")


def test_scan_endpoint_returns_response_model() -> None:
    response = scan(ScanRequest(text="문의는 010-1234-5678로 주세요"), core=CoreEngineAdapter())

    assert len(response.detections) == 1
    assert response.detections[0].kind == DetectionKind.PHONE


def test_scan_endpoint_returns_empty_list_for_clean_text() -> None:
    response = scan(ScanRequest(text="오늘 회의는 오후 3시입니다"), core=CoreEngineAdapter())

    assert response.detections == []


def test_scan_http_endpoint_accepts_passport_detection_kind() -> None:
    passport = "M12345678"

    response = TestClient(create_app()).post(
        "/scan",
        json={"text": f"여권번호 {passport} 확인"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["detections"][0]["kind"] == DetectionKind.PASSPORT
    assert "text" not in payload["detections"][0]
    assert passport not in response.text


def test_anonymize_endpoint_returns_masked_text_and_detections() -> None:
    response = anonymize(
        AnonymizeRequest(text="문의는 010-1234-5678로 주세요"),
        core=CoreEngineAdapter(),
    )

    assert response.text == "문의는 *************로 주세요"
    assert len(response.detections) == 1
    assert response.detections[0].kind == DetectionKind.PHONE


def test_anonymize_http_endpoint_accepts_passport_detection_kind() -> None:
    passport = "M12345678"

    response = TestClient(create_app()).post(
        "/anonymize",
        json={"text": f"여권번호 {passport} 확인"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["detections"][0]["kind"] == DetectionKind.PASSPORT
    assert "text" not in payload["detections"][0]
    assert passport not in payload["text"]
    assert passport not in response.text


def test_anonymize_http_endpoint_supports_pseudonym_strategy() -> None:
    rrn = "800101-1234560"

    response = TestClient(create_app()).post(
        "/anonymize",
        json={"text": f"주민번호 {rrn} 확인", "strategy": "pseudonym"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert rrn not in payload["text"]
    assert "*" not in payload["text"]
    assert "[주민등록번호]" not in payload["text"]
    assert payload["detections"][0]["kind"] == DetectionKind.RRN


def test_scan_http_endpoint_passes_unknown_detection_kind_without_500() -> None:
    app = create_app()
    app.dependency_overrides[get_core_adapter] = lambda: CoreEngineAdapter(
        pipeline=UnknownKindPipeline()
    )

    try:
        response = TestClient(app).post("/scan", json={"text": "future-token"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["detections"][0]["kind"] == "future_kind"
    assert payload["detections"][0]["detector"] == "FutureDetector"


def test_anonymize_http_endpoint_passes_unknown_detection_kind_without_500() -> None:
    app = create_app()
    app.dependency_overrides[get_core_adapter] = lambda: CoreEngineAdapter(
        pipeline=UnknownKindPipeline()
    )

    try:
        response = TestClient(app).post("/anonymize", json={"text": "future-token"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["text"] == "************"
    assert payload["detections"][0]["kind"] == "future_kind"
    assert payload["detections"][0]["detector"] == "FutureDetector"


def test_anonymize_endpoint_supports_label_strategy() -> None:
    response = anonymize(
        AnonymizeRequest(
            text="문의는 010-1234-5678로 주세요",
            strategy=AnonymizeStrategy.LABEL,
        ),
        core=CoreEngineAdapter(),
    )

    assert response.text == "문의는 [전화번호]로 주세요"
