"""Predictive autoscaling hooks derived from live capacity signals."""

from __future__ import annotations

from typing import Any

from core.capacity import compute_capacity_plan
from core.config import settings


def compute_autoscale_hooks() -> dict[str, Any]:
    plan = compute_capacity_plan()
    metrics = plan["metrics"]
    request_count = int(metrics["request_count"])
    avg_latency = float(metrics["average_latency_ms"])
    error_rate = (
        metrics["error_count"] / request_count if request_count else 0.0
    )

    backend_replicas = settings.AUTOSCALE_BACKEND_REPLICAS_BASE
    if request_count > 100_000:
        backend_replicas = max(backend_replicas, 4)
    elif request_count > 25_000:
        backend_replicas = max(backend_replicas, 3)
    elif request_count > 5_000:
        backend_replicas = max(backend_replicas, 2)

    if avg_latency > settings.SLO_LATENCY_MS_TARGET:
        backend_replicas += 1

    scale_up = (
        avg_latency > settings.SLO_LATENCY_MS_TARGET
        or error_rate > 0.01
        or plan["tenants_over_quota"] > 0
    )
    scale_down = (
        not scale_up
        and request_count < 1_000
        and avg_latency < settings.SLO_LATENCY_MS_TARGET * 0.5
        and plan.get("slo_met", True)
    )

    hooks = [
        {
            "target": "backend",
            "metric": "http_requests_total",
            "recommended_replicas": backend_replicas,
            "min_replicas": settings.AUTOSCALE_BACKEND_REPLICAS_BASE,
            "max_replicas": settings.AUTOSCALE_BACKEND_REPLICAS_MAX,
            "scale_up": scale_up,
            "scale_down": scale_down,
        },
        {
            "target": "neo4j",
            "metric": "graph_read_latency_ms",
            "recommended_action": "enable_read_replica" if avg_latency > settings.SLO_LATENCY_MS_TARGET else "hold",
            "scale_up": avg_latency > settings.SLO_LATENCY_MS_TARGET,
            "scale_down": False,
        },
    ]

    return {
        "service": settings.OTEL_SERVICE_NAME,
        "hooks_enabled": settings.AUTOSCALE_HOOKS_ENABLED,
        "capacity": plan,
        "hooks": hooks,
        "prometheus_annotations": {
            "autoscaling.projectforge/enabled": str(settings.AUTOSCALE_HOOKS_ENABLED).lower(),
            "autoscaling.projectforge/backend-replicas": str(backend_replicas),
        },
    }
