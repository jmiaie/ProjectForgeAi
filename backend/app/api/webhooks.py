"""Webhook ingestion routes (Phase 3).

Accepts signed or unsigned JSON payloads from external systems and records
them in OMPA + Locus so agents can retrieve webhook content alongside
uploaded documents.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.db.repositories import AuditLogRepository, ProjectRepository
from app.db.session import fastapi_get_session
from app.storage.locus_adapter import LocusAdapter
from app.storage.ompa_adapter import OmpaAdapter
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/projects/{project_id}/webhooks", tags=["webhooks"])


class WebhookPayload(BaseModel):
    event: str = Field(min_length=1, max_length=128)
    source: str | None = Field(default=None, max_length=128)
    data: dict[str, Any] = Field(default_factory=dict)
    text: str | None = None


@router.post("/")
async def receive_webhook(
    project_id: str,
    payload: WebhookPayload,
    session: AsyncSession = Depends(fastapi_get_session),
) -> dict[str, Any]:
    """Ingest a webhook event into project memory."""

    projects = ProjectRepository(session)
    project = await projects.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    text_body = payload.text or _format_webhook_text(payload)
    locus = LocusAdapter(project_id)
    await locus.index_files(
        [
            {
                "source": f"webhook:{payload.event}",
                "text": text_body,
                "metadata": {
                    "parser": "webhook",
                    "event": payload.event,
                    "source": payload.source,
                },
            }
        ]
    )

    ompa = OmpaAdapter(project_id)
    entry = await ompa.record_decision(
        f"Webhook {payload.event} from {payload.source or 'unknown'}",
        classification="webhook",
        tags=[payload.event],
        properties={"data_keys": list(payload.data.keys())},
    )

    audit = AuditLogRepository(session)
    await audit.record(
        action="webhook.received",
        project_id=project_id,
        payload={"event": payload.event, "source": payload.source},
    )
    await session.commit()

    return {
        "project_id": project_id,
        "status": "accepted",
        "event": payload.event,
        "journal_entry_id": entry.get("id") if isinstance(entry, dict) else None,
    }


def _format_webhook_text(payload: WebhookPayload) -> str:
    lines = [f"Webhook event: {payload.event}"]
    if payload.source:
        lines.append(f"Source: {payload.source}")
    if payload.data:
        for key, value in payload.data.items():
            lines.append(f"{key}: {value}")
    return "\n".join(lines)
