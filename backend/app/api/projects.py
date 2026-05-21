"""Project orchestration HTTP routes."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import OrchestratorAgent
from app.core.integrations_manager import IntegrationsManager
from app.db.repositories import AuditLogRepository, ProjectRepository
from app.db.session import fastapi_get_session
from app.graph.builder import GraphBuilder
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
    name: str | None = Form(default=None),
    compliance: str = Form("standard"),
    objective: str | None = Form(default=None),
    pipeline: IngestionPipeline = Depends(get_ingestion_pipeline),
    orchestrator: OrchestratorAgent = Depends(get_orchestrator),
    integrations_manager: IntegrationsManager = Depends(get_integrations_manager),
    session: AsyncSession = Depends(fastapi_get_session),
) -> dict[str, Any]:
    """Create a project, persist it, ingest uploaded files, and orchestrate."""

    project_id = f"proj_{uuid.uuid4().hex[:12]}"
    projects = ProjectRepository(session)
    audit = AuditLogRepository(session)

    project = await projects.create(
        project_id=project_id,
        name=name or f"Project {project_id}",
        compliance=compliance,
        objective=objective,
        status="ingesting",
    )
    await audit.record(
        action="project.created",
        project_id=project_id,
        payload={"name": project.name, "compliance": compliance},
    )

    graph = GraphBuilder(project_id)
    await graph.add_project(
        name=project.name, compliance=compliance, objective=objective
    )

    ingestion_summary = await pipeline.process_files(project_id, files)
    graph_counts = await graph.add_documents_from_ingestion(ingestion_summary)
    await audit.record(
        action="project.ingested",
        project_id=project_id,
        payload={
            "total_files": ingestion_summary["total_files"],
            "total_chunks": ingestion_summary["total_chunks"],
            "graph_documents": graph_counts.get("documents", 0),
            "graph_chunks": graph_counts.get("chunks", 0),
        },
    )

    plan: dict[str, Any] | None = None
    if objective:
        await projects.update_status(project_id, "orchestrating")
        state = await orchestrator.run(project_id=project_id, objective=objective)
        graph_artefact_counts = await graph.add_orchestrator_outputs(
            state.get("outputs", {})
        )
        plan = {
            "objective": state.get("objective"),
            "compliance_category": state.get("compliance_category"),
            "plan": state.get("plan", []),
            "context_chunks": len(state.get("context", [])),
            "specialists_invoked": list(state.get("outputs", {}).keys()),
            "final_summary": state.get("final_summary"),
            "graph_artefacts": graph_artefact_counts,
        }
        await audit.record(
            action="project.orchestrated",
            project_id=project_id,
            payload={
                "specialists_invoked": plan["specialists_invoked"],
                "warnings": state.get("warnings", []),
                "graph_artefacts": graph_artefact_counts,
            },
        )

    await projects.update_status(project_id, "orchestrated")
    await session.commit()

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


@router.get("/")
async def list_projects(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(fastapi_get_session),
) -> dict[str, Any]:
    projects = ProjectRepository(session)
    rows = await projects.list(limit=limit, offset=offset)
    return {
        "items": [project.to_dict() for project in rows],
        "limit": limit,
        "offset": offset,
    }


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    session: AsyncSession = Depends(fastapi_get_session),
) -> dict[str, Any]:
    projects = ProjectRepository(session)
    project = await projects.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project.to_dict()
