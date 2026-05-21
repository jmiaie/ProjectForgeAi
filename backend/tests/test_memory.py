"""Tests for the BM25 LocusEngine, the OMPA journal engine, and the
project memory API."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.storage.locus_engine import LocusEngine
from app.storage.ompa_engine import CLASSIFICATIONS, OmpaEngine


# ---------------------------------------------------------------------------
# LocusEngine
# ---------------------------------------------------------------------------
def _make_locus(tmp_path: Path) -> LocusEngine:
    return LocusEngine(str(tmp_path / "locus"))


def test_locus_engine_bm25_ranks_relevant_chunks_higher(tmp_path: Path) -> None:
    engine = _make_locus(tmp_path)
    engine.index(
        [
            {
                "id": "c1",
                "text": "Quarterly compliance review for the HIPAA controls.",
                "metadata": {"section": "compliance", "page": 1},
            },
            {
                "id": "c2",
                "text": "Vendor delay risk mitigation for the build phase.",
                "metadata": {"section": "risk", "page": 2},
            },
            {
                "id": "c3",
                "text": "HIPAA HIPAA HIPAA — required encryption controls and BAA list.",
                "metadata": {"section": "compliance", "page": 3},
            },
        ]
    )

    results = engine.retrieve("HIPAA encryption controls", limit=3)
    assert results, "expected at least one result"
    ids = [r["id"] for r in results]
    assert ids[0] == "c3"
    assert "c2" not in ids[:1]
    assert all(r["score"] > 0 for r in results)


def test_locus_engine_retrieve_returns_empty_on_unknown_query(tmp_path: Path) -> None:
    engine = _make_locus(tmp_path)
    engine.index([{"id": "c1", "text": "compliance review", "metadata": {}}])
    assert engine.retrieve("xyzzy-no-such-token") == []


def test_locus_engine_supports_metadata_filters(tmp_path: Path) -> None:
    engine = _make_locus(tmp_path)
    engine.index(
        [
            {"id": "c1", "text": "schedule kickoff milestone", "metadata": {"page": 1}},
            {"id": "c2", "text": "schedule milestone review", "metadata": {"page": 2}},
        ]
    )
    results = engine.retrieve("milestone schedule", filters={"page": 2})
    assert [r["id"] for r in results] == ["c2"]


def test_locus_engine_is_idempotent_and_persistent(tmp_path: Path) -> None:
    engine = _make_locus(tmp_path)
    chunks = [
        {"id": "c1", "text": "first chunk", "metadata": {"section": "page"}},
        {"id": "c2", "text": "second chunk", "metadata": {"section": "page"}},
    ]
    first = engine.index(chunks)
    assert first["added"] == 2 and first["skipped"] == 0

    second = engine.index(chunks)
    assert second["added"] == 0 and second["skipped"] == 2

    # Reload from disk -> chunks survive.
    reopened = _make_locus(tmp_path)
    assert reopened.stats()["total_chunks"] == 2


def test_locus_engine_clear(tmp_path: Path) -> None:
    engine = _make_locus(tmp_path)
    engine.index([{"id": "c1", "text": "x y z", "metadata": {}}])
    engine.clear()
    assert engine.stats()["total_chunks"] == 0
    assert engine.retrieve("x") == []


# ---------------------------------------------------------------------------
# OmpaEngine
# ---------------------------------------------------------------------------
def _make_ompa(tmp_path: Path) -> OmpaEngine:
    return OmpaEngine(str(tmp_path / "ompa"))


def test_ompa_engine_classifies_messages_heuristically(tmp_path: Path) -> None:
    engine = _make_ompa(tmp_path)
    decision = engine.classify("We decided to ship next Tuesday")
    assert decision["classification"] == "decision"

    error = engine.classify("Build failed with an exception on staging")
    assert error["classification"] == "error"

    note = engine.classify("Background colour is blue")
    assert note["classification"] == "note"


def test_ompa_engine_respects_explicit_classification(tmp_path: Path) -> None:
    engine = _make_ompa(tmp_path)
    entry = engine.classify(
        "any message body", classification="milestone", tags=["alpha"]
    )
    assert entry["classification"] == "milestone"
    assert entry["tags"] == ["alpha"]


def test_ompa_engine_invalid_classification_normalises_to_note(tmp_path: Path) -> None:
    engine = _make_ompa(tmp_path)
    entry = engine.classify("foo", classification="not-a-real-bucket")
    assert entry["classification"] == "note"


def test_ompa_engine_session_lifecycle_and_filtering(tmp_path: Path) -> None:
    engine = _make_ompa(tmp_path)
    session = engine.session_start({"actor": "agent"})
    session_id = session["session_id"]
    assert engine.current_session_id() == session_id

    engine.classify("Kickoff scheduled for Monday", classification="milestone")
    engine.classify("Reviewing scope", classification="observation", tags=["scope"])
    engine.classify(
        "Reviewing scope and budget",
        classification="observation",
        tags=["scope", "budget"],
    )

    ended = engine.session_end()
    assert ended and ended["session_id"] == session_id
    assert engine.current_session_id() is None

    # Filter by session.
    in_session = engine.entries(session_id=session_id)
    assert len(in_session) == 3

    # Filter by classification.
    observations = engine.entries(classification="observation")
    assert len(observations) == 2

    # Filter by tags (superset semantics).
    only_budget = engine.entries(tags=["budget"])
    assert len(only_budget) == 1
    assert "budget" in only_budget[0]["tags"]

    stats = engine.stats()
    assert stats["total_entries"] == 3
    assert stats["by_classification"]["milestone"] == 1
    assert stats["by_classification"]["observation"] == 2
    assert stats["total_sessions"] == 1
    assert stats["open_sessions"] == 0


def test_ompa_engine_persists_journal_and_sessions(tmp_path: Path) -> None:
    engine = _make_ompa(tmp_path)
    engine.session_start()
    engine.classify("decided to proceed", classification="decision")
    engine.session_end()

    reopened = _make_ompa(tmp_path)
    entries = reopened.entries()
    assert len(entries) == 1
    assert entries[0]["classification"] == "decision"
    assert reopened.stats()["total_sessions"] == 1


def test_ompa_engine_classifications_enum_consistent() -> None:
    assert "decision" in CLASSIFICATIONS
    assert "note" in CLASSIFICATIONS


# ---------------------------------------------------------------------------
# Memory API
# ---------------------------------------------------------------------------
SAMPLE_EMAIL = b"""From: alice@example.com
To: bob@example.com
Subject: HIPAA encryption review
Date: Wed, 01 Jan 2025 09:00:00 +0000
Content-Type: text/plain

