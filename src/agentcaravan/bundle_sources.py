"""Storage-neutral sources for normalized framework artifact bundles."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Protocol


class BundleSourceError(Exception):
    """Raised when a bundle source cannot provide a valid bundle."""


class BundleSource(Protocol):
    """Logical source contract used by the resolver entry point."""

    def load(self) -> dict[str, Any]:
        """Load and return one normalized artifact bundle."""


def _validate_bundle_shape(bundle: Any) -> dict[str, Any]:
    if not isinstance(bundle, dict):
        raise BundleSourceError("bundle source must return a JSON object")
    if not isinstance(bundle.get("context"), dict):
        raise BundleSourceError("bundle source must provide a context object")
    if not isinstance(bundle.get("artifacts"), list):
        raise BundleSourceError("bundle source must provide an artifacts list")
    return bundle


class LocalJsonBundleSource:
    """Load one normalized bundle from a local JSON file."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> dict[str, Any]:
        if not self.path.is_file():
            raise BundleSourceError(f"bundle file does not exist: {self.path}")
        try:
            bundle = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise BundleSourceError(f"bundle file is not valid JSON: {self.path}") from exc
        return _validate_bundle_shape(bundle)


class InMemoryBundleSource:
    """Provide a bundle directly for tests and embedding applications."""

    def __init__(self, bundle: dict[str, Any]):
        self.bundle = bundle

    def load(self) -> dict[str, Any]:
        return _validate_bundle_shape(self.bundle)


class GitCheckoutArtifactSource:
    """Load artifact JSON from a local Git checkout without fetching it.

    ``url`` is optional shared-source identity metadata. ``checkout`` is the
    employee-local checkout location, and ``subdirectory`` selects the
    artifact tree within it. Files are read from the current working tree;
    provenance records HEAD and whether the checkout has local modifications.
    """

    def __init__(
        self,
        checkout: str | Path,
        *,
        url: str | None = None,
        subdirectory: str | Path = ".",
    ):
        self.checkout = Path(checkout).expanduser()
        self.url = url
        self.subdirectory = Path(subdirectory)
        if self.subdirectory.is_absolute() or ".." in self.subdirectory.parts:
            raise BundleSourceError("Git source subdirectory must stay inside the checkout")

    def source_path(self) -> tuple[Path, dict[str, Any]]:
        checkout = self.checkout.resolve()
        if not checkout.is_dir():
            raise BundleSourceError(f"Git source checkout does not exist: {checkout}")
        try:
            revision = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=checkout,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            git_root = Path(revision).resolve()
            commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=checkout,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=checkout,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
        except (OSError, subprocess.CalledProcessError) as exc:
            raise BundleSourceError(f"Git source is not a readable Git checkout: {checkout}") from exc

        source_root = (checkout / self.subdirectory).resolve()
        if source_root != git_root and git_root not in source_root.parents:
            raise BundleSourceError("Git source subdirectory must stay inside the checkout")
        if not source_root.exists():
            raise BundleSourceError(f"Git source subdirectory does not exist: {source_root}")

        return source_root, {
            "type": "git",
            "url": self.url,
            "checkout": str(checkout),
            "subdirectory": str(self.subdirectory),
            "revision": commit,
            "dirty": bool(status.strip()),
        }

    def load_artifacts(self) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        source_root, provenance = self.source_path()

        # Reuse profile's JSON artifact loader without making bundle_sources
        # depend on profile's public API.
        artifacts: list[dict[str, Any]] = []
        files = [source_root] if source_root.is_file() else sorted(source_root.rglob("*.json"))
        for file in files:
            try:
                value = json.loads(file.read_text(encoding="utf-8"))
            except OSError as exc:
                raise BundleSourceError(f"cannot read Git source artifact file: {file}") from exc
            except json.JSONDecodeError as exc:
                raise BundleSourceError(f"Git source artifact file is not valid JSON: {file}") from exc
            if isinstance(value, dict) and isinstance(value.get("artifacts"), list):
                artifacts.extend(item for item in value["artifacts"] if isinstance(item, dict))
            elif isinstance(value, dict) and isinstance(value.get("artifact_type"), str):
                artifacts.append(value)

        return artifacts, provenance
