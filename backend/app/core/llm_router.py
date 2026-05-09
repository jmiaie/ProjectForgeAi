from typing import Any

from pydantic import BaseModel

from compliance.enforcer import ComplianceEnforcer
from core.config import settings


class LLMRequest(BaseModel):
    messages: list[dict[str, Any]]
    project_id: str
    model: str | None = None
    task_type: str = "general"


class LLMRouter:
    def __init__(self, compliance: ComplianceEnforcer | None = None):
        self.compliance = compliance or ComplianceEnforcer()

    async def call(self, req: LLMRequest) -> str:
        decision = self.compliance.check_action(
            req.project_id,
            "llm_call",
            payload=req.messages,
        )
        profile = decision.profile
        messages = decision.payload if decision.payload is not None else req.messages
        if profile.required_model:
            model = profile.required_model
        else:
            model = req.model or settings.DEFAULT_LLM_MODEL

        try:
            import litellm
        except ImportError as exc:
            raise RuntimeError("LiteLLM is required for LLMRouter.call") from exc

        response = await litellm.acompletion(
            model=model,
            messages=messages,
            temperature=0.3 if req.task_type == "reasoning" else 0.0,
        )
        return response.choices[0].message.content
