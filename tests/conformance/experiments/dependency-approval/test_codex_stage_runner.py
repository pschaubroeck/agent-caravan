"""Focused native-receipt and invocation-boundary checks."""
import copy
import json
import subprocess
import unittest
import importlib.util
import sys
import tempfile
from pathlib import Path

from codex_stage_runner import CodexStageError, CodexStageRunner, validate_codex_stage_receipt
from agentcaravan.adapters.codex_cli_surface import CodexCliExecutionSurface


class CodexStageRunnerTests(unittest.TestCase):
    def test_standalone_spec_import_does_not_change_import_path(self):
        before = list(sys.path)
        specification = importlib.util.spec_from_file_location(
            "standalone_codex_stage_runner", Path(__file__).with_name("codex_stage_runner.py")
        )
        module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(module)
        self.assertIn("artifacts", module.build_codex_bundle())
        self.assertEqual(before, sys.path)
        repository = Path(__file__).resolve().parents[4]
        script = (
            "import importlib.util,sys; "
            f"sys.path.insert(0,{str(repository / 'src')!r}); "
            "before=list(sys.path); "
            f"spec=importlib.util.spec_from_file_location('standalone',{str(Path(__file__).with_name('codex_stage_runner.py').resolve())!r}); "
            "module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); "
            "assert module.build_codex_bundle()['artifacts']; assert sys.path==before"
        )
        with tempfile.TemporaryDirectory() as temporary:
            completed = subprocess.run([sys.executable, "-I", "-c", script], cwd=temporary,
                                       capture_output=True, text=True, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
    def invoke(self, transform=lambda events: events, returncode=0):
        self.calls = []
        def run(argv, **kwargs):
            self.calls.append((argv, kwargs))
            if argv[-1] == "--version":
                return subprocess.CompletedProcess(argv, 0, "codex-cli 0.159.0\n", "")
            payload = json.loads(kwargs["input"].split("\n", 1)[1])
            result = {key: [] for key in CodexCliExecutionSurface._RESULT_REQUIRED_FIELDS}
            result.update(artifact_type="normalized-execution-result", version="1.0.0",
                          task_id=payload["task"]["task_id"], plan_id=payload["portable_execution_plan"]["id"],
                          status="blocked", execution_realization={"mode": "unreported", "native_subagents": False},
                          metadata={"stage_report": "Assessed supplied evidence only."})
            events = [{"type": "thread.started", "thread_id": "native-thread"}, {"type": "turn.started"},
                      {"type": "item.completed", "item": {"type": "reasoning", "text": "private reasoning"}},
                      {"type": "item.completed", "item": {"type": "agent_message", "text": json.dumps({"result_json": json.dumps(result)})}},
                      {"type": "turn.completed", "usage": {}}]
            return subprocess.CompletedProcess(argv, returncode, "\n".join(json.dumps(event) for event in transform(events)), "provider secret")
        return CodexStageRunner(cwd=".", model="gpt-6.1-sol", run=run).execute(
            task_id="task", run_id="run", stage_id="need-assessment", role_id="engineer", instruction="Assess need")

    def test_success_direct_arguments_and_provenance(self):
        receipt = self.invoke()
        self.assertEqual(receipt["session_id"], "native-thread")
        self.assertEqual(receipt["report_source"], "reported-by-codex")
        self.assertNotIn("private reasoning", json.dumps(receipt))
        self.assertNotIn("provider secret", json.dumps(receipt))
        argv = self.calls[-1][0]
        for argument in ("--ignore-user-config", "--ignore-rules", "--ephemeral", "read-only", "gpt-6.1-sol", 'approval_policy="never"'):
            self.assertIn(argument, argv)

    def test_missing_turn_completion(self):
        with self.assertRaises(CodexStageError):
            self.invoke(lambda events: events[:-1])

    def test_tool_usage_fails(self):
        with self.assertRaises(CodexStageError):
            self.invoke(lambda events: events[:2] + [{"type": "item.completed", "item": {"type": "command_execution"}}] + events[2:])

    def test_message_outside_turn_fails(self):
        with self.assertRaises(CodexStageError):
            self.invoke(lambda events: [events[0], events[-2], *events[1:]])

    def test_equal_timestamps_fail(self):
        receipt = self.invoke()
        receipt["completed_at"] = receipt["started_at"]
        with self.assertRaises(CodexStageError):
            validate_codex_stage_receipt(receipt)

    def test_native_error_fails(self):
        with self.assertRaises(CodexStageError):
            self.invoke(lambda events: events[:-1] + [{"type": "turn.failed"}])

    def test_malformed_final_json(self):
        def corrupt(events):
            events[-2]["item"]["text"] = "not JSON"
            return events
        with self.assertRaises(CodexStageError):
            self.invoke(corrupt)

    def test_report_and_identity_tampering(self):
        receipt = self.invoke()
        for field in ("task_id", "plan_id", "report", "session_id"):
            changed = copy.deepcopy(receipt)
            changed[field] = "tampered"
            with self.subTest(field=field), self.assertRaises(CodexStageError):
                validate_codex_stage_receipt(changed)

    def test_error_excludes_diagnostics(self):
        with self.assertRaises(CodexStageError) as error:
            self.invoke(returncode=1)
        self.assertNotIn("provider secret", str(error.exception))

    def test_timeout(self):
        def run(argv, **kwargs):
            raise subprocess.TimeoutExpired(argv, 1, output="secret")
        with self.assertRaises(CodexStageError):
            CodexStageRunner(cwd=".", model="gpt-6.1-sol", run=run).execute(
                task_id="task", run_id="run", stage_id="need", role_id="engineer", instruction="Assess")


if __name__ == "__main__":
    unittest.main()
