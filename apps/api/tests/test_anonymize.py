# SPDX-License-Identifier: Apache-2.0

from maskingtape_api.routers.pii import anonymize
from maskingtape_api.schemas import AnonymizeRequest, AnonymizeStrategy, DetectionKind
from maskingtape_api.services.core_adapter import CoreEngineAdapter


def test_anonymize_endpoint_returns_masked_text_and_detections() -> None:
    text = "Contact sample@example.com"

    response = anonymize(AnonymizeRequest(text=text), core=CoreEngineAdapter())

    assert response.text != text
    assert "sample@example.com" not in response.text
    assert len(response.detections) == 1
    assert response.detections[0].kind == DetectionKind.EMAIL


def test_anonymize_endpoint_supports_label_strategy() -> None:
    phone = "010-1234-5678"
    text = f"Call {phone} now"

    response = anonymize(
        AnonymizeRequest(text=text, strategy=AnonymizeStrategy.LABEL),
        core=CoreEngineAdapter(),
    )

    assert phone not in response.text
    assert "[" in response.text
    assert "]" in response.text
    assert len(response.detections) == 1
    assert response.detections[0].kind == DetectionKind.PHONE


def test_anonymize_endpoint_supports_pseudonym_strategy() -> None:
    rrn = "800101-1234560"
    text = f"주민번호 {rrn} 확인"

    response = anonymize(
        AnonymizeRequest(text=text, strategy=AnonymizeStrategy.PSEUDONYM),
        core=CoreEngineAdapter(),
    )

    assert rrn not in response.text
    assert "*" not in response.text
    assert "[주민등록번호]" not in response.text
    assert len(response.detections) == 1
    assert response.detections[0].kind == DetectionKind.RRN
