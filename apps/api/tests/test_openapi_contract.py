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
    assert anonymize_operation["requestBody"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/AnonymizeRequest")
    assert anonymize_operation["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/AnonymizeResponse")
