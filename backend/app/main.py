from fastapi import Depends, FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agents.orchestrator import OrchestratorAgent
from agents.state import OrchestratorRequest
from automations.models import AutomationDefinition, AutomationSchedule, AutomationStatus, AutomationType
from automations.service import AutomationService
from automations.temporal_worker import temporal_worker_settings
from compliance.enforcer import ComplianceEnforcer
from core.config import settings
from core.integrations_manager import IntegrationsManager
from core.llm_router import LLMRouter
from graph.builder import ProjectGraphBuilder
from graph.enricher import GraphEnrichmentService
from ingestion.pipeline import IngestionPipeline
from integrations.intake_form import router as intake_router
from storage.status import get_storage_status
from workbench.service import WorkbenchService


app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(intake_router, prefix="/api/v1")


class CreateProjectRequest(BaseModel):
    files: list[str] = Field(default_factory=list)
    compliance: str = "standard"


class SetComplianceProfileRequest(BaseModel):
    category: str = Field(..., examples=["standard", "hipaa", "legal", "soc2", "gdpr"])


class ApproveAutomationRequest(BaseModel):
    approved_by: str = "project_owner"


class CreateAutomationRequest(BaseModel):
    type: AutomationType
    name: str
    payload: dict = Field(default_factory=dict)
    schedule: AutomationSchedule = Field(default_factory=AutomationSchedule)
    status: AutomationStatus = AutomationStatus.SCHEDULED
    requires_approval: bool = False


class WorkbenchQueryRequest(BaseModel):
    query: str
    limit: int = 5


class EnrichGraphRequest(BaseModel):
    use_llm: bool = False


def get_llm_router() -> LLMRouter:
    return LLMRouter()


def get_integrations_manager() -> IntegrationsManager:
    return IntegrationsManager()


def get_compliance_enforcer() -> ComplianceEnforcer:
    return ComplianceEnforcer()


def get_ingestion_pipeline() -> IngestionPipeline:
    return IngestionPipeline()


def get_graph_builder() -> ProjectGraphBuilder:
    return ProjectGraphBuilder()


def get_orchestrator_agent() -> OrchestratorAgent:
    return OrchestratorAgent()


def get_automation_service() -> AutomationService:
    return AutomationService()


def get_workbench_service() -> WorkbenchService:
    return WorkbenchService()


def get_graph_enrichment_service() -> GraphEnrichmentService:
    return GraphEnrichmentService()


@app.post("/api/v1/projects/")
async def create_project(
    request: CreateProjectRequest,
    compliance: ComplianceEnforcer = Depends(get_compliance_enforcer),
    integrations_manager: IntegrationsManager = Depends(get_integrations_manager),
    ingestion: IngestionPipeline = Depends(get_ingestion_pipeline),
    graph_builder: ProjectGraphBuilder = Depends(get_graph_builder),
):
    project_id = "proj_123"
    compliance.set_profile(project_id, request.compliance)
    await integrations_manager.get_recommended_connectors(compliance=request.compliance)
    ingestion_result = await ingestion.process_files(project_id, request.files)
    graph_result = graph_builder.build_from_latest_manifest(project_id)
    return {
        "project_id": project_id,
        "status": "orchestrated",
        "message": "ProjectForge AI is live!",
        "ingestion": ingestion_result,
        "graph": _graph_summary(graph_result),
    }


@app.post("/api/v1/projects/upload")
async def create_project_from_uploads(
    files: list[UploadFile] = File(default_factory=list),
    compliance: str = Form(default="standard"),
    project_id: str = Form(default="proj_123"),
    compliance_enforcer: ComplianceEnforcer = Depends(get_compliance_enforcer),
    integrations_manager: IntegrationsManager = Depends(get_integrations_manager),
    ingestion: IngestionPipeline = Depends(get_ingestion_pipeline),
    graph_builder: ProjectGraphBuilder = Depends(get_graph_builder),
):
    compliance_enforcer.set_profile(project_id, compliance)
    await integrations_manager.get_recommended_connectors(compliance=compliance)
    ingestion_result = await ingestion.process_files(project_id, files)
    graph_result = graph_builder.build_from_latest_manifest(project_id)
    return {
        "project_id": project_id,
        "status": "orchestrated",
        "message": "ProjectForge AI uploaded project documents.",
        "ingestion": ingestion_result,
        "graph": _graph_summary(graph_result),
    }


@app.get("/health")
async def health():
    storage = get_storage_status()
    return {
        "status": "healthy",
        "llm_default": settings.DEFAULT_LLM_MODEL,
        "storage": storage,
    }


