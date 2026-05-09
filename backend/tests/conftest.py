"""Shared pytest fixtures.

Forces every test session onto an in-memory aiosqlite database so the test
suite never touches a real Postgres instance.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import tempfile

import pytest

# Configure DB env BEFORE the app is imported anywhere.
_TMP_DB = os.path.join(tempfile.gettempdir(), "projectforge_test.db")
if os.path.exists(_TMP_DB):
    os.remove(_TMP_DB)

os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_TMP_DB}")
os.environ.setdefault("ENCRYPTION_KEY", "test-only-not-secure")
os.environ.setdefault("AUTO_CREATE_SCHEMA", "true")

_TMP_GRAPH = os.path.join(tempfile.gettempdir(), "projectforge_test_graph")
if os.path.isdir(_TMP_GRAPH):
    shutil.rmtree(_TMP_GRAPH, ignore_errors=True)
os.environ.setdefault("GRAPH_DATA_ROOT", _TMP_GRAPH)
os.environ.setdefault("GRAPH_BACKEND", "memory")

from app.core.config import get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_engine, reset_engine  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _initialise_database() -> None:
    """Create all tables once per test session."""

    get_settings.cache_clear()  # type: ignore[attr-defined]
    reset_engine()
    engine = get_engine()

    async def _create() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_create())

    yield

    async def _drop() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    asyncio.run(_drop())
