"""Package-resource bundling for distribution builds."""

import json
import shutil
from pathlib import Path

from setuptools.command.build_py import build_py
from setuptools import setup


ROOT = Path(__file__).resolve().parent
SKILL_MANIFEST_PATH = Path("skills/skill-distribution.json")
SKILL_MANIFEST = json.loads((ROOT / SKILL_MANIFEST_PATH).read_text(encoding="utf-8"))
SKILL_PATHS = tuple(Path(skill["path"]) for skill in SKILL_MANIFEST["skills"])
if any(
    path.is_absolute() or len(path.parts) != 2 or path.parts[0] != "skills" or ".." in path.parts
    for path in SKILL_PATHS
) or len(SKILL_PATHS) != len(set(SKILL_PATHS)):
    raise RuntimeError("skill distribution manifest contains invalid or duplicate paths")
BUNDLED_PATHS = (
    SKILL_MANIFEST_PATH,
    Path("resources/schemas"),
    Path("resources/core/agentcaravan-core-team.json"),
    Path("resources/runtime/agentcaravan-codex-runtime.json"),
    Path("resources/runtime/agentcaravan-opencode-runtime.json"),
    Path("resources/runtime/agentcaravan-kiro-runtime.json"),
    Path("resources/execution/workflows/information-technology-core-team-basic-work.json"),
    Path("resources/execution/workflows/information-technology-core-team-feature-delivery.json"),
    Path("resources/execution/policies/information-technology-core-team-safety-policy.json"),
    *SKILL_PATHS,
)


def distribution_manifest() -> dict:
    """Describe only the framework resources shipped inside the wheel."""
    bundled_json = [path.as_posix() for path in BUNDLED_PATHS if path.suffix == ".json"]
    return {
        "manifest_type": "agentfoundry-distribution-catalog",
        "id": "agentfoundry-python-distribution",
        "machine_readable_bundles": [
            path for path in bundled_json
            if path.startswith(("resources/core/", "resources/runtime/"))
        ],
        "machine_readable_artifacts": [],
        "machine_readable_roots": [],
        "distribution_snapshot_pairs": [],
        "markdown_artifact_roots": [],
        "markdown_artifact_documents": [],
        "execution_workflows": [
            path for path in bundled_json if path.startswith("resources/execution/workflows/")
        ],
        "policy_artifacts": [
            path for path in bundled_json if path.startswith("resources/execution/policies/")
        ],
        "schemas": [
            path.relative_to(ROOT).as_posix()
            for path in sorted((ROOT / "resources/schemas").glob("*.schema.json"))
        ],
        "portable_execution_plan_examples": [],
        "execution_state_templates": [],
    }


class build_py_with_agentcaravan_resources(build_py):
    """Bundle the distributable framework defaults into the installed package."""

    def run(self):
        super().run()
        target_root = Path(self.build_lib) / "agentcaravan" / "_bundled"
        for relative_path in BUNDLED_PATHS:
            source = ROOT / relative_path
            destination = target_root / relative_path
            if source.is_dir():
                shutil.copytree(source, destination, dirs_exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
        manifest_path = target_root / "catalog-manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(distribution_manifest(), indent=2) + "\n",
            encoding="utf-8",
        )


setup(cmdclass={"build_py": build_py_with_agentcaravan_resources})
