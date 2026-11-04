import json
import unittest
from pathlib import Path

from agentfoundry.codex_adapter import project_execution_brief
from agentfoundry.execution_plan import build_portable_execution_plan, validate_portable_execution_plan


ROOT = Path(__file__).parents[2]
MANIFEST = ROOT / "catalog-manifest.json"


class CatalogManifestTests(unittest.TestCase):
    def test_reference_manifest_is_non_versioned_and_points_to_existing_content(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

        self.assertEqual(manifest["manifest_type"], "agentfoundry-catalog")
        self.assertNotIn("version", manifest)
        self.assertIsNone(manifest["release_identity"]["package_version_field"])

        for path in manifest["artifact_roots"].values():
            self.assertTrue((ROOT / path).is_dir(), path)
        for path in manifest["specifications"]:
            self.assertTrue((ROOT / path).is_file(), path)
        for path in manifest["runtime_adapter_docs"]:
            self.assertTrue((ROOT / path).is_file(), path)
        for path in manifest["machine_readable_bundles"]:
            self.assertTrue((ROOT / path).is_file(), path)
        for path in manifest["machine_readable_artifacts"]:
            self.assertTrue((ROOT / path).is_file(), path)
        for path in manifest["machine_readable_roots"]:
            self.assertTrue((ROOT / path).is_dir(), path)
        for item in manifest["distribution_snapshot_pairs"]:
            self.assertTrue((ROOT / item["snapshot"]).is_file(), item["snapshot"])
            self.assertTrue((ROOT / item["canonical"]).is_file(), item["canonical"])
        for path in manifest["portable_execution_plan_examples"]:
            self.assertTrue((ROOT / path).is_file(), path)
        for path in manifest["markdown_artifact_roots"]:
            self.assertTrue((ROOT / path).is_dir(), path)
        for path in manifest["markdown_artifact_documents"]:
            self.assertTrue((ROOT / path).is_file(), path)
        for path in manifest["execution_workflows"]:
            self.assertTrue((ROOT / path).is_file(), path)
        for path in manifest["policy_artifacts"]:
            self.assertTrue((ROOT / path).is_file(), path)
        for path in manifest["schemas"]:
            self.assertTrue((ROOT / path).is_file(), path)
        for path in manifest["examples"]:
            self.assertTrue((ROOT / path).exists(), path)
        plan = json.loads((ROOT / "tests/fixtures/portable-feature-delivery-plan.json").read_text(encoding="utf-8"))
        self.assertEqual(plan["artifact_type"], "portable-execution-plan")
        self.assertNotIn("runtime", plan)
        for path in manifest["execution_state_templates"]:
            self.assertTrue((ROOT / path).is_file(), path)
        self.assertTrue((ROOT / manifest["conformance_scenarios"]).is_file())
        self.assertTrue((ROOT / manifest["vocabulary"]).is_file())
        self.assertTrue((ROOT / manifest["local_profile"]).is_file())

    def test_python_package_metadata_uses_src_layout_and_tag_versioning(self):
        metadata = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

        self.assertIn('name = "agent-caravan"', metadata)
        self.assertIn('dynamic = ["version"]', metadata)
        self.assertIn('where = ["src"]', metadata)
        self.assertIn('"setuptools-scm==9.2.2"', metadata)

    def test_execution_profile_example_has_required_contract_sections(self):
        profile_path = ROOT / "resources/execution/workflows/information-technology-core-team-feature-delivery.json"
        profile = json.loads(profile_path.read_text(encoding="utf-8"))

        self.assertEqual(profile["artifact_type"], "execution-profile")
        for field in ("id", "version", "scope", "team_blueprint_id", "entry_roles", "activation_policy", "topology", "termination", "escalation"):
            self.assertIn(field, profile)
        self.assertTrue(profile["stages"])
        self.assertTrue(profile["communication"]["requires_structured_handoff"])
        self.assertEqual(profile["topology"]["handoff_semantics"], "mixed")
        self.assertTrue(profile["tool_requirements"])
        self.assertTrue(profile["evidence_requirements"])
        self.assertNotIn("release-manager", profile["reasoning_policy"]["role_defaults"])
        self.assertIn("product-owner", profile["entry_roles"])
        self.assertNotIn("product-owner", profile["activation_policy"]["supporting_roles"])
        self.assertNotIn("product-owner", profile["activation_policy"]["conditional_roles"])
        self.assertEqual(
            profile["activation_policy"]["conditional_roles"]["release-manager"],
            "merge, pipeline, release, or promotion work is requested",
        )

    def test_starter_execution_profile_does_not_require_policy_or_audit_evidence(self):
        profile = json.loads(
            (ROOT / "resources/execution/workflows/information-technology-core-team-basic-work.json").read_text(encoding="utf-8")
        )

        self.assertEqual(profile["id"], "information-technology-core-team-basic-work")
        self.assertNotIn("policy_ids", profile)
        self.assertNotIn("evidence_requirements", profile)
        self.assertNotIn("tool_requirements", profile)

    def test_execution_state_templates_preserve_task_session_run_identity(self):
        task = json.loads((ROOT / "resources/execution/state/task.template.json").read_text(encoding="utf-8"))
        session = json.loads((ROOT / "resources/execution/state/session.template.json").read_text(encoding="utf-8"))
        run = json.loads((ROOT / "resources/execution/state/run.template.json").read_text(encoding="utf-8"))

        self.assertIn("task_id", task)
        self.assertEqual(session["task_id"], "<task-id>")
        self.assertEqual(run["session_id"], "<session-id>")
        self.assertEqual(run["task_id"], "<task-id>")

    def test_conformance_scenarios_are_runtime_neutral_and_complete(self):
        scenarios_path = ROOT / "tests/conformance/scenarios.json"
        payload = json.loads(scenarios_path.read_text(encoding="utf-8"))
        scenarios = payload["scenarios"]
        expected_ids = {
            "simple-sequential-execution",
            "technical-handoff",
            "quality-review",
            "human-approval",
            "failed-tool-call",
            "resumable-task",
            "completion-evidence",
            "tool-permission-boundary",
            "interrupted-run",
            "checkpoint-resume",
            "idempotent-side-effect-replay",
            "degraded-capability-fallback",
            "dependency-wait-with-independent-work",
        }

        self.assertEqual({scenario["id"] for scenario in scenarios}, expected_ids)
        serialized = scenarios_path.read_text(encoding="utf-8").lower()
        for vendor_term in ("langgraph", "crewai", "autogen", "codex", "agno"):
            self.assertNotIn(vendor_term, serialized)
        for scenario in scenarios:
            self.assertIn("task", scenario)
            self.assertIn("expected", scenario)
            self.assertIn("status", scenario["expected"])

    def test_conformance_scenarios_compile_to_portable_plans(self):
        scenarios = json.loads((ROOT / "tests/conformance/scenarios.json").read_text(encoding="utf-8"))["scenarios"]
        for scenario in scenarios:
            active_roles = scenario["expected"]["active_roles"]
            resolved = {
                "status": "pass",
                "context": {
                    "organization_catalog_id": "example-organization",
                    "team_blueprint_id": "information-technology-core-team",
                    "execution_profile_id": "conformance-workflow",
                },
                "effective_roles": [{"id": role, "source_chain": [role]} for role in active_roles],
                "execution_profile": {
                    "entry_roles": active_roles[:1],
                    "activation_policy": {"primary_roles": active_roles[1:]},
                    "stages": [{"id": "scenario-step", "roles": active_roles, "output": "scenario result"}],
                    "communication": {"requires_structured_handoff": True, "allowed_role_handoffs": []},
                    "escalation": {},
                    "required_outputs": ["completion record"],
                },
            }
            plan = build_portable_execution_plan(
                resolved,
                {"task_id": scenario["id"], "objective": scenario["task"]["objective"]},
            )
            validate_portable_execution_plan(plan)
            brief = project_execution_brief(plan)
            self.assertEqual(brief["plan_id"], f"{scenario['id']}-execution-plan")
            self.assertEqual([lane["role_id"] for lane in brief["role_lanes"]], active_roles)
            self.assertNotIn("runtime", plan)

    def test_portable_fixture_contains_runtime_neutral_execution_contracts(self):
        plan = json.loads((ROOT / "tests/fixtures/portable-feature-delivery-plan.json").read_text(encoding="utf-8"))

        self.assertEqual(plan["execution_topology"]["mode"], "sequential")
        self.assertEqual(plan["communication"]["handoff_semantics"], "mixed")
        self.assertEqual(plan["tool_requirements"][0]["side_effect_class"], "read-only")
        self.assertEqual(plan["evidence_requirements"][0]["kind"], "handoff-record")
        validate_portable_execution_plan(plan)

    def test_portable_plan_schema_declares_team_context_contract(self):
        schema = json.loads(
            (ROOT / "resources/schemas/portable-execution-plan.schema.json").read_text(encoding="utf-8")
        )
        context = schema["properties"]["context"]
        team_context = context["properties"]["team_context"]
        self.assertFalse(context["additionalProperties"])
        self.assertEqual(
            set(team_context["properties"]),
            {
                "mission",
                "work_surfaces",
                "knowledge_sources",
                "working_agreements",
                "instructions",
                "preferred_roles",
                "role_guidance",
            },
        )
        self.assertFalse(team_context["additionalProperties"])
        knowledge_context = schema["properties"]["knowledge_context"]
        self.assertFalse(knowledge_context["additionalProperties"])
        self.assertEqual(set(knowledge_context["properties"]), {"layers"})
        layer = knowledge_context["properties"]["layers"]["items"]
        self.assertFalse(layer["additionalProperties"])
        self.assertEqual(
            set(layer["properties"]),
            {
                "artifact_type", "id", "version", "scope", "owner_team_instance_id",
                "parent_domain_pack_id", "purpose", "domain_intent", "knowledge_surface",
                "trusted_sources", "loading_guidance", "role_guidance", "documentation_references",
            },
        )


if __name__ == "__main__":
    unittest.main()
