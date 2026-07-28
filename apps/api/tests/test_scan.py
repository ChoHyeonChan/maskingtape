# SPDX-License-Identifier: Apache-2.0

from maskingtape_api.routers.pii import anonymize, scan
from maskingtape_api.schemas import AnonymizeRequest, AnonymizeStrategy, DetectionKind, ScanRequest
from maskingtape_api.services.core_adapter import CoreEngineAdapter


def test_core_adapter_returns_core_detections() -> None:
    text = "고객 주민번호 800101-1234560 확인 부탁드립니다"

    detections = CoreEngineAdapter().scan(text).detections

    assert len(detections) == 1
    assert detections[0].kind == DetectionKind.RRN
    assert detections[0].text == "800101-1234560"
    assert text[detections[0].start : detections[0].end] == detections[0].text


def test_scan_endpoint_returns_response_model() -> None:
    response = scan(ScanRequest(text="문의는 010-1234-5678로 주세요"), core=CoreEngineAdapter())

    assert len(response.detections) == 1
    assert response.detections[0].kind == DetectionKind.PHONE


def test_scan_endpoint_returns_empty_list_for_clean_text() -> None:
    response = scan(ScanRequest(text="오늘 회의는 오후 3시입니다"), core=CoreEngineAdapter())

    assert response.detections == []


def test_anonymize_endpoint_returns_masked_text_and_detections() -> None:
    response = anonymize(
        AnonymizeRequest(text="문의는 010-1234-5678로 주세요"),
        core=CoreEngineAdapter(),
    )

    assert response.text == "문의는 *************로 주세요"
    assert len(response.detections) == 1
    assert response.detections[0].kind == DetectionKind.PHONE


def test_anonymize_endpoint_supports_label_strategy() -> None:
    response = anonymize(
        AnonymizeRequest(
            text="문의는 010-1234-5678로 주세요",
            strategy=AnonymizeStrategy.LABEL,
        ),
        core=CoreEngineAdapter(),
    )

    assert response.text == "문의는 [전화번호]로 주세요"
