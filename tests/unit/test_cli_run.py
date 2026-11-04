import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentcaravan.cli import generated_task_id, main


def resolved_codex_profile():
    return {
        "status": "pass",
        "context": {
            "organization_catalog_id": "example-organization",
            "team_instance_id": "example-team",
            "team_blueprint_id": "information-technology-core-team",
            "runtime_profile_id": "codex-desktop-information-technology-core-team",
            "execution_profile_id": "information-technology-core-team-feature-delivery",
        },
        "effective_roles": [
            {"id": "tech-owner", "source_chain": ["tech-owner"]},
            {"id": "engineer", "source_chain": ["engineer"]},
            {"id": "quality-engineer", "source_chain": ["quality-engineer"]},
        ],
        "runtime": {"adapter_id": "codex-desktop-agent-runtime", "degraded_capabilities": []},
        "execution_profile": {
            "entry_roles": ["tech-owner"],
            "activation_policy": {"primary_roles": ["engineer"], "supporting_roles": ["quality-engineer"]},
            "stages": [
                {"id": "breakdown", "roles": ["tech-owner"]},
                {"id": "implementation", "roles": ["engineer"]},
            ],
            "communication": {
                "requires_structured_handoff": True,
                "allowed_role_handoffs": [{"from": "tech-owner", "to": "engineer"}],
            },
            "escalation": {"human_approval_required_for": ["new dependency or integration"]},
            "required_outputs": ["completion record"],
            "topology": {"mode": "sequential", "task_ownership": "caller-retains"},
            "tool_requirements": [{"id": "repository-inspection", "side_effect_class": "read-only", "approval_required": False}],
            "evidence_requirements": [{"kind": "completion-record", "required": True}],
            "termination": {
                "success_criteria": [
                    {"id": "task-accepted", "description": "Task was accepted.", "assessor_roles": ["tech-owner"]}
                ]
            },
        },
    }


