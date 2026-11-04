"""Resumable controller gates; fixtures never invoke a model."""

import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timezone
from pathlib import Path

from agentcaravan.adapters.codex_cli_surface import CodexCliExecutionSurface
from codex_stage_runner import CodexStageRunner
from run_codex import CodexExperimentDriver


class CodexDriverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.calls = []

        def run(argv, **kwargs):
            if argv[-1] == "--version":
                return subprocess.CompletedProcess(argv, 0, "codex-cli 0.159.0", "")
            payload = json.loads(kwargs["input"].split("\n", 1)[1])
            self.calls.append(payload)
            result = {key: [] for key in CodexCliExecutionSurface._RESULT_REQUIRED_FIELDS}
            result.update(artifact_type="normalized-execution-result", version="1.0.0",
                          task_id=payload["task"]["task_id"], plan_id=payload["portable_execution_plan"]["id"],
                          status="blocked", execution_realization={"mode": "unreported", "native_subagents": False},
                          metadata={"stage_report": "Assessed supplied evidence."})
            events = [{"type": "thread.started", "thread_id": f"thread-{len(self.calls)}"}, {"type": "turn.started"},
                      {"type": "item.completed", "item": {"type": "agent_message", "text": json.dumps(result)}}, {"type": "turn.completed"}]
            return subprocess.CompletedProcess(argv, 0, "\n".join(json.dumps(e) for e in events), "")

        self.driver = CodexExperimentDriver(state_dir=self.root, workspace=".",
            runner=CodexStageRunner(cwd=".", model="gpt-6.1-sol", run=run))

    def evidence(self, case, *, technical=False, review=False):
        identity = self.driver._identity(case)
        stages = self.driver._stages(case)
        current = self.driver._external(case)
        humans = current.setdefault("human_attestations", [])
        checks = current.setdefault("verification_receipts", [])
        base = {key: identity[key] for key in ("task_id", "run_id")}
        now = datetime.now(timezone.utc).isoformat()
        if technical:
            humans.append({**base, "kind": "technical-need", "evidence_id": "need", "source": "human-reviewed",
                "status": "passed", "actor": "user", "attested_at": now,
                "references": [f"codex-thread:{stages['need-assessment']['session_id']}"]})
            for kind in (["compatibility-assessment", "failed-hard-criterion"] if case.endswith("reject") else ["compatibility-assessment"]):
                checks.append({**base, "kind": kind, "evidence_id": kind, "source": "independently-verified",
                    "status": "passed", "verifier": "test-checker", "verified_at": now, "references": ["local-check"]})
        if review:
            humans.append({**base, "kind": "independent-review", "evidence_id": "review", "source": "human-reviewed",
                "status": "passed", "actor": "user", "attested_at": now, "disposition": case.rsplit("-", 1)[-1],
                "references": [f"codex-thread:{stages['independent-review']['session_id']}"]})
        (self.driver.case_dir(case) / "external-receipts.json").write_text(json.dumps(current))

    def test_resume_and_human_need_gate_without_duplicate_calls(self):
        case = "dependency-approval-reject"
        first = self.driver.advance(case)
        self.assertEqual(first["stage_id"], "need-assessment")
        self.assertEqual(self.driver.advance(case)["needed"], "technical-need")
        self.assertEqual(len(self.calls), 1)
        resumed = CodexExperimentDriver(state_dir=self.root, workspace=".", runner=self.driver.runner)
        self.assertEqual(resumed.advance(case)["needed"], "technical-need")

    def test_readonly_stages_are_separate_and_do_not_receive_expected_outcomes(self):
        case = "dependency-approval-reject"
        self.driver.advance(case)
        self.evidence(case, technical=True)
        self.driver.advance(case)
        self.driver.advance(case)
        self.assertEqual(self.driver.advance(case)["needed"], "independent-review")
        stages = self.driver._stages(case)
        self.assertEqual(len({stage["session_id"] for stage in stages.values()}), 3)
        candidate = self.calls[-1]["task"]["context"]["candidate"]
        for name in ("case_id", "expected_disposition", "criterion_results", "installation_prohibited", "approval"):
            self.assertNotIn(name, candidate)
        self.assertNotIn("expected", self.calls[-1])

    def test_workspace_or_model_change_on_resume_is_rejected(self):
        case = "dependency-approval-reject"
        self.driver.advance(case)
        other = CodexExperimentDriver(state_dir=self.root, workspace=self.root, runner=self.driver.runner)
        with self.assertRaisesRegex(ValueError, "pinned inputs changed"):
            other.advance(case)
        identity_path = self.driver.case_dir(case) / "identity.json"
        identity = json.loads(identity_path.read_text())
        identity["candidate_inputs_sha256"] = "tampered"
        identity_path.write_text(json.dumps(identity))
        with self.assertRaises(ValueError):
            self.driver.advance(case)

    def test_reject_cannot_include_approval_artifacts(self):
        case = "dependency-approval-reject"
        self.driver._identity(case)
        (self.driver.case_dir(case) / "external-receipts.json").write_text(json.dumps({"artifact_receipts": [{}]}))
        with self.assertRaises(ValueError):
            self.driver.advance(case)

    def test_resolved_role_or_policy_drift_blocks_resume(self):
        case = "dependency-approval-reject"
        self.driver.advance(case)
        from run_codex import resolve_bundle
        def changed(bundle):
            resolved = resolve_bundle(bundle)
            resolved["review_test_drift"] = "changed role or policy"
            return resolved
        with patch("run_codex.resolve_bundle", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "pinned inputs changed"):
                self.driver.advance(case)
        self.assertEqual(len(self.calls), 1)

    def test_wrong_native_review_cannot_advance_to_write_request(self):
        case = "dependency-approval-accept"
        self.driver.advance(case)
        self.evidence(case, technical=True)
        self.driver.advance(case)
        self.driver.advance(case)
        self.evidence(case, review=True)
        path = self.driver.case_dir(case) / "external-receipts.json"
        external = json.loads(path.read_text())
        external["human_attestations"][-1]["references"] = ["codex-thread:wrong"]
        path.write_text(json.dumps(external))
        with self.assertRaises(ValueError):
            self.driver.advance(case)

    def test_accept_creates_stable_pending_request_without_dispatch(self):
        case = "dependency-approval-accept"
        self.driver.advance(case)
        self.evidence(case, technical=True)
        self.driver.advance(case)
        self.driver.advance(case)
        self.evidence(case, review=True)
        self.driver.advance(case)
        self.driver.advance(case)
        pending = self.driver.advance(case)
        self.assertEqual(pending["status"], "waiting-for-human-approval")
        self.assertEqual(self.driver.advance(case)["request"], pending["request"])
        self.assertEqual(len(self.calls), 5)

    def test_incomplete_run_cannot_be_evaluated(self):
        with self.assertRaises(ValueError):
            self.driver.evaluate("dependency-approval-reject")

    def test_failed_dispatch_is_retained_and_never_repeated_automatically(self):
        case = "dependency-approval-accept"
        self.driver.advance(case)
        self.evidence(case, technical=True)
        self.driver.advance(case)
        self.driver.advance(case)
        self.evidence(case, review=True)
        self.driver.advance(case)
        self.driver.advance(case)
        pending = self.driver.advance(case)["request"]
        path = self.driver.case_dir(case) / "external-receipts.json"
        external = json.loads(path.read_text())
        external["human_attestations"].append({
            **{key: pending[key] for key in ("task_id", "run_id", "request_id", "action")},
            "kind": "human-approval", "source": "human-reviewed", "status": "passed", "approved": True,
            "actor": "user", "owner_role": "program-manager", "evidence_id": "human-approval-evidence-1",
            "attested_at": datetime.now(timezone.utc).isoformat(),
            "references": [f"controller-request:{pending['request_id']}"],
        })
        path.write_text(json.dumps(external))
        calls = []

        class FailedAction:
            def execute(self, pending, decision):
                calls.append(pending)
                raise ValueError("native result failed")

        self.driver.action_runner = FailedAction()
        with self.assertRaises(ValueError):
            self.driver.advance(case)
        self.assertEqual(self.driver.advance(case)["status"], "waiting-for-action-resolution")
        self.assertEqual(len(calls), 1)
        self.assertTrue((self.driver.case_dir(case) / "failed-action.json").exists())


if __name__ == "__main__":
    unittest.main()
