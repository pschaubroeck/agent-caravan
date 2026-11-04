#!/usr/bin/env python3
"""Print a deterministic, local dry run for the organization-coordination recipe."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

EXAMPLE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXAMPLE_ROOT.parents[1]
DEFAULT_MAP = EXAMPLE_ROOT / "organization-map.json"
DEFAULT_CATALOG = (
    REPOSITORY_ROOT
    / "examples/example-organization/organizations/example-organization-catalog.json"
)
DEFAULT_TEAM_DIRECTORY = REPOSITORY_ROOT / "examples/example-organization/caravans"
DEFAULT_SCENARIO = "shared-preferences-change"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"could not read JSON from {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return value


def _require_array(value: dict[str, Any], key: str, source: str) -> list[Any]:
    result = value.get(key)
    if not isinstance(result, list):
        raise ValueError(f"{source} must contain a '{key}' array")
    return result


def _require_string(value: dict[str, Any], key: str, context: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result.strip():
        raise ValueError(f"{context} must contain a non-empty '{key}' string")
    return result


def _validate_hierarchy(organization_map: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    raw_units = _require_array(organization_map, "units", "organization map")
    raw_teams = _require_array(organization_map, "teams", "organization map")
    units: dict[str, dict[str, Any]] = {}
    for index, unit in enumerate(raw_units):
        context = f"unit at index {index}"
        if not isinstance(unit, dict):
            raise ValueError(f"{context} must be an object")
        unit_id = _require_string(unit, "id", context)
        _require_string(unit, "name", context)
        if unit_id in units:
            raise ValueError(f"duplicate unit id in organization map: {unit_id}")
        parent_id = unit.get("parent_unit_id")
        if parent_id is not None and (not isinstance(parent_id, str) or not parent_id.strip()):
            raise ValueError(f"unit {unit_id!r} parent_unit_id must be null or a non-empty string")
        units[unit_id] = unit

    for unit_id, unit in units.items():
        parent_id = unit.get("parent_unit_id")
        if parent_id is not None and parent_id not in units:
            raise ValueError(f"unit {unit_id!r} references unknown parent unit {parent_id!r}")

    checked: set[str] = set()
    for unit_id in units:
        ancestry: set[str] = set()
        current_id: str | None = unit_id
        while current_id is not None and current_id not in checked:
            if current_id in ancestry:
                raise ValueError(f"cycle detected in unit hierarchy at {current_id!r}")
            ancestry.add(current_id)
            current_id = units[current_id].get("parent_unit_id")
        checked.update(ancestry)

    team_ids: set[str] = set()
    for index, team in enumerate(raw_teams):
        context = f"team at index {index}"
        if not isinstance(team, dict):
            raise ValueError(f"{context} must be an object")
        team_id = _require_string(team, "id", context)
        _require_string(team, "name", context)
        _require_string(team, "team_instance_id", context)
        unit_id = _require_string(team, "unit_id", context)
        if team_id in team_ids:
            raise ValueError(f"duplicate team id in organization map: {team_id}")
        team_ids.add(team_id)
        if unit_id not in units:
            raise ValueError(f"team {team_id!r} references unknown unit {unit_id!r}")
    return raw_units, raw_teams


def load_and_validate(
    map_path: Path = DEFAULT_MAP,
    catalog_path: Path = DEFAULT_CATALOG,
    team_directory: Path = DEFAULT_TEAM_DIRECTORY,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Load the sidecar map and confirm its hierarchy and team references."""
    organization_map = _read_json(map_path)
    _, teams = _validate_hierarchy(organization_map)
    catalog = _read_json(catalog_path)
    catalog_id = _require_string(catalog, "id", "organization catalog")
    published = catalog.get("published_artifacts")
    if not isinstance(published, dict):
        raise ValueError("organization catalog must contain a 'published_artifacts' object")
    catalog_team_ids = published.get("team-instance", [])
    if not isinstance(catalog_team_ids, list) or not all(
        isinstance(team_id, str) for team_id in catalog_team_ids
    ):
        raise ValueError("organization catalog 'team-instance' must be an array of IDs")

    team_instances: dict[str, dict[str, Any]] = {}
    try:
        team_paths = sorted(team_directory.glob("*.json"))
    except OSError as error:
        raise ValueError(f"could not read team directory {team_directory}: {error}") from error
    for path in team_paths:
        instance = _read_json(path)
        if instance.get("artifact_type") == "team-instance" and isinstance(instance.get("id"), str):
            team_instances[instance["id"]] = instance

    team_ids = {team["id"] for team in teams}
    for team in teams:
        team_id = team["id"]
        instance_id = team["team_instance_id"]
        if instance_id not in catalog_team_ids:
            raise ValueError(
                f"unknown team instance reference {instance_id!r} for map team {team_id!r}: "
                f"not published by organization catalog {catalog_id!r}"
            )
        if instance_id not in team_instances:
            raise ValueError(
                f"team instance {instance_id!r} is published by catalog {catalog_id!r} "
                f"but has no matching JSON file under {team_directory}"
            )
        if team_instances[instance_id].get("organization_catalog_id") != catalog_id:
            raise ValueError(
                f"team instance {instance_id!r} does not reference catalog {catalog_id!r}"
            )

    scenarios = _require_array(organization_map, "scenarios", "organization map")
    scenario_ids: set[str] = set()
    for index, scenario in enumerate(scenarios):
        context = f"scenario at index {index}"
        if not isinstance(scenario, dict):
            raise ValueError(f"{context} must be an object")
        scenario_id = _require_string(scenario, "id", context)
        _require_string(scenario, "request", context)
        if scenario_id in scenario_ids:
            raise ValueError(f"duplicate scenario id in organization map: {scenario_id}")
        scenario_ids.add(scenario_id)
        route = _require_array(scenario, "route", context)
        for step_index, step in enumerate(route):
            step_context = f"step {step_index + 1} in scenario {scenario_id!r}"
            if not isinstance(step, dict):
                raise ValueError(f"{step_context} must be an object")
            team_id = _require_string(step, "team_id", step_context)
            if team_id not in team_ids:
                raise ValueError(
                    f"scenario {scenario_id!r} references unknown map team {team_id!r}"
                )
            _require_string(step, "responsibility", step_context)
            _require_string(step, "handoff", step_context)
    return organization_map, team_instances