class CliRunTests(unittest.TestCase):
    def test_generated_task_id_is_readable_safe_and_bounded(self):
        task_id = generated_task_id("Review the team / configuration boundaries!")

        self.assertRegex(task_id, r"^task-review-the-team-configuration-boundaries-\d{8}-\d{12}-[0-9a-f]{8}$")
        self.assertLessEqual(len(task_id), 200)

    def test_dry_run_resolves_executes_and_persists_the_golden_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = io.StringIO()
            with patch("agentcaravan.cli.resolve_profile", return_value=resolved_codex_profile()):
                with contextlib.redirect_stdout(output):
                    exit_code = main([
                        "run",
                        "--root", str(root),
                        "--task-id", "task-1",
                        "--objective", "Demonstrate the golden path",
                        "--dry-run",
                    ])

            self.assertEqual(exit_code, 0)
            summary = json.loads(output.getvalue())
            self.assertEqual(summary["status"], "completed")
            self.assertEqual(summary["task_id"], "task-1")
            self.assertEqual(summary["execution_realization"]["mode"], "simulated-sequential")
            self.assertIn("topology_conformance", summary)
            self.assertNotIn("execution_diagnostics", summary)
            self.assertFalse(summary["execution_realization"]["native_subagents"])
            self.assertTrue(summary["role_turns"])
            self.assertEqual(summary["role_turns"][0]["status"], "unverified")
            self.assertEqual(summary["workflow_assessment"]["status"], "unverified")
            self.assertEqual(summary["workflow_assessment"]["run_id"], "task-1-codex-run-1")
            self.assertEqual(
                summary["reasoning_evidence"],
                [
                    {
                        "stage_id": "breakdown",
                        "role_id": "tech-owner",
                        "requested_level": "standard",
                        "requested_runtime_value": "medium",
                        "status": "unverified",
                        "dispatch_status": "not-attempted",
                        "telemetry_status": "unverified",
                    },
                    {
                        "stage_id": "implementation",
                        "role_id": "engineer",
                        "requested_level": "standard",
                        "requested_runtime_value": "medium",
                        "status": "unverified",
                        "dispatch_status": "not-attempted",
                        "telemetry_status": "unverified",
                    },
                ],
            )
            self.assertNotIn("worker_ref", summary["reasoning_evidence"][0])
            self.assertEqual(summary["session_path"], str(root / "sessions" / "task-1"))
            self.assertTrue(summary["session_validation"]["valid"], summary)
            self.assertIn("agent-caravan-codex-orchestrator", summary["next_step"])
            completion = json.loads((root / "sessions" / "task-1" / "completion.json").read_text())
            self.assertEqual(completion["status"], "completed")
            self.assertEqual(completion["workflow_assessment"], summary["workflow_assessment"])
            self.assertTrue((root / "sessions" / "task-1" / "runs" / "task-1-codex-run-1.json").exists())

    def test_debug_flag_includes_opt_in_execution_diagnostics(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = io.StringIO()
            with patch("agentcaravan.cli.resolve_profile", return_value=resolved_codex_profile()):
                with contextlib.redirect_stdout(output):
                    exit_code = main(["run", "--root", temporary, "--task-id", "debug-task", "--objective", "Inspect topology", "--dry-run", "--debug"])
            self.assertEqual(exit_code, 0)
            summary = json.loads(output.getvalue())
            self.assertIn("execution_diagnostics", summary)
            self.assertEqual(summary["execution_diagnostics"]["topology_conformance"]["status"], "pass")
            session_root = Path(temporary) / "sessions" / "debug-task"
            self.assertIn("execution_diagnostics", json.loads((session_root / "completion.json").read_text()))
            self.assertIn("execution_diagnostics", json.loads((session_root / "task.json").read_text()))
            self.assertIn("execution_diagnostics", json.loads((session_root / "session.json").read_text()))
            self.assertIn("execution_diagnostics", json.loads((session_root / "runs" / "debug-task-codex-run-1.json").read_text()))

    def test_dry_run_generates_task_id_and_validates_persisted_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = io.StringIO()
            with patch("agentcaravan.cli.resolve_profile", return_value=resolved_codex_profile()):
                with contextlib.redirect_stdout(output):
                    exit_code = main([
                        "run",
                        "--root", str(root),
                        "--objective", "Demonstrate generated task IDs",
                        "--dry-run",
                    ])

            self.assertEqual(exit_code, 0)
            summary = json.loads(output.getvalue())
            self.assertRegex(summary["task_id"], r"^task-demonstrate-generated-task-ids-\d{8}-\d{12}-[0-9a-f]{8}$")
            self.assertTrue(summary["session_validation"]["valid"], summary)
            self.assertTrue((root / "sessions" / summary["task_id"] / "completion.json").exists())

    def test_run_reasoning_summary_omits_unbounded_runtime_fields(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = io.StringIO()
            with patch("agentcaravan.cli.resolve_profile", return_value=resolved_codex_profile()):
                with patch(
                    "agentcaravan.cli.run_codex_task",
                    return_value={
                        "status": "completed",
                        "task_id": "task-1",
                        "plan_id": "task-1-execution-plan",
                        "active_roles": ["engineer"],
                        "completed_stages": ["implementation"],
                        "execution_realization": {"mode": "native-sequential", "native_subagents": True},
                        "role_turns": [],
                        "reasoning_evidence": [
                            {
                                "stage_id": "implementation",
                                "role_id": "engineer",
                                "requested_level": "standard",
                                "requested_runtime_value": "medium",
                                "status": "runtime-observed",
                                "dispatch_status": "accepted",
                                "telemetry_status": "observed",
                                "worker_ref": "worker-1",
                                "effective_level": "standard",
                                "effective_runtime_value": "medium",
                                "hidden_reasoning": "must not be exposed",
                            }
                        ],
                        "decisions": [],
                        "handoffs": [],
                        "verification": [],
                        "degraded_capabilities": [],
                        "metadata": {},
                    },
                ), patch(
                    "agentcaravan.cli.validate_session_directory",
                    return_value={"valid": True, "task_id": "task-1", "issues": []},
                ):
                    with contextlib.redirect_stdout(output):
                        exit_code = main([
                            "run",
                            "--root", str(root),
                            "--task-id", "task-1",
                            "--objective", "Expose bounded reasoning evidence",
                            "--dry-run",
                        ])

            summary = json.loads(output.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(
                summary["reasoning_evidence"],
                [{
                    "stage_id": "implementation",
                    "role_id": "engineer",
                    "requested_level": "standard",
                    "requested_runtime_value": "medium",
                    "status": "runtime-observed",
                    "dispatch_status": "accepted",
                    "telemetry_status": "observed",
                    "worker_ref": "worker-1",
                }],
            )
            self.assertNotIn("hidden_reasoning", json.dumps(summary))

    def test_dry_run_reports_recovery_action_when_session_validation_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = io.StringIO()
            invalid_report = {
                "valid": False,
                "task_id": "task-1",
                "issues": ["completion.json is invalid"],
            }
            with patch("agentcaravan.cli.resolve_profile", return_value=resolved_codex_profile()):
                with patch("agentcaravan.cli.validate_session_directory", return_value=invalid_report):
                    with contextlib.redirect_stdout(output):
                        exit_code = main([
                            "run",
                            "--root", str(root),
                            "--task-id", "task-1",
                            "--objective", "Demonstrate recovery guidance",
                            "--dry-run",
                        ])

            summary = json.loads(output.getvalue())
            self.assertEqual(exit_code, 1)
            self.assertFalse(summary["session_validation"]["valid"])
            self.assertIn("validate-session --task-id task-1", summary["next_step"])
            self.assertNotIn("agent-caravan-codex-orchestrator", summary["next_step"])

    def test_dry_run_does_not_overwrite_an_existing_run_slot(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            arguments = [
                "run",
                "--root", str(root),
                "--task-id", "task-1",
                "--objective", "Demonstrate retry evidence",
                "--dry-run",
            ]
            with patch("agentcaravan.cli.resolve_profile", return_value=resolved_codex_profile()):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(arguments), 0)

                with self.assertRaisesRegex(SystemExit, "increment --attempt"):
                    main(arguments)

                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main([*arguments, "--attempt", "2"]), 0)

            self.assertTrue((root / "sessions" / "task-1" / "runs" / "task-1-codex-run-1.json").exists())
            self.assertTrue((root / "sessions" / "task-1" / "runs" / "task-1-codex-run-2.json").exists())

    def test_live_run_is_rejected_until_a_live_surface_is_available(self):
        with self.assertRaises(SystemExit):
            main(["run", "--task-id", "task-1", "--objective", "x"])

    def test_validate_session_reports_the_persisted_golden_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch("agentcaravan.cli.resolve_profile", return_value=resolved_codex_profile()):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(
                        main([
                            "run",
                            "--root", str(root),
                            "--task-id", "task-1",
                            "--objective", "Demonstrate the golden path",
                            "--dry-run",
                        ]),
                        0,
                    )
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    exit_code = main(["validate-session", "--root", str(root), "--task-id", "task-1"])

            report = json.loads(output.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertTrue(report["valid"], report)
            self.assertEqual(report["run_ids"], ["task-1-codex-run-1"])

    def test_handoff_exports_and_persists_without_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = io.StringIO()
            with patch("agentcaravan.cli.resolve_profile", return_value=resolved_codex_profile()):
                with contextlib.redirect_stdout(output):
                    exit_code = main([
                        "handoff", "--root", str(root), "--task-id", "task-1",
                        "--objective", "Implement the change",
                        "--requested-action", "Implement and test the change",
                    ])
            self.assertEqual(exit_code, 0)
            result = json.loads(output.getvalue())
            self.assertEqual(result["artifact_type"], "task-handoff")
            self.assertEqual(result["plan_id"], "task-1-execution-plan")
            self.assertEqual(result["status"], "ready")
            self.assertEqual(result["session_validation"]["valid"], True)
            handoff_path = root / "sessions" / "task-1" / "handoffs" / "task-1-handoff-1.json"
            self.assertEqual(Path(result["handoff_path"]), handoff_path)
            self.assertTrue(handoff_path.is_file())
            persisted = json.loads(handoff_path.read_text())
            self.assertEqual(persisted["handoff_id"], result["handoff_id"])
            self.assertEqual(persisted["task_id"], "task-1")
            self.assertEqual(result["selected_context"]["runtime"]["profile_id"], "codex-desktop-information-technology-core-team")


if __name__ == "__main__":
    unittest.main()
