"""Runtime skill inventory and safe local installation lifecycle."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Callable

from .org_framework_layout import _bundled_root, packaged_skill_path


SKILL_MANIFEST_PATH = Path("skills/skill-distribution.json")
MANAGED_SKILL_MARKER = ".agentcaravan-managed.json"
MANAGED_SKILL_FORMAT_VERSION = "1.0.0"
SUPPORTED_RUNTIMES = frozenset({"codex", "opencode", "kiro"})


def skill_inventory() -> tuple[dict, ...]:
    """Load the packaged skill inventory and validate its stable identifiers."""
    path = _bundled_root() / SKILL_MANIFEST_PATH
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"invalid packaged skill inventory: {error}") from error
    entries = manifest.get("skills") if isinstance(manifest, dict) else None
    if not isinstance(entries, list):
        raise RuntimeError("packaged skill inventory must contain a skills array")

    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    normalized = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise RuntimeError("packaged skill inventory entries must be objects")
        skill_id = entry.get("id")
        source_path = entry.get("path")
        runtimes = entry.get("runtimes")
        if (
            not isinstance(skill_id, str)
            or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", skill_id)
            or source_path != f"skills/{skill_id}"
        ):
            raise RuntimeError("each packaged skill requires a matching id and skills/<id> path")
        if skill_id in seen_ids or source_path in seen_paths:
            raise RuntimeError(f"duplicate packaged skill entry: {skill_id}")
        if (
            not isinstance(runtimes, list)
            or not runtimes
            or any(not isinstance(runtime, str) or runtime not in SUPPORTED_RUNTIMES for runtime in runtimes)
            or len(runtimes) != len(set(runtimes))
        ):
            raise RuntimeError(f"packaged skill {skill_id} has invalid runtime selection")
        seen_ids.add(skill_id)
        seen_paths.add(source_path)
        normalized.append({"id": skill_id, "path": source_path, "runtimes": tuple(runtimes)})
    if not normalized:
        raise RuntimeError("packaged skill inventory must not be empty")
    return tuple(normalized)


def skill_ids_for_runtime(runtime: str) -> tuple[str, ...]:
    if runtime not in SUPPORTED_RUNTIMES:
        raise ValueError(f"unsupported skill runtime: {runtime}")
    return tuple(
        skill["id"] for skill in skill_inventory()
        if runtime in skill["runtimes"]
    )


def all_skill_ids() -> tuple[str, ...]:
    return tuple(skill["id"] for skill in skill_inventory())


def default_skill_root(runtime: str) -> Path:
    if runtime == "kiro":
        return Path.home() / ".kiro" / "skills"
    if runtime == "opencode":
        return Path.home() / ".config" / "opencode" / "skills"
    if runtime == "codex":
        return Path.home() / ".agents" / "skills"
    raise ValueError(f"unsupported skill runtime: {runtime}")


def skill_status(skill_root: Path | None = None, *, runtime: str = "codex") -> dict[str, object]:
    skill_root = skill_root or default_skill_root(runtime)
    missing = []
    modified = []
    for skill_id in skill_ids_for_runtime(runtime):
        destination = skill_root / skill_id
        if not destination.is_dir():
            missing.append(skill_id)
            continue
        marker = _read_skill_marker(destination, skill_id)
        if marker is None or marker.get("content_hash") != _try_skill_fingerprint(destination):
            modified.append(skill_id)
    if missing:
        status = "missing"
    elif modified:
        status = "modified"
    else:
        status = "installed"
    return {
        "status": status,
        "root": str(skill_root),
        "runtime": runtime,
        "missing": missing,
        "modified": modified,
    }


def _iter_skill_entries(path: Path):
    for entry in sorted(path.iterdir(), key=lambda item: item.name):
        relative = entry.relative_to(path).as_posix()
        if entry.name == MANAGED_SKILL_MARKER:
            continue
        if entry.is_symlink():
            raise OSError(f"symlinks are not supported in skill fingerprints: {entry}")
        elif entry.is_dir():
            yield relative, "directory", None
            for child in _iter_skill_entries(entry):
                yield f"{relative}/{child[0]}", child[1], child[2]
        elif entry.is_file():
            yield relative, "file", entry.read_bytes()
        else:
            raise OSError(f"unsupported filesystem entry in skill: {entry}")


def skill_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    for relative, entry_type, value in _iter_skill_entries(path):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(entry_type.encode("ascii"))
        digest.update(b"\0")
        if isinstance(value, bytes):
            digest.update(value)
        elif value is not None:
            digest.update(value.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _try_skill_fingerprint(path: Path) -> str | None:
    try:
        return skill_fingerprint(path)
    except (OSError, UnicodeError):
        return None


def _package_version() -> str:
    try:
        return version("agent-caravan")
    except PackageNotFoundError:
        return "development"


def _write_skill_marker(destination: Path, skill_id: str) -> None:
    marker = {
        "format_version": MANAGED_SKILL_FORMAT_VERSION,
        "managed_by": "agentcaravan",
        "artifact_type": "runtime-skill-installation",
        "skill_id": skill_id,
        "package_name": "agent-caravan",
        "package_version": _package_version(),
        "content_hash": skill_fingerprint(destination),
    }
    marker_path = destination / MANAGED_SKILL_MARKER
    temporary_marker = marker_path.with_name(f".{marker_path.name}.tmp")
    try:
        temporary_marker.write_text(json.dumps(marker, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary_marker, marker_path)
    finally:
        temporary_marker.unlink(missing_ok=True)


def _read_skill_marker(destination: Path, expected_skill_id: str | None = None) -> dict | None:
    marker_path = destination / MANAGED_SKILL_MARKER
    if marker_path.is_symlink() or not marker_path.is_file():
        return None
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(marker, dict):
        return None
    required = {
        "format_version": MANAGED_SKILL_FORMAT_VERSION,
        "managed_by": "agentcaravan",
        "artifact_type": "runtime-skill-installation",
        "package_name": "agent-caravan",
    }
    if any(marker.get(key) != value for key, value in required.items()):
        return None
    if not isinstance(marker.get("skill_id"), str):
        return None
    if expected_skill_id is not None and marker["skill_id"] != expected_skill_id:
        return None
    content_hash = marker.get("content_hash")
    if not isinstance(content_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", content_hash):
        return None
    return marker


def _replace_skill(source: Path, destination: Path, skill_id: str) -> None:
    parent = destination.parent
    temporary_root = Path(tempfile.mkdtemp(prefix=f".{skill_id}-", dir=parent))
    staged = temporary_root / "replacement"
    backup = parent / f".{destination.name}-backup-{temporary_root.name[1:]}"
    destination_moved = False
    try:
        shutil.copytree(source, staged)
        _write_skill_marker(staged, skill_id)
        staged_marker = _read_skill_marker(staged, skill_id)
        if staged_marker is None or staged_marker["content_hash"] != skill_fingerprint(staged):
            raise OSError("staged skill marker validation failed")
        destination.rename(backup)
        destination_moved = True
        try:
            staged.rename(destination)
        except BaseException:
            backup.rename(destination)
            raise
        shutil.rmtree(backup)
    finally:
        shutil.rmtree(temporary_root, ignore_errors=True)
        if destination_moved and backup.exists():
            shutil.rmtree(backup, ignore_errors=True)


def install_skills(
    skill_root: Path | None = None,
    *,
    runtime: str = "codex",
    confirm_replace: Callable[[str], bool],
) -> None:
    skill_root = skill_root or default_skill_root(runtime)
    skill_root.mkdir(parents=True, exist_ok=True)
    for skill_id in skill_ids_for_runtime(runtime):
        destination = skill_root / skill_id
        source = packaged_skill_path(skill_id)
        if destination.exists() or destination.is_symlink():
            if destination.is_symlink():
                if destination.resolve() == source:
                    print(f"Skill already linked: {destination}")
                else:
                    print(f"Preserving existing symlink: {destination}")
                continue

            source_hash = skill_fingerprint(source)
            destination_hash = _try_skill_fingerprint(destination)
            marker = _read_skill_marker(destination, skill_id)
            marker_path_exists = (destination / MANAGED_SKILL_MARKER).exists()
            if marker is None and not marker_path_exists and destination_hash == source_hash:
                _write_skill_marker(destination, skill_id)
                print(f"Adopted unchanged legacy skill: {destination}")
                continue
            if marker is None:
                print(f"Preserving unmanaged skill: {destination}")
                continue

            if marker.get("content_hash") != destination_hash:
                if not confirm_replace(
                    f"{destination} is a modified Agent Caravan skill. Replace it?"
                ):
                    print(f"Preserving modified skill: {destination}")
                    continue
            _replace_skill(source, destination, skill_id)
            print(f"Skill refreshed: {destination}")
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, destination)
        _write_skill_marker(destination, skill_id)
        print(f"Skill installed: {destination}")
