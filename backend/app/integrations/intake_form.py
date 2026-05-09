from fastapi import APIRouter, Depends

from app.core.integrations_manager import IntegrationsManager

router = APIRouter()


def get_integrations_manager() -> IntegrationsManager:
    return IntegrationsManager()


@router.post("/intake/connections")
async def run_intake(
    data: dict, manager: IntegrationsManager = Depends(get_integrations_manager)
) -> dict:
    return await manager.connect(data["connector_type"], data["auth_data"], data.get("project_id"))
