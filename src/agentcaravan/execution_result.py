"""Normalize runtime outcomes at the Agent Caravan execution boundary."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Iterable

from .handoff import TaskHandoffError, validate_task_handoff


NORMALIZED_RESULT_STATUSES = {
    "completed",
    "interrupted",
    "blocked",
    "blocked-until-approved",
    "failed",
    "escalated",
    "degraded",
    "cancelled",
}
DEGRADED_CAPABILITY_MODES = {"adapted", "externalized"}
EXECUTION_REALIZATION_MODES = {
    "native-parallel",
    "native-sequential",
    "simulated-sequential",
    "human-gated",
    "unreported",
}
REASONING_EVIDENCE_STATUSES = {"unverified", "runtime-observed", "failed"}
REASONING_DISPATCH_STATUSES = {"not-attempted", "accepted", "failed", "unknown"}
REASONING_TELEMETRY_STATUSES = {"unverified", "observed", "unavailable", "failed"}
WORK_ITEM_EVIDENCE_SOURCES = {"adapter-observed", "runtime-receipt", "agent-reported", "simulated"}
OBSERVED_WORK_ITEM_EVIDENCE_SOURCES = {"adapter-observed", "runtime-receipt"}


class ExecutionResultError(ValueError):
    """Raised when a runtime result cannot satisfy the portable result contract."""


def _parts(prepared: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(prepared, dict) or prepared.get("status") != "ready":
        raise ExecutionResultError("execution result requires a ready prepared execution")
    plan = prepared.get("plan")
    context = prepared.get("context")
    if not isinstance(plan, dict) or not isinstance(context, dict):
        raise ExecutionResultError("prepared execution is missing plan or context")
    task = plan.get("task")
    if not isinstance(task, dict) or not task.get("task_id"):
        raise ExecutionResultError("prepared execution is missing task identity")
    if not plan.get("id"):
        raise ExecutionResultError("prepared execution is missing plan identity")
    return plan, context


def _strings(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ExecutionResultError(f"{field} must be a list of non-empty strings")
    return list(value)


def _records(value: Any, field: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ExecutionResultError(f"{field} must be a list of objects")
    return [dict(item) for item in value]


def _validate_execution_realization(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ExecutionResultError("execution_realization must be an object")
    mode = value.get("mode")
    if mode not in EXECUTION_REALIZATION_MODES:
        raise ExecutionResultError(f"unsupported execution realization mode: {mode}")
    if "native_subagents" in value and not isinstance(value["native_subagents"], bool):
        raise ExecutionResultError("execution_realization native_subagents must be a boolean")
    lane_ids = _strings(value.get("parallel_lane_ids", []), "execution_realization parallel_lane_ids")
    if len(lane_ids) != len(set(lane_ids)):
        raise ExecutionResultError("execution_realization parallel_lane_ids must be unique")
    lane_evidence = _records(value.get("parallel_lane_evidence", []), "execution_realization parallel_lane_evidence")
    lane_role_pairs = set()
    for item in lane_evidence:
        for field in ("lane_id", "stage_id", "role_id", "worker_ref"):
            if not isinstance(item.get(field), str) or not item[field]:
                raise ExecutionResultError(f"parallel lane evidence requires {field}")
        pair = (item["lane_id"], item["role_id"])
        if pair in lane_role_pairs:
            raise ExecutionResultError("parallel lane evidence contains duplicate lane/role entries")
        lane_role_pairs.add(pair)
        for field in ("started_at", "completed_at"):
            if field in item and not isinstance(item[field], str):
                raise ExecutionResultError(f"parallel lane evidence {field} must be an ISO timestamp")
    delegation = value.get("delegation")
    if delegation is not None:
        if not isinstance(delegation, dict):
            raise ExecutionResultError("execution_realization delegation must be an object")
        for field in ("support_level", "execution_mode", "ownership"):
            if not isinstance(delegation.get(field), str) or not delegation[field]:
                raise ExecutionResultError(f"delegation requires {field}")
        if delegation["support_level"] not in {"native", "adapted", "externalized", "unsupported"}:
            raise ExecutionResultError("unsupported delegation support level")
        if delegation["execution_mode"] not in {"parallel", "sequential", "mixed", "none"}:
            raise ExecutionResultError("unsupported delegation execution mode")
        if delegation["ownership"] not in {"caller-retains", "receiver-takes-over", "code-controlled", "model-routed-within-boundary"}:
            raise ExecutionResultError("unsupported delegation ownership")
        for worker in _records(delegation.get("child_tasks", []), "delegation child_tasks"):
            for field in ("delegation_id", "role_id", "status"):
                if not isinstance(worker.get(field), str) or not worker[field]:
                    raise ExecutionResultError(f"delegated worker requires {field}")
            if worker["status"] not in {"started", "completed", "blocked", "failed", "cancelled"}:
                raise ExecutionResultError(f"unsupported delegated worker status: {worker['status']}")
    if value.get("native_subagents") is True and value["mode"] not in {"native-parallel", "native-sequential"}:
        raise ExecutionResultError("native subagents require a native execution realization mode")
    return dict(value)


def validate_execution_realization(value: Any) -> dict[str, Any]:
    """Validate the runtime realization declared by an execution receipt."""
    return _validate_execution_realization(value)


def _validate_role_turns(value: Any) -> list[dict[str, Any]]:
    turns = _records(value, "role_turns")
    valid_statuses = {"projected", "started", "completed", "blocked", "unverified"}
    for turn in turns:
        for field in ("role_turn_id", "task_id", "role_id", "status", "summary"):
            if not isinstance(turn.get(field), str) or not turn[field]:
                raise ExecutionResultError(f"role turn requires {field}")
        if turn["status"] not in valid_statuses:
            raise ExecutionResultError(f"unsupported role turn status: {turn['status']}")
        if "worker_ref" in turn and (not isinstance(turn["worker_ref"], str) or not turn["worker_ref"]):
            raise ExecutionResultError("role turn worker_ref must be a non-empty string")
    return turns


def _validate_result_against_plan(
    result: dict[str, Any], plan: dict[str, Any], *, allow_unverified_required_evidence: bool = False
) -> None:
    """Reject completion claims that exceed or omit the portable plan contract."""
    assignments = {
        item.get("role_id") for item in plan.get("role_assignments", []) if isinstance(item, dict)
    }
    steps = {
        item.get("step_id"): item for item in plan.get("steps", []) if isinstance(item, dict)
    }
    active_roles = set(result.get("active_roles", []))
    unknown_roles = active_roles - assignments
    if unknown_roles:
        raise ExecutionResultError(f"result reports roles not assigned by the plan: {sorted(unknown_roles)}")
    completed_stages = set(result.get("completed_stages", []))
    unknown_stages = completed_stages - set(steps)
    if unknown_stages:
        raise ExecutionResultError(f"result reports stages not declared by the plan: {sorted(unknown_stages)}")

    for turn in result.get("role_turns", []):
        role_id = turn["role_id"]
        if role_id not in assignments:
            raise ExecutionResultError(f"role turn reports a role not assigned by the plan: {role_id}")
        stage_id = turn.get("stage_id")
        if stage_id is not None:
            step = steps.get(stage_id)
            if step is None or role_id not in step.get("role_ids", []):
                raise ExecutionResultError(f"role turn {stage_id}/{role_id} is not authorized by the plan")

    for handoff in result.get("handoffs", []):
        if handoff.get("artifact_type") == "task-handoff":
            try:
                validate_task_handoff(handoff, plan=plan, task_id=result["task_id"])
            except TaskHandoffError as error:
                raise ExecutionResultError(f"result contains an unauthorized task handoff: {error}") from error

    if result["status"] != "completed":
        return

    # An unconditional task step is part of the completion contract. Conditional
    # steps may be skipped when their condition is false or unresolved.
    required_stages = {
        step_id for step_id, step in steps.items()
        if step.get("kind") == "task" and not step.get("condition")
    }
    missing_stages = required_stages - completed_stages
    if missing_stages:
        raise ExecutionResultError(f"completed result is missing planned stages: {sorted(missing_stages)}")

    evidence = result.get("evidence", [])
    artifacts = result.get("artifacts", [])
    verification = result.get("verification", [])
    output_records = artifacts + evidence + verification + result.get("handoffs", []) + result.get("decisions", [])
    available_output_names = {
        value.casefold().replace("-", " ")
        for item in output_records
        for field in ("kind", "name", "type", "artifact_type", "output", "required_output")
        if isinstance((value := item.get(field)), str)
    }
    evidence_requirements = [
        requirement for requirement in plan.get("evidence_requirements", [])
        if isinstance(requirement, dict) and requirement.get("required") is True
    ]
    for requirement in evidence_requirements:
        kind = requirement.get("kind")
        stage_id = requirement.get("stage_id")
        owner_role = requirement.get("owner_role")
        candidates = evidence + artifacts + verification
        satisfied = False
        for item in candidates:
            if item.get("kind") != kind:
                continue
            if not isinstance(item.get("kind"), str) or not item["kind"]:
                raise ExecutionResultError("required evidence record kind must be a non-empty string")
            if not isinstance(item.get("status"), str) or not item["status"]:
                raise ExecutionResultError(f"required evidence {kind!r} must have a non-empty status")
            for field in ("stage_id", "role_id", "owner_role"):
                if field in item and item[field] is not None and (
                    not isinstance(item[field], str) or not item[field]
                ):
                    raise ExecutionResultError(f"required evidence {kind!r} has invalid {field}")
            observed_owner = item.get("role_id", item.get("owner_role"))
            if (
                (
                    item["status"] == "passed"
                    or (allow_unverified_required_evidence and item["status"] == "unverified")
                )
                and (stage_id is None or item.get("stage_id") == stage_id)
                and (owner_role is None or observed_owner == owner_role)
            ):
                satisfied = True
                break
        if not satisfied:
            raise ExecutionResultError(
                f"completed result is missing passing required evidence {kind!r}"
                + (f" for stage {stage_id}" if stage_id else "")
            )

    required_outputs = plan.get("required_outputs", [])
    missing_outputs = []
    for output in required_outputs:
        normalized = output.casefold().replace("-", " ")
        # These records are owned by the framework execution lifecycle: the task
        # record is created before dispatch, while this normalized result is the
        # completion record persisted after validation. They cannot be required
        # from the runtime's output payload.
        if normalized in {"task record", "completion record", "task completion summary"}:
            continue
        if normalized == "handoff records":
            if result.get("handoffs") or (
                allow_unverified_required_evidence
                and "handoff record" in available_output_names
            ):
                continue
        elif normalized in available_output_names:
            continue
        missing_outputs.append(output)
    if missing_outputs:
        raise ExecutionResultError(f"completed result is missing required outputs: {missing_outputs}")


WORKFLOW_ASSESSMENT_STATUSES = {"met", "not-met", "unverified", "not-applicable"}


def _assessment_evidence_ids(result: dict[str, Any]) -> set[str]:
    identifiers = set()
    for field, id_fields in (
        ("evidence", ("evidence_id",)),
        ("verification", ("verification_id", "evidence_id")),
        ("decisions", ("decision_id",)),
        ("approvals", ("approval_id",)),
        ("artifacts", ("artifact_id",)),
        ("handoffs", ("handoff_id", "id")),
    ):
        for record in result.get(field, []):
            if not isinstance(record, dict):
                continue
            for id_field in id_fields:
                value = record.get(id_field)
                if isinstance(value, str) and value:
                    identifiers.add(value)
    return identifiers


def _workflow_assessment_status(criteria: list[dict[str, Any]], result: dict[str, Any]) -> str:
    if not criteria:
        return "not-applicable"
    statuses = {item["status"] for item in criteria}
    if "not-met" in statuses:
        return "not-met"
    if (
        result.get("status") != "completed"
        or result.get("unresolved_conditions")
        or result.get("degraded_capabilities")
        or result.get("failures")
    ):
        return "unverified"
    if statuses <= {"met", "not-applicable"} and "met" in statuses:
        return "met"
    if statuses == {"not-applicable"}:
        return "not-applicable"
    return "unverified"


def _build_workflow_assessment(
    plan: dict[str, Any], result: dict[str, Any], supplied: Any = None
) -> dict[str, Any] | None:
    termination = plan.get("termination", {})
    definitions = termination.get("success_criteria", []) if isinstance(termination, dict) else []
    if not definitions:
        if supplied is not None:
            raise ExecutionResultError("workflow_assessment was supplied for a plan without success_criteria")
        return None

    if supplied is None:
        supplied_criteria = []
    elif isinstance(supplied, dict) and isinstance(supplied.get("criteria"), list):
        supplied_criteria = supplied["criteria"]
    else:
        raise ExecutionResultError("workflow_assessment must contain a criteria list")

    definitions_by_id = {}
    assigned_roles = {
        item.get("role_id") for item in plan.get("role_assignments", []) if isinstance(item, dict)
    }
    for definition in definitions:
        if not isinstance(definition, dict) or not isinstance(definition.get("id"), str) or not definition["id"]:
            raise ExecutionResultError("success criteria require a non-empty id")
        if definition["id"] in definitions_by_id:
            raise ExecutionResultError(f"duplicate success criterion id: {definition['id']}")
        assessor_roles = definition.get("assessor_roles")
        if (
            not isinstance(assessor_roles, list)
            or not assessor_roles
            or any(not isinstance(role, str) or not role or role not in assigned_roles for role in assessor_roles)
        ):
            raise ExecutionResultError(f"success criterion {definition['id']} has invalid assessor roles")
        definitions_by_id[definition["id"]] = definition

    supplied_by_id = {}
    for item in supplied_criteria:
        if not isinstance(item, dict) or not isinstance(item.get("criterion_id"), str):
            raise ExecutionResultError("workflow assessment criteria require criterion_id")
        if set(item) - {"criterion_id", "status", "assessor_role_id", "rationale", "evidence_refs"}:
            raise ExecutionResultError("workflow assessment criterion contains unsupported fields")
        criterion_id = item["criterion_id"]
        if criterion_id not in definitions_by_id:
            raise ExecutionResultError(f"workflow assessment contains undeclared criterion: {criterion_id}")
        if criterion_id in supplied_by_id:
            raise ExecutionResultError(f"workflow assessment contains duplicate criterion: {criterion_id}")
        supplied_by_id[criterion_id] = item

    valid_evidence_ids = _assessment_evidence_ids(result)
    role_turns = result.get("role_turns", [])
    normalized_criteria = []
    for criterion_id, definition in definitions_by_id.items():
        item = supplied_by_id.get(criterion_id)
        if item is None:
            normalized_criteria.append({
                "criterion_id": criterion_id,
                "status": "unverified",
                "assessor_role_id": None,
                "rationale": "No assessment was supplied for this criterion.",
                "evidence_refs": [],
            })
            continue

        status = item.get("status")
        rationale = item.get("rationale")
        assessor_role_id = item.get("assessor_role_id")
        evidence_refs = _strings(item.get("evidence_refs", []), f"{criterion_id} evidence_refs")
        if status not in WORKFLOW_ASSESSMENT_STATUSES:
            raise ExecutionResultError(f"unsupported workflow assessment status for {criterion_id}: {status}")
        if not isinstance(rationale, str) or not rationale.strip():
            raise ExecutionResultError(f"workflow assessment {criterion_id} requires a rationale")
        if assessor_role_id is not None:
            if not isinstance(assessor_role_id, str) or not assessor_role_id:
                raise ExecutionResultError(f"workflow assessment {criterion_id} has an invalid assessor_role_id")
            if assessor_role_id not in definition.get("assessor_roles", []):
                raise ExecutionResultError(f"workflow assessment {criterion_id} uses an undeclared assessor role")
        if status in {"met", "not-met", "not-applicable"} and assessor_role_id is None:
            raise ExecutionResultError(f"workflow assessment {criterion_id} requires an assessor role")
        unknown_refs = sorted(set(evidence_refs) - valid_evidence_ids)
        if unknown_refs:
            raise ExecutionResultError(
                f"workflow assessment {criterion_id} cites unknown evidence: {unknown_refs}"
            )
        if status in {"met", "not-met"} and not evidence_refs:
            status = "unverified"
            rationale = f"{rationale} Assessment has no evidence reference, so it remains unverified."
        if status in {"met", "not-met", "not-applicable"} and assessor_role_id is not None and not any(
            turn.get("task_id") == result.get("task_id")
            and turn.get("role_id") == assessor_role_id
            and turn.get("status") == "completed"
            for turn in role_turns
        ):
            status = "unverified"
            rationale = f"{rationale} No completed role turn was recorded for the assessor."
        normalized_criteria.append({
            "criterion_id": criterion_id,
            "status": status,
            "assessor_role_id": assessor_role_id,
            "rationale": rationale.strip(),
            "evidence_refs": evidence_refs,
        })

    run = result.get("run", {})
    report = {
        "artifact_type": "workflow-assessment",
        "version": "1.0.0",
        "status": _workflow_assessment_status(normalized_criteria, result),
        "task_id": plan["task"]["task_id"],
        "plan_id": plan["id"],
        "workflow_id": plan.get("context", {}).get("workflow_id"),
        "criteria": normalized_criteria,
    }
    if isinstance(run, dict):
        for field in ("session_id", "run_id"):
            if isinstance(run.get(field), str) and run[field]:
                report[field] = run[field]
    return report


def _validate_workflow_assessment_record(result: dict[str, Any]) -> None:
    assessment = result.get("workflow_assessment")
    if assessment is None:
        return
    required = ("artifact_type", "version", "status", "task_id", "plan_id", "workflow_id", "criteria")
    if any(field not in assessment for field in required):
        raise ExecutionResultError("workflow_assessment is missing required fields")
    if set(assessment) - {*required, "session_id", "run_id"}:
        raise ExecutionResultError("workflow_assessment contains unsupported fields")
    if assessment["artifact_type"] != "workflow-assessment":
        raise ExecutionResultError("workflow_assessment has an invalid artifact_type")
    if assessment["task_id"] != result.get("task_id") or assessment["plan_id"] != result.get("plan_id"):
        raise ExecutionResultError("workflow_assessment identity does not match the execution result")
    if not isinstance(assessment["version"], str) or not assessment["version"]:
        raise ExecutionResultError("workflow_assessment version must be a non-empty string")
    if not isinstance(assessment["workflow_id"], str) or not assessment["workflow_id"]:
        raise ExecutionResultError("workflow_assessment workflow_id must be a non-empty string")
    for field in ("session_id", "run_id"):
        if field in assessment and (not isinstance(assessment[field], str) or not assessment[field]):
            raise ExecutionResultError(f"workflow_assessment {field} must be a non-empty string")
    run = result.get("run", {})
    if isinstance(run, dict):
        for field in ("session_id", "run_id"):
            if isinstance(run.get(field), str) and run[field] and assessment.get(field) != run[field]:
                raise ExecutionResultError(f"workflow_assessment {field} does not match the execution result")
    if not isinstance(assessment["criteria"], list):
        raise ExecutionResultError("workflow_assessment criteria must be a list")
    seen = set()
    valid_evidence_ids = _assessment_evidence_ids(result)
    for item in assessment["criteria"]:
        if not isinstance(item, dict):
            raise ExecutionResultError("workflow_assessment criteria must contain objects")
        if set(item) != {"criterion_id", "status", "assessor_role_id", "rationale", "evidence_refs"}:
            raise ExecutionResultError("workflow_assessment criterion has an invalid shape")
        for field in ("criterion_id", "rationale"):
            if not isinstance(item.get(field), str) or not item[field]:
                raise ExecutionResultError(f"workflow_assessment criterion requires {field}")
        criterion_id = item["criterion_id"]
        if criterion_id in seen:
            raise ExecutionResultError(f"workflow_assessment contains duplicate criterion: {criterion_id}")
        seen.add(criterion_id)
        if item.get("status") not in WORKFLOW_ASSESSMENT_STATUSES:
            raise ExecutionResultError(f"unsupported workflow assessment status for {criterion_id}")
        assessor_role_id = item.get("assessor_role_id")
        if assessor_role_id is not None and (not isinstance(assessor_role_id, str) or not assessor_role_id):
            raise ExecutionResultError(f"workflow assessment {criterion_id} has an invalid assessor_role_id")
        refs = _strings(item.get("evidence_refs"), f"{criterion_id} evidence_refs")
        if set(refs) - valid_evidence_ids:
            raise ExecutionResultError(f"workflow assessment {criterion_id} cites unknown evidence")
        if item["status"] in {"met", "not-met"} and not refs:
            raise ExecutionResultError(f"workflow assessment {criterion_id} requires evidence for {item['status']}")
    expected_status = _workflow_assessment_status(assessment["criteria"], result)
    if assessment["status"] != expected_status:
        raise ExecutionResultError("workflow_assessment status does not match its criteria and execution result")


def _topology_conformance(
    topology: Any,
    realization: dict[str, Any],
    role_turns: list[dict[str, Any]],
) -> dict[str, Any]:
    """Check lane-level runtime evidence against the portable execution topology."""
    topology_declared = topology is not None
    if topology is not None and not isinstance(topology, dict):
        raise ExecutionResultError("execution_topology must be an object")
    lanes = topology.get("parallel_lanes", []) if isinstance(topology, dict) else []
    declared = {lane["id"]: lane for lane in lanes if isinstance(lane, dict) and isinstance(lane.get("id"), str)}
    lane_evidence = realization.get("parallel_lane_evidence", [])
    reported_ids = realization.get("parallel_lane_ids", [])
    evidence_ids = list(dict.fromkeys(item["lane_id"] for item in lane_evidence))
    issues: list[str] = []
    failed = False
    unverified = False

    if lane_evidence and realization["mode"] != "native-parallel":
        issues.append("parallel lane evidence conflicts with the reported execution mode")
        failed = True
    for item in lane_evidence:
        lane = declared.get(item["lane_id"])
        if not topology_declared:
            issues.append("execution topology was not declared, so lane evidence could not be authorized")
            failed = True
            continue
        if lane is None or item["stage_id"] != lane.get("stage_id") or item["role_id"] not in lane.get("role_ids", []):
            issues.append(f"lane evidence does not match declared topology for {item['lane_id']}")
            failed = True
            continue
        matching_turn = any(
            turn.get("stage_id") == item["stage_id"]
            and turn.get("role_id") == item["role_id"]
            and turn.get("worker_ref") == item["worker_ref"]
            and turn.get("status") in {"started", "completed", "blocked"}
            for turn in role_turns
        )
        if not matching_turn:
            issues.append(f"lane evidence for {item['lane_id']}/{item['role_id']} has no matching worker role turn")
            failed = True
    for lane_id in evidence_ids:
        lane = declared.get(lane_id)
        if lane and any(
            not any(item["lane_id"] == lane_id and item["role_id"] == role_id for item in lane_evidence)
            for role_id in lane.get("role_ids", [])
        ):
            issues.append(f"lane evidence for {lane_id} is missing a declared role")
            failed = True

    if reported_ids and evidence_ids and set(reported_ids) != set(evidence_ids):
        issues.append("parallel_lane_ids do not match lane-level worker evidence")
        failed = True
    observed_ids = evidence_ids or reported_ids
    observed_worker_turns = any(turn.get("status") in {"started", "completed", "blocked"} for turn in role_turns)
    if observed_ids and realization["mode"] != "native-parallel":
        issues.append("parallel lane IDs conflict with the reported execution mode")
        failed = True
    unauthorized = sorted(set(observed_ids) - set(declared)) if topology_declared else []
    if unauthorized:
        issues.append("runtime reported undeclared parallel lanes")
        failed = True
    if realization["mode"] == "native-parallel":
        if topology_declared and not declared:
            issues.append("parallel execution was reported but no parallel lanes are authorized")
            failed = True
        elif not observed_ids or not lane_evidence:
            if not topology_declared:
                issues.append("execution topology was not declared, so parallel execution could not be checked")
            else:
                issues.append("runtime did not provide lane-to-worker evidence for parallel execution")
            unverified = True

    if realization["mode"] == "unreported" and not observed_ids and not observed_worker_turns:
        return {
            "status": "not-applicable",
            "planned_mode": topology.get("mode", "unreported") if isinstance(topology, dict) else "unreported",
            "observed_mode": realization["mode"],
            "observed_parallel_lane_ids": [],
            "issues": ["no runtime dispatch or worker turns were observed"],
        }

    return {
        "status": "failed" if failed else "unverified" if unverified else "pass",
        "planned_mode": topology.get("mode", "unreported") if isinstance(topology, dict) else "unreported",
        "observed_mode": realization["mode"],
        "observed_parallel_lane_ids": observed_ids,
        "issues": issues,
    }


def _parallel_timing_conformance(realization: dict[str, Any]) -> dict[str, Any]:
    """Only claim observed parallel work when distinct lanes have overlapping intervals."""
    if realization["mode"] != "native-parallel":
        return {"status": "not-applicable", "issues": []}
    evidence = realization.get("parallel_lane_evidence", [])
    intervals: dict[str, tuple[datetime, datetime]] = {}
    issues: list[str] = []
    for item in evidence:
        lane_id = item["lane_id"]
        if "started_at" not in item or "completed_at" not in item:
            continue
        try:
            start = datetime.fromisoformat(item["started_at"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(item["completed_at"].replace("Z", "+00:00"))
        except ValueError:
            issues.append(f"parallel timing for {lane_id} contains an invalid timestamp")
            continue
        if start.tzinfo is None or end.tzinfo is None or end <= start:
            issues.append(f"parallel timing for {lane_id} must have ordered timezone-aware timestamps")
            continue
        current = intervals.get(lane_id)
        if current is None:
            intervals[lane_id] = (start, end)
        else:
            intervals[lane_id] = (min(current[0], start), max(current[1], end))
    if issues:
        status = "failed"
    elif len(intervals) < 2:
        status = "unverified"
        issues.append("overlapping start/end telemetry for at least two parallel lanes was not provided")
    elif any(
        max(first[0], second[0]) < min(first[1], second[1])
        for index, first in enumerate(intervals.values())
        for second in list(intervals.values())[index + 1 :]
    ):
        status = "pass"
    else:
        status = "failed"
        issues.append("reported parallel lane intervals do not overlap")
    return {"status": status, "issues": issues}


def _normalize_reasoning_evidence(value: Any) -> list[dict[str, Any]]:
    evidence = _records(value, "reasoning_evidence")
    for item in evidence:
        for field in ("stage_id", "role_id", "requested_level", "status"):
            if not isinstance(item.get(field), str) or not item[field]:
                raise ExecutionResultError(f"reasoning evidence requires {field}")
        if item["status"] not in REASONING_EVIDENCE_STATUSES:
            raise ExecutionResultError(f"unsupported reasoning evidence status: {item['status']}")
        for field in ("requested_runtime_value", "effective_level", "effective_runtime_value", "worker_ref", "evidence_source"):
            if field in item and item[field] is not None and (not isinstance(item[field], str) or not item[field]):
                raise ExecutionResultError(f"reasoning evidence {field} must be a non-empty string or null")
        if "dispatch_status" in item and item["dispatch_status"] not in REASONING_DISPATCH_STATUSES:
            raise ExecutionResultError(f"unsupported reasoning dispatch status: {item['dispatch_status']}")
        if "telemetry_status" in item and item["telemetry_status"] not in REASONING_TELEMETRY_STATUSES:
            raise ExecutionResultError(f"unsupported reasoning telemetry status: {item['telemetry_status']}")
        if item["status"] == "runtime-observed":
            if item.get("telemetry_status") != "observed":
                raise ExecutionResultError("runtime-observed reasoning evidence requires observed telemetry")
            if not item.get("effective_level") and not item.get("effective_runtime_value"):
                raise ExecutionResultError("runtime-observed reasoning evidence requires an effective value")
            if not item.get("evidence_source"):
                raise ExecutionResultError("runtime-observed reasoning evidence requires evidence_source")
        if item.get("telemetry_status") == "observed" and item["status"] != "runtime-observed":
            raise ExecutionResultError("observed reasoning telemetry requires runtime-observed status")
        if item.get("dispatch_status") == "accepted" and not item.get("worker_ref"):
            raise ExecutionResultError("accepted reasoning dispatch requires worker_ref")
    return evidence


def _validate_reasoning_evidence_against_plan(
    evidence: list[dict[str, Any]],
    assignments: Any,
) -> None:
    if not isinstance(assignments, list):
        raise ExecutionResultError("prepared plan reasoning_assignments must be a list")

    canonical: dict[tuple[str, str], dict[str, Any]] = {}
    for assignment in assignments:
        if not isinstance(assignment, dict):
            raise ExecutionResultError("prepared plan reasoning assignments must be objects")
        key = (assignment.get("stage_id"), assignment.get("role_id"))
        canonical[key] = assignment

    seen: set[tuple[str, str]] = set()
    for item in evidence:
        key = (item["stage_id"], item["role_id"])
        if key not in canonical:
            raise ExecutionResultError(
                f"reasoning evidence references unknown assignment: {key[0]}/{key[1]}"
            )
        if key in seen:
            raise ExecutionResultError(
                f"duplicate reasoning evidence assignment: {key[0]}/{key[1]}"
            )
        seen.add(key)

        assignment = canonical[key]
        if item["requested_level"] != assignment.get("level"):
            raise ExecutionResultError(
                f"reasoning evidence requested level does not match assignment: {key[0]}/{key[1]}"
            )
        expected_runtime_value = next(
            (
                assignment[field]
                for field in ("requested_runtime_value", "runtime_value", "codex_reasoning_effort")
                if assignment.get(field) is not None
            ),
            None,
        )
        if (
            expected_runtime_value is not None
            and item.get("requested_runtime_value") is not None
            and item["requested_runtime_value"] != expected_runtime_value
        ):
            raise ExecutionResultError(
                f"reasoning evidence requested runtime value does not match assignment: "
                f"{key[0]}/{key[1]}"
            )


def _complete_reasoning_evidence_from_plan(
    evidence: list[dict[str, Any]],
    assignments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    provided = {(item["stage_id"], item["role_id"]): item for item in evidence}
    completed: list[dict[str, Any]] = []
    for assignment in assignments:
        key = (assignment["stage_id"], assignment["role_id"])
        item = provided.get(key)
        if item is None:
            item = {
                "stage_id": assignment["stage_id"],
                "role_id": assignment["role_id"],
                "requested_level": assignment["level"],
                "effective_level": None,
                "status": "unverified",
                "dispatch_status": "not-attempted",
                "telemetry_status": "unverified",
                "evidence_source": "plan-projection",
            }
        completed.append(item)
    return completed


def _validate_checkpoint(checkpoint: Any, task_id: str, expected_status: str | None = None) -> dict[str, Any]:
    if not isinstance(checkpoint, dict):
        raise ExecutionResultError("checkpoint must be an object")
    required = ("checkpoint_id", "task_id", "status", "resumable")
    if any(not checkpoint.get(field) if field != "resumable" else "resumable" not in checkpoint for field in required):
        raise ExecutionResultError("checkpoint requires checkpoint_id, task_id, status, and resumable")
    if checkpoint["task_id"] != task_id:
        raise ExecutionResultError("checkpoint task_id does not match the prepared task")
    if checkpoint["status"] not in {"created", "accepted", "resumed", "superseded"}:
        raise ExecutionResultError(f"unsupported checkpoint status: {checkpoint['status']}")
    if not isinstance(checkpoint["resumable"], bool):
        raise ExecutionResultError("checkpoint resumable must be a boolean")
    if expected_status and checkpoint["status"] != expected_status:
        raise ExecutionResultError(
            f"checkpoint status {checkpoint['status']} does not satisfy expected status {expected_status}"
        )
    if checkpoint["status"] == "resumed" and not checkpoint["resumable"]:
        raise ExecutionResultError("a non-resumable checkpoint cannot be resumed")
    if "sequence" in checkpoint and checkpoint["sequence"] is not None:
        if not isinstance(checkpoint["sequence"], int) or checkpoint["sequence"] < 0:
            raise ExecutionResultError("checkpoint sequence must be a non-negative integer")
    return dict(checkpoint)


def _validate_idempotency_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    valid_statuses = {"new", "applied", "replayed", "skipped", "conflict"}
    for record in records:
        for field in ("idempotency_key", "operation", "status", "side_effect_applied"):
            if field not in record:
                raise ExecutionResultError(f"idempotency record requires {field}")
        key = record["idempotency_key"]
        if not isinstance(key, str) or not key:
            raise ExecutionResultError("idempotency_key must be a non-empty string")
        if key in seen:
            raise ExecutionResultError(f"duplicate idempotency key: {key}")
        seen.add(key)
        if not isinstance(record["operation"], str) or not record["operation"]:
            raise ExecutionResultError("idempotency operation must be a non-empty string")
        if record["status"] not in valid_statuses:
            raise ExecutionResultError(f"unsupported idempotency status: {record['status']}")
        if not isinstance(record["side_effect_applied"], bool):
            raise ExecutionResultError("idempotency side_effect_applied must be a boolean")
    return records


def _normalize_degraded_capabilities(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ExecutionResultError("degraded_capabilities must be a list")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in value:
        if isinstance(item, str):
            capability = item
            record = {"capability": capability, "mode": "adapted", "fallback": None}
        elif isinstance(item, dict):
            record = dict(item)
            capability = record.get("capability")
        else:
            raise ExecutionResultError("each degraded capability must be a string or object")
        if not isinstance(capability, str) or not capability:
            raise ExecutionResultError("degraded capability requires a non-empty capability")
        if capability in seen:
            raise ExecutionResultError(f"duplicate degraded capability: {capability}")
        seen.add(capability)
        if record.get("mode") not in DEGRADED_CAPABILITY_MODES:
            raise ExecutionResultError(
                f"degraded capability {capability} must use adapted or externalized mode"
            )
        normalized.append(record)
    return normalized


def validate_normalized_execution_result(
    result: dict[str, Any],
    prepared: dict[str, Any] | None = None,
    *,
    allow_unverified_required_evidence: bool = False,
) -> dict[str, Any]:
    """Validate and return a normalized result without mutating it."""
    if not isinstance(result, dict):
        raise ExecutionResultError("normalized execution result must be an object")
    required = ("artifact_type", "version", "task_id", "plan_id", "status")
    if any(not result.get(field) for field in required):
        raise ExecutionResultError("normalized execution result is missing required identity or status")
    required_collections = (
        "active_roles",
        "completed_stages",
        "decisions",
        "handoffs",
        "approvals",
        "artifacts",
        "evidence",
        "failures",
        "retries",
        "idempotency_records",
        "degraded_capabilities",
        "unresolved_conditions",
    )
    required_fields = ("execution_realization", "role_turns", "verification")
    missing_collections = [field for field in required_collections + required_fields if field not in result]
    if missing_collections:
        raise ExecutionResultError(
            "normalized execution result is missing required fields: "
            + ", ".join(missing_collections)
        )
    if result["artifact_type"] != "normalized-execution-result":
        raise ExecutionResultError("invalid normalized execution result artifact_type")
    if result["status"] not in NORMALIZED_RESULT_STATUSES:
        raise ExecutionResultError(f"unsupported normalized result status: {result['status']}")
    _strings(result["active_roles"], "active_roles")
    for field in (
        "completed_stages",
        "unresolved_conditions",
        "degraded_capabilities",
    ):
        if field == "degraded_capabilities":
            _normalize_degraded_capabilities(result[field])
        else:
            _strings(result.get(field, []), field)
    for field in ("handoffs", "approvals", "artifacts", "evidence", "failures", "retries", "decisions"):
        _records(result.get(field, []), field)
    _validate_execution_events(result.get("execution_events", []))
    _normalize_reasoning_evidence(result.get("reasoning_evidence", []))
    if "execution_realization" in result:
        _validate_execution_realization(result["execution_realization"])
    role_turns = _validate_role_turns(result.get("role_turns", []))
    if "execution_topology" in result and "topology_conformance" not in result:
        raise ExecutionResultError("normalized result with execution_topology requires topology_conformance")
    if "topology_conformance" in result:
        expected_conformance = _topology_conformance(
            result.get("execution_topology"),
            result["execution_realization"],
            role_turns,
        )
        if result["topology_conformance"] != expected_conformance:
            raise ExecutionResultError("topology_conformance does not match persisted topology and worker evidence")
        expected_timing = _parallel_timing_conformance(result["execution_realization"])
        if result.get("parallel_timing_conformance") != expected_timing:
            raise ExecutionResultError("parallel_timing_conformance does not match persisted lane timing evidence")
    if "scheduling_conformance" in result or (
        isinstance(result.get("execution_topology"), dict)
        and result["execution_topology"].get("work_items")
    ):
        expected_scheduling = _scheduling_conformance(
            result["execution_topology"],
            _validate_execution_events(result.get("execution_events", [])),
            result["status"],
            result["execution_realization"]["mode"],
        )
        if result.get("scheduling_conformance") != expected_scheduling:
            raise ExecutionResultError("scheduling_conformance does not match persisted work-item events")
    _records(result.get("verification", []), "verification")
    if result.get("checkpoint") is not None:
        _validate_checkpoint(result["checkpoint"], result["task_id"])
    _validate_idempotency_records(_records(result.get("idempotency_records", []), "idempotency_records"))
    resume = result.get("resume")
    if resume is not None:
        if not isinstance(resume, dict):
            raise ExecutionResultError("resume must be an object")
        if "same_task_id" in resume and resume["same_task_id"] is not True:
            raise ExecutionResultError("resume same_task_id must be true")
        if "prior_run_preserved" in resume and not isinstance(resume["prior_run_preserved"], bool):
            raise ExecutionResultError("resume prior_run_preserved must be a boolean")
    if result["status"] == "interrupted":
        checkpoint = result.get("checkpoint")
        if checkpoint is None or checkpoint.get("status") != "accepted" or not checkpoint.get("resumable"):
            raise ExecutionResultError("interrupted results require an accepted resumable checkpoint")
    if result["status"] == "degraded" and not result.get("degraded_capabilities"):
        raise ExecutionResultError("degraded results require degraded_capabilities")
    if "workflow_assessment" in result and not isinstance(result["workflow_assessment"], dict):
        raise ExecutionResultError("workflow_assessment must be an object")
    _validate_workflow_assessment_record(result)
    if prepared is not None:
        plan, _ = _parts(prepared)
        if result["task_id"] != plan["task"]["task_id"] or result["plan_id"] != plan["id"]:
            raise ExecutionResultError("normalized result identity does not match the prepared execution")
        _validate_result_against_plan(
            result, plan, allow_unverified_required_evidence=allow_unverified_required_evidence
        )
        expected_assessment = _build_workflow_assessment(
            plan,
            result,
            {"criteria": result["workflow_assessment"].get("criteria", [])}
            if isinstance(result.get("workflow_assessment"), dict)
            else None,
        )
        if expected_assessment != result.get("workflow_assessment"):
            raise ExecutionResultError("workflow_assessment does not match the plan and session evidence")
    return dict(result)


def _validate_execution_events(value: Any) -> list[dict[str, Any]]:
    """Validate the optional, provenance-preserving execution timeline."""
    events = _records(value, "execution_events")
    for event in events:
        for field in ("kind", "status"):
            if not isinstance(event.get(field), str) or not event[field]:
                raise ExecutionResultError(f"execution event requires {field}")
        for field in ("event_id", "task_id", "session_id", "run_id", "role_id", "stage_id", "timestamp"):
            if field in event and event[field] is not None and not isinstance(event[field], str):
                raise ExecutionResultError(f"execution event {field} must be a string")
        if "evidence_refs" in event:
            _strings(event["evidence_refs"], "execution event evidence_refs")
        if "metadata" in event and not isinstance(event["metadata"], dict):
            raise ExecutionResultError("execution event metadata must be an object")
        if event["kind"] == "work-item":
            for field in ("work_item_id", "role_id", "stage_id"):
                if not isinstance(event.get(field), str) or not event[field]:
                    raise ExecutionResultError(f"work-item execution event requires {field}")
            evidence_source = event.get("evidence_source")
            if not isinstance(evidence_source, str) or evidence_source not in WORK_ITEM_EVIDENCE_SOURCES:
                raise ExecutionResultError("work-item execution event requires a supported evidence_source")
            if evidence_source == "runtime-receipt" and not event.get("evidence_refs"):
                raise ExecutionResultError("runtime-receipt work-item events require evidence_refs")
            if event["status"] not in {
                "queued", "started", "waiting", "resumed", "completed",
                "not-applicable", "failed", "cancelled",
            }:
                raise ExecutionResultError(f"unsupported work-item event status: {event['status']}")
            dependencies = _strings(event.get("dependency_ids", []), "work-item dependency_ids")
            if len(dependencies) != len(set(dependencies)):
                raise ExecutionResultError("work-item dependency_ids must be unique")
            if "worker_ref" in event and (not isinstance(event["worker_ref"], str) or not event["worker_ref"]):
                raise ExecutionResultError("work-item worker_ref must be a non-empty string")
            if event.get("timestamp") is not None:
                try:
                    timestamp = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
                except ValueError as error:
                    raise ExecutionResultError("work-item timestamp must be an ISO timestamp") from error
                if timestamp.tzinfo is None:
                    raise ExecutionResultError("work-item timestamp must include a timezone")
    return events


def _scheduling_conformance(
    topology: Any,
    events: list[dict[str, Any]],
    result_status: str,
    execution_mode: str,
) -> dict[str, Any]:
    """Check work-item lifecycle, dependency ordering, and observable wait intervals."""
    work_items = topology.get("work_items", []) if isinstance(topology, dict) else []
    if not work_items:
        return {
            "status": "not-applicable",
            "planned_work_item_ids": [],
            "observed_work_item_ids": [],
            "wait_durations_seconds": {},
            "work_during_wait": [],
            "issues": [],
        }

    planned = {item["id"]: item for item in work_items}
    item_events: dict[str, list[dict[str, Any]]] = {}
    issues: list[str] = []
    failed = False
    for event in events:
        if event.get("kind") != "work-item":
            continue
        work_item_id = event["work_item_id"]
        item = planned.get(work_item_id)
        if item is None:
            issues.append(f"event references undeclared work item {work_item_id}")
            failed = True
            continue
        if event["role_id"] != item["role_id"] or event["stage_id"] != item["stage_id"]:
            issues.append(f"event identity does not match work item {work_item_id}")
            failed = True
            continue
        if set(event.get("dependency_ids", [])) != set(item.get("depends_on", [])):
            issues.append(f"event dependencies do not match work item {work_item_id}")
            failed = True
            continue
        item_events.setdefault(work_item_id, []).append(event)

    unverified_evidence = any(
        event.get("evidence_source") not in OBSERVED_WORK_ITEM_EVIDENCE_SOURCES
        for records in item_events.values()
        for event in records
    )
    if unverified_evidence:
        issues.append("scheduling timing is unverified because one or more work-item events lack adapter-observed or runtime-receipt evidence")

    if any(event.get("timestamp") is None for records in item_events.values() for event in records):
        issues.append("scheduling timing is unverified because one or more work-item events lack timestamps")
        return {
            "status": "failed" if failed else "unverified",
            "planned_work_item_ids": list(planned),
            "observed_work_item_ids": sorted(item_events),
            "wait_durations_seconds": {},
            "work_during_wait": [],
            "issues": issues,
        }

    parsed: dict[str, list[tuple[datetime, dict[str, Any]]]] = {}
    durations: dict[str, float] = {}
    active_segments: dict[str, list[tuple[datetime, datetime | None]]] = {}
    terminal_status = {"completed", "not-applicable", "failed", "cancelled"}
    for work_item_id, records in item_events.items():
        try:
            ordered = sorted(
                ((datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00")), event) for event in records),
                key=lambda pair: pair[0],
            )
        except ValueError:
            continue  # Timestamp syntax is reported by _validate_execution_events.
        parsed[work_item_id] = ordered
        states: list[str] = []
        wait_started: datetime | None = None
        starts: list[datetime] = []
        active_started: datetime | None = None
        active_segments[work_item_id] = []
        for timestamp, event in ordered:
            state = event["status"]
            previous = states[-1] if states else None
            allowed = {
                None: {"queued", "started", "waiting", "not-applicable"},
                "queued": {"started", "waiting", "not-applicable", "cancelled"},
                "started": {"waiting", "completed", "failed", "cancelled"},
                "waiting": {"resumed", "failed", "cancelled"},
                "resumed": {"waiting", "completed", "failed", "cancelled"},
            }
            if state not in allowed.get(previous, set()):
                issues.append(f"invalid lifecycle transition for {work_item_id}: {previous} -> {state}")
                failed = True
            if previous in terminal_status:
                issues.append(f"work item {work_item_id} has events after terminal status {previous}")
                failed = True
            states.append(state)
            if state == "started":
                starts.append(timestamp)
                active_started = timestamp
            elif state == "resumed":
                starts.append(timestamp)
                active_started = timestamp
                if wait_started is not None:
                    durations[work_item_id] = durations.get(work_item_id, 0.0) + (timestamp - wait_started).total_seconds()
                    wait_started = None
            elif state == "waiting":
                if active_started is not None:
                    active_segments[work_item_id].append((active_started, timestamp))
                    active_started = None
                wait_started = timestamp
            elif state in terminal_status:
                if active_started is not None:
                    active_segments[work_item_id].append((active_started, timestamp))
                    active_started = None
        if active_started is not None:
            active_segments[work_item_id].append((active_started, None))
        if states and states[-1] in {"failed", "cancelled"}:
            issues.append(f"work item {work_item_id} ended as {states[-1]}")
            failed = True
        if states and states[-1] not in terminal_status:
            issues.append(f"work item {work_item_id} has no terminal lifecycle event")
            if result_status == "completed":
                failed = True

    for work_item_id, item in planned.items():
        records = parsed.get(work_item_id, [])
        start_events = [(timestamp, event) for timestamp, event in records if event["status"] in {"started", "resumed"}]
        if not records:
            if result_status == "completed":
                if execution_mode == "simulated-sequential":
                    issues.append(f"work-item lifecycle is unverified for simulated execution: {work_item_id}")
                else:
                    issues.append(f"completed result has no lifecycle events for {work_item_id}")
                    failed = True
            continue
        for dependency_id in item.get("depends_on", []):
            dependency_records = parsed.get(dependency_id, [])
            terminal = [
                (timestamp, event) for timestamp, event in dependency_records
                if event["status"] in {"completed", "not-applicable"}
            ]
            if not terminal and start_events:
                issues.append(f"work item {work_item_id} started before dependency {dependency_id} completed")
                failed = True
            elif terminal and start_events and min(timestamp for timestamp, _ in start_events) < terminal[-1][0]:
                issues.append(f"work item {work_item_id} started before dependency {dependency_id} completed")
                failed = True

    work_during_wait = []
    for waiting_id, records in parsed.items():
        waits: list[tuple[datetime, datetime]] = []
        waiting_at: datetime | None = None
        for timestamp, event in records:
            if event["status"] == "waiting":
                waiting_at = timestamp
            elif event["status"] == "resumed" and waiting_at is not None:
                waits.append((waiting_at, timestamp))
                waiting_at = None
        for wait_start, wait_end in waits:
            active_ids = sorted(
                item_id for item_id, segments in active_segments.items()
                if item_id != waiting_id and any(
                    start < wait_end and (end is None or end > wait_start)
                    for start, end in segments
                )
            )
            work_during_wait.append({"work_item_id": waiting_id, "other_work_item_ids": active_ids})

    observed = sorted(item_events)
    complete_observation = all(
        item_id in parsed
        and parsed[item_id]
        and parsed[item_id][-1][1]["status"] in terminal_status
        for item_id in planned
    )
    unverified = not complete_observation or not events
    if result_status == "completed" and complete_observation and not failed and not unverified_evidence:
        status = "pass"
    elif failed:
        status = "failed"
    else:
        status = "unverified"
    if any(event["status"] == "waiting" for records in item_events.values() for event in records) and not durations:
        issues.append("wait duration is unverified because a matching resumed event was not observed")
        unverified = True
        if status == "pass":
            status = "unverified"
    return {
        "status": status if not unverified or status == "failed" else "unverified",
        "planned_work_item_ids": list(planned),
        "observed_work_item_ids": observed,
        "wait_durations_seconds": durations,
        "work_during_wait": work_during_wait,
        "issues": issues,
    }


def retain_run_observability(run: dict[str, Any], result: dict[str, Any]) -> None:
    """Retain optional associations without granting them evidence provenance."""
    metadata = result.get("metadata", {})
    association = metadata.get("observability") if isinstance(metadata, dict) else None
    if association is None:
        runtime_run = result.get("run", {})
        run_metadata = runtime_run.get("metadata", {}) if isinstance(runtime_run, dict) else {}
        association = run_metadata.get("observability") if isinstance(run_metadata, dict) else None
    if not isinstance(association, dict):
        return
    association = deepcopy(association)
    correlation = association.get("correlation", {})
    if isinstance(correlation, dict):
        association["correlation"] = {
            **correlation,
            **{field: run[field] for field in (
                "task_id", "session_id", "run_id", "plan_id", "execution_profile_id",
                "runtime_profile_id", "runtime_adapter_id",
            ) if isinstance(run.get(field), str) and run[field]},
        }
    result.setdefault("metadata", {})["observability"] = association
    run.setdefault("metadata", {})["observability"] = deepcopy(association)


def normalize_execution_result(
    prepared: dict[str, Any],
    runtime_result: dict[str, Any],
    *,
    scenario_id: str | None = None,
    allow_unverified_required_evidence: bool = False,
) -> dict[str, Any]:
    """Normalize a runtime-neutral result payload against a prepared plan."""
    plan, _ = _parts(prepared)
    if not isinstance(runtime_result, dict):
        raise ExecutionResultError("runtime result must be an object")
    reasoning_evidence = runtime_result.get("reasoning_evidence")
    if reasoning_evidence is None or reasoning_evidence == []:
        role_turns = _records(runtime_result.get("role_turns", []), "role_turns")
        reasoning_evidence = []
        for item in plan.get("reasoning_assignments", []):
            matching_turn = next(
                (
                    turn
                    for turn in role_turns
                    if turn.get("stage_id") == item["stage_id"]
                    and turn.get("role_id") == item["role_id"]
                    and turn.get("worker_ref")
                ),
                None,
            )
            accepted = matching_turn is not None
            reasoning_evidence.append(
                {
                    "stage_id": item["stage_id"],
                    "role_id": item["role_id"],
                    "requested_level": item["level"],
                    "effective_level": None,
                    "status": "unverified",
                    "dispatch_status": "accepted" if accepted else "not-attempted",
                    "telemetry_status": "unverified",
                    "evidence_source": "native-dispatch" if accepted else "plan-projection",
                    **({"worker_ref": matching_turn["worker_ref"]} if accepted else {}),
                }
            )
    else:
        reasoning_evidence = _normalize_reasoning_evidence(reasoning_evidence)
        if "reasoning_assignments" in plan:
            _validate_reasoning_evidence_against_plan(reasoning_evidence, plan["reasoning_assignments"])
            reasoning_evidence = _complete_reasoning_evidence_from_plan(
                reasoning_evidence,
                plan["reasoning_assignments"],
            )
    result = {
        "artifact_type": "normalized-execution-result",
        "version": "1.0.0",
        "scenario_id": scenario_id,
        "task_id": plan["task"]["task_id"],
        "plan_id": plan["id"],
        "status": runtime_result.get("status"),
        "execution_realization": runtime_result.get(
            "execution_realization",
            {"mode": "unreported", "native_subagents": False},
        ),
        "execution_topology": plan.get("execution_topology"),
        "active_roles": runtime_result.get("active_roles", []),
        "completed_stages": runtime_result.get("completed_stages", []),
        "decisions": runtime_result.get("decisions", []),
        "role_turns": runtime_result.get("role_turns", []),
        "handoffs": runtime_result.get("handoffs", []),
        "approvals": runtime_result.get("approvals", []),
        "artifacts": runtime_result.get("artifacts", []),
        "evidence": runtime_result.get("evidence", []),
        "verification": runtime_result.get("verification", []),
        "failures": runtime_result.get("failures", []),
        "retries": runtime_result.get("retries", []),
        "checkpoint": runtime_result.get("checkpoint"),
        "idempotency_records": runtime_result.get("idempotency_records", []),
        "degraded_capabilities": _normalize_degraded_capabilities(runtime_result.get("degraded_capabilities", [])),
        "resume": runtime_result.get("resume"),
        "unresolved_conditions": runtime_result.get("unresolved_conditions", []),
        "reasoning_evidence": reasoning_evidence,
        "execution_events": _validate_execution_events(runtime_result.get("execution_events", [])),
    }
    topology = plan.get("execution_topology")
    realization = dict(_validate_execution_realization(result["execution_realization"]))
    lane_evidence = realization.get("parallel_lane_evidence", [])
    if lane_evidence and not realization.get("parallel_lane_ids"):
        realization["parallel_lane_ids"] = list(dict.fromkeys(item["lane_id"] for item in lane_evidence))
    result["execution_realization"] = realization
    result["execution_topology"] = topology
    result["topology_conformance"] = _topology_conformance(topology, realization, result["role_turns"])
    result["parallel_timing_conformance"] = _parallel_timing_conformance(realization)
    result["scheduling_conformance"] = _scheduling_conformance(
        topology, result["execution_events"], result["status"], realization["mode"]
    )
    if plan["task"].get("execution_diagnostics") is True:
        team_context = plan["context"].get("team_context", {})
        preferred_roles = set(team_context.get("preferred_roles", []))
        assignments = {item["role_id"]: item for item in plan["role_assignments"]}
        turns_by_role = {}
        for turn in result["role_turns"]:
            turns_by_role.setdefault(turn.get("role_id"), []).append(turn.get("status"))
        result["execution_diagnostics"] = {
            "planned_parallel_lanes": [lane["id"] for lane in (topology or {}).get("parallel_lanes", [])],
            "serial_fallback_lane_ids": ((topology or {}).get("serial_fallback") or {}).get("lane_ids", []),
            "topology_conformance": result["topology_conformance"],
            "parallel_timing_conformance": result["parallel_timing_conformance"],
            "scheduling_conformance": result["scheduling_conformance"],
            "parallel_lane_evidence": lane_evidence,
            "role_selection": {
                "preference_semantics": "guidance-only",
                "preferred_role_ids": sorted(preferred_roles),
                "assignments": [
                    {
                        "role_id": role_id,
                        "participation": assignment["participation"],
                        "team_preferred": role_id in preferred_roles,
                        "stage_ids": [step["step_id"] for step in plan["steps"] if role_id in step["role_ids"]],
                        "observed_turn_statuses": turns_by_role.get(role_id, []),
                    }
                    for role_id, assignment in assignments.items()
                ],
            },
            "role_dispatch": [
                {
                    key: turn[key]
                    for key in ("stage_id", "role_id", "status", "worker_ref")
                    if turn.get(key) is not None
                }
                for turn in result["role_turns"]
            ],
        }
    if "run" in runtime_result:
        result["run"] = dict(runtime_result["run"])
    if "metadata" in runtime_result:
        result["metadata"] = dict(runtime_result["metadata"])
    workflow_assessment = _build_workflow_assessment(
        plan, result, runtime_result.get("workflow_assessment")
    )
    if workflow_assessment is not None:
        result["workflow_assessment"] = workflow_assessment
    return validate_normalized_execution_result(
        result, prepared, allow_unverified_required_evidence=allow_unverified_required_evidence
    )


def build_interrupted_result(
    prepared: dict[str, Any],
    checkpoint: dict[str, Any],
    *,
    active_roles: Iterable[str] = (),
    reason: str | None = None,
    scenario_id: str | None = None,
) -> dict[str, Any]:
    """Build an interrupted result that can be resumed from an accepted checkpoint."""
    plan, _ = _parts(prepared)
    accepted = _validate_checkpoint(checkpoint, plan["task"]["task_id"], "accepted")
    return normalize_execution_result(
        prepared,
        {
            "status": "interrupted",
            "active_roles": list(active_roles),
            "checkpoint": accepted,
            "resume": {"required": True, "same_task_id": True, "prior_run_preserved": True},
            "unresolved_conditions": [reason] if reason else [],
        },
        scenario_id=scenario_id,
    )


def build_checkpoint_resume_result(
    prepared: dict[str, Any],
    checkpoint: dict[str, Any],
    *,
    active_roles: Iterable[str] = (),
    replay_from_stage: str | None = None,
    run_count: int = 2,
    scenario_id: str | None = None,
) -> dict[str, Any]:
    """Build a completed result resumed from a prior accepted checkpoint."""
    plan, _ = _parts(prepared)
    resumed = _validate_checkpoint(checkpoint, plan["task"]["task_id"], "resumed")
    if run_count < 2:
        raise ExecutionResultError("checkpoint resume requires at least two runs")
    resume = {
        "required": False,
        "run_count": run_count,
        "same_task_id": True,
        "prior_run_preserved": True,
        "checkpoint_status": resumed["status"],
    }
    if replay_from_stage:
        resume["replay_from_stage"] = replay_from_stage
    return normalize_execution_result(
        prepared,
        {
            "status": "completed",
            "active_roles": list(active_roles),
            "checkpoint": resumed,
            "resume": resume,
        },
        scenario_id=scenario_id,
    )


def build_idempotent_replay_result(
    prepared: dict[str, Any],
    idempotency_record: dict[str, Any],
    *,
    active_roles: Iterable[str] = (),
    side_effect_count: int = 1,
    scenario_id: str | None = None,
) -> dict[str, Any]:
    """Build a result proving a replay did not duplicate an external side effect."""
    records = _validate_idempotency_records([dict(idempotency_record)])
    if records[0]["status"] != "replayed":
        raise ExecutionResultError("idempotent replay requires a replayed idempotency record")
    if records[0]["side_effect_applied"]:
        raise ExecutionResultError("a replayed operation cannot apply the side effect again")
    if not isinstance(side_effect_count, int) or side_effect_count != 1:
        raise ExecutionResultError("idempotent replay must report exactly one applied side effect")
    return normalize_execution_result(
        prepared,
        {
            "status": "completed",
            "active_roles": list(active_roles),
            "idempotency_records": records,
            "metadata": {
                "idempotency_status": "replayed",
                "side_effect_count": side_effect_count,
                "idempotency_key_required": True,
            },
        },
        scenario_id=scenario_id,
    )


def build_degraded_result(
    prepared: dict[str, Any],
    degraded_capabilities: Iterable[str | dict[str, Any]],
    *,
    active_roles: Iterable[str] = (),
    serial_fallback_recorded: bool = False,
    scenario_id: str | None = None,
) -> dict[str, Any]:
    """Build a result that records adapted or externalized capability behavior."""
    capabilities = _normalize_degraded_capabilities(list(degraded_capabilities))
    if not capabilities:
        raise ExecutionResultError("degraded result requires at least one capability")
    return normalize_execution_result(
        prepared,
        {
            "status": "degraded",
            "active_roles": list(active_roles),
            "degraded_capabilities": capabilities,
            "metadata": {"serial_fallback_recorded": serial_fallback_recorded},
        },
        scenario_id=scenario_id,
    )


__all__ = [
    "DEGRADED_CAPABILITY_MODES",
    "ExecutionResultError",
    "validate_execution_realization",
    "NORMALIZED_RESULT_STATUSES",
    "build_checkpoint_resume_result",
    "build_degraded_result",
    "build_idempotent_replay_result",
    "build_interrupted_result",
    "normalize_execution_result",
    "validate_normalized_execution_result",
]
