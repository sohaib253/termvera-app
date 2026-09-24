from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"

    database_url: str = "postgresql+asyncpg://tenderguard:tenderguard@localhost:5432/tenderguard"

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    cors_origins: list[str] = ["http://localhost:3000"]

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-opus-5"

    # ClauseRisk AI provider — "ollama" (local, default) or "claude" (cloud).
    # No module in app/services/clauserisk may branch on this string itself;
    # only app/services/clauserisk/ai/__init__.py's factory may.
    clauserisk_ai_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral:7b-instruct"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
