from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from core.config import settings


SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "X-XSS-Protection": "0",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        if settings.SECURITY_HEADERS_ENABLED or settings.PRODUCTION_HARDENING:
            for header, value in SECURITY_HEADERS.items():
                response.headers.setdefault(header, value)
            if settings.STRICT_TRANSPORT_SECURITY or settings.PRODUCTION_HARDENING:
                response.headers.setdefault(
                    "Strict-Transport-Security",
                    "max-age=31536000; includeSubDomains",
                )
        return response


def cors_allowed_origins() -> list[str]:
    if settings.CORS_ALLOWED_ORIGINS.strip():
        return [origin.strip() for origin in settings.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]
    if settings.PRODUCTION_HARDENING or settings.DEPLOYMENT_MODE == "onprem":
        frontend = settings.FRONTEND_BASE_URL.rstrip("/")
        backend = settings.BACKEND_BASE_URL.rstrip("/")
        return list({frontend, backend})
    return ["*"]
