import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs" / "developer-examples.md"


class DeveloperExamplesDocumentationTests(unittest.TestCase):
    def test_docs_index_links_examples_and_checkout_guide_routes_product_users(self):
        docs_index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
        getting_started = (ROOT / "docs" / "getting-started.md").read_text(encoding="utf-8")
        examples_index = ROOT / "examples" / "README.md"

        self.assertTrue(GUIDE.is_file())
        self.assertTrue(examples_index.is_file())
        self.assertIn("[Developer examples](developer-examples.md)", docs_index)
        self.assertIn(
            "user-guide.md",
            getting_started,
        )

    def test_example_map_connects_generic_scenarios_and_sample_catalog(self):
        content = GUIDE.read_text(encoding="utf-8")
        examples_index = (ROOT / "examples" / "README.md").read_text(encoding="utf-8")

        self.assertIn("## Example map", content)
        self.assertIn("## Create a reusable role or role variant", content)
        self.assertIn("For first-time setup,", content)
        self.assertIn(
            "user-guide.md",
            content,
        )
        for setup_heading in (
            "## Create a new organization and team",
            "## Re-run setup for an existing organization",
            "## Add another team to an existing organization",
        ):
            self.assertNotIn(setup_heading, content)
        self.assertIn("../examples/coworker-sharing/README.md", content)
        self.assertIn("../examples/codex-plugins/example-organization-platform-team/README.md", content)
        self.assertIn("../examples/org-coordination/README.md", content)
        self.assertIn("../examples/sample-organization/README.md", content)
        self.assertIn("fictional organizations and products", examples_index)
        self.assertIn("fictional organizations and products", examples_index)

    def test_examples_cover_requested_workflows_and_boundaries(self):
        content = GUIDE.read_text(encoding="utf-8")

        for required_text in (
            "## Create a reusable role or role variant",
            "## Customize each team Markdown file",
            "## Use or switch between configured teams",
            "## Make Agent Caravan the default task workflow",
            "## Wire Agent Caravan into a harness",
            "## Check, resolve, validate, and dry-run",
            "## Start a real implementation through an AI harness",
            "## Coordinate work across an organization",
            "## Add advanced configuration",
            "## Export a runtime-neutral handoff",
            "## Common setup and validation problems",
            "agent-caravan-builder",
            "agent-caravan-resolver",
            "agent-caravan-validator",
            "agent-caravan-codex-orchestrator",
            "[CLI guide](getting-started.md#use-the-checkout-cli)",
            "The Agent Caravan validator skill checks the selected artifacts",
            "caravan.md",
            "repositories.md",
            "knowledge.md",
            "working-agreements.md",
            "instructions.md",
            "responsibilities.md",
            "Changes to `responsibilities.md` take effect in the next profile resolution",
            "does not change role assignments in the execution plan",
            "Domain knowledge",
            "Capability knowledge",
            "Configuration override",
            "Runtime integration",
            "Runtime mapping",
            "Workflow",
            "Reuse an existing matching artifact",
            "checked-in repository examples",
            "These paths validate different scopes",
            "repository-provided example",
            "Replace `<task>` with a specific, bounded objective",
            "generates task and handoff IDs",
            "`--root` and `--sessions-root`",
            "agent-caravan validate-session --task-id <task-id>",
            "same `--root` and `--sessions-root` used by",
            "The CLI is a separate authoring and diagnostic path; see the\n"
            "[CLI guide](getting-started.md#use-the-checkout-cli) for its supported commands.",
            "**Does not enforce:**",
            "does not call a model",
            "does not transport, accept, or execute the",
            "role artifact",
            "persistent instruction",
            "Runtime-specific installation belongs",
            "Do not silently use another team.",
            "agent-caravan configure --team-id <team-id>",
            "PYTHONPATH=src python3 -m agentcaravan.cli resolve --root /path/to/profile",
            "validate` checks the packaged or checkout resources",
            "Use my active Agent Caravan team to implement:",
            "<real change for this repository>",
            "worker names and display labels are runtime-owned",
            "Reasoning settings are unclear",
            "Improve one small piece of developer documentation.",
            "organization map in examples/org-coordination",
            "The map is orchestration input, not an Agent Caravan",
            "does not invoke a model, dispatch work, or implement",
        ):
            self.assertIn(required_text, content)

        self.assertGreaterEqual(content.count("<details>"), 7)
        self.assertIn("<summary>CLI equivalent</summary>", content)
        self.assertIn("There is no CLI command for live implementation.", content)
        self.assertIn("There is no general CLI command for authoring these advanced artifact types.", content)

        prompts = re.findall(r"```text\n(.*?)\n```", content, flags=re.DOTALL)
        self.assertGreaterEqual(len(prompts), 12)
        for prompt in prompts:
            self.assertLessEqual(len(prompt.split()), 45)
            self.assertFalse(prompt.lstrip().startswith("agent-caravan "))

        visible_content = re.sub(r"<details>.*?</details>", "", content, flags=re.DOTALL)
        self.assertGreaterEqual(content.count("agent-caravan "), 10)
        self.assertNotRegex(
            visible_content,
            r"(?m)^\s*agentcaravan\s+(init|configure|status|resolve|validate|run|handoff)",
        )

        self.assertGreaterEqual(content.count("**When to use:**"), 11)
        self.assertGreaterEqual(content.count("**Expected result:**"), 11)
        self.assertGreaterEqual(content.count("**Changed files:**"), 11)
        self.assertGreaterEqual(content.count("**Validation:**"), 11)
        self.assertGreaterEqual(content.count("**Does not enforce:**"), 11)

if __name__ == "__main__":
    unittest.main()
