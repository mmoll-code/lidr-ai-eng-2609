"""Tests for application settings."""

import pytest
from pydantic import ValidationError

from app.config import Settings

_SESSION_3_ENV_KEYS = (
    "PRIMARY_MODEL",
    "FALLBACK_MODEL",
    "LLM_TIMEOUT",
    "LLM_RETRIES",
    "REDIS_URL",
    "CACHE_TTL",
    "APP_ENV",
    "LOG_LEVEL",
    "CORS_ALLOW_ORIGINS",
)


def _isolated_settings(monkeypatch: pytest.MonkeyPatch, **env: str) -> Settings:
    for key in _SESSION_3_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return Settings(_env_file=None)


class TestSession3Settings:
    def test_defaults_when_env_is_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        settings = _isolated_settings(monkeypatch)

        assert settings.primary_model == "gpt-4o-mini"
        assert settings.fallback_model == "claude-haiku-4-5-20251001"
        assert settings.llm_timeout == 30
        assert settings.llm_retries == 2
        assert settings.redis_url == "redis://localhost:6379"
        assert settings.cache_ttl == 86400
        assert settings.app_env == "development"
        assert settings.log_level == "DEBUG"
        assert settings.cors_allow_origins == "http://localhost:8501"

    def test_env_overrides_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        settings = _isolated_settings(
            monkeypatch,
            PRIMARY_MODEL="gpt-4o",
            FALLBACK_MODEL="claude-sonnet-4-5",
            LLM_TIMEOUT="15",
            LLM_RETRIES="1",
            REDIS_URL="redis://redis:6379",
            CACHE_TTL="60",
            APP_ENV="production",
            LOG_LEVEL="INFO",
            CORS_ALLOW_ORIGINS="http://localhost:8501,http://localhost:3000",
        )

        assert settings.primary_model == "gpt-4o"
        assert settings.fallback_model == "claude-sonnet-4-5"
        assert settings.llm_timeout == 15
        assert settings.llm_retries == 1
        assert settings.redis_url == "redis://redis:6379"
        assert settings.cache_ttl == 60
        assert settings.app_env == "production"
        assert settings.log_level == "INFO"
        assert settings.cors_allow_origins == "http://localhost:8501,http://localhost:3000"

    def test_invalid_app_env_is_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with pytest.raises(ValidationError):
            _isolated_settings(monkeypatch, APP_ENV="local")
