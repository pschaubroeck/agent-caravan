import unittest
from copy import deepcopy
from pathlib import Path

from agentcaravan.conformance import (
    ConformanceError,
    load_conformance_scenarios,
    run_conformance_suite,
)
from agentcaravan.orchestration import prepare_execution


SCENARIOS = Path(__file__).parents[1] / "conformance" / "scenarios.json"
DEPENDENCY_CASES = Path(__file__).parents[1] / "conformance" / "experiments" / "dependency-approval" / "cases.json"


def prepared_execution(scenario=None):
    roles = [
        "program-manager", "product-owner", "tech-owner", "engineer",
        "quality-engineer", "software-architect", "release-manager",
    ]
    expected_stages = (scenario or {}).get("expected", {}).get("completed_stages", [])
    stages = [
        {"id": stage_id, "roles": roles}
        for stage_id in expected_stages
    ] or [{"id": "scenario-step", "roles": roles, "condition": "no stage completion is asserted by this scenario"}]
    prepared = prepare_execution(
        {
            "status": "pass",
            "context": {
                "organization_catalog_id": "example-organization",
                "team_instance_id": "example-team",
                "team_blueprint_id": "information-technology-core-team",
                "runtime_profile_id": "example-runtime-profile",
                "execution_profile_id": "example-execution-profile",
            },
            "effective_roles": [
                {"id": "program-manager", "source_chain": ["program-manager"]},
                {"id": "product-owner", "source_chain": ["product-owner"]},
                {"id": "tech-owner", "source_chain": ["tech-owner"]},
                {"id": "engineer", "source_chain": ["engineer"]},
                {"id": "quality-engineer", "source_chain": ["quality-engineer"]},
                {"id": "software-architect", "source_chain": ["software-architect"]},
                {"id": "release-manager", "source_chain": ["release-manager"]},
            ],
            "runtime": {"adapter_id": "example-runtime", "degraded_capabilities": []},
            "execution_profile": {
                "entry_roles": roles,
                "activation_policy": {"primary_roles": ["engineer"]},
                "stages": stages,
                "communication": {"requires_structured_handoff": True, "allowed_role_handoffs": []},
                "escalation": {},
                "termination": {"success_criteria": (scenario or {}).get("workflow", {}).get("success_criteria", [])},
                "required_outputs": ["completion record"],
            },
        },
        {"task_id": "conformance-task", "objective": "Run a conformance scenario"},
    )
    if scenario and scenario.get("work_items"):
        prepared["plan"]["execution_topology"] = {
            "mode": "coordinator-worker",
            "work_items": scenario["work_items"],
        }
    return prepared


def reference_executor(scenario):
    expected = scenario["expected"]
    result = {
        "status": expected["status"],
        "active_roles": expected["active_roles"],
        "completed_stages": expected.get("completed_stages", []),
        "handoffs": [
            {"from": item["from"], "to": item["to"], "status": item["status"]}
            for item in expected.get("handoff_statuses", [])
        ],
        "approvals": [
            {"trigger": item["trigger"], "status": item["status"]}
            for item in expected.get("approval_statuses", [])
        ],
        "failures": [{} for _ in range(expected.get("failure_count", 0))],
        "retries": [{} for _ in range(expected.get("max_retries", 0))],
        "evidence": [{"kind": kind, "status": "passed"} for kind in expected.get("required_tool_evidence", [])],
        "decisions": [{}] if "decisions" in expected.get("required_completion_fields", []) else [],
    }
    if (scenario.get("workflow") or {}).get("assessment"):
        result["evidence"].append({
            "evidence_id": "completion-evidence-quality-1",
            "kind": "quality-evidence",
            "status": "passed",
            "references": ["quality-evidence-snapshot-1"],
        })
        result["role_turns"] = [
            {
                "role_turn_id": "completion-evidence-quality-turn",
                "task_id": "conformance-task",
                "role_id": "quality-engineer",
                "status": "completed",
                "summary": "Recorded and reviewed quality evidence.",
            }
        ]
        result["workflow_assessment"] = scenario["workflow"]["assessment"]
    for field in expected.get("required_completion_fields", []):
        result.setdefault(field, [])
    if "run_count" in expected or "same_task_id" in expected or "prior_run_preserved" in expected:
        result["resume"] = {
            "run_count": expected.get("run_count"),
            "same_task_id": expected.get("same_task_id"),
            "prior_run_preserved": expected.get("prior_run_preserved"),
            "required": expected.get("resume_required"),
            "replay_from_stage": expected.get("replay_from_stage"),
        }
    if "checkpoint_status" in expected:
        result["checkpoint"] = {
            "checkpoint_id": f"{scenario['id']}-checkpoint",
            "task_id": "conformance-task",
            "status": expected["checkpoint_status"],
            "resumable": True,
        }
    if "idempotency_status" in expected:
        result["idempotency_records"] = [{
            "idempotency_key": f"{scenario['id']}-key",
            "operation": "reference-operation",
            "status": expected["idempotency_status"],
            "side_effect_applied": False,
        }]
        result["metadata"] = {
            "idempotency_status": expected["idempotency_status"],
            "side_effect_count": expected.get("side_effect_count"),
            "idempotency_key_required": expected.get("idempotency_key_required"),
        }
    if "degraded_capabilities" in expected:
        result["degraded_capabilities"] = expected["degraded_capabilities"]
        result.setdefault("metadata", {})["serial_fallback_recorded"] = expected.get("serial_fallback_recorded")
    if scenario.get("work_item_events"):
        result["execution_events"] = [
            {
                "kind": "work-item",
                **event,
                "event_id": f"{scenario['id']}-work-event-{index}",
                "task_id": "conformance-task",
            }
            for index, event in enumerate(scenario["work_item_events"])
        ]
    return result


