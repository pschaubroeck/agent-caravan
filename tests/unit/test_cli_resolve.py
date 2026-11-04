import argparse
import contextlib
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from agentcaravan.cli import main, resolve
from agentcaravan.resolve_framework import ResolutionError


class ResolveCommandTests(unittest.TestCase):
    def test_nonzero_handler_result_is_logged_at_error_level(self):
        error_output = io.StringIO()
        with patch("agentcaravan.cli.validate", return_value=1):
            with contextlib.redirect_stderr(error_output):
                status = main(["validate", "--log-level", "ERROR", "--log-format", "json"])

        self.assertEqual(status, 1)
        records = [json.loads(line) for line in error_output.getvalue().splitlines()]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["event_type"], "agentcaravan.command.failed")
        self.assertEqual(records[0]["severity"], "ERROR")
        self.assertEqual(records[0]["attributes"]["exit_code"], 1)

    def test_json_logging_stays_structured_when_command_handler_fails(self):
        error_output = io.StringIO()
        with patch("agentcaravan.cli.validate", side_effect=RuntimeError("failure details")):
            with contextlib.redirect_stderr(error_output):
                status = main(["validate", "--log-format", "json"])

        self.assertEqual(status, 1)
        records = [json.loads(line) for line in error_output.getvalue().splitlines()]
        self.assertEqual([record["event_type"] for record in records], [
            "agentcaravan.command.started",
            "agentcaravan.command.failed",
        ])
        self.assertEqual(records[-1]["attributes"]["error_type"], "RuntimeError")
        self.assertEqual(records[-1]["attributes"]["exit_code"], 1)
        self.assertEqual(records[-1]["attributes"]["diagnostic"], "failure details")

    def test_diagnostics_print_structured_coverage_findings_on_resolution_failure(self):
        error = ResolutionError(
            "coverage requirement implementation has no effective role",
            diagnostics={
                "team_coverage": {
                    "status": "fail",
                    "issues": [{"kind": "coverage-requirement", "name": "implementation"}],
                }
            },
        )
        output = io.StringIO()
        args = argparse.Namespace(root=Path("/tmp/profile"), diagnostics=True)

        with patch("agentcaravan.cli.resolve_profile", side_effect=error):
            with contextlib.redirect_stdout(output):
                status = resolve(args)

        self.assertEqual(status, 1)
        report = json.loads(output.getvalue())
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["team_coverage"]["issues"][0]["name"], "implementation")

    def test_resolve_parser_exposes_diagnostics_option(self):
        with patch("agentcaravan.cli.resolve", return_value=0) as handler:
            self.assertEqual(main(["resolve", "--diagnostics"]), 0)
        self.assertTrue(handler.call_args.args[0].diagnostics)

    def test_success_prints_resolved_validation_evidence(self):
        result = {
            "status": "pass",
            "validation_evidence": {
                "team_coverage": {"status": "pass"},
                "runtime_verification": {"status": "unverified"},
                "task_behavior_evaluation": {"status": "not-evaluated"},
            },
        }
        output = io.StringIO()
        args = argparse.Namespace(root=Path("/tmp/profile"), diagnostics=True)

        with patch("agentcaravan.cli.resolve_profile", return_value=result):
            with contextlib.redirect_stdout(output):
                status = resolve(args)

        self.assertEqual(status, 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report["validation_evidence"]["runtime_verification"]["status"], "unverified")


if __name__ == "__main__":
    unittest.main()
