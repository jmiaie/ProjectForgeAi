"""Tests for auth, RBAC, and the project DELETE policy."""

from __future__ import annotations

import io
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.auth.roles import ROLE_HIERARCHY, Role, role_at_least
from app.main import app
from app.security import (
    TokenError,
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
def test_password_hash_and_verify_round_trip() -> None:
    hashed = hash_password("hunter2-very-strong")
    assert hashed != "hunter2-very-strong"
    assert verify_password("hunter2-very-strong", hashed) is True
    assert verify_password("not-the-password", hashed) is False


def test_verify_password_handles_blank_hash() -> None:
    assert verify_password("anything", "") is False


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
def test_jwt_round_trip_carries_subject_and_extra_claims() -> None:
    token = create_access_token("user_abc", extra_claims={"role": "owner"})
    claims = decode_token(token)
    assert claims["sub"] == "user_abc"
    assert claims["role"] == "owner"


def test_decode_token_rejects_garbage() -> None:
    with pytest.raises(TokenError):
        decode_token("not.a.token")


# ---------------------------------------------------------------------------
# Role hierarchy
# ---------------------------------------------------------------------------
def test_role_hierarchy_orders_roles_correctly() -> None:
    assert role_at_least(Role.OWNER, Role.ADMIN)
    assert role_at_least(Role.ADMIN, Role.MEMBER)
    assert role_at_least(Role.MEMBER, Role.VIEWER)
    assert role_at_least(Role.VIEWER, Role.VIEWER)
    assert role_at_least(Role.MEMBER, Role.ADMIN) is False
    assert role_at_least(Role.VIEWER, Role.MEMBER) is False
    assert ROLE_HIERARCHY[Role.OWNER] > ROLE_HIERARCHY[Role.VIEWER]


# ---------------------------------------------------------------------------
# Helpers for HTTP tests
# ---------------------------------------------------------------------------
def _register(
    client: TestClient,
    email: str,
    password: str = "supersecret123",
    full_name: str | None = None,
    organization_name: str | None = None,
) -> dict[str, Any]:
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": full_name,
            "organization_name": organization_name,
        },
    )
    assert res.status_code == 200, res.text
    return res.json()


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Register / login / me
# ---------------------------------------------------------------------------
def test_register_creates_user_and_personal_org() -> None:
    client = TestClient(app)
    body = _register(client, "alice@example.com", full_name="Alice Example")
    assert body["access_token"]
    assert body["user"]["email"] == "alice@example.com"
    assert body["user"]["default_organization"]["name"] == "Alice Example's workspace"


def test_register_rejects_duplicate_email() -> None:
    client = TestClient(app)
    _register(client, "bob@example.com")
    res = client.post(
        "/api/v1/auth/register",
        json={"email": "bob@example.com", "password": "anotherpass1"},
    )
    assert res.status_code == 409


def test_login_succeeds_with_correct_credentials_and_fails_otherwise() -> None:
    client = TestClient(app)
    _register(client, "carol@example.com", password="carolpass1234")

    res = client.post(
        "/api/v1/auth/login",
        json={"email": "carol@example.com", "password": "carolpass1234"},
    )
    assert res.status_code == 200
    token = res.json()["access_token"]
    assert token

    res = client.post(
        "/api/v1/auth/login",
        json={"email": "carol@example.com", "password": "wrong"},
    )
    assert res.status_code == 401


def test_me_endpoint_requires_token_and_returns_user_with_orgs() -> None:
    client = TestClient(app)
    body = _register(client, "dave@example.com")
    token = body["access_token"]

    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401

    res = client.get("/api/v1/auth/me", headers=_auth_headers(token))
    assert res.status_code == 200
    payload = res.json()
    assert payload["user"]["email"] == "dave@example.com"
    assert len(payload["organizations"]) >= 1


# ---------------------------------------------------------------------------
# Organisations + membership + RBAC
# ---------------------------------------------------------------------------
def test_create_and_list_my_organizations() -> None:
    client = TestClient(app)
    body = _register(client, "eve@example.com")
    token = body["access_token"]
    headers = _auth_headers(token)

    res = client.post(
        "/api/v1/orgs/", json={"name": "Eve Industries"}, headers=headers
    )
    assert res.status_code == 200, res.text
    org = res.json()
    assert org["name"] == "Eve Industries"

    res = client.get("/api/v1/orgs/", headers=headers)
    assert res.status_code == 200
    names = {o["name"] for o in res.json()["items"]}
    assert "Eve Industries" in names


