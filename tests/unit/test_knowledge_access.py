import unittest

from agentcaravan.knowledge_access import merge_knowledge_access, normalize_knowledge_access


class KnowledgeAccessTests(unittest.TestCase):
    def test_defaults_to_enabled(self):
        self.assertEqual(
            normalize_knowledge_access(),
            {"external_sources": "enabled", "approved_sources": []},
        )

    def test_disabled_policy_wins(self):
        self.assertEqual(
            merge_knowledge_access(
                [
                    {"knowledge_access": {"external_sources": "enabled"}},
                    {"knowledge_access": {"external_sources": "disabled"}},
                ]
            ),
            {"external_sources": "disabled", "approved_sources": []},
        )

    def test_approved_sources_intersect_conservatively(self):
        self.assertEqual(
            merge_knowledge_access(
                [
                    {
                        "knowledge_access": {
                            "external_sources": "approved_sources",
                            "approved_sources": ["https://example.test/", "https://other.test/"],
                        }
                    },
                    {
                        "knowledge_access": {
                            "external_sources": "approved_sources",
                            "approved_sources": [{"id": "example", "source": "https://example.test/"}],
                        }
                    },
                ]
            ),
            {
                "external_sources": "approved_sources",
                "approved_sources": [{"source": "https://example.test/"}],
            },
        )


if __name__ == "__main__":
    unittest.main()
