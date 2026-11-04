"""Focused result-assembly provenance checks; no live model calls."""

from __future__ import annotations

import importlib.util
import json
import shlex
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from agentcaravan.adapters.codex_execution_surface import CodexExecutionRequest
from agentcaravan.execution_result import normalize_execution_result
from agentcaravan.adapters.codex_cli_surface import CodexCliExecutionSurface


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("dependency_result_builder", HERE / "codex_result_builder.py")
assert SPEC and SPEC.loader
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


def stamp(minute: int) -> str:
    return (datetime(2026, 9, 30, tzinfo=timezone.utc) + timedelta(minutes=minute)).isoformat()


def request(case_id: str) -> CodexExecutionRequest:
    task_id = f"conformance-{case_id}"
    steps = [
        {"step_id": stage, "role_ids": [builder._STAGE_ROLES[stage]]}
        for stage in builder._STAGES[case_id]
    ]
    role_ids = sorted({step["role_ids"][0] for step in steps})
    return CodexExecutionRequest(
        scenario={"id": case_id},
        prepared={"status": "ready", "context": {},
                  "plan": {"id": f"plan-{case_id}", "task": {"task_id": task_id},
                           "role_assignments": [{"role_id": role_id} for role_id in role_ids],
                           "steps": steps}},
        brief={},
        records={"task": {"task_id": task_id},
                 "session": {"session_id": "portable-session"},
                 "run": {"run_id": "portable-run"}},
    )


def stage_receipts(req: CodexExecutionRequest, case_id: str) -> list[dict]:
    result = []
    for i, stage in enumerate(builder._STAGES[case_id]):
        native_id = f"codex-native-{i}"
        native_result = {key: [] for key in CodexCliExecutionSurface._RESULT_REQUIRED_FIELDS}
        native_result.update(artifact_type="normalized-execution-result", version="1.0.0", task_id=req.task_id,
                             plan_id=req.prepared["plan"]["id"], status="blocked",
                             execution_realization={"mode": "unreported", "native_subagents": False},
                             metadata={"stage_report": "Candidate assessed."})
        result.append({
            "task_id": req.task_id, "run_id": req.run_id, "plan_id": req.prepared["plan"]["id"],
            "stage_id": stage, "role_id": builder._STAGE_ROLES[stage], "session_id": native_id,
            "native_jsonl_events": [{"type": "thread.started", "thread_id": native_id}, {"type": "turn.started"},
                {"type": "item.completed", "item": {"type": "agent_message", "text": json.dumps(native_result)}}, {"type": "turn.completed"}],
            "report": "Candidate assessed.", "requested_model": "gpt-6.1-sol", "effective_model": None,
            "version": "0.159.0", "started_at": stamp(i * 10), "completed_at": stamp(i * 10 + 5),
            "receipt_source": "directly-observed-by-agentcaravan", "report_source": "reported-by-codex",
            "permission_boundary": "sandbox-read-only",
        })
    return result


