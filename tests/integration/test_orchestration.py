import json
import tempfile
import unittest
from pathlib import Path

from agentcaravan.adapters.codex import prepare_codex_execution, run_codex_task
from agentcaravan.foundation import OrchestrationError, build_completion_record, build_execution_records
from agentcaravan.team_configuration import load_team_context
from agentcaravan.session_store import LocalJsonExecutionStore
from agentcaravan.session_validation import validate_session_directory


def resolved_codex_profile():
    return {
        "status": "pass",
        "context": {
            "organization_catalog_id": "sample-organization-technology-catalog",
            "team_instance_id": "sample-product-workflows-team",
            "team_blueprint_id": "information-technology-core-team",
            "runtime_profile_id": "codex-desktop-information-technology-core-team",
            "execution_profile_id": "information-technology-core-team-feature-delivery",
        },
        "effective_roles": [
            {"id": "tech-owner", "source_chain": ["tech-owner"]},
            {"id": "engineer", "source_chain": ["engineer"]},
            {"id": "quality-engineer", "source_chain": ["quality-engineer"]},
        ],
        "runtime": {
            "adapter_id": "codex-desktop-agent-runtime",
            "degraded_capabilities": ["parallel_lane_execution"],
        },
        "execution_profile": {
            "entry_roles": ["tech-owner"],
            "activation_policy": {
                "primary_roles": ["engineer"],
                "supporting_roles": ["quality-engineer"],
            },
            "stages": [
                {"id": "breakdown", "roles": ["tech-owner"]},
                {"id": "implementation", "roles": ["engineer"]},
                {"id": "quality", "roles": ["quality-engineer"]},
            ],
            "communication": {
                "requires_structured_handoff": True,
                "allowed_role_handoffs": [{"from": "tech-owner", "to": "engineer"}],
            },
            "escalation": {"human_approval_required_for": ["new dependency or integration"]},
            "required_outputs": ["completion record"],
            "topology": {"mode": "sequential", "task_ownership": "caller-retains"},
            "tool_requirements": [
                {
                    "id": "repository-inspection",
                    "side_effect_class": "read-only",
                    "approval_required": False,
                }
            ],
            "evidence_requirements": [{"kind": "completion-record", "required": True}],
        },
    }


