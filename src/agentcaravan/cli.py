"""Installed Agent Caravan bootstrap and profile commands."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import logging
import os
import re
import shlex
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .org_framework_layout import (
    DEFAULT_CONFIG,
    MANAGED_PACKAGE_SOURCE_ID,
    MANAGED_PACKAGE_SOURCE_RELATIVE_PATH,
    _bundled_root,
    bootstrap,
    install_packaged_sources,
    packaged_skill_path,
)
from .managed_skills import (
    all_skill_ids,
    default_skill_root,
    install_skills,
    skill_status,
)
from .bootstrap.starter import (
    STARTER_RUNTIME_ADAPTERS,
    STARTER_RUNTIME_PROFILES,
    StarterConfigurationError,
    build_starter_team_instance,
)
from .adapters.codex import DryRunCodexExecutor, run_codex_task
from .foundation import build_completion_record, build_execution_records, prepare_execution
from .handoff import TaskHandoffError, build_task_handoff
from .profile import (
    ProfileError,
    find_organization_catalogs,
    load_config,
    load_configured_source,
    load_profile,
    load_source,
    resolve_source_path,
)
from .resolve_framework import ResolutionError, resolve_bundle, resolve_profile
from .session_store import LocalJsonExecutionStore
from .session_validation import validate_session_directory
from .schema_validation import (
    validate_artifact,
    validate_framework_artifact,
    validate_framework_artifacts,
    validate_markdown_artifact_metadata,
    validate_schema_file,
)
from .telemetry import configure_logging, event_record, log_event
from .team_configuration import (
    TEAM_DOCUMENTS,
    build_team_context,
    load_team_context,
    portable_work_surfaces,
    team_workspace,
    update_team_documents,
)


DEFAULT_ROOT = Path.home() / ".agents" / "agent-caravan"
DEFAULT_ORGANIZATION_NAME = "My Organization"
DEFAULT_TEAM_NAME = "My Team"
DEFAULT_RUNTIME = "codex"


def _runtime_for_adapter(adapter_id: str | None) -> str | None:
    return next((runtime for runtime, adapter in STARTER_RUNTIME_ADAPTERS.items() if adapter == adapter_id), None)


def _runtime_name(runtime: str) -> str:
    return {"codex": "Codex", "opencode": "OpenCode", "kiro": "Kiro IDE"}.get(runtime, runtime)


def _configured_skill_root(config: dict, runtime: str) -> Path:
    legacy_root = config.get("managed_skill_root") if runtime == "codex" else None
    return Path(config.get("managed_skill_roots", {}).get(runtime) or legacy_root or default_skill_root(runtime)).expanduser()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not slug:
        raise ValueError("organization name must contain letters or numbers")
    return slug


def generated_task_id(objective: str) -> str:
    """Create a readable, filesystem-safe task ID when one is not supplied."""
    objective_slug = re.sub(r"[^a-z0-9]+", "-", objective.strip().lower()).strip("-")
    objective_slug = objective_slug[:56].strip("-") or "task"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S%f")
    suffix = hashlib.sha256(objective.encode("utf-8")).hexdigest()[:8]
    return f"task-{objective_slug}-{timestamp}-{suffix}"


def _write_config(root: Path, config: dict) -> None:
    _atomic_write_text(root / "config.json", json.dumps(config, indent=2) + "\n")


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary_path = handle.name
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path:
            Path(temporary_path).unlink(missing_ok=True)


def _ensure_run_slot_available(sessions_root: Path, task_id: str, run_id: str) -> None:
    run_path = sessions_root / task_id / "runs" / f"{run_id}.json"
    if run_path.exists():
        raise SystemExit(
            f"run evidence already exists: {run_path}. "
            "Use a new --task-id, increment --attempt, or provide a new --run-id."
        )


def _team_instance_path(root: Path, team_id: str) -> Path:
    """Find the configured source file for one team instance."""
    config = load_config(root)
    for configured_source in config.get("sources", []):
        source = resolve_source_path(root, configured_source)
        candidates = [source] if source.is_file() else sorted(source.rglob("*.json")) if source.is_dir() else []
        for candidate in candidates:
            try:
                artifact = json.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if artifact.get("artifact_type") == "team-instance" and artifact.get("id") == team_id:
                return candidate
    raise SystemExit(f"caravan is not writable in the active profile: {team_id}")


def _prompt_with_default(label: str, default: str, *, empty_hint: str = "press Enter to leave blank") -> str:
    display_default = " ".join(default.split())
    if display_default:
        prompt = f"{label} (default: {display_default}; press Enter to accept): "
    else:
        prompt = f"{label}; {empty_hint}: "
    value = input(prompt).strip()
    return value or default


def _prompt_yes_no(label: str, *, default: bool) -> bool:
    """Read a case-insensitive yes/no response with an explicit default."""
    default_value = "y" if default else "n"
    while True:
        value = input(f"{label} (y/n; default: {default_value}): ").strip().casefold()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Please enter y or n.")


def _confirm_initialization(
    root: Path,
    organization: str,
    team: str,
    runtime: str,
    skill_root: Path | None,
    *,
    existing_team: dict | None = None,
) -> None:
    action = "use existing configuration for" if existing_team else "create"
    blueprint = existing_team.get("team_blueprint_id", "information-technology-core-team") if existing_team else "information-technology-core-team"
    blueprint_name = "Information Technology Core Team" if blueprint == "information-technology-core-team" else blueprint
    runtime_name = _runtime_name(runtime)
    if existing_team:
        runtime_defaults = existing_team.get("runtime_defaults", [])
        if runtime_defaults:
            runtime_name = _runtime_name(_runtime_for_adapter(runtime_defaults[0]) or runtime_defaults[0])
    knowledge = "None"
    if existing_team and (existing_team.get("domain_packs") or existing_team.get("specialization_packs")):
        knowledge = "Existing caravan configuration"
    ownership = "Not configured"
    if existing_team and existing_team.get("ownership_boundary"):
        ownership = "Existing caravan configuration"

    print(f"\nI’m going to {action}:")
    print(f"  Organization: {organization}")
    print(f"  Caravan: {team}")
    print(f"  Caravan template: {blueprint_name}")
    print(f"  Runtime: {runtime_name}")
    print(f"  Knowledge: {knowledge}")
    print(f"  Ownership scope: {ownership}")
    print(f"\nProfile location: {root.expanduser()}")
    if runtime in STARTER_RUNTIME_ADAPTERS:
        config = load_config(root) if (root / "config.json").is_file() else {}
        destination = skill_root or _configured_skill_root(config, runtime)
        print(f"{_runtime_name(runtime)} skills: {destination.expanduser()}")
    if not _prompt_yes_no("\nContinue?", default=True):
        raise SystemExit("Initialization cancelled.")


def _print_setup_summary(
    root: Path,
    organization: str,
    team: str,
    resolved: dict,
    *,
    command_prefix: str = "agent-caravan",
) -> None:
    status = resolved.get("status")
    status_label = "Valid" if status == "pass" else status.capitalize()
    print("\nSetup complete.")
    print(f"  Organization: {organization}")
    print(f"  Caravan: {team}")
    print("  Caravan template: Information Technology Core Team")
    runtime = _runtime_for_adapter(resolved["context"].get("runtime_adapter_id"))
    print(f"  Runtime: {_runtime_name(runtime or 'none')}")
    print(f"  Status: {status_label}")

    root_argument = ""
    if root.expanduser() != DEFAULT_ROOT.expanduser():
        root_argument = f" --root {shlex.quote(str(root.expanduser()))}"
    print("\nNext step:")
    print(f"  {command_prefix} configure{root_argument}")
    if runtime == "codex":
        print(
            f"  {command_prefix} run"
            f"{root_argument}"
            " --dry-run"
            ' --objective "Validate the configured team workflow"'
        )
    else:
        print(f"  {command_prefix} status{root_argument}")
        print(f"  {command_prefix} resolve{root_argument}")
        print(f"  {command_prefix} validate")
        print("  CLI run --dry-run is currently Codex-only.")
    print(f"  Then use the agent-caravan-{runtime}-orchestrator skill for implementation work.")


def _print_team_artifact_summary(root: Path, organization_id: str, team_id: str) -> None:
    """Show the durable artifacts created by starter setup and configure."""
    organization_root = root.expanduser() / "sources" / organization_id
    team_workspace_path = root.expanduser() / "caravans" / team_id
    documents = ", ".join(filename for filename, _ in TEAM_DOCUMENTS)
    print("\nCaravan artifacts:")
    print(f"  Organization catalog: {organization_root / 'organization-catalog.json'}")
    print(f"  Caravan: {organization_root / f'{team_id}.json'}")
    print(f"  Caravan workspace: {team_workspace_path} (created by configure)")
    print(f"  Caravan documents: {documents} (created by configure)")
    print(f"  Active caravan ID: {team_id}")


def _status_report(root: Path) -> dict[str, object]:
    report: dict[str, object] = {
        "status": "incomplete",
        "profile_root": str(root),
        "organization_id": None,
        "organization_name": None,
        "team_id": None,
        "team_name": None,
        "blueprint_id": None,
        "runtime_profile_id": None,
        "runtime_adapter_id": None,
        "repository_guidance": None,
        "configuration": {
            "status": "not-configured",
            "workspace": None,
            "work_surfaces": [],
            "knowledge_sources": [],
        },
        "skills": skill_status(),
        "sessions": {
            "status": "missing" if not (root / "sessions").is_dir() else "ready",
            "root": str(root / "sessions"),
        },
        "issues": [],
        "next_action": "agent-caravan init",
    }
    issues = report["issues"]
    context: dict = {}

    if not (root / "config.json").is_file():
        issues.append(f"profile config does not exist: {root / 'config.json'}")
        return report

    try:
        config = load_config(root)
        context = config.get("active_context", {})
        runtime = _runtime_for_adapter(context.get("runtime_adapter_id"))
        if runtime:
            skill_root = _configured_skill_root(config, runtime)
            report["skills"] = skill_status(skill_root, runtime=runtime)
        else:
            report["skills"] = {"status": "not-applicable", "runtime": None, "root": None, "missing": [], "modified": []}
        report["organization_id"] = context.get("organization_catalog_id")
        report["team_id"] = context.get("team_instance_id")
        report["runtime_profile_id"] = context.get("runtime_profile_id")
        profile = load_profile(root)
        artifacts = {
            (artifact.get("artifact_type"), artifact.get("id")): artifact
            for artifact in profile.get("artifacts", [])
        }
        organization = artifacts.get(("organization-catalog", report["organization_id"]))
        team = artifacts.get(("team-instance", report["team_id"]))
        if organization:
            report["organization_name"] = organization.get("name")
        if team:
            report["team_name"] = team.get("name")
            report["blueprint_id"] = team.get("team_blueprint_id")
            team_context = team.get("team_context", {})
            if isinstance(team_context, dict) and team_context:
                report["configuration"] = {
                    "status": "configured",
                    "workspace": team_context.get("authoring_workspace"),
                    "work_surfaces": team_context.get("work_surfaces", []),
                    "knowledge_sources": team_context.get("knowledge_sources", []),
                }
        resolved = resolve_profile(root)
        runtime = _runtime_for_adapter(resolved["runtime"]["adapter_id"])
        if runtime:
            report["skills"] = skill_status(_configured_skill_root(config, runtime), runtime=runtime)
        resolved_team_context = resolved.get("team_context", {})
        if isinstance(resolved_team_context, dict) and resolved_team_context:
            report["configuration"] = {
                "status": "configured",
                "workspace": resolved_team_context.get("authoring_workspace"),
                "work_surfaces": resolved_team_context.get("work_surfaces", []),
                "knowledge_sources": resolved_team_context.get("knowledge_sources", []),
            }
        report["status"] = resolved.get("status", "invalid")
        report["blueprint_id"] = resolved["context"].get("team_blueprint_id")
        report["runtime_profile_id"] = resolved["context"].get("runtime_profile_id")
        report["runtime_adapter_id"] = resolved["runtime"].get("adapter_id")
        report["repository_guidance"] = resolved["runtime"].get("repository_guidance")
        root_argument = "" if root == DEFAULT_ROOT else f" --root {shlex.quote(str(root))}"
        if runtime == "codex":
            report["next_action"] = (
                f'agent-caravan run{root_argument} --dry-run '
                '--objective "Validate the configured team workflow"'
            )
        elif runtime:
            report["next_action"] = f"Use the agent-caravan-{runtime}-orchestrator skill."
        else:
            report["next_action"] = f"agent-caravan resolve{root_argument}"
        if report["status"] == "degraded":
            issues.append("active profile resolved with degraded runtime capabilities")
    except (ProfileError, ResolutionError, OSError, ValueError, KeyError) as error:
        report["status"] = "invalid"
        issues.append(str(error))
        report["next_action"] = (
            "agent-caravan init"
            if not context.get("team_instance_id")
            else "agent-caravan resolve"
        )

    if report["skills"]["status"] not in {"installed", "not-applicable"}:
        issues.append(f"managed {_runtime_name(report['skills']['runtime'])} skills are missing or modified")
    return report


def _render_status(report: dict[str, object]) -> None:
    print("Agent Caravan status\n")
    print(f"Profile: {report['profile_root']}")
    if report["organization_name"] or report["organization_id"]:
        print(f"Organization: {report['organization_name'] or report['organization_id']}")
    if report["team_name"] or report["team_id"]:
        print(f"Caravan: {report['team_name'] or report['team_id']}")
    if report["blueprint_id"]:
        print(f"Caravan template: {report['blueprint_id']}")
    if report["runtime_profile_id"]:
        print(f"Runtime mapping: {report['runtime_profile_id']}")
    if report["runtime_adapter_id"]:
        print(f"Runtime integration: {report['runtime_adapter_id']}")
    repository_guidance = report["repository_guidance"]
    if repository_guidance:
        print(f"Repository guidance files: {', '.join(repository_guidance['native_files'])}")
        print(f"  Discovery: {repository_guidance['discovery']}")
        print(f"  Reference policy: {repository_guidance['reference_policy']}")
    print(f"Profile status: {str(report['status']).capitalize()}")
    print(f"Caravan configuration: {report['configuration']['status'].capitalize()}")
    print(f"Managed skills: {report['skills']['status'].capitalize()}")
    if report["skills"]["root"]:
        print(f"Skill destination: {report['skills']['root']}")
    print(f"Session evidence: {report['sessions']['status'].capitalize()}")
    issues = report["issues"]
    if issues:
        print("\nIssues:")
        for issue in issues:
            print(f"  - {issue}")
    print(f"\nNext step:\n  {report['next_action']}")


def _check_runtime_selection(
    root: Path,
    runtime: str,
    *,
    organization: str | None = None,
    team_name: str | None = None,
    team_id: str | None = None,
) -> None:
    """Reject changing an existing team's runtime before bootstrap writes."""
    if runtime not in STARTER_RUNTIME_ADAPTERS or not (root / "config.json").is_file():
        return
    config = load_config(root)
    context = config.get("active_context", {})
    organization_id = slugify(organization) if organization else (
        None if team_name or team_id else context.get("organization_catalog_id")
    )
    artifacts = []
    for configured_source in config.get("sources", []):
        # Checkout initialization has historically tolerated stale repository
        # resource paths so it can replace them with resources from this clone.
        if isinstance(configured_source, str) and not resolve_source_path(root, configured_source).exists():
            continue
        source_artifacts, _ = load_configured_source(root, configured_source)
        artifacts.extend(source_artifacts)
    for artifact in artifacts:
        if artifact.get("artifact_type") != "team-instance":
            continue
        if organization_id and artifact.get("organization_catalog_id") not in {None, organization_id}:
            continue
        if team_id:
            selected = artifact.get("id") == team_id
        elif team_name:
            selected = artifact.get("name", "").casefold() == team_name.casefold()
        else:
            selected = artifact.get("id") == context.get("team_instance_id")
        defaults = artifact.get("runtime_defaults", [])
        if selected and defaults and defaults[0] != STARTER_RUNTIME_ADAPTERS[runtime]:
            existing_runtime = _runtime_for_adapter(defaults[0]) or defaults[0]
            raise SystemExit(
                f"Caravan {artifact['id']} uses {existing_runtime}, not {runtime}. "
                f"Rerun with --runtime {existing_runtime}, or use --organization/--team "
                "to select or create a separate caravan for the selected runtime."
            )


