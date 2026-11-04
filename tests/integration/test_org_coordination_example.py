"""Checks for the organization-coordination cookbook example."""

from __future__ import annotations

import json
import runpy
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agentcaravan.profile import load_profile
from agentcaravan.resolve_framework import resolve_profile

EXAMPLE = runpy.run_path(str(ROOT / "examples/org-coordination/run.py"))


class OrganizationCoordinationExampleTests(unittest.TestCase):
    def test_team_references_validate_and_route_product_platform_product(self) -> None:
        organization_map, team_instances = EXAMPLE["load_and_validate"]()
        route = EXAMPLE["build_route"](organization_map)

        self.assertEqual(
            [step["team_id"] for step in route], ["product", "platform", "product"]
        )
        self.assertEqual(
            {team["team_instance_id"] for team in organization_map["teams"]},
            {
                "example-organization-platform-team",
                "example-organization-product-team",
            },
        )
        for team in organization_map["teams"]:
            self.assertIn(team["team_instance_id"], team_instances)
            self.assertTrue(team["specialties"])
            self.assertTrue(team["owns"])
            self.assertEqual(team["unit_id"], "engineering")
            self.assertTrue(team["reports_to"])
        self.assertTrue(all(step["responsibility"] and step["handoff"] for step in route))

    def test_runner_keeps_the_checked_in_example_as_its_default(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            status = EXAMPLE["main"]([])

        self.assertEqual(status, 0)
        self.assertIn("Scenario: shared-preferences-change", output.getvalue())
        self.assertIn("Product Team (product)", output.getvalue())

    def test_each_referenced_team_resolves_with_its_selected_context(self) -> None:
        organization_map, _ = EXAMPLE["load_and_validate"]()
        shared_source = ROOT / "examples/example-organization"
        common_resources = [
            ROOT / "resources/core/agentcaravan-core-team.json",
            ROOT / "resources/runtime/agentcaravan-codex-runtime.json",
        ]
        template_path = ROOT / "examples/coworker-sharing/profiles/coworker-one/config.json"

        with tempfile.TemporaryDirectory(prefix="agentcaravan-org-coordination-") as temporary:
            for team in organization_map["teams"]:
                profile_root = Path(temporary) / team["id"] / "profile"
                profile_root.mkdir(parents=True)
                config = json.loads(template_path.read_text(encoding="utf-8"))
                config["sources"] = [str(shared_source), *(str(path) for path in common_resources)]
                config["active_context"]["team_instance_id"] = team["team_instance_id"]
                (profile_root / "config.json").write_text(
                    json.dumps(config, indent=2) + "\n", encoding="utf-8"
                )

                bundle = load_profile(profile_root)
                result = resolve_profile(profile_root)
                self.assertTrue(bundle["artifacts"])
                self.assertEqual(result["status"], "pass")
                self.assertEqual(
                    result["context"]["team_instance_id"], team["team_instance_id"]
                )

    def test_unknown_team_reference_fails_validation(self) -> None:
        organization_map = json.loads(EXAMPLE["DEFAULT_MAP"].read_text(encoding="utf-8"))
        organization_map["teams"][0]["team_instance_id"] = "unknown-team-instance"
        with tempfile.TemporaryDirectory() as temporary:
            invalid_map = Path(temporary) / "organization-map.json"
            invalid_map.write_text(json.dumps(organization_map), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unknown team instance reference"):
                EXAMPLE["load_and_validate"](invalid_map)

    def test_cli_accepts_custom_inputs_and_selects_a_scenario(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            team_directory = root / "teams"
            team_directory.mkdir()
            for team_file in (ROOT / "examples/example-organization/caravans").glob("*.json"):
                shutil.copyfile(team_file, team_directory / team_file.name)

            catalog_path = root / "catalog.json"
            shutil.copyfile(
                ROOT / "examples/example-organization/organizations/example-organization-catalog.json",
                catalog_path,
            )
            organization_map = json.loads(EXAMPLE["DEFAULT_MAP"].read_text(encoding="utf-8"))
            selected_scenario = dict(organization_map["scenarios"][0])
            selected_scenario["id"] = "custom-route"
            selected_scenario["request"] = "Run a custom route."
            selected_scenario["route"] = [selected_scenario["route"][1]]
            organization_map["scenarios"].append(selected_scenario)
            map_path = root / "org-map.json"
            map_path.write_text(json.dumps(organization_map), encoding="utf-8")

            output = StringIO()
            with redirect_stdout(output):
                status = EXAMPLE["main"](
                    [
                        "--map",
                        str(map_path),
                        "--catalog",
                        str(catalog_path),
                        "--team-dir",
                        str(team_directory),
                        "--scenario",
                        "custom-route",
                    ]
                )

        self.assertEqual(status, 0)
        self.assertIn("Scenario: custom-route", output.getvalue())
        self.assertIn("Platform Team (platform)", output.getvalue())
        self.assertNotIn("Product Team (product)", output.getvalue())

    def test_invalid_unit_parent_and_team_unit_references_fail_validation(self) -> None:
        cases = (
            (
                lambda data: data["units"][1].update(parent_unit_id="missing-unit"),
                "references unknown parent unit",
            ),
            (
                lambda data: data["units"][0].update(parent_unit_id="engineering"),
                "cycle detected in unit hierarchy",
            ),
            (
                lambda data: data["teams"][0].update(unit_id="missing-unit"),
                "references unknown unit",
            ),
            (
                lambda data: data["units"].append(dict(data["units"][0])),
                "duplicate unit id",
            ),
        )
        for mutate, expected_error in cases:
            with self.subTest(expected_error=expected_error), tempfile.TemporaryDirectory() as temporary:
                organization_map = json.loads(EXAMPLE["DEFAULT_MAP"].read_text(encoding="utf-8"))
                mutate(organization_map)
                invalid_map = Path(temporary) / "organization-map.json"
                invalid_map.write_text(json.dumps(organization_map), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, expected_error):
                    EXAMPLE["load_and_validate"](invalid_map)


if __name__ == "__main__":
    unittest.main()
