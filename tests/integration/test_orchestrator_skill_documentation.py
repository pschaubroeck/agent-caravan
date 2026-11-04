import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "agent-caravan-codex-orchestrator" / "SKILL.md"
OPENAI_METADATA = ROOT / "skills" / "agent-caravan-codex-orchestrator" / "agents" / "openai.yaml"


class OrchestratorSkillDocumentationTests(unittest.TestCase):
    def test_orchestrator_skill_describes_ai_first_implementation(self):
        content = SKILL.read_text(encoding="utf-8")

        for required_text in (
            "## AI-First Implementation Workflow",
            "active Agent Caravan team",
            "repository guidance",
            "bounded implementation plan",
            "native subagents",
            "focused tests",
            "Required implementor report",
            "planned roles and roles actually delegated",
            "worker references",
            "persisted task, session, plan, run, and completion evidence",
            "unverified conditions",
            "For a read-only or no-change task, report that no implementation occurred.",
            "runtime-neutral at the plan level",
        ):
            self.assertIn(required_text, content)

    def test_orchestrator_metadata_is_implementation_oriented(self):
        content = OPENAI_METADATA.read_text(encoding="utf-8")

        self.assertIn('display_name: "Agent Caravan Implementation Orchestrator"', content)
        self.assertIn("Implement work through an active Agent Caravan team", content)
        self.assertIn("report evidence and unverified conditions", content)


if __name__ == "__main__":
    unittest.main()
