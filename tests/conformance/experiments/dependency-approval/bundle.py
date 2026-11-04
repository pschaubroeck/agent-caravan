"""Assemble experiment-local dependency-approval resolver inputs."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[3]
RUNTIME_PROFILE_ID = "opencode-dependency-approval-experiment"
CODEX_RUNTIME_PROFILE_ID = "codex-dependency-approval-experiment"
TEAM_INSTANCE_ID = "dependency-approval-experiment-team"
CATALOG_ID = "dependency-approval-experiment-catalog"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_opencode_bundle() -> dict[str, Any]:
    """Return a self-contained, experiment-local bundle without changing shared sources."""
    return _build_bundle("agentcaravan-opencode-runtime.json", RUNTIME_PROFILE_ID)


def build_codex_bundle() -> dict[str, Any]:
    """Return the same experiment contract with the actual Codex runtime artifacts."""
    return _build_bundle("agentcaravan-codex-runtime.json", CODEX_RUNTIME_PROFILE_ID)


def _build_bundle(runtime_filename: str, runtime_profile_id: str) -> dict[str, Any]:
    core = _read_json(REPOSITORY_ROOT / "resources/core/agentcaravan-core-team.json")
    runtime = _read_json(REPOSITORY_ROOT / "resources/runtime" / runtime_filename)
    execution_profile = _read_json(EXPERIMENT_DIR / "execution-profile.json")
    safety_policy = _read_json(
        REPOSITORY_ROOT
        / "resources/execution/policies/information-technology-core-team-safety-policy.json"
    )

    adapter = next(item for item in runtime["artifacts"] if item["artifact_type"] == "runtime-adapter")
    runtime_profile = copy.deepcopy(
        next(item for item in runtime["artifacts"] if item["artifact_type"] == "runtime-profile")
    )
    runtime_profile["id"] = runtime_profile_id
    runtime_profile["scope"] = "session"
    runtime_profile["execution_profile_ids"].append(execution_profile["id"])
    if runtime_profile_id == CODEX_RUNTIME_PROFILE_ID:
        runtime_profile["execution"]["observability"]["capture_content"] = True

    team_instance = {
        "artifact_type": "team-instance",
        "id": TEAM_INSTANCE_ID,
        "version": "1.0.0",
        "scope": "organization",
        "team_blueprint_id": "information-technology-core-team",
        "runtime_defaults": [adapter["id"]],
    }
    artifacts = [
        *copy.deepcopy(core["artifacts"]),
        copy.deepcopy(adapter),
        runtime_profile,
        execution_profile,
        safety_policy,
        team_instance,
    ]
    catalog = {
        "artifact_type": "organization-catalog",
        "id": CATALOG_ID,
        "version": "1.0.0",
        "scope": "organization",
        "published_artifacts": {
            artifact_type: [
                item["id"] for item in artifacts if item["artifact_type"] == artifact_type
            ]
            for artifact_type in (
                "role",
                "team-blueprint",
                "team-instance",
                "runtime-adapter",
                "runtime-profile",
                "execution-profile",
                "policy",
            )
        },
    }
    return {
        "context": {
            "organization_catalog_id": CATALOG_ID,
            "team_instance_id": TEAM_INSTANCE_ID,
            "runtime_adapter_id": adapter["id"],
            "runtime_profile_id": runtime_profile_id,
            "execution_profile_id": execution_profile["id"],
            "validation_profile_id": "local-experimental",
        },
        "artifacts": [catalog, *artifacts],
    }
