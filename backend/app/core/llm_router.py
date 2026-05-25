from typing import Any

from pydantic import BaseModel

from compliance.enforcer import ComplianceEnforcer
from core.config import settings
from core.llm_keys import LLMKeyStore
from core.llm_routing import select_model
from core.usage_meter import LLMUsageMeter


class LLMRequest(BaseModel):
    messages: list[dict[str, Any]]
    project_id: str
    model: str | None = None
    task_type: str = "general"
    use_flagship: bool = False


class LLMResponse(BaseModel):
    content: str
    model: str
    routing_tier: str
    routing_reason: str
    used_byo_key: bool
    usage: dict[str, Any]


class LLMRouter:
    def __init__(
        self,
        compliance: ComplianceEnforcer | None = None,
        key_store: LLMKeyStore | None = None,
        usage_meter: LLMUsageMeter | None = None,
    ):
        self.compliance = compliance or ComplianceEnforcer()
        self.key_store = key_store or LLMKeyStore()
        self.usage_meter = usage_meter or LLMUsageMeter()

    async def call(self, req: LLMRequest) -> str:
        result = await self.call_with_metadata(req)
        return result.content

    async def call_with_metadata(self, req: LLMRequest) -> LLMResponse:
        decision = self.compliance.check_action(
            req.project_id,
            "llm_call",
            payload=req.messages,
        )
        profile = decision.profile
        messages = decision.payload if decision.payload is not None else req.messages

        routing = select_model(
            project_id=req.project_id,
            requested_model=req.model,
            task_type=req.task_type,
            use_flagship=req.use_flagship,
            compliance_required_model=profile.required_model,
        )
        model = routing.model

        api_key = self.key_store.resolve_api_key(req.project_id, model)
        completion_kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": 0.3 if req.task_type == "reasoning" else 0.0,
        }
        if api_key:
            completion_kwargs["api_key"] = api_key

        try:
            import litellm
        except ImportError as exc:
            raise RuntimeError("LiteLLM is required for LLMRouter.call") from exc

        response = await litellm.acompletion(**completion_kwargs)
        content = response.choices[0].message.content

        usage = getattr(response, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0) if usage else 0
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0) if usage else 0

        usage_event = self.usage_meter.record(
            project_id=req.project_id,
            model=model,
            task_type=req.task_type,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            routing_tier=routing.routing_tier,
            used_byo_key=bool(api_key),
        )

        return LLMResponse(
            content=content,
            model=model,
            routing_tier=routing.routing_tier,
            routing_reason=routing.reason,
            used_byo_key=bool(api_key),
            usage=usage_event,
        )
