class Orchestrator:
    async def run(self, project_id: str) -> dict:
        # LangGraph workflow wiring lands in the next phase.
        return {"project_id": project_id, "status": "queued"}
