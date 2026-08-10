# SPDX-License-Identifier: Apache-2.0

from fastapi.testclient import TestClient

from maskingtape_api.main import create_app
from maskingtape_api.routers.pii import anonymize, scan
from maskingtape_api.schemas import AnonymizeRequest, AnonymizeStrategy, DetectionKind, ScanRequest
from maskingtape_api.services.core_adapter import CoreEngineAdapter


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


def test_anonymize_endpoint_supports_label_strategy() -> None:
    response = anonymize(
        AnonymizeRequest(
            text="문의는 010-1234-5678로 주세요",
            strategy=AnonymizeStrategy.LABEL,
        ),
        core=CoreEngineAdapter(),
    )

    assert response.text == "문의는 [전화번호]로 주세요"
