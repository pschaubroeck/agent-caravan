import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentcaravan.cli import _prompt_with_default, _prompt_yes_no, main
from agentcaravan.org_framework_layout import bootstrap
from agentcaravan.team_configuration import load_team_context, render_team_documents, team_workspace


class CliConfigureTests(unittest.TestCase):
    def test_team_context_preserves_content_after_starter_placeholders(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "team"
            context = {
                "mission": "Support platform delivery.",
                "work_surfaces": [],
                "knowledge_sources": [],
                "working_agreements": "",
                "instructions": "",
                "preferred_roles": [],
                "role_guidance": "",
            }
            workspace.mkdir()
            for filename, content in render_team_documents("Platform Team", context).items():
                (workspace / filename).write_text(content, encoding="utf-8")
            (workspace / "working-agreements.md").write_text(
                (workspace / "working-agreements.md").read_text(encoding="utf-8")
                + "\n- Prefer focused tests before review.\n",
                encoding="utf-8",
            )
            (workspace / "instructions.md").write_text(
                (workspace / "instructions.md").read_text(encoding="utf-8")
                + "\nInspect repository guidance before editing.\n",
                encoding="utf-8",
            )
            (workspace / "responsibilities.md").write_text(
                (workspace / "responsibilities.md").read_text(encoding="utf-8")
                + "\nPrefer quality-engineer for focused verification.\n",
                encoding="utf-8",
            )

            loaded = load_team_context(workspace)

            self.assertEqual(loaded["working_agreements"], "- Prefer focused tests before review.")
            self.assertEqual(loaded["instructions"], "Inspect repository guidance before editing.")
            self.assertEqual(loaded["role_guidance"], "Prefer quality-engineer for focused verification.")
    def test_configure_creates_runtime_neutral_team_workspace_and_context(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bootstrap(root)
            source = root / "sources" / "example-organization"
            source.mkdir(parents=True)
            team_id = "example-organization-platform-team"
            (source / f"{team_id}.json").write_text(
                json.dumps({
                    "artifact_type": "team-instance",
                    "id": team_id,
                    "name": "Platform Team",
                    "team_blueprint_id": "information-technology-core-team",
                    "team_context": {},
                }) + "\n",
                encoding="utf-8",
            )
            (root / "config.json").write_text(json.dumps({
                "sources": [str(source)],
                "active_context": {"team_instance_id": team_id},
            }) + "\n", encoding="utf-8")

            output = io.StringIO()
            with patch("agentcaravan.cli.load_profile", return_value={"artifacts": [{
                "artifact_type": "team-instance",
                "id": team_id,
                "name": "Platform Team",
                "team_context": {},
            }]}), patch("agentcaravan.cli.resolve_profile", return_value={"status": "pass"}), patch(
                "builtins.input",
                side_effect=[
                    "Own platform delivery and service reliability.",
                    "platform-api, platform-infrastructure, /Users/alex/workspace/platform-api",
                    "https://docs.example.test/platform, repo-local README",
                    "Require focused tests before review.",
                    "",
                ],
            ), contextlib.redirect_stdout(output):
                exit_code = main(["configure", "--root", str(root)])

            self.assertEqual(exit_code, 0)
            workspace = root / "caravans" / "example-organization-platform-team"
            self.assertEqual(
                sorted(path.name for path in workspace.iterdir()),
                [
                    "caravan.md",
                    "instructions.md",
                    "knowledge.md",
                    "repositories.md",
                    "responsibilities.md",
                    "working-agreements.md",
                ],
            )
            self.assertNotIn("Codex", "".join(path.read_text(encoding="utf-8") for path in workspace.iterdir()))

            team_path = source / f"{team_id}.json"
            team = json.loads(team_path.read_text(encoding="utf-8"))
            self.assertEqual(team["team_context"]["work_surfaces"], ["platform-api", "platform-infrastructure"])
            self.assertIn(
                "/Users/alex/workspace/platform-api",
                (workspace / "repositories.md").read_text(encoding="utf-8"),
            )
            self.assertEqual(
                team["team_context"]["knowledge_sources"],
                ["https://docs.example.test/platform", "repo-local README"],
            )

            self.assertIn("Own platform delivery and service reliability.", (workspace / "caravan.md").read_text(encoding="utf-8"))
            self.assertIn("Setup: press Enter to accept defaults or skip optional fields.", output.getvalue())
            self.assertNotIn("[Enter", output.getvalue())
            self.assertNotIn("[]:", output.getvalue())

            (workspace / "caravan.md").write_text(
                "# Platform Team\n\n## Mission\n\nManually customized mission.\n\n## Notes\n\nKeep this heading.\n",
                encoding="utf-8",
            )
            (workspace / "instructions.md").write_text(
                "# Platform Team AI Instructions\n\nKeep the existing AI instructions.\n",
                encoding="utf-8",
            )
            (workspace / "responsibilities.md").write_text(
                "# Platform Team Role Guidance\n\n## Preferred roles\n\n- engineer\n\n"
                "## Participation guidance\n\nKeep the existing role guidance.\n",
                encoding="utf-8",
            )
            with patch("agentcaravan.cli.load_profile", return_value={"artifacts": [{
                "artifact_type": "team-instance",
                "id": team_id,
                "name": "Platform Team",
                "team_context": team["team_context"],
            }]}), patch("agentcaravan.cli.resolve_profile", return_value={"status": "pass"}), patch(
                "builtins.input",
                side_effect=[
                    "A replacement mission",
                    "platform-cli",
                    "Updated team docs",
                    "Updated agreements",
                    "",
                ],
            ), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["configure", "--root", str(root)]), 0)
            customized = (workspace / "caravan.md").read_text(encoding="utf-8")
            self.assertIn("A replacement mission", customized)
            self.assertIn("## Notes", customized)
            self.assertIn("Keep this heading.", customized)
            self.assertIn("Keep the existing AI instructions.", (workspace / "instructions.md").read_text(encoding="utf-8"))
            self.assertIn("Keep the existing role guidance.", (workspace / "responsibilities.md").read_text(encoding="utf-8"))

            updated_team = json.loads((source / f"{team_id}.json").read_text(encoding="utf-8"))
            self.assertEqual(updated_team["team_context"]["mission"], "A replacement mission")
            self.assertEqual(updated_team["team_context"]["work_surfaces"], ["platform-cli"])
            self.assertEqual(updated_team["team_context"]["knowledge_sources"], ["Updated team docs"])
            self.assertEqual(updated_team["team_context"]["working_agreements"], "Updated agreements")

    def test_local_work_surface_paths_are_not_written_into_shared_team_artifact(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bootstrap(root)
            source = root / "sources" / "example-organization"
            source.mkdir(parents=True)
            team_id = "example-organization-platform-team"
            (source / f"{team_id}.json").write_text(json.dumps({
                "artifact_type": "team-instance",
                "id": team_id,
                "name": "Platform Team",
                "team_blueprint_id": "information-technology-core-team",
                "team_context": {"work_surfaces": ["git@gitlab.example:org/platform.git"]},
            }) + "\n", encoding="utf-8")
            (root / "config.json").write_text(json.dumps({
                "sources": [str(source)],
                "active_context": {"team_instance_id": team_id},
            }) + "\n", encoding="utf-8")
            workspace = root / "caravans" / team_id
            workspace.mkdir(parents=True)
            (workspace / "repositories.md").write_text(
                "# Platform Team Work Surfaces\n\n"
                "- /Users/alex/workspace/platform\n",
                encoding="utf-8",
            )

            with patch("agentcaravan.cli.load_profile", return_value={"artifacts": [{
                "artifact_type": "team-instance",
                "id": team_id,
                "name": "Platform Team",
                "team_context": {"work_surfaces": ["git@gitlab.example:org/platform.git"]},
            }]}), patch("agentcaravan.cli.resolve_profile", return_value={"status": "pass"}), patch(
                "builtins.input",
                side_effect=[
                    "Support platform delivery.",
                    "git@gitlab.example:org/platform.git, /Users/alex/workspace/platform",
                    "",
                    "",
                    "",
                ],
            ), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["configure", "--root", str(root)]), 0)

            team = json.loads((source / f"{team_id}.json").read_text(encoding="utf-8"))
            self.assertEqual(
                team["team_context"]["work_surfaces"],
                ["git@gitlab.example:org/platform.git"],
            )
            self.assertIn(
                "/Users/alex/workspace/platform",
                (workspace / "repositories.md").read_text(encoding="utf-8"),
            )


    def test_configure_can_be_cancelled_without_changing_team_workspace(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bootstrap(root)
            source = root / "sources" / "example-organization"
            source.mkdir(parents=True)
            team_id = "example-organization-platform-team"
            (source / f"{team_id}.json").write_text(json.dumps({
                "artifact_type": "team-instance",
                "id": team_id,
                "name": "Platform Team",
                "team_blueprint_id": "information-technology-core-team",
                "team_context": {},
            }) + "\n", encoding="utf-8")
            (root / "config.json").write_text(json.dumps({
                "sources": [str(source)],
                "active_context": {"team_instance_id": team_id},
            }) + "\n", encoding="utf-8")
            workspace = root / "caravans" / team_id
            workspace.mkdir(parents=True)
            original_team_markdown = "# Platform Team\n\n## Mission\n\nOriginal mission.\n"
            (workspace / "caravan.md").write_text(original_team_markdown, encoding="utf-8")
            original_team_artifact = (source / f"{team_id}.json").read_text(encoding="utf-8")

            with patch("agentcaravan.cli.load_profile", return_value={"artifacts": [{
                "artifact_type": "team-instance",
                "id": team_id,
                "name": "Platform Team",
                "team_context": {},
            }]}), patch("builtins.input", side_effect=["Mission", "", "", "", "n"]):
                with self.assertRaisesRegex(SystemExit, "Configuration cancelled"):
                    main(["configure", "--root", str(root)])

            self.assertEqual((workspace / "caravan.md").read_text(encoding="utf-8"), original_team_markdown)
            self.assertEqual((source / f"{team_id}.json").read_text(encoding="utf-8"), original_team_artifact)

    def test_team_workspace_rejects_path_traversal_identifier(self):
        with self.assertRaisesRegex(ValueError, "filesystem-safe"):
            team_workspace(Path("/tmp/profile"), "../outside")

    def test_prompt_with_default_uses_copy_safe_guidance(self):
        with patch("builtins.input", return_value="") as prompt:
            self.assertEqual(_prompt_with_default("Team mission", "Support the work owned by My Team."), "Support the work owned by My Team.")
            self.assertEqual(
                prompt.call_args.args[0],
                "Team mission (default: Support the work owned by My Team.; press Enter to accept): ",
            )

        with patch("builtins.input", return_value="") as prompt:
            self.assertEqual(_prompt_with_default("Repositories/services (optional, comma-separated)", ""), "")
            self.assertEqual(
                prompt.call_args.args[0],
                "Repositories/services (optional, comma-separated); press Enter to leave blank: ",
            )

    def test_yes_no_prompt_is_case_insensitive_and_uses_lowercase_options(self):
        with patch("builtins.input", return_value="Y") as prompt:
            self.assertTrue(_prompt_yes_no("Continue?", default=False))
            self.assertEqual(prompt.call_args.args[0], "Continue? (y/n; default: n): ")

        with patch("builtins.input", return_value="n"):
            self.assertFalse(_prompt_yes_no("Continue?", default=True))

        with patch("builtins.input", return_value=""):
            self.assertTrue(_prompt_yes_no("Continue?", default=True))

    def test_configure_ignores_pasted_prompt_placeholders(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bootstrap(root)
            source = root / "sources" / "example-organization"
            source.mkdir(parents=True)
            team_id = "example-organization-platform-team"
            (source / f"{team_id}.json").write_text(json.dumps({
                "artifact_type": "team-instance",
                "id": team_id,
                "name": "Platform Team",
                "team_blueprint_id": "information-technology-core-team",
                "team_context": {},
            }) + "\n", encoding="utf-8")
            (root / "config.json").write_text(json.dumps({
                "sources": [str(source)],
                "active_context": {"team_instance_id": team_id},
            }) + "\n", encoding="utf-8")

            with patch("agentcaravan.cli.load_profile", return_value={"artifacts": [{
                "artifact_type": "team-instance",
                "id": team_id,
                "name": "Platform Team",
                "team_context": {},
            }]}), patch("agentcaravan.cli.resolve_profile", return_value={"status": "pass"}), patch(
                "builtins.input",
                side_effect=[
                    "Support platform delivery.",
                    "Relevant repositories, services, or workspaces?",
                    "[Enter the real repositories or press Enter to leave blank]",
                    "[Enter the real repositories or press Enter to leave blank]",
                    "",
                ],
            ), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["configure", "--root", str(root)]), 0)

            team = json.loads((source / f"{team_id}.json").read_text(encoding="utf-8"))
            self.assertEqual(team["team_context"]["work_surfaces"], [])
            self.assertEqual(team["team_context"]["knowledge_sources"], [])
            self.assertEqual(team["team_context"]["working_agreements"], "")
            self.assertNotIn(
                "Relevant repositories",
                (root / "caravans" / team_id / "knowledge.md").read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
