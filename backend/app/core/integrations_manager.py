from integrations.registry import ConnectorRegistry


class IntegrationsManager:
    async def get_recommended_connectors(
        self,
        project_id: str | None = None,
        compliance: str = "standard",
    ) -> list[str]:
        return ConnectorRegistry.get_recommended(compliance)

    async def connect(
        self,
        connector_type: str,
        auth_data: dict,
        project_id: str | None = None,
    ) -> dict:
        connector = ConnectorRegistry.get_connector(connector_type)
        connection = await connector.authenticate(auth_data)
        return {
            "status": "connected",
            "connector": connector_type,
            "project_id": project_id,
            "connection": connection,
        }
