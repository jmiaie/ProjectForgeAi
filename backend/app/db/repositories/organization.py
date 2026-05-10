"""Organization + membership repositories."""

from __future__ import annotations

import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Membership, Organization


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(name: str) -> str:
    base = _SLUG_RE.sub("-", name.lower()).strip("-") or "org"
    return f"{base}-{uuid.uuid4().hex[:6]}"


class OrganizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, name: str, slug: str | None = None) -> Organization:
        organization = Organization(
            id=f"org_{uuid.uuid4().hex[:16]}",
            name=name,
            slug=(slug or _slugify(name)).lower(),
        )
        self.session.add(organization)
        await self.session.flush()
        return organization

    async def get(self, organization_id: str) -> Organization | None:
        return await self.session.get(Organization, organization_id)

    async def get_by_slug(self, slug: str) -> Organization | None:
        stmt = select(Organization).where(Organization.slug == slug.lower())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: str) -> list[Organization]:
        stmt = (
            select(Organization)
            .join(Membership, Membership.organization_id == Organization.id)
            .where(Membership.user_id == user_id)
            .order_by(Organization.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class MembershipRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        user_id: str,
        organization_id: str,
        role: str = "member",
    ) -> Membership:
        existing = await self.get(user_id=user_id, organization_id=organization_id)
        if existing is not None:
            existing.role = role
            await self.session.flush()
            return existing
        membership = Membership(
            id=f"mem_{uuid.uuid4().hex[:16]}",
            user_id=user_id,
            organization_id=organization_id,
            role=role,
        )
        self.session.add(membership)
        await self.session.flush()
        return membership

    async def get(
        self, *, user_id: str, organization_id: str
    ) -> Membership | None:
        stmt = select(Membership).where(
            Membership.user_id == user_id,
            Membership.organization_id == organization_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_organization(
        self, organization_id: str
    ) -> list[Membership]:
        stmt = (
            select(Membership)
            .where(Membership.organization_id == organization_id)
            .order_by(Membership.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def remove(self, membership: Membership) -> None:
        await self.session.delete(membership)
        await self.session.flush()
