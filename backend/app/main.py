from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agents.orchestrator import OrchestratorAgent
from agents.state import OrchestratorRequest
from auth.router import router as auth_router
from automations.models import AutomationDefinition, AutomationSchedule, AutomationStatus, AutomationType
from automations.service import AutomationService
from automations.temporal_worker import run_due_automations, temporal_worker_settings
from compliance.enforcer import ComplianceEnforcer
from compliance.soc2_export import SOC2ExportService
from core.access_deps import get_actor_context, get_rbac_service, require_permission
from core.build_info import build_info_status
from core.config import settings
from core.hardening import SecurityHeadersMiddleware, cors_allowed_origins
from core.otel_export import jaeger_trace_batch, otlp_trace_payload, otel_status, prometheus_metrics_text
from core.integrations_manager import IntegrationsManager
from core.llm_keys import LLMKeyStore
from core.llm_router import LLMRouter
from core.llm_routing import routing_preview
from core.usage_meter import LLMUsageMeter
from core.rbac import ActorContext, RBACService
from core.upgrade_manager import UpgradeManager
from graph.builder import ProjectGraphBuilder
from graph.enricher import GraphEnrichmentService
from graph.models import EdgeType, NodeLabel
from graph.mutations import GraphMutationError, GraphMutationService
from ingestion.intake_sources import snapshot_postgres_schema
from ingestion.pipeline import IngestionPipeline
from integrations.intake_form import router as intake_router
from projects.portfolio_orchestrator import PortfolioOrchestratorService
from projects.service import PortfolioService
from projects.intelligence import PortfolioIntelligenceService
from projects.registry import ProjectRegistry
from spatial.service import SpatialService
from storage.status import get_storage_status
from core.observability import ObservabilityMiddleware, metrics_collector, observability_status, recent_traces
from tenancy.billing import TenantBillingService
from tenancy.context import TenantContext, get_tenant_context, get_tenant_registry
from tenancy.isolation import TenantIsolation
from tenancy.neo4j_isolation import TenantNeo4jRegistry, create_graph_adapter
from tenancy.registry import TenantRegistry
from tenancy.stripe_billing import StripeBillingService
from workbench.service import WorkbenchService


app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(ObservabilityMiddleware)

