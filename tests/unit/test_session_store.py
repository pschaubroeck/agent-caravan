import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from agentcaravan.session_store import LocalJsonExecutionStore, SessionStoreError
from agentcaravan.session_validation import validate_session_directory


def valid_records():
    return {
        "task": {
            "task_id": "task-1",
            "objective": "Test persisted evidence",
            "selected_context": {},
            "plan": [{"plan_id": "plan-1", "status": "validated"}],
            "decisions": [],
            "evidence": [],
            "approvals": [],
            "blockers": [],
            "artifacts": [],
            "status": "active",
        },
        "session": {
            "session_id": "session-1",
            "task_id": "task-1",
            "selected_context": {},
            "status": "active",
            "started_at": "2026-08-24T00:00:00Z",
            "ended_at": None,
        },
        "run": {
            "run_id": "run-1",
            "session_id": "session-1",
            "task_id": "task-1",
            "execution_profile_id": "profile-1",
            "status": "active",
            "started_at": "2026-08-24T00:00:00Z",
            "ended_at": None,
            "attempt": 1,
            "handoffs": [{
                "handoff_id": "handoff-1",
                "task_id": "task-1",
                "sender_role": "tech-owner",
                "receiver_role": "engineer",
                "objective": "Implement the approved change",
                "requested_action": "Implement the approved change",
                "inputs": [],
                "expected_outputs": [],
                "validation": {},
                "status": "completed",
            }],
        },
    }


def valid_completion():
    return {
        "artifact_type": "normalized-execution-result",
        "version": "1.0.0",
        "task_id": "task-1",
        "plan_id": "plan-1",
        "status": "completed",
        "execution_realization": {"mode": "simulated-sequential", "native_subagents": False},
        "active_roles": [],
        "completed_stages": [],
        "unresolved_conditions": [],
        "degraded_capabilities": [],
        "handoffs": [],
        "approvals": [],
        "artifacts": [],
        "evidence": [],
        "failures": [],
        "retries": [],
        "decisions": [],
        "role_turns": [],
        "verification": [],
        "idempotency_records": [],
    }


class SessionStoreTests(unittest.TestCase):
    def test_writes_task_session_run_and_completion_records(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = LocalJsonExecutionStore(temporary)
            records = valid_records()
            completion = valid_completion()

            store.write_records("task-1", records)
            store.write_completion("task-1", completion)

            task_root = Path(temporary) / "task-1"
            self.assertEqual(json.loads((task_root / "task.json").read_text())["task_id"], "task-1")
            self.assertEqual(json.loads((task_root / "session.json").read_text())["session_id"], "session-1")
            self.assertEqual(json.loads((task_root / "runs" / "run-1.json").read_text())["run_id"], "run-1")
            self.assertEqual(json.loads((task_root / "completion.json").read_text())["status"], "completed")
            self.assertTrue((task_root / "handoffs" / "handoff-1.json").exists())
            report = validate_session_directory(temporary, "task-1")
            self.assertTrue(report["valid"], report)

    def test_rejects_incoherent_record_identity(self):
        store = LocalJsonExecutionStore("/tmp/agentcaravan-test-sessions")
        records = valid_records()
        records["run"]["session_id"] = "different-session"
        with self.assertRaises(SessionStoreError):
            store.write_records("task-1", records)

    def test_allows_lifecycle_updates_with_stable_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = LocalJsonExecutionStore(temporary)
            records = valid_records()
            store.write_records("task-1", records)

            records["task"]["status"] = "completed"
            records["session"]["status"] = "completed"
            records["run"]["status"] = "completed"
            store.write_records("task-1", records)

            task_root = Path(temporary) / "task-1"
            self.assertEqual(json.loads((task_root / "task.json").read_text())["status"], "completed")
            self.assertEqual(json.loads((task_root / "runs" / "run-1.json").read_text())["status"], "completed")

    def test_rejects_divergent_duplicate_handoff_ids_before_writing(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = LocalJsonExecutionStore(temporary)
            records = valid_records()
            duplicate = deepcopy(records["run"]["handoffs"][0])
            duplicate["objective"] = "A divergent objective"
            records["task"]["handoffs"] = [duplicate]

            with self.assertRaisesRegex(SessionStoreError, "divergent handoff payloads"):
                store.write_records("task-1", records)

            self.assertFalse((Path(temporary) / "task-1").exists())

    def test_rejects_divergent_existing_handoff_payload(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = LocalJsonExecutionStore(temporary)
            store.write_records("task-1", valid_records())
            records = valid_records()
            records["run"]["handoffs"][0]["objective"] = "A divergent objective"

            with self.assertRaisesRegex(SessionStoreError, "existing handoff handoff-1"):
                store.write_records("task-1", records)

            run = json.loads((Path(temporary) / "task-1" / "runs" / "run-1.json").read_text())
            self.assertEqual(run["handoffs"][0]["objective"], "Implement the approved change")

    def test_rejects_divergent_completion_payload(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = LocalJsonExecutionStore(temporary)
            store.write_completion("task-1", valid_completion())
            completion = valid_completion()
            completion["unresolved_conditions"] = ["new condition"]

            with self.assertRaisesRegex(SessionStoreError, "existing completion"):
                store.write_completion("task-1", completion)

            persisted = json.loads((Path(temporary) / "task-1" / "completion.json").read_text())
            self.assertEqual(persisted["unresolved_conditions"], [])

    def test_rejects_divergent_completion_for_the_same_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = LocalJsonExecutionStore(temporary)
            completion = valid_completion()
            completion["metadata"] = {"execution_records": {"run": {"run_id": "run-1"}}}
            store.write_completion("task-1", completion)
            divergent = deepcopy(completion)
            divergent["unresolved_conditions"] = ["new condition"]

            with self.assertRaisesRegex(SessionStoreError, "existing completion"):
                store.write_completion("task-1", divergent)

    def test_allows_divergent_completion_for_a_distinct_retry_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = LocalJsonExecutionStore(temporary)
            completion = valid_completion()
            completion["metadata"] = {"execution_records": {"run": {"run_id": "run-1"}}}
            store.write_completion("task-1", completion)
            retry = deepcopy(completion)
            retry["metadata"]["execution_records"]["run"]["run_id"] = "run-2"

            store.write_completion("task-1", retry)
            persisted = json.loads((Path(temporary) / "task-1" / "completion.json").read_text())
            self.assertEqual(persisted["metadata"]["execution_records"]["run"]["run_id"], "run-2")

    def test_session_validation_detects_edited_run_record(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = LocalJsonExecutionStore(temporary)
            store.write_records("task-1", valid_records())
            store.write_completion("task-1", valid_completion())
            run_path = Path(temporary) / "task-1" / "runs" / "run-1.json"
            run = json.loads(run_path.read_text())
            run["task_id"] = "different-task"
            run_path.write_text(json.dumps(run))

            report = validate_session_directory(temporary, "task-1")

            self.assertFalse(report["valid"])
            self.assertTrue(any("run[0].task_id" in issue for issue in report["issues"]))

    def test_rejects_path_traversal_identifiers(self):
        store = LocalJsonExecutionStore("/tmp/agentcaravan-test-sessions")
        with self.assertRaises(SessionStoreError):
            store.write_completion("../outside", {"status": "completed"})


if __name__ == "__main__":
    unittest.main()
