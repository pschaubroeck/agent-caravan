#!/usr/bin/env python3
"""Run the complete interactive starter setup from a repository checkout."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANAGED_SOURCE_ID = "agentcaravan_repository"
MANAGED_SOURCE_RELATIVE_PATHS = (
    "resources/core/agentcaravan-core-team.json",
    "resources/runtime/agentcaravan-codex-runtime.json",
    "resources/runtime/agentcaravan-opencode-runtime.json",
    "resources/execution/policies",
    "resources/execution/workflows",
)
sys.path.insert(0, str(ROOT / "src"))


def _require_supported_python() -> None:
    """Fail clearly before importing modules that require Python 3.10 syntax."""
    if sys.version_info < (3, 10):
        found = ".".join(str(part) for part in sys.version_info[:3])
        raise SystemExit(
            f"Agent Caravan requires Python 3.10 or newer; found Python {found}."
        )


_require_supported_python()

from agentcaravan.cli import (  # noqa: E402
    DEFAULT_TEAM_NAME,
    DEFAULT_RUNTIME,
    _confirm_initialization,
    _check_runtime_selection,
    _prompt_with_default,
    init as package_init,
)
from agentcaravan.profile import find_organization_catalogs, load_config  # noqa: E402


def _refresh_repository_sources(config: dict, repository_root: Path) -> None:
    """Replace legacy checkout-managed paths while preserving user sources."""
    managed_sources = config.setdefault("managed_sources", {})
    previous = managed_sources.get(MANAGED_SOURCE_ID, {}).get("paths", [])
    managed_paths = [str(repository_root / relative) for relative in MANAGED_SOURCE_RELATIVE_PATHS]

    def is_managed(path: str | dict) -> bool:
        if not isinstance(path, str):
            return False
        if path in previous:
            return True
        candidate = Path(path)
        return candidate.is_absolute() and any(
            candidate.as_posix().endswith(f"/{relative}")
            for relative in MANAGED_SOURCE_RELATIVE_PATHS
        )

    config["sources"] = [source for source in config.get("sources", []) if not is_managed(source)]
    config["sources"].extend(managed_paths)
    managed_sources[MANAGED_SOURCE_ID] = {
        "root": str(repository_root),
        "paths": managed_paths,
    }


def _organization_selection(existing: list[tuple[dict, Path]]) -> tuple[str, dict | None, Path | None]:
    if not existing:
        return _prompt_with_default("Organization name", "My Organization"), None, None

    print("Existing organizations:")
    for index, (artifact, path) in enumerate(existing, 1):
        print(f"  {index}. {artifact['id']} ({path})")
    choice = input("Choose an organization number, (n)ew, or (c)ancel: ").strip().lower()
    if choice == "c":
        raise SystemExit("Initialization cancelled.")
    if choice == "n":
        return _prompt_with_default("Organization name", "My Organization"), None, None
    try:
        selected = int(choice)
        if selected < 1 or selected > len(existing):
            raise IndexError
        artifact, path = existing[selected - 1]
    except (ValueError, IndexError) as error:
        raise SystemExit("Invalid organization selection.") from error
    return artifact.get("name", artifact["id"]), artifact, path


def _existing_team(root: Path, organization: dict | None, organization_path: Path | None) -> dict | None:
    """Find the active or sole team instance for a selected organization."""
    if not organization or organization_path is None:
        return None
    config = load_config(root)
    active_context = config.get("active_context", {})
    active_team_id = active_context.get("team_instance_id")
    candidates: list[dict] = []
    for path in sorted(organization_path.parent.glob("*.json")):
        if path.name == "organization-catalog.json":
            continue
        try:
            artifact = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if (
            isinstance(artifact, dict)
            and artifact.get("artifact_type") == "team-instance"
            and artifact.get("organization_catalog_id") == organization.get("id")
        ):
            candidates.append(artifact)
    if active_team_id:
        active = next((team for team in candidates if team.get("id") == active_team_id), None)
        if active:
            return active
    return candidates[0] if len(candidates) == 1 else None


def _without_legacy_repository_sources(root: Path) -> dict:
    """Prepare source cleanup without changing the persisted profile."""
    config = load_config(root)
    managed = config.get("managed_sources", {}).pop(MANAGED_SOURCE_ID, {})
    previous = set(managed.get("paths", []))
    previous.update(
        source
        for source in config.get("sources", [])
        if isinstance(source, str)
        and any(source.endswith(f"/{relative}") for relative in MANAGED_SOURCE_RELATIVE_PATHS)
    )
    config["sources"] = [source for source in config.get("sources", []) if source not in previous]
    return config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.home() / ".agents" / "agent-caravan")
    parser.add_argument("--skill-root", type=Path, help="skill destination; defaults to the selected runtime's skill directory")
    parser.add_argument("--runtime", choices=("codex", "opencode"), default=DEFAULT_RUNTIME)
    args = parser.parse_args()

    root = args.root.expanduser()
    existing = find_organization_catalogs(root) if (root / "config.json").exists() else []
    organization_name, organization, organization_path = _organization_selection(existing)
    existing_team = _existing_team(root, organization, organization_path)
    team_default = existing_team.get("name", DEFAULT_TEAM_NAME) if existing_team else DEFAULT_TEAM_NAME
    team_name = _prompt_with_default("Team name", team_default)
    _check_runtime_selection(
        root,
        args.runtime,
        organization=organization_name,
        team_name=team_name,
        team_id=existing_team.get("id") if existing_team else None,
    )
    _confirm_initialization(
        root,
        organization_name,
        team_name,
        args.runtime,
        args.skill_root,
        existing_team=existing_team,
    )
    prepared_config = _without_legacy_repository_sources(root) if (root / "config.json").exists() else None

    package_args = argparse.Namespace(
        root=root,
        prepared_config=prepared_config,
        skill_root=args.skill_root,
        runtime=args.runtime,
        organization=organization_name,
        team=team_name,
        team_id=existing_team.get("id") if existing_team else None,
        ownership_boundary=None,
        blueprint="information-technology-core-team",
        domain_pack_id=[],
        command_prefix="PYTHONPATH=src python3 -m agentcaravan.cli",
    )
    return package_init(package_args)


if __name__ == "__main__":
    raise SystemExit(main())
