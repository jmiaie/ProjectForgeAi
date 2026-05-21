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

    # Async SQLAlchemy URL. When unset, derived from POSTGRES_URI; for local
    # development / tests an aiosqlite URL such as
    # ``sqlite+aiosqlite:///./projectforge.db`` works out of the box.
    DATABASE_URL: str | None = None
    DATABASE_ECHO: bool = False

    # When true, ``Base.metadata.create_all`` is run at startup. Convenient for
    # local dev / sqlite tests; production should rely on Alembic migrations
    # instead.
    AUTO_CREATE_SCHEMA: bool = True

    ENCRYPTION_KEY: str = "dev-only-not-secure-change-me"

    # OAuth provider client credentials. Optional — when unset, the legacy
    # stubbed OAuth connector is used instead of a live token exchange.
    OAUTH_REDIRECT_BASE_URL: str = "http://localhost:8000"
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    MICROSOFT_CLIENT_ID: str | None = None
    MICROSOFT_CLIENT_SECRET: str | None = None
    GITHUB_CLIENT_ID: str | None = None
    GITHUB_CLIENT_SECRET: str | None = None
    SLACK_CLIENT_ID: str | None = None
    SLACK_CLIENT_SECRET: str | None = None
    OAUTH_STATE_TTL_SECONDS: int = 600

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


def get_oauth_client_credentials(
    settings: Settings, provider: str
) -> tuple[str | None, str | None]:
    """Return ``(client_id, client_secret)`` for ``provider`` from settings."""

    key = provider.upper()
    return (
        getattr(settings, f"{key}_CLIENT_ID", None),
        getattr(settings, f"{key}_CLIENT_SECRET", None),
    )


def resolve_database_url(settings: Settings) -> str:
    """Resolve the async SQLAlchemy URL.

    If ``DATABASE_URL`` is set we use it verbatim. Otherwise we upgrade the
    sync Postgres URI to its asyncpg variant.
    """

    if settings.DATABASE_URL:
        return settings.DATABASE_URL
    if settings.POSTGRES_URI.startswith("postgresql+asyncpg://"):
        return settings.POSTGRES_URI
    if settings.POSTGRES_URI.startswith("postgresql://"):
        return settings.POSTGRES_URI.replace("postgresql://", "postgresql+asyncpg://", 1)
    return settings.POSTGRES_URI


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance."""

    return Settings()
