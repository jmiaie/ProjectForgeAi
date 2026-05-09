from typing import Any

import litellm
from pydantic import BaseModel

from app.compliance.enforcer import record_audit_event, resolve_model_for_profile
from app.core.config import Settings


class LLMRequest(BaseModel):
    messages: list[dict[str, Any]]
    model: str | None = None
    project_id: str
    task_type: str = "general"


class LLMRouter:
    async def call(self, req: LLMRequest) -> str:
        profile, model = resolve_model_for_profile(
            project_id=req.project_id,
            requested_model=req.model,
            fallback_default_model=Settings().DEFAULT_LLM_MODEL,
        )
        record_audit_event(
            project_id=req.project_id,
            event_type="llm_request_routed",
            payload={"model": model, "compliance": profile.category, "task_type": req.task_type},
        )

        response = await litellm.acompletion(
            model=model,
            messages=req.messages,
            temperature=0.3 if req.task_type == "reasoning" else 0.0,
        )
        content = response.choices[0].message.content or ""
        record_audit_event(
            project_id=req.project_id,
            event_type="llm_response_received",
            payload={"model": model, "response_chars": len(content)},
        )
        return content
