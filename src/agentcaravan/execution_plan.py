"""Build runtime-neutral execution plans from resolved framework semantics."""

from __future__ import annotations

import copy
from typing import Any

try:
    from .knowledge_access import KnowledgeAccessError, normalize_knowledge_access
except ImportError:  # Support direct script execution during local development.
    from knowledge_access import KnowledgeAccessError, normalize_knowledge_access


class ExecutionPlanError(ValueError):
    """Raised when a resolved profile cannot produce a portable plan."""


TOPOLOGY_MODES = {
    "sequential",
    "parallel",
    "handoff",
    "loop",
    "coordinator",
    "coordinator-worker",
    "graph",
    "group-chat",
    "concurrent-fanout",
    "human-gated",
    "remote-agent",
}
TASK_OWNERSHIP_MODES = {
    "caller-retains",
    "receiver-takes-over",
    "code-controlled",
    "model-routed-within-boundary",
}
HANDOFF_SEMANTICS = {"explicit-ownership-transfer", "caller-retains", "mixed"}
SIDE_EFFECT_CLASSES = {"read-only", "local-write", "remote-write", "release", "production", "destructive"}
REASONING_LEVELS = {"focused", "standard", "deep"}
OBSERVABILITY_CAPABILITIES = {
    "execution_trace", "step_logging", "tool_call_audit", "handoff_traceability",
    "run_metadata", "reasoning_effort_telemetry",
}


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _normalize_documentation_references(value: Any, location: str) -> list[dict[str, str]]:
    """Validate and copy explicit documentation references without retrieving them."""
    if not isinstance(value, list):
        raise ExecutionPlanError(f"{location} must be a list")
    normalized = []
    allowed = {"uri", "media_type", "title", "purpose"}
    for reference in value:
        if not isinstance(reference, dict) or set(reference) - allowed:
            raise ExecutionPlanError(f"{location} entries must be documentation reference objects")
        if not isinstance(reference.get("uri"), str) or not reference["uri"].strip():
            raise ExecutionPlanError(f"{location} entries require a non-empty uri")
        if any(
            key in reference and (not isinstance(reference[key], str) or not reference[key].strip())
            for key in allowed - {"uri"}
        ):
            raise ExecutionPlanError(f"{location} optional fields must be non-empty strings")
        normalized.append(copy.deepcopy(reference))
    return normalized