def _default_catalog(org_id: str, name: str) -> dict:
    return {
        "artifact_type": "organization-catalog",
        "id": org_id,
        "version": "1.0.0",
        "scope": "organization",
        "name": name,
        "description": f"Agent Caravan organization catalog for {name}.",
        "published_artifacts": {
            "role": ["program-manager", "product-owner", "tech-owner", "engineer", "quality-engineer", "software-architect", "release-manager"],
            "team-blueprint": ["information-technology-core-team"],
            "team-instance": [],
            "execution-profile": [
                "information-technology-core-team-basic-work",
                "information-technology-core-team-feature-delivery",
            ],
            "domain-pack": [], "specialization-pack": [], "overlay": [],
            "runtime-adapter": list(STARTER_RUNTIME_ADAPTERS.values()),
            "runtime-profile": list(STARTER_RUNTIME_PROFILES.values()),
            "policy": ["information-technology-core-team-safety-policy"],
        },
    }


def _merge_catalog_defaults(catalog: dict, defaults: dict) -> dict:
    merged = dict(catalog)
    published = dict(merged.get("published_artifacts", {}))
    for artifact_type, artifact_ids in defaults["published_artifacts"].items():
        current = list(published.get(artifact_type, []))
        published[artifact_type] = current + [artifact_id for artifact_id in artifact_ids if artifact_id not in current]
    merged["published_artifacts"] = published
    return merged


