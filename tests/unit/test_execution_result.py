import unittest

from agentcaravan.execution_result import (
    ExecutionResultError,
    build_checkpoint_resume_result,
    build_degraded_result,
    build_idempotent_replay_result,
    build_interrupted_result,
    normalize_execution_result,
    validate_normalized_execution_result,
)
from agentcaravan.orchestration import prepare_execution
from agentcaravan.schema_validation import validate_packaged_artifact


def prepared_execution():
    resolved = {
        "status": "pass",
        "context": {
            "organization_catalog_id": "example-organization",
            "team_instance_id": "example-team",
            "team_blueprint_id": "information-technology-core-team",
            "runtime_profile_id": "example-runtime-profile",
            "execution_profile_id": "example-execution-profile",
        },
        "effective_roles": [
            {"id": "engineer", "source_chain": ["engineer"]},
            {"id": "quality-engineer", "source_chain": ["quality-engineer"]},
        ],
        "runtime": {"adapter_id": "example-runtime", "degraded_capabilities": []},
        "execution_profile": {
            "entry_roles": ["engineer"],
            "activation_policy": {"primary_roles": ["engineer"], "supporting_roles": ["quality-engineer"]},
            # Most tests exercise result fields unrelated to stage completion.
            # Dedicated contract tests below make this stage unconditional.
            "stages": [{"id": "implementation", "roles": ["engineer"], "condition": "fixture stage"}],
            "reasoning_policy": {"default": "standard"},
            "communication": {"requires_structured_handoff": True, "allowed_role_handoffs": []},
            "escalation": {},
            "required_outputs": ["completion record"],
        },
    }
    return prepare_execution(resolved, {"task_id": "task-1", "objective": "Implement a bounded change"})