@app.get("/api/v1/storage/{project_id}/status")
async def storage_status(project_id: str):
    return get_storage_status(project_id)


@app.get("/api/v1/projects/{project_id}/compliance/profile")
async def compliance_profile(
    project_id: str,
    compliance: ComplianceEnforcer = Depends(get_compliance_enforcer),
):
    return compliance.get_profile(project_id).as_dict()


@app.post("/api/v1/projects/{project_id}/compliance/profile")
async def set_compliance_profile(
    project_id: str,
    request: SetComplianceProfileRequest,
    compliance: ComplianceEnforcer = Depends(get_compliance_enforcer),
):
    return compliance.set_profile(project_id, request.category).as_dict()


@app.get("/api/v1/projects/{project_id}/compliance/audit")
async def compliance_audit(
    project_id: str,
    limit: int = 100,
    compliance: ComplianceEnforcer = Depends(get_compliance_enforcer),
):
    return {"project_id": project_id, "events": compliance.audit_events(project_id, limit)}


@app.post("/api/v1/projects/{project_id}/graph/build")
async def build_project_graph(
    project_id: str,
    graph_builder: ProjectGraphBuilder = Depends(get_graph_builder),
):
    return graph_builder.build_from_latest_manifest(project_id)


@app.get("/api/v1/projects/{project_id}/graph")
async def get_project_graph(
    project_id: str,
    graph_builder: ProjectGraphBuilder = Depends(get_graph_builder),
):
    return graph_builder.get_graph(project_id)


@app.get("/api/v1/projects/{project_id}/graph/status")
async def project_graph_status(
    project_id: str,
    graph_builder: ProjectGraphBuilder = Depends(get_graph_builder),
):
    return graph_builder.status(project_id)


@app.post("/api/v1/projects/{project_id}/graph/enrich")
async def enrich_project_graph(
    project_id: str,
    request: EnrichGraphRequest,
    enrichment: GraphEnrichmentService = Depends(get_graph_enrichment_service),
):
    return await enrichment.enrich(project_id, use_llm=request.use_llm)


@app.post("/api/v1/projects/{project_id}/workbench/query")
async def workbench_query(
    project_id: str,
    request: WorkbenchQueryRequest,
    workbench: WorkbenchService = Depends(get_workbench_service),
):
    return await workbench.query(project_id, request.query, limit=request.limit)


@app.post("/api/v1/orchestrator/run")
async def run_orchestrator(
    request: OrchestratorRequest,
    orchestrator: OrchestratorAgent = Depends(get_orchestrator_agent),
):
    return await orchestrator.run(request)


@app.get("/api/v1/projects/{project_id}/orchestrator/status")
async def orchestrator_status(
    project_id: str,
    run_id: str | None = None,
    orchestrator: OrchestratorAgent = Depends(get_orchestrator_agent),
):
    return orchestrator.status(project_id, run_id)


@app.post("/api/v1/projects/{project_id}/automations")
async def create_automation(
    project_id: str,
    request: CreateAutomationRequest,
    service: AutomationService = Depends(get_automation_service),
):
    automation = AutomationDefinition(project_id=project_id, **request.model_dump())
    return service.create(automation)


@app.get("/api/v1/projects/{project_id}/automations")
async def list_automations(
    project_id: str,
    service: AutomationService = Depends(get_automation_service),
):
    return service.list(project_id)


@app.post("/api/v1/projects/{project_id}/automations/{automation_id}/run")
async def run_automation(
    project_id: str,
    automation_id: str,
    service: AutomationService = Depends(get_automation_service),
):
    return await service.run(project_id, automation_id)


@app.post("/api/v1/projects/{project_id}/automations/{automation_id}/approve")
async def approve_automation(
    project_id: str,
    automation_id: str,
    request: ApproveAutomationRequest,
    service: AutomationService = Depends(get_automation_service),
):
    return service.approve(project_id, automation_id, request.approved_by)


@app.get("/api/v1/projects/{project_id}/automations/runs")
async def automation_runs(
    project_id: str,
    limit: int = 100,
    service: AutomationService = Depends(get_automation_service),
):
    return service.runs(project_id, limit)


@app.get("/api/v1/automations/temporal/status")
async def temporal_status():
    return temporal_worker_settings()


def _graph_summary(graph_result: dict) -> dict:
    return {
        "project_id": graph_result["project_id"],
        "node_count": graph_result["node_count"],
        "edge_count": graph_result["edge_count"],
        "warnings": graph_result["warnings"],
        "storage": graph_result["storage"],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
