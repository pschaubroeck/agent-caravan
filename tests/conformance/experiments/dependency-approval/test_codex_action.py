"""Exact-action approval checks, native auditing, and failure retention."""

import json
import shlex
import subprocess
import unittest
from datetime import datetime, timedelta, timezone

from codex_action import CodexActionError, CodexApprovedActionRunner, manifest_action


def approval():
    now = datetime.now(timezone.utc)
    pending = {"task_id": "task", "run_id": "run", "session_id": "session", "plan_id": "task-execution-plan",
               "request_id": "request", "action": manifest_action(), "requested_at": (now - timedelta(seconds=20)).isoformat()}
    decision = {key: pending[key] for key in ("task_id", "run_id", "request_id", "action")}
    decision.update(kind="human-approval", source="human-reviewed", status="passed", approved=True,
                    actor="operator", owner_role="program-manager", evidence_id="human-approval-evidence-1",
                    attested_at=(now - timedelta(seconds=10)).isoformat(), references=["controller-request:request"])
    return pending, decision


class CodexActionTests(unittest.TestCase):
    def invoke(self, pending, decision, *, fail=False):
        self.calls = []

        def run(argv, **kwargs):
            self.calls.append((argv, kwargs))
            return subprocess.CompletedProcess(argv, 1 if fail else 0, "", "private diagnostic")

        return CodexApprovedActionRunner(cwd=".", model="gpt-6.1-sol", run=run).execute(pending, decision)

    def test_scoped_approval_dispatches_only_exact_controller_argv(self):
        pending, decision = approval()
        result = self.invoke(pending, decision)
        self.assertEqual(result["enforcement"], "external-controller-before-dispatch")
        self.assertEqual(result["external_decision"]["decided_at"], decision["attested_at"])
        self.assertEqual(self.calls[-1][0], shlex.split(manifest_action()))
        self.assertIs(self.calls[-1][1]["shell"], False)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(result["execution_method"], "controller-direct-argv")
        self.assertNotIn("native_thread_id", result)
        self.assertNotIn("native_jsonl_events", result)
        self.assertNotIn("private diagnostic", json.dumps(result))

    def test_invalid_approval_never_invokes_cli(self):
        for field, value in (("action", "other command"), ("run_id", "other-run"), ("source", "reported-by-codex"),
                             ("approved", False), ("references", []), ("attested_at", "2000-01-01T00:00:00+00:00")):
            pending, decision = approval()
            decision[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.invoke(pending, decision)
            self.assertEqual(self.calls, [])

    def test_nonexperiment_action_never_dispatches(self):
        pending, decision = approval()
        pending["action"] = decision["action"] = "another write"
        with self.assertRaises(ValueError):
            self.invoke(pending, decision)
        self.assertEqual(self.calls, [])

    def test_failed_command_preserves_bounded_evidence(self):
        pending, decision = approval()
        with self.assertRaises(CodexActionError) as error:
            self.invoke(pending, decision, fail=True)
        self.assertEqual(error.exception.receipt["status"], "failed")
        self.assertEqual(error.exception.receipt["command_exit_code"], 1)
        self.assertEqual(error.exception.receipt["command_argv"], shlex.split(manifest_action()))

    def test_timeout_retains_indeterminate_receipt(self):
        pending, decision = approval()
        def run(argv, **kwargs):
            raise subprocess.TimeoutExpired(argv, 1, output="private diagnostic")
        with self.assertRaises(CodexActionError) as error:
            CodexApprovedActionRunner(cwd=".", model="gpt-6.1-sol", run=run).execute(pending, decision)
        self.assertEqual(error.exception.receipt["status"], "indeterminate-post-dispatch")
        self.assertNotIn("private diagnostic", json.dumps(error.exception.receipt))


if __name__ == "__main__":
    unittest.main()