class ExecutionResultTests(unittest.TestCase):
    def test_assesses_declared_workflow_criteria_with_completed_assessor_and_evidence(self):
        prepared = prepared_execution()
        prepared["plan"]["termination"] = {
            "success_criteria": [
                {"id": "quality-passed", "description": "Quality checks passed.", "assessor_roles": ["quality-engineer"]}
            ]
        }
        result = normalize_execution_result(
            prepared,
            {
                "status": "completed",
                "run": {"session_id": "session-1", "run_id": "run-1"},
                "role_turns": [
                    {
                        "role_turn_id": "turn-quality",
                        "task_id": "task-1",
                        "role_id": "quality-engineer",
                        "status": "completed",
                        "summary": "Reviewed the recorded quality evidence.",
                    }
                ],
                "evidence": [
                    {"evidence_id": "quality-evidence-1", "kind": "quality-evidence", "status": "passed"}
                ],
                "workflow_assessment": {
                    "criteria": [
                        {
                            "criterion_id": "quality-passed",
                            "status": "met",
                            "assessor_role_id": "quality-engineer",
                            "rationale": "The quality evidence passed.",
                            "evidence_refs": ["quality-evidence-1"],
                        }
                    ]
                },
            },
        )

        assessment = result["workflow_assessment"]
        self.assertEqual(assessment["status"], "met")
        self.assertEqual(assessment["session_id"], "session-1")
        self.assertEqual(assessment["run_id"], "run-1")
        self.assertEqual(assessment["criteria"][0]["status"], "met")
        validate_normalized_execution_result(result, prepared)
        validate_packaged_artifact(result, "execution-result.schema.json")

    def test_missing_workflow_assessment_remains_unverified(self):
        prepared = prepared_execution()
        prepared["plan"]["termination"] = {
            "success_criteria": [
                {"id": "accepted", "description": "Work was accepted.", "assessor_roles": ["quality-engineer"]}
            ]
        }

        result = normalize_execution_result(prepared, {"status": "completed"})

        self.assertEqual(result["workflow_assessment"]["status"], "unverified")
        self.assertEqual(result["workflow_assessment"]["criteria"][0]["status"], "unverified")
        self.assertIn("No assessment", result["workflow_assessment"]["criteria"][0]["rationale"])

    def test_workflow_assessment_cannot_claim_met_without_resolvable_evidence(self):
        prepared = prepared_execution()
        prepared["plan"]["termination"] = {
            "success_criteria": [
                {"id": "quality-passed", "description": "Quality passed.", "assessor_roles": ["quality-engineer"]}
            ]
        }

        with self.assertRaisesRegex(ExecutionResultError, "unknown evidence"):
            normalize_execution_result(
                prepared,
                {
                    "status": "completed",
                    "role_turns": [
                        {"role_turn_id": "turn-q", "task_id": "task-1", "role_id": "quality-engineer", "status": "completed", "summary": "Assessment"}
                    ],
                    "workflow_assessment": {
                        "criteria": [
                            {"criterion_id": "quality-passed", "status": "met", "assessor_role_id": "quality-engineer", "rationale": "Passed.", "evidence_refs": ["missing-evidence"]}
                        ]
                    },
                },
            )

    def test_blocked_execution_cannot_aggregate_to_met_workflow_assessment(self):
        prepared = prepared_execution()
        prepared["plan"]["termination"] = {
            "success_criteria": [
                {"id": "quality-passed", "description": "Quality passed.", "assessor_roles": ["quality-engineer"]}
            ]
        }

        result = normalize_execution_result(
            prepared,
            {
                "status": "blocked",
                "role_turns": [
                    {"role_turn_id": "turn-q", "task_id": "task-1", "role_id": "quality-engineer", "status": "completed", "summary": "Assessment"}
                ],
                "evidence": [{"evidence_id": "quality-1", "kind": "quality-evidence", "status": "passed"}],
                "workflow_assessment": {
                    "criteria": [
                        {"criterion_id": "quality-passed", "status": "met", "assessor_role_id": "quality-engineer", "rationale": "Passed.", "evidence_refs": ["quality-1"]}
                    ]
                },
            },
        )

        self.assertEqual(result["workflow_assessment"]["status"], "unverified")

    def test_completed_results_require_unconditional_stages_but_not_exact_output_labels(self):
        prepared = prepared_execution()
        prepared["plan"]["steps"][0]["condition"] = None
        prepared["plan"]["steps"][0]["expected_outputs"] = ["working code, tests, and documentation"]

        with self.assertRaisesRegex(ExecutionResultError, "missing planned stages"):
            normalize_execution_result(prepared, {"status": "completed"})

        result = normalize_execution_result(
            prepared,
            {"status": "completed", "completed_stages": ["implementation"]},
        )
        self.assertEqual(result["completed_stages"], ["implementation"])

    def test_simulated_metadata_does_not_bypass_required_evidence_validation(self):
        prepared = prepared_execution()
        prepared["plan"]["evidence_requirements"] = [
            {"kind": "completion-record", "required": True}
        ]
        simulated = {
            "status": "completed",
            "execution_realization": {"mode": "simulated-sequential", "native_subagents": False},
            "evidence": [{"kind": "completion-record", "status": "unverified"}],
            "metadata": {"execution_mode": "dry-run"},
        }

        with self.assertRaisesRegex(ExecutionResultError, "missing passing required evidence"):
            normalize_execution_result(prepared, simulated)

    def test_task_completion_summary_is_satisfied_by_the_normalized_lifecycle_record(self):
        prepared = prepared_execution()
        prepared["plan"]["required_outputs"] = ["task completion summary"]

        result = normalize_execution_result(prepared, {"status": "completed"})

        self.assertEqual(result["status"], "completed")

    def test_execution_events_are_preserved_in_the_normalized_result(self):
        prepared = prepared_execution()
        events = [
            {
                "event_id": "approval-1",
                "kind": "approval",
                "status": "approved",
                "task_id": "task-1",
                "timestamp": "2026-09-28T10:00:00Z",
                "evidence_refs": ["approval-record-1"],
                "metadata": {"source": "human-reviewed"},
            }
        ]

        result = normalize_execution_result(
            prepared,
            {"status": "completed", "execution_events": events},
        )

        self.assertEqual(result["execution_events"], events)
        self.assertEqual(validate_normalized_execution_result(result)["execution_events"], events)

    def test_execution_events_require_semantic_identity(self):
        prepared = prepared_execution()

        with self.assertRaisesRegex(ExecutionResultError, "execution event requires kind"):
            normalize_execution_result(
                prepared,
                {"status": "completed", "execution_events": [{"status": "approved"}]},
            )

    def test_scheduling_conformance_measures_wait_and_work_that_continues_during_wait(self):
        prepared = prepared_execution()
        prepared["plan"]["steps"][0]["role_ids"].append("quality-engineer")
        prepared["plan"]["execution_topology"] = {
            "mode": "coordinator-worker",
            "work_items": [
                {"id": "design", "stage_id": "implementation", "role_id": "quality-engineer", "purpose": "Resolve the independent design question"},
                {"id": "implement", "stage_id": "implementation", "role_id": "engineer", "purpose": "Implement after the design decision", "depends_on": ["design"]},
            ],
        }
        def event(work_item_id, role_id, status, timestamp, dependencies=None):
            return {
                "kind": "work-item",
                "work_item_id": work_item_id,
                "role_id": role_id,
                "stage_id": "implementation",
                "status": status,
                "timestamp": timestamp,
                "dependency_ids": dependencies or [],
                "evidence_source": "runtime-receipt",
                "evidence_refs": [f"receipt-{work_item_id}-{status}-{timestamp}"],
            }

        result = normalize_execution_result(
            prepared,
            {
                "status": "completed",
                "execution_events": [
                    event("implement", "engineer", "queued", "2026-10-01T10:00:00Z", ["design"]),
                    event("implement", "engineer", "waiting", "2026-10-01T10:01:00Z", ["design"]),
                    event("design", "quality-engineer", "started", "2026-10-01T10:02:00Z"),
                    event("design", "quality-engineer", "completed", "2026-10-01T10:05:00Z"),
                    event("implement", "engineer", "resumed", "2026-10-01T10:06:00Z", ["design"]),
                    event("implement", "engineer", "completed", "2026-10-01T10:10:00Z", ["design"]),
                ],
            },
        )

        scheduling = result["scheduling_conformance"]
        self.assertEqual(scheduling["status"], "pass")
        self.assertEqual(scheduling["wait_durations_seconds"], {"implement": 300.0})
        self.assertEqual(scheduling["work_during_wait"], [{"work_item_id": "implement", "other_work_item_ids": ["design"]}])
        validate_packaged_artifact(result, "execution-result.schema.json")

    def test_scheduling_conformance_rejects_work_started_before_dependency_completion(self):
        prepared = prepared_execution()
        prepared["plan"]["execution_topology"] = {
            "mode": "coordinator-worker",
            "work_items": [
                {"id": "design", "stage_id": "implementation", "role_id": "engineer", "purpose": "Design"},
                {"id": "implement", "stage_id": "implementation", "role_id": "engineer", "purpose": "Implement", "depends_on": ["design"]},
            ],
        }
        events = [
            {"kind": "work-item", "work_item_id": "design", "role_id": "engineer", "stage_id": "implementation", "status": "started", "timestamp": "2026-10-01T10:00:00Z", "evidence_source": "runtime-receipt", "evidence_refs": ["receipt-design-start"]},
            {"kind": "work-item", "work_item_id": "implement", "role_id": "engineer", "stage_id": "implementation", "dependency_ids": ["design"], "status": "started", "timestamp": "2026-10-01T10:01:00Z", "evidence_source": "runtime-receipt", "evidence_refs": ["receipt-implement-start"]},
            {"kind": "work-item", "work_item_id": "implement", "role_id": "engineer", "stage_id": "implementation", "dependency_ids": ["design"], "status": "completed", "timestamp": "2026-10-01T10:02:00Z", "evidence_source": "runtime-receipt", "evidence_refs": ["receipt-implement-completed"]},
            {"kind": "work-item", "work_item_id": "design", "role_id": "engineer", "stage_id": "implementation", "status": "completed", "timestamp": "2026-10-01T10:03:00Z", "evidence_source": "runtime-receipt", "evidence_refs": ["receipt-design-completed"]},
        ]
        result = normalize_execution_result(prepared, {"status": "completed", "execution_events": events})

        self.assertEqual(result["scheduling_conformance"]["status"], "failed")
        self.assertTrue(any("started before dependency design completed" in item for item in result["scheduling_conformance"]["issues"]))

    def test_simulated_execution_without_work_item_events_is_unverified(self):
        prepared = prepared_execution()
        prepared["plan"]["execution_topology"] = {
            "mode": "coordinator-worker",
            "work_items": [
                {"id": "implementation", "stage_id": "implementation", "role_id": "engineer", "purpose": "Implement the task"},
            ],
        }

        result = normalize_execution_result(
            prepared,
            {
                "status": "completed",
                "completed_stages": ["implementation"],
                "execution_realization": {"mode": "simulated-sequential", "native_subagents": False},
            },
            allow_unverified_required_evidence=True,
        )

        self.assertEqual(result["scheduling_conformance"]["status"], "unverified")
        self.assertEqual(result["scheduling_conformance"]["observed_work_item_ids"], [])
        self.assertTrue(
            any("work-item lifecycle is unverified for simulated execution" in issue
                for issue in result["scheduling_conformance"]["issues"])
        )
        validate_normalized_execution_result(result)

    def test_completed_live_execution_without_work_item_events_fails(self):
        prepared = prepared_execution()
        prepared["plan"]["execution_topology"] = {
            "mode": "coordinator-worker",
            "work_items": [
                {"id": "implementation", "stage_id": "implementation", "role_id": "engineer", "purpose": "Implement the task"},
            ],
        }

        result = normalize_execution_result(
            prepared,
            {
                "status": "completed",
                "completed_stages": ["implementation"],
                "execution_realization": {"mode": "native-sequential", "native_subagents": False},
            },
            allow_unverified_required_evidence=True,
        )

        self.assertEqual(result["scheduling_conformance"]["status"], "failed")
        self.assertTrue(
            any("completed result has no lifecycle events" in issue
                for issue in result["scheduling_conformance"]["issues"])
        )

    def test_no_dispatch_is_not_reported_as_topology_conformant(self):
        prepared = prepared_execution()
        prepared["plan"]["execution_topology"] = {
            "mode": "sequential",
            "parallel_lanes": [{"id": "quality-prep", "stage_id": "implementation", "role_ids": ["quality-engineer"], "purpose": "testability"}],
        }
        result = normalize_execution_result(
            prepared,
            {"status": "blocked", "execution_realization": {"mode": "unreported", "native_subagents": False}},
        )

        self.assertEqual(result["topology_conformance"]["status"], "not-applicable")
        self.assertIn("no runtime dispatch", result["topology_conformance"]["issues"][0])
        validate_normalized_execution_result(result)

    def test_execution_diagnostics_are_opt_in_and_topology_is_reported(self):
        prepared = prepared_execution()
        prepared["plan"]["context"]["team_context"] = {"preferred_roles": ["quality-engineer"]}
        prepared["plan"]["execution_topology"] = {
            "mode": "sequential",
            "parallel_lanes": [{"id": "quality-prep", "stage_id": "implementation", "role_ids": ["engineer"], "purpose": "independent checks"}],
            "serial_fallback": {"mode": "run-in-order", "lane_ids": ["quality-prep"]},
        }
        base_runtime_result = {
            "status": "completed",
            "execution_realization": {"mode": "native-parallel", "native_subagents": True, "parallel_lane_ids": ["undeclared"]},
            "role_turns": [{"role_turn_id": "turn-1", "task_id": "task-1", "stage_id": "implementation", "role_id": "engineer", "status": "completed", "worker_ref": "worker-1", "summary": "private text"}],
        }

        ordinary = normalize_execution_result(prepared, base_runtime_result)
        self.assertNotIn("execution_diagnostics", ordinary)
        self.assertEqual(ordinary["topology_conformance"]["status"], "failed")

        prepared["plan"]["task"]["execution_diagnostics"] = True
        base_runtime_result["execution_realization"]["parallel_lane_ids"] = ["quality-prep"]
        self.assertEqual(normalize_execution_result(prepared, base_runtime_result)["topology_conformance"]["status"], "unverified")
        base_runtime_result["execution_realization"]["mode"] = "native-sequential"
        self.assertEqual(normalize_execution_result(prepared, base_runtime_result)["topology_conformance"]["status"], "failed")
        base_runtime_result["execution_realization"]["mode"] = "native-parallel"
        diagnostic = normalize_execution_result(prepared, base_runtime_result)
        self.assertEqual(diagnostic["execution_diagnostics"]["role_selection"]["preference_semantics"], "guidance-only")
        quality_selection = next(item for item in diagnostic["execution_diagnostics"]["role_selection"]["assignments"] if item["role_id"] == "quality-engineer")
        self.assertFalse(quality_selection["observed_turn_statuses"])
        self.assertEqual(diagnostic["execution_diagnostics"]["role_dispatch"][0]["worker_ref"], "worker-1")
        self.assertNotIn("summary", diagnostic["execution_diagnostics"]["role_dispatch"][0])

        base_runtime_result["execution_realization"]["parallel_lane_evidence"] = [
            {"lane_id": "quality-prep", "stage_id": "implementation", "role_id": "engineer", "worker_ref": "worker-1"}
        ]
        self.assertEqual(normalize_execution_result(prepared, base_runtime_result)["topology_conformance"]["status"], "pass")
        self.assertEqual(normalize_execution_result(prepared, base_runtime_result)["parallel_timing_conformance"]["status"], "unverified")
        base_runtime_result["execution_realization"]["parallel_lane_evidence"][0]["worker_ref"] = "other-worker"
        self.assertEqual(normalize_execution_result(prepared, base_runtime_result)["topology_conformance"]["status"], "failed")

    def test_parallel_timing_requires_and_checks_overlapping_lane_intervals(self):
        prepared = prepared_execution()
        prepared["plan"]["execution_topology"] = {
            "mode": "sequential",
            "parallel_lanes": [
                {"id": "quality-prep", "stage_id": "implementation", "role_ids": ["quality-engineer"], "purpose": "testability"},
                {"id": "architecture-research", "stage_id": "implementation", "role_ids": ["engineer"], "purpose": "design"},
            ],
        }
        prepared["plan"]["steps"][0]["role_ids"].append("quality-engineer")
        runtime_result = {
            "status": "completed",
            "execution_realization": {
                "mode": "native-parallel",
                "native_subagents": True,
                "parallel_lane_evidence": [
                    {"lane_id": "quality-prep", "stage_id": "implementation", "role_id": "quality-engineer", "worker_ref": "worker-q", "started_at": "2026-09-25T10:00:00Z", "completed_at": "2026-09-25T10:05:00Z"},
                    {"lane_id": "architecture-research", "stage_id": "implementation", "role_id": "engineer", "worker_ref": "worker-e", "started_at": "2026-09-25T10:02:00Z", "completed_at": "2026-09-25T10:07:00Z"},
                ],
            },
            "role_turns": [
                {"role_turn_id": "turn-q", "task_id": "task-1", "stage_id": "implementation", "role_id": "quality-engineer", "status": "completed", "worker_ref": "worker-q", "summary": "testability"},
                {"role_turn_id": "turn-e", "task_id": "task-1", "stage_id": "implementation", "role_id": "engineer", "status": "completed", "worker_ref": "worker-e", "summary": "design"},
            ],
        }
        result = normalize_execution_result(prepared, runtime_result)
        self.assertEqual(result["parallel_timing_conformance"]["status"], "pass")

        runtime_result["execution_realization"]["parallel_lane_evidence"][1]["started_at"] = "2026-09-25T10:05:00Z"
        runtime_result["execution_realization"]["parallel_lane_evidence"][1]["completed_at"] = "2026-09-25T10:07:00Z"
        self.assertEqual(normalize_execution_result(prepared, runtime_result)["parallel_timing_conformance"]["status"], "failed")

    def test_parallel_realization_without_lane_telemetry_is_unverified(self):
        result = normalize_execution_result(
            prepared_execution(),
            {"status": "completed", "execution_realization": {"mode": "native-parallel", "native_subagents": True}},
        )
        self.assertEqual(result["topology_conformance"]["status"], "unverified")
        self.assertIn("topology was not declared", result["topology_conformance"]["issues"][0])

    def test_normalizes_generic_runtime_result_to_prepared_identity(self):
        result = normalize_execution_result(
            prepared_execution(),
            {
                "status": "completed",
                "active_roles": ["engineer"],
                "completed_stages": ["implementation"],
                "evidence": [{"kind": "test", "status": "passed"}],
            },
            scenario_id="simple-sequential-execution",
        )

        self.assertEqual(result["artifact_type"], "normalized-execution-result")
        self.assertEqual(result["task_id"], "task-1")
        self.assertEqual(result["plan_id"], "task-1-execution-plan")
        self.assertEqual(result["parallel_timing_conformance"]["status"], "not-applicable")
        self.assertEqual(result["scenario_id"], "simple-sequential-execution")
        validate_normalized_execution_result(result, prepared_execution())

    def test_builds_interrupted_and_resumed_results(self):
        prepared = prepared_execution()
        interrupted = build_interrupted_result(
            prepared,
            {
                "checkpoint_id": "checkpoint-1",
                "task_id": "task-1",
                "status": "accepted",
                "resumable": True,
                "stage_id": "implementation",
                "source": "runtime",
                "created_at": "2026-08-21T12:00:00Z",
            },
            active_roles=["engineer"],
            scenario_id="interrupted-run",
        )
        self.assertEqual(interrupted["status"], "interrupted")
        self.assertTrue(interrupted["resume"]["required"])
        self.assertTrue(interrupted["checkpoint"]["resumable"])

        resumed = build_checkpoint_resume_result(
            prepared,
            {
                "checkpoint_id": "checkpoint-1",
                "task_id": "task-1",
                "status": "resumed",
                "resumable": True,
                "stage_id": "implementation",
                "source": "runtime",
                "created_at": "2026-08-21T12:00:00Z",
                "resumed_at": "2026-08-21T12:30:00Z",
            },
            active_roles=["engineer", "quality-engineer"],
            replay_from_stage="implementation",
            scenario_id="checkpoint-resume",
        )
        self.assertEqual(resumed["status"], "completed")
        self.assertEqual(resumed["resume"]["checkpoint_status"], "resumed")
        self.assertTrue(resumed["resume"]["prior_run_preserved"])

    def test_builds_idempotent_replay_without_second_side_effect(self):
        result = build_idempotent_replay_result(
            prepared_execution(),
            {
                "idempotency_key": "mutation-1",
                "operation": "apply-remote-change",
                "scope": "external-system",
                "status": "replayed",
                "side_effect_applied": False,
            },
            active_roles=["engineer"],
        )

        self.assertEqual(result["metadata"]["idempotency_status"], "replayed")
        self.assertEqual(result["metadata"]["side_effect_count"], 1)
        self.assertFalse(result["idempotency_records"][0]["side_effect_applied"])

    def test_builds_degraded_result_with_explicit_capability_mode(self):
        result = build_degraded_result(
            prepared_execution(),
            ["parallel_lane_execution"],
            active_roles=["engineer", "quality-engineer"],
            serial_fallback_recorded=True,
            scenario_id="degraded-capability-fallback",
        )

        self.assertEqual(result["status"], "degraded")
        self.assertEqual(result["degraded_capabilities"][0]["capability"], "parallel_lane_execution")
        self.assertEqual(result["degraded_capabilities"][0]["mode"], "adapted")
        self.assertTrue(result["metadata"]["serial_fallback_recorded"])

    def test_rejects_invalid_resume_and_duplicate_idempotency(self):
        prepared = prepared_execution()
        with self.assertRaises(ExecutionResultError):
            build_checkpoint_resume_result(
                prepared,
                {"checkpoint_id": "checkpoint-1", "task_id": "task-1", "status": "resumed", "resumable": False},
            )
        with self.assertRaises(ExecutionResultError):
            normalize_execution_result(
                prepared,
                {
                    "status": "completed",
                    "idempotency_records": [
                        {"idempotency_key": "same", "operation": "one", "status": "applied", "side_effect_applied": True},
                        {"idempotency_key": "same", "operation": "two", "status": "replayed", "side_effect_applied": False},
                    ],
                },
            )

    def test_validates_native_delegation_and_worker_reference(self):
        prepared = prepared_execution()
        result = normalize_execution_result(
            prepared,
            {
                "status": "completed",
                "active_roles": ["engineer"],
                "execution_realization": {
                    "mode": "native-parallel",
                    "native_subagents": True,
                    "delegation": {
                        "support_level": "native",
                        "execution_mode": "parallel",
                        "ownership": "caller-retains",
                        "child_tasks": [
                            {
                                "delegation_id": "delegation-1",
                                "role_id": "engineer",
                                "worker_ref": "worker-1",
                                "status": "completed",
                            }
                        ],
                    },
                },
                "role_turns": [
                    {
                        "role_turn_id": "turn-1",
                        "task_id": "task-1",
                        "role_id": "engineer",
                        "stage_id": "implementation",
                        "worker_ref": "worker-1",
                        "status": "completed",
                        "summary": "Completed bounded implementation inspection.",
                    }
                ],
                "verification": [],
            },
        )

        self.assertEqual(result["execution_realization"]["delegation"]["support_level"], "native")
        evidence = result["reasoning_evidence"][0]
        self.assertEqual(evidence["dispatch_status"], "accepted")
        self.assertEqual(evidence["telemetry_status"], "unverified")
        self.assertEqual(evidence["worker_ref"], "worker-1")

    def test_accepts_runtime_observed_reasoning_evidence(self):
        result = normalize_execution_result(
            prepared_execution(),
            {
                "status": "completed",
                "reasoning_evidence": [
                    {
                        "stage_id": "implementation",
                        "role_id": "engineer",
                        "requested_level": "standard",
                        "requested_runtime_value": "medium",
                        "effective_level": "standard",
                        "effective_runtime_value": "medium",
                        "status": "runtime-observed",
                        "dispatch_status": "accepted",
                        "telemetry_status": "observed",
                        "evidence_source": "runtime-response",
                        "worker_ref": "worker-1",
                    }
                ],
            },
        )

        self.assertEqual(result["reasoning_evidence"][0]["status"], "runtime-observed")

    def test_accepts_complete_runtime_reasoning_evidence_for_plan_assignment(self):
        prepared = prepared_execution()
        prepared["plan"]["reasoning_assignments"][0]["requested_runtime_value"] = "medium"
        result = normalize_execution_result(
            prepared,
            {
                "status": "completed",
                "completed_stages": ["implementation"],
                "reasoning_evidence": [
                    {
                        "stage_id": "implementation",
                        "role_id": "engineer",
                        "requested_level": "standard",
                        "requested_runtime_value": "medium",
                        "status": "unverified",
                    }
                ],
            },
        )

        self.assertEqual(result["reasoning_evidence"][0]["requested_level"], "standard")

    def test_rejects_unknown_reasoning_evidence_assignment(self):
        with self.assertRaises(ExecutionResultError):
            normalize_execution_result(
                prepared_execution(),
                {
                    "status": "completed",
                    "reasoning_evidence": [
                        {
                            "stage_id": "implementation",
                            "role_id": "quality-engineer",
                            "requested_level": "standard",
                            "status": "unverified",
                        }
                    ],
                },
            )

    def test_rejects_duplicate_reasoning_evidence_assignment(self):
        evidence = {
            "stage_id": "implementation",
            "role_id": "engineer",
            "requested_level": "standard",
            "status": "unverified",
        }
        with self.assertRaises(ExecutionResultError):
            normalize_execution_result(
                prepared_execution(),
                {"status": "completed", "reasoning_evidence": [evidence, dict(evidence)]},
            )

    def test_rejects_mismatched_reasoning_level_or_runtime_value(self):
        prepared = prepared_execution()
        prepared["plan"]["reasoning_assignments"][0]["requested_runtime_value"] = "medium"
        base_evidence = {
            "stage_id": "implementation",
            "role_id": "engineer",
            "requested_level": "standard",
            "requested_runtime_value": "medium",
            "status": "unverified",
        }
        for field, value in (("requested_level", "deep"), ("requested_runtime_value", "high")):
            evidence = dict(base_evidence)
            evidence[field] = value
            with self.assertRaises(ExecutionResultError):
                normalize_execution_result(
                    prepared,
                    {"status": "completed", "reasoning_evidence": [evidence]},
                )

    def test_projects_missing_runtime_reasoning_evidence_in_plan_order(self):
        prepared = prepared_execution()
        prepared["plan"]["steps"].append(
            {
                "step_id": "quality",
                "kind": "task",
                "role_ids": ["quality-engineer"],
                "mode": "sequential",
                "condition": None,
                "expected_outputs": [],
            }
        )
        prepared["plan"]["reasoning_assignments"].append(
            {
                "stage_id": "quality",
                "role_id": "quality-engineer",
                "level": "deep",
                "source": "default",
            }
        )

        result = normalize_execution_result(
            prepared,
            {
                "status": "completed",
                "completed_stages": ["implementation", "quality"],
                "reasoning_evidence": [
                    {
                        "stage_id": "quality",
                        "role_id": "quality-engineer",
                        "requested_level": "deep",
                        "status": "runtime-observed",
                        "effective_level": "deep",
                        "telemetry_status": "observed",
                        "evidence_source": "runtime-response",
                    }
                ],
            },
        )

        self.assertEqual(
            [(item["stage_id"], item["role_id"]) for item in result["reasoning_evidence"]],
            [("implementation", "engineer"), ("quality", "quality-engineer")],
        )
        self.assertEqual(result["reasoning_evidence"][0]["evidence_source"], "plan-projection")
        self.assertEqual(result["reasoning_evidence"][1]["status"], "runtime-observed")

    def test_uses_plan_projection_for_omitted_or_empty_reasoning_evidence(self):
        prepared = prepared_execution()
        for runtime_result in ({"status": "completed"}, {"status": "completed", "reasoning_evidence": []}):
            result = normalize_execution_result(prepared, runtime_result)

            self.assertEqual(len(result["reasoning_evidence"]), 1)
            self.assertEqual(result["reasoning_evidence"][0]["status"], "unverified")
            self.assertEqual(result["reasoning_evidence"][0]["evidence_source"], "plan-projection")

    def test_accepts_runtime_reasoning_evidence_for_legacy_plan_without_assignments(self):
        prepared = prepared_execution()
        del prepared["plan"]["reasoning_assignments"]

        result = normalize_execution_result(
            prepared,
            {
                "status": "completed",
                "reasoning_evidence": [
                    {
                        "stage_id": "implementation",
                        "role_id": "engineer",
                        "requested_level": "standard",
                        "status": "unverified",
                    }
                ],
            },
        )

        self.assertEqual(result["reasoning_evidence"][0]["role_id"], "engineer")

    def test_rejects_accepted_reasoning_without_worker_reference(self):
        with self.assertRaises(ExecutionResultError):
            normalize_execution_result(
                prepared_execution(),
                {
                    "status": "completed",
                    "reasoning_evidence": [
                        {
                            "stage_id": "implementation",
                            "role_id": "engineer",
                            "requested_level": "standard",
                            "status": "unverified",
                            "dispatch_status": "accepted",
                            "telemetry_status": "unverified",
                        }
                    ],
                },
            )


if __name__ == "__main__":
    unittest.main()
