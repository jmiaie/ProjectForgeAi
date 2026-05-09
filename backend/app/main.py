from fastapi import Depends, FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.config import settings
from core.integrations_manager import IntegrationsManager
from core.llm_router import LLMRouter
from ingestion.pipeline import IngestionPipeline
from integrations.intake_form import router as intake_router
from storage.status import get_storage_status


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


def get_llm_router() -> LLMRouter:
    return LLMRouter()


def get_integrations_manager() -> IntegrationsManager:
    return IntegrationsManager()


def get_ingestion_pipeline() -> IngestionPipeline:
    return IngestionPipeline()


@app.post("/api/v1/projects/")
async def create_project(
    request: CreateProjectRequest,
    integrations_manager: IntegrationsManager = Depends(get_integrations_manager),
    ingestion: IngestionPipeline = Depends(get_ingestion_pipeline),
):
    project_id = "proj_123"
    await integrations_manager.get_recommended_connectors(compliance=request.compliance)
    ingestion_result = await ingestion.process_files(project_id, request.files)
    return {
        "project_id": project_id,
        "status": "orchestrated",
        "message": "ProjectForge AI is live!",
        "ingestion": ingestion_result,
    }


@app.post("/api/v1/projects/upload")
async def create_project_from_uploads(
    files: list[UploadFile] = File(default_factory=list),
    compliance: str = Form(default="standard"),
    project_id: str = Form(default="proj_123"),
    integrations_manager: IntegrationsManager = Depends(get_integrations_manager),
    ingestion: IngestionPipeline = Depends(get_ingestion_pipeline),
):
    await integrations_manager.get_recommended_connectors(compliance=compliance)
    ingestion_result = await ingestion.process_files(project_id, files)
    return {
        "project_id": project_id,
        "status": "orchestrated",
        "message": "ProjectForge AI uploaded project documents.",
        "ingestion": ingestion_result,
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
