from pydantic_settings import BaseSettings, SettingsConfigDict


class UiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    estimator_api_url: str = "http://localhost:8000"
    estimator_request_timeout_seconds: float = 120.0
    primary_model: str = "gpt-4o-mini"
    fallback_model: str = "claude-haiku-4-5-20251001"
    cache_ttl: int = 86400


ui_settings = UiSettings()
