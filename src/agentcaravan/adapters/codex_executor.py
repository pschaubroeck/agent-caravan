"""Codex execution boundaries and a truthful dry-run executor."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol

from .codex_execution_surface import CodexExecutionRequest, CodexExecutionSurface


class CodexExecutionError(ValueError):
    """Raised when a Codex execution surface cannot consume a prepared brief."""


class CodexExecutionExecutor(Protocol):
    """Compatibility callable boundary for a live or simulated Codex task."""

    def __call__(self, scenario: dict[str, Any], brief: dict[str, Any]) -> dict[str, Any]:
        """Execute one scenario and return a raw runtime result payload."""
        ...


class DryRunCodexExecutor:
    """Simulate one sequential Codex task without claiming live execution."""

    execution_mode = "dry-run"

    def execute(self, request: CodexExecutionRequest) -> dict[str, Any]:
        records = request.records
        if not isinstance(records, dict):
            raise CodexExecutionError("Codex request is missing execution records")
        role_lanes = request.brief.get("role_lanes", [])
        stage_checkpoints = request.brief.get("stage_checkpoints", [])
        if not isinstance(role_lanes, list) or not isinstance(stage_checkpoints, list):
            raise CodexExecutionError("Codex brief has invalid role or stage projections")

        ended_at = datetime.now(timezone.utc).isoformat()
        completed_stages = [
            checkpoint["stage_id"]
            for checkpoint in stage_checkpoints
            if isinstance(checkpoint, dict) and checkpoint.get("stage_id")
        ]
        active_roles = [
            lane["role_id"]
            for lane in role_lanes
            if isinstance(lane, dict) and lane.get("role_id")
        ]
        evidence = [
            {
                "kind": requirement["kind"],
                "status": "unverified",
                **(
                    {"stage_id": requirement["stage_id"]}
                    if isinstance(requirement.get("stage_id"), str)
                    else {}
                ),
                **(
                    {"role_id": requirement["owner_role"]}
                    if isinstance(requirement.get("owner_role"), str)
                    else {}
                ),
                "source": "codex-dry-run",
                "summary": "Requirement projected but not produced by a live Codex task.",
            }
            for requirement in request.brief.get("evidence_requirements", [])
            if isinstance(requirement, dict) and requirement.get("required") and requirement.get("kind")
        ]
        records["task"]["status"] = "completed"
        records["session"]["status"] = "completed"
        records["session"]["ended_at"] = ended_at
        records["run"]["status"] = "completed"
        records["run"]["ended_at"] = ended_at
        records["run"]["evidence"] = list(evidence)

        return {
            "status": "completed",
            "execution_realization": {
                "mode": "simulated-sequential",
                "native_subagents": False,
                "parallel_lane_ids": [],
                "reason": "Dry-run projects the workflow without executing separate role turns.",
            },
            "active_roles": active_roles,
            "completed_stages": completed_stages,
            "decisions": [],
            "role_turns": [
                {
                    "role_turn_id": f"{records['run']['run_id']}-{lane['role_id']}",
                    "task_id": records["task"]["task_id"],
                    "role_id": lane["role_id"],
                    "status": "unverified",
                    "summary": "Role lane projected; no live role turn occurred.",
                }
                for lane in role_lanes
                if isinstance(lane, dict) and lane.get("role_id")
            ],
            "handoffs": [],
            "approvals": [],
            "artifacts": [],
            "evidence": evidence,
            "verification": [
                {
                    "kind": "dry-run",
                    "status": "unverified",
                    "summary": "No live Codex task execution occurred.",
                }
            ],
            "failures": [],
            "retries": [],
            "metadata": {
                "execution_mode": self.execution_mode,
                "execution_records": records,
                "unverified": ["no live Codex task execution occurred"],
                "persistence_mode": "requested-store" if request.store is not None else "unpersisted",
            },
        }

    def __call__(self, scenario: dict[str, Any], brief: dict[str, Any]) -> dict[str, Any]:
        """Retain direct-call convenience for callers outside the bridge."""
        records = brief.get("execution_records")
        if not isinstance(records, dict):
            raise CodexExecutionError("Codex brief is missing execution_records")
        request = CodexExecutionRequest(
            scenario=scenario,
            prepared={},
            brief=brief,
            records=records,
        )
        return self.execute(request)


__all__ = ["CodexExecutionError", "CodexExecutionExecutor", "DryRunCodexExecutor"]
