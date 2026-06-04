"""Tests for RTK context optimization."""

from __future__ import annotations

from app.storage.context_optimizer import optimize_context_chunks


def test_optimize_context_trims_by_char_budget() -> None:
    chunks = [
        {"text": "a" * 5000, "metadata": {}},
        {"text": "b" * 5000, "metadata": {}},
        {"text": "c" * 5000, "metadata": {}},
    ]
    optimized, meta = optimize_context_chunks(chunks, max_chunks=8, max_chars=7000)
    assert len(optimized) <= 2
    assert meta["original_chunks"] == 3
    assert meta["optimized_chars"] <= 7000


def test_optimize_context_respects_chunk_limit() -> None:
    chunks = [{"text": f"chunk {i}", "metadata": {}} for i in range(20)]
    optimized, meta = optimize_context_chunks(chunks, max_chunks=5, max_chars=50_000)
    assert len(optimized) == 5
    assert meta["optimized_chunks"] == 5
