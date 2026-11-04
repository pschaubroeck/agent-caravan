"""Prepare portable executions and their runtime evidence records."""

from __future__ import annotations

from typing import Any, Iterable

from .execution_plan import ExecutionPlanError, build_portable_execution_plan


class OrchestrationError(ValueError):
    """Raised when an execution cannot cross the portable-plan boundary."""


def prepare_execution(resolved: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    """Build and validate the runtime-neutral execution plan for a task."""
    try:
        plan = build_portable_execution_plan(resolved, task)
    except ExecutionPlanError as error:
        raise OrchestrationError(str(error)) from error
    return {
        "status": "ready",
        "plan": plan,
        "context": dict(plan["context"]),
    }


def _parts(prepared: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if not isinstance(prepared, dict) or prepared.get("status") != "ready":
        raise OrchestrationError("execution preparation must have ready status")
    plan = prepared.get("plan")
    context = prepared.get("context")
    if not isinstance(plan, dict) or not isinstance(context, dict):
        raise OrchestrationError("execution preparation is incomplete")
    runtime = prepared.get("runtime", {})
    if not isinstance(runtime, dict):
        raise OrchestrationError("execution runtime metadata must be an object")
    return plan, context, runtime


def build_execution_records(
    prepared: dict[str, Any],
    session_id: str,
    run_id: str,
    started_at: str,
    attempt: int = 1,
) -> dict[str, dict[str, Any]]:
    """Build initial task, session, and run records without writing them."""
    plan, context, runtime = _parts(prepared)
    if not session_id or not run_id or not started_at or attempt < 1:
        raise OrchestrationError("execution records require IDs, a start timestamp, and a positive attempt")
    task = plan["task"]
    active_roles = [assignment["role_id"] for assignment in plan["role_assignments"]]
    return {
        "task": {
            "task_id": task["task_id"],
            "objective": task["objective"],
            "selected_context": context,
            "plan": [{"plan_id": plan["id"], "status": "validated"}],
            "reasoning_policy": plan.get("reasoning_policy", {}),
            "reasoning_assignments": list(plan.get("reasoning_assignments", [])),
            "tool_requirements": list(plan.get("tool_requirements", [])),
            "evidence_requirements": list(plan.get("evidence_requirements", [])),
            "decisions": [],
            "evidence": [],
            "approvals": [],
            "checkpoints": [],
            "idempotency_records": [],
            "blockers": [],
            "artifacts": [],
            "status": "active",
        },
        "session": {
            "session_id": session_id,
            "task_id": task["task_id"],
            "selected_context": context,
            "runtime": runtime,
            "execution_realization": runtime.get(
                "execution_realization", {"mode": "unreported", "native_subagents": False}
            ),
            "active_roles": active_roles,
            "plan_id": plan["id"],
            "execution_topology": plan.get("execution_topology"),
            "reasoning_policy": plan.get("reasoning_policy", {}),
            "reasoning_assignments": list(plan.get("reasoning_assignments", [])),
            "evidence": [],
            "role_turns": [],
            "handoffs": [],
            "checkpoints": [],
            "status": "active",
            "started_at": started_at,
            "ended_at": None,
        },
        "run": {
            "run_id": run_id,
            "session_id": session_id,
            "task_id": task["task_id"],
            "execution_profile_id": context["workflow_id"],
            "runtime_adapter_id": runtime.get("adapter_id"),
            "runtime_profile_id": runtime.get("runtime_profile_id"),
            "plan_id": plan["id"],
            "reasoning_policy": plan.get("reasoning_policy", {}),
            "reasoning_assignments": list(plan.get("reasoning_assignments", [])),
            "status": "active",
            "started_at": started_at,
            "ended_at": None,
            "attempt": attempt,
            "events": [],
            "evidence": [],
            "checkpoints": [],
            "idempotency_records": [],
            "metrics": {},
            "execution_realization": runtime.get(
                "execution_realization", {"mode": "unreported", "native_subagents": False}
            ),
            "role_turns": [],
            "handoffs": [],
            "verification": [],
        },
    }


def build_completion_record(
    prepared: dict[str, Any],
    status: str,
    ended_at: str,
    *,
    decisions: Iterable[dict[str, Any]] = (),
    evidence: Iterable[dict[str, Any]] = (),
    approvals: Iterable[dict[str, Any]] = (),
    artifacts: Iterable[dict[str, Any]] = (),
    unresolved_conditions: Iterable[str] = (),
    execution_realization: dict[str, Any] | None = None,
    role_turns: Iterable[dict[str, Any]] = (),
    handoffs: Iterable[dict[str, Any]] = (),
    verification: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Build normalized completion evidence tied to the prepared plan."""
    plan, context, runtime = _parts(prepared)
    if not status or not ended_at:
        raise OrchestrationError("completion records require status and an end timestamp")
    return {
        "artifact_type": "execution-completion-record",
        "version": "1.0.0",
        "task_id": plan["task"]["task_id"],
        "plan_id": plan["id"],
        "selected_context": context,
        "runtime": runtime,
        "execution_realization": execution_realization or runtime.get(
            "execution_realization", {"mode": "unreported", "native_subagents": False}
        ),
        "execution_topology": plan.get("execution_topology"),
        "reasoning_policy": plan.get("reasoning_policy", {}),
        "reasoning_assignments": list(plan.get("reasoning_assignments", [])),
        "evidence_requirements": list(plan.get("evidence_requirements", [])),
        "status": status,
        "ended_at": ended_at,
        "decisions": list(decisions),
        "role_turns": list(role_turns),
        "handoffs": list(handoffs),
        "evidence": list(evidence),
        "verification": list(verification),
        "approvals": list(approvals),
        "artifacts": list(artifacts),
        "unresolved_conditions": list(unresolved_conditions),
    }
