import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "agent-caravan-builder" / "SKILL.md"
OPENAI_METADATA = ROOT / "skills" / "agent-caravan-builder" / "agents" / "openai.yaml"


class BuilderSkillDocumentationTests(unittest.TestCase):
    def test_builder_skill_describes_ai_first_setup(self):
        content = SKILL.read_text(encoding="utf-8")

        for required_text in (
            "## AI-Guided Setup And Update",
            "Inspect Before Asking",
            "Ask Only For Missing Decisions",
            "Preview Before Writing",
            "Persist The Starter Configuration",
            "Explain And Validate",
            "Offer Optional Team Customization",
            "Advanced Customization",
            "existing organization, team, blueprint, and runtime values",
            "information-technology-core-team",
            "Do not ask for ownership scope during basic setup",
            "They do not enforce repository ownership",
            "Preserve existing Markdown files and user edits",
            "runtime-specific projection",
            "classify each as blank, starter",
            "content, or user-customized",
            "file-by-file preview",
            "They do not replace role",
            "## Artifact Authoring Workflow",
        ):
            self.assertIn(required_text, content)

        self.assertNotIn("ask for the team name and ownership/domain", content)
        self.assertNotIn("selected Codex runtime", content)

    def test_builder_metadata_is_setup_oriented(self):
        content = OPENAI_METADATA.read_text(encoding="utf-8")

        self.assertIn('display_name: "Agent Caravan Setup Builder"', content)
        self.assertIn("Set up and customize Agent Caravan teams", content)
        self.assertIn("preserving Markdown customizations", content)


if __name__ == "__main__":
    unittest.main()
