from typing import Annotated

from fastapi import Depends, Header, HTTPException

from auth.session import AuthSessionStore
from core.config import settings
from core.rbac import ActorContext, RBACService


def get_rbac_service() -> RBACService:
    return RBACService()


def get_session_store() -> AuthSessionStore:
    return AuthSessionStore()


def get_actor_context(
    authorization: Annotated[str | None, Header()] = None,
    x_projectforge_actor: Annotated[str | None, Header()] = None,
    x_projectforge_role: Annotated[str | None, Header()] = None,
    rbac: RBACService = Depends(get_rbac_service),
    session_store: AuthSessionStore = Depends(get_session_store),
) -> ActorContext:
    token = _extract_bearer(authorization)
    if token:
        session = session_store.get(token)
        if session:
            return ActorContext(actor_id=session["actor_id"], role=session.get("role", settings.OIDC_DEFAULT_ROLE))
    return rbac.resolve_actor(x_projectforge_actor, x_projectforge_role)


def _extract_bearer(authorization: str | None) -> str | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization[7:].strip() or None


def require_permission(action: str):
    async def _dependency(
        project_id: str,
        actor: ActorContext = Depends(get_actor_context),
        rbac: RBACService = Depends(get_rbac_service),
    ) -> ActorContext:
        decision = rbac.check(project_id, actor, action)
        if not decision.allowed:
            raise HTTPException(status_code=403, detail=decision.reason)
        return actor

    return _dependency
