import json
import subprocess
import unittest

from agentcaravan.adapters.codex_cli_surface import CodexCliExecutionSurface, CodexCliSurfaceError
from agentcaravan.adapters.codex_execution_surface import CodexExecutionRequest


def normalized_result():
    return {
        "artifact_type": "normalized-execution-result",
        "version": "1.0.0",
        "task_id": "task-1",
        "plan_id": "plan-1",
        "status": "completed",
        "active_roles": ["engineer"],
        "completed_stages": ["implementation"],
        "decisions": [],
        "execution_realization": {"mode": "native-sequential", "native_subagents": False, "parallel_lane_ids": []},
        "role_turns": [],
        "handoffs": [],
        "approvals": [],
        "artifacts": [{"kind": "dependency-manifest", "status": "modified", "source": "independently-verified"}],
        "evidence": [{"kind": "review", "status": "passed", "source": "human-reviewed"}],
        "verification": [{"kind": "test", "status": "passed", "source": "independently-verified"}],
        "failures": [],
        "retries": [],
        "idempotency_records": [],
        "degraded_capabilities": [],
        "unresolved_conditions": [],
    }


def jsonl(result=None):
    result = normalized_result() if result is None else result
    events = [
        {"type": "thread.started", "thread_id": "thread-123"},
        {"type": "item.completed", "item": {"type": "agent_message", "text": json.dumps(result)}},
        {"type": "turn.completed"},
    ]
    return "\n".join(json.dumps(event) for event in events) + "\n"


