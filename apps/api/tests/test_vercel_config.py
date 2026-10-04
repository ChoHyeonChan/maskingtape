# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

import json
import re
from pathlib import Path


def test_spa_rewrite_does_not_capture_static_assets() -> None:
    config_path = Path(__file__).resolve().parents[3] / "vercel.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    rewrite_source = config["rewrites"][0]["source"]

    assert re.fullmatch(rewrite_source, "/demo")
    assert not re.fullmatch(rewrite_source, "/api/health")
    assert not re.fullmatch(rewrite_source, "/assets/index-Bb75dFf9.js")
    assert not re.fullmatch(rewrite_source, "/assets/index-JsUtNOH6.css")
    assert not re.fullmatch(rewrite_source, "/favicon.ico")


def test_spa_rewrite_does_not_capture_public_files() -> None:
    """Files in apps/web/public are served from the root, not /assets."""
    config_path = Path(__file__).resolve().parents[3] / "vercel.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    rewrite_source = config["rewrites"][0]["source"]
    public_dir = Path(__file__).resolve().parents[2] / "web" / "public"

    for public_file in public_dir.iterdir():
        assert not re.fullmatch(rewrite_source, f"/{public_file.name}"), public_file.name
    assert re.fullmatch(rewrite_source, "/")
    assert re.fullmatch(rewrite_source, "/accuracy")
