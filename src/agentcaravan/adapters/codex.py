"""Codex adapter namespace with compatibility and conformance exports."""

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

from ..codex_adapter import (
    CodexAdapterError,
    project_execution_brief,
    project_resolved_execution_brief,
    project_team_guidance,
)
from ..conformance import ConformanceSuiteResult, run_conformance_suite
from ..execution_result import normalize_execution_result, retain_run_observability
from ..orchestration import OrchestrationError, build_execution_records, prepare_execution
from ..observability import RunObservation, _marker_outcome
from ..session_store import ExecutionRecordStore
from ..telemetry import normalize_execution_events
from .codex_execution_surface import (
    CodexExecutionRequest,
    CodexExecutionSurface,
    LegacyCodexExecutionSurface,
)
from .codex_executor import CodexExecutionError, CodexExecutionExecutor, DryRunCodexExecutor


def prepare_codex_execution(resolved: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    """Prepare a portable plan and its Codex-specific projection."""
    prepared = prepare_execution(resolved, task)
    runtime = resolved.get("runtime")
    if not isinstance(runtime, dict) or runtime.get("adapter_id") != "codex-desktop-agent-runtime":
        raise OrchestrationError("resolved runtime is not the Codex Desktop Agent Runtime")
    try:
        brief = project_execution_brief(prepared["plan"])
    except CodexAdapterError as error:
        raise OrchestrationError(str(error)) from error
    observability = deepcopy(runtime.get("observability", {
        "enabled": False, "export": "local", "capture_content": False,
    }))
    brief["observability"] = observability
    prepared.update(
        {
            "runtime": {
                "adapter_id": runtime["adapter_id"],
                "runtime_profile_id": runtime.get("runtime_profile_id")
                or resolved.get("context", {}).get("runtime_profile_id"),
                "degraded_capabilities": list(runtime.get("degraded_capabilities", [])),
                "observability": deepcopy(observability),
                "execution_realization": {
                    "mode": "unreported",
                    "native_subagents": False,
                    "reason": "Preparation describes the selected runtime capability; execution realization is recorded only after dispatch.",
                },
            },
            "projection": brief,
        }
    )
    return prepared


def normalize_codex_result(
    prepared: dict[str, Any],
    runtime_result: dict[str, Any],
    *,
    scenario_id: str | None = None,
    _allow_unverified_required_evidence: bool = False,
) -> dict[str, Any]:
    """Normalize a Codex orchestration result without changing its semantics."""
    result = normalize_execution_result(
        prepared,
        runtime_result,
        scenario_id=scenario_id,
        allow_unverified_required_evidence=_allow_unverified_required_evidence,
    )
    if not runtime_result.get("reasoning_evidence"):
        role_turns = result.get("role_turns", [])
        result["reasoning_evidence"] = []
        for item in prepared.get("projection", {}).get("reasoning_assignments", []):
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
            result["reasoning_evidence"].append(
                {
                    "stage_id": item["stage_id"],
                    "role_id": item["role_id"],
                    "requested_level": item["level"],
                    "requested_runtime_value": item.get("codex_reasoning_effort"),
                    "effective_level": None,
                    "effective_runtime_value": None,
                    "status": "unverified",
                    "dispatch_status": "accepted" if accepted else "not-attempted",
                    "telemetry_status": "unverified",
                    "evidence_source": "native-dispatch" if accepted else "plan-projection",
                    **({"worker_ref": matching_turn["worker_ref"]} if accepted else {}),
                }
            )
    return result


def run_codex_task(
    resolved: dict[str, Any],
    task: dict[str, Any],
    executor: CodexExecutionSurface | CodexExecutionExecutor | Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
    *,
    store: ExecutionRecordStore | None = None,
    session_id: str | None = None,
    run_id: str | None = None,
    attempt: int = 1,
) -> dict[str, Any]:
    """Execute one prepared Codex task and return its normalized result."""
    prepared = prepare_codex_execution(resolved, task)
    task_id = prepared["plan"]["task"]["task_id"]
    request = _build_codex_request(
        prepared,
        {"id": task_id, "task": task},
        store=store,
        session_id=session_id or f"{task_id}-codex-session",
        run_id=run_id or f"{task_id}-codex-run-{attempt}",
        attempt=attempt,
    )
    _, normalized = _execute_codex_request(request, executor)
    return normalized


def run_codex_conformance_suite(
    resolved: dict[str, Any],
    scenarios: Iterable[dict[str, Any]],
    executor: CodexExecutionSurface | CodexExecutionExecutor | Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
    *,
    store: ExecutionRecordStore | None = None,
    session_id_factory: Callable[[dict[str, Any]], str] | None = None,
    run_id_factory: Callable[[dict[str, Any]], str] | None = None,
) -> ConformanceSuiteResult:
    """Run shared scenarios through Codex projection and a supplied executor.

    The preferred executor implements ``CodexExecutionSurface.execute`` and
    receives a ``CodexExecutionRequest``. The original two-argument callback
    remains accepted through a compatibility wrapper. A store is optional so
    callers can choose whether local session persistence is enabled.

    ID factories are optional hooks for retries and resume flows. The default
    keeps the deterministic conformance IDs used by the shared scenario suite.
    """
    def prepare_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
        task = dict(scenario["task"])
        task.setdefault("task_id", f"conformance-{scenario['id']}")
        return prepare_codex_execution(resolved, task)

    def execute_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
        prepared = prepare_scenario(scenario)
        request = _build_codex_request(
            prepared,
            scenario,
            store=store,
            session_id=session_id_factory(scenario) if session_id_factory else None,
            run_id=run_id_factory(scenario) if run_id_factory else None,
        )
        _, normalized = _execute_codex_request(request, executor, scenario_id=scenario["id"])
        return normalized

    return run_conformance_suite(scenarios, execute_scenario)


def _build_codex_request(
    prepared: dict[str, Any],
    scenario: dict[str, Any],
    *,
    store: ExecutionRecordStore | None,
    session_id: str | None = None,
    run_id: str | None = None,
    attempt: int = 1,
) -> CodexExecutionRequest:
    task_id = prepared["plan"]["task"]["task_id"]
    records = build_execution_records(
        prepared,
        session_id=session_id or f"{task_id}-codex-session",
        run_id=run_id or f"{task_id}-codex-run-{attempt}",
        started_at=datetime.now(timezone.utc).isoformat(),
        attempt=attempt,
    )
    brief = dict(prepared["projection"])
    brief["execution_records"] = records
    return CodexExecutionRequest(
        scenario=scenario,
        prepared=prepared,
        brief=brief,
        records=records,
        store=store,
    )


def _execute_codex_request(
    request: CodexExecutionRequest,
    executor: CodexExecutionSurface | CodexExecutionExecutor | Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
    *,
    scenario_id: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if request.store is not None:
        request.store.write_records(request.task_id, request.records)
    surface = executor if hasattr(executor, "execute") else LegacyCodexExecutionSurface(executor)
    observation = RunObservation.start(request.prepared, request.records)
    try:
        raw_result = dict(surface.execute(request))
    except Exception as error:
        _finalize_failed_request(request, error)
        if observation is not None:
            observation.finish("error")
        raise
    run_record = raw_result.get("run", {})
    if not isinstance(run_record, dict):
        run_record = {"runtime_run_record": run_record}
    else:
        run_record = dict(run_record)
    runtime_run_id = run_record.get("run_id")
    if runtime_run_id and runtime_run_id != request.run_id:
        run_record.setdefault("runtime_run_id", runtime_run_id)
    run_record["run_id"] = request.run_id
    run_record["session_id"] = request.session_id
    raw_result["run"] = run_record
    try:
        normalized = normalize_codex_result(
            request.prepared,
            raw_result,
            scenario_id=scenario_id,
            _allow_unverified_required_evidence=isinstance(surface, DryRunCodexExecutor),
        )
    except Exception:
        if observation is not None:
            observation.finish("error")
        raise
    _update_records_from_result(request.records, normalized)
    if observation is not None:
        observation.finish(_marker_outcome(normalized["status"]))
        observation.attach(normalized, request.records["run"])
    runtime_metadata = raw_result.setdefault("metadata", {})
    runtime_execution_records = runtime_metadata.get("execution_records")
    if "execution_records" in runtime_metadata and runtime_metadata["execution_records"] != request.records:
        runtime_metadata.setdefault("runtime_execution_records", runtime_metadata["execution_records"])
    runtime_metadata["execution_records"] = request.records
    normalized_metadata = normalized.setdefault("metadata", {})
    normalized_metadata["execution_records"] = request.records
    if runtime_execution_records is not None and runtime_execution_records != request.records:
        normalized_metadata["runtime_execution_records"] = runtime_execution_records
    if request.store is not None:
        request.store.write_records(request.task_id, request.records)
        request.store.write_completion(request.task_id, normalized)
    return raw_result, normalized


def _finalize_failed_request(request: CodexExecutionRequest, error: Exception) -> None:
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


def _update_records_from_result(records: dict[str, dict[str, Any]], result: dict[str, Any]) -> None:
    """Reflect normalized result state into the local task/session/run records."""
    ended_at = datetime.now(timezone.utc).isoformat()
    status = result["status"]
    task_status = {
        "completed": "completed",
        "cancelled": "cancelled",
        "blocked": "blocked",
        "blocked-until-approved": "blocked",
    }.get(status, "active")
    session_status = {
        "completed": "completed",
        "failed": "failed",
        "cancelled": "cancelled",
        "interrupted": "paused",
    }.get(status, "active")
    records["task"]["status"] = task_status
    records["task"]["evidence"] = list(result.get("evidence", []))
    records["task"]["decisions"] = list(result.get("decisions", []))
    records["task"]["role_turns"] = list(result.get("role_turns", []))
    records["task"]["handoffs"] = list(result.get("handoffs", []))
    records["task"]["approvals"] = list(result.get("approvals", []))
    records["task"]["checkpoints"] = [result["checkpoint"]] if result.get("checkpoint") else []
    records["task"]["idempotency_records"] = list(result.get("idempotency_records", []))
    records["task"]["artifacts"] = list(result.get("artifacts", []))
    records["task"]["reasoning_evidence"] = list(result.get("reasoning_evidence", []))
    records["task"]["execution_events"] = list(result.get("execution_events", []))
    records["task"]["scheduling_conformance"] = result.get("scheduling_conformance")
    records["task"]["topology_conformance"] = result.get("topology_conformance")
    if "execution_diagnostics" in result:
        records["task"]["execution_diagnostics"] = result["execution_diagnostics"]
    records["session"]["status"] = session_status
    records["session"]["evidence"] = list(result.get("evidence", []))
    records["session"]["execution_realization"] = result.get("execution_realization", records["session"].get("execution_realization"))
    records["session"]["role_turns"] = list(result.get("role_turns", []))
    records["session"]["handoffs"] = list(result.get("handoffs", []))
    records["session"]["checkpoints"] = [result["checkpoint"]] if result.get("checkpoint") else []
    records["session"]["reasoning_evidence"] = list(result.get("reasoning_evidence", []))
    records["session"]["execution_events"] = list(result.get("execution_events", []))
    records["session"]["scheduling_conformance"] = result.get("scheduling_conformance")
    records["session"]["topology_conformance"] = result.get("topology_conformance")
    if "execution_diagnostics" in result:
        records["session"]["execution_diagnostics"] = result["execution_diagnostics"]
    records["session"]["ended_at"] = ended_at if status not in {"interrupted", "blocked", "blocked-until-approved"} else None
    records["run"]["status"] = status if status in {"interrupted", "completed", "failed", "cancelled", "degraded"} else "active"
    records["run"]["ended_at"] = ended_at
    records["run"]["evidence"] = list(result.get("evidence", []))
    records["run"]["execution_realization"] = result.get("execution_realization", records["run"].get("execution_realization"))
    records["run"]["role_turns"] = list(result.get("role_turns", []))
    records["run"]["handoffs"] = list(result.get("handoffs", []))
    records["run"]["verification"] = list(result.get("verification", []))
    records["run"]["checkpoints"] = [result["checkpoint"]] if result.get("checkpoint") else []
    records["run"]["idempotency_records"] = list(result.get("idempotency_records", []))
    records["run"]["reasoning_evidence"] = list(result.get("reasoning_evidence", []))
    records["run"]["execution_events"] = list(result.get("execution_events", []))
    records["run"]["scheduling_conformance"] = result.get("scheduling_conformance")
    records["run"]["topology_conformance"] = result.get("topology_conformance")
    if "execution_diagnostics" in result:
        records["run"]["execution_diagnostics"] = result["execution_diagnostics"]
    records["run"]["events"] = normalize_execution_events(
        result.get("execution_events", []),
        source=records["run"].get("runtime_adapter_id") or "codex-adapter",
        context={key: records["run"].get(key) for key in ("task_id", "session_id", "run_id")},
    )
    retain_run_observability(records["run"], result)

__all__ = [
    "CodexAdapterError",
    "CodexExecutionError",
    "CodexExecutionRequest",
    "CodexExecutionExecutor",
    "CodexExecutionSurface",
    "DryRunCodexExecutor",
    "OrchestrationError",
    "prepare_codex_execution",
    "normalize_codex_result",
    "project_execution_brief",
    "project_resolved_execution_brief",
    "project_team_guidance",
    "run_codex_task",
    "run_codex_conformance_suite",
]
