"""Runtime-neutral harness for comparing adapter execution semantics."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable

from .execution_result import normalize_execution_result, validate_normalized_execution_result


ScenarioExecutor = Callable[[dict[str, Any]], dict[str, Any]]
PreparedProvider = Callable[[dict[str, Any]], dict[str, Any]]


class ConformanceError(ValueError):
    """Raised when a conformance suite contains invalid or failing cases."""


@dataclass(frozen=True)
class ConformanceCaseResult:
    """The semantic comparison result for one scenario."""

    scenario_id: str
    passed: bool
    result: dict[str, Any] | None
    mismatches: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConformanceSuiteResult:
    """The aggregate result for a conformance suite."""

    cases: tuple[ConformanceCaseResult, ...]

    @property
    def passed(self) -> bool:
        return all(case.passed for case in self.cases)

    @property
    def failures(self) -> tuple[ConformanceCaseResult, ...]:
        return tuple(case for case in self.cases if not case.passed)

    def raise_for_failures(self) -> None:
        if self.passed:
            return
        details = []
        for case in self.failures:
            details.append(f"{case.scenario_id}: " + "; ".join(case.mismatches))
        raise ConformanceError("conformance failures: " + " | ".join(details))


def load_conformance_scenarios(path: str | Path) -> list[dict[str, Any]]:
    """Load and structurally validate the shared scenario catalog."""
    scenario_path = Path(path)
    try:
        payload = json.loads(scenario_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConformanceError(f"cannot read conformance scenarios: {scenario_path}") from exc
    except json.JSONDecodeError as exc:
        raise ConformanceError(f"conformance scenarios are not valid JSON: {scenario_path}") from exc
    scenarios = payload.get("scenarios") if isinstance(payload, dict) else None
    if not isinstance(scenarios, list) or not scenarios:
        raise ConformanceError("conformance scenario catalog must contain a non-empty scenarios list")
    seen: set[str] = set()
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            raise ConformanceError("each conformance scenario must be an object")
        scenario_id = scenario.get("id")
        if not isinstance(scenario_id, str) or not scenario_id:
            raise ConformanceError("each conformance scenario requires a stable id")
        if scenario_id in seen:
            raise ConformanceError(f"duplicate conformance scenario: {scenario_id}")
        seen.add(scenario_id)
        if not isinstance(scenario.get("task"), dict) or not isinstance(scenario.get("expected"), dict):
            raise ConformanceError(f"scenario {scenario_id} requires task and expected objects")
        if not scenario["expected"].get("status"):
            raise ConformanceError(f"scenario {scenario_id} requires an expected status")
    return [dict(scenario) for scenario in scenarios]


def _handoff_statuses(result: dict[str, Any]) -> list[dict[str, Any]]:
    statuses = []
    for handoff in result.get("handoffs", []):
        if not isinstance(handoff, dict):
            continue
        statuses.append(
            {
                "from": handoff.get("from", handoff.get("sender_role")),
                "to": handoff.get("to", handoff.get("receiver_role")),
                "status": handoff.get("status"),
            }
        )
    return statuses


def _approval_statuses(result: dict[str, Any]) -> list[dict[str, Any]]:
    statuses = []
    for approval in result.get("approvals", []):
        if not isinstance(approval, dict):
            continue
        statuses.append({"trigger": approval.get("trigger"), "status": approval.get("status")})
    return statuses


def _semantic_projection(result: dict[str, Any]) -> dict[str, Any]:
    metadata = result.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    resume = result.get("resume", {})
    if not isinstance(resume, dict):
        resume = {}
    run = result.get("run", {})
    if not isinstance(run, dict):
        run = {}
    checkpoint = result.get("checkpoint")
    idempotency_records = result.get("idempotency_records", [])
    workflow_assessment = result.get("workflow_assessment", {})
    if not isinstance(workflow_assessment, dict):
        workflow_assessment = {}
    idempotency_status = metadata.get("idempotency_status")
    if idempotency_status is None and idempotency_records:
        idempotency_status = idempotency_records[0].get("status")
    return {
        "status": result.get("status"),
        "active_roles": list(result.get("active_roles", [])),
        "completed_stages": list(result.get("completed_stages", [])),
        "handoff_statuses": _handoff_statuses(result),
        "approval_statuses": _approval_statuses(result),
        "failure_count": len(result.get("failures", [])),
        "run_count": resume.get("run_count", run.get("run_count")),
        "same_task_id": resume.get("same_task_id"),
        "prior_run_preserved": resume.get("prior_run_preserved"),
        "checkpoint_status": checkpoint.get("status") if isinstance(checkpoint, dict) else None,
        "resume_required": resume.get("required"),
        "replay_from_stage": resume.get("replay_from_stage"),
        "idempotency_status": idempotency_status,
        "side_effect_count": metadata.get("side_effect_count"),
        "idempotency_key_required": metadata.get("idempotency_key_required"),
        "degraded_capabilities": [
            item.get("capability") if isinstance(item, dict) else item
            for item in result.get("degraded_capabilities", [])
        ],
        "serial_fallback_recorded": metadata.get("serial_fallback_recorded"),
        "topology_conformance": result.get("topology_conformance"),
        "scheduling_conformance": result.get("scheduling_conformance"),
        "workflow_assessment_status": workflow_assessment.get("status"),
        "workflow_criteria_statuses": [
            {"criterion_id": item.get("criterion_id"), "status": item.get("status")}
            for item in workflow_assessment.get("criteria", [])
            if isinstance(item, dict)
        ],
    }


def _compare_result(scenario: dict[str, Any], result: dict[str, Any]) -> list[str]:
    expected = scenario["expected"]
    observed = _semantic_projection(result)
    mismatches: list[str] = []
    raw_events = [item for item in result.get("execution_events", []) if isinstance(item, dict)]
    for field, expected_value in expected.items():
        if field == "required_completion_fields":
            missing = [name for name in expected_value if name not in result or result[name] is None]
            if missing:
                mismatches.append(f"missing completion fields: {missing}")
            continue
        if field == "required_tool_evidence":
            kinds = {item.get("kind") for item in result.get("evidence", []) if isinstance(item, dict)}
            missing = [kind for kind in expected_value if kind not in kinds]
            if missing:
                mismatches.append(f"missing tool evidence: {missing}")
            continue
        if field in {
            "required_evidence_records",
            "required_artifact_records",
            "forbidden_artifact_records",
            "required_approval_records",
            "forbidden_event_records",
        }:
            collection_name = {
                "required_evidence_records": "evidence",
                "required_artifact_records": "artifacts",
                "forbidden_artifact_records": "artifacts",
                "required_approval_records": "approvals",
                "forbidden_event_records": "execution_events",
            }[field]
            records = [item for item in result.get(collection_name, []) if isinstance(item, dict)]
            for expected_record in expected_value:
                if field in {"forbidden_artifact_records", "forbidden_event_records"}:
                    if any(_record_matches(expected_record, item) for item in records):
                        mismatches.append(f"forbidden {collection_name} record present: {expected_record!r}")
                    continue
                matching = next((item for item in records if _record_matches(expected_record, item)), None)
                if matching is None:
                    mismatches.append(f"missing {collection_name} record matching {expected_record!r}")
                elif expected_record.get("require_references") is True:
                    reference_field = "evidence_refs" if collection_name == "approvals" else "references"
                    if not matching.get(reference_field):
                        mismatches.append(f"{collection_name} record lacks {reference_field}: {expected_record!r}")
            continue
        if field == "required_event_order":
            for expected_event in expected_value:
                if any(
                    _record_matches(expected_event, event) and not _event_is_attributable(result, event)
                    for event in raw_events
                ):
                    mismatches.append(f"required execution event is present but cannot be attributed: {expected_event!r}")
            event_times = _attributed_event_times(result, mismatches)
            cursor = -1
            prior_timestamp = None
            for expected_event in expected_value:
                found = next(
                    (
                        index
                        for index, (_, event) in enumerate(event_times)
                        if index > cursor and _record_matches(expected_event, event)
                    ),
                    None,
                )
                if found is None:
                    mismatches.append(
                        f"missing, unattributed, or out-of-order execution event: {expected_event!r}"
                    )
                    break
                current_timestamp = event_times[found][0]
                if prior_timestamp is not None and current_timestamp <= prior_timestamp:
                    mismatches.append(f"execution events do not have strictly increasing timestamps: {expected_event!r}")
                    break
                prior_timestamp = current_timestamp
                cursor = found
            continue
        if field == "event_order_constraints":
            event_times = _attributed_event_times(result, mismatches)
            for constraint in expected_value:
                event_match = constraint.get("event", {})
                prerequisite_match = constraint.get("after", {})
                for expected_event in (event_match, prerequisite_match):
                    if any(
                        _record_matches(expected_event, event) and not _event_is_attributable(result, event)
                        for event in raw_events
                    ):
                        mismatches.append(
                            f"event relevant to ordering constraint is present but cannot be attributed: {expected_event!r}"
                        )
                event_stamps = [timestamp for timestamp, event in event_times if _record_matches(event_match, event)]
                prerequisite_stamps = [timestamp for timestamp, event in event_times if _record_matches(prerequisite_match, event)]
                if not event_stamps:
                    continue
                if not prerequisite_stamps:
                    mismatches.append(f"missing prerequisite event for order constraint: {prerequisite_match!r}")
                    continue
                latest_prerequisite = max(prerequisite_stamps)
                if any(timestamp <= latest_prerequisite for timestamp in event_stamps):
                    mismatches.append(
                        f"event occurred before required prerequisite: {event_match!r} must follow {prerequisite_match!r}"
                    )
            continue
        if field == "max_retries":
            retry_count = len(result.get("retries", []))
            if retry_count > expected_value:
                mismatches.append(f"retries expected <= {expected_value}, got {retry_count}")
            continue
        actual = observed.get(field)
        if actual != expected_value:
            mismatches.append(f"{field}: expected {expected_value!r}, got {actual!r}")
    return mismatches


def _record_matches(expected: dict[str, Any], actual: dict[str, Any]) -> bool:
    """Match only the declared semantic fields, including nested metadata."""
    for key, expected_value in expected.items():
        if key == "require_references":
            continue
        actual_value = actual.get(key)
        if isinstance(expected_value, dict):
            if not isinstance(actual_value, dict) or not _record_matches(expected_value, actual_value):
                return False
        elif actual_value != expected_value:
            return False
    return True


def _attributed_event_times(
    result: dict[str, Any],
    mismatches: list[str],
) -> list[tuple[datetime, dict[str, Any]]]:
    """Return only timestamped events tied to this task, run, and evidence."""
    run = result.get("run", {})
    expected_run_id = run.get("run_id") if isinstance(run, dict) else None
    if not isinstance(expected_run_id, str) or not expected_run_id:
        mismatches.append("execution events cannot be attributed because the normalized result has no run_id")
        return []
    event_times = []
    for event in result.get("execution_events", []):
        if not isinstance(event, dict):
            continue
        if not _event_is_attributable(result, event):
            continue
        parsed = _event_timestamp(event)
        if parsed is not None:
            event_times.append((parsed, event))
    event_times.sort(key=lambda item: item[0])
    return event_times


def _event_is_attributable(result: dict[str, Any], event: dict[str, Any]) -> bool:
    run = result.get("run", {})
    expected_run_id = run.get("run_id") if isinstance(run, dict) else None
    return (
        isinstance(expected_run_id, str)
        and bool(expected_run_id)
        and event.get("task_id") == result.get("task_id")
        and event.get("run_id") == expected_run_id
        and bool(event.get("evidence_refs"))
        and _event_timestamp(event) is not None
    )


def _event_timestamp(event: dict[str, Any]) -> datetime | None:
    timestamp = event.get("timestamp")
    if not isinstance(timestamp, str):
        return None
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def run_conformance_scenario(
    scenario: dict[str, Any],
    executor: ScenarioExecutor,
    *,
    prepared: dict[str, Any] | PreparedProvider | None = None,
) -> ConformanceCaseResult:
    """Execute and semantically compare one scenario."""
    scenario_id = scenario.get("id", "<unknown>")
    try:
        raw_result = executor(scenario)
        scenario_prepared = prepared(scenario) if callable(prepared) else prepared
        if scenario_prepared is not None:
            result = normalize_execution_result(scenario_prepared, raw_result, scenario_id=scenario_id)
        else:
            result = validate_normalized_execution_result(raw_result)
        mismatches = _compare_result(scenario, result)
        return ConformanceCaseResult(scenario_id, not mismatches, result, tuple(mismatches))
    except Exception as exc:
        return ConformanceCaseResult(scenario_id, False, None, (f"adapter result error: {exc}",))


def run_conformance_suite(
    scenarios: Iterable[dict[str, Any]],
    executor: ScenarioExecutor,
    *,
    prepared: dict[str, Any] | PreparedProvider | None = None,
) -> ConformanceSuiteResult:
    """Run shared conformance scenarios against one adapter executor."""
    cases = tuple(run_conformance_scenario(scenario, executor, prepared=prepared) for scenario in scenarios)
    return ConformanceSuiteResult(cases)


__all__ = [
    "ConformanceCaseResult",
    "ConformanceError",
    "ConformanceSuiteResult",
    "load_conformance_scenarios",
    "run_conformance_scenario",
    "run_conformance_suite",
]
