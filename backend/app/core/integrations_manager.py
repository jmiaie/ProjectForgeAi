"""High-level orchestration of integration connectors."""

from __future__ import annotations

from typing import Any

from app.integrations.registry import ConnectorRegistry


class IntegrationsManager:
    """Facade used by API routes to discover and authenticate connectors."""

    async def get_recommended_connectors(
        self, project_id: str | None = None, compliance: str = "standard"
    ) -> list[dict[str, Any]]:
        return ConnectorRegistry.get_recommended(compliance)

    async def list_connectors(self) -> list[dict[str, Any]]:
        return ConnectorRegistry.list_all()

    async def connect(
        self,
        connector_type: str,
        auth_data: dict[str, Any],
        project_id: str | None = None,
    ) -> dict[str, Any]:
        connector = ConnectorRegistry.get_connector(connector_type)
        connection = await connector.authenticate(auth_data)
        return {
            "status": "connected",
            "connector": connector_type,
            "project_id": project_id,
            "connection": connection,
        }