def dependency_reference_executor(scenario):
    """Create deterministic contract-shaped output; this is not live runtime evidence."""
    expected = scenario["expected"]
    result = reference_executor(scenario)
    result["active_roles"] = expected["active_roles"]
    result["completed_stages"] = expected.get("completed_stages", [])
    result["handoffs"] = [
        {"from": item["from"], "to": item["to"], "status": item["status"]}
        for item in expected.get("handoff_statuses", [])
    ]
    result["approvals"] = [
        {key: value for key, value in item.items() if key != "require_references"}
        for item in expected.get("required_approval_records", [])
    ]
    for item in expected.get("approval_statuses", []):
        if not any(approval.get("trigger") == item["trigger"] for approval in result["approvals"]):
            result["approvals"].append({"trigger": item["trigger"], "status": item["status"]})
    result["run"] = {"run_id": f"{scenario['id']}-run"}
    result["evidence"] = []
    for index, item in enumerate(expected.get("required_evidence_records", [])):
        evidence = {key: value for key, value in item.items() if key != "require_references"}
        evidence.setdefault("references", [f"{scenario['id']}-evidence-{index}"])
        result["evidence"].append(evidence)
    result["artifacts"] = []
    for index, item in enumerate(expected.get("required_artifact_records", [])):
        result["artifacts"].append({
            **{key: value for key, value in item.items() if key != "require_references"},
            "references": [f"{scenario['id']}-artifact-{index}"],
        })
    ordered_events = expected.get("required_event_order", [])
    result["execution_events"] = [
        {
            **item,
            "event_id": f"{scenario['id']}-event-{index}",
            "task_id": "conformance-task",
            "run_id": result["run"]["run_id"],
            "evidence_refs": [f"{scenario['id']}-event-evidence-{index}"],
            "timestamp": f"2026-09-28T10:{index:02d}:00Z",
        }
        for index, item in enumerate(ordered_events)
    ]
    return result


