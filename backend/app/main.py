from typing import Any, Literal

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.agents.orchestrator import Orchestrator
from app.compliance.enforcer import (
    get_audit_events,
    get_compliance_profile,
    record_audit_event,
    set_compliance_profile,
)
from app.core.config import Settings
from app.core.integrations_manager import IntegrationsManager
from app.core.llm_router import LLMRouter
from app.ingestion.pipeline import IngestionPipeline
from app.integrations.intake_form import router as intake_router
from app.storage.neo4j_adapter import ProjectGraphStore
from app.workflows.scheduler import WorkflowScheduler

settings = Settings()
app = FastAPI(title=settings.PROJECT_NAME)
orchestrator = Orchestrator()
project_graph_store = ProjectGraphStore(settings=settings)
workflow_scheduler = WorkflowScheduler()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(intake_router, prefix="/api/v1")


def get_llm_router() -> LLMRouter:
    return LLMRouter()


def get_integrations_manager() -> IntegrationsManager:
    return IntegrationsManager()


def get_orchestrator() -> Orchestrator:
    return orchestrator


def get_project_graph_store() -> ProjectGraphStore:
    return project_graph_store


def get_workflow_scheduler() -> WorkflowScheduler:
    return workflow_scheduler


class ComplianceUpdateRequest(BaseModel):
    category: str


class WorkflowJobCreateRequest(BaseModel):
    name: str
    job_type: str = "weekly_status_report"
    schedule_type: Literal["once", "hourly", "daily", "weekly"] = "weekly"
    run_at: str | None = None
    interval_minutes: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class WorkflowJobRunRequest(BaseModel):
    payload_override: dict[str, Any] | None = None


class WeeklyReportScheduleRequest(BaseModel):
    name: str = "Weekly Status Automation"
    schedule_type: Literal["once", "hourly", "daily", "weekly"] = "weekly"
    run_at: str | None = None
    interval_minutes: int | None = None


@app.post("/api/v1/projects/")
async def create_project(
    files: list[UploadFile] = File(default=[]),
    compliance: str = "standard",
    integrations_manager: IntegrationsManager = Depends(get_integrations_manager),
    llm_router: LLMRouter = Depends(get_llm_router),
    workflow_orchestrator: Orchestrator = Depends(get_orchestrator),
    graph_store: ProjectGraphStore = Depends(get_project_graph_store),
) -> dict:
    pipeline = IngestionPipeline()
    project_id = "proj_123"
    try:
        set_compliance_profile(project_id=project_id, category=compliance)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # 1) Intake wizard data can be used to auto-connect integrations.
    # 2) Files are ingested into Locus + OMPA adapters.
    ingestion_result = await pipeline.process_files(project_id=project_id, files=files)
    orchestration = await workflow_orchestrator.run(
        project_id=project_id,
        compliance=compliance,
        ingestion=ingestion_result,
    )
    graph_summary = await graph_store.upsert_project_graph(
        project_id=project_id,
        compliance=compliance,
        ingestion=ingestion_result,
        orchestration=orchestration,
    )

    # Keep these dependencies resolved now so service wiring is validated.
    _ = integrations_manager
    _ = llm_router
    record_audit_event(
        project_id=project_id,
        event_type="project_created",
        payload={"compliance": compliance, "files_uploaded": len(files)},
    )

    return {
        "project_id": project_id,
        "status": "orchestrated",
        "compliance": compliance,
        "ingestion": ingestion_result,
        "orchestration": orchestration,
        "graph": graph_summary,
        "message": "ProjectForge AI is live!",
    }


@app.post("/api/v1/projects/{project_id}/orchestrate")
async def orchestrate_project(
    project_id: str,
    compliance: str = "standard",
    workflow_orchestrator: Orchestrator = Depends(get_orchestrator),
    graph_store: ProjectGraphStore = Depends(get_project_graph_store),
) -> dict:
    try:
        set_compliance_profile(project_id=project_id, category=compliance)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    orchestration = await workflow_orchestrator.run(project_id=project_id, compliance=compliance)
    graph_summary = await graph_store.upsert_project_graph(
        project_id=project_id,
        compliance=compliance,
        ingestion=orchestration.get("ingestion"),
        orchestration=orchestration,
    )
    return {"orchestration": orchestration, "graph": graph_summary}


