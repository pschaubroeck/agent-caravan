#!/usr/bin/env python3
"""Demonstrate two separate profiles resolving one shared team catalog."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from agentcaravan.profile import load_profile
from agentcaravan.resolve_framework import resolve_profile


PROFILE_TEMPLATES = (
    ("Coworker One", Path(__file__).parent / "profiles/coworker-one/config.json"),
    ("Coworker Two", Path(__file__).parent / "profiles/coworker-two/config.json"),
)
SHARED_CHECKOUT_TOKEN = "<shared-catalog-checkout>"


def _artifact_versions(bundle: dict[str, Any], result: dict[str, Any]) -> dict[str, str]:
    versions = {
        (artifact.get("artifact_type"), artifact.get("id")): artifact.get("version")
        for artifact in bundle["artifacts"]
    }
    context = result["context"]
    return {
        "team_instance": versions[("team-instance", context["team_instance_id"])],
        "team_blueprint": versions[("team-blueprint", context["team_blueprint_id"])],
    }


def run_scenario() -> dict[str, Any]:
    """Resolve both sample profiles under isolated temporary profile roots."""
    shared_source = REPOSITORY_ROOT / "examples/example-organization"
    common_resources = [
        REPOSITORY_ROOT / "resources/core/agentcaravan-core-team.json",
        REPOSITORY_ROOT / "resources/runtime/agentcaravan-codex-runtime.json",
    ]
    profiles: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="agentcaravan-coworker-sharing-") as temporary:
        temporary_root = Path(temporary)
        for index, (name, template_path) in enumerate(PROFILE_TEMPLATES, start=1):
            profile_root = temporary_root / f"coworker-{index}" / "profile"
            profile_root.mkdir(parents=True)
            config = json.loads(template_path.read_text(encoding="utf-8"))
            for source in config["sources"]:
                if isinstance(source, dict) and source.get("checkout") == SHARED_CHECKOUT_TOKEN:
                    source["checkout"] = str(REPOSITORY_ROOT)
            config["sources"].extend(str(path) for path in common_resources)
            (profile_root / "config.json").write_text(
                json.dumps(config, indent=2) + "\n", encoding="utf-8"
            )

            loaded = load_profile(profile_root)
            resolved = resolve_profile(profile_root)
            profiles.append(
                {
                    "name": name,
                    "profile_root": str(profile_root),
                    "status": resolved["status"],
                    "organization_catalog_id": resolved["context"]["organization_catalog_id"],
                    "team_instance_id": resolved["context"]["team_instance_id"],
                    "team_blueprint_id": resolved["context"]["team_blueprint_id"],
                    "artifact_versions": _artifact_versions(loaded, resolved),
                    "source_provenance": resolved.get("source_provenance", []),
                }
            )

    if profiles[0]["profile_root"] == profiles[1]["profile_root"]:
        raise RuntimeError("coworker profiles must have separate local roots")
    shared_identity = (
        "organization_catalog_id",
        "team_instance_id",
        "team_blueprint_id",
        "artifact_versions",
    )
    if any(any(profile[key] != profiles[0][key] for key in shared_identity) for profile in profiles[1:]):
        raise RuntimeError("coworker profiles did not resolve the same shared artifacts")

    return {"shared_source": str(shared_source), "profiles": profiles}


def main() -> int:
    try:
        report = run_scenario()
    except Exception as error:
        print(f"Coworker sharing example failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
