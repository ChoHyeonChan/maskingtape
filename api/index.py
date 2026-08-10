# SPDX-License-Identifier: Apache-2.0

from fastapi import FastAPI

from maskingtape_api.main import create_app


app = FastAPI(
    title="maskingtape web demo",
    version="0.1.0",
    description="Vercel entrypoint that serves the API under /api.",
)
app.mount("/api", create_app())
