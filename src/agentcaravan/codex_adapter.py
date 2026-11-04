"""Project resolved Agent Caravan semantics into a Codex execution brief."""

from __future__ import annotations

from typing import Any

from .execution_plan import (
    ExecutionPlanError,
    build_portable_execution_plan,
    normalize_team_context,
    validate_portable_execution_plan,
)


class CodexAdapterError(ValueError):
    """Raised when a resolved bundle cannot be projected for Codex."""


CODEX_REASONING_EFFORT = {"focused": "low", "standard": "medium", "deep": "high"}


def project_team_guidance(team_context: dict[str, Any] | None) -> dict[str, Any]:
    """Project portable team guidance into explicit Codex instruction fields."""
    normalized = normalize_team_context(team_context) or {}
    instructions = [
        "Treat selected Agent Caravan roles as subagent assignments when the runtime provides native delegation; do not collapse independent lanes into one perspective.",
        "Follow execution topology exactly: stages remain ordered; parallelize only lanes explicitly authorized by the plan; run them in the declared serial fallback order when parallel execution is unavailable.",
        "Run the smallest effective role set and preserve mandatory debates and review gates.",
        "Create structured handoffs for every role-to-role transfer.",
        "Pause for explicit human approval before actions listed by the active policy.",
        "Record decisions, evidence, approvals, artifacts, and unresolved conditions in the completion record.",
        "If native subagent delegation is unavailable, mark the run degraded or blocked unless the user explicitly authorizes sequential simulation.",
    ]
    if normalized.get("instructions"):
        instructions.append(normalized["instructions"])
    if normalized.get("working_agreements"):
        instructions.append("Team working agreements: " + normalized["working_agreements"])
    if normalized.get("preferred_roles"):
        instructions.append(
            "When choosing among permitted role lanes, prioritize these team-preferred roles: "
            + ", ".join(normalized["preferred_roles"])
            + "."
        )
    if normalized.get("role_guidance"):
        instructions.append("Team role participation guidance: " + normalized["role_guidance"])
    return {
        "instructions": instructions,
        "preferred_roles": normalized.get("preferred_roles", []),
        "role_guidance": normalized.get("role_guidance", ""),
    }


def project_knowledge_context(knowledge_context: dict[str, Any] | None) -> dict[str, Any]:
    """Keep shared knowledge layers common while retaining per-role guidance."""
    if not knowledge_context:
        return {"layers": []}
    layers = knowledge_context["layers"]
    return {"layers": layers}


def project_execution_brief(plan: dict[str, Any]) -> dict[str, Any]:
    """Project a portable execution plan into a Codex-facing brief."""
    try:
        validate_portable_execution_plan(plan)
    except ExecutionPlanError as error:
        raise CodexAdapterError(str(error)) from error
    team_guidance = project_team_guidance(plan["context"].get("team_context"))
    knowledge_context = project_knowledge_context(plan.get("knowledge_context"))
    instructions = list(team_guidance["instructions"])
    if knowledge_context["layers"]:
        instructions.append(
            "Apply knowledge_context layers to all assigned roles in their declared order, then apply "
            "context.team_context.knowledge_sources in their listed order. Apply each layer's role_guidance only to the matching role. "
            "Treat trusted_sources and documentation_references as references, not fetched content; follow the plan's knowledge_access policy before retrieval."
        )
    if any(assignment.get("documentation_references") for assignment in plan["role_assignments"]):
        instructions.append(
            "Role documentation_references are supplemental guidance associated with the listed role and source_chain. "
            "They do not override the machine-readable role contract; retrieve them only when permitted by knowledge_access."
        )
    return {
        "artifact_type": "codex-execution-brief",
        "adapter_id": "codex-desktop-agent-runtime",
        "plan_id": plan["id"],
        "task": plan["task"],
        "context": plan["context"],
        "role_lanes": [
            {
                "role_id": assignment["role_id"],
                **({"role_version": assignment["role_version"]}
                   if assignment.get("role_version") else {}),
                "source_chain": assignment.get("source_chain", [assignment["role_id"]]),
                "lane": assignment["participation"],
                **({"documentation_references": assignment["documentation_references"]}
                   if assignment.get("documentation_references") else {}),
            }
            for assignment in plan["role_assignments"]
        ],
        "reasoning_assignments": [
            {
                **assignment,
                "codex_reasoning_effort": CODEX_REASONING_EFFORT[assignment["level"]],
            }
            for assignment in plan.get("reasoning_assignments", [])
        ],
        "reasoning_policy": plan.get("reasoning_policy", {}),
        "stage_checkpoints": [
            {
                "stage_id": step["step_id"],
                "roles": step["role_ids"],
                "mode": step["mode"],
                "condition": step.get("condition"),
                "output": ", ".join(step.get("expected_outputs", [])) or None,
            }
            for step in plan["steps"]
        ],
        "execution_topology": plan.get("execution_topology"),
        "knowledge_context": knowledge_context,
        "execution_diagnostics": plan["task"].get("execution_diagnostics", False),
        "capability_requirements": plan.get("capability_requirements", {}),
        "tool_requirements": plan.get("tool_requirements", []),
        "evidence_requirements": plan.get("evidence_requirements", []),
        "instructions": instructions,
        "team_guidance": {
            "preferred_roles": team_guidance["preferred_roles"],
            "role_guidance": team_guidance["role_guidance"],
        },
        "handoff_contract": "resources/schemas/handoff.schema.json",
        "result_contract": "resources/schemas/execution-result.schema.json",
        "completion_record": "~/.agents/agent-caravan/sessions/<task-id>/completion.json",
        "persistence": "task-record-and-session-state",
        "approval_boundaries": plan["policy"].get("approval_requirements", []),
        "knowledge_access": plan["policy"].get("knowledge_access", {"external_sources": "enabled", "approved_sources": []}),
        "required_outputs": plan["required_outputs"],
    }


def project_resolved_execution_brief(resolved: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    """Build a portable plan and project it for Codex in one compatibility call."""
    try:
        plan = build_portable_execution_plan(resolved, task)
    except ExecutionPlanError as error:
        raise CodexAdapterError(str(error)) from error
    runtime = resolved.get("runtime")
    if not isinstance(runtime, dict) or runtime.get("adapter_id") != "codex-desktop-agent-runtime":
        raise CodexAdapterError("resolved runtime is not the Codex Desktop Agent Runtime")
    brief = project_execution_brief(plan)
    brief["runtime_profile_id"] = resolved["context"].get("runtime_profile_id")
    brief["degraded_capabilities"] = runtime.get("degraded_capabilities", [])
    degraded = runtime.get("degraded_capabilities", [])
    reasoning_degraded = any("reasoning_effort_control" in str(item) for item in degraded)
    brief["reasoning_control"] = {
        "status": "degraded" if reasoning_degraded else "available",
        "mapping": CODEX_REASONING_EFFORT,
    }
    return brief