def test_membership_add_and_role_enforcement() -> None:
    client = TestClient(app)
    owner = _register(client, "owner@example.com", full_name="Owner")
    owner_token = owner["access_token"]
    org_id = owner["user"]["default_organization"]["id"]

    invitee = _register(client, "invitee@example.com")
    invitee_token = invitee["access_token"]

    # Invitee is not yet a member -> listing members should 403.
    res = client.get(
        f"/api/v1/orgs/{org_id}/members",
        headers=_auth_headers(invitee_token),
    )
    assert res.status_code == 403

    # Owner adds invitee as a viewer.
    res = client.post(
        f"/api/v1/orgs/{org_id}/members",
        json={"email": "invitee@example.com", "role": "viewer"},
        headers=_auth_headers(owner_token),
    )
    assert res.status_code == 200
    assert res.json()["role"] == "viewer"

    # Viewer can list members but cannot add new ones (admin+ required).
    res = client.get(
        f"/api/v1/orgs/{org_id}/members",
        headers=_auth_headers(invitee_token),
    )
    assert res.status_code == 200

    res = client.post(
        f"/api/v1/orgs/{org_id}/members",
        json={"email": "owner@example.com", "role": "viewer"},
        headers=_auth_headers(invitee_token),
    )
    assert res.status_code == 403


def test_add_member_with_unknown_email_is_404() -> None:
    client = TestClient(app)
    owner = _register(client, "frank@example.com")
    org_id = owner["user"]["default_organization"]["id"]
    res = client.post(
        f"/api/v1/orgs/{org_id}/members",
        json={"email": "ghost@example.com"},
        headers=_auth_headers(owner["access_token"]),
    )
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# Project DELETE RBAC
# ---------------------------------------------------------------------------
SAMPLE_EMAIL = b"""From: a@b.com
To: c@d.com
Subject: t
Date: Wed, 01 Jan 2025 09:00:00 +0000
Content-Type: text/plain

Hi.
"""


def _create_project(
    client: TestClient,
    headers: dict[str, str] | None = None,
    organization_id: str | None = None,
) -> dict[str, Any]:
    files = [("files", ("kickoff.eml", io.BytesIO(SAMPLE_EMAIL), "message/rfc822"))]
    data: dict[str, str] = {"name": "RBAC Demo", "compliance": "standard"}
    if organization_id:
        data["organization_id"] = organization_id
    res = client.post(
        "/api/v1/projects/",
        files=files,
        data=data,
        headers=headers or {},
    )
    assert res.status_code == 200, res.text
    return res.json()


def test_authenticated_project_creation_binds_org_and_creator() -> None:
    client = TestClient(app)
    body = _register(client, "gina@example.com")
    token = body["access_token"]
    org_id = body["user"]["default_organization"]["id"]

    project = _create_project(client, headers=_auth_headers(token))
    project_id = project["project_id"]

    res = client.get(f"/api/v1/projects/{project_id}")
    assert res.status_code == 200
    fetched = res.json()
    assert fetched["organization_id"] == org_id
    assert fetched["created_by_user_id"]


def test_delete_project_requires_admin_role_in_org() -> None:
    client = TestClient(app)
    owner = _register(client, "harry@example.com")
    owner_token = owner["access_token"]
    org_id = owner["user"]["default_organization"]["id"]

    # Owner creates the project bound to their org.
    project = _create_project(client, headers=_auth_headers(owner_token))
    project_id = project["project_id"]

    # Add a viewer-only second user.
    viewer = _register(client, "viewer@example.com")
    client.post(
        f"/api/v1/orgs/{org_id}/members",
        json={"email": "viewer@example.com", "role": "viewer"},
        headers=_auth_headers(owner_token),
    )

    # Anonymous DELETE -> 401.
    res = client.delete(f"/api/v1/projects/{project_id}")
    assert res.status_code == 401

    # Viewer DELETE -> 403.
    res = client.delete(
        f"/api/v1/projects/{project_id}",
        headers=_auth_headers(viewer["access_token"]),
    )
    assert res.status_code == 403

    # Owner DELETE -> 200.
    res = client.delete(
        f"/api/v1/projects/{project_id}",
        headers=_auth_headers(owner_token),
    )
    assert res.status_code == 200
    assert res.json()["status"] == "deleted"

    # Project really gone.
    res = client.get(f"/api/v1/projects/{project_id}")
    assert res.status_code == 404


def test_anonymous_project_creation_still_works_without_org_binding() -> None:
    """Regression: legacy / dev path should continue to function."""

    client = TestClient(app)
    project = _create_project(client)
    res = client.get(f"/api/v1/projects/{project['project_id']}")
    assert res.status_code == 200
    fetched = res.json()
    assert fetched["organization_id"] is None
    assert fetched["created_by_user_id"] is None
