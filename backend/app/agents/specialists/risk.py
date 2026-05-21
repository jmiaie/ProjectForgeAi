"""Risk specialist: surfaces risks from project context."""

from __future__ import annotations

from app.agents.specialists.base import SpecialistAgent
from app.agents.state import OrchestratorState, SpecialistOutput


class RiskAgent(SpecialistAgent):
    name = "risk"

    def system_prompt(self, state: OrchestratorState) -> str:
        return (
            "You are the Risk specialist for ProjectForge AI. "
            "Identify the top 5 risks for this project. For each risk emit a single line of "
            "the form: 'Risk: <name> | Likelihood: <low/medium/high> | Impact: <low/medium/high> "
            "| Mitigation: <one-sentence mitigation>'."
        )

    def parse_response(
        self, text: str, state: OrchestratorState
    ) -> SpecialistOutput:
        lines = [line for line in self.split_lines(text) if "Risk:" in line]
        artefacts = [{"kind": "risk", "value": line} for line in lines]
        if not artefacts:
            artefacts = [{"kind": "risk", "value": text.strip() or "No risks identified."}]
        return SpecialistOutput(
            agent=self.name,
            summary=f"Identified {len(artefacts)} risk(s).",
            artefacts=artefacts,
            warnings=[],
        )
