from typing import Any

import litellm
from pydantic import BaseModel

from app.compliance.enforcer import get_compliance_profile
from app.core.config import Settings


class LLMRequest(BaseModel):
    messages: list[dict[str, Any]]
    model: str | None = None
    project_id: str
    task_type: str = "general"


class LLMRouter:
    async def call(self, req: LLMRequest) -> str:
        profile = get_compliance_profile(req.project_id)
        if profile.category in {"hipaa", "legal"}:
            model = "anthropic/claude-3-5-sonnet-20241022"
        elif req.model:
            model = req.model
        else:
            model = Settings().DEFAULT_LLM_MODEL

        response = await litellm.acompletion(
            model=model,
            messages=req.messages,
            temperature=0.3 if req.task_type == "reasoning" else 0.0,
        )
        return response.choices[0].message.content or ""
