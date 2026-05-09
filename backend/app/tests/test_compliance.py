import tempfile
import unittest
from pathlib import Path

from compliance.audit import ComplianceAuditStore
from compliance.enforcer import ComplianceEnforcer, ComplianceProfileStore
from compliance.redaction import redact_text
from storage.ompa_adapter import OmpaAdapter


class ComplianceTests(unittest.IsolatedAsyncioTestCase):
    async def test_hipaa_profile_redacts_llm_payload_and_blocks_memory_writes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            enforcer = ComplianceEnforcer(
                profile_store=ComplianceProfileStore(root=str(root / "profiles")),
                audit_store=ComplianceAuditStore(root=str(root / "audit")),
            )
            enforcer.set_profile("compliance-test", "hipaa")

            decision = enforcer.check_action(
                "compliance-test",
                "llm_call",
                payload=[{"role": "user", "content": "Email owner@example.com, MRN 1234-A"}],
            )

            self.assertTrue(decision.allowed)
            self.assertEqual(decision.profile.category, "hipaa")
            self.assertIn("[REDACTED_EMAIL]", decision.payload[0]["content"])
            self.assertTrue(decision.redactions)

            memory_decision = enforcer.check_action(
                "compliance-test",
                "memory_write",
                payload="Remember owner@example.com",
            )
            self.assertFalse(memory_decision.allowed)
            self.assertIn("blocks", memory_decision.reason)

    async def test_ompa_adapter_skips_blocked_memory_write(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            enforcer = ComplianceEnforcer(
                profile_store=ComplianceProfileStore(root=str(root / "profiles")),
                audit_store=ComplianceAuditStore(root=str(root / "audit")),
            )
            enforcer.set_profile("ompa-hipaa", "hipaa")
            ompa = OmpaAdapter("ompa-hipaa", compliance=enforcer)

            await ompa.record_decision("Do not persist this")

            self.assertEqual(getattr(ompa.ao, "records", []), [])
            events = enforcer.audit_events("ompa-hipaa")
            self.assertTrue(any(event["action"] == "memory_write" and not event["allowed"] for event in events))

    async def test_standard_profile_allows_memory_write(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            enforcer = ComplianceEnforcer(
                profile_store=ComplianceProfileStore(root=str(root / "profiles")),
                audit_store=ComplianceAuditStore(root=str(root / "audit")),
            )
            enforcer.set_profile("ompa-standard", "standard")
            ompa = OmpaAdapter("ompa-standard", compliance=enforcer)

            await ompa.record_decision("Persist this")

            self.assertEqual(getattr(ompa.ao, "records", []), ["Persist this"])


class RedactionTests(unittest.TestCase):
    def test_redact_text_masks_common_sensitive_values(self):
        result = redact_text("Contact owner@example.com at 555-123-4567 with SSN 123-45-6789")

        self.assertIn("[REDACTED_EMAIL]", result.text)
        self.assertIn("[REDACTED_PHONE]", result.text)
        self.assertIn("[REDACTED_SSN]", result.text)
        self.assertEqual(len(result.redactions), 3)


if __name__ == "__main__":
    unittest.main()
