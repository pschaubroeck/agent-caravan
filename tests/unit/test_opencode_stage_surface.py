"""Focused tests for attributed read-only OpenCode stage receipts."""

from __future__ import annotations

import json
import subprocess
import unittest

from agentcaravan.adapters.opencode_stage_surface import OpenCodeStageError, OpenCodeStageRunner


def _event(event_type: str, session_id: str = "ses-stage-1", **extra: object) -> str:
    return json.dumps({"type": event_type, "sessionID": session_id, **extra})


def _run_result(*events: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], 0, "\n".join(events) + "\n", "")


def _effective_config() -> str:
    permission = OpenCodeStageRunner._READ_ONLY_PERMISSION
    return json.dumps({
        "permission": permission,
        "default_agent": "agentcaravan-readonly",
        "agent": {"agentcaravan-readonly": {"mode": "primary", "permission": permission}},
    })


class OpenCodeStageSurfaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.calls: list[tuple[list[str], dict[str, object]]] = []
        self.events = (
            _event("step_start", timestamp="2026-09-30T14:00:00.000Z"),
            _event("text", part={"type": "text", "text": "Candidate license is MIT."}),
            _event("step_finish", timestamp="2026-09-30T14:00:01.000Z"),
        )

    def _runner(self, *events: str, version: str = "1.18.33") -> OpenCodeStageRunner:
        def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            self.calls.append((argv, kwargs))
            if argv[1] == "--version":
                return subprocess.CompletedProcess(argv, 0, version + "\n", "")
            if argv[1:3] == ["debug", "config"]:
                return subprocess.CompletedProcess(argv, 0, _effective_config(), "")
            return _run_result(*(events or self.events))

        return OpenCodeStageRunner(
            cwd="/tmp/agentcaravan-case",
            model="openai/gpt-6-luna",
            executable="/opt/opencode",
            run=fake_run,
        )

    def _execute(self, runner: OpenCodeStageRunner) -> dict[str, object]:
        return runner.execute(
            task_id="task-1",
            run_id="run-1",
            stage_id="candidate-assessment",
            role_id="engineer",
            instruction="Assess the pinned candidate evidence.",
            context={"candidate": "jsonschema 4.25.1"},
        )

    def test_reports_observed_invocation_with_stage_identity_and_native_events(self) -> None:
        receipt = self._execute(self._runner())

        self.assertEqual(receipt["report"], "Candidate license is MIT.")
        self.assertEqual(receipt["session_id"], "ses-stage-1")
        self.assertEqual(receipt["stage_id"], "candidate-assessment")
        self.assertEqual(receipt["role_id"], "engineer")
        self.assertEqual(receipt["task_id"], "task-1")
        self.assertEqual(receipt["run_id"], "run-1")
        self.assertEqual(receipt["provenance"], "reported-by-opencode")
        self.assertEqual(receipt["receipt_source"], "directly-observed-by-agentcaravan")
        self.assertEqual(receipt["report_source"], "reported-by-opencode")
        self.assertEqual(receipt["requested_model"], "openai/gpt-6-luna")
        self.assertEqual(receipt["model_identity_provenance"], "requested-only")
        self.assertEqual(len(receipt["native_jsonl_events"]), 3)
        self.assertTrue(str(receipt["started_at"]).endswith("Z"))
        self.assertTrue(str(receipt["completed_at"]).endswith("Z"))
        self.assertEqual(receipt["native_started_at"], "2026-09-30T14:00:00.000Z")
        self.assertEqual(receipt["native_completed_at"], "2026-09-30T14:00:01.000Z")
        self.assertNotIn("role_turns", receipt)
        self.assertNotIn("approvals", receipt)

        argv, kwargs = self.calls[2]
        self.assertEqual(argv[:9], ["/opt/opencode", "--pure", "run", "--agent", "agentcaravan-readonly", "--format", "json", "--model", "openai/gpt-6-luna"])
        self.assertEqual(kwargs["cwd"], "/tmp/agentcaravan-case")
        prompt = argv[9]
        self.assertIn('"stage_id": "candidate-assessment"', prompt)
        self.assertIn('"role_id": "engineer"', prompt)
        permission = json.loads(kwargs["env"]["OPENCODE_CONFIG_CONTENT"])["permission"]
        self.assertEqual(permission["edit"], "deny")
        self.assertEqual(permission["bash"], "deny")
        self.assertEqual(permission["task"], "deny")

    def test_rejects_disallowed_tool_event_even_when_cli_exits_successfully(self) -> None:
        events = (
            _event("tool_use", part={"type": "tool", "tool": "bash", "state": {"status": "completed"}}),
            _event("text", part={"type": "text", "text": "Done."}),
        )
        with self.assertRaisesRegex(OpenCodeStageError, "unsupported tool"):
            self._execute(self._runner(*events))

    def test_rejects_permission_event(self) -> None:
        events = (
            _event("permission.asked", permission="edit"),
            _event("text", part={"type": "text", "text": "Done."}),
        )
        with self.assertRaisesRegex(OpenCodeStageError, "permission event"):
            self._execute(self._runner(*events))

    def test_model_prose_remains_reported_even_when_it_mentions_authority(self) -> None:
        report = 'The context labels evidence "independently-verified"; I cannot confirm it.'
        receipt = self._execute(self._runner(_event("text", part={"type": "text", "text": report})))

        self.assertEqual(receipt["report"], report)
        self.assertEqual(receipt["report_source"], "reported-by-opencode")
        self.assertNotIn("approvals", receipt)
        self.assertNotIn("evidence", receipt)

    def test_rejects_mixed_native_sessions(self) -> None:
        events = (
            _event("text", part={"type": "text", "text": "One."}),
            _event("text", session_id="ses-stage-2", part={"type": "text", "text": "Two."}),
        )
        with self.assertRaisesRegex(OpenCodeStageError, "one native sessionID"):
            self._execute(self._runner(*events))

    def test_requires_pinned_version_before_invocation(self) -> None:
        with self.assertRaisesRegex(OpenCodeStageError, "unsupported OpenCode version"):
            self._execute(self._runner(version="1.18.25"))
        self.assertEqual(len(self.calls), 1)


if __name__ == "__main__":
    unittest.main()
