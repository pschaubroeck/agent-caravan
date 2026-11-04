import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentcaravan.resolve_framework import resolve_profile
from agentcaravan.orchestration import prepare_execution
from tools.init_agentcaravan import _require_supported_python, main as checkout_init


class CheckoutInitializationTests(unittest.TestCase):
    def test_checkout_init_reports_unsupported_python(self):
        with patch.object(sys, "version_info", (3, 9, 0)), self.assertRaisesRegex(
            SystemExit,
            "Agent Caravan requires Python 3.10 or newer; found Python 3.9.0",
        ):
            _require_supported_python()

    def test_checkout_init_defaults_to_and_retains_existing_team(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "profile"
            skill_root = Path(temporary) / "skills"
            root.mkdir(parents=True)
            source_root = root / "sources" / "example-organization"
            source_root.mkdir(parents=True)
            (source_root / "organization-catalog.json").write_text(
                json.dumps(
                    {
                        "artifact_type": "organization-catalog",
                        "id": "example-organization",
                        "version": "1.0.0",
                        "scope": "organization",
                        "name": "Example Organization",
                        "published_artifacts": {"team-instance": ["example-organization-team-ai"]},
                    }
                ),
                encoding="utf-8",
            )
            existing_team = {
                "artifact_type": "team-instance",
                "id": "example-organization-team-ai",
                "version": "1.0.0",
                "scope": "organization",
                "name": "Team AI",
                "organization_catalog_id": "example-organization",
                "team_blueprint_id": "information-technology-core-team",
                "runtime_defaults": ["codex-desktop-agent-runtime"],
                "runtime_profile_id": "codex-desktop-information-technology-core-team",
                "execution_profile_id": "information-technology-core-team-feature-delivery",
                "ownership_boundary": {"summary": "Agent Caravan framework"},
                "custom_field": "preserve me",
            }
            team_path = source_root / "example-organization-team-ai.json"
            team_path.write_text(json.dumps(existing_team, indent=2) + "\n", encoding="utf-8")
            (root / "config.json").write_text(
                json.dumps(
                    {
                        "sources": [str(source_root)],
                        "active_context": {
                            "organization_catalog_id": "example-organization",
                            "team_instance_id": "example-organization-team-ai",
                        },
                    }
                ),
                encoding="utf-8",
            )

            output = io.StringIO()
            with patch.object(
                sys,
                "argv",
                ["init_agentcaravan.py", "--root", str(root), "--skill-root", str(skill_root)],
            ), patch("builtins.input", side_effect=["1", "", ""]), contextlib.redirect_stdout(output):
                self.assertEqual(checkout_init(), 0)

            self.assertEqual(json.loads(team_path.read_text(encoding="utf-8")), existing_team)
            config = json.loads((root / "config.json").read_text(encoding="utf-8"))
            self.assertEqual(config["active_context"]["team_instance_id"], "example-organization-team-ai")
            self.assertIn("I’m going to use existing configuration for:", output.getvalue())
            self.assertIn("Caravan: Team AI", output.getvalue())
            self.assertIn("Caravan template: Information Technology Core Team", output.getvalue())
            self.assertIn("Ownership scope: Existing caravan configuration", output.getvalue())
            self.assertIn("Caravan already configured", output.getvalue())

    def test_checkout_init_creates_and_resolves_starter_team(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "profile"
            skill_root = Path(temporary) / "skills"
            output = io.StringIO()
            with patch.object(sys, "argv", ["init_agentcaravan.py", "--root", str(root), "--skill-root", str(skill_root)]), patch(
                "builtins.input", side_effect=["", "", ""]
            ), contextlib.redirect_stdout(output):
                self.assertEqual(checkout_init(), 0)

            config = json.loads((root / "config.json").read_text(encoding="utf-8"))
            self.assertEqual(config["active_context"]["organization_catalog_id"], "my-organization")
            self.assertEqual(config["active_context"]["team_instance_id"], "my-organization-my-team")
            resolved = resolve_profile(root)
            self.assertEqual(resolved["status"], "pass")
            self.assertEqual(resolved["context"]["execution_profile_id"], "information-technology-core-team-basic-work")
            self.assertEqual(resolved["policies"], [])
            self.assertNotIn("evidence_requirements", resolved["execution_profile"])
            prepared = prepare_execution(
                resolved,
                {"task_id": "starter-task", "objective": "Complete a bounded development task"},
            )
            self.assertEqual(prepared["status"], "ready")
            self.assertEqual(prepared["plan"]["policy"]["policy_ids"], [])
            self.assertEqual(prepared["plan"]["policy"]["approval_requirements"], [])
            self.assertNotIn("evidence_requirements", prepared["plan"])
            self.assertTrue((skill_root / "agent-caravan-codex-orchestrator").is_dir())
            self.assertIn("python3 -m agentcaravan.cli configure", output.getvalue())
            self.assertIn("python3 -m agentcaravan.cli run", output.getvalue())

    def test_checkout_init_preserves_unmanaged_skill_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "profile"
            skill_root = Path(temporary) / "skills"
            existing_skill = skill_root / "agent-caravan-codex-orchestrator"
            existing_skill.mkdir(parents=True)
            marker = existing_skill / "custom.md"
            marker.write_text("keep this", encoding="utf-8")

            with patch.object(sys, "argv", ["init_agentcaravan.py", "--root", str(root), "--skill-root", str(skill_root)]), patch(
                "builtins.input", side_effect=["Example Organization", "Platform Team", ""]
            ), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(checkout_init(), 0)

            self.assertEqual(marker.read_text(encoding="utf-8"), "keep this")
            self.assertEqual(resolve_profile(root)["status"], "pass")

    def test_checkout_init_preserves_user_owned_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "profile"
            skill_root = Path(temporary) / "skills"
            user_source = Path(temporary) / "user-source"
            user_source.mkdir()
            (user_source / "notes.json").write_text('{"notes": "keep"}\n', encoding="utf-8")
            root.mkdir()
            (root / "config.json").write_text(
                json.dumps(
                    {
                        "sources": [
                            str(user_source),
                            str(Path("/old/checkout") / "resources/core/agentcaravan-core-team.json"),
                        ],
                        "managed_sources": {
                            "agentcaravan_repository": {
                                "paths": [str(Path("/old/checkout") / "resources/core/agentcaravan-core-team.json")]
                            }
                        },
                        "active_context": {},
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with patch.object(
                sys,
                "argv",
                ["init_agentcaravan.py", "--root", str(root), "--skill-root", str(skill_root)],
            ), patch(
                "builtins.input", side_effect=["Example Organization", "Platform Team", ""]
            ), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(checkout_init(), 0)

            config = json.loads((root / "config.json").read_text(encoding="utf-8"))
            self.assertIn(str(user_source), config["sources"])
            self.assertNotIn(str(Path("/old/checkout") / "resources/core/agentcaravan-core-team.json"), config["sources"])
            self.assertEqual(resolve_profile(root)["status"], "pass")

    def test_checkout_init_can_be_cancelled_before_profile_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "profile"
            with patch.object(sys, "argv", ["init_agentcaravan.py", "--root", str(root)]), patch(
                "builtins.input", side_effect=["", "", "n"]
            ), self.assertRaisesRegex(SystemExit, "Initialization cancelled"):
                checkout_init()

            self.assertFalse(root.exists())


if __name__ == "__main__":
    unittest.main()
