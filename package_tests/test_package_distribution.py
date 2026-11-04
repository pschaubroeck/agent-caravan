import importlib
import contextlib
from importlib.metadata import PackageNotFoundError
from importlib.metadata import metadata as distribution_metadata
from importlib.metadata import version as distribution_version
from importlib.resources import files
import json
import tempfile
import unittest
import io
from pathlib import Path
from unittest.mock import patch

from agentcaravan.cli import init as initialize
from agentcaravan.cli import main as cli_main
from agentcaravan.resolve_framework import resolve_profile
from agentcaravan.schema_validation import validate_packaged_artifact


class PackageDistributionTests(unittest.TestCase):
    def test_installed_distribution_bootstraps_opencode_with_its_runtime_and_skills(self):
        bundled = files("agentcaravan").joinpath("_bundled")
        if not bundled.is_dir():
            self.skipTest("bundled resources are only present in the installed distribution")

        self.assertTrue(bundled.joinpath("resources/runtime/agentcaravan-opencode-runtime.json").is_file())
        with tempfile.TemporaryDirectory(prefix="agentcaravan-opencode-package-") as directory:
            root = Path(directory) / "profile"
            skill_root = Path(directory) / "skills"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli_main([
                    "init", "--runtime", "opencode", "--root", str(root),
                    "--skill-root", str(skill_root), "--organization", "Package Organization",
                    "--team", "OpenCode Team",
                ]), 0)
            resolved = resolve_profile(root)
            self.assertEqual(resolved["status"], "degraded")
            self.assertEqual(resolved["context"]["runtime_adapter_id"], "opencode-agent-runtime")
            self.assertEqual(resolved["context"]["runtime_profile_id"], "opencode-information-technology-core-team")
            self.assertEqual(len(list(skill_root.iterdir())), 5)
            self.assertTrue((skill_root / "agent-caravan-opencode-orchestrator" / "SKILL.md").is_file())
            self.assertFalse((skill_root / "agent-caravan-codex-orchestrator").exists())
            status = io.StringIO()
            with contextlib.redirect_stdout(status):
                self.assertEqual(cli_main(["status", "--root", str(root), "--json"]), 0)
            self.assertEqual(json.loads(status.getvalue())["skills"]["runtime"], "opencode")
            self.assertEqual(json.loads(status.getvalue())["skills"]["status"], "installed")

    def test_installed_distribution_bootstraps_kiro_ide_with_native_skill(self):
        bundled = files("agentcaravan").joinpath("_bundled")
        if not bundled.is_dir():
            self.skipTest("bundled resources are only present in the installed distribution")

        self.assertTrue(bundled.joinpath("resources/runtime/agentcaravan-kiro-runtime.json").is_file())
        with tempfile.TemporaryDirectory(prefix="agentcaravan-kiro-package-") as directory:
            root = Path(directory) / "profile"
            skill_root = Path(directory) / "skills"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli_main([
                    "init", "--runtime", "kiro", "--root", str(root),
                    "--skill-root", str(skill_root), "--organization", "Package Organization",
                    "--team", "Kiro IDE Team",
                ]), 0)
            resolved = resolve_profile(root)
            self.assertEqual(resolved["status"], "degraded")
            self.assertEqual(resolved["context"]["runtime_adapter_id"], "kiro-ide-agent-runtime")
            self.assertEqual(resolved["context"]["runtime_profile_id"], "kiro-ide-information-technology-core-team")
            self.assertEqual(len(list(skill_root.iterdir())), 5)
            self.assertTrue((skill_root / "agent-caravan-kiro-orchestrator" / "SKILL.md").is_file())
            self.assertFalse((skill_root / "agent-caravan-codex-orchestrator").exists())
            status = io.StringIO()
            with contextlib.redirect_stdout(status):
                self.assertEqual(cli_main(["status", "--root", str(root), "--json"]), 0)
            self.assertEqual(json.loads(status.getvalue())["skills"]["runtime"], "kiro")
            self.assertEqual(json.loads(status.getvalue())["skills"]["status"], "installed")

    def test_installed_distribution_bundles_schemas_for_package_validation(self):
        bundled = files("agentcaravan").joinpath("_bundled", "resources")
        schemas = bundled.joinpath("schemas")
        if not schemas.is_dir():
            self.skipTest("bundled schemas are only present in the installed distribution")

        schema_files = list(schemas.glob("*.schema.json"))
        manifest = json.loads(
            files("agentcaravan").joinpath("_bundled", "catalog-manifest.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(
            {path.name for path in schema_files},
            {Path(path).name for path in manifest["schemas"]},
        )
        artifact = json.loads(
            bundled.joinpath(
                "execution",
                "workflows",
                "information-technology-core-team-feature-delivery.json",
            ).read_text(encoding="utf-8")
        )
        validate_packaged_artifact(artifact, "execution-profile.schema.json")

    def test_installed_distribution_metadata_version_and_public_imports(self):
        try:
            package_metadata = distribution_metadata("agent-caravan")
            installed_version = distribution_version("agent-caravan")
        except PackageNotFoundError:
            self.skipTest("agentcaravan distribution is not installed in this checkout")

        self.assertEqual(package_metadata["Name"], "agent-caravan")
        self.assertEqual(package_metadata["Version"], installed_version)
        self.assertTrue(installed_version.strip())
        self.assertIsNotNone(importlib.import_module("agentcaravan"))
        self.assertIsNotNone(importlib.import_module("agentcaravan.resolve_framework"))
        self.assertIsNotNone(importlib.import_module("agentcaravan.foundation"))
        self.assertIsNotNone(importlib.import_module("agentcaravan.adapters.codex"))
        self.assertIsNotNone(importlib.import_module("agentcaravan.bootstrap"))

    def test_installed_distribution_bootstraps_and_resolves_packaged_defaults(self):
        bundled = files("agentcaravan").joinpath("_bundled", "resources")
        if not bundled.is_dir():
            self.skipTest("bundled resources are only present in the installed distribution")

        self.assertEqual(cli_main(["validate"]), 0)

        with tempfile.TemporaryDirectory(prefix="agentcaravan-profile-test-") as temporary_root:
            root = Path(temporary_root)
            args = type(
                "Args",
                (),
                {
                    "root": root,
                    "runtime": "none",
                    "organization": "Package Test Organization",
                    "team": None,
                    "ownership_boundary": None,
                    "skill_root": None,
                },
            )()
            with patch("builtins.input", return_value="Package Test Organization"):
                initialize(args)

            organization_root = root / "sources" / "package-test-organization"
            team = {
                "artifact_type": "team-instance",
                "id": "package-test-organization-core-team",
                "version": "1.0.0",
                "scope": "organization",
                "name": "Package Test Core Team",
                "team_blueprint_id": "information-technology-core-team",
                "role_overlays": [],
                "domain_packs": [],
                "specialization_packs": [],
                "runtime_defaults": ["codex-desktop-agent-runtime"],
                "execution_profile_id": "information-technology-core-team-feature-delivery",
            }
            (organization_root / "team-instance.json").write_text(json.dumps(team) + "\n", encoding="utf-8")

            catalog_path = organization_root / "organization-catalog.json"
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            catalog["published_artifacts"]["team-instance"].append(team["id"])
            catalog_path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")

            config_path = root / "config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["active_context"].update(
                {
                    "team_instance_id": team["id"],
                    "runtime_adapter_id": "codex-desktop-agent-runtime",
                    "runtime_profile_id": "codex-desktop-information-technology-core-team",
                    "execution_profile_id": "information-technology-core-team-feature-delivery",
                }
            )
            config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

            result = resolve_profile(root)

            self.assertEqual(result["status"], "pass")
            self.assertEqual(result["context"]["organization_catalog_id"], "package-test-organization")
            self.assertEqual(result["context"]["team_instance_id"], team["id"])
            self.assertEqual(result["context"]["execution_profile_id"], "information-technology-core-team-feature-delivery")
            self.assertEqual(
                result["policies"][0]["id"],
                "information-technology-core-team-safety-policy",
            )
            self.assertTrue(result["execution_profile"]["evidence_requirements"])

    def test_installed_distribution_runs_real_init_resolve_and_dry_run_path(self):
        bundled = files("agentcaravan").joinpath("_bundled", "resources")
        if not bundled.is_dir():
            self.skipTest("bundled resources are only present in the installed distribution")

        with tempfile.TemporaryDirectory(prefix="agentcaravan-golden-path-") as temporary_root:
            root = Path(temporary_root)
            skill_root = root / "skills"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli_main([
                    "init",
                    "--root", str(root),
                    "--skill-root", str(skill_root),
                    "--organization", "Golden Path Organization",
                    "--team", "Platform Team",
                    "--runtime", "codex",
                ]), 0)

            self.assertTrue((skill_root / "agent-caravan-codex-orchestrator").is_dir())
            resolved = resolve_profile(root)
            self.assertEqual(resolved["status"], "pass")
            self.assertEqual(
                resolved["context"]["organization_catalog_id"],
                "golden-path-organization",
            )
            self.assertEqual(
                resolved["context"]["team_instance_id"],
                "golden-path-organization-platform-team",
            )
            self.assertEqual(
                resolved["context"]["execution_profile_id"],
                "information-technology-core-team-basic-work",
            )
            team_sources = list((root / "sources" / "golden-path-organization").glob("*.json"))
            team = next(
                json.loads(path.read_text(encoding="utf-8"))
                for path in team_sources
                if json.loads(path.read_text(encoding="utf-8")).get("artifact_type") == "team-instance"
            )
            self.assertNotIn("ownership_boundary", team)

            with patch(
                "builtins.input",
                side_effect=[
                    "Own platform delivery and service reliability.",
                    "platform-api",
                    "repo-local README",
                    "Focused tests before review.",
                    "",
                ],
            ), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli_main(["configure", "--root", str(root)]), 0)
            self.assertTrue(
                (root / "caravans" / "golden-path-organization-platform-team" / "caravan.md").is_file()
            )
            status_after_configure = io.StringIO()
            with contextlib.redirect_stdout(status_after_configure):
                self.assertEqual(cli_main(["status", "--root", str(root), "--json"]), 0)
            self.assertEqual(
                json.loads(status_after_configure.getvalue())["configuration"]["status"],
                "configured",
            )
            resolved_after_configure = resolve_profile(root)
            self.assertEqual(
                resolved_after_configure["team_context"]["work_surfaces"],
                ["platform-api"],
            )
            workspace = root / "caravans" / "golden-path-organization-platform-team"
            (workspace / "repositories.md").write_text(
                "# Platform Team Work Surfaces\n\n- platform-api\n- platform-cli\n",
                encoding="utf-8",
            )
            resolved_after_edit = resolve_profile(root)
            self.assertEqual(
                resolved_after_edit["team_context"]["work_surfaces"],
                ["platform-api", "platform-cli"],
            )
            (workspace / "instructions.md").write_text(
                "# Platform Team AI Instructions\n\nPrefer small, verifiable changes.\n",
                encoding="utf-8",
            )
            (workspace / "responsibilities.md").write_text(
                "# Platform Team Role Guidance\n\n## Preferred roles\n\n- engineer\n- quality-engineer\n\n"
                "## Participation guidance\n\nEngineering leads implementation.\n",
                encoding="utf-8",
            )
            resolved_after_guidance = resolve_profile(root)
            self.assertEqual(
                resolved_after_guidance["team_context"]["preferred_roles"],
                ["engineer", "quality-engineer"],
            )
            self.assertEqual(
                resolved_after_guidance["team_context"]["instructions"],
                "Prefer small, verifiable changes.",
            )

            run_output = io.StringIO()
            with contextlib.redirect_stdout(run_output):
                self.assertEqual(cli_main([
                    "run",
                    "--root", str(root),
                    "--task-id", "golden-path-task",
                    "--objective", "Exercise the installed package golden path",
                    "--dry-run",
                ]), 0)
            summary = json.loads(run_output.getvalue())
            self.assertEqual(summary["status"], "completed")
            self.assertEqual(summary["task_id"], "golden-path-task")

            session_root = root / "sessions" / "golden-path-task"
            task = json.loads((session_root / "task.json").read_text(encoding="utf-8"))
            session = json.loads((session_root / "session.json").read_text(encoding="utf-8"))
            run = json.loads((session_root / "runs" / "golden-path-task-codex-run-1.json").read_text(encoding="utf-8"))
            completion = json.loads((session_root / "completion.json").read_text(encoding="utf-8"))
            self.assertEqual(task["task_id"], "golden-path-task")
            self.assertEqual(task["status"], "completed")
            self.assertEqual(session["task_id"], "golden-path-task")
            self.assertEqual(session["status"], "completed")
            self.assertEqual(run["task_id"], "golden-path-task")
            self.assertEqual(run["status"], "completed")
            self.assertEqual(completion["artifact_type"], "normalized-execution-result")
            self.assertEqual(completion["task_id"], "golden-path-task")
            self.assertEqual(completion["status"], "completed")

    def test_guided_init_uses_defaults_and_previews_before_writing(self):
        bundled = files("agentcaravan").joinpath("_bundled", "resources")
        if not bundled.is_dir():
            self.skipTest("bundled resources are only present in the installed distribution")

        with tempfile.TemporaryDirectory(prefix="agentcaravan-guided-init-") as temporary_root:
            root = Path(temporary_root) / "profile"
            skill_root = Path(temporary_root) / "skills"
            output = io.StringIO()
            with patch("builtins.input", side_effect=["", "", ""]), contextlib.redirect_stdout(output):
                self.assertEqual(cli_main([
                    "init",
                    "--root", str(root),
                    "--skill-root", str(skill_root),
                ]), 0)

            rendered = output.getvalue()
            self.assertIn("Organization: My Organization", rendered)
            self.assertIn("Caravan: My Team", rendered)
            self.assertIn("Caravan template: Information Technology Core Team", rendered)
            self.assertIn("Runtime: Codex", rendered)
            self.assertIn("Ownership scope: Not configured", rendered)
            self.assertIn("Setup complete.", rendered)
            self.assertIn("Status: Valid", rendered)
            self.assertIn("agent-caravan run", rendered)
            self.assertIn("Caravan artifacts:", rendered)
            self.assertIn("Caravan:", rendered)
            self.assertIn("Caravan workspace:", rendered)
            self.assertIn("caravan.md, repositories.md, knowledge.md", rendered)
            self.assertEqual(
                resolve_profile(root)["context"]["organization_catalog_id"],
                "my-organization",
            )
            self.assertEqual(
                resolve_profile(root)["context"]["team_instance_id"],
                "my-organization-my-team",
            )

            status_output = io.StringIO()
            with contextlib.redirect_stdout(status_output):
                self.assertEqual(cli_main(["status", "--root", str(root)]), 0)
            self.assertIn("Profile status: Pass", status_output.getvalue())
            self.assertIn("Next step:", status_output.getvalue())

            status_json = io.StringIO()
            with contextlib.redirect_stdout(status_json):
                self.assertEqual(cli_main(["status", "--root", str(root), "--json"]), 0)
            report = json.loads(status_json.getvalue())
            self.assertEqual(report["status"], "pass")
            self.assertEqual(report["organization_id"], "my-organization")
            self.assertEqual(report["team_id"], "my-organization-my-team")
            self.assertEqual(report["skills"]["status"], "installed")
            self.assertEqual(report["skills"]["root"], str(skill_root))
            self.assertIn(
                f"agent-caravan run --root {root} --dry-run",
                report["next_action"],
            )

    def test_status_reports_missing_profile_actionably(self):
        with tempfile.TemporaryDirectory(prefix="agentcaravan-status-missing-") as temporary_root:
            root = Path(temporary_root) / "profile"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(cli_main(["status", "--root", str(root)]), 1)

            rendered = output.getvalue()
            self.assertIn("Profile status: Incomplete", rendered)
            self.assertIn("agent-caravan init", rendered)

    def test_guided_init_can_be_cancelled_before_profile_creation(self):
        bundled = files("agentcaravan").joinpath("_bundled", "resources")
        if not bundled.is_dir():
            self.skipTest("bundled resources are only present in the installed distribution")

        with tempfile.TemporaryDirectory(prefix="agentcaravan-guided-cancel-") as temporary_root:
            root = Path(temporary_root) / "profile"
            with patch("builtins.input", side_effect=["", "", "n"]), self.assertRaises(SystemExit):
                cli_main(["init", "--root", str(root)])

            self.assertFalse(root.exists())


if __name__ == "__main__":
    unittest.main()
