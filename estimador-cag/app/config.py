from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Defaults are fallbacks; matching vars in .env or the process environment override them.
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"

    primary_model: str = "gpt-4o-mini"
    fallback_model: str = "claude-haiku-4-5-20251001"
    llm_timeout: int = 30
    llm_retries: int = 2

    redis_url: str = "redis://localhost:6379"
    cache_ttl: int = 86400

    app_env: Literal["development", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "DEBUG"

    cors_allow_origins: str = "http://localhost:8501"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings (singleton)."""
    return Settings()


settings = get_settings()
