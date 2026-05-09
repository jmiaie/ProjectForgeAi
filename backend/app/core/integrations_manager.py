from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from app.compliance.enforcer import record_audit_event
from app.integrations.registry import ConnectorRegistry


class IntegrationStateStore:
    def __init__(self) -> None:
        self.oauth_sessions: dict[str, dict[str, Any]] = {}
        self.project_connections: dict[str, list[dict[str, Any]]] = {}

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(UTC).isoformat()

    def add_connection(self, project_id: str, connection: dict[str, Any]) -> None:
        connection.setdefault("connected_at", self._now_iso())
        self.project_connections.setdefault(project_id, []).append(connection)

    def get_connections(self, project_id: str) -> list[dict[str, Any]]:
        return self.project_connections.get(project_id, [])


_STATE_STORE = IntegrationStateStore()


class IntegrationsManager:
    def __init__(self, state_store: IntegrationStateStore | None = None):
        self._store = state_store or _STATE_STORE

    @staticmethod
    def _default_project(project_id: str | None) -> str:
        return project_id or "proj_123"

    @staticmethod
    def _pkce_pair() -> tuple[str, str]:
        verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).decode().rstrip("=")
        digest = hashlib.sha256(verifier.encode()).digest()
        challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
        return verifier, challenge

    @staticmethod
    def _expiry(minutes: int = 15) -> datetime:
        return datetime.now(UTC) + timedelta(minutes=minutes)

    async def get_recommended_connectors(self, project_id: str | None = None) -> dict:
        _ = self._default_project(project_id)
        connectors = ConnectorRegistry.get_recommended_with_metadata("standard")
        return {"status": "ok", "connectors": connectors}

    async def begin_oauth(self, connector_type: str, project_id: str | None, redirect_uri: str) -> dict:
        connector_kind = ConnectorRegistry.get_type(connector_type)
        if connector_kind != "oauth":
            raise ValueError(f"{connector_type} is not an OAuth connector")

        state = secrets.token_urlsafe(24)
        code_verifier, code_challenge = self._pkce_pair()
        expires_at = self._expiry()
        connector = ConnectorRegistry.get_connector(connector_type)

        resolved_project = self._default_project(project_id)
        self._store.oauth_sessions[state] = {
            "connector_type": connector_type,
            "project_id": resolved_project,
            "code_verifier": code_verifier,
            "redirect_uri": redirect_uri,
            "expires_at": expires_at,
        }

        authorize_url = connector.build_authorization_url(
            redirect_uri=redirect_uri,
            state=state,
            code_challenge=code_challenge,
        )
        record_audit_event(
            project_id=resolved_project,
            event_type="oauth_authorization_started",
            payload={"connector": connector_type},
        )
        return {
            "status": "authorization_required",
            "connector": connector_type,
            "project_id": resolved_project,
            "authorization_url": authorize_url,
            "state": state,
            "code_challenge": code_challenge,
            "expires_at": expires_at.isoformat(),
        }

    async def complete_oauth(
        self,
        connector_type: str,
        project_id: str | None,
        state: str,
        code: str,
        redirect_uri: str,
    ) -> dict:
        session = self._store.oauth_sessions.get(state)
        if not session:
            raise ValueError("Unknown or expired OAuth state")
        if session["connector_type"] != connector_type:
            raise ValueError("OAuth state connector mismatch")
        if datetime.now(UTC) > session["expires_at"]:
            self._store.oauth_sessions.pop(state, None)
            raise ValueError("OAuth state expired")

        expected_project = self._default_project(project_id)
        session_project = self._default_project(session["project_id"])
        if expected_project != session_project:
            raise ValueError("OAuth state project mismatch")

        connector = ConnectorRegistry.get_connector(connector_type)
        token = await connector.authenticate(
            {
                "code": code,
                "state": state,
                "redirect_uri": redirect_uri,
                "code_verifier": session["code_verifier"],
            }
        )
        self._store.oauth_sessions.pop(state, None)

        connection = {
            "connector": connector_type,
            "type": "oauth",
            "project_id": expected_project,
            "token": token,
            "status": "connected",
        }
        self._store.add_connection(expected_project, connection)
        record_audit_event(
            project_id=expected_project,
            event_type="integration_connected",
            payload={"connector": connector_type, "type": "oauth"},
        )
        return {"status": "connected", "connection": connection}

    async def connect_api_key(self, connector_type: str, project_id: str | None, api_key: str) -> dict:
        connector_kind = ConnectorRegistry.get_type(connector_type)
        if connector_kind != "api_key":
            raise ValueError(f"{connector_type} is not an API-key connector")

        project = self._default_project(project_id)
        connector = ConnectorRegistry.get_connector(connector_type)
        auth_result = await connector.authenticate({"api_key": api_key})
        connection = {
            "connector": connector_type,
            "type": "api_key",
            "project_id": project,
            "auth": auth_result,
            "status": "connected",
        }
        self._store.add_connection(project, connection)
        record_audit_event(
            project_id=project,
            event_type="integration_connected",
            payload={"connector": connector_type, "type": "api_key"},
        )
        return {"status": "connected", "connection": connection}

    async def connect_mcp(
        self,
        project_id: str | None,
        server_url: str,
        token: str | None = None,
        connector_type: str = "mcp_server",
    ) -> dict:
        connector_kind = ConnectorRegistry.get_type(connector_type)
        if connector_kind != "mcp":
            raise ValueError(f"{connector_type} is not an MCP connector")

        project = self._default_project(project_id)
        connector = ConnectorRegistry.get_connector(connector_type)
        auth_result = await connector.authenticate({"server_url": server_url, "token": token})
        connection = {
            "connector": connector_type,
            "type": "mcp",
            "project_id": project,
            "auth": auth_result,
            "status": "connected" if auth_result.get("mode") != "error" else "error",
        }
        self._store.add_connection(project, connection)
        record_audit_event(
            project_id=project,
            event_type="integration_connected",
            payload={
                "connector": connector_type,
                "type": "mcp",
                "status": connection["status"],
                "mode": auth_result.get("mode"),
            },
        )
        return {"status": connection["status"], "connection": connection}

    async def list_connections(self, project_id: str | None = None) -> dict:
        project = self._default_project(project_id)
        return {"status": "ok", "project_id": project, "connections": self._store.get_connections(project)}

    async def connect(
        self, connector_type: str, auth_data: dict, project_id: str | None = None
    ) -> dict:
        connector_kind = ConnectorRegistry.get_type(connector_type)
        if connector_kind == "oauth":
            return await self.complete_oauth(
                connector_type=connector_type,
                project_id=project_id,
                state=auth_data["state"],
                code=auth_data["code"],
                redirect_uri=auth_data["redirect_uri"],
            )
        if connector_kind == "api_key":
            return await self.connect_api_key(
                connector_type=connector_type,
                project_id=project_id,
                api_key=auth_data["api_key"],
            )
        if connector_kind == "mcp":
            return await self.connect_mcp(
                project_id=project_id,
                server_url=auth_data["server_url"],
                token=auth_data.get("token"),
                connector_type=connector_type,
            )
        raise ValueError(f"Unsupported connector type: {connector_kind}")
