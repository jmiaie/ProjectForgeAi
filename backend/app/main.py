"""ProjectForge AI FastAPI entry point.

Wires the Intake / Connections wizard, the LLM router, integrations manager,
storage adapters, and the project orchestration routes. Keep the file thin:
new functionality should land in feature routers under :mod:`app.api`.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.agents import router as agents_router
from app.api.audit import router as audit_router
from app.api.projects import router as projects_router
from app.db.base import Base
from app.db.session import get_engine
from app.core.config import get_settings
from app.core.integrations_manager import IntegrationsManager
from app.core.llm_router import LLMRouter
from app.integrations.intake_form import router as intake_router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Application factory used by ASGI servers and tests."""

    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "%s v%s starting in %s mode",
            settings.PROJECT_NAME,
            settings.PROJECT_VERSION,
            settings.DEPLOYMENT_MODE,
        )
        if settings.AUTO_CREATE_SCHEMA:
            engine = get_engine()
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        yield

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(intake_router, prefix="/api/v1")
    app.include_router(projects_router, prefix="/api/v1")
    app.include_router(agents_router, prefix="/api/v1")
    app.include_router(audit_router, prefix="/api/v1")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {
            "status": "healthy",
            "project": settings.PROJECT_NAME,
            "version": settings.PROJECT_VERSION,
            "llm_default": settings.DEFAULT_LLM_MODEL,
            "deployment_mode": settings.DEPLOYMENT_MODE,
        }

    @app.get("/")
    async def root() -> dict[str, str]:
        return {
            "name": settings.PROJECT_NAME,
            "version": settings.PROJECT_VERSION,
            "docs": "/docs",
        }

    return app


app = create_app()


def get_llm_router() -> LLMRouter:
    return LLMRouter()


def get_integrations_manager() -> IntegrationsManager:
    return IntegrationsManager()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
