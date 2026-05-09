from typing import Any

from pydantic import BaseModel

from compliance.enforcer import get_compliance_profile
from core.config import settings


class LLMRequest(BaseModel):
    messages: list[dict[str, Any]]
    project_id: str
    model: str | None = None
    task_type: str = "general"


class LLMRouter:
    async def call(self, req: LLMRequest) -> str:
        profile = get_compliance_profile(req.project_id)
        if profile.category in {"hipaa", "legal"}:
            model = "anthropic/claude-3-5-sonnet-20241022"
        else:
            model = req.model or settings.DEFAULT_LLM_MODEL

        try:
            import litellm
        except ImportError as exc:
            raise RuntimeError("LiteLLM is required for LLMRouter.call") from exc

        response = await litellm.acompletion(
            model=model,
            messages=req.messages,
            temperature=0.3 if req.task_type == "reasoning" else 0.0,
        )
        return response.choices[0].message.content
