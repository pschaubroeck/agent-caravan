from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import threading
import time
import unittest

from agentcaravan.schema_validation import validate_artifact


ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = ROOT / "tests" / "conformance" / "experiments" / "parallel-scheduling"
SPEC = importlib.util.spec_from_file_location(
    "parallel_scheduling_controller", EXPERIMENT / "controller.py"
)
controller = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(controller)
SCHEMA = ROOT / "resources" / "schemas" / "runtime-verification-record.schema.json"


class FakeRunner:
    def __init__(self):
        self.ready = threading.Barrier(2)

    def execute(self, *, task_id, run_id, stage_id, role_id, instruction, context=None):
        if run_id in {"run-1-design", "run-1-independent-analysis"}:
            self.ready.wait(timeout=2)
        started_at = datetime.now(timezone.utc)
        if run_id.endswith("design"):
            time.sleep(0.03)
        elif run_id.endswith("independent-analysis"):
            time.sleep(0.06)
        completed_at = datetime.now(timezone.utc)
        return {
            "task_id": task_id,
            "run_id": run_id,
            "stage_id": stage_id,
            "role_id": role_id,
            "session_id": f"thread-{run_id}",
            "started_at": started_at.isoformat().replace("+00:00", "Z"),
            "completed_at": completed_at.isoformat().replace("+00:00", "Z"),
            "version": "0.162.0",
            "report": "A bounded report.",
        }


class IndependentFinishesBeforeDesignStartsRunner(FakeRunner):
    def execute(self, **kwargs):
        result = super().execute(**kwargs)
        if result["run_id"].endswith("independent-analysis"):
            result["started_at"] = "2026-10-01T09:59:00Z"
            result["completed_at"] = "2026-10-01T09:59:30Z"
        elif result["run_id"].endswith("design"):
            result["started_at"] = "2026-10-01T10:00:00Z"
            result["completed_at"] = "2026-10-01T10:00:30Z"
        return result


class ParallelSchedulingControllerTests(unittest.TestCase):
    def test_independent_work_overlaps_wait_and_dependent_work_starts_after_answer(self):
        timeline = controller.run_scenario(
            FakeRunner(),
            task_id="task-1",
            run_id="run-1",
            clock=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        )

        self.assertEqual(timeline["scheduling_conformance"]["status"], "pass", timeline)
        self.assertEqual(
            timeline["scheduling_conformance"]["work_during_wait"],
            [{"work_item_id": "implement", "other_work_item_ids": ["design", "independent-analysis"]}],
        )
        implementation_start = next(
            event["timestamp"] for event in timeline["execution_events"]
            if event["work_item_id"] == "implement" and event["status"] == "resumed"
        )
        design_complete = next(
            event["timestamp"] for event in timeline["execution_events"]
            if event["work_item_id"] == "design" and event["status"] == "completed"
        )
        self.assertGreaterEqual(implementation_start, design_complete)
        self.assertTrue(all(event["evidence_source"] == "adapter-observed" for event in timeline["execution_events"]))
        record = controller.build_verification_record(
            timeline,
            model="gpt-6.1-sol",
            runtime_version="0.162.0",
            evidence_ref="repo://timeline.json#sha256=abc123",
            recorded_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        )
        validate_artifact(record, SCHEMA)

    def test_independent_work_that_finishes_before_dependency_starts_is_unverified(self):
        timeline = controller.run_scenario(
            IndependentFinishesBeforeDesignStartsRunner(),
            task_id="task-2",
            run_id="run-2",
            clock=lambda: "2026-10-01T09:58:00Z",
        )

        self.assertEqual(timeline["scheduling_conformance"]["status"], "unverified")
        self.assertIn(
            "independent work did not overlap the dependency wait interval",
            timeline["scheduling_conformance"]["issues"],
        )


if __name__ == "__main__":
    unittest.main()
