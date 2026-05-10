"""Authentication / RBAC primitives."""

from app.auth.dependencies import (
    get_current_user,
    require_authenticated_user,
    require_role,
)
from app.auth.roles import ROLE_HIERARCHY, Role, role_at_least

__all__ = [
    "ROLE_HIERARCHY",
    "Role",
    "get_current_user",
    "require_authenticated_user",
    "require_role",
    "role_at_least",
]
