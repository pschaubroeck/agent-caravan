import unittest
from pathlib import Path


PACKAGING_DOC = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "reference"
    / "packaging-and-distribution.md"
)


class PackagingDocumentationTests(unittest.TestCase):
    def test_describes_the_implemented_package_first_boundary(self):
        content = PACKAGING_DOC.read_text(encoding="utf-8")

        for stale_claim in (
            "distributes resolver utilities",
            "supporting distribution for resolver",
            "Deferred: Pip-Installable Bootstrap CLI",
            "Clone the repository or consume its release archive",
        ):
            self.assertNotIn(stale_claim, content)

        for implemented_claim in (
            "self-contained Python package",
            "agent-caravan init --runtime codex",
            "Packaged Core And Local Organization Boundary",
            "Local organization artifacts",
            "organization-specific catalogs",
            "Consumers do not need to clone the repository",
        ):
            self.assertIn(implemented_claim, content)


if __name__ == "__main__":
    unittest.main()
