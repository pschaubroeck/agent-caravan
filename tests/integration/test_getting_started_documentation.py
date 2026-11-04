import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs" / "getting-started.md"


class GettingStartedDocumentationTests(unittest.TestCase):
    def test_repository_getting_started_is_checkout_and_contributor_focused(self):
        content = GUIDE.read_text(encoding="utf-8")

        for required_text in (
            "# Getting Started in the Agent Caravan Repository",
            "contributors setting up a local checkout",
            "user-guide.md",
            "## Requirements",
            "## Set up a development checkout",
            "python -m pip install -e .",
            "## Initialize a local profile",
            "make init",
            "## Run repository checks",
            "make preflight",
            "PYTHONPATH=src python3 -m unittest discover",
            "## Use the checkout CLI",
            "agent-caravan validate",
            "## Next steps",
        ):
            self.assertIn(required_text, content)

        for product_onboarding_text in (
            "## First 15 minutes",
            "### Start a first implementation task",
            "Use my active Agent Caravan team to implement this change.",
            "agent-caravan run --dry-run",
            "agent-caravan handoff",
        ):
            self.assertNotIn(product_onboarding_text, content)

    def test_readme_and_manifest_route_to_the_canonical_guide(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        manifest = json.loads((ROOT / "catalog-manifest.json").read_text(encoding="utf-8"))
        docs_index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
        developer_examples = (ROOT / "docs" / "developer-examples.md").read_text(encoding="utf-8")

        self.assertIn(
            "docs/user-guide.md",
            readme,
        )
        self.assertIn("[repository setup guide](docs/getting-started.md)", readme)
        self.assertLess(
            readme.index("For product requirements, installation, setup"),
            readme.index("If you are contributing to this repository"),
        )
        self.assertIn("### GitHub Actions and packaging", readme)
        for private_registry_recipe in (
            "PIP_EXTRA_INDEX_URL",
            "PIP_INDEX_URL",
            "packages/pypi/simple",
            "__token__",
            "personal_token",
            "read_api",
            "read_registry",
            "read_repository",
            "pip install agentcaravan",
            "CI_JOB_TOKEN",
            "agent-caravan init",
        ):
            self.assertNotIn(private_registry_recipe, readme)
        self.assertEqual(manifest["getting_started"], "docs/getting-started.md")
        self.assertTrue(GUIDE.is_file())
        self.assertIn("# Agent Caravan Documentation", docs_index)
        self.assertIn(
            "user-guide.md",
            docs_index,
        )
        self.assertIn("repository pages for", docs_index)
        self.assertIn("not the canonical product", developer_examples)
        self.assertIn(
            "user-guide.md",
            developer_examples,
        )
        self.assertNotIn("Framework Documentation Draft Set", docs_index)
        self.assertIn("[Configuration and design notes](maintainers/configuration-and-design-notes.md)", docs_index)


if __name__ == "__main__":
    unittest.main()
