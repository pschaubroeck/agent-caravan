#!/usr/bin/env python3
"""Copy the plugin's organization snapshot into an explicit Agent Caravan profile."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_ROOT = PLUGIN_ROOT / "team-snapshot"
FILES = {
    "example-organization-catalog.json": "organization-catalog.json",
    "platform-team.json": "team-instance.json",
    "product-team.json": "product-team.json",
}


def install(profile_root: Path) -> Path:
    destination = profile_root.expanduser() / "sources" / "example-organization"
    if destination.exists():
        raise FileExistsError(f"destination already exists; refusing to overwrite: {destination}")
    missing = [name for name in FILES if not (SNAPSHOT_ROOT / name).is_file()]
    if missing:
        raise FileNotFoundError(f"plugin snapshot is incomplete: {', '.join(missing)}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.mkdir()
    try:
        for source_name, target_name in FILES.items():
            with (destination / target_name).open("xb") as target:
                target.write((SNAPSHOT_ROOT / source_name).read_bytes())
    except Exception:
        shutil.rmtree(destination)
        raise
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile-root",
        required=True,
        type=Path,
        help="explicit Agent Caravan profile root to receive the organization source",
    )
    args = parser.parse_args()
    try:
        installed = install(args.profile_root)
    except (FileExistsError, FileNotFoundError, OSError) as exc:
        print(f"Installation stopped: {exc}", file=sys.stderr)
        return 1
    print(f"Installed the Example Organization snapshot at {installed}")
    print("The snapshot is not linked to the catalog repository; update it by installing a newer plugin version.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
