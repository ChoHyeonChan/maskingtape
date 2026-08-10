# SPDX-License-Identifier: Apache-2.0

from maskingtape_api.main import create_app


def test_openapi_contains_scan_and_anonymize_contracts() -> None:
    schema = create_app().openapi()

    assert "/scan" in schema["paths"]
    assert "/anonymize" in schema["paths"]

    scan_operation = schema["paths"]["/scan"]["post"]
    anonymize_operation = schema["paths"]["/anonymize"]["post"]

    assert scan_operation["requestBody"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/ScanRequest")
    assert scan_operation["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/ScanResponse")
    assert "501" not in scan_operation["responses"]
    assert "422" not in scan_operation["responses"]
    for status_code in ("400", "413", "429", "500"):
        assert scan_operation["responses"][status_code]["content"]["application/json"][
            "schema"
        ]["$ref"].endswith("/ErrorResponse")
    assert anonymize_operation["requestBody"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/AnonymizeRequest")
    assert anonymize_operation["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/AnonymizeResponse")
    assert "501" not in anonymize_operation["responses"]

    assert "422" not in anonymize_operation["responses"]
    for status_code in ("400", "413", "429", "500"):
        assert anonymize_operation["responses"][status_code]["content"]["application/json"][
            "schema"
        ]["$ref"].endswith("/ErrorResponse")

    detection_properties = schema["components"]["schemas"]["DetectionResponse"]["properties"]
    assert "text" not in detection_properties