class OrchestrationIntegrationTests(unittest.TestCase):
    def test_parallel_lane_worker_evidence_is_normalized_persisted_and_revalidated(self):
        resolved = resolved_codex_profile()
        resolved["effective_roles"].append({"id": "software-architect", "source_chain": ["software-architect"]})
        resolved["team_context"] = {"preferred_roles": ["tech-owner", "quality-engineer"]}
        resolved["execution_profile"]["activation_policy"]["mandatory_reviewers"] = ["software-architect"]
        resolved["execution_profile"]["stages"] = [
            {"id": "solution-and-testability", "roles": ["tech-owner", "quality-engineer", "software-architect"]},
            {"id": "implementation", "roles": ["engineer"]},
        ]
        resolved["execution_profile"]["topology"]["parallel_lanes"] = [
            {"id": "quality-preparation", "stage_id": "solution-and-testability", "role_ids": ["quality-engineer"], "purpose": "testability preparation"},
            {"id": "architecture-research", "stage_id": "solution-and-testability", "role_ids": ["software-architect"], "purpose": "architecture research"},
        ]
        resolved["execution_profile"]["topology"]["serial_fallback"] = {
            "mode": "run-in-order", "lane_ids": ["quality-preparation", "architecture-research"]
        }
        task = {"task_id": "parallel-evidence-task", "objective": "Validate lane evidence persistence", "execution_diagnostics": True}

        def executor(_, __):
            return {
                "status": "completed",
                "execution_realization": {
                    "mode": "native-parallel",
                    "native_subagents": True,
                    "parallel_lane_evidence": [
                        {"lane_id": "quality-preparation", "stage_id": "solution-and-testability", "role_id": "quality-engineer", "worker_ref": "worker-quality"},
                        {"lane_id": "architecture-research", "stage_id": "solution-and-testability", "role_id": "software-architect", "worker_ref": "worker-architect"},
                    ],
                },
                "active_roles": ["quality-engineer", "software-architect"],
                "completed_stages": ["solution-and-testability", "implementation"],
                "evidence": [{"kind": "completion-record", "status": "passed"}],
                "role_turns": [
                    {"role_turn_id": "turn-quality", "task_id": task["task_id"], "stage_id": "solution-and-testability", "role_id": "quality-engineer", "status": "completed", "summary": "Testability risks identified.", "worker_ref": "worker-quality"},
                    {"role_turn_id": "turn-architect", "task_id": task["task_id"], "stage_id": "solution-and-testability", "role_id": "software-architect", "status": "completed", "summary": "Architecture risks identified.", "worker_ref": "worker-architect"},
                ],
            }

        with tempfile.TemporaryDirectory() as temporary:
            store = LocalJsonExecutionStore(temporary)
            result = run_codex_task(resolved, task, executor, store=store)
            self.assertEqual(result["execution_realization"]["parallel_lane_ids"], ["quality-preparation", "architecture-research"])
            self.assertEqual(result["topology_conformance"]["status"], "pass")
            self.assertEqual(result["parallel_timing_conformance"]["status"], "unverified")
            self.assertEqual(result["execution_diagnostics"]["role_selection"]["preferred_role_ids"], ["quality-engineer", "tech-owner"])
            self.assertTrue(validate_session_directory(temporary, task["task_id"])["valid"])

            session_root = Path(temporary) / task["task_id"]
            completion_path = session_root / "completion.json"
            completion = json.loads(completion_path.read_text(encoding="utf-8"))
            completion["execution_realization"]["parallel_lane_evidence"][0]["worker_ref"] = "tampered-worker"
            completion_path.write_text(json.dumps(completion), encoding="utf-8")
            validation = validate_session_directory(temporary, task["task_id"])
            self.assertFalse(validation["valid"])
            self.assertTrue(any("topology_conformance does not match" in issue for issue in validation["issues"]))

    def test_file_backed_team_guidance_reaches_runtime_brief(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            (workspace / "instructions.md").write_text(
                "# Team AI Instructions\n\nPrefer small, verifiable changes.\n",
                encoding="utf-8",
            )
            (workspace / "responsibilities.md").write_text(
                "# Team AI Role Guidance\n\n## Preferred roles\n\n- engineer\n- quality-engineer\n\n"
                "## Participation guidance\n\nEngineering leads implementation; quality reviews evidence.\n",
                encoding="utf-8",
            )

            resolved = resolved_codex_profile()
            resolved["team_context"] = load_team_context(
                workspace,
                {
                    "mission": "Own platform delivery.",
                    "work_surfaces": [],
                    "knowledge_sources": [],
                    "working_agreements": "Test before review.",
                },
            )

            prepared = prepare_codex_execution(
                resolved,
                {"task_id": "team-guidance-task", "objective": "Prove team guidance projection"},
            )

            self.assertIn("Prefer small, verifiable changes.", prepared["projection"]["instructions"])
            self.assertIn(
                "Team working agreements: Test before review.",
                prepared["projection"]["instructions"],
            )
            self.assertIn(
                "Team role participation guidance: Engineering leads implementation; quality reviews evidence.",
                prepared["projection"]["instructions"],
            )
            self.assertEqual(
                prepared["projection"]["team_guidance"]["preferred_roles"],
                ["engineer", "quality-engineer"],
            )

    def test_prepares_plan_projection_and_evidence_for_a_real_task(self):
        prepared = prepare_codex_execution(
            resolved_codex_profile(),
            {
                "task_id": "TASK-999999",
                "objective": "Plan and implement a small feature",
                "references": [{
                    "system_type": "work-tracker",
                    "reference_type": "work-item",
                    "identifier": "TASK-999999",
                    "provider": "jira",
                }],
            },
        )

        self.assertEqual(prepared["status"], "ready")
        self.assertEqual(
            prepared["runtime"]["runtime_profile_id"],
            "codex-desktop-information-technology-core-team",
        )
        self.assertEqual(prepared["plan"]["id"], "TASK-999999-execution-plan")
        self.assertNotIn("runtime", prepared["plan"])
        self.assertEqual(prepared["projection"]["plan_id"], prepared["plan"]["id"])

        records = build_execution_records(
            prepared,
            session_id="session-1",
            run_id="run-1",
            started_at="2026-08-17T12:00:00Z",
        )
        self.assertEqual(records["task"]["plan"][0]["plan_id"], prepared["plan"]["id"])
        self.assertEqual(records["session"]["plan_id"], prepared["plan"]["id"])
        self.assertEqual(records["run"]["plan_id"], prepared["plan"]["id"])
        self.assertEqual(records["session"]["execution_topology"]["mode"], "sequential")
        self.assertEqual(records["task"]["tool_requirements"][0]["id"], "repository-inspection")
        self.assertEqual(records["task"]["checkpoints"], [])
        self.assertEqual(records["run"]["idempotency_records"], [])

        completion = build_completion_record(
            prepared,
            "completed",
            "2026-08-17T12:30:00Z",
            evidence=[{"kind": "test", "status": "passed"}],
        )
        self.assertEqual(completion["plan_id"], prepared["plan"]["id"])
        self.assertEqual(completion["task_id"], "TASK-999999")
        self.assertEqual(completion["evidence"][0]["status"], "passed")
        self.assertEqual(completion["evidence_requirements"][0]["kind"], "completion-record")

    def test_runtime_projection_is_blocked_when_codex_is_not_selected(self):
        resolved = resolved_codex_profile()
        resolved["runtime"]["adapter_id"] = "other-runtime"
        with self.assertRaises(OrchestrationError):
            prepare_codex_execution(resolved, {"task_id": "task-1", "objective": "x"})


if __name__ == "__main__":
    unittest.main()
