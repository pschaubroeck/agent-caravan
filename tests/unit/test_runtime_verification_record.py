import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import ValidationError

from agentcaravan.schema_validation import validate_artifact
from agentcaravan.cli import main as cli_main


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "resources" / "schemas" / "runtime-verification-record.schema.json"


def valid_record():
    return {
        "record_id": "codex-cli-dependency-wait-2026-10-14",
        "adapter": {"id": "codex", "version": "0.4.0"},
        "runtime": {"product": "Codex CLI", "version": "1.2.3"},
        "execution_surface": "local CLI",
        "configuration": {
            "safe_fingerprint": {"algorithm": "sha256", "value": "abc123"}
        },
        "scenario": {
            "id": "dependency-wait-with-independent-work",
            "version": "1.0.0",
            "capability_ids": ["parallel_lane_execution", "role_handoff"],
        },
        "result": {"status": "pass", "summary": "Independent work proceeded while a dependency was pending."},
        "recorded_at": "2026-10-14T15:00:00Z",
        "provenance": {"kind": "adapter-executed", "description": "Adapter conformance job output."},
        "evidence_refs": ["artifact://runs/run-123/summary.json"],
    }


class RuntimeVerificationRecordTests(unittest.TestCase):
    def test_accepts_scenario_scoped_record_with_safe_fingerprint(self):
        validate_artifact(valid_record(), SCHEMA)

    def test_accepts_material_configuration_without_fingerprint(self):
        record = valid_record()
        record["configuration"] = {
            "material_configuration": {"parallelism": 2, "approval_mode": "required"}
        }

        validate_artifact(record, SCHEMA)

    def test_accepts_unverified_record_without_evidence_and_does_not_call_it_unsupported(self):
        record = valid_record()
        record["result"] = {
            "status": "unverified",
            "summary": "The runtime did not expose a receipt for this scenario.",
        }
        record["evidence_refs"] = []

        validate_artifact(record, SCHEMA)

    def test_rejects_unsupported_as_a_verification_outcome(self):
        record = valid_record()
        record["result"]["status"] = "unsupported"

        with self.assertRaises(ValidationError):
            validate_artifact(record, SCHEMA)

    def test_rejects_pass_without_evidence_reference(self):
        record = valid_record()
        record["evidence_refs"] = []

        with self.assertRaises(ValidationError):
            validate_artifact(record, SCHEMA)

    def test_rejects_invalid_recorded_at_timestamp(self):
        record = valid_record()
        record["recorded_at"] = "not-a-timestamp"

        with self.assertRaises(ValidationError):
            validate_artifact(record, SCHEMA)

    def test_requires_scenario_runtime_surface_and_configuration_scope(self):
        for field in ("scenario", "runtime", "execution_surface", "configuration"):
            with self.subTest(field=field):
                record = valid_record()
                del record[field]
                with self.assertRaises(ValidationError):
                    validate_artifact(record, SCHEMA)

    def test_rejects_configuration_without_safe_details_or_fingerprint(self):
        record = valid_record()
        record["configuration"] = {}

        with self.assertRaises(ValidationError):
            validate_artifact(record, SCHEMA)

    def test_rejects_nested_configuration_values(self):
        record = valid_record()
        record["configuration"] = {
            "material_configuration": {"credentials": {"token": "should-not-be-recorded"}}
        }

        with self.assertRaises(ValidationError):
            validate_artifact(record, SCHEMA)

    def test_rejects_secret_like_scalar_configuration_key(self):
        record = valid_record()
        record["configuration"] = {
            "material_configuration": {"API_KEY": "should-not-be-recorded"}
        }

        with self.assertRaises(ValidationError):
            validate_artifact(record, SCHEMA)

    def test_rejects_general_claim_extensions_outside_the_scenario_scope(self):
        record = valid_record()
        record["claims_all_runtime_versions"] = True

        with self.assertRaises(ValidationError):
            validate_artifact(record, SCHEMA)

    def test_cli_validates_and_reports_only_the_recorded_scope(self):
        with tempfile.TemporaryDirectory(prefix="agentcaravan-verification-record-") as temporary:
            path = Path(temporary) / "record.json"
            path.write_text(json.dumps(valid_record()), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(cli_main(["validate-verification-record", str(path)]), 0)

        report = json.loads(output.getvalue())
        self.assertTrue(report["valid"])
        self.assertEqual(report["scenario"]["id"], "dependency-wait-with-independent-work")
        self.assertFalse(report["evidence_authenticity_checked"])
        self.assertEqual(report["evidence_reference_count"], 1)

    def test_cli_rejects_invalid_verification_record(self):
        with tempfile.TemporaryDirectory(prefix="agentcaravan-verification-record-") as temporary:
            path = Path(temporary) / "record.json"
            record = valid_record()
            record["result"]["status"] = "unsupported"
            path.write_text(json.dumps(record), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(cli_main(["validate-verification-record", str(path)]), 1)

        report = json.loads(output.getvalue())
        self.assertFalse(report["valid"])
        self.assertTrue(report["diagnostics"])


if __name__ == "__main__":
    unittest.main()
