"""Runtime-neutral task handoff contracts."""

from __future__ import annotations

import copy
from typing import Any


class TaskHandoffError(ValueError):
    """Raised when a task handoff is incomplete or crosses a role boundary."""


_STATUSES = {"draft", "ready", "accepted", "blocked", "completed", "rejected"}
_FORBIDDEN_KEYS = {
    "codex",
    "mcp",
    "prompt",
    "skill",
    "worker_ref",
    "worker_id",
    "thread_id",
    "storage_path",
    "session_path",
}


def validate_task_handoff(
    handoff: dict[str, Any],
    *,
    plan: dict[str, Any] | None = None,
    task_id: str | None = None,
) -> dict[str, Any]:
    """Validate one complete, task-scoped handoff without invoking a runtime."""
    if not isinstance(handoff, dict):
        raise TaskHandoffError("task handoff must be an object")
    required = (
        "artifact_type", "version", "handoff_id", "task_id", "plan_id",
        "selected_context", "role_assignments", "execution_topology",
        "capability_requirements", "sender_role", "receiver_role", "objective",
        "requested_action", "inputs", "expected_outputs", "next_action",
        "validation", "evidence", "approvals", "unresolved_questions", "blockers", "status",
    )
    missing = [field for field in required if field not in handoff]
    if missing:
        raise TaskHandoffError(f"task handoff is missing fields: {', '.join(missing)}")
    if handoff["artifact_type"] != "task-handoff":
        raise TaskHandoffError("invalid task handoff artifact type")
    if task_id is not None and handoff["task_id"] != task_id:
        raise TaskHandoffError("task handoff task_id does not match the enclosing task")
    for field in ("handoff_id", "task_id", "plan_id", "sender_role", "receiver_role", "objective", "requested_action", "next_action"):
        if not isinstance(handoff[field], str) or not handoff[field]:
            raise TaskHandoffError(f"task handoff {field} must be a non-empty string")
    if handoff["status"] not in _STATUSES:
        raise TaskHandoffError("task handoff has an invalid status")
    for field in ("selected_context", "execution_topology", "capability_requirements", "validation"):
        if not isinstance(handoff[field], dict):
            raise TaskHandoffError(f"task handoff {field} must be an object")
    for field in ("role_assignments", "inputs", "expected_outputs", "evidence", "approvals", "unresolved_questions", "blockers"):
        if not isinstance(handoff[field], list):
            raise TaskHandoffError(f"task handoff {field} must be an array")
    if handoff["validation"].get("status") not in {"pending", "passed", "failed", "unverified"}:
        raise TaskHandoffError("task handoff validation has an invalid status")
    assignments = {item.get("role_id") for item in handoff["role_assignments"] if isinstance(item, dict)}
    if not assignments or None in assignments:
        raise TaskHandoffError("task handoff role_assignments require role_id values")
    if handoff["sender_role"] not in assignments or handoff["receiver_role"] not in assignments:
        raise TaskHandoffError("task handoff sender and receiver must be assigned roles")
    if plan is not None:
        if handoff["plan_id"] != plan.get("id"):
            raise TaskHandoffError("task handoff plan_id does not match the portable plan")
        communication = plan.get("communication")
        if not isinstance(communication, dict):
            raise TaskHandoffError("portable plan is missing handoff communication rules")
        allowed = communication.get("allowed_role_handoffs", [])
        if not isinstance(allowed, list):
            raise TaskHandoffError("portable plan allowed_role_handoffs must be an array")
        if not any(
            edge.get("from") == handoff["sender_role"] and edge.get("to") == handoff["receiver_role"]
            for edge in allowed if isinstance(edge, dict)
        ):
            raise TaskHandoffError("task handoff sender and receiver are not an allowed role handoff")
    leaked = _FORBIDDEN_KEYS.intersection(handoff)
    if leaked:
        raise TaskHandoffError(f"task handoff contains runtime-specific fields: {sorted(leaked)}")
    return handoff


def build_task_handoff(
    plan: dict[str, Any],
    *,
    runtime_context: dict[str, Any],
    sender_role: str,
    receiver_role: str,
    requested_action: str,
    handoff_id: str | None = None,
) -> dict[str, Any]:
    """Build a complete handoff from an already validated portable plan."""
    if not isinstance(runtime_context, dict):
        raise TaskHandoffError("runtime_context must be an object")
    task = plan.get("task", {})
    task_id = task.get("task_id")
    if not task_id:
        raise TaskHandoffError("portable plan task_id is required")
    handoff = {
        "artifact_type": "task-handoff",
        "version": "1.0.0",
        "handoff_id": handoff_id or f"{task_id}-handoff-1",
        "task_id": task_id,
        "plan_id": plan.get("id"),
        "selected_context": {
            **copy.deepcopy(plan.get("context", {})),
            "runtime": copy.deepcopy(runtime_context),
        },
        "role_assignments": copy.deepcopy(plan.get("role_assignments", [])),
        "execution_topology": copy.deepcopy(plan.get("execution_topology") or {"mode": "sequential"}),
        "capability_requirements": copy.deepcopy(plan.get("capability_requirements", {})),
        "sender_role": sender_role,
        "receiver_role": receiver_role,
        "objective": task.get("objective"),
        "requested_action": requested_action,
        "inputs": [{"kind": "portable-execution-plan", "plan_id": plan.get("id"), "task_id": task_id}],
        "expected_outputs": copy.deepcopy(plan.get("required_outputs", [])),
        "next_action": "The selected harness should validate this handoff, accept it, execute the bounded requested action, and return updated evidence.",
        "validation": {"status": "pending", "checks": ["task identity", "plan identity", "role boundary", "approval policy"]},
        "evidence": [],
        "approvals": [],
        "unresolved_questions": [],
        "blockers": [],
        "status": "ready",
    }
    return validate_task_handoff(handoff, plan=plan)


__all__ = ["TaskHandoffError", "build_task_handoff", "validate_task_handoff"]