app.include_router(intake_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")


class CreateProjectRequest(BaseModel):
    name: str = "Starter Project"
    files: list[str] = Field(default_factory=list)
    compliance: str = "standard"
    tier: str | None = None


class RegisterProjectRequest(BaseModel):
    name: str = Field(..., min_length=1)
    compliance: str = "standard"
    tier: str | None = None


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
    max_retries: int | None = None


class WorkbenchQueryRequest(BaseModel):
    query: str
    limit: int = 5


class EnrichGraphRequest(BaseModel):
    use_llm: bool = False


class AssignMemberRequest(BaseModel):
    actor_id: str
    role: str = Field(..., examples=["viewer", "editor", "admin", "owner"])


class SelfImproveRequest(BaseModel):
    goal: str = "Analyze project outcomes and propose improvements"


class DatabaseSnapshotRequest(BaseModel):
    connection_uri: str | None = None
    db_schema: str = "public"


class LLMKeyRequest(BaseModel):
    provider: str = Field(..., examples=["openai", "anthropic", "groq"])
    api_key: str


class SpatialAssetRequest(BaseModel):
    name: str
    latitude: float
    longitude: float
    altitude: float | None = None
    asset_type: str = "site"
    graph_node_id: str | None = None
    properties: dict = Field(default_factory=dict)


class PortfolioOrchestratorRunRequest(BaseModel):
    goal: str = "Review portfolio risk and compliance posture"
    project_ids: list[str] = Field(default_factory=list)
    requested_agents: list[str] = Field(default_factory=list)


class RegisterTenantRequest(BaseModel):
    name: str
    tier: str | None = None


class BillingCheckoutRequest(BaseModel):
    success_url: str | None = None
    target_tier: str | None = None
    billing_mode: str = "payment"


class BillingSubscribeRequest(BaseModel):
    success_url: str | None = None
    target_tier: str | None = None


class CreateGraphNodeRequest(BaseModel):
    label: NodeLabel
    properties: dict = Field(default_factory=dict)


class UpdateGraphNodeRequest(BaseModel):
    properties: dict = Field(default_factory=dict)


class CreateGraphEdgeRequest(BaseModel):
    source_id: str
    target_id: str
    type: EdgeType = EdgeType.DEPENDS_ON
    properties: dict = Field(default_factory=dict)


def get_llm_router() -> LLMRouter:
    return LLMRouter()


def get_integrations_manager() -> IntegrationsManager:
    return IntegrationsManager()


def get_compliance_enforcer() -> ComplianceEnforcer:
    return ComplianceEnforcer()


def get_soc2_export_service() -> SOC2ExportService:
    return SOC2ExportService(compliance=get_compliance_enforcer())


def get_ingestion_pipeline() -> IngestionPipeline:
    return IngestionPipeline()


def get_graph_builder(tenant: TenantContext = Depends(get_tenant_context)) -> ProjectGraphBuilder:
    return ProjectGraphBuilder(adapter=create_graph_adapter(tenant.tenant_id))


def get_orchestrator_agent() -> OrchestratorAgent:
    return OrchestratorAgent()


def get_automation_service() -> AutomationService:
    return AutomationService()


def get_workbench_service() -> WorkbenchService:
    return WorkbenchService()


def get_graph_enrichment_service(tenant: TenantContext = Depends(get_tenant_context)) -> GraphEnrichmentService:
    return GraphEnrichmentService(builder=ProjectGraphBuilder(adapter=create_graph_adapter(tenant.tenant_id)))


def get_graph_mutation_service(tenant: TenantContext = Depends(get_tenant_context)) -> GraphMutationService:
    return GraphMutationService(builder=ProjectGraphBuilder(adapter=create_graph_adapter(tenant.tenant_id)))


def get_upgrade_manager() -> UpgradeManager:
    return UpgradeManager()


def get_portfolio_service(tenant: TenantContext = Depends(get_tenant_context)) -> PortfolioService:
    TenantIsolation.ensure_tenant_dirs(tenant.tenant_id)
    return PortfolioService(registry=ProjectRegistry(tenant_id=tenant.tenant_id))


def get_portfolio_intelligence_service(
    tenant: TenantContext = Depends(get_tenant_context),
) -> PortfolioIntelligenceService:
    TenantIsolation.ensure_tenant_dirs(tenant.tenant_id)
    registry = ProjectRegistry(tenant_id=tenant.tenant_id)
    return PortfolioIntelligenceService(registry=registry)


def get_portfolio_orchestrator_service(
    orchestrator: OrchestratorAgent = Depends(get_orchestrator_agent),
    tenant: TenantContext = Depends(get_tenant_context),
) -> PortfolioOrchestratorService:
    TenantIsolation.ensure_tenant_dirs(tenant.tenant_id)
    return PortfolioOrchestratorService(
        orchestrator=orchestrator,
        registry=ProjectRegistry(tenant_id=tenant.tenant_id),
    )


def get_llm_key_store() -> LLMKeyStore:
    return LLMKeyStore()


def get_llm_usage_meter() -> LLMUsageMeter:
    return LLMUsageMeter()


def get_spatial_service() -> SpatialService:
    return SpatialService()


def get_tenant_billing_service(
    tenant: TenantContext = Depends(get_tenant_context),
) -> TenantBillingService:
    return TenantBillingService(
        project_registry_factory=lambda tenant_id: ProjectRegistry(tenant_id=tenant_id),
    )


def get_stripe_billing_service() -> StripeBillingService:
    return StripeBillingService()


@app.get("/api/v1/tenants")
async def list_tenants(registry: TenantRegistry = Depends(get_tenant_registry)):
    tenants = registry.list_tenants()
    return {"count": len(tenants), "tenants": [tenant.as_dict() for tenant in tenants]}


@app.post("/api/v1/tenants/register")
async def register_tenant(
    request: RegisterTenantRequest,
    registry: TenantRegistry = Depends(get_tenant_registry),
):
    record = registry.create(name=request.name, tier=request.tier)
    TenantIsolation.ensure_tenant_dirs(record.tenant_id)
    if settings.NEO4J_TENANT_ISOLATION_ENABLED:
        TenantNeo4jRegistry().ensure_database(record.tenant_id)
    return {"status": "created", "tenant": record.as_dict()}


@app.get("/api/v1/tenants/{tenant_id}/status")
async def tenant_status(
    tenant_id: str,
    registry: TenantRegistry = Depends(get_tenant_registry),
):
    from fastapi import HTTPException

    record = registry.get(tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Unknown tenant: {tenant_id}")
    return {
        "tenant": record.as_dict(),
        "isolation_enabled": settings.TENANT_ISOLATION_ENABLED,
        "project_registry_root": TenantIsolation.project_registry_root(tenant_id),
        "neo4j": TenantNeo4jRegistry().status(tenant_id),
    }


@app.get("/api/v1/tenants/{tenant_id}/billing/invoices")
async def tenant_billing_invoices(
    tenant_id: str,
    stripe_billing: StripeBillingService = Depends(get_stripe_billing_service),
):
    return stripe_billing.list_invoices(tenant_id)


@app.post("/api/v1/tenants/{tenant_id}/billing/checkout")
async def tenant_billing_checkout(
    tenant_id: str,
    request: BillingCheckoutRequest,
    stripe_billing: StripeBillingService = Depends(get_stripe_billing_service),
):
    from fastapi import HTTPException

    try:
        return await stripe_billing.create_checkout(
            tenant_id,
            success_url=request.success_url,
            target_tier=request.target_tier,
            billing_mode=request.billing_mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/v1/tenants/{tenant_id}/billing/subscribe")
async def tenant_billing_subscribe(
    tenant_id: str,
    request: BillingSubscribeRequest,
    stripe_billing: StripeBillingService = Depends(get_stripe_billing_service),
):
    from fastapi import HTTPException

    try:
        return await stripe_billing.create_subscription(
            tenant_id,
            success_url=request.success_url,
            target_tier=request.target_tier,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/tenants/{tenant_id}/billing/subscription")
async def tenant_billing_subscription(
    tenant_id: str,
    stripe_billing: StripeBillingService = Depends(get_stripe_billing_service),
):
    return stripe_billing.get_subscription(tenant_id)


@app.post("/api/v1/billing/webhook")
async def stripe_billing_webhook(
    request: Request,
    stripe_billing: StripeBillingService = Depends(get_stripe_billing_service),
):
    from fastapi import HTTPException

    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    try:
        return stripe_billing.handle_webhook(payload, signature)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/billing/status")
async def billing_provider_status(
    stripe_billing: StripeBillingService = Depends(get_stripe_billing_service),
):
    return stripe_billing.billing_status()


@app.get("/api/v1/tenants/{tenant_id}/billing/usage")
async def tenant_billing_usage(
    tenant_id: str,
    billing: TenantBillingService = Depends(get_tenant_billing_service),
):
    from fastapi import HTTPException

    try:
        return billing.usage_summary(tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/tenants/{tenant_id}/billing/quota")
async def tenant_billing_quota(
    tenant_id: str,
    billing: TenantBillingService = Depends(get_tenant_billing_service),
):
    from fastapi import HTTPException

    try:
        return billing.quota_status(tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/tenants/{tenant_id}/billing/check")
async def tenant_billing_check(
    tenant_id: str,
    action: str,
    billing: TenantBillingService = Depends(get_tenant_billing_service),
):
    from fastapi import HTTPException

    try:
        return billing.check_action(tenant_id, action)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/projects")
async def list_projects(
    include_archived: bool = False,
    portfolio: PortfolioService = Depends(get_portfolio_service),
):
    return portfolio.list_projects(include_archived=include_archived)


@app.get("/api/v1/portfolio/summary")
async def portfolio_summary(
    include_archived: bool = False,
    portfolio: PortfolioService = Depends(get_portfolio_service),
):
    return portfolio.portfolio_summary(include_archived=include_archived)


@app.get("/api/v1/portfolio/compliance/rollup")
async def portfolio_compliance_rollup(
    include_archived: bool = False,
    intelligence: PortfolioIntelligenceService = Depends(get_portfolio_intelligence_service),
):
    return intelligence.compliance_rollup(include_archived=include_archived)


@app.get("/api/v1/portfolio/risk/rollup")
async def portfolio_risk_rollup(
    include_archived: bool = False,
    intelligence: PortfolioIntelligenceService = Depends(get_portfolio_intelligence_service),
):
    return intelligence.risk_rollup(include_archived=include_archived)


@app.get("/api/v1/portfolio/intelligence/dashboard")
async def portfolio_executive_dashboard(
    include_archived: bool = False,
    intelligence: PortfolioIntelligenceService = Depends(get_portfolio_intelligence_service),
):
    return intelligence.executive_dashboard(include_archived=include_archived)


@app.post("/api/v1/portfolio/orchestrator/run")
async def portfolio_orchestrator_run(
    request: PortfolioOrchestratorRunRequest,
    actor: ActorContext = Depends(get_actor_context),
    rbac: RBACService = Depends(get_rbac_service),
    portfolio: PortfolioService = Depends(get_portfolio_service),
    portfolio_orchestrator: PortfolioOrchestratorService = Depends(get_portfolio_orchestrator_service),
):
    from fastapi import HTTPException

    targets = request.project_ids
    if not targets:
        targets = [
            project["project_id"]
            for project in portfolio.list_projects(include_archived=False)["projects"]
        ]
    for project_id in targets:
        try:
            rbac.require(project_id, actor, "orchestrator.run")
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
    try:
        return await portfolio_orchestrator.run(
            goal=request.goal,
            project_ids=targets or None,
            requested_agents=request.requested_agents or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/portfolio/orchestrator/runs")
async def portfolio_orchestrator_runs(
    limit: int = 20,
    portfolio_orchestrator: PortfolioOrchestratorService = Depends(get_portfolio_orchestrator_service),
):
    return portfolio_orchestrator.list_runs(limit)


@app.get("/api/v1/portfolio/orchestrator/runs/{portfolio_run_id}")
async def portfolio_orchestrator_run_detail(
    portfolio_run_id: str,
    portfolio_orchestrator: PortfolioOrchestratorService = Depends(get_portfolio_orchestrator_service),
):
    from fastapi import HTTPException

    try:
        return portfolio_orchestrator.get_run(portfolio_run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/projects/{project_id}/record")
async def get_project_record(
    project_id: str,
    portfolio: PortfolioService = Depends(get_portfolio_service),
):
    try:
        return portfolio.get_project(project_id)
    except ValueError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/v1/projects/register")
async def register_project(
    request: RegisterProjectRequest,
    actor: ActorContext = Depends(get_actor_context),
    rbac: RBACService = Depends(get_rbac_service),
    tenant: TenantContext = Depends(get_tenant_context),
    portfolio: PortfolioService = Depends(get_portfolio_service),
    billing: TenantBillingService = Depends(get_tenant_billing_service),
):
    from fastapi import HTTPException

    try:
        rbac.require(settings.DEFAULT_PROJECT_ID, actor, "access.manage")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    if settings.TENANT_BILLING_ENABLED:
        decision = billing.check_action(tenant.tenant_id, "project_create")
        if not decision["allowed"]:
            raise HTTPException(status_code=402, detail=decision["reason"])

    record = portfolio.create_project(
        name=request.name,
        compliance=request.compliance,
        tier=request.tier,
    )
    return {"status": "created", "project": record.as_dict()}


@app.post("/api/v1/projects/{project_id}/archive")
async def archive_project(
    project_id: str,
    _: ActorContext = Depends(require_permission("access.manage")),
    portfolio: PortfolioService = Depends(get_portfolio_service),
):
    try:
        record = portfolio.archive_project(project_id)
    except ValueError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "archived", "project": record.as_dict()}


@app.get("/api/v1/projects/{project_id}/access/members")
async def list_project_members(
    project_id: str,
    _: ActorContext = Depends(require_permission("access.manage")),
    rbac: RBACService = Depends(get_rbac_service),
):
    return {"project_id": project_id, "members": rbac.list_members(project_id)}


@app.post("/api/v1/projects/{project_id}/access/members")
async def assign_project_member(
    project_id: str,
    request: AssignMemberRequest,
    _: ActorContext = Depends(require_permission("access.manage")),
    rbac: RBACService = Depends(get_rbac_service),
):
    try:
        member = rbac.assign_member(project_id, request.actor_id, request.role)
    except ValueError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"project_id": project_id, "member": member}


@app.get("/api/v1/projects/{project_id}/access/check")
async def check_project_access(
    project_id: str,
    action: str,
    actor: ActorContext = Depends(get_actor_context),
    rbac: RBACService = Depends(get_rbac_service),
):
    decision = rbac.check(project_id, actor, action)
    return {
        "project_id": project_id,
        "action": action,
        "allowed": decision.allowed,
        "reason": decision.reason,
        "role": decision.role,
        "actor": actor.as_dict(),
    }


@app.get("/api/v1/projects/{project_id}/upgrade/status")
async def upgrade_status(
    project_id: str,
    _: ActorContext = Depends(require_permission("project.read")),
    upgrade: UpgradeManager = Depends(get_upgrade_manager),
):
    return upgrade.feature_status(project_id)


@app.post("/api/v1/projects/{project_id}/upgrade/self-improve")
async def run_self_improvement(
    project_id: str,
    request: SelfImproveRequest,
    actor: ActorContext = Depends(require_permission("self_learning.run")),
    upgrade: UpgradeManager = Depends(get_upgrade_manager),
    compliance: ComplianceEnforcer = Depends(get_compliance_enforcer),
    orchestrator: OrchestratorAgent = Depends(get_orchestrator_agent),
):
    upgrade.require_feature(project_id, "self_learning")
    compliance_decision = compliance.check_action(project_id, "self_learning", payload={"goal": request.goal})
    if not compliance_decision.allowed:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail=compliance_decision.reason)

    result = await orchestrator.run(
        OrchestratorRequest(
            project_id=project_id,
            goal=f"[self-improve] {request.goal}",
            requested_agents=["intake_analyst", "risk_analyst", "template_generator"],
        )
    )
    return {
        "project_id": project_id,
        "actor": actor.as_dict(),
        "self_improvement": result,
    }


@app.post("/api/v1/projects/")
async def create_project(
    request: CreateProjectRequest,
    compliance: ComplianceEnforcer = Depends(get_compliance_enforcer),
    integrations_manager: IntegrationsManager = Depends(get_integrations_manager),
    ingestion: IngestionPipeline = Depends(get_ingestion_pipeline),
    graph_builder: ProjectGraphBuilder = Depends(get_graph_builder),
    portfolio: PortfolioService = Depends(get_portfolio_service),
):
    record = portfolio.create_project(
        name=request.name,
        compliance=request.compliance,
        tier=request.tier,
    )
    project_id = record.project_id
    await integrations_manager.get_recommended_connectors(compliance=request.compliance)
    ingestion_result = await ingestion.process_files(project_id, request.files)
    graph_result = graph_builder.build_from_latest_manifest(project_id)
    portfolio.registry.touch(project_id)
    return {
        "project_id": project_id,
        "project": record.as_dict(),
        "status": "orchestrated",
        "message": "ProjectForge AI is live!",
        "ingestion": ingestion_result,
        "graph": _graph_summary(graph_result),
    }


@app.post("/api/v1/projects/upload")
async def create_project_from_uploads(
    files: list[UploadFile] = File(default_factory=list),
    compliance: str = Form(default="standard"),
    project_id: str = Form(default=""),
    name: str = Form(default="Uploaded project"),
    tier: str = Form(default=""),
    compliance_enforcer: ComplianceEnforcer = Depends(get_compliance_enforcer),
    integrations_manager: IntegrationsManager = Depends(get_integrations_manager),
    ingestion: IngestionPipeline = Depends(get_ingestion_pipeline),
    graph_builder: ProjectGraphBuilder = Depends(get_graph_builder),
    portfolio: PortfolioService = Depends(get_portfolio_service),
):
    if project_id:
        record = portfolio.registry.get(project_id)
        if record is None:
            record = portfolio.registry.create(
                name=name,
                compliance=compliance,
                tier=tier or None,
                project_id=project_id,
            )
            compliance_enforcer.set_profile(project_id, compliance)
        else:
            compliance_enforcer.set_profile(project_id, record.compliance)
    else:
        record = portfolio.create_project(
            name=name,
            compliance=compliance,
            tier=tier or None,
        )
        project_id = record.project_id

    await integrations_manager.get_recommended_connectors(compliance=compliance)
    ingestion_result = await ingestion.process_files(project_id, files)
    graph_result = graph_builder.build_from_latest_manifest(project_id)
    portfolio.registry.touch(project_id)
    return {
        "project_id": project_id,
        "project": record.as_dict(),
        "status": "orchestrated",
        "message": "ProjectForge AI uploaded project documents.",
        "ingestion": ingestion_result,
        "graph": _graph_summary(graph_result),
    }


@app.post("/api/v1/projects/{project_id}/ingestion/database-snapshot")
async def ingest_database_snapshot(
    project_id: str,
    request: DatabaseSnapshotRequest,
    _: ActorContext = Depends(require_permission("graph.write")),
    ingestion: IngestionPipeline = Depends(get_ingestion_pipeline),
    graph_builder: ProjectGraphBuilder = Depends(get_graph_builder),
    portfolio: PortfolioService = Depends(get_portfolio_service),
):
    from fastapi import HTTPException

    if portfolio.registry.get(project_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown project: {project_id}")

    connection_uri = request.connection_uri or settings.POSTGRES_URI
    try:
        parsed = snapshot_postgres_schema(connection_uri, schema=request.db_schema)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    ingestion_result = await ingestion.append_documents(project_id, [parsed])
    graph_result = graph_builder.build_from_latest_manifest(project_id)
    portfolio.registry.touch(project_id)
    return {
        "project_id": project_id,
        "status": "snapshot_ingested",
        "ingestion": ingestion_result,
        "graph": _graph_summary(graph_result),
    }


@app.get("/api/v1/projects/{project_id}/llm/routing")
async def llm_routing_preview(
    project_id: str,
    _: ActorContext = Depends(require_permission("project.read")),
):
    return routing_preview(project_id)


@app.get("/api/v1/projects/{project_id}/llm/keys")
async def list_llm_keys(
    project_id: str,
    _: ActorContext = Depends(require_permission("project.read")),
    key_store: LLMKeyStore = Depends(get_llm_key_store),
):
    return {"project_id": project_id, "keys": key_store.list_keys(project_id)}


@app.post("/api/v1/projects/{project_id}/llm/keys")
async def upsert_llm_key(
    project_id: str,
    request: LLMKeyRequest,
    _: ActorContext = Depends(require_permission("access.manage")),
    key_store: LLMKeyStore = Depends(get_llm_key_store),
):
    record = key_store.upsert(
        project_id=project_id,
        provider=request.provider,
        api_key=request.api_key,
    )
    return {"project_id": project_id, "key": record}


@app.delete("/api/v1/projects/{project_id}/llm/keys/{provider}")
async def delete_llm_key(
    project_id: str,
    provider: str,
    _: ActorContext = Depends(require_permission("access.manage")),
    key_store: LLMKeyStore = Depends(get_llm_key_store),
):
    deleted = key_store.delete(project_id, provider)
    if not deleted:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"No key for provider: {provider}")
    return {"project_id": project_id, "provider": provider, "status": "deleted"}


@app.get("/api/v1/projects/{project_id}/llm/usage")
async def llm_usage_summary(
    project_id: str,
    limit: int = 100,
    _: ActorContext = Depends(require_permission("project.read")),
    usage_meter: LLMUsageMeter = Depends(get_llm_usage_meter),
):
    return usage_meter.summary(project_id, limit)


@app.get("/api/v1/projects/{project_id}/spatial/assets")
async def list_spatial_assets(
    project_id: str,
    _: ActorContext = Depends(require_permission("project.read")),
    spatial: SpatialService = Depends(get_spatial_service),
):
    return spatial.list_assets(project_id)


@app.post("/api/v1/projects/{project_id}/spatial/assets")
async def register_spatial_asset(
    project_id: str,
    request: SpatialAssetRequest,
    _: ActorContext = Depends(require_permission("graph.write")),
    spatial: SpatialService = Depends(get_spatial_service),
):
    asset = spatial.register_asset(
        project_id,
        name=request.name,
        latitude=request.latitude,
        longitude=request.longitude,
        altitude=request.altitude,
        asset_type=request.asset_type,
        graph_node_id=request.graph_node_id,
        properties=request.properties,
    )
    return {"project_id": project_id, "asset": asset.as_dict()}


@app.post("/api/v1/projects/{project_id}/spatial/sync-graph")
async def sync_spatial_from_graph(
    project_id: str,
    _: ActorContext = Depends(require_permission("graph.write")),
    spatial: SpatialService = Depends(get_spatial_service),
):
    return spatial.sync_from_graph(project_id)


@app.get("/api/v1/projects/{project_id}/spatial/map")
async def spatial_map_view(
    project_id: str,
    _: ActorContext = Depends(require_permission("project.read")),
    spatial: SpatialService = Depends(get_spatial_service),
):
    return spatial.map_view(project_id)


@app.get("/api/v1/projects/{project_id}/spatial/status")
async def spatial_rtk_status(
    project_id: str,
    _: ActorContext = Depends(require_permission("project.read")),
    spatial: SpatialService = Depends(get_spatial_service),
):
    return spatial.rtk_status(project_id)


@app.get("/health")
async def health():
    storage = get_storage_status()
    return {
        "status": "healthy",
        "llm_default": settings.DEFAULT_LLM_MODEL,
        "deployment_mode": settings.DEPLOYMENT_MODE,
        "project_tier": settings.PROJECT_TIER,
        "rbac_enforce": settings.RBAC_ENFORCE,
        "oidc_enabled": settings.OIDC_ENABLED,
        "oidc_mock": settings.OIDC_MOCK,
        "production_hardening": settings.PRODUCTION_HARDENING,
        "build_info": build_info_status(),
        "tenant_isolation_enabled": settings.TENANT_ISOLATION_ENABLED,
        "observability": observability_status(),
        "storage": storage,
    }


@app.get("/api/v1/deploy/status")
async def deploy_status():
    return {
        "deployment_mode": settings.DEPLOYMENT_MODE,
        "project_tier": settings.PROJECT_TIER,
        "production_hardening": settings.PRODUCTION_HARDENING,
        "security_headers_enabled": settings.SECURITY_HEADERS_ENABLED or settings.PRODUCTION_HARDENING,
        "strict_transport_security": settings.STRICT_TRANSPORT_SECURITY or settings.PRODUCTION_HARDENING,
        "rbac_enforce": settings.RBAC_ENFORCE,
        "oidc_enabled": settings.OIDC_ENABLED,
        "oidc_mock": settings.OIDC_MOCK,
        "tenant_isolation_enabled": settings.TENANT_ISOLATION_ENABLED,
        "airgap_require_signature": settings.AIRGAP_REQUIRE_SIGNATURE,
        "cors_allowed_origins": cors_allowed_origins(),
        "build_info": build_info_status(),
        "observability": observability_status(),
    }


@app.get("/api/v1/observability/status")
async def observability_status_endpoint():
    return observability_status()


@app.get("/api/v1/observability/metrics")
async def observability_metrics(limit: int = 50):
    return {
        "status": observability_status(),
        "metrics": metrics_collector.snapshot() if settings.METRICS_ENABLED else {},
        "recent_traces": recent_traces(limit),
        "otel": otel_status(),
    }


@app.get("/api/v1/observability/prometheus")
async def observability_prometheus():
    from fastapi import Response

    if not settings.OTEL_EXPORTER_ENABLED:
        return {"enabled": False}
    return Response(content=prometheus_metrics_text(), media_type="text/plain; version=0.0.4")


@app.get("/api/v1/observability/traces/jaeger")
async def observability_jaeger_export(limit: int = 50):
    if not settings.OTEL_EXPORTER_ENABLED:
        return {"enabled": False, "data": []}
    return jaeger_trace_batch(limit)


@app.get("/api/v1/observability/traces/otlp")
async def observability_otlp_export(limit: int = 50):
    if not settings.OTEL_EXPORTER_ENABLED:
        return {"enabled": False, "resourceSpans": []}
    return otlp_trace_payload(limit)


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
    _: ActorContext = Depends(require_permission("compliance.set")),
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


@app.get("/api/v1/projects/{project_id}/compliance/export/soc2")
async def compliance_export_soc2(
    project_id: str,
    limit: int = 500,
    _: ActorContext = Depends(require_permission("compliance.export")),
    exporter: SOC2ExportService = Depends(get_soc2_export_service),
):
    return exporter.export_project(project_id, limit=limit)


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


@app.post("/api/v1/graph/bootstrap")
async def bootstrap_graph_storage(
    graph_builder: ProjectGraphBuilder = Depends(get_graph_builder),
):
    return graph_builder.adapter.bootstrap()


@app.post("/api/v1/projects/{project_id}/graph/enrich")
async def enrich_project_graph(
    project_id: str,
    request: EnrichGraphRequest,
    _: ActorContext = Depends(require_permission("graph.write")),
    enrichment: GraphEnrichmentService = Depends(get_graph_enrichment_service),
    upgrade: UpgradeManager = Depends(get_upgrade_manager),
):
    if request.use_llm:
        upgrade.require_feature(project_id, "graph_enrichment_llm")
    return await enrichment.enrich(project_id, use_llm=request.use_llm)


@app.post("/api/v1/projects/{project_id}/graph/nodes")
async def create_graph_node(
    project_id: str,
    request: CreateGraphNodeRequest,
    _: ActorContext = Depends(require_permission("graph.write")),
    mutations: GraphMutationService = Depends(get_graph_mutation_service),
):
    try:
        return mutations.create_node(project_id, label=request.label, properties=request.properties)
    except GraphMutationError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/api/v1/projects/{project_id}/graph/nodes/{node_id}")
async def update_graph_node(
    project_id: str,
    node_id: str,
    request: UpdateGraphNodeRequest,
    _: ActorContext = Depends(require_permission("graph.write")),
    mutations: GraphMutationService = Depends(get_graph_mutation_service),
):
    try:
        return mutations.update_node(project_id, node_id, properties=request.properties)
    except GraphMutationError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/v1/projects/{project_id}/graph/nodes/{node_id}")
async def delete_graph_node(
    project_id: str,
    node_id: str,
    _: ActorContext = Depends(require_permission("graph.write")),
    mutations: GraphMutationService = Depends(get_graph_mutation_service),
):
    try:
        return mutations.delete_node(project_id, node_id)
    except GraphMutationError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/projects/{project_id}/graph/edges")
async def create_graph_edge(
    project_id: str,
    request: CreateGraphEdgeRequest,
    _: ActorContext = Depends(require_permission("graph.write")),
    mutations: GraphMutationService = Depends(get_graph_mutation_service),
):
    try:
        return mutations.create_edge(
            project_id,
            source_id=request.source_id,
            target_id=request.target_id,
            edge_type=request.type,
            properties=request.properties,
        )
    except GraphMutationError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/v1/projects/{project_id}/graph/edges")
async def delete_graph_edge(
    project_id: str,
    source_id: str,
    target_id: str,
    edge_type: EdgeType = EdgeType.DEPENDS_ON,
    _: ActorContext = Depends(require_permission("graph.write")),
    mutations: GraphMutationService = Depends(get_graph_mutation_service),
):
    try:
        return mutations.delete_edge(
            project_id,
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
        )
    except GraphMutationError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
    actor: ActorContext = Depends(get_actor_context),
    rbac: RBACService = Depends(get_rbac_service),
    orchestrator: OrchestratorAgent = Depends(get_orchestrator_agent),
):
    try:
        rbac.require(request.project_id, actor, "orchestrator.run")
    except PermissionError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return await orchestrator.run(request)


@app.get("/api/v1/projects/{project_id}/orchestrator/status")
async def orchestrator_status(
    project_id: str,
    run_id: str | None = None,
    orchestrator: OrchestratorAgent = Depends(get_orchestrator_agent),
):
    return orchestrator.status(project_id, run_id)


@app.get("/api/v1/projects/{project_id}/orchestrator/runs")
async def orchestrator_runs(
    project_id: str,
    limit: int = 20,
    orchestrator: OrchestratorAgent = Depends(get_orchestrator_agent),
):
    return orchestrator.list_runs(project_id, limit)


@app.get("/api/v1/projects/{project_id}/orchestrator/audit")
async def orchestrator_audit(
    project_id: str,
    run_id: str | None = None,
    limit: int = 100,
    orchestrator: OrchestratorAgent = Depends(get_orchestrator_agent),
):
    return orchestrator.audit_events(project_id, run_id, limit)


@app.post("/api/v1/projects/{project_id}/automations")
async def create_automation(
    project_id: str,
    request: CreateAutomationRequest,
    service: AutomationService = Depends(get_automation_service),
):
    automation = AutomationDefinition(project_id=project_id, **request.model_dump(exclude_none=True))
    created = service.create(automation)
    if settings.TEMPORAL_SYNC_SCHEDULES:
        schedule_result = await service.sync_temporal_schedule(project_id, created["id"])
        created["temporal_schedule"] = schedule_result
    return created


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
    _: ActorContext = Depends(require_permission("automations.approve")),
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


@app.get("/api/v1/projects/{project_id}/automations/dead-letters")
async def automation_dead_letters(
    project_id: str,
    limit: int = 100,
    service: AutomationService = Depends(get_automation_service),
):
    return service.dead_letters(project_id, limit)


@app.post("/api/v1/projects/{project_id}/automations/{automation_id}/retry")
async def retry_automation(
    project_id: str,
    automation_id: str,
    service: AutomationService = Depends(get_automation_service),
):
    return await service.retry(project_id, automation_id)


@app.get("/api/v1/automations/temporal/status")
async def temporal_status():
    return temporal_worker_settings()


@app.post("/api/v1/automations/temporal/run-due")
async def temporal_run_due(
    service: AutomationService = Depends(get_automation_service),
):
    return await run_due_automations(service)


@app.post("/api/v1/automations/temporal/start-due")
async def temporal_start_due():
    from automations.temporal_worker import start_due_automations_workflow

    return await start_due_automations_workflow()


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
