# SPDX-License-Identifier: Apache-2.0

from maskingtape_api.settings import (
    DEFAULT_CORS_ALLOWED_ORIGINS,
    get_api_settings,
)


def test_settings_default_to_local_web_dev_origins(monkeypatch) -> None:
    monkeypatch.delenv("MASKINGTAPE_API_ENV", raising=False)
    monkeypatch.delenv("MASKINGTAPE_API_CORS_ORIGINS", raising=False)

    settings = get_api_settings()

    assert settings.environment == "development"
    assert settings.cors_allowed_origins == DEFAULT_CORS_ALLOWED_ORIGINS


def test_settings_read_cors_origins_from_comma_separated_env(monkeypatch) -> None:
    monkeypatch.setenv("MASKINGTAPE_API_ENV", "demo")
    monkeypatch.setenv(
        "MASKINGTAPE_API_CORS_ORIGINS",
        "https://demo.example, http://localhost:5173, https://demo.example",
    )

    settings = get_api_settings()

    assert settings.environment == "demo"
    assert settings.cors_allowed_origins == (
        "https://demo.example",
        "http://localhost:5173",
    )
