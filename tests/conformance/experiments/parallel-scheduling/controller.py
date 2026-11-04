"""Run the portable dependency-wait scenario through bounded Codex stages."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Protocol

from agentcaravan.execution_result import normalize_execution_result


SCENARIO_ID = "dependency-wait-with-independent-work"
WORK_ITEMS = [
    {
        "id": "design",
        "stage_id": "implementation",
        "role_id": "quality-engineer",
        "purpose": "Resolve the design question that implementation depends on.",
    },
    {
        "id": "independent-analysis",
        "stage_id": "implementation",
        "role_id": "software-architect",
        "purpose": "Complete unrelated analysis while the design answer is pending.",
    },
    {
        "id": "implement",
        "stage_id": "implementation",
        "role_id": "engineer",
        "purpose": "Produce an implementation plan after the design answer.",
        "depends_on": ["design"],
    },
]


class StageRunner(Protocol):
    def execute(self, *, task_id: str, run_id: str, stage_id: str, role_id: str,
                instruction: str, context: dict[str, Any] | None = None) -> dict[str, Any]: ...


def _event(item: dict[str, Any], status: str, timestamp: str) -> dict[str, Any]:
    return {
        "kind": "work-item",
        "work_item_id": item["id"],
        "role_id": item["role_id"],
        "stage_id": item["stage_id"],
        "status": status,
        "timestamp": timestamp,
        "dependency_ids": item.get("depends_on", []),
        "evidence_source": "adapter-observed",
    }


def build_verification_record(
    timeline: dict[str, Any],
    *,
    model: str,
    runtime_version: str,
    evidence_ref: str,
    recorded_at: str,
) -> dict[str, Any]:
    conformance = timeline["scheduling_conformance"]
    status = {"pass": "pass", "failed": "fail", "unverified": "unverified"}.get(
        conformance["status"], "unverified"
    )
    return {
        "record_id": f"{timeline['run_id']}-verification",
        "adapter": {"id": "codex-desktop-agent-runtime", "version": "1.1.0"},
        "runtime": {"product": "Codex CLI", "version": runtime_version},
        "execution_surface": "codex exec --json; read-only, one invocation per work item",
        "configuration": {
            "material_configuration": {
                "model": model,
                "sandbox": "read-only",
                "max_concurrent_work_items": 2,
            }
        },
        "scenario": {
            "id": SCENARIO_ID,
            "version": "1.0.0",
            "capability_ids": ["parallel_lane_execution"],
        },
        "result": {
            "status": status,
            "summary": "; ".join(conformance["issues"])
            or "Independent analysis overlapped the dependency wait and implementation resumed after the design answer.",
            "limitations": [
                "This verifies Agent Caravan's Codex stage controller and CLI invocation scheduling; it does not establish all Codex orchestration capabilities or work quality."
            ],
        },
        "recorded_at": recorded_at,
        "provenance": {
            "kind": "adapter-executed",
            "description": "Controller-observed Codex CLI invocation timestamps and native thread identities; model reports were not used as timeline evidence.",
        },
        "evidence_refs": [evidence_ref],
    }


def run_scenario(
    runner: StageRunner,
    *,
    task_id: str,
    run_id: str,
    clock: Any = lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
) -> dict[str, Any]:
    """Execute ready work concurrently and release the dependent item on completion."""
    by_id = {item["id"]: item for item in WORK_ITEMS}
    started = clock()
    events = [
        _event(by_id["implement"], "queued", started),
        _event(by_id["implement"], "waiting", started),
        _event(by_id["design"], "queued", started),
        _event(by_id["independent-analysis"], "queued", started),
    ]
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="agentcaravan-work-item") as pool:
        design_future = pool.submit(
            runner.execute,
            task_id=task_id,
            run_id=f"{run_id}-design",
            stage_id=by_id["design"]["stage_id"],
            role_id=by_id["design"]["role_id"],
            instruction=(
                "Resolve this design question: what one check must be satisfied before "
                "implementation starts? Give one concise, actionable check."
            ),
        )
        independent_future = pool.submit(
            runner.execute,
            task_id=task_id,
            run_id=f"{run_id}-independent-analysis",
            stage_id=by_id["independent-analysis"]["stage_id"],
            role_id=by_id["independent-analysis"]["role_id"],
            instruction=(
                "While the design question is being resolved, identify one independent "
                "architecture risk check for a small, read-only documentation change. "
                "Do not answer or depend on the design question."
            ),
        )
        design = design_future.result()
        events.extend([
            _event(by_id["design"], "started", design["started_at"]),
            _event(by_id["design"], "completed", design["completed_at"]),
        ])
        implementation = runner.execute(
            task_id=task_id,
            run_id=f"{run_id}-implement",
            stage_id=by_id["implement"]["stage_id"],
            role_id=by_id["implement"]["role_id"],
            instruction="Prepare a concise implementation plan using the resolved design check.",
            context={"design_answer": design["report"]},
        )
        independent = independent_future.result()
        events.extend([
            _event(by_id["independent-analysis"], "started", independent["started_at"]),
            _event(by_id["independent-analysis"], "completed", independent["completed_at"]),
            _event(by_id["implement"], "resumed", implementation["started_at"]),
            _event(by_id["implement"], "completed", implementation["completed_at"]),
        ])

    prepared = {
        "status": "ready",
        "plan": {
            "id": f"{run_id}-plan",
            "task": {"task_id": task_id},
            "execution_topology": {"work_items": WORK_ITEMS},
            "steps": [],
            "role_assignments": [
                {"role_id": item["role_id"], "participation": "required"}
                for item in WORK_ITEMS
            ],
        },
        "context": {},
    }
    normalized = normalize_execution_result(
        prepared,
        {
            "status": "completed",
            "execution_realization": {"mode": "unreported", "native_subagents": False},
            "active_roles": [item["role_id"] for item in WORK_ITEMS],
            "execution_events": events,
        },
        scenario_id=SCENARIO_ID,
    )
    independent_interval_overlaps_wait = (
        independent["started_at"] < design["completed_at"]
        and independent["completed_at"] > design["started_at"]
    )
    if not independent_interval_overlaps_wait:
        normalized["scheduling_conformance"]["status"] = "unverified"
        normalized["scheduling_conformance"]["issues"].append(
            "independent work did not overlap the dependency wait interval"
        )
    return {
        "task_id": task_id,
        "run_id": run_id,
        "scenario_id": SCENARIO_ID,
        "plan_id": prepared["plan"]["id"],
        "work_items": WORK_ITEMS,
        "execution_events": normalized["execution_events"],
        "scheduling_conformance": normalized["scheduling_conformance"],
        "stage_receipts": [
            {key: receipt[key] for key in (
                "run_id", "stage_id", "role_id", "session_id", "started_at", "completed_at", "version"
            )}
            for receipt in (design, independent, implementation)
        ],
    }