def _create_organization(
    root: Path,
    config: dict,
    existing: list[tuple[dict, Path]],
    organization_name: str | None = None,
    *,
    prepared: dict[Path, dict] | None = None,
) -> str:
    replace_existing = False
    if organization_name:
        name = organization_name.strip()
        org_id = slugify(name)
        match = next(((artifact, path) for artifact, path in existing if artifact["id"] == org_id), None)
        if match:
            artifact, output = match
            try:
                output.relative_to(root / "sources")
            except ValueError as exc:
                raise SystemExit(
                    "refusing to modify an organization catalog outside the local profile; "
                    "select it interactively or configure a local caravan source"
                ) from exc
            name = artifact.get("name", name)
            print(f"Using existing organization catalog: {output}")
        else:
            output = root / "sources" / org_id / "organization-catalog.json"
    elif existing:
        print("Existing organizations:")
        for index, (artifact, path) in enumerate(existing, 1):
            print(f"  {index}. {artifact['id']} ({path})")
        choice = input("Choose (o)verwrite, (n)ew organization, or (c)ancel: ").strip().lower()
        if choice == "c":
            raise SystemExit("Initialization cancelled.")
        if choice == "o":
            number = input("Organization number to overwrite: ").strip()
            try:
                artifact, path = existing[int(number) - 1]
            except (ValueError, IndexError):
                raise SystemExit("Invalid organization selection.")
            local_root = root / "sources"
            try:
                path.relative_to(local_root)
            except ValueError:
                raise SystemExit("Refusing to overwrite an organization outside the local profile.")
            name = _prompt_with_default("Organization name", artifact.get("name", artifact["id"]))
            org_id = artifact["id"]
            output = path
            replace_existing = True
        elif choice == "n":
            name = input("New organization name: ").strip()
            org_id = slugify(name)
            if any(artifact["id"] == org_id for artifact, _ in existing):
                raise SystemExit(f"Organization id already exists: {org_id}.")
            output = root / "sources" / org_id / "organization-catalog.json"
        else:
            raise SystemExit("Choose o, n, or c.")
    else:
        name = input("Organization name: ").strip()
        org_id = slugify(name)
        output = root / "sources" / org_id / "organization-catalog.json"

    if prepared is None:
        output.parent.mkdir(parents=True, exist_ok=True)
    defaults = _default_catalog(org_id, name)
    if output.exists() and not replace_existing:
        try:
            catalog = _merge_catalog_defaults(json.loads(output.read_text(encoding="utf-8")), defaults)
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"cannot update organization catalog: {output}: {exc}") from exc
    else:
        catalog = defaults
    if prepared is None:
        _atomic_write_text(output, json.dumps(catalog, indent=2) + "\n")
    else:
        prepared[output] = catalog
    source = str(output.parent)
    if source not in config["sources"]:
        config["sources"].append(source)
    managed_root = str(root / MANAGED_PACKAGE_SOURCE_RELATIVE_PATH)
    config["sources"] = [source for source in config["sources"] if source != managed_root]
    config["sources"].append(managed_root)
    config.setdefault("managed_sources", {})[MANAGED_PACKAGE_SOURCE_ID] = {
        "root": "installed-package",
        "paths": [managed_root],
    }
    config.setdefault("active_context", {})["organization_catalog_id"] = org_id
    if prepared is None:
        _write_config(root, config)
    print(f"Organization catalog: {output}")
    return org_id


