"""Focused approval-gate checks with a recorded v1.18.33 event shape."""

import unittest
from datetime import datetime, timezone

from agentcaravan.adapters.opencode_execution_surface import OpenCodeExecutionRequest
from agentcaravan.adapters.opencode_server_surface import (
    ApprovalDecision,
    OpenCodeServerApprovalSurface,
    OpenCodeServerSurfaceError,
)


ACTION = "python3 -m pip install --no-deps jsonschema==4.25.1"
POLICY = {"*": "deny", "read": "allow", "glob": "allow", "grep": "allow", "list": "allow", "bash": "ask"}


def event(kind, props, number):
    return {"id": f"evt-{number}", "type": kind, "properties": props}


class FakeTransport:
    def __init__(self, *, events=None, policy=POLICY):
        self.calls = []
        self.policy = policy
        self.event_list = events or [
            event("server.connected", {}, 0),
            event("permission.asked", {
                "id": "per-1", "sessionID": "ses-1", "permission": "bash",
                "patterns": ["python3 -m pip install*"],
                "metadata": {"command": ACTION},
                "tool": {"messageID": "msg-1", "callID": "call-1"},
            }, 1),
            event("permission.replied", {"sessionID": "ses-1", "requestID": "per-1", "reply": "once"}, 2),
            event("message.part.updated", {
                "sessionID": "ses-1",
                "part": {"type": "tool", "callID": "call-1", "state": {"status": "completed", "input": {"command": ACTION}}},
            }, 3),
            event("session.status", {"sessionID": "ses-1", "status": {"type": "idle"}}, 4),
        ]

    def get(self, path):
        self.calls.append(("GET", path))
        if path == "/global/health":
            return {"healthy": True, "version": "1.18.33"}
        if path == "/config":
            return {"agent": {"experiment": {"permission": self.policy}}}
        raise AssertionError(path)

    def post(self, path, body):
        self.calls.append(("POST", path, body))
        if path == "/session":
            return {"id": "ses-1"}
        if path.endswith("/prompt_async"):
            return None
        if "/permissions/" in path or path.endswith("/abort"):
            return True
        raise AssertionError(path)

    def events(self):
        self.calls.append(("GET", "/event"))
        return iter(self.event_list)


class ServerApprovalSurfaceTests(unittest.TestCase):
    def setUp(self):
        self.request = OpenCodeExecutionRequest(
            scenario={"id": "dependency-approval-accept"},
            prepared={"plan": {"id": "plan-1"}},
            projection={},
            records={
                "task": {"task_id": "task-1"},
                "session": {"session_id": "portable-session-1"},
                "run": {"run_id": "run-1"},
            },
        )

    def decision(self, observed, *, approved=True, action=ACTION):
        return ApprovalDecision(
            task_id=observed["task_id"], run_id=observed["run_id"],
            session_id=observed["session_id"], permission_id=observed["permission_id"],
            action=action, approved=approved, actor="named-human-1",
            decided_at=datetime.now(timezone.utc).isoformat(), evidence_id="human-decision-1",
        )

    def surface(self, transport, decide):
        return OpenCodeServerApprovalSurface(
            transport=transport, model="openai/gpt-6-luna", agent="experiment",
            action=ACTION, decide=decide,
        )

    def test_server_approvals_are_disabled_before_transport_or_decision(self):
        transport = FakeTransport()
        decision_calls = []

        def decide(observed):
            decision_calls.append(observed)
            return self.decision(observed)

        with self.assertRaisesRegex(OpenCodeServerSurfaceError, "approvals are disabled"):
            self.surface(transport, decide)

        self.assertEqual(transport.calls, [])
        self.assertEqual(decision_calls, [])


if __name__ == "__main__":
    unittest.main()
