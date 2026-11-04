import json
import unittest
from pathlib import Path

from agentcaravan.managed_skills import all_skill_ids, skill_ids_for_runtime, skill_inventory
from agentcaravan.org_framework_layout import packaged_skill_path


class SkillInventoryTests(unittest.TestCase):
    def test_runtime_skill_sets_match_the_supported_installations(self):
        self.assertEqual(
            skill_ids_for_runtime("codex"),
            (
                "agent-caravan-builder",
                "agent-caravan-codex-orchestrator",
                "agent-caravan-resolver",
                "agent-caravan-runtime-adapter-builder",
                "agent-caravan-validator",
            ),
        )
        self.assertEqual(
            skill_ids_for_runtime("opencode"),
            (
                "agent-caravan-builder",
                "agent-caravan-resolver",
                "agent-caravan-runtime-adapter-builder",
                "agent-caravan-validator",
                "agent-caravan-opencode-orchestrator",
            ),
        )
        self.assertEqual(
            skill_ids_for_runtime("kiro"),
            (
                "agent-caravan-builder",
                "agent-caravan-resolver",
                "agent-caravan-runtime-adapter-builder",
                "agent-caravan-validator",
                "agent-caravan-kiro-orchestrator",
            ),
        )

    def test_inventory_ids_and_paths_are_unique_and_packaged(self):
        inventory = skill_inventory()
        ids = [entry["id"] for entry in inventory]
        paths = [entry["path"] for entry in inventory]

        self.assertEqual(all_skill_ids(), tuple(ids))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(paths), len(set(paths)))
        for skill_id in ids:
            self.assertTrue(packaged_skill_path(skill_id).is_dir(), skill_id)

    def test_catalog_skill_index_matches_distributable_inventory(self):
        catalog_path = Path(__file__).resolve().parents[2] / "catalog-manifest.json"
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        catalog_skill_ids = catalog["skills"]
        distribution_skill_ids = all_skill_ids()

        self.assertEqual(len(catalog_skill_ids), len(set(catalog_skill_ids)))
        self.assertEqual(set(catalog_skill_ids), set(distribution_skill_ids))


if __name__ == "__main__":
    unittest.main()
