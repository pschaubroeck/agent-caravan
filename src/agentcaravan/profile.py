"""Load local Agent Caravan sources selected by an implementation profile."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .bundle_sources import BundleSourceError, GitCheckoutArtifactSource


class ProfileError(ValueError):
    """Raised when local profile configuration cannot be loaded safely."""


def _configured_git_source(
    profile_root: str | Path,
    configured_source: dict[str, Any],
) -> GitCheckoutArtifactSource:
    if configured_source.get("type") != "git":
        raise ProfileError("structured profile sources must have type 'git'")
    checkout_value = configured_source.get("checkout")
    if not isinstance(checkout_value, str) or not checkout_value.strip():
        raise ProfileError("Git profile sources must provide a non-empty checkout path")
    url = configured_source.get("url")
    if url is not None and (not isinstance(url, str) or not url.strip()):
        raise ProfileError("Git profile source url must be a non-empty string")
    subdirectory = configured_source.get("subdirectory", ".")
    if not isinstance(subdirectory, str) or not subdirectory:
        raise ProfileError("Git profile source subdirectory must be a non-empty string")
    checkout = Path(checkout_value).expanduser()
    if not checkout.is_absolute():
        checkout = Path(profile_root).expanduser() / checkout
    try:
        return GitCheckoutArtifactSource(
            checkout,
            url=url,
            subdirectory=subdirectory,
        )
    except BundleSourceError as exc:
        raise ProfileError(str(exc)) from exc


def resolve_source_path(
    profile_root: str | Path,
    configured_source: str | dict[str, Any],
) -> Path:
    """Resolve a configured source to its local artifact root.

    Legacy path strings may be absolute or relative to the profile. Git source
    declarations resolve their employee-local checkout and optional subtree.
    """
    if isinstance(configured_source, str):
        source = Path(configured_source).expanduser()
        if not source.is_absolute():
            source = Path(profile_root).expanduser() / source
        return source
    if isinstance(configured_source, dict):
        try:
            source, _ = _configured_git_source(profile_root, configured_source).source_path()
            return source
        except BundleSourceError as exc:
            raise ProfileError(str(exc)) from exc
    raise ProfileError("profile sources must be path strings or Git source objects")


def load_configured_source(
    profile_root: str | Path,
    configured_source: str | dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Load configured-source artifacts and return optional Git provenance."""
    if isinstance(configured_source, str):
        return load_source(resolve_source_path(profile_root, configured_source)), None
    if isinstance(configured_source, dict):
        try:
            return _configured_git_source(profile_root, configured_source).load_artifacts()
        except BundleSourceError as exc:
            raise ProfileError(str(exc)) from exc
    raise ProfileError("profile sources must be path strings or Git source objects")


def load_config(root: str | Path) -> dict[str, Any]:
    path = Path(root).expanduser() / "config.json"
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProfileError(f"profile config does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ProfileError(f"profile config is not valid JSON: {path}") from exc
    if not isinstance(config, dict) or not isinstance(config.get("sources", []), list):
        raise ProfileError("profile config must contain a sources list")
    if not isinstance(config.get("adapter_overrides", {}), dict):
        raise ProfileError("profile config adapter_overrides must be an object")
    logging_config = config.get("logging", {})
    if not isinstance(logging_config, dict):
        raise ProfileError("profile config logging must be an object")
    level = logging_config.get("level", "INFO")
    if not isinstance(level, str) or level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ProfileError("profile config logging.level must be DEBUG, INFO, WARNING, ERROR, or CRITICAL")
    output_format = logging_config.get("format", "text")
    if not isinstance(output_format, str) or output_format not in {"text", "json"}:
        raise ProfileError("profile config logging.format must be text or json")
    return config


def _read_source_file(path: Path) -> list[dict[str, Any]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ProfileError(f"cannot read configured source: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ProfileError(f"configured source is not valid JSON: {path}") from exc
    if isinstance(value, dict) and isinstance(value.get("artifacts"), list):
        return [item for item in value["artifacts"] if isinstance(item, dict)]
    if isinstance(value, dict) and isinstance(value.get("artifact_type"), str):
        return [value]
    return []


def load_source(path: str | Path) -> list[dict[str, Any]]:
    """Load artifact JSON from a file or recursively from a directory.

    Non-artifact JSON, such as catalog manifests, is intentionally ignored.
    """
    source = Path(path).expanduser()
    if source.is_file():
        return _read_source_file(source)
    if not source.is_dir():
        raise ProfileError(f"configured source does not exist: {source}")
    artifacts: list[dict[str, Any]] = []
    for file in sorted(source.rglob("*.json")):
        artifacts.extend(_read_source_file(file))
    return artifacts


def load_profile(root: str | Path) -> dict[str, Any]:
    """Return the resolver bundle represented by a local profile."""
    profile_root = Path(root).expanduser()
    config = load_config(profile_root)
    artifacts: list[dict[str, Any]] = []
    source_provenance: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for configured_source in config.get("sources", []):
        source_artifacts, provenance = load_configured_source(profile_root, configured_source)
        if provenance is not None:
            source_provenance.append(provenance)
        for artifact in source_artifacts:
            key = (artifact.get("artifact_type", ""), artifact.get("id", ""))
            if key in seen:
                raise ProfileError(f"duplicate artifact in profile sources: {key[0]}:{key[1]}")
            seen.add(key)
            artifacts.append(artifact)
    return {
        "context": config.get("active_context", {}),
        "artifacts": artifacts,
        "source_provenance": source_provenance,
        "adapter_overrides": config.get("adapter_overrides", {}),
    }


def find_organization_catalogs(root: str | Path) -> list[tuple[dict[str, Any], Path]]:
    """Find organization catalogs in configured source files."""
    profile_root = Path(root).expanduser()
    config = load_config(profile_root)
    found: list[tuple[dict[str, Any], Path]] = []
    for configured_source in config.get("sources", []):
        source = resolve_source_path(profile_root, configured_source)
        files = [source] if source.is_file() else sorted(source.rglob("*.json")) if source.is_dir() else []
        for file in files:
            for artifact in _read_source_file(file):
                if artifact.get("artifact_type") == "organization-catalog":
                    found.append((artifact, file))
    return found
