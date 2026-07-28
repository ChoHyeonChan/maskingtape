# SPDX-License-Identifier: Apache-2.0

import json

from maskingtape_api.routers.pii import anonymize, scan
from maskingtape_api.schemas import AnonymizeRequest, ScanRequest
from maskingtape_api.services.core_adapter import CoreEngineError


class FailingCore:
    def scan(self, text: str):
        raise CoreEngineError("core scan failed")

    def anonymize(self, text: str, strategy):
        raise CoreEngineError("core anonymize failed")


def test_scan_endpoint_returns_shared_error_shape_on_core_failure() -> None:
    response = scan(ScanRequest(text="합성 텍스트"), core=FailingCore())

    assert response.status_code == 500
    assert json.loads(response.body) == {
        "code": "core_scan_failed",
        "message": "core 탐지 엔진 호출에 실패했습니다.",
        "details": None,
    }


def test_anonymize_endpoint_returns_shared_error_shape_on_core_failure() -> None:
    response = anonymize(AnonymizeRequest(text="합성 텍스트"), core=FailingCore())

    assert response.status_code == 500
    assert json.loads(response.body) == {
        "code": "core_anonymize_failed",
        "message": "core 비식별화 엔진 호출에 실패했습니다.",
        "details": None,
    }
