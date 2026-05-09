"""Specialist agents invoked by the orchestrator.

Each specialist exposes the same async ``run(state) -> SpecialistOutput``
contract so the orchestrator can fan out / fan in deterministically.
"""

from app.agents.specialists.base import SpecialistAgent
from app.agents.specialists.comms import CommsAgent
from app.agents.specialists.compliance import ComplianceAgent
from app.agents.specialists.contracts import ContractsAgent
from app.agents.specialists.risk import RiskAgent
from app.agents.specialists.schedule import ScheduleAgent

DEFAULT_SPECIALISTS: dict[str, type[SpecialistAgent]] = {
    "schedule": ScheduleAgent,
    "comms": CommsAgent,
    "contracts": ContractsAgent,
    "compliance": ComplianceAgent,
    "risk": RiskAgent,
}

__all__ = [
    "CommsAgent",
    "ComplianceAgent",
    "ContractsAgent",
    "DEFAULT_SPECIALISTS",
    "RiskAgent",
    "ScheduleAgent",
    "SpecialistAgent",
]
