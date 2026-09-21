from pydantic_settings import BaseSettings, SettingsConfigDict


class UiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    estimator_api_url: str = "http://localhost:8000"
    estimator_request_timeout_seconds: float = 120.0


ui_settings = UiSettings()
