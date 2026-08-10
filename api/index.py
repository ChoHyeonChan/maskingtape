# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from maskingtape_api.main import create_app

app = FastAPI(
    title="maskingtape web demo",
    version="0.1.0",
    description="Vercel entrypoint: API under /api, the built web app for everything else.",
)
app.mount("/api", create_app())

# Vercel classifies this repo as a Python app and routes every path to this function,
# so the function also serves the built Vite frontend (apps/web/dist) for non-/api paths.
# /api is mounted first, so API routes win; StaticFiles(html=True) serves index.html for "/".
_web_dist = Path(__file__).resolve().parent.parent / "apps" / "web" / "dist"
if _web_dist.is_dir():
    app.mount("/", StaticFiles(directory=str(_web_dist), html=True), name="web")
