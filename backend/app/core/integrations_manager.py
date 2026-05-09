from compliance.enforcer import ComplianceEnforcer
from integrations.connection_store import ConnectionStore
from integrations.registry import ConnectorRegistry


class IntegrationsManager:
    def __init__(
        self,
        compliance: ComplianceEnforcer | None = None,
        connection_store: ConnectionStore | None = None,
    ):
        self.compliance = compliance or ComplianceEnforcer()
        self.connection_store = connection_store or ConnectionStore()

    async def get_recommended_connectors(
        self,
        project_id: str | None = None,
        compliance: str = "standard",
    ) -> list[str]:
        return ConnectorRegistry.get_recommended(compliance)

    async def start_oauth(
        self,
        connector_type: str,
        project_id: str | None = None,
        redirect_uri: str | None = None,
    ) -> dict:
        connector = ConnectorRegistry.get_connector(connector_type)
        start = getattr(connector, "start", None)
        if start is None:
            raise ValueError(f"{connector_type} does not support OAuth start")
        return start(project_id=project_id, redirect_uri=redirect_uri)

    async def connect(
        self,
        connector_type: str,
        auth_data: dict,
        project_id: str | None = None,
    ) -> dict:
        if project_id:
            decision = self.compliance.check_action(
                project_id,
                "external_write",
                payload={"connector_type": connector_type},
            )
            if not decision.allowed:
                raise PermissionError(decision.reason)
        connector = ConnectorRegistry.get_connector(connector_type)
        connection = await connector.authenticate(auth_data)
        stored = (
            self.connection_store.upsert(
                project_id=project_id,
                connector_type=connector_type,
                connection=connection,
            )
            if project_id
            else {"summary": _safe_connection_summary(connection)}
        )
        return {
            "status": "connected",
            "connector": connector_type,
            "project_id": project_id,
            "connection": stored,
        }

    async def list_connections(self, project_id: str) -> dict:
        return {"project_id": project_id, "connections": self.connection_store.list(project_id)}

    async def connection_status(self, project_id: str, connector_type: str) -> dict:
        connection = self.connection_store.get(project_id, connector_type)
        if connection is None:
            return {
                "project_id": project_id,
                "connector": connector_type,
                "status": "not_connected",
            }
        return {"project_id": project_id, "connector": connector_type, **connection}

    async def health_check(self, project_id: str, connector_type: str) -> dict:
        connector = ConnectorRegistry.get_connector(connector_type)
        secret = self.connection_store.load_secret(project_id, connector_type)
        health = getattr(connector, "health", None)
        if health is None:
            return {"project_id": project_id, "connector": connector_type, "status": "unknown"}
        return {"project_id": project_id, **await health(secret)}

    async def discover_mcp_tools(self, project_id: str, connector_type: str = "mcp_server") -> dict:
        connector = ConnectorRegistry.get_connector(connector_type)
        secret = self.connection_store.load_secret(project_id, connector_type)
        discover = getattr(connector, "discover_tools", None)
        if discover is None:
            raise ValueError(f"{connector_type} does not support MCP tool discovery")
        return {"project_id": project_id, **await discover(secret)}


def _safe_connection_summary(connection: dict) -> dict:
    return {
        key: value
        for key, value in connection.items()
        if key.lower() not in {"token", "access_token", "refresh_token", "api_key", "client_secret", "client"}
    }
