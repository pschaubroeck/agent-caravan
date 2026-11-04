import unittest

from agentcaravan.adapters.opencode import (
    prepare_opencode_execution,
    run_opencode_conformance_suite,
)
from agentcaravan.adapters.opencode_execution_surface import OpenCodeExecutionRequest
from agentcaravan.orchestration import OrchestrationError


def resolved_runtime(adapter_id="opencode-agent-runtime"):
    return {
        "status": "pass",
        "context": {
            "organization_catalog_id": "example-org",
            "team_blueprint_id": "blueprint",
            "execution_profile_id": "workflow",
        },
        "runtime": {"adapter_id": adapter_id, "runtime_profile_id": "opencode-profile"},
        "effective_roles": [{"id": "engineer", "source_chain": ["engineer"]}],
        "execution_profile": {
            "entry_roles": ["engineer"],
            "activation_policy": {"primary_roles": ["engineer"]},
            "stages": [{"id": "inspection", "roles": ["engineer"]}],
            "communication": {},
            "escalation": {},
            "required_outputs": ["completion record"],
        },
    }


class OpenCodeAdapterTests(unittest.TestCase):
    def test_rejects_a_different_runtime_before_dispatch(self):
        with self.assertRaisesRegex(OrchestrationError, "OpenCode"):
            prepare_opencode_execution(
                resolved_runtime("codex-desktop-agent-runtime"),
                {"task_id": "task-1", "objective": "inspect"},
            )

    def test_projection_preserves_portable_plan_identity_and_role(self):
        prepared = prepare_opencode_execution(
            resolved_runtime(), {"task_id": "task-1", "objective": "inspect"}
        )
        plan = prepared["plan"]
        projection = prepared["projection"]
        self.assertEqual(projection["plan_id"], plan["id"])
        self.assertEqual(projection["task"], plan["task"])
        self.assertEqual(projection["role_assignments"], plan["role_assignments"])
        self.assertEqual(prepared["runtime"]["adapter_id"], "opencode-agent-runtime")
        self.assertEqual(prepared["runtime"]["execution_realization"]["mode"], "unreported")

    def test_projection_carries_shared_knowledge_once_in_order_with_policy(self):
        resolved = resolved_runtime()
        resolved["effective_roles"].append({"id": "reviewer", "source_chain": ["reviewer"]})
        resolved["execution_profile"]["activation_policy"]["supporting_roles"] = ["reviewer"]
        resolved["execution_profile"]["stages"][0]["roles"].append("reviewer")
        resolved["domain_packs"] = [{
            "id": "product-domain",
            "version": "1.0.0",
            "scope": "organization",
            "knowledge_surface": ["Product architecture"],
            "trusted_sources": ["docs/product"],
            "role_guidance": {"engineer": "Focus on implementation."},
        }]
        resolved["specialization_packs"] = [{
            "id": "team-product",
            "version": "1.0.0",
            "scope": "team",
            "owner_team_instance_id": "team-instance",
            "knowledge_surface": ["Team conventions"],
            "trusted_sources": ["docs/team"],
            "role_guidance": {"reviewer": "Check team conventions."},
        }]
        resolved["team_context"] = {"knowledge_sources": ["wiki/team-overview", "wiki/release-process"]}
        resolved["knowledge_access"] = {
            "external_sources": "approved_sources",
            "approved_sources": ["docs/product", "docs/team"],
        }

        prepared = prepare_opencode_execution(
            resolved, {"task_id": "task-knowledge", "objective": "inspect"}
        )
        projection = prepared["projection"]

        layers = projection["knowledge_context"]["layers"]
        self.assertEqual([layer["id"] for layer in layers], ["product-domain", "team-product"])
        self.assertEqual(projection["supplemental_knowledge_sources"], [
            "wiki/team-overview", "wiki/release-process"
        ])
        self.assertEqual(projection["knowledge_access"]["external_sources"], "approved_sources")
        self.assertEqual(
            [entry["source"] for entry in projection["knowledge_access"]["approved_sources"]],
            ["docs/product", "docs/team"],
        )
        self.assertEqual(projection["role_assignments"], prepared["plan"]["role_assignments"])
        self.assertEqual(layers[0]["role_guidance"], {"engineer": "Focus on implementation."})
        self.assertEqual(layers[1]["role_guidance"], {"reviewer": "Check team conventions."})
        self.assertIn("every assigned role", projection["instructions"][0])
        self.assertIn("matching role", projection["instructions"][0])
        self.assertIn("knowledge_access", projection["instructions"][0])

    def test_shared_conformance_runner_receives_open_code_request_and_result(self):
        seen = []

        class Surface:
            def execute(self, request):
                seen.append(request)
                return {
                    "status": "completed",
                    "active_roles": ["engineer"],
                    "completed_stages": ["inspection"],
                    "metadata": {"opencode_cli": {"session_id": "ses-observed"}},
                }

        scenarios = [{
            "id": "one-case",
            "task": {"objective": "inspect"},
            "expected": {
                "status": "completed",
                "active_roles": ["engineer"],
                "completed_stages": ["inspection"],
                "failure_count": 0,
            },
        }]
        suite = run_opencode_conformance_suite(resolved_runtime(), scenarios, Surface())
        self.assertTrue(suite.passed)
        self.assertEqual(len(seen), 1)
        self.assertIsInstance(seen[0], OpenCodeExecutionRequest)
        self.assertEqual(seen[0].task_id, "conformance-one-case")
        self.assertEqual(seen[0].projection["plan_id"], seen[0].prepared["plan"]["id"])
        self.assertEqual(suite.cases[0].result["metadata"]["opencode_cli"]["session_id"], "ses-observed")


if __name__ == "__main__":
    unittest.main()
