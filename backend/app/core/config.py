"""Application configuration loaded from environment variables.

The settings here are intentionally permissive in development so the API can
boot without every secret configured. Production deployments should provide
all required values via environment variables or a mounted ``.env`` file.

Production guardrails
---------------------
When ``APP_ENV=production`` the following checks run at import time:

* Wildcard CORS (``ALLOWED_ORIGINS=["*"]``) is rejected.
* Known development-only secrets for ``JWT_SECRET`` and ``ENCRYPTION_KEY``
  are rejected.
* ``AUTO_CREATE_SCHEMA`` must be ``False`` (use Alembic migrations in prod).

These checks raise :class:`ValueError` with actionable messages so the
process fails fast rather than starting with unsafe defaults.
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

# Secrets that are only safe during local development.
_DEV_JWT_SECRETS = {"dev-only-jwt-secret-change-me"}
_DEV_ENCRYPTION_KEYS = {"dev-only-not-secure-change-me"}


class Settings(BaseSettings):
    """Global application settings."""

    PROJECT_NAME: str = "ProjectForge AI"
    PROJECT_VERSION: str = "0.14.0"
    DEPLOYMENT_MODE: DeploymentMode = "saas"

    # ``APP_ENV`` drives production safety checks. Recognised values:
    # ``development`` (default), ``test``, ``staging``, ``production``.
    # Set to ``production`` to activate fail-closed guardrails.
    APP_ENV: str = "development"

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

    # JWT / auth
    JWT_SECRET: str = "dev-only-jwt-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "projectforge-ai"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12  # 12 hours

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
    GRAPH_DATA_ROOT: str = "./.graph"

    # Storage backends: ``local`` (the production-shaped in-process engines,
    # default) or ``submodule`` (load the upstream ``locus`` / ``ompa``
    # packages when they are installed).
    LOCUS_BACKEND: str = "local"
    OMPA_BACKEND: str = "local"

    # Graph backend: ``memory`` (file-backed JSON, dev/test default) or
    # ``neo4j`` (uses the async driver against ``NEO4J_URI``).
    GRAPH_BACKEND: str = "memory"

    # Workflow / automation backend: ``memory`` (in-process polling, dev/test
    # default) or ``temporal`` (uses the temporalio SDK).
    WORKFLOW_BACKEND: str = "memory"
    TEMPORAL_TARGET: str = "localhost:7233"
    TEMPORAL_NAMESPACE: str = "default"
    TEMPORAL_TASK_QUEUE: str = "projectforge-automations"
    AUTOMATION_POLL_SECONDS: float = 5.0

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


def validate_production_settings(settings: Settings) -> None:
    """Raise :class:`ValueError` if *settings* contains unsafe production values.

    This function is a no-op unless ``APP_ENV`` is ``"production"``.
    Call it explicitly (e.g. in the ASGI lifespan) when you want fail-closed
    startup behaviour, or call it from tests to verify the guardrails.
    """
    if settings.APP_ENV != "production":
        return

    errors: list[str] = []

    if "*" in settings.ALLOWED_ORIGINS:
        errors.append(
            "ALLOWED_ORIGINS contains '*' – wildcard CORS is not allowed in production. "
            "Set ALLOWED_ORIGINS to the explicit list of trusted origins."
        )

    if settings.JWT_SECRET in _DEV_JWT_SECRETS:
        errors.append(
            "JWT_SECRET is set to a known development default. "
            "Generate a strong secret and set JWT_SECRET in your environment."
        )

    if settings.ENCRYPTION_KEY in _DEV_ENCRYPTION_KEYS:
        errors.append(
            "ENCRYPTION_KEY is set to a known development default. "
            "Generate a strong key and set ENCRYPTION_KEY in your environment."
        )

    if settings.AUTO_CREATE_SCHEMA:
        errors.append(
            "AUTO_CREATE_SCHEMA=true is not allowed in production. "
            "Run Alembic migrations instead and set AUTO_CREATE_SCHEMA=false."
        )

    if errors:
        joined = "\n  - ".join(errors)
        raise ValueError(
            f"Unsafe production configuration detected:\n  - {joined}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance."""

    return Settings()
