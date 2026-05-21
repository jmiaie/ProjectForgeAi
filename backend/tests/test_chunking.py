"""Unit tests for the text chunking helper."""

from __future__ import annotations

import pytest

from app.ingestion.chunking import ChunkingOptions, chunk_text


def test_short_text_returns_single_chunk() -> None:
    assert chunk_text("Hello world") == ["Hello world"]


def test_empty_text_returns_empty_list() -> None:
    assert chunk_text("") == []
    assert chunk_text("   \n  ") == []


def test_long_text_splits_with_overlap() -> None:
    paragraph = (
        "Para one sentence one. Para one sentence two.\n\n"
        "Para two sentence one. Para two sentence two.\n\n"
        "Para three sentence one."
    )
    text = (paragraph + "\n\n") * 6
    options = ChunkingOptions(chunk_size=200, overlap=40, min_chunk_size=20)
    chunks = chunk_text(text, options)
    assert len(chunks) > 1
    assert all(len(chunk) <= 200 for chunk in chunks)
    overlap_pairs = [
        bool(set(chunks[i][-30:]).intersection(chunks[i + 1][:30]))
        for i in range(len(chunks) - 1)
    ]
    assert any(overlap_pairs)


def test_long_text_with_no_breaks_is_still_chunked() -> None:
    text = "x" * 1000
    options = ChunkingOptions(chunk_size=200, overlap=20, min_chunk_size=10)
    chunks = chunk_text(text, options)
    assert len(chunks) >= 4
    assert all(len(chunk) <= 200 for chunk in chunks)


def test_invalid_options_raise() -> None:
    with pytest.raises(ValueError):
        ChunkingOptions(chunk_size=0)
    with pytest.raises(ValueError):
        ChunkingOptions(chunk_size=100, overlap=200)
    with pytest.raises(ValueError):
        ChunkingOptions(chunk_size=100, overlap=-1)


def test_tail_smaller_than_min_chunk_is_merged() -> None:
    text = ("Sentence. " * 30).strip()
    options = ChunkingOptions(chunk_size=120, overlap=10, min_chunk_size=80)
    chunks = chunk_text(text, options)
    assert chunks
    assert len(chunks[-1]) >= options.min_chunk_size or len(chunks) == 1
