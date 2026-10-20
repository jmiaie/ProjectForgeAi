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


# ---------------------------------------------------------------------------
# Startup wiring – create_app() must run the guardrails
# ---------------------------------------------------------------------------

@pytest.fixture
def _fresh_settings(monkeypatch: pytest.MonkeyPatch):
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield monkeypatch
    get_settings.cache_clear()


def test_create_app_refuses_to_boot_with_unsafe_production_config(
    _fresh_settings: pytest.MonkeyPatch,
) -> None:
    from app.main import create_app

    mp = _fresh_settings
    mp.setenv("APP_ENV", "production")
    mp.setenv("ALLOWED_ORIGINS", '["*"]')
    mp.setenv("JWT_SECRET", "dev-only-jwt-secret-change-me")
    mp.setenv("ENCRYPTION_KEY", "dev-only-not-secure-change-me")
    mp.setenv("AUTO_CREATE_SCHEMA", "false")
    with pytest.raises(ValueError) as exc_info:
        create_app()
    msg = str(exc_info.value)
    assert "wildcard CORS" in msg
    assert "JWT_SECRET" in msg
    assert "ENCRYPTION_KEY" in msg


def test_create_app_boots_with_safe_production_config(
    _fresh_settings: pytest.MonkeyPatch,
) -> None:
    from app.main import create_app

    mp = _fresh_settings
    mp.setenv("APP_ENV", "production")
    mp.setenv("ALLOWED_ORIGINS", '["https://app.example.com"]')
    mp.setenv("JWT_SECRET", "a-very-long-and-random-jwt-secret-value-00000")
    mp.setenv("ENCRYPTION_KEY", "a-very-long-and-random-encryption-key-0000")
    mp.setenv("AUTO_CREATE_SCHEMA", "false")
    assert create_app() is not None


def test_create_app_does_not_enforce_outside_production(
    _fresh_settings: pytest.MonkeyPatch,
) -> None:
    from app.main import create_app

    mp = _fresh_settings
    mp.setenv("APP_ENV", "development")
    mp.setenv("ALLOWED_ORIGINS", '["*"]')
    assert create_app() is not None


# ---------------------------------------------------------------------------
# LLM model defaults are current and overridable through env
# ---------------------------------------------------------------------------

def test_flagship_model_default_is_current() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.FLAGSHIP_LLM_MODEL == "anthropic/claude-sonnet-5-5"
    assert "claude-3-5-sonnet" not in settings.FLAGSHIP_LLM_MODEL


def test_llm_models_are_configurable_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEFAULT_LLM_MODEL", "groq/some-current-model")
    monkeypatch.setenv("FLAGSHIP_LLM_MODEL", "anthropic/some-other-model")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.DEFAULT_LLM_MODEL == "groq/some-current-model"
    assert settings.FLAGSHIP_LLM_MODEL == "anthropic/some-other-model"
