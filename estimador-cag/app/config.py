from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Defaults are fallbacks; matching vars in .env or the process environment override them.
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"


settings = Settings()
