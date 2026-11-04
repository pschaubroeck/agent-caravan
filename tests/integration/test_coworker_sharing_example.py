import contextlib
import io
import json
import runpy
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[2]
EXAMPLE = runpy.run_path(str(ROOT / "examples/coworker-sharing/run.py"))


class CoworkerSharingExampleTests(unittest.TestCase):
    def test_two_independent_profiles_resolve_same_shared_team(self):
        report = EXAMPLE["run_scenario"]()
        first, second = report["profiles"]

        self.assertEqual(first["status"], "pass")
        self.assertEqual(second["status"], "pass")
        self.assertNotEqual(first["profile_root"], second["profile_root"])
        self.assertEqual(first["organization_catalog_id"], "example-organization")
        self.assertEqual(first["team_instance_id"], "example-organization-platform-team")
        self.assertEqual(first["team_blueprint_id"], "information-technology-core-team")
        for field in (
            "organization_catalog_id",
            "team_instance_id",
            "team_blueprint_id",
            "artifact_versions",
        ):
            self.assertEqual(first[field], second[field])
        self.assertTrue(first["artifact_versions"]["team_instance"])
        self.assertTrue(first["artifact_versions"]["team_blueprint"])

    def test_runner_prints_resolutions_and_uses_temporary_roots(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(EXAMPLE["main"](), 0)
        report = json.loads(output.getvalue())

        self.assertEqual(len(report["profiles"]), 2)
        for profile in report["profiles"]:
            self.assertIn("agentcaravan-coworker-sharing-", profile["profile_root"])
            self.assertIn("organization_catalog_id", profile)
            self.assertIn("artifact_versions", profile)
        self.assertTrue((ROOT / "examples/example-organization").is_dir())
