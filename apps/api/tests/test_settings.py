# SPDX-License-Identifier: Apache-2.0

from maskingtape_api.settings import (
    DEFAULT_CORS_ALLOWED_ORIGINS,
    DEFAULT_MAX_BODY_BYTES,
    DEFAULT_PRODUCTION_CORS_ALLOWED_ORIGINS,
    DEFAULT_RATE_LIMIT_MAX_BUCKETS,
    DEFAULT_RATE_LIMIT_REQUESTS,
    DEFAULT_RATE_LIMIT_WINDOW_SECONDS,
    get_api_settings,
)


def test_settings_default_to_local_web_dev_origins(monkeypatch) -> None:
    monkeypatch.delenv("MASKINGTAPE_API_ENV", raising=False)
    monkeypatch.delenv("MASKINGTAPE_API_CORS_ORIGINS", raising=False)

    settings = get_api_settings()

    assert settings.environment == "development"
    assert settings.cors_allowed_origins == DEFAULT_CORS_ALLOWED_ORIGINS
    assert settings.rate_limit_requests == DEFAULT_RATE_LIMIT_REQUESTS
    assert settings.rate_limit_window_seconds == DEFAULT_RATE_LIMIT_WINDOW_SECONDS
    assert settings.rate_limit_max_buckets == DEFAULT_RATE_LIMIT_MAX_BUCKETS
    assert settings.max_body_bytes == DEFAULT_MAX_BODY_BYTES


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


def test_settings_disable_cors_by_default_in_production(monkeypatch) -> None:
    monkeypatch.setenv("MASKINGTAPE_API_ENV", "production")
    monkeypatch.delenv("MASKINGTAPE_API_CORS_ORIGINS", raising=False)

    settings = get_api_settings()

    assert settings.environment == "production"
    assert settings.cors_allowed_origins == DEFAULT_PRODUCTION_CORS_ALLOWED_ORIGINS


def test_settings_read_rate_limit_from_env(monkeypatch) -> None:
    monkeypatch.setenv("MASKINGTAPE_API_RATE_LIMIT_REQUESTS", "3")
    monkeypatch.setenv("MASKINGTAPE_API_RATE_LIMIT_WINDOW_SECONDS", "10")
    monkeypatch.setenv("MASKINGTAPE_API_RATE_LIMIT_MAX_BUCKETS", "7")

    settings = get_api_settings()

    assert settings.rate_limit_requests == 3
    assert settings.rate_limit_window_seconds == 10
    assert settings.rate_limit_max_buckets == 7


def test_settings_read_max_body_bytes_from_env(monkeypatch) -> None:
    monkeypatch.setenv("MASKINGTAPE_API_MAX_BODY_BYTES", "512")

    settings = get_api_settings()

    assert settings.max_body_bytes == 512


def test_settings_ignore_invalid_rate_limit_env(monkeypatch) -> None:
    monkeypatch.setenv("MASKINGTAPE_API_RATE_LIMIT_REQUESTS", "0")
    monkeypatch.setenv("MASKINGTAPE_API_RATE_LIMIT_WINDOW_SECONDS", "abc")
    monkeypatch.setenv("MASKINGTAPE_API_RATE_LIMIT_MAX_BUCKETS", "-1")
    monkeypatch.setenv("MASKINGTAPE_API_MAX_BODY_BYTES", "0")

    settings = get_api_settings()

    assert settings.rate_limit_requests == DEFAULT_RATE_LIMIT_REQUESTS
    assert settings.rate_limit_window_seconds == DEFAULT_RATE_LIMIT_WINDOW_SECONDS
    assert settings.rate_limit_max_buckets == DEFAULT_RATE_LIMIT_MAX_BUCKETS
    assert settings.max_body_bytes == DEFAULT_MAX_BODY_BYTES