def receipt(req: CodexExecutionRequest, kind: str, *, human: bool, minute: int,
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


class CodexResultBuilderTests(unittest.TestCase):
    def inputs(self, accept=False):
        case = "dependency-approval-accept" if accept else "dependency-approval-reject"
        req = request(case)
        args = {"case_id": case, "candidate_inputs": json.loads((HERE / "inputs/candidate-evidence.json").read_text()),
                "stage_receipts": stage_receipts(req, case),
                "human_attestations": [
                    receipt(req, "technical-need", human=True, minute=6, refs=["codex-thread:codex-native-0"]),
                    receipt(req, "independent-review", human=True, minute=26,
                            refs=["codex-thread:codex-native-2"] + ([] if accept else ["evidence-failed-hard-criterion"]), disposition="accept" if accept else "reject"),
                    receipt(req, "completion", human=True, minute=67 if accept else 47,
                            refs=["codex-thread:codex-native-6" if accept else "codex-thread:codex-native-4"], disposition="accept" if accept else "reject")],
                "verification_receipts": [receipt(req, "compatibility-assessment", human=False, minute=14)]}
        if not accept:
            args["verification_receipts"].append(receipt(req, "failed-hard-criterion", human=False, minute=13))
            return req, args
        action = builder.manifest_action()
        human = receipt(req, "human-approval", human=True, minute=47, refs=["controller-request:request-1"])
        human.update(evidence_id="human-approval-evidence-1", owner_role="program-manager", request_id="request-1", action=action)
        args["human_attestations"].append(human)
        args["verification_receipts"].append(receipt(req, "verification", human=False, minute=55))
        args["artifact_receipts"] = [{"task_id": req.task_id, "run_id": req.run_id, "artifact_id": "manifest-1",
            "kind": "dependency-manifest", "status": "modified", "source": "independently-verified",
            "verifier": "independent-check", "verified_at": stamp(50), "references": ["manifest:diff"]}]
        args["approval_receipt"] = {
            "task_id": req.task_id, "run_id": req.run_id, "plan_id": req.prepared["plan"]["id"],
            "request_id": "request-1", "action": action, "requested_at": stamp(46), "started_at": stamp(48), "completed_at": stamp(49),
            "execution_source": "directly-observed-by-agentcaravan", "enforcement": "external-controller-before-dispatch",
            "command_exit_status": "passed", "command_exit_code": 0,
            "execution_method": "controller-direct-argv", "command_argv": shlex.split(action),
            "controller_execution_id": "request-1:action",
            "external_decision": {"task_id": req.task_id, "run_id": req.run_id, "request_id": "request-1", "action": action,
                "actor": "operator", "approved": True, "decided_at": stamp(47), "evidence_id": "human-approval-evidence-1", "provenance": "caller-attested"},
        }
        return req, args

    def test_both_cases_pass_shared_comparator(self):
        from agentcaravan.conformance import _compare_result
        scenarios = json.loads((HERE / "cases.json").read_text())["scenarios"]
        for accept in (False, True):
            req, args = self.inputs(accept)
            raw = builder.build_codex_dependency_result(req, **args)
            result = normalize_execution_result(req.prepared, raw, scenario_id=args["case_id"])
            scenario = next(item for item in scenarios if item["id"] == args["case_id"])
            self.assertEqual(_compare_result(scenario, result), [])

    def test_untrusted_stage_and_human_provenance(self):
        for collection, key, value in (("stage_receipts", "report_source", "human-reviewed"),
                                       ("human_attestations", "source", "reported-by-codex")):
            req, args = self.inputs()
            args[collection][0][key] = value
            with self.assertRaises(builder.DependencyResultError):
                builder.build_codex_dependency_result(req, **args)

    def test_stage_identity_and_native_report_tampering(self):
        for key in ("task_id", "plan_id", "session_id", "report"):
            req, args = self.inputs()
            args["stage_receipts"][0][key] = "different"
            with self.subTest(key=key), self.assertRaises(builder.DependencyResultError):
                builder.build_codex_dependency_result(req, **args)

    def test_approval_binding_and_chronology(self):
        for key, value in (("task_id", "different"), ("plan_id", "different"), ("action", "broader"),
                           ("requested_at", stamp(44)), ("started_at", stamp(46)),
                           ("command_exit_code", 1), ("execution_source", "reported-by-codex")):
            req, args = self.inputs(True)
            args["approval_receipt"][key] = value
            with self.subTest(key=key), self.assertRaises(builder.DependencyResultError):
                builder.build_codex_dependency_result(req, **args)

    def test_missing_or_mismatched_human_approval(self):
        for key, value in (("request_id", "other"), ("action", "broader"), ("attested_at", stamp(48)), ("references", ["wrong"])):
            req, args = self.inputs(True)
            args["human_attestations"][-1][key] = value
            with self.subTest(key=key), self.assertRaises(builder.DependencyResultError):
                builder.build_codex_dependency_result(req, **args)

    def test_controller_command_argv_mismatch(self):
        req, args = self.inputs(True)
        args["approval_receipt"]["command_argv"].append("extra command")
        with self.assertRaises(builder.DependencyResultError):
            builder.build_codex_dependency_result(req, **args)

    def test_independent_stage_threads_are_required(self):
        req, args = self.inputs()
        stage = args["stage_receipts"][1]
        stage["session_id"] = args["stage_receipts"][0]["session_id"]
        stage["native_jsonl_events"][0]["thread_id"] = stage["session_id"]
        with self.assertRaisesRegex(builder.DependencyResultError, "separate native threads"):
            builder.build_codex_dependency_result(req, **args)

    def test_human_review_and_manifest_chronology(self):
        req, args = self.inputs()
        args["human_attestations"][1]["attested_at"] = stamp(24)
        with self.assertRaisesRegex(builder.DependencyResultError, "predates its stage"):
            builder.build_codex_dependency_result(req, **args)
        req, args = self.inputs(True)
        args["artifact_receipts"][0]["verified_at"] = stamp(48)
        with self.assertRaisesRegex(builder.DependencyResultError, "predates the approved action"):
            builder.build_codex_dependency_result(req, **args)

    def test_reject_cannot_claim_changed_artifacts(self):
        req, args = self.inputs()
        args["artifact_receipts"] = [{"artifact_id": "made-up"}]
        with self.assertRaisesRegex(builder.DependencyResultError, "cannot have approval"):
            builder.build_codex_dependency_result(req, **args)


if __name__ == "__main__":
    unittest.main()
