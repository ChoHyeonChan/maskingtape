# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

import hashlib
import os
from dataclasses import replace
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import Headers
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import FileResponse, Response
from starlette.staticfiles import NotModifiedResponse
from starlette.types import Scope

from maskingtape_api.errors import http_exception_handler
from maskingtape_api.main import create_app
from maskingtape_api.settings import get_api_settings


class WebStaticFiles(StaticFiles):
    """Serve the built web app with content-based ETags (#569).

    Starlette's default ETag is md5("mtime-size"). Vercel's function bundle gives every
    file the same mtime (Last-Modified: Sat, 20 Oct 2018 01:46:40 GMT), and index.html
    keeps the same size across deploys because the hashed asset names have a fixed length.
    So the ETag never changed between deploys: a returning browser got 304, kept its old
    index.html, and loaded asset files that the new deploy no longer has, which left a
    blank page. Hash the content instead, and drop Last-Modified since the mtime is fake.
    """

    def file_response(
        self,
        full_path: str | os.PathLike[str],
        stat_result: os.stat_result,
        scope: Scope,
        status_code: int = 200,
    ) -> Response:
        digest = hashlib.md5(Path(full_path).read_bytes(), usedforsecurity=False).hexdigest()
        response = FileResponse(
            full_path,
            status_code=status_code,
            stat_result=stat_result,
            headers={"etag": f'"{digest}"'},
        )
        del response.headers["last-modified"]
        if self.is_not_modified(response.headers, Headers(scope=scope)):
            return NotModifiedResponse(response.headers)
        return response


app = FastAPI(
    title="maskingtape web demo",
    version="0.1.0",
    description="Vercel entrypoint: API under /api, the built web app for everything else.",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.mount("/api", create_app(replace(get_api_settings(), environment="production")))

# Vercel classifies this repo as a Python app and routes every path to this function,
# so the function also serves the built Vite frontend (apps/web/dist) for non-/api paths.
# /api is mounted first, so API routes win; StaticFiles(html=True) serves index.html for "/".
_web_dist = Path(__file__).resolve().parent.parent / "apps" / "web" / "dist"
if _web_dist.is_dir():
    app.mount("/", WebStaticFiles(directory=str(_web_dist), html=True), name="web")
