"""Communications specialist: drafts kickoff + status communications."""

from __future__ import annotations

from app.agents.specialists.base import SpecialistAgent
from app.agents.state import OrchestratorState, SpecialistOutput


class CommsAgent(SpecialistAgent):
    name = "comms"

    def system_prompt(self, state: OrchestratorState) -> str:
        return (
            "You are the Communications specialist for ProjectForge AI. "
            "Produce three artefacts in this order, each separated by a line containing only '---': "
            "1) a project kickoff email, "
            "2) a weekly status update template, "
            "3) a stakeholder escalation message template. "
            "Keep tone professional and concise."
        )

    def parse_response(
        self, text: str, state: OrchestratorState
    ) -> SpecialistOutput:
        sections = [section.strip() for section in text.split("---") if section.strip()]
        labels = ["kickoff_email", "status_update", "escalation"]
        artefacts = []
        for label, section in zip(labels, sections):
            artefacts.append({"kind": "comms_template", "label": label, "value": section})
        if len(sections) < 3:
            artefacts.append(
                {
                    "kind": "comms_template",
                    "label": "raw",
                    "value": text.strip(),
                }
            )
        return SpecialistOutput(
            agent=self.name,
            summary=f"Generated {len(artefacts)} communication template(s).",
            artefacts=artefacts,
            warnings=[],
        )
