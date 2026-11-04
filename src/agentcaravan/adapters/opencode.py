"""OpenCode projection and bridge to the shared conformance runner."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

from ..conformance import ConformanceSuiteResult, run_conformance_suite
from ..execution_result import normalize_execution_result, retain_run_observability
from ..orchestration import OrchestrationError, build_execution_records, prepare_execution
from ..observability import RunObservation, _marker_outcome
from ..session_store import ExecutionRecordStore
from ..telemetry import normalize_execution_events
from .opencode_execution_surface import OpenCodeExecutionRequest, OpenCodeExecutionSurface


def prepare_opencode_execution(resolved: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    """Project a portable plan into an OpenCode request without changing its intent."""
    prepared = prepare_execution(resolved, task)
    runtime = resolved.get("runtime")
    if not isinstance(runtime, dict) or runtime.get("adapter_id") != "opencode-agent-runtime":
        raise OrchestrationError("resolved runtime is not the OpenCode Agent Runtime")
    plan = prepared["plan"]
    knowledge_context = plan.get("knowledge_context") or {"layers": []}
    team_context = plan.get("context", {}).get("team_context") or {}
    supplemental_knowledge_sources = list(team_context.get("knowledge_sources", []))
    knowledge_instructions = []
    if (
        knowledge_context["layers"]
        or supplemental_knowledge_sources
        or any(item.get("documentation_references") for item in plan.get("role_assignments", []))
    ):
        knowledge_instructions.append(
            "Provide every selected knowledge_context layer to every assigned role in the declared order, "
            "then provide context.team_context.knowledge_sources in their declared order. "
            "Apply each layer's role_guidance only to the matching role. Treat trusted_sources and "
            "documentation_references as references, not fetched content, and follow policy.knowledge_access "
            "before retrieving them. Role documentation is supplemental and does not override artifact semantics."
        )
    observability = deepcopy(runtime.get("observability", {
        "enabled": False, "export": "local", "capture_content": False,
    }))
    prepared.update(
        {
            "runtime": {
                "adapter_id": runtime["adapter_id"],
                "runtime_profile_id": runtime.get("runtime_profile_id")
                or resolved.get("context", {}).get("runtime_profile_id"),
                "degraded_capabilities": list(runtime.get("degraded_capabilities", [])),
                "observability": observability,
                "execution_realization": {
                    "mode": "unreported",
                    "native_subagents": False,
                    "reason": "OpenCode execution has not been dispatched or observed.",
                },
            },
            "projection": {
                "observability": deepcopy(observability),
                "plan_id": plan["id"],
                "task": plan["task"],
                "steps": plan.get("steps", []),
                "role_assignments": plan.get("role_assignments", []),
                "execution_topology": plan.get("execution_topology"),
                "tool_requirements": plan.get("tool_requirements", []),
                "evidence_requirements": plan.get("evidence_requirements", []),
                "reasoning_assignments": plan.get("reasoning_assignments", []),
                "knowledge_context": knowledge_context,
                "supplemental_knowledge_sources": supplemental_knowledge_sources,
                "knowledge_access": plan["policy"].get(
                    "knowledge_access", {"external_sources": "enabled", "approved_sources": []}
                ),
                "instructions": knowledge_instructions,
            },
        }
    )
    return prepared


def run_opencode_task(
    resolved: dict[str, Any],
    task: dict[str, Any],
    surface: OpenCodeExecutionSurface,
    *,
    store: ExecutionRecordStore | None = None,
    session_id: str | None = None,
    run_id: str | None = None,
    attempt: int = 1,
) -> dict[str, Any]:
    """Execute one prepared task through an OpenCode surface."""
    prepared = prepare_opencode_execution(resolved, task)
    task_id = prepared["plan"]["task"]["task_id"]
    request = _build_request(
        prepared,
        {"id": task_id, "task": task},
        store=store,
        session_id=session_id or f"{task_id}-opencode-session",
        run_id=run_id or f"{task_id}-opencode-run-{attempt}",
        attempt=attempt,
    )
    _, normalized = _execute(request, surface)
    return normalized


def run_opencode_conformance_suite(
    resolved: dict[str, Any],
    scenarios: Iterable[dict[str, Any]],
    surface: OpenCodeExecutionSurface,
    *,
    store: ExecutionRecordStore | None = None,
    session_id_factory: Callable[[dict[str, Any]], str] | None = None,
    run_id_factory: Callable[[dict[str, Any]], str] | None = None,
) -> ConformanceSuiteResult:
    """Run the shared case pack through an independently prepared OpenCode surface."""

    def prepare_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
        task = dict(scenario["task"])
        task.setdefault("task_id", f"conformance-{scenario['id']}")
        return prepare_opencode_execution(resolved, task)

    def execute_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
        prepared = prepare_scenario(scenario)
        request = _build_request(
            prepared,
            scenario,
            store=store,
            session_id=session_id_factory(scenario) if session_id_factory else None,
            run_id=run_id_factory(scenario) if run_id_factory else None,
        )
        raw_result, _ = _execute(request, surface, scenario_id=scenario["id"])
        return raw_result

    return run_conformance_suite(scenarios, execute_scenario, prepared=prepare_scenario)


def _build_request(
    prepared: dict[str, Any],
    scenario: dict[str, Any],
    *,
    store: ExecutionRecordStore | None,
    session_id: str | None = None,
    run_id: str | None = None,
    attempt: int = 1,
) -> OpenCodeExecutionRequest:
    task_id = prepared["plan"]["task"]["task_id"]
    records = build_execution_records(
        prepared,
        session_id=session_id or f"{task_id}-opencode-session",
        run_id=run_id or f"{task_id}-opencode-run-{attempt}",
        started_at=datetime.now(timezone.utc).isoformat(),
        attempt=attempt,
    )
    projection = dict(prepared["projection"])
    projection["execution_records"] = records
    return OpenCodeExecutionRequest(
        scenario=scenario,
        prepared=prepared,
        projection=projection,
        records=records,
        store=store,
    )


def _execute(
    request: OpenCodeExecutionRequest,
    surface: OpenCodeExecutionSurface,
    *,
    scenario_id: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if request.store is not None:
        request.store.write_records(request.task_id, request.records)
    observation = RunObservation.start(request.prepared, request.records)
    try:
        raw_result = dict(surface.execute(request))
    except Exception as error:
        _finalize_failed_request(request, error)
        if observation is not None:
            observation.finish("error")
        raise
    run_record = raw_result.get("run", {})
    run_record = dict(run_record) if isinstance(run_record, dict) else {"runtime_run_record": run_record}
    runtime_run_id = run_record.get("run_id")
    if runtime_run_id and runtime_run_id != request.run_id:
        run_record.setdefault("runtime_run_id", runtime_run_id)
    run_record.update({"run_id": request.run_id, "session_id": request.session_id})
    raw_result["run"] = run_record
    try:
        normalized = normalize_execution_result(request.prepared, raw_result, scenario_id=scenario_id)
    except Exception:
        if observation is not None:
            observation.finish("error")
        raise
    _update_records(request.records, normalized)
    if observation is not None:
        observation.finish(_marker_outcome(normalized["status"]))
        observation.attach(normalized, request.records["run"])
    metadata = raw_result.setdefault("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
        raw_result["metadata"] = metadata
    existing = metadata.get("execution_records")
    if existing is not None and existing != request.records:
        metadata.setdefault("runtime_execution_records", existing)
    metadata["execution_records"] = request.records
    normalized_metadata = normalized.setdefault("metadata", {})
    normalized_metadata["execution_records"] = request.records
    if existing is not None and existing != request.records:
        normalized_metadata["runtime_execution_records"] = existing
    if request.store is not None:
        request.store.write_records(request.task_id, request.records)
        request.store.write_completion(request.task_id, normalized)
    return raw_result, normalized


def _finalize_failed_request(request: OpenCodeExecutionRequest, error: Exception) -> None:
    """Persist a terminal run state when runtime dispatch raises."""
    ended_at = datetime.now(timezone.utc).isoformat()
    request.records["task"]["status"] = "blocked"
    request.records["session"].update({"status": "failed", "ended_at": ended_at})
    request.records["run"].update({
        "status": "failed",
        "ended_at": ended_at,
        "failure": {"type": type(error).__name__},
    })
    if request.store is not None:
        request.store.write_records(request.task_id, request.records)


def _update_records(records: dict[str, dict[str, Any]], result: dict[str, Any]) -> None:
    ended_at = datetime.now(timezone.utc).isoformat()
    status = result["status"]
    records["task"]["status"] = {
        "completed": "completed",
        "cancelled": "cancelled",
        "blocked": "blocked",
        "blocked-until-approved": "blocked",
    }.get(status, "active")
    records["session"]["status"] = {
        "completed": "completed",
        "failed": "failed",
        "cancelled": "cancelled",
        "interrupted": "paused",
    }.get(status, "active")
    for key in ("evidence", "decisions", "role_turns", "handoffs", "approvals", "idempotency_records", "artifacts", "reasoning_evidence", "execution_events"):
        records["task"][key] = list(result.get(key, []))
    for key in ("evidence", "role_turns", "handoffs", "reasoning_evidence", "execution_events"):
        records["session"][key] = list(result.get(key, []))
    for key in ("evidence", "role_turns", "handoffs", "verification", "idempotency_records", "reasoning_evidence", "execution_events"):
        records["run"][key] = list(result.get(key, []))
    checkpoints = [result["checkpoint"]] if result.get("checkpoint") else []
    for record in records.values():
        record["checkpoints"] = checkpoints
        record["topology_conformance"] = result.get("topology_conformance")
        record["scheduling_conformance"] = result.get("scheduling_conformance")
        if "execution_diagnostics" in result:
            record["execution_diagnostics"] = result["execution_diagnostics"]
    records["session"]["execution_realization"] = result["execution_realization"]
    records["session"]["ended_at"] = ended_at if status not in {"interrupted", "blocked", "blocked-until-approved"} else None
    records["run"]["status"] = status if status in {"interrupted", "completed", "failed", "cancelled", "degraded"} else "active"
    records["run"]["execution_realization"] = result["execution_realization"]
    records["run"]["ended_at"] = ended_at
    records["run"]["events"] = normalize_execution_events(
        result.get("execution_events", []),
        source=records["run"].get("runtime_adapter_id") or "opencode-adapter",
        context={key: records["run"].get(key) for key in ("task_id", "session_id", "run_id")},
    )
    retain_run_observability(records["run"], result)


__all__ = ["prepare_opencode_execution", "run_opencode_task", "run_opencode_conformance_suite"]
