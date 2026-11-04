#!/usr/bin/env python3
"""Resolve a normalized AI organization framework artifact bundle."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

try:
    from .bundle_sources import BundleSource, LocalJsonBundleSource
    from .execution_plan import HANDOFF_SEMANTICS, OBSERVABILITY_CAPABILITIES, SIDE_EFFECT_CLASSES, TASK_OWNERSHIP_MODES, TOPOLOGY_MODES
    from .knowledge_access import KnowledgeAccessError, merge_knowledge_access, normalize_knowledge_access
    from .profile import load_profile
    from .team_configuration import load_team_context
except ImportError:  # Support direct script execution during local development.
    from bundle_sources import BundleSource, LocalJsonBundleSource
    from execution_plan import HANDOFF_SEMANTICS, OBSERVABILITY_CAPABILITIES, SIDE_EFFECT_CLASSES, TASK_OWNERSHIP_MODES, TOPOLOGY_MODES
    from knowledge_access import KnowledgeAccessError, merge_knowledge_access, normalize_knowledge_access
    from profile import load_profile
    from team_configuration import load_team_context


SCOPE_ORDER = {"shared": 0, "organization": 1, "team": 2, "local": 3, "session": 4}
ALLOWED_ARTIFACT_TYPES = {
    "organization-catalog",
    "role",
    "team-blueprint",
    "team-instance",
    "domain-pack",
    "specialization-pack",
    "overlay",
    "runtime-adapter",
    "runtime-profile",
    "execution-profile",
    "policy",
    "validation-profile",
}
SUPPORTED_CAPABILITY_STATUSES = {"native", "adapted", "externalized"}
DEFAULT_VALIDATION_POLICIES = {
    "local-experimental": {"allow_degraded": True},
    "team-shared": {"allow_degraded": True},
    "organization-shared": {"allow_degraded": False},
    "runtime-production": {"allow_degraded": False},
}


class ResolutionError(Exception):
    """Base error for invalid or unsafe resolution."""

    def __init__(self, message: str, *, diagnostics: dict[str, Any] | None = None):
        super().__init__(message)
        self.diagnostics = diagnostics or {}


class MissingArtifactError(ResolutionError):
    """Raised when a required artifact cannot be resolved."""


class AmbiguousOverlayError(ResolutionError):
    """Raised when overlays have no deterministic winner."""


def _artifact_key(artifact_type: str, artifact_id: str) -> tuple[str, str]:
    return artifact_type, artifact_id


def _replace_strings(value: Any, replacements: dict[str, str]) -> Any:
    if isinstance(value, str):
        return replacements.get(value, value)
    if isinstance(value, list):
        return [_replace_strings(item, replacements) for item in value]
    if isinstance(value, dict):
        return {
            replacements.get(key, key): _replace_strings(item, replacements)
            for key, item in value.items()
        }
    return value


def _merge_dict(base: dict[str, Any], changes: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in changes.items():
        if isinstance(result.get(key), dict) and isinstance(value, dict):
            result[key] = _merge_dict(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


class FrameworkResolver:
    def __init__(self, bundle: dict[str, Any]):
        self.bundle = bundle
        self.artifacts: dict[tuple[str, str], dict[str, Any]] = {}
        self._index_artifacts()

    def _index_artifacts(self) -> None:
        artifacts = self.bundle.get("artifacts")
        if not isinstance(artifacts, list):
            raise ResolutionError("bundle.artifacts must be a list")
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                raise ResolutionError("each artifact must be an object")
            artifact_type = artifact.get("artifact_type")
            artifact_id = artifact.get("id")
            if artifact_type not in ALLOWED_ARTIFACT_TYPES:
                raise ResolutionError(f"unsupported artifact_type: {artifact_type!r}")
            if not artifact_id or not isinstance(artifact_id, str):
                raise ResolutionError("every artifact requires a string id")
            if not artifact.get("version"):
                raise ResolutionError(f"{artifact_type}:{artifact_id} requires version")
            if not artifact.get("scope"):
                raise ResolutionError(f"{artifact_type}:{artifact_id} requires scope")
            key = _artifact_key(artifact_type, artifact_id)
            if key in self.artifacts:
                raise ResolutionError(f"duplicate artifact: {artifact_type}:{artifact_id}")
            self.artifacts[key] = artifact

    def artifact(self, artifact_type: str, artifact_id: str) -> dict[str, Any]:
        try:
            return self.artifacts[_artifact_key(artifact_type, artifact_id)]
        except KeyError as exc:
            raise MissingArtifactError(f"missing artifact: {artifact_type}:{artifact_id}") from exc

    def resolve(self, context: dict[str, str]) -> dict[str, Any]:
        profile_id = context.get("validation_profile_id", "organization-shared")
        profile_artifact = self.artifacts.get(("validation-profile", profile_id))
        policy = copy.deepcopy(DEFAULT_VALIDATION_POLICIES.get(profile_id, {}))
        if profile_artifact:
            self._assert_catalog_contains(
                self.artifact("organization-catalog", context["organization_catalog_id"]),
                profile_artifact,
            )
            policy.update(profile_artifact.get("policy", {}))
        if not policy and not profile_artifact:
            raise ResolutionError(f"unknown validation profile: {profile_id}")
        catalog = self.artifact("organization-catalog", context["organization_catalog_id"])
        team_id = context.get("team_instance_id")
        if not team_id:
            raise ResolutionError(
                "active profile has no selected team; run `agent-caravan init` for the team you want to use"
            )
        team_instance = self.artifact("team-instance", team_id)
        team_blueprint = self.artifact("team-blueprint", team_instance["team_blueprint_id"])
        self._assert_catalog_contains(catalog, team_instance)
        self._assert_catalog_contains(catalog, team_blueprint)

        base_roles = [self.artifact("role", role_id) for role_id in team_blueprint["core_roles"]]
        for role in base_roles:
            self._assert_catalog_contains(catalog, role)

        overlays = [
            self.artifact("overlay", overlay_id)
            for overlay_id in team_instance.get("role_overlays", [])
        ]
        for overlay in overlays:
            self._assert_catalog_contains(catalog, overlay)
        overlays = self._ordered_overlays(overlays)
        effective_template, role_replacements, overlay_details = self._apply_overlays(
            overlays, team_instance, team_blueprint, catalog
        )
        team_coverage = self._validate_team_coverage(
            effective_template,
            role_replacements,
            overlay_details,
            team_blueprint["core_roles"],
        )
        effective_roles = []
        for role_id in effective_template["core_roles"]:
            role = self.artifact("role", role_id)
            self._assert_catalog_contains(catalog, role)
            effective_roles.append(self._effective_role(role))

        domain_ids = team_instance.get("domain_packs", [])
        specialization_ids = team_instance.get("specialization_packs", [])
        domains = [self.artifact("domain-pack", domain_id) for domain_id in domain_ids]
        for domain in domains:
            self._assert_catalog_contains(catalog, domain)
        specializations = [
            self.artifact("specialization-pack", specialization_id)
            for specialization_id in specialization_ids
        ]
        for specialization in specializations:
            self._assert_catalog_contains(catalog, specialization)
            owner = specialization.get("owner_team_instance_id")
            if owner and owner != team_instance["id"]:
                raise ResolutionError(
                    f"specialization {specialization['id']} belongs to {owner}, "
                    f"not {team_instance['id']}"
                )

        adapter_id = context.get("runtime_adapter_id") or team_instance["runtime_defaults"][0]
        adapter = self.artifact("runtime-adapter", adapter_id)
        self._assert_catalog_contains(catalog, adapter)
        adapter_overrides = self.bundle.get("adapter_overrides", {})
        if not isinstance(adapter_overrides, dict):
            raise ResolutionError("bundle adapter_overrides must be an object")
        selected_adapter_override = adapter_overrides.get(adapter["id"], {})
        if not isinstance(selected_adapter_override, dict):
            raise ResolutionError(f"adapter override for {adapter['id']} must be an object")
        unsupported_adapter_overrides = set(selected_adapter_override) - {"repository_guidance"}
        if unsupported_adapter_overrides:
            raise ResolutionError(
                f"unsupported adapter override fields for {adapter['id']}: "
                f"{', '.join(sorted(unsupported_adapter_overrides))}"
            )
        runtime_profile_id = context.get("runtime_profile_id")
        if not runtime_profile_id:
            raise ResolutionError("runtime_profile_id is required for runtime resolution")
        runtime_profile = self.artifact("runtime-profile", runtime_profile_id)
        self._assert_catalog_contains(catalog, runtime_profile)
        if runtime_profile.get("target_adapter_id") != adapter["id"]:
            raise ResolutionError(
                f"runtime profile {runtime_profile['id']} targets {runtime_profile.get('target_adapter_id')}, "
                f"not adapter {adapter['id']}"
            )
        self._validate_runtime_execution_settings(runtime_profile)
        execution_profile_id = context.get("execution_profile_id") or team_instance.get(
            "execution_profile_id"
        )
        execution_profile = None
        if execution_profile_id:
            execution_profile = self.artifact("execution-profile", execution_profile_id)
            self._assert_catalog_contains(catalog, execution_profile)
            self._validate_execution_profile(
                execution_profile,
                effective_template,
                team_instance,
                runtime_profile,
                role_replacements,
            )
            supported_profiles = runtime_profile.get("execution_profile_ids")
            if supported_profiles is not None and execution_profile_id not in supported_profiles:
                raise ResolutionError(
                    f"runtime profile {runtime_profile['id']} does not support execution profile "
                    f"{execution_profile_id}"
                )
        policy_ids = list(context.get("policy_ids", []))
        if execution_profile:
            policy_ids.extend(execution_profile.get("policy_ids", []))
        if len(policy_ids) != len(set(policy_ids)):
            raise ResolutionError("execution profile contains duplicate policy references")
        policies = []
        for policy_id in policy_ids:
            policy_artifact = self.artifact("policy", policy_id)
            self._assert_catalog_contains(catalog, policy_artifact)
            self._validate_policy(policy_artifact, set(effective_template.get("core_roles", [])), role_replacements)
            policies.append(policy_artifact)
        try:
            effective_knowledge_access = merge_knowledge_access(policies)
        except KnowledgeAccessError as error:
            raise ResolutionError(str(error)) from error
        runtime_result = self._check_runtime(
            adapter,
            runtime_profile,
            execution_profile,
            selected_adapter_override,
        )
        if runtime_result["status"] == "degraded" and not policy["allow_degraded"]:
            raise ResolutionError(
                f"validation profile {profile_id} does not allow degraded runtime capabilities"
            )

        team_context = copy.deepcopy(team_instance.get("team_context", {}))
        authoring_workspace = team_context.get("authoring_workspace") if isinstance(team_context, dict) else None
        profile_root = self.bundle.get("profile_root")
        if authoring_workspace and profile_root:
            profile_path = Path(profile_root).expanduser().resolve()
            teams_root = profile_path / "caravans"
            if teams_root.is_symlink():
                raise ResolutionError("team workspace root must not be a symlink")
            expected_workspace = teams_root / team_instance["id"]
            workspace_reference = Path(authoring_workspace).expanduser()
            if workspace_reference.is_absolute():
                raise ResolutionError("team authoring workspace must be relative to the profile")
            workspace = (profile_path / workspace_reference).resolve()
            try:
                workspace.relative_to(teams_root.resolve())
            except ValueError as error:
                raise ResolutionError("team authoring workspace must remain under the profile teams directory") from error
            if workspace != expected_workspace.resolve():
                raise ResolutionError("team authoring workspace must match the active team")
            if not workspace.is_dir():
                raise ResolutionError(f"team authoring workspace does not exist: {workspace}")
            loaded_context = load_team_context(workspace, team_context)
            loaded_context["authoring_workspace"] = authoring_workspace
            team_context = loaded_context

        return {
            "resolution_version": "1.0.0",
            "status": runtime_result["status"],
            "validation_profile_id": profile_id,
            "context": {
                "organization_catalog_id": catalog["id"],
                "team_instance_id": team_instance["id"],
                "team_blueprint_id": team_blueprint["id"],
                "runtime_adapter_id": adapter["id"],
                "runtime_profile_id": runtime_profile["id"],
                **({"execution_profile_id": execution_profile["id"]} if execution_profile else {}),
            },
            "effective_roles": effective_roles,
            "effective_team": effective_template,
            "team_context": team_context,
            "domain_pack_ids": domain_ids,
            "specialization_pack_ids": specialization_ids,
            "domain_packs": copy.deepcopy(domains),
            "specialization_packs": copy.deepcopy(specializations),
            "applied_overlays": [overlay["id"] for overlay in overlays],
            "role_replacements": role_replacements,
            "overlay_details": overlay_details,
            "runtime": runtime_result,
            "validation_evidence": {
                "artifact_structure": {
                    "status": "basic-checks-passed",
                    "scope": "selected source JSON and resolver artifact identity checks; not exhaustive schema conformance",
                },
                "team_coverage": team_coverage,
                "runtime_capability_compatibility": {
                    "status": runtime_result["status"],
                    "basis": "declared adapter capabilities and selected profile requirements",
                    "runtime_adapter_id": adapter["id"],
                    "runtime_profile_id": runtime_profile["id"],
                },
                "runtime_verification": {
                    "status": "unverified",
                    "scope": "scenario-specific execution evidence is not attached to this resolved configuration",
                },
                "task_behavior_evaluation": {"status": "not-evaluated"},
            },
            "execution_profile": execution_profile,
            "policies": policies,
            "knowledge_access": effective_knowledge_access,
            "source_provenance": copy.deepcopy(self.bundle.get("source_provenance", [])),
            "provenance": {
                "base_team_blueprint": team_blueprint["id"],
                "overlay_order": [overlay["id"] for overlay in overlays],
                "knowledge_order": domain_ids + specialization_ids,
            },
        }

    def _validate_runtime_execution_settings(self, binding: dict[str, Any]) -> None:
        execution = binding.get("execution")
        if execution is None:
            return
        if not isinstance(execution, dict):
            raise ResolutionError("runtime profile execution settings must be an object")
        for field in ("model_profile", "instructions", "output_schema", "persistence"):
            if field in execution and not isinstance(execution[field], str):
                raise ResolutionError(f"runtime profile execution.{field} must be a string")
        for field in ("tools", "skills", "guardrails"):
            if field in execution and not isinstance(execution[field], list):
                raise ResolutionError(f"runtime profile execution.{field} must be a list")
        for field in ("workspace", "limits"):
            if field in execution and not isinstance(execution[field], dict):
                raise ResolutionError(f"runtime profile execution.{field} must be an object")
        self._observability_settings(binding)

    @staticmethod
    def _observability_settings(binding: dict[str, Any]) -> dict[str, Any]:
        """Resolve collection policy only; adapters own collection and export."""
        settings = (binding.get("execution") or {}).get("observability", {})
        if not isinstance(settings, dict):
            raise ResolutionError("runtime profile execution.observability must be an object")
        effective = {"enabled": False, "export": "local", "capture_content": False, **settings}
        for field in ("enabled", "capture_content"):
            if not isinstance(effective[field], bool):
                raise ResolutionError(f"execution.observability.{field} must be a boolean")
        if not isinstance(effective["export"], str) or effective["export"] not in {"local", "remote"}:
            raise ResolutionError("execution.observability.export must be local or remote")
        destination = effective.get("destination_ref")
        if "destination_ref" in effective and (not isinstance(destination, str) or not destination.strip()):
            raise ResolutionError("execution.observability.destination_ref must be a non-empty string")
        if effective["export"] == "remote" and not destination:
            raise ResolutionError("remote observability export requires destination_ref")
        return copy.deepcopy(effective)

    def _validate_execution_profile(
        self,
        profile: dict[str, Any],
        team: dict[str, Any],
        team_instance: dict[str, Any],
        binding: dict[str, Any],
        replacements: dict[str, str],
    ) -> None:
        target_team = profile.get("team_instance_id") or profile.get("team_blueprint_id")
        if target_team not in {team_instance["id"], team["id"]}:
            raise ResolutionError(
                f"execution profile {profile['id']} does not target team {team_instance['id']} "
                f"or template {team['id']}"
            )
        if profile.get("runtime_profile_id") and profile["runtime_profile_id"] != binding["id"]:
            raise ResolutionError(
                f"execution profile {profile['id']} targets runtime profile "
                f"{profile['runtime_profile_id']}, not {binding['id']}"
            )
        roles = set(team.get("core_roles", []))
        entry_roles = profile.get("entry_roles")
        if not isinstance(entry_roles, list) or not entry_roles:
            raise ResolutionError(f"execution profile {profile['id']} requires entry_roles")
        self._assert_profile_roles(profile, roles, entry_roles, "entry_roles", replacements)
        activation = profile.get("activation_policy")
        if not isinstance(activation, dict):
            raise ResolutionError(f"execution profile {profile['id']} requires activation_policy")
        for field in ("primary_roles", "supporting_roles", "mandatory_reviewers"):
            self._assert_profile_roles(profile, roles, activation.get(field, []), f"activation_policy.{field}", replacements)
        conditional_roles = activation.get("conditional_roles", {})
        if not isinstance(conditional_roles, dict):
            raise ResolutionError(f"execution profile {profile['id']} conditional_roles must be an object")
        self._assert_profile_roles(profile, roles, list(conditional_roles), "activation_policy.conditional_roles", replacements)

        topology = profile.get("topology")
        if not isinstance(topology, dict) or topology.get("mode") not in TOPOLOGY_MODES:
            raise ResolutionError(f"execution profile {profile['id']} has invalid topology")
        if topology.get("task_ownership") is not None and topology["task_ownership"] not in TASK_OWNERSHIP_MODES:
            raise ResolutionError(f"execution profile {profile['id']} has invalid task ownership")
        if topology.get("handoff_semantics") is not None and topology["handoff_semantics"] not in HANDOFF_SEMANTICS:
            raise ResolutionError(f"execution profile {profile['id']} has invalid topology handoff semantics")
        supported_modes = topology.get("supported_modes", [])
        if not isinstance(supported_modes, list) or any(mode not in TOPOLOGY_MODES for mode in supported_modes):
            raise ResolutionError(f"execution profile {profile['id']} has invalid supported topology modes")
        if topology.get("mode") in {"parallel", "concurrent-fanout"} and not topology.get("serial_fallback"):
            raise ResolutionError(f"execution profile {profile['id']} requires serial_fallback for parallel topology")

        stages = profile.get("stages")
        if not isinstance(stages, list) or not stages:
            raise ResolutionError(f"execution profile {profile['id']} requires stages")
        for stage in stages:
            if not isinstance(stage, dict) or not stage.get("id") or not stage.get("output"):
                raise ResolutionError(f"execution profile {profile['id']} has an incomplete stage")
            self._assert_profile_roles(profile, roles, stage.get("roles", []), f"stage:{stage['id']}.roles", replacements)

        stage_ids = {stage["id"] for stage in stages}
        communication = profile.get("communication", {})
        if not isinstance(communication, dict):
            raise ResolutionError(f"execution profile {profile['id']} communication must be an object")
        if communication.get("handoff_semantics") is not None and communication["handoff_semantics"] not in HANDOFF_SEMANTICS:
            raise ResolutionError(f"execution profile {profile['id']} has invalid handoff semantics")
        if communication.get("requires_structured_handoff"):
            for handoff in communication.get("allowed_role_handoffs", []):
                self._assert_profile_roles(profile, roles, [handoff.get("from"), handoff.get("to")], "communication", replacements)
                if handoff.get("ownership") is not None and handoff["ownership"] not in HANDOFF_SEMANTICS:
                    raise ResolutionError(f"execution profile {profile['id']} has invalid handoff ownership")

        tool_requirements = profile.get("tool_requirements", [])
        if not isinstance(tool_requirements, list):
            raise ResolutionError(f"execution profile {profile['id']} tool_requirements must be a list")
        tool_ids = set()
        for requirement in tool_requirements:
            if not isinstance(requirement, dict) or not requirement.get("id"):
                raise ResolutionError(f"execution profile {profile['id']} has an incomplete tool requirement")
            if requirement["id"] in tool_ids:
                raise ResolutionError(f"execution profile {profile['id']} contains duplicate tool requirement {requirement['id']}")
            tool_ids.add(requirement["id"])
            if requirement.get("side_effect_class") not in SIDE_EFFECT_CLASSES:
                raise ResolutionError(f"execution profile {profile['id']} has invalid tool side-effect class")
            if not isinstance(requirement.get("approval_required"), bool):
                raise ResolutionError(f"execution profile {profile['id']} tool requirement needs approval_required")
            approval_lane = requirement.get("approval_lane")
            if requirement["approval_required"] and not approval_lane:
                raise ResolutionError(f"execution profile {profile['id']} approval-required tool needs approval_lane")
            if approval_lane and approval_lane != "human":
                self._assert_profile_roles(profile, roles, [approval_lane], "tool_requirements", replacements)

        evidence_requirements = profile.get("evidence_requirements", [])
        if not isinstance(evidence_requirements, list):
            raise ResolutionError(f"execution profile {profile['id']} evidence_requirements must be a list")
        for requirement in evidence_requirements:
            if not isinstance(requirement, dict) or not requirement.get("kind") or not isinstance(requirement.get("required"), bool):
                raise ResolutionError(f"execution profile {profile['id']} has an incomplete evidence requirement")
            owner_role = requirement.get("owner_role")
            if owner_role:
                self._assert_profile_roles(profile, roles, [owner_role], "evidence_requirements", replacements)
            stage_id = requirement.get("stage_id")
            if stage_id is not None and stage_id not in stage_ids:
                raise ResolutionError(
                    f"execution profile {profile['id']} evidence requirement references missing stage {stage_id}"
                )
        termination = profile.get("termination")
        if not isinstance(termination, dict) or not termination.get("success_conditions") or not termination.get("failure_conditions"):
            raise ResolutionError(f"execution profile {profile['id']} requires termination conditions")
        escalation = profile.get("escalation")
        if not isinstance(escalation, dict) or not escalation:
            raise ResolutionError(f"execution profile {profile['id']} requires escalation")
        self._assert_profile_roles(profile, roles, [value for key, value in escalation.items() if key != "human_approval_required_for"], "escalation", replacements)

    @staticmethod
    def _assert_profile_roles(
        profile: dict[str, Any],
        roles: set[str],
        references: list[Any],
        field: str,
        replacements: dict[str, str],
    ) -> None:
        effective_references = [replacements.get(reference, reference) for reference in references]
        if not isinstance(references, list) or any(reference not in roles for reference in effective_references):
            missing = sorted({str(reference) for reference in effective_references if reference not in roles})
            raise ResolutionError(
                f"execution profile {profile['id']} {field} references missing roles: {missing}"
            )

    def _validate_policy(
        self,
        policy: dict[str, Any],
        roles: set[str],
        replacements: dict[str, str],
    ) -> None:
        policy_id = policy["id"]
        if policy.get("policy_type") not in {"guardrail", "approval", "quality", "termination"}:
            raise ResolutionError(f"policy {policy_id} has an invalid policy_type")
        for section in ("input_validation", "tool_authorization", "retry", "escalation", "termination"):
            if not isinstance(policy.get(section), dict):
                raise ResolutionError(f"policy {policy_id} requires object section {section}")
        input_validation = policy["input_validation"]
        if not isinstance(input_validation.get("required", []), list):
            raise ResolutionError(f"policy {policy_id} input_validation.required must be a list")
        tool_authorization = policy["tool_authorization"]
        if tool_authorization.get("default") not in {"bounded", "deny", "allow"}:
            raise ResolutionError(f"policy {policy_id} has invalid tool_authorization.default")
        approvals = policy.get("approval_requirements", [])
        if not isinstance(approvals, list):
            raise ResolutionError(f"policy {policy_id} approval_requirements must be a list")
        for approval in approvals:
            if not isinstance(approval, dict) or not approval.get("trigger") or not approval.get("approval_lane"):
                raise ResolutionError(f"policy {policy_id} has an incomplete approval requirement")
            if approval.get("on_missing") not in {"block", "escalate", "defer"}:
                raise ResolutionError(f"policy {policy_id} has invalid approval on_missing behavior")
            self._assert_policy_roles(policy, roles, [approval["approval_lane"]], replacements)
        retry = policy["retry"]
        if not isinstance(retry.get("default_max_attempts"), int) or retry["default_max_attempts"] < 0:
            raise ResolutionError(f"policy {policy_id} requires a non-negative default_max_attempts")
        if not isinstance(retry.get("denied_action_max_attempts"), int) or retry["denied_action_max_attempts"] < 0:
            raise ResolutionError(f"policy {policy_id} requires a non-negative denied_action_max_attempts")
        escalation = policy["escalation"]
        self._assert_policy_roles(policy, roles, list(escalation.values()), replacements)
        termination = policy["termination"]
        for condition in ("success_conditions", "failure_conditions", "unresolved_conditions"):
            if not isinstance(termination.get(condition), list) or not termination[condition]:
                raise ResolutionError(f"policy {policy_id} requires termination.{condition}")
        try:
            normalize_knowledge_access(policy.get("knowledge_access"))
        except KnowledgeAccessError as error:
            raise ResolutionError(f"policy {policy_id} has invalid knowledge_access: {error}") from error

    @staticmethod
    def _assert_policy_roles(
        policy: dict[str, Any], roles: set[str], references: list[Any], replacements: dict[str, str]
    ) -> None:
        effective_references = [replacements.get(reference, reference) for reference in references]
        invalid = [reference for reference in effective_references if reference != "human" and reference not in roles]
        if invalid:
            raise ResolutionError(
                f"policy {policy['id']} references missing approval/escalation roles: {sorted(set(invalid))}"
            )

    def _assert_catalog_contains(
        self, catalog: dict[str, Any], artifact: dict[str, Any]
    ) -> None:
        published = catalog.get("published_artifacts", {}).get(artifact["artifact_type"], [])
        if artifact["id"] not in published:
            raise ResolutionError(
                f"{artifact['artifact_type']}:{artifact['id']} is not published by "
                f"catalog {catalog['id']}"
            )

    def _effective_role(self, role: dict[str, Any]) -> dict[str, Any]:
        return self._effective_role_with_chain(role, [])

    def _effective_role_with_chain(
        self, role: dict[str, Any], chain: list[str]
    ) -> dict[str, Any]:
        if role["id"] in chain:
            raise ResolutionError(f"role inheritance cycle: {' -> '.join(chain + [role['id']])}")
        if "extends" not in role:
            return {"id": role["id"], "source_chain": [role["id"]], "role": role}
        parent = self.artifact("role", role["extends"])
        parent_effective = self._effective_role_with_chain(parent, chain + [role["id"]])
        return {
            "id": role["id"],
            "source_chain": parent_effective["source_chain"] + [role["id"]],
            "role": _merge_dict(parent_effective["role"], role),
        }

    def _ordered_overlays(self, overlays: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for overlay in overlays:
            operation = overlay.get("operation")
            if operation not in {"add", "extend", "replace", "suppress"}:
                raise ResolutionError(f"unsupported overlay operation: {operation!r}")
            if overlay.get("scope") not in SCOPE_ORDER:
                raise ResolutionError(f"invalid overlay scope: {overlay.get('scope')!r}")
        ordered = sorted(
            overlays,
            key=lambda item: (SCOPE_ORDER[item["scope"]], item.get("priority", 0), item["id"]),
        )
        seen: dict[tuple[str, str, str, str | None], dict[str, Any]] = {}
        for overlay in ordered:
            target = (
                overlay["scope"],
                overlay.get("target_artifact_type", ""),
                overlay.get("target_artifact_id", ""),
                overlay.get("target_role_id"),
            )
            if target in seen and overlay.get("priority", 0) == seen[target].get("priority", 0):
                raise AmbiguousOverlayError(
                    f"overlays {seen[target]['id']} and {overlay['id']} have equal priority "
                    f"for {target}"
                )
            seen[target] = overlay
        return ordered

    def _apply_overlays(
        self,
        overlays: list[dict[str, Any]],
        team_instance: dict[str, Any],
        team_blueprint: dict[str, Any],
        catalog: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, str], list[dict[str, Any]]]:
        effective_template = copy.deepcopy(team_blueprint)
        replacements: dict[str, str] = {}
        suppressed: set[str] = set()
        details: list[dict[str, Any]] = []
        replacement_targets = {
            overlay.get("target_role_id")
            for overlay in overlays
            if overlay.get("operation") == "replace" and overlay.get("target_role_id")
        }
        replacement_values = {
            overlay.get("replacement_role_id")
            for overlay in overlays
            if overlay.get("operation") == "replace" and overlay.get("replacement_role_id")
        }
        suppressed_targets = {
            overlay.get("suppressed_artifact_id") or overlay.get("target_role_id")
            for overlay in overlays
            if overlay.get("operation") == "suppress"
        }
        conflicts = (replacement_targets | replacement_values) & suppressed_targets
        if conflicts:
            raise ResolutionError(
                f"role overlays cannot both replace and suppress roles: {sorted(conflicts)}"
            )
        for overlay in overlays:
            if overlay.get("target_artifact_id") != team_instance["id"]:
                raise ResolutionError(
                    f"overlay {overlay['id']} targets {overlay.get('target_artifact_id')}, "
                    f"not team instance {team_instance['id']}"
                )
            operation = overlay["operation"]
            detail = {"id": overlay["id"], "operation": operation, "priority": overlay.get("priority", 0)}
            if operation == "replace":
                target_role = overlay.get("target_role_id")
                replacement_role = overlay.get("replacement_role_id")
                if target_role not in effective_template["core_roles"]:
                    raise ResolutionError(f"overlay targets role not in team blueprint: {target_role}")
                replacement = self.artifact("role", replacement_role)
                self._assert_catalog_contains(catalog, replacement)
                if overlay.get("replacement_artifact_type") != "role":
                    raise ResolutionError("role replacement must declare replacement_artifact_type=role")
                if replacement.get("extends") != target_role:
                    raise ResolutionError(
                        f"replacement {replacement_role} must extend target role {target_role}"
                    )
                replacements[target_role] = replacement_role
                detail["target"] = target_role
                detail["replacement"] = replacement_role
            elif operation == "add":
                artifact_type = overlay.get("added_artifact_type")
                artifact_id = overlay.get("added_artifact_id")
                collection = overlay.get("target_collection", "core_roles")
                added = self.artifact(artifact_type, artifact_id)
                self._assert_catalog_contains(catalog, added)
                if artifact_type != "role" or collection != "core_roles":
                    raise ResolutionError("prototype add supports roles into core_roles only")
                if artifact_id in effective_template[collection]:
                    raise ResolutionError(f"added artifact already exists: role:{artifact_id}")
                effective_template[collection].append(artifact_id)
                detail["added"] = f"{artifact_type}:{artifact_id}"
            elif operation == "extend":
                if overlay.get("target_artifact_type") != "team-instance":
                    raise ResolutionError("prototype extend supports team-instance targets only")
                changes = overlay.get("changes")
                if not isinstance(changes, dict):
                    raise ResolutionError(f"extend overlay {overlay['id']} requires changes")
                previous_core_roles = set(effective_template.get("core_roles", []))
                effective_template = _merge_dict(effective_template, changes)
                detail["changed_fields"] = sorted(changes)
                if "core_roles" in changes:
                    detail["added_roles"] = sorted(
                        set(effective_template.get("core_roles", [])) - previous_core_roles
                    )
            elif operation == "suppress":
                suppressed_role = overlay.get("suppressed_artifact_id") or overlay.get("target_role_id")
                if overlay.get("suppressed_artifact_type", "role") != "role":
                    raise ResolutionError("prototype suppress supports roles only")
                if suppressed_role not in effective_template["core_roles"]:
                    raise ResolutionError(f"suppressed role is not active: {suppressed_role}")
                suppressed.add(suppressed_role)
                detail["suppressed"] = suppressed_role
            details.append(detail)
        effective_template = _replace_strings(effective_template, replacements)
        effective_template["core_roles"] = [
            role_id for role_id in effective_template["core_roles"]
            if role_id not in suppressed
        ]
        effective_template["optional_roles"] = [
            role_id for role_id in effective_template.get("optional_roles", [])
            if role_id not in suppressed
        ]
        effective_template["stage_owners"] = [
            role_id for role_id in effective_template.get("stage_owners", [])
            if role_id not in suppressed
        ]
        mandatory_debates = set(effective_template.get("mandatory_debates", []))
        for debate, participants in effective_template.get("debate_participants", {}).items():
            if debate not in mandatory_debates:
                effective_template["debate_participants"][debate] = [
                    role_id for role_id in participants if role_id not in suppressed
                ]
        return effective_template, replacements, details

    def _validate_team_coverage(
        self,
        team: dict[str, Any],
        replacements: dict[str, str],
        overlay_details: list[dict[str, Any]],
        base_role_ids: list[str],
    ) -> dict[str, Any]:
        effective_role_ids = team.get("core_roles", [])
        roles = set(effective_role_ids)
        base_roles = set(base_role_ids)
        original_role_ids = {effective: original for original, effective in replacements.items()}
        suppressed_role_ids = {
            detail["suppressed"] for detail in overlay_details if detail.get("suppressed")
        }

        def original_role_id(role_id: str) -> str:
            return original_role_ids.get(role_id, role_id)

        def effective_role_id(role_id: str) -> str:
            return replacements.get(role_id, role_id)

        role_sources: dict[str, dict[str, str]] = {}
        for detail in overlay_details:
            added = detail.get("added")
            if isinstance(added, str) and added.startswith("role:"):
                role_id = added.removeprefix("role:")
                role_sources[role_id] = {"kind": "overlay-add", "artifact_id": detail["id"]}
            replacement = detail.get("replacement")
            if replacement:
                role_sources[replacement] = {
                    "kind": "overlay-replacement",
                    "artifact_id": detail["id"],
                    "replaces_role_id": detail["target"],
                }
            for role_id in detail.get("added_roles", []):
                mapped_role_id = replacements.get(role_id, role_id)
                if mapped_role_id in roles and mapped_role_id not in role_sources:
                    role_sources[mapped_role_id] = {
                        "kind": "overlay-extend",
                        "artifact_id": detail["id"],
                    }
        for role_id in effective_role_ids:
            if role_id not in role_sources:
                role_sources[role_id] = {
                    "kind": "team-blueprint" if role_id in base_roles else "effective-team",
                    "artifact_id": team["id"],
                }

        issues: list[dict[str, Any]] = []
        if len(roles) != len(effective_role_ids):
            issues.append({"kind": "duplicate-role", "role_ids": effective_role_ids})

        requirements: list[dict[str, Any]] = []
        for coverage_name, required_roles in team.get("coverage_requirements", {}).items():
            original_requirements = list(dict.fromkeys(original_role_id(role) for role in required_roles))
            candidates = list(dict.fromkeys(effective_role_id(role) for role in original_requirements))
            satisfied_by = [role_id for role_id in candidates if role_id in roles]
            status = "pass" if satisfied_by else "fail"
            requirement = {
                "name": coverage_name,
                "required_role_ids": original_requirements,
                "effective_candidate_role_ids": candidates,
                "satisfied_by": [
                    {"role_id": role_id, "source": role_sources.get(role_id)}
                    for role_id in satisfied_by
                ],
                "status": status,
            }
            requirements.append(requirement)
            if status == "fail":
                issues.append({"kind": "coverage-requirement", "name": coverage_name})
                issues.extend(
                    {
                        "kind": "suppressed-role-reference",
                        "path": f"coverage_requirements.{coverage_name}",
                        "role_id": role_id,
                    }
                    for role_id in original_requirements if role_id in suppressed_role_ids
                )

        debates: list[dict[str, Any]] = []
        for debate in team.get("mandatory_debates", []):
            original_participants = list(dict.fromkeys(
                original_role_id(role_id)
                for role_id in team.get("debate_participants", {}).get(debate, [])
            ))
            participants = [effective_role_id(role_id) for role_id in original_participants]
            missing = [role_id for role_id in participants if role_id not in roles]
            debates.append({
                "name": debate,
                "required_role_ids": original_participants,
                "effective_role_ids": participants,
                "satisfied_by": [
                    {"role_id": role_id, "source": role_sources.get(role_id)}
                    for role_id in participants if role_id in roles
                ],
                "missing_role_ids": missing,
                "status": "fail" if missing else "pass",
            })
            if missing:
                issues.append({"kind": "mandatory-debate", "name": debate, "missing_role_ids": missing})
                issues.extend(
                    {
                        "kind": "suppressed-role-reference",
                        "path": f"debate_participants.{debate}",
                        "role_id": role_id,
                    }
                    for role_id in original_participants if role_id in suppressed_role_ids
                )

        blocking_lanes = self._role_coverage_entries(
            team.get("blocking_lanes", []), roles, role_sources, original_role_id
        )
        for lane in blocking_lanes:
            if lane["status"] == "fail":
                issues.append({"kind": "blocking-lane", "role_id": lane["role_id"]})
                if lane["role_id"] in suppressed_role_ids:
                    issues.append({
                        "kind": "suppressed-role-reference",
                        "path": "blocking_lanes",
                        "role_id": lane["role_id"],
                    })

        documentation_ownership = [
            {
                "role_id": original_role_id(role_id),
                "effective_role_id": role_id,
                "documentation": list(sections) if isinstance(sections, list) else [sections],
                "source": role_sources.get(role_id),
                "status": "pass" if role_id in roles else "fail",
            }
            for role_id, sections in team.get("documentation_ownership", {}).items()
        ]
        for ownership in documentation_ownership:
            if ownership["status"] == "fail":
                issues.append({"kind": "documentation-ownership", "role_id": ownership["role_id"]})
                if ownership["role_id"] in suppressed_role_ids:
                    issues.append({
                        "kind": "suppressed-role-reference",
                        "path": f"documentation_ownership.{ownership['role_id']}",
                        "role_id": ownership["role_id"],
                    })

        report = {
            "status": "fail" if issues else "pass",
            "effective_role_sources": [
                {"role_id": role_id, "source": role_sources.get(role_id)}
                for role_id in effective_role_ids
            ],
            "requirements": requirements,
            "mandatory_debates": debates,
            "blocking_lanes": blocking_lanes,
            "documentation_ownership": documentation_ownership,
            "issues": issues,
        }
        if issues:
            summaries = []
            for issue in issues:
                if issue["kind"] == "duplicate-role":
                    summaries.append("effective team contains duplicate roles")
                elif issue["kind"] == "coverage-requirement":
                    summaries.append(f"coverage requirement {issue['name']} has no effective role")
                elif issue["kind"] == "mandatory-debate":
                    summaries.append(
                        f"mandatory debate {issue['name']} has missing roles: "
                        f"{sorted(issue['missing_role_ids'])}"
                    )
                elif issue["kind"] == "blocking-lane":
                    summaries.append(f"blocking lane has missing role: {issue['role_id']}")
                elif issue["kind"] == "documentation-ownership":
                    summaries.append(f"documentation ownership has missing role: {issue['role_id']}")
                elif issue["kind"] == "suppressed-role-reference":
                    summaries.append(
                        f"suppressed role {issue['role_id']} remains required at {issue['path']}"
                    )
            raise ResolutionError("; ".join(summaries), diagnostics={"team_coverage": report})
        return report

    @staticmethod
    def _role_coverage_entries(
        role_ids: list[str],
        roles: set[str],
        role_sources: dict[str, dict[str, str]],
        original_role_id: Any,
    ) -> list[dict[str, Any]]:
        return [
            {
                "role_id": original_role_id(role_id),
                "effective_role_id": role_id,
                "source": role_sources.get(role_id),
                "status": "pass" if role_id in roles else "fail",
            }
            for role_id in role_ids
        ]

    def _check_runtime(
        self, adapter: dict[str, Any], runtime_profile: dict[str, Any],
        execution_profile: dict[str, Any] | None = None,
        adapter_override: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        capabilities = adapter.get("capabilities", {})
        support_levels = runtime_profile.get("capability_support_requirements", {})
        if not isinstance(support_levels, dict):
            raise ResolutionError("runtime profile capability_support_requirements must be an object")
        support_levels = dict(support_levels)
        support_order = {"unsupported": 0, "externalized": 1, "adapted": 2, "native": 3}
        required_capabilities = list(runtime_profile.get("required_capabilities", []))
        if execution_profile:
            workflow_required = execution_profile.get("required_capabilities", [])
            if not isinstance(workflow_required, list) or any(
                not isinstance(capability, str) or not capability.strip() for capability in workflow_required
            ):
                raise ResolutionError("execution profile required_capabilities must be a list of non-empty strings")
            required_capabilities.extend(
                capability for capability in workflow_required
                if capability not in required_capabilities
            )
            workflow_support = execution_profile.get("capability_support_requirements", {})
            if not isinstance(workflow_support, dict):
                raise ResolutionError("execution profile capability_support_requirements must be an object")
            for capability, level in workflow_support.items():
                if not isinstance(level, str) or level not in support_order:
                    raise ResolutionError(f"invalid support level for capability {capability}: {level}")
                previous = support_levels.get(capability, "unsupported")
                if not isinstance(previous, str) or previous not in support_order:
                    raise ResolutionError(f"invalid support level for capability {capability}: {previous}")
                support_levels[capability] = max((previous, level), key=support_order.get)
        unsupported: list[str] = []
        degraded: list[str] = []
        observability_gaps: list[str] = []
        for capability in required_capabilities:
            status = capabilities.get(capability, "unsupported")
            if status == "unsupported":
                unsupported.append(capability)
            elif status not in SUPPORTED_CAPABILITY_STATUSES:
                raise ResolutionError(f"invalid status for capability {capability}: {status}")
            elif status != "native":
                degraded.append(f"{capability}:{status}")
        for capability, required_status in support_levels.items():
            if required_status not in support_order:
                raise ResolutionError(f"invalid support level for capability {capability}: {required_status}")
            actual_status = capabilities.get(capability, "unsupported")
            if actual_status not in SUPPORTED_CAPABILITY_STATUSES:
                raise ResolutionError(f"invalid status for capability {capability}: {actual_status}")
            if support_order[actual_status] < support_order[required_status]:
                unsupported.append(f"{capability} (requires {required_status}, has {actual_status})")
        for capability in runtime_profile.get("preferred_capabilities", []):
            status = capabilities.get(capability, "unsupported")
            if status == "unsupported":
                if capability in OBSERVABILITY_CAPABILITIES:
                    observability_gaps.append(f"preferred:{capability}:unsupported")
                else:
                    degraded.append(f"preferred:{capability}:unsupported")
        if unsupported:
            raise ResolutionError(
                f"runtime profile requires unsupported capabilities: {', '.join(unsupported)}"
            )
        repository_guidance = adapter.get("repository_guidance", {})
        if not isinstance(repository_guidance, dict):
            raise ResolutionError("runtime adapter repository_guidance must be an object")
        guidance_override = (adapter_override or {}).get("repository_guidance", {})
        if not isinstance(guidance_override, dict):
            raise ResolutionError("adapter override repository_guidance must be an object")
        unsupported_guidance_overrides = set(guidance_override) - {
            "native_files", "discovery", "reference_policy"
        }
        if unsupported_guidance_overrides:
            raise ResolutionError(
                "unsupported repository_guidance override fields: "
                f"{', '.join(sorted(unsupported_guidance_overrides))}"
            )
        repository_guidance = {**repository_guidance, **guidance_override}
        native_files = repository_guidance.get("native_files", ["AGENTS.md"])
        discovery = repository_guidance.get("discovery", "explicit")
        reference_policy = repository_guidance.get("reference_policy", "follow-explicit-links")
        if not isinstance(native_files, list) or not native_files or any(
            not isinstance(path, str) or not path.strip() for path in native_files
        ):
            raise ResolutionError(
                "runtime adapter repository_guidance native_files must be a non-empty list of strings"
            )
        if not isinstance(discovery, str) or discovery not in {"automatic", "explicit"}:
            raise ResolutionError("runtime adapter repository_guidance discovery must be automatic or explicit")
        if (
            not isinstance(reference_policy, str)
            or reference_policy not in {"follow-explicit-links", "entrypoint-only"}
        ):
            raise ResolutionError("runtime adapter repository_guidance reference_policy is invalid")
        repository_guidance = {
            "canonical_file": "AGENTS.md",
            "native_files": list(native_files),
            "discovery": discovery,
            "reference_policy": reference_policy,
        }
        return {
            "adapter_id": adapter["id"],
            "runtime_profile_id": runtime_profile["id"],
            "status": "degraded" if degraded else "pass",
            "degraded_capabilities": degraded,
            "capability_support_requirements": dict(support_levels),
            "observability": self._observability_settings(runtime_profile),
            **({"repository_guidance": repository_guidance} if repository_guidance else {}),
            **({"observability_gaps": observability_gaps} if observability_gaps else {}),
        }


def resolve_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    context = bundle.get("context")
    if not isinstance(context, dict):
        raise ResolutionError("bundle.context must be an object")
    return FrameworkResolver(bundle).resolve(context)


def resolve_source(source: BundleSource) -> dict[str, Any]:
    """Resolve a normalized bundle supplied by any BundleSource implementation."""
    return resolve_bundle(source.load())


def resolve_profile(root: str | Path) -> dict[str, Any]:
    """Resolve the active organization/team context from a local profile."""
    bundle = load_profile(root)
    bundle["profile_root"] = str(Path(root).expanduser())
    return resolve_bundle(bundle)


def main(argv: list[str]) -> int:
    if len(argv) == 3 and argv[1] == "--profile":
        result = resolve_profile(argv[2])
    elif len(argv) == 2:
        result = resolve_source(LocalJsonBundleSource(argv[1]))
    else:
        print(f"usage: {argv[0]} BUNDLE.json | {argv[0]} --profile PROFILE_ROOT", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
