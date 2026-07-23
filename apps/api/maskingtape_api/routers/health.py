# SPDX-License-Identifier: Apache-2.0

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Return a small liveness response for local and CI checks."""
    return {"status": "ok"}
