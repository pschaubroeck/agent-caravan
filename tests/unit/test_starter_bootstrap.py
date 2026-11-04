import unittest
import json
import tempfile
from pathlib import Path

from agentcaravan.bootstrap import StarterConfigurationError, build_starter_team_instance
from agentcaravan.cli import _create_organization, _create_starter_team
from agentcaravan.org_framework_layout import bootstrap
from agentcaravan.profile import load_config


class StarterBootstrapTests(unittest.TestCase):
    def test_builds_minimal_runtime_neutral_team_instance(self):
        team = build_starter_team_instance(
            "example-organization",
            "Platform Team",
            "shared platform services",
        )

        self.assertEqual(team["id"], "example-organization-platform-team")
        self.assertEqual(team["team_blueprint_id"], "information-technology-core-team")
        self.assertEqual(team["ownership_boundary"]["owned_surfaces"], ["shared platform services"])
        self.assertEqual(team["runtime_defaults"], [])
        self.assertEqual(team["execution_profile_id"], "information-technology-core-team-basic-work")
        self.assertEqual(team["role_overlays"], [])
        self.assertEqual(team["specialization_packs"], [])

    def test_runtime_selection_only_adds_a_runtime_default(self):
        team = build_starter_team_instance(
            "example-organization",
            "Platform Team",
            "shared platform services",
            runtime="codex",
        )

        self.assertEqual(team["runtime_defaults"], ["codex-desktop-agent-runtime"])
        self.assertEqual(team["team_blueprint_id"], "information-technology-core-team")

    def test_kiro_runtime_selection_uses_ide_adapter(self):
        team = build_starter_team_instance(
            "example-organization",
            "Platform Team",
            runtime="kiro",
        )

        self.assertEqual(team["runtime_defaults"], ["kiro-ide-agent-runtime"])

    def test_ownership_boundary_is_optional_for_starter_setup(self):
        team = build_starter_team_instance(
            "example-organization",
            "Platform Team",
            runtime="codex",
        )

        self.assertNotIn("ownership_boundary", team)
        self.assertEqual(team["runtime_defaults"], ["codex-desktop-agent-runtime"])

    def test_rejects_incomplete_starter_configuration(self):
        with self.assertRaises(StarterConfigurationError):
            build_starter_team_instance("example-organization", "", "owned services")
        with self.assertRaises(StarterConfigurationError):
            build_starter_team_instance("example-organization", "Platform", "")
        with self.assertRaises(StarterConfigurationError):
            build_starter_team_instance("example-organization", "Platform", "owned services", runtime="unknown")

    def test_cli_starter_setup_creates_catalog_team_and_active_context(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bootstrap(root)
            config = load_config(root)

            organization_id = _create_organization(root, config, [], "Example Organization")
            team_path = _create_starter_team(
                root,
                config,
                organization_id,
                team_name="Platform Team",
                ownership_boundary="shared platform services",
                runtime="codex",
            )

            self.assertTrue(team_path.is_file())
            team = json.loads(team_path.read_text(encoding="utf-8"))
            catalog = json.loads(team_path.with_name("organization-catalog.json").read_text(encoding="utf-8"))
            active_context = json.loads((root / "config.json").read_text(encoding="utf-8"))["active_context"]
            self.assertIn(team["id"], catalog["published_artifacts"]["team-instance"])
            self.assertEqual(active_context["team_instance_id"], team["id"])
            self.assertEqual(active_context["runtime_adapter_id"], "codex-desktop-agent-runtime")
            self.assertEqual(active_context["execution_profile_id"], "information-technology-core-team-basic-work")


if __name__ == "__main__":
    unittest.main()
