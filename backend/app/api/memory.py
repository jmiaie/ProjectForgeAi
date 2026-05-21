"""Project memory routes (Locus retrieval + OMPA journal)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.storage.locus_adapter import LocusAdapter
from app.storage.ompa_adapter import OmpaAdapter

router = APIRouter(
    prefix="/projects/{project_id}/memory",
    tags=["memory"],
)


class RetrieveRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=10, ge=1, le=100)
    filters: dict[str, Any] | None = None


class JournalEntryRequest(BaseModel):
    message: str = Field(min_length=1)
    classification: str | None = None
    tags: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)
    session_id: str | None = None


class SessionStartRequest(BaseModel):
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.post("/retrieve")
async def retrieve(
    project_id: str,
    payload: RetrieveRequest,
) -> dict[str, Any]:
    """Run a BM25 retrieval query against the project's Locus store."""

    locus = LocusAdapter(project_id)
    results = await locus.retrieve(
        payload.query, limit=payload.limit, filters=payload.filters
    )
    return {
        "project_id": project_id,
        "query": payload.query,
        "results": results,
        "result_count": len(results),
    }


@router.get("/stats")
async def stats(project_id: str) -> dict[str, Any]:
    locus = LocusAdapter(project_id)
    ompa = OmpaAdapter(project_id)
    return {
        "project_id": project_id,
        "locus": await locus.stats(),
        "ompa": await ompa.stats(),
    }


@router.get("/journal")
async def list_journal(
    project_id: str,
    session_id: str | None = Query(default=None),
    classification: str | None = Query(default=None),
    tag: list[str] | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
) -> dict[str, Any]:
    ompa = OmpaAdapter(project_id)
    entries = await ompa.entries(
        session_id=session_id,
        classification=classification,
        tags=tag,
        limit=limit,
    )
    return {
        "project_id": project_id,
        "entries": entries,
        "count": len(entries),
    }


@router.post("/journal")
async def append_journal_entry(
    project_id: str,
    payload: JournalEntryRequest,
) -> dict[str, Any]:
    ompa = OmpaAdapter(project_id)
    entry = await ompa.record_decision(
        payload.message,
        classification=payload.classification,
        tags=payload.tags,
        properties=payload.properties,
    )
    return {"project_id": project_id, "entry": entry}


@router.post("/sessions/start")
async def start_session(
    project_id: str,
    payload: SessionStartRequest,
) -> dict[str, Any]:
    ompa = OmpaAdapter(project_id)
    return await ompa.session_start(metadata=payload.metadata)


@router.post("/sessions/{session_id}/end")
async def end_session(
    project_id: str,
    session_id: str,
) -> dict[str, Any]:
    ompa = OmpaAdapter(project_id)
    ended = await ompa.session_end(session_id)
    return {"project_id": project_id, "session": ended}
