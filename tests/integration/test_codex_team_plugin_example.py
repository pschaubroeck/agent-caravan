import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = REPOSITORY_ROOT / "examples/codex-plugins/example-organization-platform-team"


class CodexTeamPluginExampleTests(unittest.TestCase):
    def test_plugin_manifest_marketplace_and_skill_are_wired(self):
        manifest = json.loads((PLUGIN_ROOT / "plugin.json").read_text(encoding="utf-8"))
        marketplace = json.loads(
            (REPOSITORY_ROOT / "examples/codex-plugins/.agents/plugins/marketplace.json").read_text(encoding="utf-8")
        )
        skill_path = PLUGIN_ROOT / "skills/setup-example-team/SKILL.md"
        skill = skill_path.read_text(encoding="utf-8")
        readme = (PLUGIN_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertEqual(manifest["name"], "example-organization-platform-team")
        self.assertEqual(manifest["version"], "1.0.0")
        self.assertEqual(manifest["$schema"], "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json")
        self.assertEqual(marketplace["name"], "agentcaravan-examples")
        entry = next(item for item in marketplace["plugins"] if item["name"] == manifest["name"])
        self.assertEqual(entry["source"]["source"], "local")
        self.assertEqual(
            (REPOSITORY_ROOT / "examples/codex-plugins" / entry["source"]["path"]).resolve(),
            PLUGIN_ROOT.resolve(),
        )
        self.assertIn("name: setup-example-team", skill)
        self.assertIn("versioned snapshot", skill)
        self.assertIn("Do not overwrite", skill)
        self.assertIn("codex plugin marketplace add ./examples/codex-plugins", readme)
        self.assertIn("does not modify an", readme)
        self.assertIn("codex plugin marketplace add ./examples/codex-plugins", skill)
        self.assertTrue((PLUGIN_ROOT / "scripts/install_snapshot.py").is_file())

    def test_plugin_snapshot_matches_canonical_artifacts(self):
        pairs = (
            (
                REPOSITORY_ROOT / "examples/example-organization/organizations/example-organization-catalog.json",
                PLUGIN_ROOT / "team-snapshot/example-organization-catalog.json",
            ),
            (
                REPOSITORY_ROOT / "examples/example-organization/caravans/platform-team.json",
                PLUGIN_ROOT / "team-snapshot/platform-team.json",
            ),
            (
                REPOSITORY_ROOT / "examples/example-organization/caravans/product-team.json",
                PLUGIN_ROOT / "team-snapshot/product-team.json",
            ),
        )
        for canonical, snapshot in pairs:
            self.assertTrue(canonical.is_file(), f"missing canonical artifact: {canonical}")
            self.assertTrue(snapshot.is_file(), f"missing plugin snapshot: {snapshot}")
            self.assertEqual(json.loads(snapshot.read_text()), json.loads(canonical.read_text()))

        catalog = json.loads(pairs[0][1].read_text(encoding="utf-8"))
        team = json.loads(pairs[1][1].read_text(encoding="utf-8"))
        self.assertEqual(catalog["id"], "example-organization")
        self.assertEqual(
            catalog["published_artifacts"]["team-instance"],
            ["example-organization-platform-team", "example-organization-product-team"],
        )
        self.assertEqual(team["id"], "example-organization-platform-team")
        self.assertEqual(team["team_blueprint_id"], "information-technology-core-team")

        check = subprocess.run(
            [sys.executable, str(PLUGIN_ROOT / "scripts/check_snapshot.py")],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(check.returncode, 0, check.stderr)
        self.assertIn("matches the canonical", check.stdout)

    def test_installer_copies_snapshot_and_refuses_existing_organization_directory(self):
        installer = PLUGIN_ROOT / "scripts/install_snapshot.py"
        with tempfile.TemporaryDirectory(prefix="agentcaravan-plugin-example-") as temp_root:
            profile_root = Path(temp_root) / "profile"
            install = subprocess.run(
                [sys.executable, str(installer), "--profile-root", str(profile_root)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(install.returncode, 0, install.stderr)
            destination = profile_root / "sources/example-organization"
            self.assertEqual(
                json.loads((destination / "organization-catalog.json").read_text()),
                json.loads((PLUGIN_ROOT / "team-snapshot/example-organization-catalog.json").read_text()),
            )
            self.assertEqual(
                json.loads((destination / "team-instance.json").read_text()),
                json.loads((PLUGIN_ROOT / "team-snapshot/platform-team.json").read_text()),
            )
            self.assertEqual(
                json.loads((destination / "product-team.json").read_text()),
                json.loads((PLUGIN_ROOT / "team-snapshot/product-team.json").read_text()),
            )

            sentinel = destination / "user-owned.json"
            sentinel.write_text("keep me", encoding="utf-8")
            conflict = subprocess.run(
                [sys.executable, str(installer), "--profile-root", str(profile_root)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(conflict.returncode, 1)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep me")
            self.assertIn("refusing to overwrite", conflict.stderr)


if __name__ == "__main__":
    unittest.main()
