"""Role enum + hierarchy used for RBAC checks."""

from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


ROLE_HIERARCHY: dict[Role, int] = {
    Role.VIEWER: 1,
    Role.MEMBER: 2,
    Role.ADMIN: 3,
    Role.OWNER: 4,
}


def role_at_least(actual: Role, required: Role) -> bool:
    """Return True when ``actual`` >= ``required`` in the hierarchy."""

    return ROLE_HIERARCHY[actual] >= ROLE_HIERARCHY[required]
