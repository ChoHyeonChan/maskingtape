from maskingtape_api.main import create_app
from maskingtape_api.routers.health import health


def test_health_returns_ok() -> None:
    assert health() == {"status": "ok"}


def test_health_route_is_registered() -> None:
    app = create_app()

    assert "/health" in app.openapi()["paths"]
