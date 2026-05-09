import os
from typing import Any

from compliance.enforcer import ComplianceEnforcer
from core.config import settings
from storage.native_loader import (
    NativeIntegrationError,
    call_first_available,
    instantiate_with_path,
    load_symbol,
)


class InMemoryOmpa:
    def __init__(self, vault_path: str):
        self.vault_path = vault_path
        self.records: list[str] = []

    def classify(self, message: str) -> None:
        self.records.append(message)

    def session_start(self) -> dict:
        return {"vault_path": self.vault_path, "status": "started"}


class OmpaAdapter:
    def __init__(self, project_id: str, compliance: ComplianceEnforcer | None = None):
        self.project_id = project_id
        self.compliance = compliance or ComplianceEnforcer()
        self.vault_path = os.path.join(settings.OMPA_VAULT_ROOT, f"project_{project_id}")
        os.makedirs(self.vault_path, exist_ok=True)
        self.native = True
        self.warning: str | None = None
        try:
            Ompa = load_symbol(settings.OMPA_ENGINE, settings.OMPA_SOURCE_PATH)
            self.ao = instantiate_with_path(Ompa, "vault_path", self.vault_path)
        except NativeIntegrationError as exc:
            if settings.REQUIRE_NATIVE_LOCUS_OMPA:
                raise
            self.native = False
            self.warning = str(exc)
            self.ao = InMemoryOmpa(vault_path=self.vault_path)

    async def record_decision(self, message: str) -> None:
        decision = self.compliance.check_action(
            self.project_id,
            "memory_write",
            payload=message,
        )
        if not decision.allowed:
            return
        await call_first_available(
            self.ao,
            ("record_decision", "classify", "record", "remember"),
            decision.payload,
        )

    async def session_start(self):
        return await call_first_available(
            self.ao,
            ("session_start", "start_session", "begin_session"),
        )

    def status(self) -> dict[str, Any]:
        return {
            "name": "ompa",
            "native": self.native,
            "engine": self.ao.__class__.__name__,
            "vault_path": self.vault_path,
            "warning": self.warning,
        }
