"""Validate persisted Agent Caravan execution evidence."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from .execution_result import (
    ExecutionResultError,
    validate_execution_realization,
    validate_normalized_execution_result,
)


class SessionValidationError(ValueError):
    """Raised when persisted execution evidence cannot be trusted."""


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$")
TASK_STATUSES = {"active", "blocked", "completed", "cancelled"}
SESSION_STATUSES = {"active", "paused", "completed", "failed", "cancelled"}
RUN_STATUSES = {"active", "interrupted", "completed", "failed", "cancelled", "degraded"}


def _required_string(record: dict[str, Any], field: str, issues: list[str], label: str) -> None:
    if not isinstance(record.get(field), str) or not record[field]:
        issues.append(f"{label}.{field} must be a non-empty string")


def _required_object(record: dict[str, Any], field: str, issues: list[str], label: str) -> None:
    if not isinstance(record.get(field), dict):
        issues.append(f"{label}.{field} must be an object")


def _required_list(record: dict[str, Any], field: str, issues: list[str], label: str) -> None:
    if not isinstance(record.get(field), list):
        issues.append(f"{label}.{field} must be an array")


def _validate_task(task: Any, task_id: str, issues: list[str]) -> str | None:
    if not isinstance(task, dict):
        issues.append("task record must be an object")
        return None
    for field in ("task_id", "objective"):
        _required_string(task, field, issues, "task")
    for field in ("selected_context",):
        _required_object(task, field, issues, "task")
    for field in ("plan", "decisions", "evidence", "approvals", "blockers", "artifacts"):
        _required_list(task, field, issues, "task")
    if task.get("status") not in TASK_STATUSES:
        issues.append(f"task.status is not one of {sorted(TASK_STATUSES)}")
    if task.get("task_id") != task_id:
        issues.append("task.task_id does not match the requested task_id")
    plan_id: str | None = None
    plans = task.get("plan")
    if isinstance(plans, list) and plans:
        first_plan = plans[0]
        if isinstance(first_plan, dict) and isinstance(first_plan.get("plan_id"), str) and first_plan["plan_id"]:
            plan_id = first_plan["plan_id"]
        else:
            issues.append("task.plan must contain a plan_id in its first entry")
    elif isinstance(plans, list):
        issues.append("task.plan must contain at least one plan entry")
    return plan_id


def _validate_session(session: Any, task_id: str, plan_id: str | None, issues: list[str]) -> str | None:
    if not isinstance(session, dict):
        issues.append("session record must be an object")
        return None
    for field in ("session_id", "task_id", "started_at"):
        _required_string(session, field, issues, "session")
    _required_object(session, "selected_context", issues, "session")
    if session.get("task_id") != task_id:
        issues.append("session.task_id does not match task.task_id")
    if session.get("status") not in SESSION_STATUSES:
        issues.append(f"session.status is not one of {sorted(SESSION_STATUSES)}")
    if plan_id and session.get("plan_id") not in (None, plan_id):
        issues.append("session.plan_id does not match task.plan")
    session_id = session.get("session_id")
    if not isinstance(session_id, str) or not _SAFE_ID.fullmatch(session_id):
        issues.append("session.session_id must be a filesystem-safe identifier")
    return session_id if isinstance(session_id, str) else None


def _validate_run(
    run: Any,
    task_id: str,
    session_id: str | None,
    plan_id: str | None,
    issues: list[str],
    label: str,
) -> str | None:
    if not isinstance(run, dict):
        issues.append(f"{label} must be an object")
        return None
    for field in ("run_id", "session_id", "task_id", "execution_profile_id", "started_at"):
        _required_string(run, field, issues, label)
    if run.get("task_id") != task_id:
        issues.append(f"{label}.task_id does not match task.task_id")
    if session_id and run.get("session_id") != session_id:
        issues.append(f"{label}.session_id does not match session.session_id")
    if run.get("status") not in RUN_STATUSES:
        issues.append(f"{label}.status is not one of {sorted(RUN_STATUSES)}")
    if plan_id and run.get("plan_id") not in (None, plan_id):
        issues.append(f"{label}.plan_id does not match task.plan")
    run_id = run.get("run_id")
    if not isinstance(run_id, str) or not _SAFE_ID.fullmatch(run_id):
        issues.append(f"{label}.run_id must be a filesystem-safe identifier")
    return run_id if isinstance(run_id, str) else None


def validate_completion_payload(completion: Any, *, task_id: str | None = None, plan_id: str | None = None) -> dict[str, Any]:
    """Validate one normalized or legacy completion payload."""
    issues: list[str] = []
    if not isinstance(completion, dict):
        raise SessionValidationError("completion payload must be an object")
    artifact_type = completion.get("artifact_type")
    if artifact_type == "normalized-execution-result":
        try:
            validate_normalized_execution_result(completion)
        except ExecutionResultError as exc:
            issues.append(str(exc))
    elif artifact_type == "execution-completion-record":
        for field in ("version", "task_id", "plan_id", "status", "ended_at"):
            _required_string(completion, field, issues, "completion")
        for field in ("selected_context", "runtime", "execution_topology"):
            _required_object(completion, field, issues, "completion")
        for field in ("evidence_requirements", "decisions", "evidence", "approvals", "artifacts", "unresolved_conditions"):
            _required_list(completion, field, issues, "completion")
        if "execution_realization" in completion:
            try:
                validate_execution_realization(completion["execution_realization"])
            except ExecutionResultError as exc:
                issues.append(str(exc))
        for field in ("role_turns", "handoffs", "verification"):
            if field in completion:
                _required_list(completion, field, issues, "completion")
    else:
        issues.append("completion.artifact_type must be normalized-execution-result or execution-completion-record")
    if task_id and completion.get("task_id") != task_id:
        issues.append("completion.task_id does not match task.task_id")
    if plan_id and completion.get("plan_id") != plan_id:
        issues.append("completion.plan_id does not match task.plan")
    if issues:
        raise SessionValidationError("; ".join(issues))
    return dict(completion)


def validate_persisted_records(
    task_id: str,
    records: dict[str, Any],
    *,
    run_records: Iterable[dict[str, Any]] | None = None,
    completion: dict[str, Any] | None = None,
    require_completion: bool = False,
) -> dict[str, Any]:
    """Return a report describing whether a persisted evidence set is coherent."""
    issues: list[str] = []
    if not isinstance(task_id, str) or not _SAFE_ID.fullmatch(task_id):
        issues.append("task_id must be a filesystem-safe identifier")
    if not isinstance(records, dict):
        issues.append("execution records must be an object")
        records = {}
    task = records.get("task")
    session = records.get("session")
    plan_id = _validate_task(task, task_id, issues)
    session_id = _validate_session(session, task_id, plan_id, issues)
    runs = list(run_records) if run_records is not None else ([records["run"]] if isinstance(records.get("run"), dict) else [])
    if not runs:
        issues.append("at least one run record is required")
    run_ids: list[str] = []
    for index, run in enumerate(runs):
        run_id = _validate_run(run, task_id, session_id, plan_id, issues, f"run[{index}]")
        if run_id:
            if run_id in run_ids:
                issues.append(f"duplicate run_id: {run_id}")
            run_ids.append(run_id)
    if completion is None:
        if require_completion:
            issues.append("completion.json is required")
        completion_status = None
    else:
        try:
            validate_completion_payload(completion, task_id=task_id, plan_id=plan_id)
        except SessionValidationError as exc:
            issues.append(str(exc))
        completion_status = completion.get("status") if isinstance(completion, dict) else None
    return {
        "valid": not issues,
        "task_id": task_id,
        "session_id": session_id,
        "plan_id": plan_id,
        "run_ids": run_ids,
        "completion_status": completion_status,
        "issues": issues,
    }


def _read_json(path: Path, issues: list[str]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        issues.append(f"missing persisted evidence: {path.name}")
    except (OSError, json.JSONDecodeError) as exc:
        issues.append(f"cannot read {path.name}: {exc}")
    return None


def validate_session_directory(root: str | Path, task_id: str) -> dict[str, Any]:
    """Read and validate one local JSON session directory without changing it."""
    if not isinstance(task_id, str) or not _SAFE_ID.fullmatch(task_id):
        return {
            "valid": False,
            "task_id": task_id,
            "session_path": None,
            "issues": ["task_id must be a filesystem-safe identifier"],
        }
    task_root = Path(root).expanduser() / task_id
    issues: list[str] = []
    if (task_root / ".pending-write.json").exists():
        issues.append("pending persisted write requires recovery")
    task = _read_json(task_root / "task.json", issues)
    session = _read_json(task_root / "session.json", issues)
    completion = _read_json(task_root / "completion.json", issues)
    runs_root = task_root / "runs"
    try:
        run_paths = sorted(runs_root.glob("*.json"))
    except OSError as exc:
        issues.append(f"cannot enumerate runs: {exc}")
        run_paths = []
    runs = [_read_json(path, issues) for path in run_paths]
    report = validate_persisted_records(
        task_id,
        {"task": task, "session": session},
        run_records=[run for run in runs if run is not None],
        completion=completion,
        require_completion=True,
    )
    report["session_path"] = str(task_root)
    report["issues"] = issues + report["issues"]
    report["valid"] = not report["issues"]
    return report


__all__ = [
    "RUN_STATUSES",
    "SESSION_STATUSES",
    "TASK_STATUSES",
    "SessionValidationError",
    "validate_completion_payload",
    "validate_persisted_records",
    "validate_session_directory",
]
