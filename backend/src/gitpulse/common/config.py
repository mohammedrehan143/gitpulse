"""Centralized Configuration Settings for GitPulse Platform."""

from __future__ import annotations

from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General Environment
    GITPULSE_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # API Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    PORT: int | None = None
    CORS_ORIGINS: str | list[str] = ["http://localhost:5173", "http://localhost:3000", "*"]

    @field_validator("CORS_ORIGINS")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json

                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def server_port(self) -> int:
        return self.PORT or self.API_PORT

    # GitHub Ingestion & Automatic Discovery
    GITHUB_TOKEN: str = ""
    GITHUB_API_BASE_URL: str = "https://api.github.com"
    GITHUB_RATE_LIMIT_BUFFER: int = 100
    AUTO_DISCOVER_REPOSITORIES: bool = True
    REPO_DISCOVERY_INTERVAL_MINUTES: int = 60
    GITHUB_TARGET_REPOS: str = "apache/spark,fastapi/fastapi,facebook/react"

    # Supabase Relational Database & Cloud Storage
    DATABASE_URL: str = "sqlite+aiosqlite:///./gitpulse_dev.db"
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # Caching & Webhooks
    REDIS_URL: str = "redis://localhost:6379/0"
    GITHUB_WEBHOOK_SECRET: str = ""

    # Notifications & Webhooks
    DISCORD_WEBHOOK_URL: str = ""

    # AI & Multi-Agent LLM Orchestration
    LLM_PROVIDER: str = "groq"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""


settings = Settings()
