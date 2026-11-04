"""Focused checks for the declarative Kiro IDE adapter contract."""

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_BUNDLE = ROOT / "resources" / "runtime" / "agentcaravan-kiro-runtime.json"
SKILL_MANIFEST = ROOT / "skills" / "skill-distribution.json"
SKILL_SOURCE = ROOT / "skills" / "agent-caravan-kiro-orchestrator" / "SKILL.md"
INTEGRATION_DOC = ROOT / "docs" / "integrations" / "kiro-ide-adapter.md"


class KiroAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bundle = json.loads(RUNTIME_BUNDLE.read_text(encoding="utf-8"))
        cls.artifacts = {item["artifact_type"]: item for item in bundle["artifacts"]}

    def test_runtime_profile_targets_the_kiro_ide_adapter_and_core_team(self):
        adapter = self.artifacts["runtime-adapter"]
        profile = self.artifacts["runtime-profile"]

        self.assertEqual(adapter["id"], "kiro-ide-agent-runtime")
        self.assertEqual(profile["id"], "kiro-ide-information-technology-core-team")
        self.assertEqual(profile["target_adapter_id"], adapter["id"])
        self.assertEqual(profile["target_team_blueprint_id"], "information-technology-core-team")

    def test_native_and_adapted_capabilities_have_explicit_serial_and_evidence_fallbacks(self):
        adapter = self.artifacts["runtime-adapter"]
        profile = self.artifacts["runtime-profile"]
        capabilities = adapter["capabilities"]

        self.assertEqual(capabilities["subagent_delegation"], "native")
        self.assertEqual(capabilities["parallel_lane_execution"], "native")
        self.assertEqual(capabilities["tool_approval_gates"], "native")
        self.assertEqual(capabilities["role_handoff"], "adapted")
        self.assertEqual(capabilities["execution_trace"], "adapted")
        self.assertEqual(profile["capability_support_requirements"]["subagent_delegation"], "native")
        self.assertTrue(any("serially" in rule for rule in profile["fallback_rules"]))
        self.assertIn(
            "operator-visible activity is not a complete machine-readable execution trace",
            adapter["observability_model"]["constraints"],
        )

    def test_app_native_entry_point_is_packaged_only_for_kiro(self):
        manifest = json.loads(SKILL_MANIFEST.read_text(encoding="utf-8"))
        entry = next(item for item in manifest["skills"] if item["id"] == "agent-caravan-kiro-orchestrator")
        skill = SKILL_SOURCE.read_text(encoding="utf-8")

        self.assertEqual(entry["runtimes"], ["kiro"])
        self.assertIn("does not launch or depend on Kiro CLI", skill)
        self.assertIn("If the selected harness or adapter differs, stop", skill)
        self.assertIn("Do not claim a subagent ran", skill)

    def test_kiro_guidance_consumes_portable_team_knowledge_without_overclaiming(self):
        skill = " ".join(SKILL_SOURCE.read_text(encoding="utf-8").split())
        integration_doc = " ".join(INTEGRATION_DOC.read_text(encoding="utf-8").split())

        for text in (skill, integration_doc):
            self.assertIn("knowledge_context.layers", text)
            self.assertIn("every role assigned", text)
            self.assertIn("domain layers before", text)
            self.assertIn("role_guidance", text)
            self.assertIn("context.team_context.knowledge_sources", text)
            self.assertIn("policy.knowledge_access", text)

        self.assertIn("repository-local Kiro code bridge", skill)
        self.assertIn("live knowledge-consumption conformance are not present", skill)
        self.assertIn("no local Kiro code bridge", integration_doc)
        self.assertIn("remains unverified", integration_doc)


if __name__ == "__main__":
    unittest.main()
