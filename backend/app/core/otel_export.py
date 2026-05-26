"""OpenTelemetry-compatible export bridges for Prometheus and Jaeger."""

from __future__ import annotations

from typing import Any

from core.config import settings
from core.observability import metrics_collector, recent_traces


def otel_status() -> dict[str, Any]:
    return {
        "enabled": settings.OTEL_EXPORTER_ENABLED,
        "service_name": settings.OTEL_SERVICE_NAME,
        "exporter": settings.OTEL_EXPORTER,
        "prometheus_path": settings.OTEL_PROMETHEUS_PATH,
        "jaeger_endpoint": settings.OTEL_JAEGER_ENDPOINT,
    }


def prometheus_metrics_text() -> str:
    snapshot = metrics_collector.snapshot()
    lines = [
        "# HELP projectforge_http_requests_total Total HTTP requests handled",
        "# TYPE projectforge_http_requests_total counter",
        f'projectforge_http_requests_total{{service="{settings.OTEL_SERVICE_NAME}"}} {snapshot["request_count"]}',
        "# HELP projectforge_http_errors_total Total HTTP 5xx responses",
        "# TYPE projectforge_http_errors_total counter",
        f'projectforge_http_errors_total{{service="{settings.OTEL_SERVICE_NAME}"}} {snapshot["error_count"]}',
        "# HELP projectforge_http_request_duration_ms_avg Average request latency in milliseconds",
        "# TYPE projectforge_http_request_duration_ms_avg gauge",
        f'projectforge_http_request_duration_ms_avg{{service="{settings.OTEL_SERVICE_NAME}"}} {snapshot["average_latency_ms"]}',
    ]
    for route, count in snapshot.get("routes", {}).items():
        safe_route = route.replace('"', '\\"')
        lines.append(
            f'projectforge_http_requests_by_route{{service="{settings.OTEL_SERVICE_NAME}",route="{safe_route}"}} {count}'
        )
    for code, count in snapshot.get("status_codes", {}).items():
        lines.append(
            f'projectforge_http_responses{{service="{settings.OTEL_SERVICE_NAME}",code="{code}"}} {count}'
        )
    lines.append("")
    return "\n".join(lines)


def jaeger_trace_batch(limit: int = 50) -> dict[str, Any]:
    traces = recent_traces(limit)
    spans = []
    for index, trace in enumerate(traces):
        spans.append(
            {
                "traceID": trace["trace_id"].replace("trace_", ""),
                "spanID": f"{index:016x}",
                "operationName": f"{trace['method']} {trace['route']}",
                "references": [],
                "startTime": 0,
                "duration": int(trace["latency_ms"] * 1000),
                "tags": [
                    {"key": "http.status_code", "type": "int64", "value": trace["status_code"]},
                    {"key": "service.name", "type": "string", "value": settings.OTEL_SERVICE_NAME},
                ],
                "logs": [],
                "processID": "p1",
            }
        )
    return {
        "data": [
            {
                "traceID": spans[0]["traceID"] if spans else "0",
                "spans": spans,
                "processes": {
                    "p1": {
                        "serviceName": settings.OTEL_SERVICE_NAME,
                        "tags": [{"key": "exporter", "type": "string", "value": "projectforge-jaeger-bridge"}],
                    }
                },
            }
        ] if spans else [],
        "total": len(spans),
        "limit": limit,
        "errors": None,
    }


def otlp_trace_payload(limit: int = 50) -> dict[str, Any]:
    traces = recent_traces(limit)
    spans = []
    for trace in traces:
        spans.append(
            {
                "traceId": trace["trace_id"].replace("trace_", ""),
                "spanId": trace["trace_id"][-16:],
                "name": f"{trace['method']} {trace['route']}",
                "kind": 2,
                "attributes": [
                    {"key": "http.route", "value": {"stringValue": trace["route"]}},
                    {"key": "http.status_code", "value": {"intValue": trace["status_code"]}},
                ],
                "endTimeUnixNano": "0",
                "startTimeUnixNano": "0",
            }
        )
    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": settings.OTEL_SERVICE_NAME}},
                    ]
                },
                "scopeSpans": [{"spans": spans}],
            }
        ]
    }
