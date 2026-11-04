import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentcaravan.cli import main


class CliStatusTests(unittest.TestCase):
    def test_status_reports_resolved_adapter_and_repository_guidance(self):
        guidance_values = (
            {
                "canonical_file": "AGENTS.md",
                "native_files": ["AGENTS.md"],
                "discovery": "automatic",
                "reference_policy": "follow-explicit-links",
            },
            {
                "canonical_file": "AGENTS.md",
                "native_files": ["TEAM_GUIDANCE.md", "docs/ASSISTANT.md"],
                "discovery": "explicit",
                "reference_policy": "entrypoint-only",
            },
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "config.json").write_text("{}\n", encoding="utf-8")
            config = {
                "active_context": {
                    "organization_catalog_id": "example-organization",
                    "team_instance_id": "example-team",
                    "runtime_adapter_id": "custom-test-runtime-adapter",
                }
            }
            profile = {"artifacts": [
                {
                    "artifact_type": "organization-catalog",
                    "id": "example-organization",
                    "name": "Example Organization",
                },
                {
                    "artifact_type": "team-instance",
                    "id": "example-team",
                    "name": "Example Team",
                    "team_blueprint_id": "example-blueprint",
                    "team_context": {},
                },
            ]}

            for guidance in guidance_values:
                resolved = {
                    "status": "pass",
                    "context": {
                        "team_blueprint_id": "example-blueprint",
                        "runtime_profile_id": "example-runtime-profile",
                    },
                    "runtime": {
                        "adapter_id": "custom-test-runtime-adapter",
                        "repository_guidance": guidance,
                    },
                    "team_context": {},
                }
                with patch("agentcaravan.cli.load_config", return_value=config), patch(
                    "agentcaravan.cli.load_profile", return_value=profile
                ), patch("agentcaravan.cli.resolve_profile", return_value=resolved), patch(
                    "agentcaravan.cli.skill_status",
                    return_value={"status": "not-applicable", "runtime": None, "root": None, "missing": [], "modified": []},
                ):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        self.assertEqual(main(["status", "--root", str(root), "--json"]), 0)
                    report = json.loads(output.getvalue())
                    self.assertEqual(report["runtime_adapter_id"], "custom-test-runtime-adapter")
                    self.assertEqual(report["repository_guidance"], guidance)

                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        self.assertEqual(main(["status", "--root", str(root)]), 0)
                    rendered = output.getvalue()
                    self.assertIn("Runtime integration: custom-test-runtime-adapter", rendered)
                    self.assertIn(
                        f"Repository guidance files: {', '.join(guidance['native_files'])}",
                        rendered,
                    )
                    self.assertIn(f"Discovery: {guidance['discovery']}", rendered)
                    self.assertIn(f"Reference policy: {guidance['reference_policy']}", rendered)


if __name__ == "__main__":
    unittest.main()
