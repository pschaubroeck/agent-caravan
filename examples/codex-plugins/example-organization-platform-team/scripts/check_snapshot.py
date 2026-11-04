#!/usr/bin/env python3
"""Verify that the plugin snapshot matches the canonical example artifacts."""

from __future__ import annotations

import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
PLUGIN_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = {
    REPOSITORY_ROOT / "examples/example-organization/organizations/example-organization-catalog.json":
        PLUGIN_ROOT / "team-snapshot/example-organization-catalog.json",
    REPOSITORY_ROOT / "examples/example-organization/caravans/platform-team.json":
        PLUGIN_ROOT / "team-snapshot/platform-team.json",
    REPOSITORY_ROOT / "examples/example-organization/caravans/product-team.json":
        PLUGIN_ROOT / "team-snapshot/product-team.json",
}


def main() -> int:
    errors: list[str] = []
    for canonical, snapshot in ARTIFACTS.items():
        if not canonical.is_file():
            errors.append(f"canonical artifact is missing: {canonical.relative_to(REPOSITORY_ROOT)}")
        elif not snapshot.is_file():
            errors.append(f"plugin snapshot is missing: {snapshot.relative_to(PLUGIN_ROOT)}")
        elif canonical.read_bytes() != snapshot.read_bytes():
            errors.append(f"plugin snapshot differs from canonical artifact: {canonical.relative_to(REPOSITORY_ROOT)}")

    if errors:
        print("Snapshot check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Plugin snapshot matches the canonical Example Organization artifacts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
