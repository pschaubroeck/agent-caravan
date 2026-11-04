"""Build the smallest useful organization and team starter configuration."""

from __future__ import annotations

import re
from typing import Any


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not slug:
        raise StarterConfigurationError("team name or team id must contain letters or numbers")
    return slug


STARTER_TEAM_BLUEPRINT_ID = "information-technology-core-team"
STARTER_EXECUTION_PROFILE_ID = "information-technology-core-team-basic-work"
STARTER_RUNTIME_ADAPTERS = {
    "codex": "codex-desktop-agent-runtime",
    "opencode": "opencode-agent-runtime",
    "kiro": "kiro-ide-agent-runtime",
}
STARTER_RUNTIME_PROFILES = {
    "codex": "codex-desktop-information-technology-core-team",
    "opencode": "opencode-information-technology-core-team",
    "kiro": "kiro-ide-information-technology-core-team",
}


class StarterConfigurationError(ValueError):
    """Raised when a starter team configuration is incomplete or invalid."""


def build_starter_team_instance(
    organization_id: str,
    team_name: str,
    ownership_boundary: str | None = None,
    *,
    runtime: str = "none",
    team_id: str | None = None,
    blueprint_id: str = STARTER_TEAM_BLUEPRINT_ID,
    domain_pack_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Return a runtime-neutral team instance from a small starter input.

    Runtime selection only populates the team instance's runtime default. It
    does not change the shared blueprint or add runtime-specific semantics to
    the organization artifact.
    """
    if not organization_id:
        raise StarterConfigurationError("organization_id is required")
    if not team_name.strip():
        raise StarterConfigurationError("team_name is required")
    if ownership_boundary is not None and not ownership_boundary.strip():
        raise StarterConfigurationError("ownership_boundary must not be empty")
    if not blueprint_id:
        raise StarterConfigurationError("blueprint_id is required")
    if runtime not in {"none", *STARTER_RUNTIME_ADAPTERS}:
        raise StarterConfigurationError(f"unsupported starter runtime: {runtime}")

    resolved_team_id = _slugify(team_id) if team_id else f"{organization_id}-{_slugify(team_name)}"
    artifact: dict[str, Any] = {
        "artifact_type": "team-instance",
        "id": resolved_team_id,
        "version": "1.0.0",
        "scope": "organization",
        "name": team_name.strip(),
        "organization_catalog_id": organization_id,
        "team_blueprint_id": blueprint_id,
        "role_overlays": [],
        "domain_packs": list(domain_pack_ids or []),
        "specialization_packs": [],
        "runtime_defaults": [],
        "execution_profile_id": STARTER_EXECUTION_PROFILE_ID,
    }
    if ownership_boundary is not None:
        artifact["ownership_boundary"] = {
            "summary": ownership_boundary.strip(),
            "owned_surfaces": [ownership_boundary.strip()],
        }
    if runtime in STARTER_RUNTIME_ADAPTERS:
        artifact["runtime_defaults"] = [STARTER_RUNTIME_ADAPTERS[runtime]]
    return artifact


__all__ = [
    "STARTER_EXECUTION_PROFILE_ID",
    "STARTER_RUNTIME_ADAPTERS",
    "STARTER_TEAM_BLUEPRINT_ID",
    "StarterConfigurationError",
    "build_starter_team_instance",
]
