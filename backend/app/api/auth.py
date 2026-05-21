"""Authentication HTTP routes (register, login, me)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_authenticated_user
from app.auth.roles import Role
from app.db.models import User
from app.db.repositories import (
    MembershipRepository,
    OrganizationRepository,
    UserRepository,
)
from app.db.session import fastapi_get_session
from app.security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = None
    organization_name: str | None = Field(
        default=None,
        description=(
            "Optional organization name. If omitted a personal organization "
            "is auto-created and the new user becomes its owner."
        ),
    )


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, Any]


@router.post("/register", response_model=TokenResponse)
async def register(
    payload: RegisterRequest,
    session: AsyncSession = Depends(fastapi_get_session),
) -> TokenResponse:
    users = UserRepository(session)
    existing = await users.get_by_email(payload.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists",
        )

    user = await users.create(
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
    )

    organizations = OrganizationRepository(session)
    org_name = payload.organization_name or (
        f"{payload.full_name}'s workspace"
        if payload.full_name
        else f"{payload.email.split('@')[0]}'s workspace"
    )
    organization = await organizations.create(name=org_name)

    memberships = MembershipRepository(session)
    await memberships.create(
        user_id=user.id,
        organization_id=organization.id,
        role=Role.OWNER.value,
    )
    await session.commit()

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user={
            **user.to_dict(),
            "default_organization": organization.to_dict(),
        },
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(fastapi_get_session),
) -> TokenResponse:
    users = UserRepository(session)
    user = await users.get_by_email(payload.email)
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )
    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=user.to_dict())


@router.get("/me")
async def me(
    user: User = Depends(require_authenticated_user),
    session: AsyncSession = Depends(fastapi_get_session),
) -> dict[str, Any]:
    organizations = OrganizationRepository(session)
    orgs = await organizations.list_for_user(user.id)
    return {
        "user": user.to_dict(),
        "organizations": [org.to_dict() for org in orgs],
    }
