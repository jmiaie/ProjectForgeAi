"""Base class for specialist agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.agents.state import OrchestratorState, SpecialistOutput
from app.core.llm_router import LLMRequest, LLMRouter


class SpecialistAgent(ABC):
    """Abstract specialist that produces a single structured artefact."""

    name: str = "specialist"

    def __init__(self, llm_router: LLMRouter | None = None) -> None:
        self.llm_router = llm_router or LLMRouter()

    @abstractmethod
    def system_prompt(self, state: OrchestratorState) -> str:
        """Return the system prompt seeded into the LLM call."""

    def user_prompt(self, state: OrchestratorState) -> str:
        """Return the user-turn prompt sent to the LLM.

        Subclasses can override to inject specialist-specific framing.
        """

        context_snippets = "\n\n".join(
            chunk.get("text", "")[:1000] for chunk in state.get("context", [])[:6]
        )
        return (
            f"Project objective: {state.get('objective', '')}\n"
            f"Compliance category: {state.get('compliance_category', 'standard')}\n\n"
            f"Relevant context excerpts (truncated):\n{context_snippets or '<no context>'}"
        )

    def empty_output(self, summary: str = "") -> SpecialistOutput:
        return SpecialistOutput(
            agent=self.name,
            summary=summary,
            artefacts=[],
            warnings=[],
        )

    async def run(self, state: OrchestratorState) -> SpecialistOutput:
        """Execute the specialist and return its structured output."""

        text = await self.llm_router.call(
            LLMRequest(
                project_id=state.get("project_id", "unknown"),
                task_type="reasoning",
                messages=[
                    {"role": "system", "content": self.system_prompt(state)},
                    {"role": "user", "content": self.user_prompt(state)},
                ],
            )
        )
        return self.parse_response(text, state)

    def parse_response(
        self, text: str, state: OrchestratorState
    ) -> SpecialistOutput:
        """Convert the LLM response into a :class:`SpecialistOutput`.

        Default implementation returns the raw text as the summary; subclasses
        should override to extract structured artefacts.
        """

        return SpecialistOutput(
            agent=self.name,
            summary=text.strip(),
            artefacts=[],
            warnings=[],
        )

    @staticmethod
    def split_lines(text: str) -> list[str]:
        """Helper used by specialists to normalise list-style LLM output."""

        return [
            line.strip(" -*\u2022\t0123456789.")
            for line in text.splitlines()
            if line.strip()
        ]

    @staticmethod
    def to_artefacts(items: list[str], kind: str) -> list[dict[str, Any]]:
        return [{"kind": kind, "value": item} for item in items if item]
