from pydantic import BaseModel


class OrchestratorRequest(BaseModel):
    project_id: str
    goal: str


class OrchestratorAgent:
    async def run(self, request: OrchestratorRequest) -> dict:
        return {
            "project_id": request.project_id,
            "goal": request.goal,
            "status": "planned",
            "next_action": "Run ingestion and build project graph",
        }
