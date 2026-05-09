from app.integrations.registry import ConnectorRegistry


class IntegrationsManager:
    async def get_recommended_connectors(self, project_id: str | None = None) -> list[str]:
        return ConnectorRegistry.get_recommended("standard")

    async def connect(
        self, connector_type: str, auth_data: dict, project_id: str | None = None
    ) -> dict:
        connector = ConnectorRegistry.get_connector(connector_type)
        await connector.authenticate(auth_data)
        return {"status": "connected", "connector": connector_type, "project_id": project_id}
