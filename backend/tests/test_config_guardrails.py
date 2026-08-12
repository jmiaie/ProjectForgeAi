"""Tests for production configuration guardrails."""

from __future__ import annotations

import pytest

from app.core.config import Settings, validate_production_settings


def _prod_safe_settings(**overrides: object) -> Settings:
    """Return a Settings instance that passes production checks by default."""
    base = dict(
        APP_ENV="production",
        JWT_SECRET="a-very-long-and-random-jwt-secret-value-00000",
        ENCRYPTION_KEY="a-very-long-and-random-encryption-key-0000",
        ALLOWED_ORIGINS=["https://app.example.com"],
        AUTO_CREATE_SCHEMA=False,
    )
    base.update(overrides)
    return Settings.model_construct(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Development mode – guardrails must be silent
# ---------------------------------------------------------------------------

def test_dev_mode_passes_with_defaults() -> None:
    """Default Settings (APP_ENV=development) must always pass validation."""
    settings = Settings.model_construct(
        APP_ENV="development",
        JWT_SECRET="dev-only-jwt-secret-change-me",
        ENCRYPTION_KEY="dev-only-not-secure-change-me",
        ALLOWED_ORIGINS=["*"],
        AUTO_CREATE_SCHEMA=True,
    )
    # Should not raise
    validate_production_settings(settings)  # type: ignore[arg-type]


def test_test_mode_passes_with_defaults() -> None:
    settings = Settings.model_construct(
        APP_ENV="test",
        JWT_SECRET="dev-only-jwt-secret-change-me",
        ENCRYPTION_KEY="dev-only-not-secure-change-me",
        ALLOWED_ORIGINS=["*"],
        AUTO_CREATE_SCHEMA=True,
    )
    validate_production_settings(settings)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Production mode – clean config must pass
# ---------------------------------------------------------------------------

def test_production_clean_config_passes() -> None:
    validate_production_settings(_prod_safe_settings())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Production mode – wildcard CORS rejected
# ---------------------------------------------------------------------------

def test_production_rejects_wildcard_cors() -> None:
    settings = _prod_safe_settings(ALLOWED_ORIGINS=["*"])
    with pytest.raises(ValueError, match="wildcard CORS"):
        validate_production_settings(settings)  # type: ignore[arg-type]


def test_production_accepts_explicit_origins() -> None:
    settings = _prod_safe_settings(ALLOWED_ORIGINS=["https://app.example.com"])
    validate_production_settings(settings)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Production mode – dev JWT secret rejected
# ---------------------------------------------------------------------------

def test_production_rejects_dev_jwt_secret() -> None:
    settings = _prod_safe_settings(JWT_SECRET="dev-only-jwt-secret-change-me")
    with pytest.raises(ValueError, match="JWT_SECRET"):
        validate_production_settings(settings)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Production mode – dev encryption key rejected
# ---------------------------------------------------------------------------

def test_production_rejects_dev_encryption_key() -> None:
    settings = _prod_safe_settings(ENCRYPTION_KEY="dev-only-not-secure-change-me")
    with pytest.raises(ValueError, match="ENCRYPTION_KEY"):
        validate_production_settings(settings)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Production mode – AUTO_CREATE_SCHEMA rejected
# ---------------------------------------------------------------------------

def test_production_rejects_auto_create_schema() -> None:
    settings = _prod_safe_settings(AUTO_CREATE_SCHEMA=True)
    with pytest.raises(ValueError, match="AUTO_CREATE_SCHEMA"):
        validate_production_settings(settings)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Production mode – multiple errors reported together
# ---------------------------------------------------------------------------

def test_production_reports_all_errors() -> None:
    settings = _prod_safe_settings(
        ALLOWED_ORIGINS=["*"],
        JWT_SECRET="dev-only-jwt-secret-change-me",
        AUTO_CREATE_SCHEMA=True,
    )
    with pytest.raises(ValueError) as exc_info:
        validate_production_settings(settings)  # type: ignore[arg-type]
    msg = str(exc_info.value)
    assert "wildcard CORS" in msg
    assert "JWT_SECRET" in msg
    assert "AUTO_CREATE_SCHEMA" in msg
