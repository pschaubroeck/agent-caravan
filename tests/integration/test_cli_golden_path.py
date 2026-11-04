import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentcaravan.cli import main as cli_main


class CliGoldenPathTests(unittest.TestCase):
    def test_source_checkout_validate_uses_repository_resources(self):
        output = io.StringIO()
        repository_root = Path(__file__).resolve().parents[2]
        with patch("agentcaravan.cli._bundled_root", return_value=repository_root), contextlib.redirect_stdout(output):
            self.assertEqual(cli_main(["validate"]), 0)
        report = json.loads(output.getvalue())
        self.assertTrue(report["valid"])
        self.assertIn("selected cross-artifact references", " ".join(report["checks_performed"]))
        self.assertIn("runtime capability compatibility (use resolve) and live runtime behavior (requires adapter-specific conformance)", report["not_checked"])
        self.assertEqual(report["coverage"]["markdown_artifact_count"], 26)
        self.assertEqual(report["coverage"]["portable_execution_plan_count"], 1)
        self.assertEqual(report["coverage"]["execution_state_template_count"], 3)
        self.assertEqual(report["coverage"]["distribution_snapshot_count"], 3)

    def test_validate_fails_when_artifact_records_lack_identity(self):
        with tempfile.TemporaryDirectory(prefix="agentcaravan-invalid-artifact-") as temporary:
            root = Path(temporary)
            (root / "catalog-manifest.json").write_text(
                json.dumps({"machine_readable_bundles": ["bundle.json"]}), encoding="utf-8"
            )
            (root / "bundle.json").write_text(
                json.dumps({"artifacts": [{"id": "missing-type", "version": "1.0.0", "scope": "shared"}]}),
                encoding="utf-8",
            )
            output = io.StringIO()
            with patch("agentcaravan.cli._bundled_root", return_value=root), patch(
                "agentcaravan.cli.all_skill_ids", return_value=[]
            ), contextlib.redirect_stdout(output):
                self.assertEqual(cli_main(["validate"]), 1)
            report = json.loads(output.getvalue())

        self.assertFalse(report["valid"])
        self.assertIn("missing a string artifact_type", report["diagnostics"][0])

    def test_status_recommends_init_when_no_team_is_selected(self):
        with tempfile.TemporaryDirectory(prefix="agentcaravan-cli-no-team-") as temporary:
            root = Path(temporary) / "profile"
            root.mkdir()
            (root / "config.json").write_text(
                json.dumps({"sources": [], "active_context": {}}) + "\n",
                encoding="utf-8",
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(cli_main(["status", "--root", str(root), "--json"]), 1)
            report = json.loads(output.getvalue())
            self.assertEqual(report["next_action"], "agent-caravan init")

    def test_source_checkout_can_add_and_switch_between_teams(self):
        with tempfile.TemporaryDirectory(prefix="agentcaravan-cli-teams-") as temporary:
            temporary_root = Path(temporary)
            profile_root = temporary_root / "profile"
            skill_root = temporary_root / "skills"

            for team_name, team_id in (
                ("Core Team", "cli-teams-core-team"),
                ("Platform Team", "cli-teams-platform-team"),
            ):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(
                        cli_main(
                            [
                                "init",
                                "--root",
                                str(profile_root),
                                "--skill-root",
                                str(skill_root),
                                "--runtime",
                                "codex",
                                "--organization",
                                "CLI Teams Organization",
                                "--team",
                                team_name,
                                "--team-id",
                                team_id,
                            ]
                        ),
                        0,
                    )

                status_output = io.StringIO()
                with contextlib.redirect_stdout(status_output):
                    self.assertEqual(cli_main(["status", "--root", str(profile_root), "--json"]), 0)
                status = json.loads(status_output.getvalue())
                self.assertEqual(status["status"], "pass")
                self.assertEqual(status["organization_id"], "cli-teams-organization")
                self.assertEqual(status["team_id"], team_id)
                self.assertEqual(status["blueprint_id"], "information-technology-core-team")

            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(
                    cli_main(
                        [
                            "init",
                            "--root",
                            str(profile_root),
                            "--skill-root",
                            str(skill_root),
                            "--runtime",
                            "codex",
                            "--organization",
                            "CLI Teams Organization",
                            "--team",
                            "Core Team",
                            "--team-id",
                            "cli-teams-core-team",
                        ]
                    ),
                    0,
                )

            status_output = io.StringIO()
            with contextlib.redirect_stdout(status_output):
                self.assertEqual(cli_main(["status", "--root", str(profile_root), "--json"]), 0)
            self.assertEqual(json.loads(status_output.getvalue())["team_id"], "cli-teams-core-team")

    def test_init_prints_artifact_inventory_for_new_team(self):
        with tempfile.TemporaryDirectory(prefix="agentcaravan-cli-artifacts-") as temporary:
            profile_root = Path(temporary) / "profile"
            skill_root = Path(temporary) / "skills"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(
                    cli_main([
                        "init",
                        "--root", str(profile_root),
                        "--skill-root", str(skill_root),
                        "--runtime", "codex",
                        "--organization", "Artifact Organization",
                        "--team", "Core Team",
                    ]),
                    0,
                )

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(
                    cli_main([
                        "init",
                        "--root", str(profile_root),
                        "--skill-root", str(skill_root),
                        "--runtime", "codex",
                        "--organization", "Artifact Organization",
                        "--team", "Platform Team",
                    ]),
                    0,
                )

            rendered = output.getvalue()
            self.assertIn("Caravan artifacts:", rendered)
            self.assertIn("organization-catalog.json", rendered)
            self.assertIn("artifact-organization-platform-team.json", rendered)
            self.assertIn("caravans/artifact-organization-platform-team", rendered)
            self.assertIn("caravan.md, repositories.md, knowledge.md, working-agreements.md, instructions.md, responsibilities.md", rendered)

    def test_init_reuses_existing_custom_team_id_when_selected_by_name(self):
        with tempfile.TemporaryDirectory(prefix="agentcaravan-cli-team-selection-") as temporary:
            profile_root = Path(temporary) / "profile"
            skill_root = Path(temporary) / "skills"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(
                    cli_main([
                        "init", "--root", str(profile_root), "--skill-root", str(skill_root),
                        "--runtime", "codex", "--organization", "Selection Organization",
                        "--team", "Platform Team", "--team-id", "platform-team-stable",
                    ]),
                    0,
                )

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(
                    cli_main([
                        "init", "--root", str(profile_root), "--skill-root", str(skill_root),
                        "--runtime", "codex", "--organization", "Selection Organization",
                        "--team", "Platform Team",
                    ]),
                    0,
                )

            status_output = io.StringIO()
            with contextlib.redirect_stdout(status_output):
                self.assertEqual(cli_main(["status", "--root", str(profile_root), "--json"]), 0)
            self.assertEqual(json.loads(status_output.getvalue())["team_id"], "platform-team-stable")
            self.assertIn("Caravan already configured", output.getvalue())

    def test_source_checkout_cli_golden_path(self):
        with tempfile.TemporaryDirectory(prefix="agentcaravan-cli-smoke-") as temporary:
            temporary_root = Path(temporary)
            profile_root = temporary_root / "profile"
            skill_root = temporary_root / "skills"
            sessions_root = temporary_root / "sessions"

            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(
                    cli_main(
                        [
                            "init",
                            "--root",
                            str(profile_root),
                            "--skill-root",
                            str(skill_root),
                            "--runtime",
                            "codex",
                            "--organization",
                            "CLI Smoke Organization",
                            "--team",
                            "CLI Smoke Team",
                            "--team-id",
                            "cli-smoke-team",
                        ]
                    ),
                    0,
                )

            before_configure = io.StringIO()
            with contextlib.redirect_stdout(before_configure):
                self.assertEqual(cli_main(["status", "--root", str(profile_root), "--json"]), 0)
            self.assertEqual(json.loads(before_configure.getvalue())["configuration"]["status"], "not-configured")

            with patch(
                "builtins.input",
                side_effect=[
                    "Support CLI smoke validation.",
                    "agent-caravan",
                    "docs/getting-started.md",
                    "Prefer focused tests before review.",
                    "",
                ],
            ), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli_main(["configure", "--root", str(profile_root)]), 0)

            status_output = io.StringIO()
            with contextlib.redirect_stdout(status_output):
                self.assertEqual(cli_main(["status", "--root", str(profile_root), "--json"]), 0)
            status = json.loads(status_output.getvalue())
            self.assertEqual(status["status"], "pass")
            self.assertEqual(status["configuration"]["status"], "configured")
            self.assertEqual(status["configuration"]["work_surfaces"], ["agent-caravan"])
            self.assertEqual(status["configuration"]["knowledge_sources"], ["docs/getting-started.md"])
            self.assertIn(
                f"agent-caravan run --root {profile_root} --dry-run",
                status["next_action"],
            )

            run_output = io.StringIO()
            with contextlib.redirect_stdout(run_output):
                self.assertEqual(
                    cli_main(
                        [
                            "run",
                            "--root",
                            str(profile_root),
                            "--sessions-root",
                            str(sessions_root),
                            "--task-id",
                            "cli-smoke-task",
                            "--objective",
                            "Validate the CLI golden path",
                            "--dry-run",
                        ]
                    ),
                    0,
                )
            summary = json.loads(run_output.getvalue())
            self.assertEqual(summary["status"], "completed")
            self.assertEqual(summary["execution_realization"]["mode"], "simulated-sequential")
            self.assertEqual(summary["active_roles"], ["engineer"])
            self.assertTrue(summary["session_validation"]["valid"])

            validation_output = io.StringIO()
            with contextlib.redirect_stdout(validation_output):
                self.assertEqual(
                    cli_main(
                        [
                            "validate-session",
                            "--root",
                            str(profile_root),
                            "--sessions-root",
                            str(sessions_root),
                            "--task-id",
                            "cli-smoke-task",
                        ]
                    ),
                    0,
                )
            validation = json.loads(validation_output.getvalue())
            self.assertTrue(validation["valid"])
            self.assertEqual(validation["completion_status"], "completed")
            self.assertEqual(validation["issues"], [])


if __name__ == "__main__":
    unittest.main()
