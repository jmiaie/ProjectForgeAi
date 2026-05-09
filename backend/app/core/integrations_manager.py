from compliance.enforcer import ComplianceEnforcer
from integrations.registry import ConnectorRegistry


class IntegrationsManager:
    def __init__(self, compliance: ComplianceEnforcer | None = None):
        self.compliance = compliance or ComplianceEnforcer()

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
        return {
            "status": "connected",
            "connector": connector_type,
            "project_id": project_id,
            "connection": connection,
        }
