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

    # PostgreSQL Relational Storage
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "gitpulse"
    POSTGRES_USER: str = "gitpulse_admin"
    POSTGRES_PASSWORD: str = "gitpulse_secure_password"
    DATABASE_URL: str = "sqlite+aiosqlite:///./gitpulse_dev.db"

    # Streaming & Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_RAW_EVENTS: str = "gitpulse.github.raw_events"
    KAFKA_TOPIC_COMMITS: str = "gitpulse.github.commits"
    KAFKA_TOPIC_PULL_REQUESTS: str = "gitpulse.github.pull_requests"
    KAFKA_CONSUMER_GROUP: str = "gitpulse-stream-processors"

    # MinIO / Lakehouse
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_LAKEHOUSE: str = "gitpulse-lakehouse"

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
