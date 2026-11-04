"""Repository-local validation and framework execution commands."""

from __future__ import annotations

import argparse
import compileall
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from . import resolve_framework


ROOT = Path(__file__).parents[2]


def manifest() -> int:
    """Validate the catalog manifest and referenced paths."""
    manifest_path = ROOT / "catalog-manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    for path in payload["artifact_roots"].values():
        if not (ROOT / path).is_dir():
            raise FileNotFoundError(ROOT / path)
    for key in (
        "specifications",
        "runtime_adapter_docs",
        "machine_readable_bundles",
        "execution_workflows",
        "policy_artifacts",
        "schemas",
        "execution_state_templates",
        "examples",
    ):
        for path in payload[key]:
            if not (ROOT / path).is_file():
                raise FileNotFoundError(ROOT / path)
    for key in ("conformance_scenarios", "vocabulary", "local_profile"):
        if not (ROOT / payload[key]).is_file():
            raise FileNotFoundError(ROOT / payload[key])
    return 0


def compile_sources() -> int:
    """Compile Python sources without writing bytecode into the repository."""
    return 0 if compileall.compile_dir(str(ROOT / "src"), quiet=1) and compileall.compile_dir(str(ROOT / "tools"), quiet=1) else 1


def tests() -> int:
    """Run source-checkout unit and integration tests."""
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


def cli_smoke() -> int:
    """Run the source-checkout CLI golden-path integration test."""
    suite = unittest.defaultTestLoader.discover(
        str(ROOT / "tests" / "integration"),
        pattern="test_cli_golden_path.py",
        top_level_dir=str(ROOT),
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


def package_smoke() -> int:
    """Build and test the wheel in an isolated offline environment."""
    if sys.version_info < (3, 10):
        print("package-smoke requires Python 3.10 or newer.", file=sys.stderr)
        return 2
    try:
        __import__("setuptools")
        __import__("setuptools_scm")
        __import__("wheel")
    except ImportError:
        print(
            "package-smoke requires setuptools, setuptools-scm, and wheel in the active environment; "
            "install the pinned build requirements first.",
            file=sys.stderr,
        )
        return 2

    with tempfile.TemporaryDirectory(prefix="agentcaravan-package-smoke-") as temporary_root:
        temporary_root_path = Path(temporary_root)
        source_copy = temporary_root_path / "source"
        wheel_dir = temporary_root_path / "wheels"
        install_dir = temporary_root_path / "install"
        ignored = shutil.ignore_patterns(
            ".git", "build", "dist", "agent_caravan.egg-info", "__pycache__", "*.pyc", ".pytest_cache"
        )
        shutil.copytree(ROOT, source_copy, ignore=ignored)
        wheel_dir.mkdir()

        build = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "wheel",
                "--no-index",
                "--no-deps",
                "--no-build-isolation",
                str(source_copy),
                "--wheel-dir",
                str(wheel_dir),
            ],
            check=False,
        )
        if build.returncode != 0:
            return build.returncode

        wheels = sorted(wheel_dir.glob("agent_caravan-*.whl"))
        if len(wheels) != 1:
            print(f"Expected exactly one Agent Caravan wheel, found {len(wheels)}.", file=sys.stderr)
            return 1

        install_dir.mkdir()
        install = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--no-index",
                "--no-deps",
                "--target",
                str(install_dir),
                str(wheels[0]),
            ],
            check=False,
        )
        if install.returncode != 0:
            return install.returncode

        test_environment = os.environ.copy()
        test_environment["PYTHONPATH"] = str(install_dir)
        test = subprocess.run(
            [
                sys.executable,
                "-m",
                "unittest",
                "package_tests.test_package_distribution",
                "-v",
            ],
            cwd=ROOT,
            env=test_environment,
            check=False,
        )
        return test.returncode


def resolve_example() -> int:
    """Resolve the checked-in representative framework configuration."""
    fixture = ROOT / "tests/fixtures/sample-product-engineer-ii.json"
    return resolve_framework.main(["agentcaravan.scripts resolve-example", str(fixture)])


def resolve_active_profile() -> int:
    """Resolve the active local organization profile."""
    return resolve_framework.main([
        "agentcaravan.scripts resolve",
        "--profile",
        str(Path.home() / ".agents/agent-caravan"),
    ])


def validate() -> int:
    """Run the complete repository-local validation sequence."""
    for command in (manifest, compile_sources, tests, resolve_example):
        if command() != 0:
            return 1
    return 0


COMMANDS = {
    "manifest": manifest,
    "compile": compile_sources,
    "tests": tests,
    "cli-smoke": cli_smoke,
    "package-smoke": package_smoke,
    "resolve": resolve_active_profile,
    "resolve-example": resolve_example,
    "validate": validate,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m agentcaravan.scripts")
    parser.add_argument("command", choices=COMMANDS)
    args = parser.parse_args(argv)
    return COMMANDS[args.command]()


if __name__ == "__main__":
    raise SystemExit(main())
