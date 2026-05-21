"""Project orchestration HTTP routes."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.agents.orchestrator import OrchestratorAgent
from app.core.integrations_manager import IntegrationsManager
from app.ingestion.pipeline import IngestionPipeline

router = APIRouter(prefix="/projects", tags=["projects"])


def get_integrations_manager() -> IntegrationsManager:
    return IntegrationsManager()


def get_ingestion_pipeline() -> IngestionPipeline:
    return IngestionPipeline()


def get_orchestrator() -> OrchestratorAgent:
    return OrchestratorAgent()


@router.post("/")
async def create_project(
    files: list[UploadFile] = File(default_factory=list),
    compliance: str = Form("standard"),
    objective: str | None = Form(default=None),
    pipeline: IngestionPipeline = Depends(get_ingestion_pipeline),
    orchestrator: OrchestratorAgent = Depends(get_orchestrator),
    integrations_manager: IntegrationsManager = Depends(get_integrations_manager),
) -> dict[str, Any]:
    """Create a project, ingest uploaded files, and kick off orchestration."""

    project_id = f"proj_{uuid.uuid4().hex[:12]}"

    ingestion_summary = await pipeline.process_files(project_id, files)

    plan: dict[str, Any] | None = None
    if objective:
        state = await orchestrator.run(project_id=project_id, objective=objective)
        plan = {
            "objective": state.objective,
            "plan": state.plan,
            "context_chunks": len(state.context),
        }

    recommended = await integrations_manager.get_recommended_connectors(
        compliance=compliance
    )

    return {
        "project_id": project_id,
        "compliance": compliance,
        "status": "orchestrated",
        "ingestion": ingestion_summary,
        "plan": plan,
        "recommended_connectors": recommended,
        "message": "ProjectForge AI is live!",
    }
