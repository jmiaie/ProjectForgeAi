"""SLO status derived from in-process metrics."""

from __future__ import annotations

from typing import Any

from core.config import settings
from core.observability import metrics_collector


def slo_targets() -> dict[str, float]:
    return {
        "availability_ratio": settings.SLO_AVAILABILITY_TARGET,
        "latency_ms_avg": settings.SLO_LATENCY_MS_TARGET,
    }


def compute_slo_status() -> dict[str, Any]:
    targets = slo_targets()
    snapshot = metrics_collector.snapshot()
    request_count = int(snapshot.get("request_count", 0))
    error_count = int(snapshot.get("error_count", 0))
    avg_latency = float(snapshot.get("average_latency_ms", 0.0))

    if request_count == 0:
        availability = 1.0
        error_rate = 0.0
    else:
        error_rate = error_count / request_count
        availability = 1.0 - error_rate

    allowed_error_rate = 1.0 - targets["availability_ratio"]
    if allowed_error_rate <= 0:
        error_budget_remaining = 1.0
    else:
        error_budget_remaining = max(0.0, 1.0 - (error_rate / allowed_error_rate))

    latency_slo_met = avg_latency <= targets["latency_ms_avg"]
    availability_slo_met = availability >= targets["availability_ratio"]

    return {
        "service": settings.OTEL_SERVICE_NAME,
        "targets": targets,
        "snapshot": {
            "request_count": request_count,
            "error_count": error_count,
            "average_latency_ms": avg_latency,
            "error_rate": round(error_rate, 6),
            "availability_ratio": round(availability, 6),
        },
        "slos": {
            "availability": {
                "target": targets["availability_ratio"],
                "current": round(availability, 6),
                "met": availability_slo_met,
            },
            "latency_avg_ms": {
                "target": targets["latency_ms_avg"],
                "current": round(avg_latency, 2),
                "met": latency_slo_met,
            },
        },
        "error_budget": {
            "allowed_error_rate": allowed_error_rate,
            "remaining_ratio": round(error_budget_remaining, 4),
            "burning": error_budget_remaining < 0.5,
            "exhausted": error_budget_remaining <= 0.0 and request_count > 0,
        },
        "overall_met": availability_slo_met and latency_slo_met,
    }
