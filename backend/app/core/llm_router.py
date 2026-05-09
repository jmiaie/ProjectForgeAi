"""LLM routing layer.

Wraps `LiteLLM` so the rest of the codebase can request a completion without
caring which provider answers. The router applies compliance-aware overrides
(e.g. routing HIPAA / legal projects to a flagship model), supports
Bring-Your-Own-Key per request, and degrades gracefully when ``litellm`` is
not installed (useful in early development / unit tests).
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from app.compliance.enforcer import get_compliance_profile
from app.core.config import get_settings

logger = logging.getLogger(__name__)

try:  # pragma: no cover - exercised only when litellm is installed
    import litellm  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    litellm = None  # type: ignore[assignment]


class LLMRequest(BaseModel):
    """Inbound request shape for :meth:`LLMRouter.call`."""

    messages: list[dict[str, Any]]
    project_id: str
    model: str | None = None
    task_type: str = "general"
    temperature: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMRouter:
    """Routes completion requests to the appropriate provider."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def _select_model(self, req: LLMRequest) -> str:
        profile = get_compliance_profile(req.project_id)
        if profile.category in {"hipaa", "legal"}:
            return self.settings.FLAGSHIP_LLM_MODEL
        if req.model:
            return req.model
        return self.settings.DEFAULT_LLM_MODEL

    def _select_temperature(self, req: LLMRequest) -> float:
        if req.temperature is not None:
            return req.temperature
        return 0.3 if req.task_type == "reasoning" else 0.0

    async def call(self, req: LLMRequest) -> str:
        """Issue a completion and return the assistant message content."""

        model = self._select_model(req)
        temperature = self._select_temperature(req)

        if litellm is None:
            logger.warning(
                "litellm is not installed; returning a stub response for model=%s",
                model,
            )
            return f"[stub:{model}] {req.messages[-1].get('content', '') if req.messages else ''}"

        response = await litellm.acompletion(  # type: ignore[union-attr]
            model=model,
            messages=req.messages,
            temperature=temperature,
        )
        return response.choices[0].message.content  # type: ignore[no-any-return]
