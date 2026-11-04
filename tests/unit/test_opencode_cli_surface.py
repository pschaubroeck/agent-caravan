import json
import subprocess
import unittest

from agentcaravan.adapters.opencode_cli_surface import (
    OpenCodeCliExecutionSurface,
    OpenCodeCliSurfaceError,
)
from agentcaravan.adapters.opencode_execution_surface import OpenCodeExecutionRequest


def result():
    return {
        "artifact_type": "normalized-execution-result",
        "version": "1.0.0",
        "task_id": "task-1",
        "plan_id": "plan-1",
        "status": "completed",
        "active_roles": [],
        "completed_stages": [],
        "decisions": [],
        "execution_realization": {"mode": "native-sequential", "native_subagents": False, "parallel_lane_ids": []},
        "role_turns": [],
        "handoffs": [],
        "approvals": [],
        "artifacts": [],
        "evidence": [{"source": "human-reviewed"}],
        "verification": [],
        "failures": [],
        "retries": [],
        "idempotency_records": [],
        "degraded_capabilities": [],
        "unresolved_conditions": [],
    }


def events(payload=None):
    data = json.dumps(result() if payload is None else payload)
    return json.dumps({"type": "text", "sessionID": "ses-1", "part": {"type": "text", "text": data}}) + "\n"


def effective_config():
    permission = OpenCodeCliExecutionSurface._READ_ONLY_PERMISSION
    return json.dumps({
        "permission": permission,
        "default_agent": "agentcaravan-readonly",
        "agent": {"agentcaravan-readonly": {"mode": "primary", "permission": permission}},
    })


class OpenCodeCliSurfaceTests(unittest.TestCase):
    def setUp(self):
        self.request = OpenCodeExecutionRequest(
            scenario={"id": "case-1", "task": {"objective": "inspect"}, "expected": "never expose"},
            prepared={"plan": {"id": "plan-1"}},
            projection={"instructions": ["inspect"]},
            records={"task": {"task_id": "task-1"}, "session": {"session_id": "s-1"}, "run": {"run_id": "r-1"}},
        )

    def test_direct_argv_permissions_and_native_event_receipt(self):
        calls = []

        def run(argv, **kwargs):
            calls.append((argv, kwargs))
            stdout = (
                "1.18.33\n" if argv[1] == "--version"
                else effective_config() if argv[1:3] == ["debug", "config"]
                else events()
            )
            return subprocess.CompletedProcess(argv, 0, stdout, "")

        output = OpenCodeCliExecutionSurface(cwd="/repo", model="openai/gpt-6-luna", run=run).execute(self.request)
        self.assertEqual(calls[2][0][:8], ["opencode", "--pure", "run", "--agent", "agentcaravan-readonly", "--format", "json", "--model"])
        self.assertNotIn("never expose", calls[2][0][-1])
        config = json.loads(calls[2][1]["env"]["OPENCODE_CONFIG_CONTENT"])
        self.assertEqual(config["permission"]["edit"], "deny")
        self.assertEqual(config["permission"]["bash"], "deny")
        self.assertEqual(config["permission"]["task"], "deny")
        self.assertEqual(output["metadata"]["opencode_cli"]["version"], "1.18.33")
        self.assertEqual(output["metadata"]["opencode_cli"]["session_id"], "ses-1")
        self.assertEqual(output["evidence"][0]["source"], "reported-by-opencode")

    def test_write_mode_fails_closed(self):
        with self.assertRaisesRegex(OpenCodeCliSurfaceError, "read-only"):
            OpenCodeCliExecutionSurface(cwd="/repo", model="openai/gpt-6-luna", mode="workspace-write")

    def test_unsupported_version_fails_before_run(self):
        calls = []

        def run(argv, **_kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, "1.18.25\n", "")

        surface = OpenCodeCliExecutionSurface(cwd="/repo", model="openai/gpt-6-luna", run=run)
        with self.assertRaisesRegex(OpenCodeCliSurfaceError, "unsupported OpenCode version"):
            surface.execute(self.request)
        self.assertEqual(len(calls), 1)

    def test_unsubstantiated_approval_is_rejected(self):
        payload = result()
        payload["approvals"] = [{"status": "approved"}]

        def run(argv, **_kwargs):
            stdout = "1.18.33\n" if argv[1] == "--version" else events(payload)
            if argv[1:3] == ["debug", "config"]:
                stdout = effective_config()
            return subprocess.CompletedProcess(argv, 0, stdout, "")

        surface = OpenCodeCliExecutionSurface(cwd="/repo", model="openai/gpt-6-luna", run=run)
        with self.assertRaisesRegex(OpenCodeCliSurfaceError, "approvals"):
            surface.execute(self.request)

    def test_model_report_cannot_supply_unobserved_execution_events_or_worker_turns(self):
        for field, claim in (
            ("execution_events", [{"kind": "approval", "status": "approved"}]),
            ("role_turns", [{"role_id": "reviewer", "worker_ref": "claimed-child"}]),
            ("handoffs", [{"from": "engineer", "to": "reviewer", "status": "completed"}]),
        ):
            with self.subTest(field=field):
                payload = result()
                payload[field] = claim

                def run(argv, **_kwargs):
                    stdout = "1.18.33\n" if argv[1] == "--version" else events(payload)
                    if argv[1:3] == ["debug", "config"]:
                        stdout = effective_config()
                    return subprocess.CompletedProcess(argv, 0, stdout, "")

                surface = OpenCodeCliExecutionSurface(cwd="/repo", model="openai/gpt-6-luna", run=run)
                with self.assertRaisesRegex(OpenCodeCliSurfaceError, field):
                    surface.execute(self.request)

    def test_model_report_cannot_supply_native_delegation(self):
        payload = result()
        payload["execution_realization"] = {
            "mode": "native-sequential", "native_subagents": True, "parallel_lane_ids": []
        }

        def run(argv, **_kwargs):
            stdout = "1.18.33\n" if argv[1] == "--version" else events(payload)
            if argv[1:3] == ["debug", "config"]:
                stdout = effective_config()
            return subprocess.CompletedProcess(argv, 0, stdout, "")

        surface = OpenCodeCliExecutionSurface(cwd="/repo", model="openai/gpt-6-luna", run=run)
        with self.assertRaisesRegex(OpenCodeCliSurfaceError, "native delegation"):
            surface.execute(self.request)


if __name__ == "__main__":
    unittest.main()
