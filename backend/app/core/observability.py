import time
import uuid
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from core.config import settings


@dataclass
class MetricsSnapshot:
    request_count: int = 0
    error_count: int = 0
    total_latency_ms: float = 0.0
    routes: dict[str, int] = field(default_factory=dict)
    status_codes: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        avg_latency = self.total_latency_ms / self.request_count if self.request_count else 0.0
        return {
            "request_count": self.request_count,
            "error_count": self.error_count,
            "average_latency_ms": round(avg_latency, 2),
            "routes": dict(sorted(self.routes.items(), key=lambda item: item[1], reverse=True)[:20]),
            "status_codes": self.status_codes,
        }


class MetricsCollector:
    def __init__(self):
        self._lock = Lock()
        self._snapshot = MetricsSnapshot()

    def record(self, *, route: str, status_code: int, latency_ms: float) -> None:
        with self._lock:
            self._snapshot.request_count += 1
            if status_code >= 500:
                self._snapshot.error_count += 1
            self._snapshot.total_latency_ms += latency_ms
            self._snapshot.routes[route] = self._snapshot.routes.get(route, 0) + 1
            key = str(status_code)
            self._snapshot.status_codes[key] = self._snapshot.status_codes.get(key, 0) + 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return self._snapshot.as_dict()


metrics_collector = MetricsCollector()
_recent_traces: list[dict[str, Any]] = []
_trace_lock = Lock()


def record_trace(*, trace_id: str, route: str, method: str, status_code: int, latency_ms: float) -> None:
    if not settings.TRACE_REQUESTS:
        return
    entry = {
        "trace_id": trace_id,
        "route": route,
        "method": method,
        "status_code": status_code,
        "latency_ms": round(latency_ms, 2),
    }
    with _trace_lock:
        _recent_traces.append(entry)
        if len(_recent_traces) > settings.TRACE_BUFFER_SIZE:
            del _recent_traces[: len(_recent_traces) - settings.TRACE_BUFFER_SIZE]


def recent_traces(limit: int = 50) -> list[dict[str, Any]]:
    with _trace_lock:
        return list(_recent_traces[-limit:])


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.OBSERVABILITY_ENABLED:
            return await call_next(request)

        trace_id = request.headers.get("X-Request-ID") or f"trace_{uuid.uuid4().hex}"
        started = time.perf_counter()
        response = await call_next(request)
        latency_ms = (time.perf_counter() - started) * 1000
        route = request.url.path
        metrics_collector.record(route=route, status_code=response.status_code, latency_ms=latency_ms)
        record_trace(
            trace_id=trace_id,
            route=route,
            method=request.method,
            status_code=response.status_code,
            latency_ms=latency_ms,
        )
        response.headers.setdefault("X-Request-ID", trace_id)
        return response


def observability_status() -> dict[str, Any]:
    return {
        "enabled": settings.OBSERVABILITY_ENABLED,
        "metrics_enabled": settings.METRICS_ENABLED,
        "trace_requests": settings.TRACE_REQUESTS,
        "trace_buffer_size": settings.TRACE_BUFFER_SIZE,
    }