def build_route(
    organization_map: dict[str, Any], scenario_id: str = DEFAULT_SCENARIO
) -> list[dict[str, str]]:
    """Expand a scenario's explicit team steps into a readable route."""
    teams = {team["id"]: team for team in organization_map["teams"]}
    scenarios = {scenario["id"]: scenario for scenario in organization_map["scenarios"]}
    if scenario_id not in scenarios:
        raise ValueError(f"unknown scenario: {scenario_id}")
    route = []
    for index, step in enumerate(scenarios[scenario_id]["route"], start=1):
        team = teams[step["team_id"]]
        route.append(
            {
                "step": str(index),
                "team_id": team["id"],
                "team_name": team["name"],
                "responsibility": step["responsibility"],
                "handoff": step["handoff"],
            }
        )
    return route


def render(scenario: dict[str, Any], route: list[dict[str, str]]) -> str:
    lines = [
        "Organization coordination dry run",
        f"Scenario: {scenario['id']}",
        f"Request: {scenario['request']}",
        "",
    ]
    for step in route:
        lines.extend(
            [
                f"{step['step']}. {step['team_name']} ({step['team_id']})",
                f"   Responsibility: {step['responsibility']}",
                f"   Handoff: {step['handoff']}",
            ]
        )
    lines.extend(
        [
            "",
            "Dry run only: this cookbook map is orchestration input, not an Agent Caravan artifact.",
            "It does not enforce reporting lines or permissions, or launch agents/runtime work.",
        ]
    )
    return "\n".join(lines)


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate an organization map and print an explicitly authored route."
    )
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP, help="organization map JSON")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG, help="organization catalog JSON")
    parser.add_argument("--team-dir", type=Path, default=DEFAULT_TEAM_DIRECTORY, help="directory of team-instance JSON files")
    parser.add_argument("--scenario", default=DEFAULT_SCENARIO, help="scenario ID to print")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _argument_parser().parse_args(argv)
    try:
        organization_map, _ = load_and_validate(
            arguments.map, arguments.catalog, arguments.team_dir
        )
        scenarios = {scenario["id"]: scenario for scenario in organization_map["scenarios"]}
        if arguments.scenario not in scenarios:
            raise ValueError(f"unknown scenario: {arguments.scenario}")
        scenario = scenarios[arguments.scenario]
        print(render(scenario, build_route(organization_map, arguments.scenario)))
    except (ValueError, KeyError) as error:
        print(f"Organization coordination example failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
