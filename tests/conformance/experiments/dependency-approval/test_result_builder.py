"""Focused result-assembly provenance checks; no live model calls."""

from __future__ import annotations

import importlib.util
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from agentcaravan.adapters.opencode_execution_surface import OpenCodeExecutionRequest
from agentcaravan.execution_result import normalize_execution_result


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("dependency_result_builder", HERE / "result_builder.py")
assert SPEC and SPEC.loader
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


def stamp(minute: int) -> str:
    return (datetime(2026, 9, 30, tzinfo=timezone.utc) + timedelta(minutes=minute)).isoformat()


def request(case_id: str) -> OpenCodeExecutionRequest:
    task_id = f"conformance-{case_id}"
    steps = [
        {"step_id": stage, "role_ids": [builder._STAGE_ROLES[stage]]}
        for stage in builder._STAGES[case_id]
    ]
    role_ids = sorted({step["role_ids"][0] for step in steps})
    return OpenCodeExecutionRequest(
        scenario={"id": case_id},
        prepared={"status": "ready", "context": {},
                  "plan": {"id": f"plan-{case_id}", "task": {"task_id": task_id},
                           "role_assignments": [{"role_id": role_id} for role_id in role_ids],
                           "steps": steps}},
        projection={},
        records={"task": {"task_id": task_id},
                 "session": {"session_id": "portable-session"},
                 "run": {"run_id": "portable-run"}},
    )


def stage_receipts(req: OpenCodeExecutionRequest, case_id: str) -> list[dict]:
    result = []
    for i, stage in enumerate(builder._STAGES[case_id]):
        native_id = f"oc-session-{i}"
        result.append({
            "task_id": req.task_id, "run_id": req.run_id,
            "stage_id": stage, "role_id": builder._STAGE_ROLES[stage],
            "session_id": native_id, "native_jsonl_events": [
                {"type": "text", "sessionID": native_id,
                 "part": {"type": "text", "text": "Candidate assessed."}},
                {"type": "step_finish", "sessionID": native_id},
            ],
            "report": "Candidate assessed.", "requested_model": "openai/gpt-6-sol",
            "version": "1.18.33", "started_at": stamp(i * 10),
            "completed_at": stamp(i * 10 + 5),
            "receipt_source": "directly-observed-by-agentcaravan",
            "report_source": "reported-by-opencode",
            "permission_boundary": "application-level-read-only",
        })
    return result


def receipt(req: OpenCodeExecutionRequest, kind: str, *, human: bool, minute: int,
            refs: list[str] | None = None, disposition: str | None = None) -> dict:
    item = {
        "task_id": req.task_id, "run_id": req.run_id,
        "kind": kind, "evidence_id": f"evidence-{kind}", "status": "passed",
        "source": "human-reviewed" if human else "independently-verified",
        "references": refs or [f"receipt:{kind}"],
        ("actor" if human else "verifier"): "operator" if human else "independent-check",
        ("attested_at" if human else "verified_at"): stamp(minute),
    }
    if disposition:
        item["disposition"] = disposition
    return item


class ResultBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inputs = json.loads((HERE / "inputs/candidate-evidence.json").read_text(encoding="utf-8"))

    def reject_inputs(self) -> tuple[OpenCodeExecutionRequest, dict]:
        case_id = "dependency-approval-reject"
        req = request(case_id)
        args = {
            "case_id": case_id,
            "stage_receipts": stage_receipts(req, case_id),
            "candidate_inputs": self.inputs,
            "human_attestations": [
                receipt(req, "technical-need", human=True, minute=6,
                        refs=["opencode-session:oc-session-0"]),
                receipt(req, "independent-review", human=True, minute=26,
                        refs=["opencode-session:oc-session-2", "evidence-failed-hard-criterion"],
                        disposition="reject"),
                receipt(req, "completion", human=True, minute=47,
                        refs=["opencode-session:oc-session-4"], disposition="reject"),
            ],
            "verification_receipts": [
                receipt(req, "compatibility-assessment", human=False, minute=14),
                receipt(req, "failed-hard-criterion", human=False, minute=13),
            ],
        }
        return req, args

    def test_reject_result_normalizes_with_attributed_events(self) -> None:
        req, args = self.reject_inputs()
        raw = builder.build_opencode_dependency_result(req, **args)
        normalized = normalize_execution_result(req.prepared, raw, scenario_id=args["case_id"])
        self.assertEqual(normalized["status"], "completed")
        self.assertEqual([event["status"] for event in normalized["execution_events"]],
                         ["failed", "completed", "recorded"])
        self.assertEqual(normalized["approvals"], [])
        self.assertEqual(normalized["artifacts"], [])

    def test_model_text_cannot_become_human_review(self) -> None:
        req, args = self.reject_inputs()
        args["human_attestations"][1]["source"] = "reported-by-opencode"
        with self.assertRaisesRegex(builder.DependencyResultError, "provenance"):
            builder.build_opencode_dependency_result(req, **args)

    def test_stage_needs_native_session_events(self) -> None:
        req, args = self.reject_inputs()
        args["stage_receipts"][0]["native_jsonl_events"][0]["sessionID"] = "different-session"
        with self.assertRaisesRegex(builder.DependencyResultError, "observed, scoped"):
            builder.build_opencode_dependency_result(req, **args)

    def test_historical_candidate_approval_cannot_satisfy_new_run(self) -> None:
        case_id = "dependency-approval-accept"
        req = request(case_id)
        args = {
            "case_id": case_id,
            "stage_receipts": stage_receipts(req, case_id),
            "candidate_inputs": self.inputs,  # Includes the prior Codex approval field.
            "human_attestations": [
                receipt(req, "technical-need", human=True, minute=6,
                        refs=["opencode-session:oc-session-0"]),
                receipt(req, "independent-review", human=True, minute=26,
                        refs=["opencode-session:oc-session-2"], disposition="accept"),
                receipt(req, "completion", human=True, minute=67,
                        refs=["opencode-session:oc-session-6"], disposition="accept"),
            ],
            "verification_receipts": [
                receipt(req, "compatibility-assessment", human=False, minute=14),
                receipt(req, "verification", human=False, minute=55),
            ],
        }
        with self.assertRaisesRegex(builder.DependencyResultError, "human or independent evidence"):
            builder.build_opencode_dependency_result(req, **args)

    def test_accept_needs_native_approval_exchange_and_verified_manifest(self) -> None:
        case_id = "dependency-approval-accept"
        req = request(case_id)
        approval_evidence = receipt(req, "human-approval", human=True, minute=47,
                                    refs=["permission:perm-1"])
        approval_evidence.update({"evidence_id": "human-approval-evidence-1",
                                  "owner_role": "program-manager"})
        action = "add exact dependency"
        native_session = "approval-session"
        ask = {"id": "ask-event", "observed_at": stamp(46), "properties": {
            "sessionID": native_session, "id": "perm-1", "permission": "bash",
            "metadata": {"command": action},
            "tool": {"callID": "call-1", "messageID": "message-1"}}}
        reply = {"id": "reply-event", "observed_at": stamp(48),
                 "provenance": "runtime-observed", "properties": {
                     "sessionID": native_session, "requestID": "perm-1", "reply": "once"}}
        applied = {"id": "applied-event", "observed_at": stamp(49), "properties": {
            "sessionID": native_session, "part": {"callID": "call-1", "state": {
                "status": "completed", "input": {"command": action}}}}}
        approval_receipt = {
            "task_id": req.task_id, "run_id": req.run_id, "version": "1.18.33",
            "human_reviewed": False, "opencode_session_id": native_session,
            "action": action, "permission_request": ask, "permission_reply": reply,
            "action_completion": applied, "command_exit_status": "passed",
            "command_exit_code": 0,
            "external_decision": {
                "task_id": req.task_id, "run_id": req.run_id,
                "session_id": native_session, "permission_id": "perm-1",
                "action": action, "approved": True, "provenance": "caller-attested",
                "actor": "operator", "decided_at": stamp(47),
                "evidence_id": "human-approval-evidence-1",
            },
        }
        args = {
            "case_id": case_id,
            "stage_receipts": stage_receipts(req, case_id),
            "candidate_inputs": self.inputs,
            "human_attestations": [
                receipt(req, "technical-need", human=True, minute=6,
                        refs=["opencode-session:oc-session-0"]),
                receipt(req, "independent-review", human=True, minute=26,
                        refs=["opencode-session:oc-session-2"], disposition="accept"),
                approval_evidence,
                receipt(req, "completion", human=True, minute=67,
                        refs=["opencode-session:oc-session-6"], disposition="accept"),
            ],
            "approval_receipt": approval_receipt,
            "verification_receipts": [
                receipt(req, "compatibility-assessment", human=False, minute=14),
                receipt(req, "verification", human=False, minute=55),
            ],
            "artifact_receipts": [{
                "task_id": req.task_id, "run_id": req.run_id,
                "artifact_id": "manifest-1", "kind": "dependency-manifest",
                "status": "modified", "source": "independently-verified",
                "verifier": "independent-check", "verified_at": stamp(49.5),
                "references": ["manifest:diff"],
            }],
        }
        raw = builder.build_opencode_dependency_result(req, **args)
        self.assertEqual(raw["metadata"]["native_approval_receipt"], approval_receipt)
        self.assertEqual(raw["metadata"]["native_stage_receipts"][0]["requested_model"], "openai/gpt-6-sol")
        self.assertEqual(raw["metadata"]["native_stage_receipts"][0]["version"], "1.18.33")
        normalized = normalize_execution_result(req.prepared, raw, scenario_id=case_id)
        self.assertEqual([event["status"] for event in normalized["execution_events"]],
                         ["passed", "completed", "blocked-until-approved", "approved", "applied", "passed"])
        from copy import deepcopy
        grouped = deepcopy(args)
        grouped["verification_receipts"][1]["verified_at"] = stamp(49.5)
        builder.build_opencode_dependency_result(req, **grouped)
        grouped["verification_receipts"][1]["verified_at"] = stamp(49.4)
        with self.assertRaisesRegex(builder.DependencyResultError, "verification predates"):
            builder.build_opencode_dependency_result(req, **grouped)
        initial = deepcopy(approval_receipt)
        initial.update(command_exit_status="failed", command_exit_code=1)
        initial["action_completion"]["observed_at"] = stamp(48.5)
        retry = deepcopy(approval_receipt)
        retry["opencode_session_id"] = "retry-session"
        for event_name in ("permission_request", "permission_reply", "action_completion"):
            retry[event_name]["id"] += "-retry"
            retry[event_name]["properties"]["sessionID"] = "retry-session"
        retry["permission_request"]["properties"]["id"] = "perm-2"
        retry["permission_request"]["properties"]["tool"] = {"callID": "call-2", "messageID": "message-2"}
        retry["action_completion"]["properties"]["part"]["callID"] = "call-2"
        retry["permission_reply"]["properties"]["requestID"] = "perm-2"
        retry["permission_request"]["observed_at"] = stamp(48.6)
        retry["external_decision"].update(session_id="retry-session", permission_id="perm-2",
                                           actor="agentcaravan-controller", decided_at=stamp(48.7))
        retry["permission_reply"]["observed_at"] = stamp(48.8)
        retry["authorization_reference"] = {
            "permission_id": "perm-1", "evidence_id": "human-approval-evidence-1",
            "task_id": req.task_id, "run_id": req.run_id, "action": action,
            "source": "derived-from-human-approval",
        }
        args["approval_receipt"] = {"initial_receipt": initial, "retry_receipts": [retry]}
        retried = builder.build_opencode_dependency_result(req, **args)
        self.assertEqual(retried["metadata"]["native_approval_receipt"]["initial_receipt"]["command_exit_code"], 1)
        self.assertEqual(retried["retries"][0]["status"], "passed")
        self.assertTrue(retried["retries"][0]["invocation_completed"])
        self.assertEqual(retried["approvals"][0]["permission_id"], "perm-1")
        self.assertEqual(retried["execution_events"][3]["timestamp"], stamp(48))
        self.assertEqual(retried["execution_events"][4]["timestamp"], stamp(49))
        self.assertEqual(retried["retries"][0]["native_receipt"]["external_decision"]["actor"],
                         "agentcaravan-controller")
        intermediate = deepcopy(retry)
        intermediate.update(command_exit_status="failed", command_exit_code=1)
        intermediate["action_completion"]["observed_at"] = stamp(48.9)
        final_retry = deepcopy(retry)
        final_retry["opencode_session_id"] = "final-session"
        for name in ("permission_request", "permission_reply", "action_completion"):
            final_retry[name]["id"] += "-final"
            final_retry[name]["properties"]["sessionID"] = "final-session"
        final_retry["permission_request"]["properties"]["id"] = "perm-3"
        final_retry["permission_request"]["properties"]["tool"] = {"callID": "call-3", "messageID": "message-3"}
        final_retry["permission_request"]["observed_at"] = stamp(48.91)
        final_retry["permission_reply"]["properties"]["requestID"] = "perm-3"
        final_retry["permission_reply"]["observed_at"] = stamp(48.93)
        final_retry["action_completion"]["properties"]["part"]["callID"] = "call-3"
        final_retry["external_decision"].update(session_id="final-session", permission_id="perm-3",
                                               decided_at=stamp(48.92))
        args["approval_receipt"] = {"initial_receipt": initial,
                                   "retry_receipts": [intermediate, final_retry]}
        history = builder.build_opencode_dependency_result(req, **args)
        self.assertEqual([item["status"] for item in history["retries"]], ["failed", "passed"])
        for mutation in ("action", "reference", "chronology"):
            bad = deepcopy(retry)
            if mutation == "action":
                bad["action"] = "broader action"
            elif mutation == "reference":
                del bad["authorization_reference"]
            else:
                bad["permission_request"]["observed_at"] = stamp(48.4)
            args["approval_receipt"] = {"initial_receipt": initial, "retry_receipts": [bad]}
            with self.assertRaises(builder.DependencyResultError):
                builder.build_opencode_dependency_result(req, **args)
        for unsafe_initial in (deepcopy(approval_receipt), deepcopy(initial)):
            if unsafe_initial.get("command_exit_code") == 1:
                unsafe_initial["status"] = "indeterminate-post-approval"
            args["approval_receipt"] = {"initial_receipt": unsafe_initial, "retry_receipts": [retry]}
            with self.assertRaisesRegex(builder.DependencyResultError, "known failed"):
                builder.build_opencode_dependency_result(req, **args)
        args["approval_receipt"] = approval_receipt
        approval_receipt["permission_reply"]["properties"]["reply"] = "always"
        with self.assertRaisesRegex(builder.DependencyResultError, "approval reply"):
            builder.build_opencode_dependency_result(req, **args)


if __name__ == "__main__":
    unittest.main()
