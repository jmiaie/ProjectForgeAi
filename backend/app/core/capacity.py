"""Automated capacity planning signals from metrics and tenant usage."""

from __future__ import annotations

from typing import Any

from core.config import settings
from core.observability import metrics_collector
from core.slo import compute_slo_status
from tenancy.billing import TenantBillingService
from tenancy.registry import TenantRegistry


def compute_capacity_plan() -> dict[str, Any]:
    metrics = metrics_collector.snapshot()
    slo = compute_slo_status()
    request_count = int(metrics.get("request_count", 0))
    error_count = int(metrics.get("error_count", 0))
    avg_latency = float(metrics.get("average_latency_ms", 0.0))

    registry = TenantRegistry()
    tenants = registry.list_tenants()
    billing = TenantBillingService()
    total_llm_tokens = 0
    tenants_over_quota = 0
    for tenant in tenants:
        try:
            status = billing.quota_status(tenant.tenant_id)
            total_llm_tokens += int(status["usage"].get("llm_tokens", 0))
            if not all(check["allowed"] for check in status["checks"].values()):
                tenants_over_quota += 1
        except ValueError:
            continue

    recommendations: list[dict[str, str]] = []
    if avg_latency > settings.SLO_LATENCY_MS_TARGET:
        recommendations.append(
            {
                "severity": "warning",
                "area": "backend",
                "action": "Scale backend replicas or enable Neo4j read replicas for graph-heavy tenants.",
            }
        )
    if error_count > 0 and request_count > 0 and (error_count / request_count) > 0.01:
        recommendations.append(
            {
                "severity": "critical",
                "area": "reliability",
                "action": "Investigate elevated 5xx rate; review SLO dashboard and on-call runbook.",
            }
        )
    if tenants_over_quota > 0:
        recommendations.append(
            {
                "severity": "info",
                "area": "billing",
                "action": f"{tenants_over_quota} tenant(s) over quota — review overage metering and invoice line items.",
            }
        )
    if request_count > 50_000:
        recommendations.append(
            {
                "severity": "info",
                "area": "capacity",
                "action": "High request volume — validate Prometheus scrape interval and cluster failover health.",
            }
        )
    if not recommendations:
        recommendations.append(
            {
                "severity": "ok",
                "area": "capacity",
                "action": "Capacity within targets; continue monitoring SLO and tenant usage trends.",
            }
        )

    return {
        "service": settings.OTEL_SERVICE_NAME,
        "metrics": {
            "request_count": request_count,
            "error_count": error_count,
            "average_latency_ms": avg_latency,
        },
        "slo_met": slo.get("overall_met", True),
        "tenant_count": len(tenants),
        "total_llm_tokens": total_llm_tokens,
        "tenants_over_quota": tenants_over_quota,
        "recommendations": recommendations,
    }
