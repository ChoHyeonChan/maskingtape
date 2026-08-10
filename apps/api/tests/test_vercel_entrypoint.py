# SPDX-License-Identifier: Apache-2.0

from fastapi.testclient import TestClient

from api.index import app


def test_vercel_entrypoint_mounts_api_under_api_prefix() -> None:
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_vercel_entrypoint_serves_scan_without_echoing_raw_detection_text() -> None:
    client = TestClient(app)
    passport = "M12345678"

    response = client.post("/api/scan", json={"text": f"passport {passport} check"})

    assert response.status_code == 200
    assert passport not in response.text
    detection = response.json()["detections"][0]
    assert detection["kind"] == "passport"
    assert "text" not in detection
