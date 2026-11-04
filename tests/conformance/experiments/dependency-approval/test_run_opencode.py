"""Focused checks for resumable OpenCode experiment sequencing."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SPEC = importlib.util.spec_from_file_location("dependency_approval_run_opencode", Path(__file__).with_name("run_opencode.py"))
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class FakeRunner:
    def __init__(self, model="openai/gpt-6-sol"):
        self.calls = []
        self.model = model

    def execute(self, **kwargs):
        self.calls.append(kwargs)
        return {
            **{key: kwargs[key] for key in ("task_id", "run_id", "stage_id", "role_id")},
            "requested_model": self.model, "version": "1.18.33",
            "receipt_source": "directly-observed-by-agentcaravan",
            "session_id": f"session-{len(self.calls)}", "report": "Observed facts.",
            "started_at": "2026-09-30T00:00:00Z", "completed_at": "2026-09-30T00:00:01Z",
            "native_jsonl_events": [
                {"type": "text", "sessionID": f"session-{len(self.calls)}",
                 "part": {"type": "text", "text": "Observed facts."}},
                {"type": "step_finish", "sessionID": f"session-{len(self.calls)}"},
            ],
        }


class DriverTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.runner = FakeRunner()
        self.driver = module.OpenCodeExperimentDriver(
            state_dir=self.temporary.name, workspace=self.temporary.name,
            model="openai/gpt-6-sol", runner=self.runner,
        )
        self.case = "dependency-approval-reject"

    def test_advances_once_then_waits_for_explicit_receipts(self):
        first = self.driver.advance(self.case)
        self.assertEqual(first["stage_id"], "need-assessment")
        self.assertEqual(first["status"], "stage-completed")
        second = self.driver.advance(self.case)
        self.assertEqual(second["status"], "waiting-for-external-receipt")
        self.assertEqual(second["needed"], "human technical-need attestation")
        self.assertEqual(len(self.runner.calls), 1)

        external = {
            "human_attestations": [{"kind": "technical-need"}],
            "verification_receipts": [
                {"kind": "compatibility-assessment"}, {"kind": "failed-hard-criterion"},
            ],
        }
        path = self.driver.case_dir(self.case) / "external-receipts.json"
        path.write_text(json.dumps(external), encoding="utf-8")
        third = self.driver.advance(self.case)
        self.assertEqual(third["stage_id"], "candidate-assessment")
        self.assertEqual(len(self.runner.calls), 2)
        prompt = self.runner.calls[-1]
        self.assertNotIn("dependency-approval-reject", json.dumps(prompt))
        self.assertNotIn("dependency-approval-accept", json.dumps(prompt))
        self.assertNotIn("criterion_results", prompt["context"]["candidate"])

    def test_saved_receipt_with_different_model_fails_closed(self):
        self.driver.advance(self.case)
        path = self.driver._stage_path(self.case, "need-assessment")
        receipt = json.loads(path.read_text(encoding="utf-8"))
        receipt["requested_model"] = "ollama/qwen3:8b"
        path.write_text(json.dumps(receipt), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.driver.advance(self.case)

    def test_explicit_previous_model_preserves_saved_receipt_and_uses_current(self):
        self.driver.advance(self.case)
        current = "openai/gpt-6.1-sol"
        runner = FakeRunner(current)
        switched = module.OpenCodeExperimentDriver(
            state_dir=self.temporary.name, workspace=self.temporary.name,
            model=current, runner=runner,
        )
        with self.assertRaisesRegex(ValueError, "does not match"):
            switched.advance(self.case)
        switched = module.OpenCodeExperimentDriver(
            state_dir=self.temporary.name, workspace=self.temporary.name,
            model=current, runner=runner, allowed_previous_models=("openai/gpt-6-sol",),
        )
        external = {
            "human_attestations": [{"kind": "technical-need"}],
            "verification_receipts": [{"kind": "compatibility-assessment"},
                                      {"kind": "failed-hard-criterion"}],
        }
        (switched.case_dir(self.case) / "external-receipts.json").write_text(json.dumps(external))
        self.assertEqual(switched.advance(self.case)["stage_id"], "candidate-assessment")
        saved = switched._stages(self.case)
        self.assertEqual(saved["need-assessment"]["requested_model"], "openai/gpt-6-sol")
        self.assertEqual(saved["candidate-assessment"]["requested_model"], current)
        self.assertEqual(len(runner.calls), 1)

    def test_previous_model_not_allowed_for_new_stage(self):
        driver = module.OpenCodeExperimentDriver(
            state_dir=self.temporary.name, workspace=self.temporary.name,
            model="openai/gpt-6.1-sol", runner=self.runner,
            allowed_previous_models=("openai/gpt-6-sol",),
        )
        with self.assertRaisesRegex(ValueError, "runner returned an invalid"):
            driver.advance(self.case)
        self.assertFalse(driver._stage_path(self.case, "need-assessment").exists())

    def test_evaluate_rejects_partial_stage_set(self):
        self.driver.advance(self.case)
        with self.assertRaisesRegex(ValueError, "all read-only stages"):
            self.driver.evaluate(self.case)


if __name__ == "__main__":
    unittest.main()