We must encrypt PHI at rest and in transit, per HIPAA requirements.
"""


def _create_project_with_ingestion() -> str:
    client = TestClient(app)
    files = [("files", ("hipaa.eml", io.BytesIO(SAMPLE_EMAIL), "message/rfc822"))]
    res = client.post(
        "/api/v1/projects/",
        files=files,
        data={"name": "Memory API", "compliance": "standard"},
    )
    assert res.status_code == 200, res.text
    return res.json()["project_id"]


def test_memory_retrieve_endpoint_returns_bm25_results() -> None:
    project_id = _create_project_with_ingestion()
    client = TestClient(app)
    res = client.post(
        f"/api/v1/projects/{project_id}/memory/retrieve",
        json={"query": "encrypt PHI HIPAA", "limit": 5},
    )
    assert res.status_code == 200, res.text
    payload = res.json()
    assert payload["project_id"] == project_id
    assert payload["result_count"] >= 1
    top = payload["results"][0]
    assert top["score"] > 0
    assert "HIPAA" in top["text"] or "PHI" in top["text"]


def test_memory_stats_endpoint_includes_locus_and_ompa() -> None:
    project_id = _create_project_with_ingestion()
    client = TestClient(app)
    res = client.get(f"/api/v1/projects/{project_id}/memory/stats")
    assert res.status_code == 200
    payload = res.json()
    assert payload["locus"]["total_chunks"] >= 1
    assert payload["locus"]["backend"] == "local"
    assert payload["ompa"]["backend"] == "local"
    assert payload["ompa"]["total_entries"] >= 1


def test_memory_journal_append_and_list() -> None:
    project_id = _create_project_with_ingestion()
    client = TestClient(app)

    res = client.post(
        f"/api/v1/projects/{project_id}/memory/sessions/start",
        json={"metadata": {"actor": "test"}},
    )
    assert res.status_code == 200
    session_id = res.json()["session_id"]

    res = client.post(
        f"/api/v1/projects/{project_id}/memory/journal",
        json={
            "message": "We decided to lock the schedule",
            "tags": ["schedule"],
        },
    )
    assert res.status_code == 200
    assert res.json()["entry"]["classification"] == "decision"

    res = client.get(
        f"/api/v1/projects/{project_id}/memory/journal",
        params={"classification": "decision"},
    )
    assert res.status_code == 200
    entries = res.json()["entries"]
    assert any("lock the schedule" in e["message"] for e in entries)

    res = client.post(
        f"/api/v1/projects/{project_id}/memory/sessions/{session_id}/end"
    )
    assert res.status_code == 200
    assert res.json()["session"]["session_id"] == session_id
