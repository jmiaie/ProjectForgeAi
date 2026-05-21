"""Organization + membership HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    require_authenticated_user,
    require_role,
)
from app.auth.roles import Role
from app.db.models import User
from app.db.repositories import (
    MembershipRepository,
    OrganizationRepository,
    UserRepository,
)
from app.db.session import fastapi_get_session

router = APIRouter(prefix="/orgs", tags=["organizations"])


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str | None = None


class MembershipCreate(BaseModel):
    email: EmailStr
    role: Role = Role.MEMBER


@router.post("/")
async def create_organization(
    payload: OrganizationCreate,
    user: User = Depends(require_authenticated_user),
    session: AsyncSession = Depends(fastapi_get_session),
) -> dict[str, Any]:
    organizations = OrganizationRepository(session)
    if payload.slug:
        existing = await organizations.get_by_slug(payload.slug)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Slug is already in use",
            )

    organization = await organizations.create(name=payload.name, slug=payload.slug)
    memberships = MembershipRepository(session)
    await memberships.create(
        user_id=user.id,
        organization_id=organization.id,
        role=Role.OWNER.value,
    )
    await session.commit()
    return organization.to_dict()


@router.get("/")
async def list_my_organizations(
    user: User = Depends(require_authenticated_user),
    session: AsyncSession = Depends(fastapi_get_session),
) -> dict[str, Any]:
    organizations = OrganizationRepository(session)
    rows = await organizations.list_for_user(user.id)
    return {"items": [row.to_dict() for row in rows]}


@router.get("/{organization_id}")
async def get_organization(
    organization_id: str,
    _: User = Depends(require_role(Role.VIEWER)),
    session: AsyncSession = Depends(fastapi_get_session),
) -> dict[str, Any]:
    organizations = OrganizationRepository(session)
    org = await organizations.get(organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org.to_dict()


@router.get("/{organization_id}/members")
async def list_members(
    organization_id: str,
    _: User = Depends(require_role(Role.VIEWER)),
    session: AsyncSession = Depends(fastapi_get_session),
) -> dict[str, Any]:
    memberships = MembershipRepository(session)
    rows = await memberships.list_for_organization(organization_id)
    return {"items": [row.to_dict() for row in rows]}


@router.post("/{organization_id}/members")
async def add_member(
    organization_id: str,
    payload: MembershipCreate,
    _: User = Depends(require_role(Role.ADMIN)),
    session: AsyncSession = Depends(fastapi_get_session),
) -> dict[str, Any]:
    users = UserRepository(session)
    target = await users.get_by_email(payload.email)
    if target is None:
        raise HTTPException(
            status_code=404, detail="No user with that email exists"
        )
    memberships = MembershipRepository(session)
    membership = await memberships.create(
        user_id=target.id,
        organization_id=organization_id,
        role=payload.role.value,
    )
    await session.commit()
    return membership.to_dict()


@router.delete("/{organization_id}/members/{user_id}")
async def remove_member(
    organization_id: str,
    user_id: str,
    _: User = Depends(require_role(Role.ADMIN)),
    session: AsyncSession = Depends(fastapi_get_session),
) -> dict[str, Any]:
    memberships = MembershipRepository(session)
    membership = await memberships.get(
        user_id=user_id, organization_id=organization_id
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="Membership not found")
    await memberships.remove(membership)
    await session.commit()
    return {"status": "removed", "user_id": user_id}
