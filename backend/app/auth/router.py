from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from auth.oidc_provider import OIDCProvider
from auth.session import AuthSessionStore
from core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


class MockLoginRequest(BaseModel):
    actor_id: str = "sso-user"
    email: str | None = "sso-user@example.com"
    role: str = "editor"
    groups: list[str] = Field(default_factory=list)


class LogoutRequest(BaseModel):
    token: str | None = None


def get_session_store() -> AuthSessionStore:
    return AuthSessionStore()


def get_oidc_provider() -> OIDCProvider:
    return OIDCProvider()


def _session_response(session: dict) -> dict:
    return {
        "token": session["token"],
        "actor_id": session["actor_id"],
        "email": session.get("email"),
        "role": session.get("role"),
        "groups": session.get("groups", []),
        "provider": session.get("provider"),
        "expires_at": session.get("expires_at"),
    }


@router.get("/status")
async def auth_status(provider: OIDCProvider = Depends(get_oidc_provider)):
    store = AuthSessionStore()
    status = provider.status()
    status["active_sessions"] = store.count_active()
    return status


@router.get("/login")
async def auth_login(
    redirect_after: str | None = Query(default=None),
    provider: OIDCProvider = Depends(get_oidc_provider),
):
    if not provider.enabled:
        raise HTTPException(status_code=404, detail="OIDC authentication is disabled")
    try:
        return provider.start_login(redirect_after=redirect_after)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/callback")
async def auth_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    provider: OIDCProvider = Depends(get_oidc_provider),
    store: AuthSessionStore = Depends(get_session_store),
):
    if not provider.enabled:
        raise HTTPException(status_code=404, detail="OIDC authentication is disabled")
    if provider.mock_mode:
        raise HTTPException(status_code=400, detail="Use mock-login in development mode")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    try:
        identity = await provider.exchange_code(code, state)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"OIDC callback failed: {exc}") from exc

    session = store.create(
        actor_id=identity["actor_id"],
        email=identity.get("email"),
        role=identity.get("role", settings.OIDC_DEFAULT_ROLE),
        groups=identity.get("groups"),
        provider="oidc",
        metadata={"userinfo": identity.get("userinfo", {})},
    )
    redirect_target = identity.get("redirect_after") or settings.FRONTEND_BASE_URL
    return RedirectResponse(
        url=f"{redirect_target.rstrip('/')}/login?token={session['token']}",
        status_code=302,
    )


@router.post("/mock-login")
async def mock_login(
    request: MockLoginRequest,
    provider: OIDCProvider = Depends(get_oidc_provider),
    store: AuthSessionStore = Depends(get_session_store),
):
    if not provider.enabled or not provider.mock_mode:
        raise HTTPException(status_code=404, detail="Mock SSO login is unavailable")
    role = provider.resolve_role(request.groups) if request.groups else request.role
    session = store.create(
        actor_id=request.actor_id,
        email=request.email,
        role=role,
        groups=request.groups,
        provider="mock",
    )
    return _session_response(session)


@router.get("/me")
async def auth_me(
    authorization: Annotated[str | None, Header()] = None,
    store: AuthSessionStore = Depends(get_session_store),
):
    token = _extract_bearer(authorization)
    session = store.get(token)
    if not session:
        raise HTTPException(status_code=401, detail="No active session")
    return _session_response(session)


@router.post("/logout")
async def auth_logout(
    request: LogoutRequest | None = None,
    authorization: Annotated[str | None, Header()] = None,
    store: AuthSessionStore = Depends(get_session_store),
):
    token = (request.token if request else None) or _extract_bearer(authorization)
    if not token:
        raise HTTPException(status_code=400, detail="Session token required")
    revoked = store.revoke(token)
    return {"revoked": revoked}


def _extract_bearer(authorization: str | None) -> str | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization[7:].strip() or None