def _create_starter_team(
    root: Path,
    config: dict,
    org_id: str,
    *,
    team_name: str,
    ownership_boundary: str | None = None,
    runtime: str,
    team_id: str | None = None,
    blueprint_id: str = "information-technology-core-team",
    domain_pack_ids: list[str] | None = None,
    prepared: dict[Path, dict] | None = None,
) -> Path:
    if team_id is None:
        catalog_path = root / "sources" / org_id / "organization-catalog.json"
        catalog = prepared[catalog_path] if prepared is not None else json.loads(catalog_path.read_text(encoding="utf-8"))
        for existing_id in catalog.get("published_artifacts", {}).get("team-instance", []):
            existing_path = catalog_path.parent / f"{existing_id}.json"
            if not existing_path.is_file():
                continue
            try:
                existing_team = json.loads(existing_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if (
                existing_team.get("artifact_type") == "team-instance"
                and existing_team.get("name", "").casefold() == team_name.casefold()
            ):
                team_id = existing_team["id"]
                break
    try:
        team = build_starter_team_instance(
            org_id,
            team_name,
            ownership_boundary,
            runtime=runtime,
            team_id=team_id,
            blueprint_id=blueprint_id,
            domain_pack_ids=domain_pack_ids,
        )
    except StarterConfigurationError as exc:
        raise SystemExit(str(exc)) from exc
    output = root / "sources" / org_id / f"{team['id']}.json"
    if output.exists():
        try:
            existing = json.loads(output.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"cannot read existing caravan: {output}: {exc}") from exc
        if not isinstance(existing, dict) or existing.get("artifact_type") != "team-instance":
            raise SystemExit(f"caravan path contains a different artifact: {output}")
        if existing.get("id") != team["id"]:
            raise SystemExit(f"caravan already exists with a different identity: {output}")
        defaults = existing.get("runtime_defaults", [])
        if defaults and defaults[0] != STARTER_RUNTIME_ADAPTERS.get(runtime):
            raise SystemExit(f"caravan uses a different runtime: {output}")
        team = existing
        print(f"Caravan already configured: {output}")
    else:
        if prepared is None:
            _atomic_write_text(output, json.dumps(team, indent=2) + "\n")
        print(f"Caravan: {output}")
    if prepared is not None:
        prepared[output] = team

    catalog_path = root / "sources" / org_id / "organization-catalog.json"
    catalog = prepared[catalog_path] if prepared is not None else json.loads(catalog_path.read_text(encoding="utf-8"))
    published = catalog.setdefault("published_artifacts", {})
    team_ids = published.setdefault("team-instance", [])
    if team["id"] not in team_ids:
        team_ids.append(team["id"])
    if prepared is None:
        _atomic_write_text(catalog_path, json.dumps(catalog, indent=2) + "\n")
    active_context = config.setdefault("active_context", {})
    active_context.update(
        {
            "organization_catalog_id": org_id,
            "team_instance_id": team["id"],
            "execution_profile_id": team["execution_profile_id"],
        }
    )
    if runtime in STARTER_RUNTIME_ADAPTERS:
        active_context["runtime_adapter_id"] = team["runtime_defaults"][0] if team["runtime_defaults"] else STARTER_RUNTIME_ADAPTERS[runtime]
        selected_runtime = _runtime_for_adapter(active_context["runtime_adapter_id"])
        if selected_runtime:
            active_context["runtime_profile_id"] = STARTER_RUNTIME_PROFILES[selected_runtime]
        if selected_runtime in {"opencode", "kiro"}:
            # These local runtime setups permit their declared adapted
            # capabilities; preserve a stricter profile explicitly chosen by the user.
            active_context.setdefault("validation_profile_id", "team-shared")
    if prepared is None:
        _write_config(root, config)
    return output


def init(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser()
    _check_runtime_selection(
        root,
        args.runtime,
        organization=getattr(args, "organization", None),
        team_name=getattr(args, "team", None),
        team_id=getattr(args, "team_id", None),
    )
    config_path = root / "config.json"
    if config_path.exists():
        existing = find_organization_catalogs(root)
    else:
        existing = []

    organization_name = getattr(args, "organization", None)
    team_name = getattr(args, "team", None)
    if organization_name is None and team_name is None and existing:
        context = load_config(root).get("active_context", {})
        active_organization = next((catalog for catalog, _ in existing if catalog["id"] == context.get("organization_catalog_id")), None)
        if active_organization and context.get("team_instance_id"):
            team_path = _team_instance_path(root, context["team_instance_id"])
            active_team = json.loads(team_path.read_text(encoding="utf-8"))
            organization_name = active_organization.get("name", active_organization["id"])
            team_name = active_team["name"]
    guided = organization_name is None and team_name is None and not existing
    if guided:
        print("\nSetup: press Enter to accept defaults or skip optional fields.")
        organization_name = _prompt_with_default("Organization name", DEFAULT_ORGANIZATION_NAME)
        team_name = _prompt_with_default("Caravan name", DEFAULT_TEAM_NAME)
        _confirm_initialization(
            root,
            organization_name,
            team_name,
            args.runtime,
            getattr(args, "skill_root", None),
        )

    config = copy.deepcopy(getattr(args, "prepared_config", None) or (
        load_config(root) if config_path.exists() else DEFAULT_CONFIG
    ))
    prepared: dict[Path, dict] = {}
    org_id = _create_organization(root, config, existing, organization_name, prepared=prepared)
    ownership_boundary = getattr(args, "ownership_boundary", None)
    if ownership_boundary and not team_name:
        raise SystemExit("--ownership-boundary requires --team")
    resolved = None
    if team_name:
        if args.runtime == "none":
            raise SystemExit("starter setup requires a runtime; use --runtime codex, --runtime opencode, or --runtime kiro")
        _create_starter_team(
            root, config, org_id, team_name=team_name,
            ownership_boundary=ownership_boundary, runtime=args.runtime,
            team_id=getattr(args, "team_id", None),
            blueprint_id=getattr(args, "blueprint", "information-technology-core-team"),
            domain_pack_ids=getattr(args, "domain_pack_id", None), prepared=prepared,
        )
        try:
            artifacts = []
            seen = set()
            managed_root = root / MANAGED_PACKAGE_SOURCE_RELATIVE_PATH
            for source in config["sources"]:
                path = resolve_source_path(root, source)
                if isinstance(source, str) and path == managed_root:
                    source_artifacts = load_source(_bundled_root() / "resources")
                elif path == root / "sources" / org_id and not path.exists():
                    source_artifacts = []
                else:
                    source_artifacts, _ = load_configured_source(root, source)
                for artifact in source_artifacts:
                    key = (artifact["artifact_type"], artifact["id"])
                    if key in seen:
                        raise ProfileError(f"duplicate artifact in profile sources: {key[0]}:{key[1]}")
                    seen.add(key)
                    artifacts.append(artifact)
            replacements = {(a["artifact_type"], a["id"]): a for a in prepared.values()}
            artifacts = [replacements.pop((a["artifact_type"], a["id"]), a) for a in artifacts]
            artifacts.extend(replacements.values())
            resolved = resolve_bundle({"context": config["active_context"], "artifacts": artifacts, "profile_root": str(root)})
        except (ProfileError, ResolutionError) as exc:
            policy = config["active_context"].get("validation_profile_id", "organization-shared")
            raise SystemExit(
                f"Setup rejected for {args.runtime} with validation profile {policy}: {exc}. "
                "Existing profile and skills were not changed. Select a compatible runtime or review your validation policy."
            ) from exc

    bootstrap(root)
    install_packaged_sources(root)
    for path, artifact in prepared.items():
        if artifact.get("artifact_type") == "team-instance" and path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_text(path, json.dumps(artifact, indent=2) + "\n")
    if args.runtime in STARTER_RUNTIME_ADAPTERS:
        skill_root = Path(getattr(args, "skill_root", None) or _configured_skill_root(config, args.runtime)).expanduser()
        install_skills(
            skill_root,
            runtime=args.runtime,
            confirm_replace=lambda prompt: _prompt_yes_no(prompt, default=False),
        )
        config.setdefault("managed_skill_roots", {})[args.runtime] = str(skill_root)
        if args.runtime == "codex":
            config["managed_skill_root"] = str(skill_root)
    _write_config(root, config)
    if resolved is not None:
        _print_setup_summary(
            root,
            organization_name,
            team_name,
            resolved,
            command_prefix=getattr(args, "command_prefix", "agent-caravan"),
        )
        _print_team_artifact_summary(root, org_id, resolved["context"]["team_instance_id"])
    else:
        print("Next step: create the first caravan from information-technology-core-team.")
    return 0


def configure(args: argparse.Namespace) -> int:
    """Create or update the approachable, runtime-neutral team workspace."""
    root = Path(args.root).expanduser()
    config = load_config(root)
    active_context = config.get("active_context", {})
    team_id = getattr(args, "team_id", None) or active_context.get("team_instance_id")
    if not team_id:
        raise SystemExit("no active caravan is configured; run `agent-caravan init` first")

    profile = load_profile(root)
    artifacts = {
        (artifact.get("artifact_type"), artifact.get("id")): artifact
        for artifact in profile.get("artifacts", [])
    }
    team = artifacts.get(("team-instance", team_id))
    if not team:
        raise SystemExit(f"caravan is not available in the active profile: {team_id}")

    team_name = team.get("name", team_id)
    existing = team.get("team_context", {})
    try:
        workspace = team_workspace(root, team_id)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    file_context = load_team_context(workspace, existing) if workspace.is_dir() else existing
    existing = file_context
    print("\nSetup: press Enter to accept defaults or skip optional fields.")
    mission = _prompt_with_default(
        "Caravan mission",
        existing.get("mission") or f"Support the work owned by {team_name}.",
    )
    repositories = _prompt_with_default(
        "Repositories/services (optional, comma-separated)",
        ", ".join(existing.get("work_surfaces", [])),
    )
    knowledge = _prompt_with_default(
        "Docs/instructions (optional, comma-separated)",
        ", ".join(existing.get("knowledge_sources", [])),
    )
    working_agreements = _prompt_with_default(
        "Caravan practices (optional)",
        existing.get("working_agreements") or "",
    )
    context = build_team_context(
        mission=mission,
        repositories=repositories,
        knowledge=knowledge,
        working_agreements=working_agreements,
        workspace=workspace,
    )
    context["instructions"] = existing.get("instructions", "")
    context["preferred_roles"] = existing.get("preferred_roles", [])
    context["role_guidance"] = existing.get("role_guidance", "")

    print("\nI’m going to configure:")
    print(f"  Caravan: {team_name}")
    print(f"  Workspace: {workspace}")
    print(f"  Mission: {context['mission']}")
    print(f"  Work surfaces: {', '.join(context['work_surfaces']) or 'None yet'}")
    print(f"  Knowledge sources: {', '.join(context['knowledge_sources']) or 'None yet'}")
    if not _prompt_yes_no("\nContinue?", default=True):
        raise SystemExit("Configuration cancelled.")

    workspace.mkdir(parents=True, exist_ok=True)
    documents = update_team_documents(team_name, context, existing.get("documents", {}))
    for filename, content in documents.items():
        _atomic_write_text(workspace / filename, content)
    context = load_team_context(workspace, context)
    context.pop("documents", None)
    context["authoring_workspace"] = str(workspace.relative_to(root.expanduser().resolve()))

    team_path = _team_instance_path(root, team_id)
    shared_context = copy.deepcopy(context)
    shared_context["work_surfaces"] = portable_work_surfaces(
        shared_context.get("work_surfaces", [])
    )
    profile_root = root.expanduser().resolve()
    local_sources = (profile_root / "sources").resolve()
    try:
        team_path.resolve().relative_to(local_sources)
        team["team_context"] = shared_context
        _atomic_write_text(team_path, json.dumps(team, indent=2) + "\n")
    except ValueError:
        # A shared checkout remains the source of truth. Per-employee guidance
        # is stored in the local team workspace; shared changes belong in Git.
        print("\nShared caravan source was left unchanged.")
        print("  This person's guidance is saved in the local caravan workspace.")
        print("  Edit and commit the shared repository to publish caravan-wide changes.")
    resolved = resolve_profile(root)
    print(f"\nCaravan configuration complete: {workspace}")
    print(f"  Resolved status: {resolved['status']}")
    print("  The caravan files are runtime-neutral and can be projected by a selected integration.")
    return 0


def resolve(args: argparse.Namespace) -> int:
    try:
        result = resolve_profile(args.root)
    except ResolutionError as error:
        if getattr(args, "diagnostics", False) and error.diagnostics:
            print(json.dumps({"status": "fail", "error": str(error), **error.diagnostics}, indent=2))
            return 1
        raise SystemExit(f"Agent Caravan resolve failed: {error}") from error
    print(json.dumps(result, indent=2))
    return 0


def status(args: argparse.Namespace) -> int:
    report = _status_report(Path(args.root).expanduser())
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _render_status(report)
    return 0 if report["status"] in {"pass", "degraded"} else 1


def _reasoning_evidence_summary(value: object) -> list[dict[str, object]]:
    """Project normalized reasoning evidence into a concise public CLI shape."""
    if not isinstance(value, list):
        return []
    summary = []
    for item in value:
        if not isinstance(item, dict):
            continue
        record = {
            field: item[field]
            for field in (
                "stage_id",
                "role_id",
                "requested_level",
                "requested_runtime_value",
                "status",
                "dispatch_status",
                "telemetry_status",
            )
            if field in item
        }
        if item.get("worker_ref"):
            record["worker_ref"] = item["worker_ref"]
        summary.append(record)
    return summary


def run(args: argparse.Namespace) -> int:
    """Run one task through the reference Codex execution surface."""
    if not args.dry_run:
        raise SystemExit("only --dry-run is currently supported; live Codex execution requires an injected surface")
    task_id = args.task_id or generated_task_id(args.objective)
    session_id = args.session_id or f"{task_id}-codex-session"
    run_id = args.run_id or f"{task_id}-codex-run-{args.attempt}"
    task = {"task_id": task_id, "objective": args.objective}
    logger = logging.getLogger("agentcaravan")
    started_event = log_event(
        logger,
        "agentcaravan.run.started",
        context={"task_id": task_id, "session_id": session_id, "run_id": run_id},
        attributes={"dry_run": args.dry_run},
    )
    if args.debug:
        task["execution_diagnostics"] = True
    try:
        resolved = resolve_profile(args.root)
        log_event(
            logger,
            "agentcaravan.run.profile_resolved",
            severity="DEBUG",
            context={"task_id": task_id, "session_id": session_id, "run_id": run_id},
            attributes={
                "runtime_adapter_id": resolved.get("runtime", {}).get("adapter_id"),
                "runtime_profile_id": resolved.get("context", {}).get("runtime_profile_id"),
            },
        )
        if resolved["runtime"].get("adapter_id") != STARTER_RUNTIME_ADAPTERS["codex"]:
            raise SystemExit(
                "CLI run --dry-run is currently Codex-only. "
                "Use the agent-caravan-opencode-orchestrator skill with an OpenCode team."
            )
        sessions_root = (
            Path(args.sessions_root).expanduser()
            if args.sessions_root
            else Path(args.root).expanduser() / "sessions"
        )
        _ensure_run_slot_available(sessions_root, task_id, run_id)
        result = run_codex_task(
            resolved,
            task,
            DryRunCodexExecutor(),
            store=LocalJsonExecutionStore(sessions_root),
            session_id=session_id,
            run_id=run_id,
            attempt=args.attempt,
        )
    except (OSError, ValueError, KeyError, ResolutionError) as exc:
        raise SystemExit(
            f"Agent Caravan run failed: {exc}. "
            "Run `agent-caravan status` to inspect the profile and managed skills."
        ) from exc

    metadata = result.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    session_path = sessions_root / task_id
    session_validation = validate_session_directory(sessions_root, task_id)
    if session_validation["valid"]:
        next_step = "Use the agent-caravan-codex-orchestrator skill for implementation work."
    else:
        next_step = (
            "Review session_validation issues and run "
            f"`agent-caravan validate-session --task-id {task_id}` before continuing."
        )
    summary = {
        "status": result["status"],
        "task_id": result["task_id"],
        "plan_id": result["plan_id"],
        "organization_catalog_id": resolved["context"].get("organization_catalog_id"),
        "team_instance_id": resolved["context"].get("team_instance_id"),
        "runtime_adapter_id": resolved["runtime"]["adapter_id"],
        "runtime_profile_id": resolved["runtime"].get(
            "runtime_profile_id",
            resolved["context"].get("runtime_profile_id"),
        ),
        "active_roles": result.get("active_roles", []),
        "completed_stages": result.get("completed_stages", []),
        "execution_realization": result.get("execution_realization", {"mode": "unreported"}),
        "topology_conformance": result.get("topology_conformance"),
        "scheduling_conformance": result.get("scheduling_conformance"),
        "role_turns": result.get("role_turns", []),
        "reasoning_evidence": _reasoning_evidence_summary(result.get("reasoning_evidence", [])),
        "decisions": result.get("decisions", []),
        "handoffs": result.get("handoffs", []),
        "verification": result.get("verification", []),
        "degraded_capabilities": result.get("degraded_capabilities", []),
        "unverified": metadata.get("unverified", []),
        "session_path": str(session_path),
        "session_validation": session_validation,
        "next_step": next_step,
    }
    if result.get("workflow_assessment") is not None:
        summary["workflow_assessment"] = result["workflow_assessment"]
    if args.debug:
        summary["execution_diagnostics"] = result.get("execution_diagnostics", {})
    finished_event = event_record(
        "agentcaravan.run.completed",
        outcome=result["status"],
        context={
            "task_id": task_id,
            "session_id": session_id,
            "run_id": run_id,
        },
        attributes={"session_valid": session_validation["valid"]},
    )
    if args.events_jsonl:
        run_record_path = sessions_root / task_id / "runs" / f"{run_id}.json"
        try:
            persisted_run = json.loads(run_record_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"cannot export run events from {run_record_path}: {exc}") from exc
        runtime_events = persisted_run.get("events", [])
        events = [started_event, *runtime_events, finished_event]
        event_path = Path(args.events_jsonl).expanduser()
        _atomic_write_text(event_path, "".join(json.dumps(event, sort_keys=True) + "\n" for event in events))
        summary["events_jsonl_path"] = str(event_path)
        summary["event_count"] = len(events)
        log_event(
            logger,
            "agentcaravan.run.events_exported",
            severity="DEBUG",
            context={"task_id": task_id, "session_id": session_id, "run_id": run_id},
            attributes={"event_count": len(events), "path": str(event_path)},
        )
    logger.log(
        logging.INFO,
        "agentcaravan.run.completed",
        extra={"agentcaravan_event": finished_event},
    )
    print(json.dumps(summary, indent=2))
    return 0 if session_validation["valid"] else 1


def handoff(args: argparse.Namespace) -> int:
    """Export and persist one runtime-neutral task handoff without launching a runtime."""
    task_id = args.task_id or generated_task_id(args.objective)
    task = {"task_id": task_id, "objective": args.objective}
    try:
        resolved = resolve_profile(args.root)
        prepared = prepare_execution(resolved, task)
        runtime = resolved.get("runtime", {})
        prepared["runtime"] = {
            "adapter_id": runtime.get("adapter_id"),
            "runtime_profile_id": resolved["context"].get("runtime_profile_id"),
            "execution_realization": {
                "mode": "unreported",
                "native_subagents": False,
                "reason": "The command exports a task handoff and does not execute a runtime.",
            },
        }
        records = build_execution_records(
            prepared,
            session_id=args.session_id or f"{task_id}-session",
            run_id=args.run_id or f"{task_id}-handoff-run-1",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        handoff_record = build_task_handoff(
            prepared["plan"],
            runtime_context={
                "adapter_id": runtime.get("adapter_id"),
                "profile_id": resolved["context"].get("runtime_profile_id"),
            },
            sender_role=args.sender_role,
            receiver_role=args.receiver_role,
            requested_action=args.requested_action,
            handoff_id=args.handoff_id,
        )
        for record in records.values():
            record["handoffs"] = [handoff_record]
        sessions_root = Path(args.sessions_root).expanduser() if args.sessions_root else Path(args.root).expanduser() / "sessions"
        _ensure_run_slot_available(sessions_root, task_id, records["run"]["run_id"])
        store = LocalJsonExecutionStore(sessions_root)
        store.write_records(task_id, records)
        completion = build_completion_record(
            prepared,
            "handoff-ready",
            datetime.now(timezone.utc).isoformat(),
            handoffs=[handoff_record],
            execution_realization=records["session"]["execution_realization"],
            unresolved_conditions=["The selected harness has not accepted or executed this handoff."],
        )
        store.write_completion(task_id, completion)
    except (OSError, ValueError, KeyError, ResolutionError, TaskHandoffError) as exc:
        raise SystemExit(f"Agent Caravan handoff failed: {exc}") from exc
    session_path = sessions_root / task_id
    handoff_path = session_path / "handoffs" / f"{handoff_record['handoff_id']}.json"
    validation = validate_session_directory(sessions_root, task_id)
    output = {
        **handoff_record,
        "session_path": str(session_path),
        "handoff_path": str(handoff_path),
        "run_id": records["run"]["run_id"],
        "session_validation": validation,
    }
    print(json.dumps(output, indent=2))
    return 0 if validation["valid"] else 1


def validate(_: argparse.Namespace) -> int:
    """Validate the manifest-declared portable artifacts and selected references."""
    bundled = _bundled_root()
    manifest = json.loads((bundled / "catalog-manifest.json").read_text(encoding="utf-8"))
    diagnostics: list[str] = []
    source_keys = (
        "machine_readable_bundles",
        "machine_readable_artifacts",
        "execution_workflows",
        "policy_artifacts",
    )
    source_groups: dict[str, list[str]] = {}
    for key in source_keys:
        value = manifest.get(key, [])
        if not isinstance(value, list) or any(not isinstance(path, str) for path in value):
            diagnostics.append(f"catalog manifest field {key} must be a list of paths")
            source_groups[key] = []
        else:
            source_groups[key] = value
    relative_paths = [path for key in source_keys for path in source_groups[key]]
    if len(relative_paths) != len(set(relative_paths)):
        diagnostics.append("catalog manifest repeats a serialized artifact source path")
    if not relative_paths:
        diagnostics.append("catalog manifest declares no serialized artifact sources")

    snapshot_pairs = manifest.get("distribution_snapshot_pairs", [])
    if not isinstance(snapshot_pairs, list):
        diagnostics.append("catalog manifest field distribution_snapshot_pairs must be a list")
        snapshot_pairs = []
    snapshot_paths = [
        item.get("snapshot")
        for item in snapshot_pairs
        if isinstance(item, dict) and isinstance(item.get("snapshot"), str)
    ]
    declared_source_paths = set(relative_paths) | set(snapshot_paths)
    inventory_roots = manifest.get("machine_readable_roots", [])
    if not isinstance(inventory_roots, list) or any(not isinstance(path, str) for path in inventory_roots):
        diagnostics.append("catalog manifest field machine_readable_roots must be a list of paths")
        inventory_roots = []
    for relative_root in inventory_roots:
        root = bundled / relative_root
        if not root.is_dir():
            diagnostics.append(f"missing machine-readable inventory root: {relative_root}")
            continue
        for resource in sorted(root.rglob("*.json")):
            relative_path = resource.relative_to(bundled).as_posix()
            if relative_path not in declared_source_paths:
                diagnostics.append(f"unlisted serialized artifact in machine-readable root: {relative_path}")

    artifacts: list[dict] = []
    checked_files: list[str] = []
    for relative_path in dict.fromkeys(relative_paths):
        resource = bundled / relative_path
        if not resource.is_file():
            diagnostics.append(f"missing packaged artifact source: {relative_path}")
            continue
        try:
            value = json.loads(resource.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            diagnostics.append(f"cannot read artifact source {relative_path}: {exc}")
            continue
        if not isinstance(value, dict):
            diagnostics.append(f"artifact source root must be an object: {relative_path}")
            continue
        if "artifacts" in value:
            values = value["artifacts"]
            if not isinstance(values, list):
                diagnostics.append(f"artifact bundle artifacts must be a list: {relative_path}")
                continue
        else:
            values = [value]
        if not values:
            diagnostics.append(f"artifact source contains no artifact records: {relative_path}")
            continue
        file_artifacts = []
        for index, item in enumerate(values):
            if not isinstance(item, dict):
                diagnostics.append(f"artifact record {index} must be an object: {relative_path}")
            elif not isinstance(item.get("artifact_type"), str) or not item["artifact_type"]:
                diagnostics.append(f"artifact record {index} is missing a string artifact_type: {relative_path}")
            else:
                file_artifacts.append(item)
        artifacts.extend(file_artifacts)
        if file_artifacts:
            checked_files.append(relative_path)

    snapshots_checked = 0
    for item in snapshot_pairs:
        if not isinstance(item, dict) or not isinstance(item.get("snapshot"), str) or not isinstance(item.get("canonical"), str):
            diagnostics.append("distribution snapshot entry must contain snapshot and canonical paths")
            continue
        snapshot_path = bundled / item["snapshot"]
        canonical_path = bundled / item["canonical"]
        try:
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
            canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
            validate_framework_artifact(snapshot)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            diagnostics.append(f"cannot validate distribution snapshot {item['snapshot']}: {exc}")
            continue
        if snapshot != canonical:
            diagnostics.append(f"distribution snapshot differs from canonical artifact: {item['snapshot']}")
        else:
            snapshots_checked += 1

    markdown_roots = manifest.get("markdown_artifact_roots", [])
    markdown_paths = manifest.get("markdown_artifact_documents", [])
    if (
        not isinstance(markdown_roots, list)
        or any(not isinstance(path, str) for path in markdown_roots)
        or not isinstance(markdown_paths, list)
        or any(not isinstance(path, str) for path in markdown_paths)
    ):
        diagnostics.append("catalog manifest Markdown artifact inventory must contain lists of paths")
        markdown_roots = []
        markdown_paths = []
    discovered_markdown: set[str] = set()
    for relative_root in markdown_roots:
        root = bundled / relative_root
        if not root.is_dir():
            diagnostics.append(f"missing Markdown artifact inventory root: {relative_root}")
            continue
        discovered_markdown.update(
            path.relative_to(bundled).as_posix()
            for path in root.rglob("*.md")
            if path.name != "README.md"
        )
    if discovered_markdown != set(markdown_paths):
        missing = sorted(discovered_markdown - set(markdown_paths))
        stale = sorted(set(markdown_paths) - discovered_markdown)
        if missing:
            diagnostics.append(f"unlisted Markdown artifact documents: {', '.join(missing)}")
        if stale:
            diagnostics.append(f"missing Markdown artifact documents: {', '.join(stale)}")
    markdown_artifacts: list[dict[str, str]] = []
    for relative_path in markdown_paths:
        try:
            resource = bundled / relative_path
            metadata = validate_markdown_artifact_metadata(resource.read_text(encoding="utf-8"))
            markdown_artifacts.append({**metadata, "file": relative_path})
        except (OSError, ValueError) as exc:
            diagnostics.append(f"invalid Markdown artifact metadata {relative_path}: {exc}")

    schema_paths = manifest.get("schemas", [])
    if not isinstance(schema_paths, list) or any(not isinstance(path, str) for path in schema_paths):
        diagnostics.append("catalog manifest field schemas must be a list of paths")
        schema_paths = []
    schemas_checked = 0
    for relative_path in schema_paths:
        try:
            validate_schema_file(bundled / relative_path)
            schemas_checked += 1
        except Exception as exc:
            diagnostics.append(f"invalid packaged JSON Schema {relative_path}: {exc}")

    plan_paths = manifest.get("portable_execution_plan_examples", [])
    if not isinstance(plan_paths, list) or any(not isinstance(path, str) for path in plan_paths):
        diagnostics.append("catalog manifest field portable_execution_plan_examples must be a list of paths")
        plan_paths = []
    plans_checked = 0
    for relative_path in plan_paths:
        try:
            plan = json.loads((bundled / relative_path).read_text(encoding="utf-8"))
            validate_artifact(plan, bundled / "resources/schemas/portable-execution-plan.schema.json")
            plans_checked += 1
        except Exception as exc:
            diagnostics.append(f"invalid portable execution plan example {relative_path}: {exc}")

    state_template_schemas = {
        "task.template.json": "task-state.schema.json",
        "session.template.json": "session-state.schema.json",
        "run.template.json": "run-record.schema.json",
    }
    state_templates = manifest.get("execution_state_templates", [])
    if not isinstance(state_templates, list) or any(not isinstance(path, str) for path in state_templates):
        diagnostics.append("catalog manifest field execution_state_templates must be a list of paths")
        state_templates = []
    state_templates_checked = 0
    for relative_path in state_templates:
        schema_name = state_template_schemas.get(Path(relative_path).name)
        if schema_name is None:
            diagnostics.append(f"unknown execution state template type: {relative_path}")
            continue
        try:
            instance = json.loads((bundled / relative_path).read_text(encoding="utf-8"))
            validate_artifact(instance, bundled / "resources/schemas" / schema_name)
            state_templates_checked += 1
        except Exception as exc:
            diagnostics.append(f"invalid execution state template {relative_path}: {exc}")

    try:
        artifact_summary = validate_framework_artifacts(artifacts)
    except Exception as exc:
        diagnostics.append(str(exc))
        artifact_summary = {"artifacts": len(artifacts), "types": len({item.get("artifact_type") for item in artifacts})}
    skills_checked = 0
    for skill_id in all_skill_ids():
        try:
            packaged_skill_path(skill_id)
            skills_checked += 1
        except (FileNotFoundError, ValueError) as exc:
            diagnostics.append(f"missing packaged skill {skill_id}: {exc}")
    report = {
        "valid": not diagnostics,
        "checks_performed": [
            "manifest coverage for scoped serialized and Markdown artifact roots",
            "JSON Schema validity for packaged schemas",
            "JSON Schema structure for serialized portable framework artifacts",
            "unique artifact identity by artifact_type and id within the collected artifact set",
            "selected cross-artifact references: catalog publications, team composition, team attachments, runtime targets, domain and specialization ownership, and overlay targets",
            "Markdown artifact title, identity, version, and scope metadata",
            "portable execution-plan examples and execution state template schemas",
            "distributable snapshot schema validity and parity with canonical artifacts",
            "packaged skill source presence",
        ],
        "coverage": {
            "artifact_count": artifact_summary["artifacts"],
            "artifact_type_count": artifact_summary["types"],
            "artifact_types": sorted({item["artifact_type"] for item in artifacts}),
            "artifact_files": checked_files,
            "markdown_artifact_count": len(markdown_artifacts),
            "markdown_artifact_type_count": len({item["artifact_type"] for item in markdown_artifacts}),
            "markdown_artifact_types": sorted({item["artifact_type"] for item in markdown_artifacts}),
            "markdown_artifact_files": markdown_paths,
            "schema_count": schemas_checked,
            "portable_execution_plan_count": plans_checked,
            "execution_state_template_count": state_templates_checked,
            "distribution_snapshot_count": snapshots_checked,
            "skill_count": skills_checked,
        },
        "not_checked": [
            "execution results and persisted task, session, and run records (use validate-session for persisted record linkage)",
            "resolved team coverage and overlay precedence outcomes (use resolve and resolver regression tests)",
            "runtime capability compatibility (use resolve) and live runtime behavior (requires adapter-specific conformance)",
            "task-level output quality against acceptance criteria",
        ],
        "diagnostics": diagnostics,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["valid"] else 1


def validate_session(args: argparse.Namespace) -> int:
    """Validate one persisted local task/session/run evidence directory."""
    sessions_root = (
        Path(args.sessions_root).expanduser()
        if args.sessions_root
        else Path(args.root).expanduser() / "sessions"
    )
    report = validate_session_directory(sessions_root, args.task_id)
    print(json.dumps(report, indent=2))
    return 0 if report["valid"] else 1


def validate_runtime_verification_record(args: argparse.Namespace) -> int:
    """Validate the portable shape of one adapter-owned verification report."""
    path = Path(args.path).expanduser()
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        validate_artifact(
            record,
            _bundled_root() / "resources/schemas/runtime-verification-record.schema.json",
        )
        report = {
            "valid": True,
            "record_id": record["record_id"],
            "adapter": record["adapter"],
            "runtime": record["runtime"],
            "execution_surface": record["execution_surface"],
            "scenario": record["scenario"],
            "result": record["result"],
            "evidence_reference_count": len(record["evidence_refs"]),
            "claim_scope": "one scenario under the recorded runtime, adapter, surface, and configuration",
            "evidence_authenticity_checked": False,
        }
        exit_code = 0
    except Exception as exc:
        report = {"valid": False, "path": str(path), "diagnostics": [str(exc)]}
        exit_code = 1
    print(json.dumps(report, indent=2))
    return exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agent-caravan")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_logging_arguments(command_parser: argparse.ArgumentParser) -> None:
        command_parser.add_argument("--log-level", choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"))
        command_parser.add_argument("--log-format", choices=("text", "json"))

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    init_parser.add_argument(
        "--skill-root",
        type=Path,
        help="skill destination; defaults to ~/.agents/skills for Codex, ~/.config/opencode/skills for OpenCode, or ~/.kiro/skills for Kiro",
    )
    init_parser.add_argument(
        "--runtime",
        choices=("none", "codex", "opencode", "kiro"),
        default=DEFAULT_RUNTIME,
        help="runtime for the starter caravan; Codex is the default",
    )
    init_parser.add_argument("--organization", help="organization name for non-interactive starter setup")
    init_parser.add_argument("--team", help="first caravan name for non-interactive starter setup")
    init_parser.add_argument("--team-id", help="stable caravan artifact ID; defaults to <organization>-<team>")
    init_parser.add_argument(
        "--ownership-boundary",
        help="advanced caravan metadata; omitted by the guided starter setup",
    )
    init_parser.add_argument(
        "--blueprint",
        default="information-technology-core-team",
        help="advanced caravan template override; the guided setup uses the sole default",
    )
    init_parser.add_argument("--domain-pack-id", action="append", default=[])
    init_parser.set_defaults(handler=init)
    add_logging_arguments(init_parser)
    resolve_parser = subparsers.add_parser("resolve")
    resolve_parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    resolve_parser.add_argument(
        "--diagnostics",
        action="store_true",
        help="print structured validation findings when resolution fails",
    )
    resolve_parser.set_defaults(handler=resolve)
    add_logging_arguments(resolve_parser)
    configure_parser = subparsers.add_parser(
        "configure",
        help="configure the active caravan using runtime-neutral Markdown files",
    )
    configure_parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    configure_parser.add_argument("--team-id", help="caravan to configure; defaults to the active caravan")
    configure_parser.set_defaults(handler=configure)
    add_logging_arguments(configure_parser)
    status_parser = subparsers.add_parser("status", help="inspect the active profile without changing it")
    status_parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    status_parser.add_argument("--json", action="store_true", help="emit machine-readable status")
    status_parser.set_defaults(handler=status)
    add_logging_arguments(status_parser)
    run_parser = subparsers.add_parser("run", help="run one task through the reference execution surface")
    run_parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    run_parser.add_argument(
        "--task-id",
        help="stable task ID; generated from the objective when omitted",
    )
    run_parser.add_argument("--objective", required=True)
    run_parser.add_argument("--dry-run", action="store_true", help="use the truthful simulated Codex surface")
    run_parser.add_argument("--debug", action="store_true", help="include a concise execution diagnostics trace")
    run_parser.add_argument("--events-jsonl", type=Path, help="write portable execution events to a separate JSONL file")
    run_parser.add_argument("--sessions-root", type=Path, help="override the profile's sessions directory")
    run_parser.add_argument("--session-id")
    run_parser.add_argument("--run-id")
    run_parser.add_argument(
        "--attempt",
        type=int,
        default=1,
        help="execution attempt number; existing run evidence is never overwritten",
    )
    run_parser.set_defaults(handler=run)
    add_logging_arguments(run_parser)
    handoff_parser = subparsers.add_parser(
        "handoff",
        help="export and persist one runtime-neutral task handoff without launching a runtime",
    )
    handoff_parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    handoff_parser.add_argument("--task-id")
    handoff_parser.add_argument("--objective", required=True)
    handoff_parser.add_argument("--requested-action", required=True)
    handoff_parser.add_argument("--sender-role", default="tech-owner")
    handoff_parser.add_argument("--receiver-role", default="engineer")
    handoff_parser.add_argument("--handoff-id")
    handoff_parser.add_argument("--sessions-root", type=Path)
    handoff_parser.add_argument("--session-id")
    handoff_parser.add_argument("--run-id")
    handoff_parser.set_defaults(handler=handoff)
    add_logging_arguments(handoff_parser)
    session_parser = subparsers.add_parser(
        "validate-session",
        help="validate persisted task, session, run, and completion evidence",
    )
    session_parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    session_parser.add_argument("--sessions-root", type=Path, help="override the profile's sessions directory")
    session_parser.add_argument("--task-id", required=True)
    session_parser.set_defaults(handler=validate_session)
    add_logging_arguments(session_parser)
    verification_parser = subparsers.add_parser(
        "validate-verification-record",
        help="validate one scenario-scoped runtime verification record",
    )
    verification_parser.add_argument("path", help="path to the integration-produced JSON record")
    verification_parser.set_defaults(handler=validate_runtime_verification_record)
    add_logging_arguments(verification_parser)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.set_defaults(handler=validate)
    add_logging_arguments(validate_parser)
    args = parser.parse_args(argv)
    logging_settings = {}
    config_path = Path(getattr(args, "root", DEFAULT_ROOT)).expanduser() / "config.json"
    if config_path.is_file():
        try:
            configured = json.loads(config_path.read_text(encoding="utf-8"))
            logging_settings = configured.get("logging", {}) if isinstance(configured, dict) else {}
            if not isinstance(logging_settings, dict):
                raise SystemExit(f"profile config logging must be an object: {config_path}")
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"cannot read logging settings from {config_path}: {exc}") from exc
    level = args.log_level or logging_settings.get("level", "INFO")
    output_format = args.log_format or logging_settings.get("format", "text")
    if not isinstance(level, str) or level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise SystemExit("logging level must be DEBUG, INFO, WARNING, ERROR, or CRITICAL")
    if not isinstance(output_format, str) or output_format not in {"text", "json"}:
        raise SystemExit("logging format must be text or json")
    configure_logging(level, output_format)
    logger = logging.getLogger("agentcaravan")
    log_event(logger, "agentcaravan.command.started", attributes={"command": args.command})
    try:
        result = args.handler(args)
    except SystemExit as exc:
        exit_code = exc.code if isinstance(exc.code, int) else 1
        log_event(
            logger,
            "agentcaravan.command.failed",
            severity="ERROR",
            outcome="failure",
            attributes={
                "command": args.command,
                "exit_code": exit_code,
                "error_type": "SystemExit",
                "diagnostic": str(exc.code) if exc.code is not None else "",
            },
        )
        if output_format == "json":
            return exit_code
        raise
    except Exception as exc:
        log_event(
            logger,
            "agentcaravan.command.failed",
            severity="ERROR",
            outcome="failure",
            attributes={
                "command": args.command,
                "exit_code": 1,
                "error_type": type(exc).__name__,
                "diagnostic": str(exc),
            },
        )
        if output_format == "json":
            return 1
        raise
    if result == 0:
        log_event(
            logger,
            "agentcaravan.command.completed",
            outcome="success",
            attributes={"command": args.command, "exit_code": result},
        )
    else:
        log_event(
            logger,
            "agentcaravan.command.failed",
            severity="ERROR",
            outcome="failure",
            attributes={"command": args.command, "exit_code": result},
        )
    return result


if __name__ == "__main__":
    raise SystemExit(main())
