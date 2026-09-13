from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("*", mode="before")
    @classmethod
    def strip_whitespace(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v

    # ── Database ────────────────────────────────────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://plateforme:plateforme@postgres:5432/plateforme"
    )
    database_url_sync: str = (
        "postgresql+psycopg2://plateforme:plateforme@postgres:5432/plateforme"
    )

    # ── Redis / Celery ───────────────────────────────────────────────────────
    redis_url: str = "redis://redis:6379/0"
    celery_always_eager: bool = False

    # ── Storage ──────────────────────────────────────────────────────────────
    storage_path: str = "/app/storage"

    # ── File limits & Lifecycle ──────────────────────────────────────────────
    max_file_size_mb: int = 10
    max_rows: int = 100_000
    session_ttl_days: int = 7

    # ── Rate limiting ────────────────────────────────────────────────────────
    rate_limit_prompts_per_hour: int = 30

    # ── LLM ──────────────────────────────────────────────────────────────────
    llm_provider: str = "local"          # local | openai | anthropic | google
    llm_model: str = "ollama/qwen2.5-coder:7b"
    ollama_base_url: str = "http://ollama:11434"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""            # Gemini API key — used as Ollama fallback
    llm_timeout_seconds: int = 300

    # ── Fuzzy matching ───────────────────────────────────────────────────────
    fuzzy_high_threshold: int = 80
    fuzzy_mid_threshold: int = 50

    # ── CORS ─────────────────────────────────────────────────────────────────
    cors_origins: List[str] = [
        "http://localhost",
        "http://localhost:80",
        "http://localhost:5173",
    ]

    # ── Keycloak ─────────────────────────────────────────────────────────────
    keycloak_server_url: str = "http://localhost:8080"
    keycloak_realm: str = "claria"
    keycloak_client_id: str = "claria-frontend"
    keycloak_admin_client_id: str = "claria-admin"
    keycloak_admin_client_secret: str = ""

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