def normalize_reasoning_policy(value: Any, assigned_roles: set[str], steps: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Normalize portable reasoning policy and resolve role/stage assignments."""
    policy = value or {}
    if not isinstance(policy, dict):
        raise ExecutionPlanError("reasoning_policy must be an object")
    default = policy.get("default", "standard")
    if default not in REASONING_LEVELS:
        raise ExecutionPlanError("reasoning_policy default must be focused, standard, or deep")

    role_defaults = policy.get("role_defaults", {})
    if not isinstance(role_defaults, dict):
        raise ExecutionPlanError("reasoning_policy role_defaults must be an object")
    for role_id, level in role_defaults.items():
        if role_id not in assigned_roles:
            raise ExecutionPlanError(f"reasoning_policy references unassigned role: {role_id}")
        if level not in REASONING_LEVELS:
            raise ExecutionPlanError(f"reasoning_policy has invalid level for role {role_id}")

    stage_roles = {step["step_id"]: set(step.get("role_ids", [])) for step in steps}
    stage_overrides = policy.get("stage_overrides", {})
    if not isinstance(stage_overrides, dict):
        raise ExecutionPlanError("reasoning_policy stage_overrides must be an object")
    for stage_id, overrides in stage_overrides.items():
        if stage_id not in stage_roles:
            raise ExecutionPlanError(f"reasoning_policy references unknown stage: {stage_id}")
        if not isinstance(overrides, dict):
            raise ExecutionPlanError(f"reasoning_policy stage override {stage_id} must be an object")
        for role_id, level in overrides.items():
            if role_id not in stage_roles[stage_id]:
                raise ExecutionPlanError(
                    f"reasoning_policy stage {stage_id} references role not assigned to the stage: {role_id}"
                )
            if level not in REASONING_LEVELS:
                raise ExecutionPlanError(f"reasoning_policy has invalid level for {stage_id}/{role_id}")

    normalized = {
        "default": default,
        "role_defaults": copy_profile_section(role_defaults),
        "stage_overrides": copy_profile_section(stage_overrides),
    }
    assignments = []
    for step in steps:
        for role_id in step.get("role_ids", []):
            if role_id not in assigned_roles:
                continue
            source = "default"
            level = default
            if role_id in role_defaults:
                source = "role-default"
                level = role_defaults[role_id]
            if role_id in stage_overrides.get(step["step_id"], {}):
                source = "stage-override"
                level = stage_overrides[step["step_id"]][role_id]
            assignments.append({"stage_id": step["step_id"], "role_id": role_id, "level": level, "source": source})
    return normalized, assignments


def merge_reasoning_policies(base: Any, override: Any) -> dict[str, Any]:
    """Merge task-local reasoning overrides over a profile policy."""
    base_policy = copy_profile_section(base or {})
    override_policy = override or {}
    if not isinstance(base_policy, dict) or not isinstance(override_policy, dict):
        raise ExecutionPlanError("reasoning policies must be objects")
    merged = {
        "default": base_policy.get("default", "standard"),
        "role_defaults": dict(base_policy.get("role_defaults", {})),
        "stage_overrides": {
            stage_id: dict(values)
            for stage_id, values in base_policy.get("stage_overrides", {}).items()
        },
    }
    if "default" in override_policy:
        merged["default"] = override_policy["default"]
    merged["role_defaults"].update(override_policy.get("role_defaults", {}))
    for stage_id, values in override_policy.get("stage_overrides", {}).items():
        merged["stage_overrides"].setdefault(stage_id, {}).update(values)
    return merged


def normalize_team_context(value: Any) -> dict[str, Any] | None:
    """Return the portable, runtime-neutral portion of team context."""
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ExecutionPlanError("portable team context must be an object")
    fields = {
        "mission": str,
        "work_surfaces": list,
        "knowledge_sources": list,
        "working_agreements": str,
        "instructions": str,
        "preferred_roles": list,
        "role_guidance": str,
    }
    normalized: dict[str, Any] = {}
    for field, expected_type in fields.items():
        if field not in value:
            continue
        field_value = value[field]
        if not isinstance(field_value, expected_type):
            raise ExecutionPlanError(f"portable team context {field} must be {expected_type.__name__}")
        if expected_type is list and any(not isinstance(item, str) for item in field_value):
            raise ExecutionPlanError(f"portable team context {field} must contain strings")
        normalized[field] = copy.deepcopy(field_value)
    unknown = set(value) - set(fields) - {"authoring_workspace", "documents"}
    if unknown:
        raise ExecutionPlanError(f"portable team context contains unsupported fields: {sorted(unknown)}")
    return normalized or None


def normalize_knowledge_context(resolved: dict[str, Any]) -> dict[str, Any] | None:
    """Project selected domain and team specialization packs into portable layers."""
    layers = []
    for field, artifact_type in (
        ("domain_packs", "domain-pack"),
        ("specialization_packs", "specialization-pack"),
    ):
        artifacts = resolved.get(field, [])
        if not isinstance(artifacts, list):
            raise ExecutionPlanError(f"resolved {field} must be a list")
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                raise ExecutionPlanError(f"resolved {field} entries must be objects")
            layer = {
                "artifact_type": artifact_type,
                "id": artifact.get("id"),
                "version": artifact.get("version"),
                "scope": artifact.get("scope"),
            }
            for field_name in (
                "owner_team_instance_id",
                "parent_domain_pack_id",
                "purpose",
                "domain_intent",
            ):
                if field_name in artifact:
                    layer[field_name] = copy.deepcopy(artifact[field_name])
            for field_name in ("knowledge_surface", "trusted_sources", "loading_guidance"):
                if field_name in artifact:
                    layer[field_name] = copy.deepcopy(artifact[field_name])
            if "documentation_references" in artifact:
                layer["documentation_references"] = _normalize_documentation_references(
                    artifact["documentation_references"], f"resolved {field} documentation_references"
                )
            if "role_guidance" in artifact:
                layer["role_guidance"] = copy.deepcopy(artifact["role_guidance"])
            if not all(
                isinstance(layer[field_name], str) and layer[field_name]
                for field_name in ("id", "version", "scope")
            ):
                raise ExecutionPlanError(f"resolved {field} entries require id, version, and scope")
            for field_name in ("owner_team_instance_id", "parent_domain_pack_id", "purpose", "domain_intent"):
                if field_name in layer and not isinstance(layer[field_name], str):
                    raise ExecutionPlanError(f"resolved {field} {field_name} must be a string")
            for field_name in ("knowledge_surface", "trusted_sources", "loading_guidance"):
                if field_name in layer and (
                    not isinstance(layer[field_name], list)
                    or any(not isinstance(item, str) for item in layer[field_name])
                ):
                    raise ExecutionPlanError(f"resolved {field} {field_name} must be a list of strings")
            role_guidance = layer.get("role_guidance")
            if role_guidance is not None and (
                not isinstance(role_guidance, dict)
                or any(
                    not isinstance(role_id, str) or not isinstance(guidance, str)
                    for role_id, guidance in role_guidance.items()
                )
            ):
                raise ExecutionPlanError(f"resolved {field} role_guidance must map role IDs to strings")
            layers.append(layer)
    if not layers:
        return None
    return {"layers": layers}


def validate_portable_execution_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Validate semantic invariants that JSON shape alone cannot express."""
    if not isinstance(plan, dict):
        raise ExecutionPlanError("portable execution plan must be an object")
    forbidden = {"runtime", "runtime_profile_id", "adapter_id"}
    leaked = forbidden.intersection(plan)
    if leaked:
        raise ExecutionPlanError(f"portable execution plan contains runtime-specific fields: {sorted(leaked)}")
    required = ("artifact_type", "id", "version", "scope", "task", "context", "role_assignments", "steps", "communication", "policy", "termination", "required_outputs")
    missing = [field for field in required if field not in plan]
    if missing:
        raise ExecutionPlanError(f"portable execution plan is missing fields: {', '.join(missing)}")
    if plan["artifact_type"] != "portable-execution-plan":
        raise ExecutionPlanError("invalid portable execution plan artifact type")
    if not plan["task"].get("task_id") or not plan["task"].get("objective"):
        raise ExecutionPlanError("portable plan task requires task_id and objective")
    references = plan["task"].get("references", [])
    if not isinstance(references, list):
        raise ExecutionPlanError("portable plan task references must be a list")
    for reference in references:
        if not isinstance(reference, dict) or any(
            not isinstance(reference.get(field), str) or not reference[field]
            for field in ("system_type", "reference_type", "identifier")
        ):
            raise ExecutionPlanError(
                "portable plan references require system_type, reference_type, and identifier"
            )
    context = plan["context"]
    if any(not context.get(field) for field in ("organization_catalog_id", "team_blueprint_id", "workflow_id")):
        raise ExecutionPlanError("portable plan context is incomplete")
    plan_team_context = context.get("team_context") or {}
    if not isinstance(plan_team_context, dict):
        raise ExecutionPlanError("portable team context must be an object")
    if {"authoring_workspace", "documents"}.intersection(plan_team_context):
        raise ExecutionPlanError("portable team context contains local authoring fields")
    normalize_team_context(plan_team_context)
    knowledge_context = plan.get("knowledge_context")
    if knowledge_context is not None:
        if not isinstance(knowledge_context, dict) or not isinstance(knowledge_context.get("layers"), list):
            raise ExecutionPlanError("portable knowledge_context requires a layers list")
        layer_keys = set()
        for layer in knowledge_context["layers"]:
            if not isinstance(layer, dict):
                raise ExecutionPlanError("portable knowledge_context layers must be objects")
            if layer.get("artifact_type") not in {"domain-pack", "specialization-pack"}:
                raise ExecutionPlanError("portable knowledge layer has an invalid artifact_type")
            if any(not isinstance(layer.get(field), str) or not layer[field] for field in ("id", "version", "scope")):
                raise ExecutionPlanError("portable knowledge layers require id, version, and scope")
            key = (layer["artifact_type"], layer["id"])
            if key in layer_keys:
                raise ExecutionPlanError(f"portable knowledge_context contains duplicate layer: {key[1]}")
            layer_keys.add(key)
            if layer["artifact_type"] == "specialization-pack":
                owner = layer.get("owner_team_instance_id")
                team_instance_id = context.get("team_instance_id")
                if owner and team_instance_id and owner != team_instance_id:
                    raise ExecutionPlanError(
                        f"portable knowledge layer {layer['id']} belongs to {owner}, not {team_instance_id}"
                    )
            allowed_layer_fields = {
                "artifact_type", "id", "version", "scope", "owner_team_instance_id",
                "parent_domain_pack_id", "purpose", "domain_intent", "knowledge_surface",
                "trusted_sources", "loading_guidance", "role_guidance",
                "documentation_references",
            }
            if set(layer) - allowed_layer_fields:
                raise ExecutionPlanError("portable knowledge layer contains unsupported fields")
            for field in ("owner_team_instance_id", "parent_domain_pack_id", "purpose", "domain_intent"):
                if field in layer and not isinstance(layer[field], str):
                    raise ExecutionPlanError(f"portable knowledge layer {field} must be a string")
            for field in ("knowledge_surface", "trusted_sources", "loading_guidance"):
                if field in layer and (
                    not isinstance(layer[field], list)
                    or any(not isinstance(item, str) for item in layer[field])
                ):
                    raise ExecutionPlanError(f"portable knowledge layer {field} must be a list of strings")
            if "documentation_references" in layer:
                _normalize_documentation_references(
                    layer["documentation_references"], "portable knowledge layer documentation_references"
                )
            role_guidance = layer.get("role_guidance")
            if role_guidance is not None and (
                not isinstance(role_guidance, dict)
                or any(
                    not isinstance(role_id, str) or not isinstance(guidance, str)
                    for role_id, guidance in role_guidance.items()
                )
            ):
                raise ExecutionPlanError("portable knowledge layer role_guidance must map role IDs to strings")

    assignments = plan["role_assignments"]
    assignment_ids = [item.get("role_id") for item in assignments]
    if not assignment_ids or any(not role_id for role_id in assignment_ids):
        raise ExecutionPlanError("portable plan role assignments require role IDs")
    if len(assignment_ids) != len(set(assignment_ids)):
        raise ExecutionPlanError("portable plan contains duplicate role assignments")
    valid_participation = {"entry", "primary", "supporting", "reviewer"}
    if any(item.get("participation") not in valid_participation for item in assignments):
        raise ExecutionPlanError("portable plan contains invalid role participation")
    for assignment in assignments:
        if "documentation_references" in assignment:
            _normalize_documentation_references(
                assignment["documentation_references"],
                f"portable role {assignment.get('role_id')} documentation_references",
            )

    steps = plan["steps"]
    step_ids = [step.get("step_id") for step in steps]
    if not steps or any(not step_id for step_id in step_ids) or len(step_ids) != len(set(step_ids)):
        raise ExecutionPlanError("portable plan steps require unique step IDs")
    valid_kinds = {"task", "message", "handoff", "artifact", "state-update", "tool-request", "approval-request", "result", "failure", "completion"}
    assigned = set(assignment_ids)
    for step in steps:
        if step.get("kind") not in valid_kinds or not step.get("role_ids"):
            raise ExecutionPlanError("portable plan step requires a valid kind and role IDs")
        missing_roles = set(step["role_ids"]) - assigned
        if missing_roles and not step.get("condition"):
            raise ExecutionPlanError(f"unassigned unconditional step roles: {sorted(missing_roles)}")

    communication = plan["communication"]
    if not isinstance(communication, dict):
        raise ExecutionPlanError("portable plan communication must be an object")
    handoff_semantics = communication.get("handoff_semantics")
    if handoff_semantics is not None and handoff_semantics not in HANDOFF_SEMANTICS:
        raise ExecutionPlanError("portable plan contains invalid handoff semantics")
    for handoff in communication.get("allowed_role_handoffs", []):
        if not handoff.get("from") or not handoff.get("to"):
            raise ExecutionPlanError("portable plan handoffs require from and to roles")
        if handoff.get("ownership") is not None and handoff["ownership"] not in HANDOFF_SEMANTICS:
            raise ExecutionPlanError("portable plan handoff contains invalid ownership semantics")

    topology = plan.get("execution_topology")
    if topology is not None:
        if not isinstance(topology, dict) or topology.get("mode") not in TOPOLOGY_MODES:
            raise ExecutionPlanError("portable plan contains invalid execution topology")
        if topology.get("task_ownership") is not None and topology["task_ownership"] not in TASK_OWNERSHIP_MODES:
            raise ExecutionPlanError("portable plan contains invalid task ownership")
        if topology.get("handoff_semantics") is not None and topology["handoff_semantics"] not in HANDOFF_SEMANTICS:
            raise ExecutionPlanError("portable plan contains invalid topology handoff semantics")
        lanes = topology.get("parallel_lanes", [])
        if not isinstance(lanes, list):
            raise ExecutionPlanError("execution topology parallel_lanes must be a list")
        lane_ids = [lane.get("id") for lane in lanes if isinstance(lane, dict)]
        if (
            len(lane_ids) != len(lanes)
            or any(not isinstance(lane_id, str) or not lane_id for lane_id in lane_ids)
            or len(lane_ids) != len(set(lane_ids))
        ):
            raise ExecutionPlanError("execution topology parallel lanes require unique IDs")
        stage_roles = {step["step_id"]: set(step["role_ids"]) for step in steps}
        stage_order = {step["step_id"]: index for index, step in enumerate(steps)}
        for lane in lanes:
            if (
                not isinstance(lane.get("purpose"), str)
                or not lane["purpose"]
                or not isinstance(lane.get("stage_id"), str)
                or lane["stage_id"] not in stage_roles
            ):
                raise ExecutionPlanError("parallel lanes require a known stage and purpose")
            role_ids = lane.get("role_ids")
            if (
                not isinstance(role_ids, list)
                or not role_ids
                or any(not isinstance(role_id, str) or not role_id for role_id in role_ids)
                or len(role_ids) != len(set(role_ids))
            ):
                raise ExecutionPlanError("parallel lanes require unique role IDs")
            if set(role_ids) - stage_roles[lane["stage_id"]]:
                raise ExecutionPlanError(f"parallel lane {lane['id']} references a role not assigned to its stage")
        fallback = topology.get("serial_fallback")
        if lanes:
            if not isinstance(fallback, dict) or fallback.get("mode") != "run-in-order":
                raise ExecutionPlanError("parallel lanes require an ordered serial fallback")
            if fallback.get("lane_ids") != lane_ids:
                raise ExecutionPlanError("serial fallback lane_ids must match parallel lane order")
        elif isinstance(fallback, dict):
            raise ExecutionPlanError("structured serial fallback requires declared parallel lanes")
        elif fallback is not None and not isinstance(fallback, str):
            raise ExecutionPlanError("legacy serial fallback must be a string")

        work_items = topology.get("work_items", [])
        if not isinstance(work_items, list):
            raise ExecutionPlanError("execution topology work_items must be a list")
        work_item_by_id = {}
        for item in work_items:
            if not isinstance(item, dict):
                raise ExecutionPlanError("execution topology work_items entries must be objects")
            item_id = item.get("id")
            stage_id = item.get("stage_id")
            role_id = item.get("role_id")
            if not all(isinstance(value, str) and value for value in (item_id, stage_id, role_id, item.get("purpose"))):
                raise ExecutionPlanError("work items require id, stage_id, role_id, and purpose")
            if item_id in work_item_by_id:
                raise ExecutionPlanError(f"duplicate work item ID: {item_id}")
            if stage_id not in stage_roles or role_id not in stage_roles[stage_id]:
                raise ExecutionPlanError(f"work item {item_id} role is not assigned to its stage")
            dependencies = item.get("depends_on", [])
            if (
                not isinstance(dependencies, list)
                or any(not isinstance(value, str) or not value for value in dependencies)
                or len(dependencies) != len(set(dependencies))
            ):
                raise ExecutionPlanError(f"work item {item_id} depends_on must contain unique IDs")
            condition = item.get("condition")
            if condition is not None and (not isinstance(condition, str) or not condition):
                raise ExecutionPlanError(f"work item {item_id} condition must be a non-empty string")
            lane_id = item.get("lane_id")
            if lane_id is not None:
                lane = next((entry for entry in lanes if entry["id"] == lane_id), None)
                if lane is None or lane["stage_id"] != stage_id or role_id not in lane["role_ids"]:
                    raise ExecutionPlanError(f"work item {item_id} references an unauthorized parallel lane")
            work_item_by_id[item_id] = item
        for item_id, item in work_item_by_id.items():
            for dependency_id in item.get("depends_on", []):
                dependency = work_item_by_id.get(dependency_id)
                if dependency is None:
                    raise ExecutionPlanError(f"work item {item_id} references unknown dependency {dependency_id}")
                if stage_order[dependency["stage_id"]] > stage_order[item["stage_id"]]:
                    raise ExecutionPlanError("work item dependencies cannot point to a later workflow stage")
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit_work_item(item_id: str) -> None:
            if item_id in visiting:
                raise ExecutionPlanError("execution topology work item dependencies must be acyclic")
            if item_id in visited:
                return
            visiting.add(item_id)
            for dependency_id in work_item_by_id[item_id].get("depends_on", []):
                visit_work_item(dependency_id)
            visiting.remove(item_id)
            visited.add(item_id)

        for item_id in work_item_by_id:
            visit_work_item(item_id)

    if "execution_diagnostics" in plan["task"] and not isinstance(plan["task"]["execution_diagnostics"], bool):
        raise ExecutionPlanError("task execution_diagnostics must be a boolean")

    tool_requirements = plan.get("tool_requirements", [])
    if not isinstance(tool_requirements, list):
        raise ExecutionPlanError("portable plan tool requirements must be a list")
    for requirement in tool_requirements:
        if not isinstance(requirement, dict) or not requirement.get("id"):
            raise ExecutionPlanError("portable plan tool requirements need an id")
        if requirement.get("side_effect_class") not in SIDE_EFFECT_CLASSES:
            raise ExecutionPlanError("portable plan tool requirement has an invalid side-effect class")
        if not isinstance(requirement.get("approval_required"), bool):
            raise ExecutionPlanError("portable plan tool requirement needs approval_required")
        if requirement["approval_required"] and not requirement.get("approval_lane"):
            raise ExecutionPlanError("approval-required tool requirement needs approval_lane")

    evidence_requirements = plan.get("evidence_requirements", [])
    if not isinstance(evidence_requirements, list):
        raise ExecutionPlanError("portable plan evidence requirements must be a list")
    for requirement in evidence_requirements:
        if not isinstance(requirement, dict) or not requirement.get("kind"):
            raise ExecutionPlanError("portable plan evidence requirements need a kind")
        if not isinstance(requirement.get("required"), bool):
            raise ExecutionPlanError("portable plan evidence requirement needs required")
    termination = plan.get("termination")
    if not isinstance(termination, dict):
        raise ExecutionPlanError("portable plan termination must be an object")
    success_criteria = termination.get("success_criteria", [])
    if not isinstance(success_criteria, list):
        raise ExecutionPlanError("portable plan success_criteria must be a list")
    criterion_ids = set()
    for criterion in success_criteria:
        if not isinstance(criterion, dict):
            raise ExecutionPlanError("portable plan success criteria must be objects")
        criterion_id = criterion.get("id")
        description = criterion.get("description")
        assessor_roles = criterion.get("assessor_roles")
        if not isinstance(criterion_id, str) or not criterion_id or not isinstance(description, str) or not description:
            raise ExecutionPlanError("portable plan success criteria require id and description")
        if criterion_id in criterion_ids:
            raise ExecutionPlanError(f"portable plan contains duplicate success criterion id: {criterion_id}")
        criterion_ids.add(criterion_id)
        if (
            not isinstance(assessor_roles, list)
            or not assessor_roles
            or any(not isinstance(role, str) or role not in assigned for role in assessor_roles)
            or len(assessor_roles) != len(set(assessor_roles))
        ):
            raise ExecutionPlanError(f"portable plan success criterion {criterion_id} has invalid assessor roles")
    policy = plan["policy"]
    if not isinstance(policy.get("policy_ids"), list) or not isinstance(policy.get("approval_requirements"), list):
        raise ExecutionPlanError("portable plan policy requires policy and approval lists")
    try:
        normalize_knowledge_access(policy.get("knowledge_access"))
    except KnowledgeAccessError as error:
        raise ExecutionPlanError(f"portable plan has invalid knowledge_access: {error}") from error
    if not isinstance(plan["required_outputs"], list) or not plan["required_outputs"]:
        raise ExecutionPlanError("portable plan requires completion outputs")
    reasoning_policy = plan.get("reasoning_policy", {})
    assignments = plan.get("reasoning_assignments", [])
    if not isinstance(assignments, list):
        raise ExecutionPlanError("portable plan reasoning_assignments must be a list")
    normalize_reasoning_policy(reasoning_policy, set(assignment_ids), plan["steps"])
    seen_assignments = set()
    for assignment in assignments:
        if not isinstance(assignment, dict) or not all(assignment.get(field) for field in ("stage_id", "role_id", "level", "source")):
            raise ExecutionPlanError("reasoning assignments require stage_id, role_id, level, and source")
        if assignment["level"] not in REASONING_LEVELS:
            raise ExecutionPlanError("reasoning assignment has an invalid level")
        key = (assignment["stage_id"], assignment["role_id"])
        if key in seen_assignments:
            raise ExecutionPlanError("portable plan contains duplicate reasoning assignments")
        seen_assignments.add(key)
    return plan


def build_portable_execution_plan(resolved: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    """Translate a resolved execution profile into runtime-neutral semantics."""
    if not isinstance(resolved, dict) or resolved.get("status") not in {"pass", "degraded"}:
        raise ExecutionPlanError("resolved bundle must have pass or degraded status")
    if not isinstance(task, dict) or not task.get("task_id") or not task.get("objective"):
        raise ExecutionPlanError("task must contain task_id and objective")

    profile = resolved.get("execution_profile")
    if not isinstance(profile, dict):
        raise ExecutionPlanError("an execution profile is required")
    context = resolved.get("context")
    if not isinstance(context, dict):
        raise ExecutionPlanError("resolved context is required")
    required_context = ("organization_catalog_id", "team_blueprint_id", "execution_profile_id")
    if any(not context.get(field) for field in required_context):
        raise ExecutionPlanError("resolved context is missing portable execution identity")

    activation = profile.get("activation_policy") or {}
    conditional_roles = activation.get("conditional_roles", {})
    if not isinstance(conditional_roles, dict):
        raise ExecutionPlanError("activation_policy conditional_roles must be an object")
    role_replacements = resolved.get("role_replacements", {})
    if not isinstance(role_replacements, dict) or any(
        not isinstance(source, str) or not source or not isinstance(target, str) or not target
        for source, target in role_replacements.items()
    ):
        raise ExecutionPlanError("resolved role_replacements must map role IDs to role IDs")
    def replace_role(role_id: str) -> str:
        return role_replacements.get(role_id, role_id)
    entry_roles = [replace_role(role_id) for role_id in profile.get("entry_roles", [])]
    role_ids = _unique(
        entry_roles
        + [replace_role(role_id) for role_id in activation.get("primary_roles", [])]
        + [replace_role(role_id) for role_id in activation.get("supporting_roles", [])]
        + [replace_role(role_id) for role_id in activation.get("mandatory_reviewers", [])]
        + [replace_role(role_id) for role_id in conditional_roles]
    )
    effective_roles = {item["id"]: item for item in resolved.get("effective_roles", [])}
    team_context = normalize_team_context(resolved.get("team_context")) or {}
    preferred_roles = [replace_role(role_id) for role_id in team_context.get("preferred_roles", [])]
    unknown_preferred_roles = set(preferred_roles) - set(effective_roles)
    if unknown_preferred_roles:
        raise ExecutionPlanError(
            f"team preferred roles are not part of the resolved team: {sorted(unknown_preferred_roles)}"
        )
    participation = {}
    for role_id in entry_roles:
        participation[role_id] = "entry"
    for role_id in (replace_role(item) for item in activation.get("primary_roles", [])):
        participation[role_id] = "primary"
    for role_id in (replace_role(item) for item in activation.get("supporting_roles", [])):
        participation.setdefault(role_id, "supporting")
    for role_id in (replace_role(item) for item in activation.get("mandatory_reviewers", [])):
        participation.setdefault(role_id, "reviewer")
    for role_id in (replace_role(item) for item in conditional_roles):
        participation.setdefault(role_id, "supporting")

    steps = []
    for stage in profile.get("stages", []):
        step = {
            "step_id": stage["id"],
            "kind": "task",
            "role_ids": [replace_role(role_id) for role_id in stage.get("roles", [])],
            "mode": stage.get("mode", "sequential"),
            "condition": stage.get("condition"),
            "expected_outputs": [stage["output"]] if stage.get("output") else [],
        }
        steps.append(step)

    merged_reasoning_policy = merge_reasoning_policies(profile.get("reasoning_policy"), task.get("reasoning_policy"))
    merged_reasoning_policy["role_defaults"] = {
        replace_role(role_id): level for role_id, level in merged_reasoning_policy.get("role_defaults", {}).items()
    }
    merged_reasoning_policy["stage_overrides"] = {
        stage_id: {replace_role(role_id): level for role_id, level in overrides.items()}
        for stage_id, overrides in merged_reasoning_policy.get("stage_overrides", {}).items()
    }
    reasoning_policy, reasoning_assignments = normalize_reasoning_policy(
        merged_reasoning_policy,
        set(role_ids),
        steps,
    )

    escalation = profile.get("escalation") or {}
    plan_context = {
        "organization_catalog_id": context["organization_catalog_id"],
        "team_blueprint_id": context["team_blueprint_id"],
        "workflow_id": context["execution_profile_id"],
    }
    if context.get("team_instance_id"):
        plan_context["team_instance_id"] = context["team_instance_id"]
    if team_context:
        plan_context["team_context"] = team_context
    knowledge_context = normalize_knowledge_context(resolved)

    runtime_support_levels = (resolved.get("runtime") or {}).get("capability_support_requirements", {})
    profile_support_levels = profile.get("capability_support_requirements", {})
    support_levels = {}
    if isinstance(runtime_support_levels, dict):
        support_levels.update(runtime_support_levels)
    if isinstance(profile_support_levels, dict):
        support_levels.update(profile_support_levels)
    support_order = {"unsupported": 0, "externalized": 1, "adapted": 2, "native": 3}
    for capability in support_levels:
        runtime_level = runtime_support_levels.get(capability) if isinstance(runtime_support_levels, dict) else None
        workflow_level = support_levels.get(capability)
        if runtime_level in support_order and workflow_level in support_order:
            support_levels[capability] = max((runtime_level, workflow_level), key=support_order.get)
    plan = {
        "artifact_type": "portable-execution-plan",
        "id": f"{task['task_id']}-execution-plan",
        "version": "1.0.0",
        "scope": "task",
        "task": {
            "task_id": task["task_id"],
            "objective": task["objective"],
            **{
                field: task[field]
                for field in ("references", "metadata", "extensions", "reasoning_policy", "execution_diagnostics")
                if field in task
            },
        },
        "context": plan_context,
        "role_assignments": [
            {
                "role_id": role_id,
                **(
                    {"role_version": effective_roles[role_id]["role"]["version"]}
                    if effective_roles.get(role_id, {}).get("role", {}).get("version")
                    else {}
                ),
                "participation": participation[role_id],
                "source_chain": effective_roles.get(role_id, {}).get("source_chain", [role_id]),
                **(
                    {"documentation_references": _normalize_documentation_references(
                        effective_roles[role_id]["role"]["documentation_references"],
                        f"resolved role {role_id} documentation_references",
                    )}
                    if effective_roles.get(role_id, {}).get("role", {}).get("documentation_references")
                    else {}
                ),
            }
            for role_id in role_ids
        ],
        "steps": steps,
        "communication": {
            "requires_structured_handoff": (profile.get("communication") or {}).get("requires_structured_handoff", True),
            "handoff_semantics": (profile.get("communication") or {}).get(
                "handoff_semantics", "explicit-ownership-transfer"
            ),
            "allowed_role_handoffs": [
                {
                    **handoff,
                    "from": replace_role(handoff["from"]),
                    "to": replace_role(handoff["to"]),
                }
                for handoff in (profile.get("communication") or {}).get("allowed_role_handoffs", [])
            ],
        },
        "policy": {
            "policy_ids": profile.get("policy_ids", []),
            "approval_requirements": escalation.get("human_approval_required_for", []),
            "knowledge_access": normalize_knowledge_access(resolved.get("knowledge_access")),
        },
        "capability_requirements": {
            "required": profile.get("required_capabilities", []),
            "preferred": profile.get("preferred_capabilities", []),
            "support_levels": copy_profile_section(support_levels),
        },
        "termination": copy_profile_section(profile.get("termination", {})),
        "required_outputs": profile.get("required_outputs", []),
        "reasoning_policy": reasoning_policy,
        "reasoning_assignments": reasoning_assignments,
    }
    if knowledge_context:
        plan["knowledge_context"] = knowledge_context
    if profile.get("topology") is not None:
        plan["execution_topology"] = copy_profile_section(profile["topology"])
        for lane in plan["execution_topology"].get("parallel_lanes", []):
            if isinstance(lane, dict) and isinstance(lane.get("role_ids"), list):
                lane["role_ids"] = [replace_role(role_id) for role_id in lane["role_ids"]]
        for item in plan["execution_topology"].get("work_items", []):
            if isinstance(item, dict) and isinstance(item.get("role_id"), str):
                item["role_id"] = replace_role(item["role_id"])
    if profile.get("tool_requirements") is not None:
        plan["tool_requirements"] = copy_profile_section(profile["tool_requirements"])
        for requirement in plan["tool_requirements"]:
            if isinstance(requirement, dict) and isinstance(requirement.get("approval_lane"), str):
                requirement["approval_lane"] = replace_role(requirement["approval_lane"])
    if profile.get("evidence_requirements") is not None:
        plan["evidence_requirements"] = copy_profile_section(profile["evidence_requirements"])
        for requirement in plan["evidence_requirements"]:
            if isinstance(requirement, dict) and isinstance(requirement.get("owner_role"), str):
                requirement["owner_role"] = replace_role(requirement["owner_role"])
    for criterion in plan["termination"].get("success_criteria", []):
        if isinstance(criterion, dict) and isinstance(criterion.get("assessor_roles"), list):
            criterion["assessor_roles"] = [replace_role(role_id) for role_id in criterion["assessor_roles"]]
    return validate_portable_execution_plan(plan)


def copy_profile_section(value: Any) -> Any:
    """Copy profile metadata without importing runtime-specific objects."""
    if isinstance(value, dict):
        return {key: copy_profile_section(item) for key, item in value.items()}
    if isinstance(value, list):
        return [copy_profile_section(item) for item in value]
    return value