@app.post("/api/v1/projects/{project_id}/compliance")
async def update_project_compliance(project_id: str, request: ComplianceUpdateRequest) -> dict:
    try:
        profile = set_compliance_profile(project_id=project_id, category=request.category)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "status": "updated",
        "project_id": profile.project_id,
        "category": profile.category,
        "last_updated": profile.last_updated,
    }


@app.get("/api/v1/projects/{project_id}/compliance")
async def get_project_compliance(project_id: str) -> dict:
    profile = get_compliance_profile(project_id=project_id)
    return {
        "status": "ok",
        "project_id": profile.project_id,
        "category": profile.category,
        "last_updated": profile.last_updated,
    }


@app.get("/api/v1/projects/{project_id}/audit-events")
async def get_project_audit_events(project_id: str, limit: int = 100) -> dict:
    return {"status": "ok", "project_id": project_id, "events": get_audit_events(project_id, limit=limit)}


@app.get("/api/v1/projects/{project_id}/dashboard")
async def get_project_dashboard(
    project_id: str,
    workflow_orchestrator: Orchestrator = Depends(get_orchestrator),
    graph_store: ProjectGraphStore = Depends(get_project_graph_store),
    integrations_manager: IntegrationsManager = Depends(get_integrations_manager),
    scheduler: WorkflowScheduler = Depends(get_workflow_scheduler),
) -> dict:
    workflow = await workflow_orchestrator.status(project_id=project_id)
    graph_summary = await graph_store.get_summary(project_id=project_id)
    compliance = get_compliance_profile(project_id=project_id)
    connections = await integrations_manager.list_connections(project_id=project_id)
    events = get_audit_events(project_id=project_id, limit=20)
    jobs = scheduler.list_jobs(project_id=project_id)
    reports = scheduler.list_reports(project_id=project_id)

    # Lightweight KPI shaping for frontend dashboard cards.
    metrics = {
        "connections": len(connections.get("connections", [])),
        "graph_nodes": graph_summary.get("nodes", 0),
        "graph_edges": graph_summary.get("edges", 0),
        "workflow_steps_completed": len(workflow.get("states_visited", [])),
        "audit_events": len(events),
        "scheduled_jobs": len(jobs),
        "reports_generated": len(reports),
    }
    return {
        "status": "ok",
        "project_id": project_id,
        "metrics": metrics,
        "compliance": {
            "category": compliance.category,
            "last_updated": compliance.last_updated,
        },
        "workflow": workflow,
        "graph_summary": graph_summary,
        "connections": connections.get("connections", []),
        "workflow_jobs": jobs,
        "reports": reports[-10:],
        "recent_events": events,
    }


