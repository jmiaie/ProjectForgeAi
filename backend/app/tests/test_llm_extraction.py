import unittest

from graph.extraction import LLMExtractionPayload, parse_llm_extraction_payload


class LLMExtractionValidationTests(unittest.TestCase):
    def test_parse_llm_payload_from_markdown_fence(self):
        response = """
Here are the facts:
```json
{
  "stakeholders": [{"name": "owner@example.com", "excerpt": "From: owner@example.com"}],
  "tasks": [{"name": "Finalize budget", "excerpt": "Task: finalize budget", "sequence": 1}],
  "risks": [{"name": "Permit delay", "excerpt": "Risk: permit delay", "severity": "high"}],
  "milestones": [{"name": "Kickoff", "excerpt": "Kickoff milestone next week", "sequence": 1}]
}
```
"""
        payload = parse_llm_extraction_payload(response)
        validated = LLMExtractionPayload.model_validate(payload)
        self.assertEqual(len(validated.stakeholders), 1)
        self.assertEqual(validated.tasks[0].name, "Finalize budget")
        self.assertEqual(validated.risks[0].severity, "high")

    def test_parse_llm_payload_rejects_invalid_shape(self):
        with self.assertRaises(Exception):
            parse_llm_extraction_payload('{"stakeholders": [{"name": ""}]}')


if __name__ == "__main__":
    unittest.main()