class ConformanceHarnessTests(unittest.TestCase):
    def test_reference_executor_passes_all_shared_scenarios(self):
        scenarios = load_conformance_scenarios(SCENARIOS)
        suite = run_conformance_suite(scenarios, reference_executor, prepared=prepared_execution)

        self.assertTrue(suite.passed)
        self.assertEqual(len(suite.cases), 13)
        self.assertEqual(suite.failures, ())

    def test_completion_evidence_is_referenced_by_the_workflow_assessment(self):
        scenario = next(
            item for item in load_conformance_scenarios(SCENARIOS)
            if item["id"] == "completion-evidence"
        )
        case = run_conformance_suite([scenario], reference_executor, prepared=prepared_execution).cases[0]

        self.assertTrue(case.passed, case.mismatches)
        evidence = next(item for item in case.result["evidence"] if item.get("evidence_id") == "completion-evidence-quality-1")
        assessment = case.result["workflow_assessment"]["criteria"][0]
        self.assertEqual(assessment["evidence_refs"], [evidence["evidence_id"]])
        self.assertTrue(evidence["references"])

    def test_waiting_work_item_can_resume_after_dependency_while_independent_work_runs(self):
        scenario = next(
            item for item in load_conformance_scenarios(SCENARIOS)
            if item["id"] == "dependency-wait-with-independent-work"
        )
        case = run_conformance_suite([scenario], reference_executor, prepared=prepared_execution).cases[0]

        self.assertTrue(case.passed, case.mismatches)
        self.assertEqual(case.result["scheduling_conformance"]["status"], "unverified")
        self.assertEqual(case.result["scheduling_conformance"]["wait_durations_seconds"], {"implement": 300.0})
        self.assertEqual(
            case.result["scheduling_conformance"]["work_during_wait"],
            [{
                "work_item_id": "implement",
                "other_work_item_ids": ["design", "independent-analysis"],
            }],
        )

    def test_runtime_receipts_with_evidence_references_support_observed_schedule_conformance(self):
        scenario = next(
            item for item in load_conformance_scenarios(SCENARIOS)
            if item["id"] == "dependency-wait-with-independent-work"
        )

        def receipt_executor(_scenario):
            result = reference_executor(scenario)
            for index, event in enumerate(result["execution_events"]):
                event["evidence_source"] = "runtime-receipt"
                event["evidence_refs"] = [f"receipt-{index}"]
            return result

        case = run_conformance_suite([scenario], receipt_executor, prepared=prepared_execution).cases[0]

        self.assertTrue(case.passed, case.mismatches)
        self.assertEqual(case.result["scheduling_conformance"]["status"], "pass")

        def receipt_without_reference_executor(_scenario):
            result = receipt_executor(scenario)
            result["execution_events"][0].pop("evidence_refs")
            return result

        invalid_case = run_conformance_suite(
            [scenario], receipt_without_reference_executor, prepared=prepared_execution
        ).cases[0]
        self.assertFalse(invalid_case.passed)
        self.assertIsNone(invalid_case.result)
        self.assertIn("runtime-receipt work-item events require evidence_refs", invalid_case.mismatches[0])

    def test_waiting_work_item_scenario_fails_when_dependency_order_is_violated(self):
        scenario = next(
            item for item in load_conformance_scenarios(SCENARIOS)
            if item["id"] == "dependency-wait-with-independent-work"
        )

        def broken_executor(_scenario):
            result = reference_executor(scenario)
            for event in result["execution_events"]:
                if event["work_item_id"] == "implement" and event["status"] == "resumed":
                    event["timestamp"] = "2026-10-01T10:04:00Z"
            return result

        case = run_conformance_suite([scenario], broken_executor, prepared=prepared_execution).cases[0]

        self.assertEqual(case.result["scheduling_conformance"]["status"], "failed")
        self.assertTrue(any("started before dependency design completed" in item for item in case.result["scheduling_conformance"]["issues"]))

    def test_work_item_events_require_a_declared_evidence_source(self):
        scenario = next(
            item for item in load_conformance_scenarios(SCENARIOS)
            if item["id"] == "dependency-wait-with-independent-work"
        )

        for source_update, expected_error in (
            (None, "requires a supported evidence_source"),
            ("unrecognized", "requires a supported evidence_source"),
        ):
            def executor(_scenario):
                result = reference_executor(scenario)
                if source_update is None:
                    result["execution_events"][0].pop("evidence_source")
                else:
                    result["execution_events"][0]["evidence_source"] = source_update
                return result

            case = run_conformance_suite([scenario], executor, prepared=prepared_execution).cases[0]
            self.assertFalse(case.passed)
            self.assertIsNone(case.result)
            self.assertIn(expected_error, case.mismatches[0])

    def test_dependency_approval_case_pack_is_exactly_two_and_comparator_ready(self):
        scenarios = load_conformance_scenarios(DEPENDENCY_CASES)
        suite = run_conformance_suite(
            scenarios,
            dependency_reference_executor,
            prepared=prepared_execution,
        )

        self.assertEqual([item["id"] for item in scenarios], ["dependency-approval-accept", "dependency-approval-reject"])
        self.assertTrue(suite.passed, suite.failures)

    def test_dependency_approval_cases_match_manifest_only_project_dependency_policy(self):
        accept, reject = load_conformance_scenarios(DEPENDENCY_CASES)

        self.assertEqual([item["kind"] for item in accept["expected"]["required_artifact_records"]], ["dependency-manifest"])
        self.assertEqual([item["kind"] for item in reject["expected"]["forbidden_artifact_records"]], ["dependency-manifest"])

    def test_dependency_approval_cases_allow_experiment_defined_criteria(self):
        scenarios = load_conformance_scenarios(DEPENDENCY_CASES)

        self.assertTrue(
            all("organizational or explicitly experiment-defined criteria" in item["task"]["eligibility"] for item in scenarios)
        )

    def test_dependency_acceptance_requires_linked_human_approval_evidence(self):
        scenario = load_conformance_scenarios(DEPENDENCY_CASES)[0]

        for mutation in (
            lambda approval: approval.update(decision_maker="automated-agent"),
            lambda approval: approval.update(evidence_refs=["unrelated-evidence"]),
        ):
            def executor(_scenario):
                result = dependency_reference_executor(scenario)
                mutation(result["approvals"][0])
                return result

            case = run_conformance_suite([deepcopy(scenario)], executor, prepared=prepared_execution).cases[0]
            self.assertFalse(case.passed)
            self.assertTrue(any("approval" in mismatch for mismatch in case.mismatches), case.mismatches)

    def test_dependency_rejection_forbids_approval_request_and_change_events(self):
        scenario = load_conformance_scenarios(DEPENDENCY_CASES)[1]

        for forbidden_event in (
            {"kind": "approval", "status": "required"},
            {"kind": "dependency-change", "status": "blocked-until-approved"},
            {"kind": "dependency-change", "status": "applied"},
        ):
            def executor(_scenario):
                result = dependency_reference_executor(scenario)
                result["execution_events"].append(forbidden_event)
                return result

            case = run_conformance_suite([deepcopy(scenario)], executor, prepared=prepared_execution).cases[0]
            self.assertFalse(case.passed)
            self.assertTrue(any("forbidden execution_events" in item for item in case.mismatches), case.mismatches)

    def test_harness_reports_semantic_mismatch(self):
        scenarios = load_conformance_scenarios(SCENARIOS)

        def broken_executor(scenario):
            result = reference_executor(scenario)
            if scenario["id"] == "tool-permission-boundary":
                result["active_roles"] = ["engineer"]
            return result

        suite = run_conformance_suite(scenarios, broken_executor, prepared=prepared_execution)

        self.assertFalse(suite.passed)
        self.assertEqual(suite.failures[0].scenario_id, "tool-permission-boundary")
        with self.assertRaises(ConformanceError):
            suite.raise_for_failures()

    def test_harness_checks_evidence_artifact_and_event_order(self):
        scenario = {
            "id": "dependency-approval-accepted",
            "task": {"objective": "Add an approved dependency"},
            "expected": {
                "status": "completed",
                "active_roles": ["engineer", "tech-owner", "program-manager"],
                "required_evidence_records": [
                    {"kind": "dependency-assessment", "source": "external-tool", "status": "passed", "require_references": True}
                ],
                "required_artifact_records": [{"kind": "dependency-manifest", "status": "changed"}],
                "required_event_order": [
                    {"kind": "approval", "status": "approved"},
                    {"kind": "repository-change", "status": "applied"},
                ],
                "event_order_constraints": [{
                    "event": {"kind": "repository-change", "status": "applied"},
                    "after": {"kind": "approval", "status": "approved"},
                }],
            },
        }

        def executor(_scenario):
            result = reference_executor(scenario)
            result["active_roles"] = scenario["expected"]["active_roles"]
            result["run"] = {"run_id": "run-1"}
            result["evidence"] = [{
                "kind": "dependency-assessment",
                "source": "external-tool",
                "status": "passed",
                "references": ["snapshot:candidate-1"],
            }]
            result["artifacts"] = [{"kind": "dependency-manifest", "status": "changed"}]
            result["execution_events"] = [
                {"kind": "approval", "status": "approved", "task_id": "conformance-task", "run_id": "run-1", "evidence_refs": ["approval-1"], "timestamp": "2026-09-28T10:00:00Z"},
                {"kind": "repository-change", "status": "applied", "task_id": "conformance-task", "run_id": "run-1", "evidence_refs": ["change-1"], "timestamp": "2026-09-28T10:01:00Z"},
            ]
            return result

        case = run_conformance_suite([scenario], executor, prepared=prepared_execution).cases[0]

        self.assertTrue(case.passed, case.mismatches)
        self.assertEqual(len(case.result["execution_events"]), 2)

    def test_harness_rejects_missing_evidence_and_preapproval_change(self):
        scenario = {
            "id": "dependency-approval-accepted",
            "task": {"objective": "Add an approved dependency"},
            "expected": {
                "status": "completed",
                "active_roles": ["engineer", "tech-owner", "program-manager"],
                "required_evidence_records": [{"kind": "dependency-assessment", "status": "passed", "require_references": True}],
                "required_event_order": [
                    {"kind": "approval", "status": "approved"},
                    {"kind": "repository-change", "status": "applied"},
                ],
                "event_order_constraints": [{
                    "event": {"kind": "repository-change", "status": "applied"},
                    "after": {"kind": "approval", "status": "approved"},
                }],
            },
        }

        def executor(_scenario):
            result = reference_executor(scenario)
            result["active_roles"] = scenario["expected"]["active_roles"]
            result["run"] = {"run_id": "run-1"}
            result["evidence"] = [{"kind": "dependency-assessment", "status": "passed"}]
            result["execution_events"] = [
                {"kind": "repository-change", "status": "applied", "task_id": "conformance-task", "run_id": "run-1", "evidence_refs": ["change-early"], "timestamp": "2026-09-28T09:59:00Z"},
                {"kind": "approval", "status": "approved", "task_id": "conformance-task", "run_id": "run-1", "evidence_refs": ["approval-1"], "timestamp": "2026-09-28T10:00:00Z"},
                {"kind": "repository-change", "status": "applied", "task_id": "conformance-task", "run_id": "run-1", "evidence_refs": ["change-late"], "timestamp": "2026-09-28T10:01:00Z"},
            ]
            return result

        case = run_conformance_suite([scenario], executor, prepared=prepared_execution).cases[0]

        self.assertFalse(case.passed)
        self.assertTrue(any("lacks references" in item for item in case.mismatches))
        self.assertTrue(any("occurred before required prerequisite" in item for item in case.mismatches))

    def test_harness_rejects_events_from_another_task_or_run(self):
        scenario = {
            "id": "dependency-approval-accepted",
            "task": {"objective": "Add an approved dependency"},
            "expected": {
                "status": "completed",
                "active_roles": ["engineer"],
                "required_event_order": [{"kind": "approval", "status": "approved"}],
            },
        }

        def executor(_scenario):
            result = reference_executor(scenario)
            result["run"] = {"run_id": "current-run"}
            result["execution_events"] = [{
                "kind": "approval",
                "status": "approved",
                "task_id": "different-task",
                "run_id": "different-run",
                "evidence_refs": ["approval-1"],
                "timestamp": "2026-09-28T10:00:00Z",
            }]
            return result

        case = run_conformance_suite([scenario], executor, prepared=prepared_execution).cases[0]

        self.assertFalse(case.passed)
        self.assertTrue(any("cannot be attributed" in item for item in case.mismatches), case.mismatches)

    def test_event_order_constraint_rejects_unattributed_early_change(self):
        scenario = {
            "id": "dependency-approval-accepted",
            "task": {"objective": "Add an approved dependency"},
            "expected": {
                "status": "completed",
                "active_roles": ["engineer"],
                "event_order_constraints": [{
                    "event": {"kind": "dependency-change", "status": "applied"},
                    "after": {"kind": "approval", "status": "approved"},
                }],
            },
        }

        def executor(_scenario):
            result = reference_executor(scenario)
            result["run"] = {"run_id": "run-1"}
            result["execution_events"] = [
                {
                    "kind": "dependency-change",
                    "status": "applied",
                    "task_id": "other-task",
                    "run_id": "run-1",
                    "evidence_refs": ["early-change"],
                    "timestamp": "2026-09-28T09:59:00Z",
                },
                {
                    "kind": "approval",
                    "status": "approved",
                    "task_id": "conformance-task",
                    "run_id": "run-1",
                    "evidence_refs": ["approval"],
                    "timestamp": "2026-09-28T10:00:00Z",
                },
                {
                    "kind": "dependency-change",
                    "status": "applied",
                    "task_id": "conformance-task",
                    "run_id": "run-1",
                    "evidence_refs": ["late-change"],
                    "timestamp": "2026-09-28T10:01:00Z",
                },
            ]
            return result

        case = run_conformance_suite([scenario], executor, prepared=prepared_execution).cases[0]

        self.assertFalse(case.passed)
        self.assertTrue(any("cannot be attributed" in item for item in case.mismatches), case.mismatches)


if __name__ == "__main__":
    unittest.main()
