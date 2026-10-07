# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.index import WebStaticFiles, app

# Vercel 함수 번들은 모든 파일의 수정 시각을 이 값으로 맞춘다(응답 Last-Modified가
# Sat, 20 Oct 2018 01:46:40 GMT). 배포가 바뀌어도 index.html은 이 시각에 크기도 같다.
_VERCEL_BUNDLE_MTIME = 1540000000


def _write_index(directory: Path, asset_hash: str) -> None:
    index = directory / "index.html"
    index.write_text(f'<script src="/assets/index-{asset_hash}.js"></script>', encoding="utf-8")
    os.utime(index, (_VERCEL_BUNDLE_MTIME, _VERCEL_BUNDLE_MTIME))


def _web_client(directory: Path) -> TestClient:
    web = FastAPI()
    web.mount("/", WebStaticFiles(directory=str(directory), html=True), name="web")
    return TestClient(web)


def test_vercel_entrypoint_mounts_api_under_api_prefix(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "hybrid_available": False}


def test_vercel_entrypoint_disables_public_api_docs() -> None:
    client = TestClient(app)

    for path in ("/docs", "/redoc", "/openapi.json", "/api/docs", "/api/redoc", "/api/openapi.json"):
        response = client.get(path)
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"


def test_vercel_entrypoint_serves_scan_without_echoing_raw_detection_text() -> None:
    client = TestClient(app)
    passport = "M12345678"

    response = client.post("/api/scan", json={"text": f"passport {passport} check"})

    assert response.status_code == 200
    assert passport not in response.text
    detection = response.json()["detections"][0]
    assert detection["kind"] == "passport"
    assert "text" not in detection


def test_web_page_is_resent_after_a_deploy_even_if_size_and_mtime_match(tmp_path: Path) -> None:
    # 옛 ETag로 물었을 때 304를 주면 브라우저가 옛 HTML을 계속 쓰고, 옛 HTML이 가리키는
    # 에셋은 새 배포에 없어 빈 화면이 된다(#569). 내용이 바뀌었으면 200으로 새 HTML을 준다.
    _write_index(tmp_path, "OLD11111")
    client = _web_client(tmp_path)
    old_etag = client.get("/").headers["etag"]

    _write_index(tmp_path, "NEW22222")
    response = client.get("/", headers={"If-None-Match": old_etag})

    assert response.status_code == 200
    assert "index-NEW22222.js" in response.text


def test_web_page_still_answers_304_when_content_is_unchanged(tmp_path: Path) -> None:
    _write_index(tmp_path, "SAME3333")
    client = _web_client(tmp_path)
    etag = client.get("/").headers["etag"]

    response = client.get("/", headers={"If-None-Match": etag})

    assert response.status_code == 304


def test_web_page_does_not_trust_the_bundle_mtime(tmp_path: Path) -> None:
    # 수정 시각이 전부 같아 Last-Modified도 믿을 수 없다. 보내지 않고, If-Modified-Since만
    # 보내는 클라이언트에게도 새 내용을 준다.
    _write_index(tmp_path, "OLD11111")
    client = _web_client(tmp_path)
    assert "last-modified" not in client.get("/").headers

    _write_index(tmp_path, "NEW22222")
    response = client.get("/", headers={"If-Modified-Since": "Sat, 20 Oct 2018 01:46:40 GMT"})

    assert response.status_code == 200
    assert "index-NEW22222.js" in response.text
