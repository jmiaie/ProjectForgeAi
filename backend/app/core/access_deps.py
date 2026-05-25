from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException

from core.config import settings
from core.rbac import ActorContext, RBACService


def get_rbac_service() -> RBACService:
    return RBACService()


def get_actor_context(
    x_projectforge_actor: Annotated[str | None, Header()] = None,
    x_projectforge_role: Annotated[str | None, Header()] = None,
    rbac: RBACService = Depends(get_rbac_service),
) -> ActorContext:
    return rbac.resolve_actor(x_projectforge_actor, x_projectforge_role)


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
