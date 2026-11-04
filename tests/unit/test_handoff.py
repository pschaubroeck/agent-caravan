import json
import unittest
from pathlib import Path

from agentcaravan.handoff import TaskHandoffError, build_task_handoff, validate_task_handoff


ROOT = Path(__file__).parents[2]


def plan():
    return {
        "id": "task-1-execution-plan",
        "task": {"task_id": "task-1", "objective": "Implement a bounded change"},
        "context": {"organization_catalog_id": "org", "team_blueprint_id": "team", "workflow_id": "flow"},
        "role_assignments": [
            {"role_id": "tech-owner", "participation": "entry"},
            {"role_id": "engineer", "participation": "primary"},
        ],
        "execution_topology": {"mode": "handoff", "task_ownership": "receiver-takes-over"},
        "capability_requirements": {"required": ["subagent_delegation"]},
        "communication": {"allowed_role_handoffs": [{"from": "tech-owner", "to": "engineer"}]},
        "required_outputs": ["working code", "verification evidence"],
    }


class TaskHandoffTests(unittest.TestCase):
    def test_role_and_task_schemas_have_distinct_discriminators(self):
        role_schema = json.loads((ROOT / "resources/schemas/handoff.schema.json").read_text())
        task_schema = json.loads((ROOT / "resources/schemas/task-handoff.schema.json").read_text())

        self.assertEqual(role_schema["properties"]["artifact_type"]["const"], "role-handoff")
        self.assertNotIn("artifact_type", role_schema["required"])
        self.assertEqual(task_schema["properties"]["artifact_type"]["const"], "task-handoff")
        self.assertIn("artifact_type", task_schema["required"])
        self.assertNotEqual(
            role_schema["properties"]["artifact_type"]["const"],
            task_schema["properties"]["artifact_type"]["const"],
        )

    def test_builds_complete_runtime_neutral_task_handoff(self):
        result = build_task_handoff(
            plan(),
            runtime_context={"adapter_id": "example-runtime", "profile_id": "example-profile"},
            sender_role="tech-owner",
            receiver_role="engineer",
            requested_action="Implement and test the bounded change",
        )
        self.assertEqual(result["artifact_type"], "task-handoff")
        self.assertEqual(result["plan_id"], "task-1-execution-plan")
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["selected_context"]["runtime"]["profile_id"], "example-profile")
        self.assertIn("selected harness should validate", result["next_action"])

    def test_rejects_disallowed_role_edge_and_runtime_leakage(self):
        with self.assertRaises(TaskHandoffError):
            build_task_handoff(
                plan(),
                runtime_context={},
                sender_role="engineer",
                receiver_role="tech-owner",
                requested_action="Reverse the handoff",
            )
        handoff = build_task_handoff(
            plan(), runtime_context={}, sender_role="tech-owner", receiver_role="engineer", requested_action="Implement"
        )
        handoff["worker_ref"] = "native-worker"
        with self.assertRaisesRegex(TaskHandoffError, "runtime-specific"):
            validate_task_handoff(handoff, plan=plan())

    def test_rejects_task_identity_mismatch(self):
        handoff = build_task_handoff(
            plan(), runtime_context={}, sender_role="tech-owner", receiver_role="engineer", requested_action="Implement"
        )
        with self.assertRaisesRegex(TaskHandoffError, "task_id"):
            validate_task_handoff(handoff, task_id="different-task")


if __name__ == "__main__":
    unittest.main()
