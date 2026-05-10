"""FastAPI dependencies for authentication + RBAC."""

from __future__ import annotations

from typing import Awaitable, Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.roles import Role, role_at_least
from app.db.models import User
from app.db.repositories import (
    MembershipRepository,
    UserRepository,
)
from app.db.session import fastapi_get_session
from app.security import TokenError, decode_token


def _extract_bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not header:
        return None
    parts = header.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip()


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(fastapi_get_session),
) -> User | None:
    """Return the authenticated :class:`User` or ``None`` for anonymous calls.

    Used by routes that work for both authenticated and anonymous callers.
    """

    token = _extract_bearer_token(request)
    if not token:
        return None
    try:
        claims = decode_token(token)
    except TokenError:
        return None
    user_id = claims.get("sub")
    if not user_id:
        return None
    user_repo = UserRepository(session)
    user = await user_repo.get(user_id)
    if user is None or not user.is_active:
        return None
    return user


async def require_authenticated_user(
    user: User | None = Depends(get_current_user),
) -> User:
    """Return the authenticated :class:`User` or raise 401."""

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(
    required_role: Role,
    *,
    organization_id_param: str = "organization_id",
) -> Callable[..., Awaitable[User]]:
    """Build a dependency that enforces ``required_role`` for a path-bound org.

    The returned callable extracts the organization id from the path
    parameter named ``organization_id_param`` (default
    ``organization_id``) and verifies the current user holds at least the
    required role there. Superusers are exempt from the membership check.
    """

    async def _checker(
        request: Request,
        user: User = Depends(require_authenticated_user),
        session: AsyncSession = Depends(fastapi_get_session),
    ) -> User:
        if user.is_superuser:
            return user

        org_id = request.path_params.get(organization_id_param)
        if not org_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing path parameter '{organization_id_param}'",
            )

        memberships = MembershipRepository(session)
        membership = await memberships.get(
            user_id=user.id, organization_id=org_id
        )
        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this organization",
            )
        try:
            actual = Role(membership.role)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Invalid stored role: {membership.role}",
            ) from exc

        if not role_at_least(actual, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Role '{actual.value}' is below required '{required_role.value}'"
                ),
            )
        return user

    return _checker
