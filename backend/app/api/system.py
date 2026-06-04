"""System-level status and readiness probes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_engine
from app.graph.adapter import get_graph_adapter
from app.storage.locus_adapter import LocusAdapter
from app.storage.ompa_adapter import OmpaAdapter

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status")
async def system_status() -> dict[str, Any]:
    """Aggregate subsystem health for operators and load balancers."""

    settings = get_settings()
    checks: dict[str, Any] = {}

    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok"}
    except Exception as exc:
        checks["database"] = {"status": "error", "detail": str(exc)}

    checks["graph"] = {
        "status": "ok",
        "backend": settings.GRAPH_BACKEND,
    }
    try:
        adapter = get_graph_adapter()
        await adapter.get_snapshot("__healthcheck__")
    except Exception as exc:
        checks["graph"]["status"] = "degraded"
        checks["graph"]["detail"] = str(exc)

    checks["storage"] = {
        "locus_backend": settings.LOCUS_BACKEND,
        "ompa_backend": settings.OMPA_BACKEND,
        "rtk_enabled": settings.RTK_ENABLED,
    }

    overall = "healthy"
    if any(c.get("status") == "error" for c in checks.values() if isinstance(c, dict)):
        overall = "unhealthy"
    elif any(c.get("status") == "degraded" for c in checks.values() if isinstance(c, dict)):
        overall = "degraded"

    return {
        "status": overall,
        "project": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "deployment_mode": settings.DEPLOYMENT_MODE,
        "checks": checks,
    }


@router.get("/storage-demo")
async def storage_demo() -> dict[str, Any]:
    """Lightweight smoke of Locus + OMPA local engines (dev / CI)."""

    locus = LocusAdapter("_system_demo")
    ompa = OmpaAdapter("_system_demo")
    await locus.index_files([{"source": "demo", "text": "system storage demo", "metadata": {}}])
    await ompa.record_decision("system storage demo")
    return {
        "locus": await locus.stats(),
        "ompa": await ompa.stats(),
    }
