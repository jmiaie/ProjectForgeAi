"""Async SQLAlchemy engine / session management.

The engine is lazy-built so tests can override ``DATABASE_URL`` (e.g. to
point at ``sqlite+aiosqlite:///``) before the first session is requested.
Call :func:`reset_engine` from teardown code if you need to swap URLs.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings, resolve_database_url

_engine: Optional[AsyncEngine] = None
_sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None


def create_engine_and_sessionmaker(
    url: str | None = None, echo: bool | None = None
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Build a fresh engine + sessionmaker pair without caching."""

    settings = get_settings()
    resolved = url or resolve_database_url(settings)
    engine = create_async_engine(
        resolved,
        echo=echo if echo is not None else settings.DATABASE_ECHO,
        future=True,
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return engine, factory


def get_engine() -> AsyncEngine:
    global _engine, _sessionmaker
    if _engine is None:
        _engine, _sessionmaker = create_engine_and_sessionmaker()
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        get_engine()
    assert _sessionmaker is not None
    return _sessionmaker


def reset_engine() -> None:
    """Drop the cached engine/sessionmaker (used by tests)."""

    global _engine, _sessionmaker
    _engine = None
    _sessionmaker = None


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Async context manager yielding a SQLAlchemy session.

    Suitable both as a FastAPI dependency (``async for session in get_session()``)
    and as a regular ``async with`` context manager.
    """

    factory = get_sessionmaker()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def fastapi_get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency variant of :func:`get_session`."""

    async with get_session() as session:
        yield session
