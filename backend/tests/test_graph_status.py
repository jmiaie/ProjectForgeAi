"""Tests for graph backend status helper."""

from __future__ import annotations

import pytest

from app.graph.status import graph_backend_status


@pytest.mark.asyncio
async def test_graph_status_memory_backend() -> None:
    status = await graph_backend_status()
    assert status["configured"] in {"memory", "neo4j"}
    assert "neo4j" in status
