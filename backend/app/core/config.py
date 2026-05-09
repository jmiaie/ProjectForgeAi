"""Application configuration loaded from environment variables.

The settings here are intentionally permissive in development so the API can
boot without every secret configured. Production deployments should provide
all required values via environment variables or a mounted ``.env`` file.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:  # pragma: no cover - fallback for older pydantic versions
    from pydantic import BaseSettings  # type: ignore[no-redef]

    SettingsConfigDict = None  # type: ignore[assignment]


DeploymentMode = Literal["saas", "hybrid", "onprem"]


class Settings(BaseSettings):
    """Global application settings."""

    PROJECT_NAME: str = "ProjectForge AI"
    PROJECT_VERSION: str = "0.14.0"
    DEPLOYMENT_MODE: DeploymentMode = "saas"

    DEFAULT_COMPLIANCE: str = "standard"
    DEFAULT_LLM_MODEL: str = "groq/llama-3.1-70b-versatile"
    FLAGSHIP_LLM_MODEL: str = "anthropic/claude-3-5-sonnet-20241022"

    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "neo4j"

    POSTGRES_URI: str = "postgresql://postgres:postgres@localhost:5432/projectforge"
    REDIS_URI: str = "redis://localhost:6379/0"

    ENCRYPTION_KEY: str = "dev-only-not-secure-change-me"

    # Frontend / CORS
    ALLOWED_ORIGINS: list[str] = ["*"]

    # Storage roots
    LOCUS_ROOT: str = "./.locus"
    OMPA_VAULT_ROOT: str = "./vaults"

    if SettingsConfigDict is not None:  # pragma: no branch
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore",
        )
    else:  # pragma: no cover - pydantic v1 path

        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
            extra = "ignore"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance."""

    return Settings()
