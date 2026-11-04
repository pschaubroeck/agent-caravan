"""Bootstrap the local Agent Caravan implementation profile."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from importlib.resources import files
from pathlib import Path


DEFAULT_ROOT = Path.home() / ".agents" / "agent-caravan"
SUBDIRECTORIES = ("sources", "overrides", "sessions", "cache")
DEFAULT_CONFIG = {
    "format_version": "1.0.0",
    "sources": [],
    "managed_sources": {},
    "active_context": {},
    "overrides": [],
    "adapter_overrides": {},
    "logging": {"level": "INFO", "format": "text"},
}

MANAGED_PACKAGE_SOURCE_ID = "agentcaravan_package"
MANAGED_PACKAGE_SOURCE_RELATIVE_PATH = Path("sources") / "_agentcaravan-core"


def _bundled_root() -> Path:
    """Return packaged resources, falling back to the repository checkout."""
    bundled = files("agentcaravan").joinpath("_bundled")
    if bundled.is_dir():
        return Path(str(bundled))

    repository_root = Path(__file__).resolve().parents[2]
    if (repository_root / "resources").is_dir() and (repository_root / "skills").is_dir():
        return repository_root
    raise RuntimeError("Agent Caravan bundled framework resources are unavailable")


def bootstrap(root: str | Path | None = None) -> Path:
    """Create the local layout without replacing existing files."""
    framework_root = Path(root) if root is not None else DEFAULT_ROOT
    framework_root.mkdir(parents=True, exist_ok=True)
    for directory in SUBDIRECTORIES:
        (framework_root / directory).mkdir(exist_ok=True)

    config_path = framework_root / "config.json"
    if not config_path.exists():
        temporary_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=framework_root,
                prefix=".config.json.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary_path = handle.name
                json.dump(DEFAULT_CONFIG, handle, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            try:
                # Linking publishes the complete file atomically and fails if
                # another initializer created config.json in the meantime.
                os.link(temporary_path, config_path)
            except FileExistsError:
                pass
        finally:
            if temporary_path:
                os.unlink(temporary_path)
    return framework_root


def install_packaged_sources(root: str | Path | None = None) -> Path:
    """Copy packaged framework defaults into a managed local source directory."""
    framework_root = bootstrap(root)
    destination = framework_root / MANAGED_PACKAGE_SOURCE_RELATIVE_PATH
    bundled = _bundled_root()
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    repository_root = Path(__file__).resolve().parents[2]
    entries = [bundled / "resources"] if bundled == repository_root else list(bundled.iterdir())
    for item in entries:
        if item.name == "skills":
            continue
        target = destination / item.name
        if item.is_dir():
            target.mkdir()
            for child in item.iterdir():
                if child.is_dir():
                    shutil.copytree(child, target / child.name)
                else:
                    shutil.copy2(child, target / child.name)
        else:
            shutil.copy2(item, target)
    return destination


def packaged_skill_path(skill_id: str) -> Path:
    """Return a packaged skill path for an installed bundle or checkout."""
    skill = _bundled_root() / "skills" / skill_id
    if not skill.is_dir():
        raise RuntimeError(f"installed Agent Caravan package does not contain skill: {skill_id}")
    return skill


def main() -> int:
    root = bootstrap()
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
