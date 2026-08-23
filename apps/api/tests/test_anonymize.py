# SPDX-License-Identifier: Apache-2.0

import re

from maskingtape_api.routers.pii import anonymize
from maskingtape_api.schemas import AnonymizeRequest, AnonymizeStrategy, DetectionKind
from maskingtape_api.services.core_adapter import CoreEngineAdapter

_PSEUDO_PHONE = re.compile(r"010-\d{4}-\d{4}")


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
    phone = "010-1234-5678"
    text = f"Call {phone} now"

    response = anonymize(
        AnonymizeRequest(text=text, strategy=AnonymizeStrategy.PSEUDONYM),
        core=CoreEngineAdapter(),
    )

    # 원본은 사라지고(유출 방지), 별표·라벨이 아닌 그럴듯한 가짜 번호로 치환된다.
    assert phone not in response.text
    assert "*" not in response.text
    assert "[" not in response.text
    assert _PSEUDO_PHONE.search(response.text) is not None
    assert len(response.detections) == 1
    assert response.detections[0].kind == DetectionKind.PHONE


def test_pseudonym_replaces_same_value_consistently() -> None:
    # 가명처리의 핵심: 같은 원본값은 한 응답 안에서 같은 가짜값으로 치환된다("그 사람" 문맥 유지).
    phone = "010-1234-5678"
    text = f"Call {phone} or {phone} again"

    response = anonymize(
        AnonymizeRequest(text=text, strategy=AnonymizeStrategy.PSEUDONYM),
        core=CoreEngineAdapter(),
    )

    fakes = _PSEUDO_PHONE.findall(response.text)
    assert len(fakes) == 2
    assert fakes[0] == fakes[1]
    assert fakes[0] != phone
