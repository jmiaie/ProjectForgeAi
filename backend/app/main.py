from fastapi import Depends, FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.agents.orchestrator import Orchestrator
from app.core.config import Settings
from app.core.integrations_manager import IntegrationsManager
from app.core.llm_router import LLMRouter
from app.ingestion.pipeline import IngestionPipeline
from app.integrations.intake_form import router as intake_router
from app.storage.neo4j_adapter import ProjectGraphStore

settings = Settings()
app = FastAPI(title=settings.PROJECT_NAME)
orchestrator = Orchestrator()
project_graph_store = ProjectGraphStore(settings=settings)

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
    orchestration = await workflow_orchestrator.run(project_id=project_id, compliance=compliance)
    graph_summary = await graph_store.upsert_project_graph(
        project_id=project_id,
        compliance=compliance,
        ingestion=orchestration.get("ingestion"),
        orchestration=orchestration,
    )
    return {"orchestration": orchestration, "graph": graph_summary}


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
