from fastapi import Depends, FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings
from app.core.integrations_manager import IntegrationsManager
from app.core.llm_router import LLMRouter
from app.ingestion.pipeline import IngestionPipeline
from app.integrations.intake_form import router as intake_router

settings = Settings()
app = FastAPI(title=settings.PROJECT_NAME)

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


@app.post("/api/v1/projects/")
async def create_project(
    files: list[UploadFile] = File(default=[]),
    compliance: str = "standard",
    integrations_manager: IntegrationsManager = Depends(get_integrations_manager),
    llm_router: LLMRouter = Depends(get_llm_router),
) -> dict:
    pipeline = IngestionPipeline()
    project_id = "proj_123"

    # 1) Intake wizard data can be used to auto-connect integrations.
    # 2) Files are ingested into Locus + OMPA adapters.
    await pipeline.process_files(project_id=project_id, files=files)

    # Keep these dependencies resolved now so service wiring is validated.
    _ = integrations_manager
    _ = llm_router

    return {
        "project_id": project_id,
        "status": "orchestrated",
        "compliance": compliance,
        "message": "ProjectForge AI is live!",
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "llm_default": settings.DEFAULT_LLM_MODEL}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