class CodexCliSurfaceTests(unittest.TestCase):
    def setUp(self):
        self.request = CodexExecutionRequest(
            scenario={"id": "case-a", "task": {"objective": "inspect"}, "expected": {"secret": "must-not-leak"}},
            prepared={"plan": {"id": "plan-1", "task": {"task_id": "task-1", "objective": "inspect"}}},
            brief={"artifact_type": "codex-execution-brief", "instructions": ["Be concise"]},
            records={"task": {"task_id": "task-1"}, "session": {"session_id": "session-1"}, "run": {"run_id": "run-1"}},
        )

    def test_uses_direct_argv_and_excludes_expected(self):
        observed = {}

        def run(argv, **kwargs):
            observed["argv"] = argv
            observed["kwargs"] = kwargs
            return subprocess.CompletedProcess(argv, 0, jsonl(), "")

        result = CodexCliExecutionSurface(cwd="/repo", run=run).execute(self.request)
        argv = observed["argv"]
        self.assertEqual(argv[:6], ["codex", "exec", "--json", "--sandbox", "read-only", "--output-schema"])
        self.assertEqual(argv[-1], "-")
        self.assertEqual(observed["kwargs"]["cwd"], "/repo")
        self.assertEqual(observed["kwargs"]["input"].count("must-not-leak"), 0)
        self.assertEqual(observed["kwargs"]["shell"] if "shell" in observed["kwargs"] else False, False)
        self.assertEqual(result["metadata"]["codex_cli"]["thread_id"], "thread-123")

    def test_prompt_supplies_validated_result_contract(self):
        prompt = CodexCliExecutionSurface._build_prompt(self.request)
        payload = json.loads(prompt[prompt.index("\n") + 1:])
        self.assertEqual(set(payload["required_result_fields"]), set(normalized_result()))
        schema = payload["result_contract_schema"]
        self.assertEqual(set(schema["$defs"]["normalizedExecutionResult"]["required"]), set(normalized_result()))
        self.assertIn("native-sequential", schema["$defs"]["executionRealization"]["properties"]["mode"]["enum"])
        self.assertNotIn("expected", payload)

    def test_preserves_native_events_and_demotes_unverified_provenance(self):
        result = CodexCliExecutionSurface(cwd="/repo", run=lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, jsonl(), "")).execute(self.request)
        metadata = result["metadata"]["codex_cli"]
        self.assertEqual(len(metadata["native_jsonl_events"]), 3)
        self.assertEqual(metadata["final_result_provenance"], "reported-by-codex")
        self.assertIsNone(metadata["model_identity"])
        self.assertFalse(metadata["human_reviewed"])
        self.assertFalse(metadata["independently_verified"])
        self.assertEqual(result["artifacts"][0]["source"], "reported-by-codex")
        self.assertEqual(result["verification"][0]["source"], "reported-by-codex")
        self.assertEqual(result["evidence"][0]["source"], "reported-by-codex")

    def test_pins_requested_model_without_claiming_observed_identity(self):
        calls = []

        def run(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, jsonl(), "")

        result = CodexCliExecutionSurface(cwd="/repo", model="gpt-6.1-sol", run=run).execute(self.request)
        self.assertEqual(calls[0][2:4], ["--model", "gpt-6.1-sol"])
        self.assertEqual(result["metadata"]["codex_cli"]["requested_model"], "gpt-6.1-sol")
        self.assertIsNone(result["metadata"]["codex_cli"]["model_identity"])
        for invalid in ("", "model with spaces", 42):
            with self.assertRaises(CodexCliSurfaceError):
                CodexCliExecutionSurface(cwd="/repo", model=invalid)

    def test_noninteractive_workspace_write_fails_closed_even_with_approval_record(self):
        invoked = []
        with self.assertRaisesRegex(CodexCliSurfaceError, "noninteractive Codex CLI surface"):
            CodexCliExecutionSurface(
                cwd="/repo",
                sandbox="workspace-write",
                approval_record=self.approval_record(),
                run=lambda argv, **_kwargs: (
                    invoked.append(True),
                    subprocess.CompletedProcess(argv, 0, jsonl(), ""),
                )[1],
            )
        self.assertEqual(invoked, [])

    def approval_record(self):
        return {
            "approval_id": "approval-1",
            "status": "approved",
            "sandbox": "workspace-write",
            "decision_maker": "operator",
            "request_identity": {
                "scenario_id": "case-a",
                "task_id": "task-1",
                "plan_id": "plan-1",
                "run_id": "run-1",
            },
        }

    def test_rejects_unsupported_sandbox(self):
        with self.assertRaisesRegex(CodexCliSurfaceError, "unsupported Codex sandbox"):
            CodexCliExecutionSurface(cwd="/repo", sandbox="danger-full-access")

    def test_successful_jsonl_result_must_match_request_identity(self):
        result = CodexCliExecutionSurface(cwd="/repo", run=lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, jsonl(), "")).execute(self.request)
        self.assertEqual(result["task_id"], "task-1")
        bad = normalized_result()
        bad["task_id"] = "another-task"
        surface = CodexCliExecutionSurface(cwd="/repo", run=lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, jsonl(bad), ""))
        with self.assertRaisesRegex(CodexCliSurfaceError, "identity"):
            surface.execute(self.request)

    def test_decodes_strict_cli_result_json_envelope(self):
        envelope = {"result_json": json.dumps(normalized_result())}
        surface = CodexCliExecutionSurface(
            cwd="/repo",
            run=lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, jsonl(envelope), ""),
        )

        result = surface.execute(self.request)

        self.assertEqual(result["artifact_type"], "normalized-execution-result")
        self.assertEqual(result["task_id"], "task-1")

    def test_fails_closed_for_malformed_jsonl(self):
        surface = CodexCliExecutionSurface(cwd="/repo", run=lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "not json\n", ""))
        with self.assertRaisesRegex(CodexCliSurfaceError, "malformed Codex JSONL"):
            surface.execute(self.request)

    def test_fails_closed_for_nonzero_exit(self):
        surface = CodexCliExecutionSurface(cwd="/repo", run=lambda *_args, **_kwargs: subprocess.CompletedProcess([], 1, jsonl(), "failed"))
        with self.assertRaisesRegex(CodexCliSurfaceError, "exited with status 1: failed"):
            surface.execute(self.request)

    def test_preserves_exit_diagnostics_when_nonzero_stdout_is_malformed(self):
        surface = CodexCliExecutionSurface(
            cwd="/repo",
            run=lambda *_args, **_kwargs: subprocess.CompletedProcess([], 1, "not json\\n", "failed"),
        )
        with self.assertRaisesRegex(CodexCliSurfaceError, "exited with status 1: failed"):
            surface.execute(self.request)

    def test_fails_closed_when_structured_result_is_missing(self):
        stdout = "\n".join([
            json.dumps({"type": "thread.started", "thread_id": "thread-123"}),
            json.dumps({"type": "turn.completed"}),
        ])
        surface = CodexCliExecutionSurface(cwd="/repo", run=lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, stdout, ""))
        with self.assertRaisesRegex(CodexCliSurfaceError, "final structured result"):
            surface.execute(self.request)

    def test_fails_closed_on_timeout(self):
        def run(*_args, **_kwargs):
            raise subprocess.TimeoutExpired("codex", 1)

        surface = CodexCliExecutionSurface(cwd="/repo", run=run)
        with self.assertRaisesRegex(CodexCliSurfaceError, "timed out"):
            surface.execute(self.request)


if __name__ == "__main__":
    unittest.main()
