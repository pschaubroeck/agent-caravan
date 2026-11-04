import json
from pathlib import Path
import tempfile
import unittest

from jsonschema import ValidationError

from agentcaravan.schema_validation import validate_artifact, validate_packaged_artifact


ROOT = Path(__file__).resolve().parents[2]


class SchemaValidationTests(unittest.TestCase):
    def test_portable_plan_schema_accepts_optional_knowledge_context_and_legacy_plan(self):
        plan_path = ROOT / "tests" / "fixtures" / "portable-feature-delivery-plan.json"
        schema_path = ROOT / "resources" / "schemas" / "portable-execution-plan.schema.json"
        plan = json.loads(plan_path.read_text(encoding="utf-8"))

        validate_artifact(plan, schema_path)
        plan["knowledge_context"] = {
            "layers": [
                {
                    "artifact_type": "specialization-pack",
                    "id": "team-knowledge",
                    "version": "1.0.0",
                    "scope": "team",
                    "owner_team_instance_id": plan["context"]["team_instance_id"],
                    "knowledge_surface": ["owned product workflows"],
                    "trusted_sources": ["https://docs.example.org/product"],
                    "documentation_references": [
                        {"uri": "https://docs.example.org/product/overview.md", "media_type": "text/markdown"}
                    ],
                    "loading_guidance": ["load the parent domain first"],
                    "role_guidance": {"engineer": "Preserve workflow invariants."},
                }
            ]
        }

        validate_artifact(plan, schema_path)

    def test_role_artifact_accepts_explicit_markdown_documentation_reference(self):
        role = {
            "artifact_type": "role", "id": "engineer", "version": "1.0.0",
            "scope": "shared", "mission": "Implement approved changes.",
            "responsibilities": ["Deliver code changes."],
            "documentation_references": [
                {"uri": "https://gitlab.example.org/team/engineer.md", "media_type": "text/markdown"}
            ],
        }
        validate_packaged_artifact(role, "role.schema.json")

    def test_validates_repository_execution_profile_artifact(self):
        artifact_path = (
            ROOT
            / "resources"
            / "execution"
            / "workflows"
            / "information-technology-core-team-feature-delivery.json"
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

        validate_packaged_artifact(artifact, "execution-profile.schema.json")

    def test_resolves_local_sibling_reference_and_rejects_invalid_instance(self):
        with tempfile.TemporaryDirectory(prefix="agentcaravan-schema-validation-") as temporary_root:
            schema_directory = Path(temporary_root)
            (schema_directory / "artifact.schema.json").write_text(
                json.dumps(
                    {
                        "$schema": "https://json-schema.org/draft/2020-12/schema",
                        "$id": "agentfoundry/artifact.schema.json",
                        "type": "object",
                        "required": ["details"],
                        "properties": {
                            "details": {"$ref": "details.schema.json"},
                        },
                    }
                ),
                encoding="utf-8",
            )
            (schema_directory / "details.schema.json").write_text(
                json.dumps(
                    {
                        "$schema": "https://json-schema.org/draft/2020-12/schema",
                        "$id": "agentfoundry/details.schema.json",
                        "type": "object",
                        "required": ["owner"],
                        "properties": {"owner": {"type": "string", "minLength": 1}},
                        "additionalProperties": False,
                    }
                ),
                encoding="utf-8",
            )
            schema_path = schema_directory / "artifact.schema.json"

            validate_artifact({"details": {"owner": "platform-team"}}, schema_path)

            with self.assertRaises(ValidationError):
                validate_artifact({"details": {"owner": ""}}, schema_path)

    def test_does_not_retrieve_remote_schema_references(self):
        with tempfile.TemporaryDirectory(prefix="agentcaravan-schema-remote-") as temporary_root:
            schema_path = Path(temporary_root) / "remote.schema.json"
            schema_path.write_text(
                json.dumps(
                    {
                        "$schema": "https://json-schema.org/draft/2020-12/schema",
                        "type": "object",
                        "properties": {
                            "details": {"$ref": "https://schemas.example.invalid/details.json"},
                        },
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(Exception) as error:
                validate_artifact({"details": {}}, schema_path)
            self.assertIn("unresolvable", str(error.exception).lower())


if __name__ == "__main__":
    unittest.main()