@app.post("/api/v1/projects/{project_id}/workflows/jobs")
async def create_workflow_job(
    project_id: str,
    request: WorkflowJobCreateRequest,
    scheduler: WorkflowScheduler = Depends(get_workflow_scheduler),
) -> dict:
    try:
        job = scheduler.create_job(
            project_id=project_id,
            name=request.name,
            job_type=request.job_type,
            schedule_type=request.schedule_type,
            run_at=request.run_at,
            interval_minutes=request.interval_minutes,
            payload=request.payload,
            enabled=request.enabled,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record_audit_event(
        project_id=project_id,
        event_type="workflow_job_created",
        payload={"job_id": job["job_id"], "job_type": job["job_type"], "schedule_type": job["schedule_type"]},
    )
    return {"status": "scheduled", "job": job}


@app.get("/api/v1/projects/{project_id}/workflows/jobs")
async def list_workflow_jobs(
    project_id: str,
    scheduler: WorkflowScheduler = Depends(get_workflow_scheduler),
) -> dict:
    return {"status": "ok", "project_id": project_id, "jobs": scheduler.list_jobs(project_id=project_id)}


@app.post("/api/v1/projects/{project_id}/workflows/jobs/{job_id}/run")
async def run_workflow_job(
    project_id: str,
    job_id: str,
    request: WorkflowJobRunRequest,
    scheduler: WorkflowScheduler = Depends(get_workflow_scheduler),
) -> dict:
    try:
        run = scheduler.run_job(
            project_id=project_id,
            job_id=job_id,
            trigger="manual",
            payload_override=request.payload_override,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record_audit_event(
        project_id=project_id,
        event_type="workflow_job_run",
        payload={"job_id": job_id, "trigger": "manual", "run_id": run["run_id"]},
    )
    return {"status": "executed", "run": run}


@app.post("/api/v1/projects/{project_id}/workflows/tick")
async def trigger_workflow_tick(
    project_id: str,
    scheduler: WorkflowScheduler = Depends(get_workflow_scheduler),
) -> dict:
    runs = scheduler.run_due_jobs(project_id=project_id)
    if runs:
        record_audit_event(
            project_id=project_id,
            event_type="workflow_tick_executed",
            payload={"runs": len(runs), "run_ids": [run["run_id"] for run in runs]},
        )
    return {"status": "ok", "project_id": project_id, "executed": len(runs), "runs": runs}


@app.get("/api/v1/projects/{project_id}/workflows/runs")
async def list_workflow_runs(
    project_id: str,
    scheduler: WorkflowScheduler = Depends(get_workflow_scheduler),
) -> dict:
    return {"status": "ok", "project_id": project_id, "runs": scheduler.list_runs(project_id=project_id)}


@app.post("/api/v1/projects/{project_id}/reports/weekly-status")
async def generate_weekly_status_report(
    project_id: str,
    scheduler: WorkflowScheduler = Depends(get_workflow_scheduler),
) -> dict:
    report = scheduler.generate_weekly_status_report(project_id=project_id, source="manual")
    record_audit_event(
        project_id=project_id,
        event_type="report_generated",
        payload={"report_id": report["report_id"], "type": report["type"], "source": "manual"},
    )
    return {"status": "generated", "report": report}


@app.post("/api/v1/projects/{project_id}/reports/weekly-status/schedule")
async def schedule_weekly_status_report(
    project_id: str,
    request: WeeklyReportScheduleRequest,
    scheduler: WorkflowScheduler = Depends(get_workflow_scheduler),
) -> dict:
    try:
        job = scheduler.create_job(
            project_id=project_id,
            name=request.name,
            job_type="weekly_status_report",
            schedule_type=request.schedule_type,
            run_at=request.run_at,
            interval_minutes=request.interval_minutes,
            payload={"template": "default"},
            enabled=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record_audit_event(
        project_id=project_id,
        event_type="workflow_job_created",
        payload={"job_id": job["job_id"], "job_type": "weekly_status_report", "source": "report_schedule"},
    )
    return {"status": "scheduled", "job": job}


@app.get("/api/v1/projects/{project_id}/reports")
async def list_reports(
    project_id: str,
    scheduler: WorkflowScheduler = Depends(get_workflow_scheduler),
) -> dict:
    return {"status": "ok", "project_id": project_id, "reports": scheduler.list_reports(project_id=project_id)}


@app.get("/api/v1/projects/{project_id}/workflow")
async def get_project_workflow(
    project_id: str, workflow_orchestrator: Orchestrator = Depends(get_orchestrator)
) -> dict:
    return await workflow_orchestrator.status(project_id=project_id)


@app.get("/api/v1/traces/{trace_id}")
async def get_trace(trace_id: str, workflow_orchestrator: Orchestrator = Depends(get_orchestrator)) -> dict:
    return await workflow_orchestrator.trace(trace_id=trace_id)


@app.get("/api/v1/projects/{project_id}/graph/summary")
async def get_project_graph_summary(
    project_id: str, graph_store: ProjectGraphStore = Depends(get_project_graph_store)
) -> dict:
    return await graph_store.get_summary(project_id=project_id)


@app.get("/api/v1/projects/{project_id}/graph/nodes")
async def get_project_graph_nodes(
    project_id: str, graph_store: ProjectGraphStore = Depends(get_project_graph_store)
) -> dict:
    return await graph_store.get_nodes(project_id=project_id)


@app.get("/api/v1/projects/{project_id}/graph/edges")
async def get_project_graph_edges(
    project_id: str, graph_store: ProjectGraphStore = Depends(get_project_graph_store)
) -> dict:
    return await graph_store.get_edges(project_id=project_id)


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "llm_default": settings.DEFAULT_LLM_MODEL}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
