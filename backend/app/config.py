"""
Application configuration using Pydantic Settings.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "InvestCTR API"
    app_version: str = "0.1.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = Field(default=False)

    # API
    api_v1_prefix: str = "/api/v1"

    # Database (Supabase PostgreSQL)
    database_url: PostgresDsn | None = None

    # Supabase
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_key: str | None = None

    # Redis
    redis_url: RedisDsn | None = None

    # JWT / Auth
    jwt_secret: str | None = None
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # Claude API (Anthropic)
    anthropic_api_key: str | None = None

    # LSEG (Market Data Premium)
    lseg_app_key: str | None = None
    lseg_username: str | None = None
    lseg_password: str | None = None

    # CORS - accepts comma-separated string or JSON array
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "https://investctr.vercel.app",
            "https://investctr-git-main-antonio-jrs-projects.vercel.app",
        ]
    )

    # Celery
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
