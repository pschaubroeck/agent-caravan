import copy
import unittest

from jsonschema import ValidationError

from agentcaravan.schema_validation import (
    validate_framework_artifacts,
    validate_markdown_artifact_metadata,
)


def valid_artifacts():
    return [
        {"artifact_type": "role", "id": "engineer", "version": "1.0.0", "scope": "shared", "mission": "Implement work.", "responsibilities": ["implementation"]},
        {"artifact_type": "team-blueprint", "id": "core-team", "version": "1.0.0", "scope": "shared", "core_roles": ["engineer"]},
        {"artifact_type": "organization-catalog", "id": "org", "version": "1.0.0", "scope": "organization", "published_artifacts": {"role": ["engineer"], "team-blueprint": ["core-team"], "team-instance": ["team"], "domain-pack": ["domain"], "specialization-pack": ["specialization"], "overlay": ["overlay"], "runtime-adapter": ["adapter"]}},
        {"artifact_type": "team-instance", "id": "team", "version": "1.0.0", "scope": "organization", "organization_catalog_id": "org", "team_blueprint_id": "core-team", "role_overlays": ["overlay"], "domain_packs": ["domain"], "specialization_packs": ["specialization"], "runtime_defaults": ["adapter"]},
        {"artifact_type": "domain-pack", "id": "domain", "version": "1.0.0", "scope": "organization", "domain_type": "platform", "base_role_ids": ["engineer"]},
        {"artifact_type": "specialization-pack", "id": "specialization", "version": "1.0.0", "scope": "team", "owner_team_instance_id": "team", "parent_domain_id": "domain"},
        {"artifact_type": "overlay", "id": "overlay", "version": "1.0.0", "scope": "team", "operation": "add", "added_artifact_type": "role", "added_artifact_id": "engineer"},
        {"artifact_type": "runtime-adapter", "id": "adapter", "version": "1.0.0", "scope": "shared", "capabilities": {}},
        {"artifact_type": "runtime-profile", "id": "binding", "version": "1.0.0", "scope": "shared", "target_adapter_id": "adapter", "target_team_blueprint_id": "core-team"},
        {"artifact_type": "execution-profile", "id": "basic", "version": "1.0.0", "scope": "shared", "entry_roles": ["engineer"], "activation_policy": {}, "topology": {"mode": "sequential", "task_ownership": "caller-retains", "handoff_semantics": "mixed", "supported_modes": ["sequential"]}, "stages": [{"id": "work", "roles": ["engineer"]}], "termination": {}, "escalation": {}},
    ]


class PortableArtifactValidationTests(unittest.TestCase):
    def test_validates_markdown_artifact_identity_metadata(self):
        metadata = validate_markdown_artifact_metadata(
            "# Role Artifact: engineer\n\n"
            "- `id`: `engineer`\n"
            "- `version`: `1.0.0`\n"
            "- `scope`: `shared`\n"
        )
        self.assertEqual(
            metadata,
            {"artifact_type": "role", "id": "engineer", "version": "1.0.0", "scope": "shared"},
        )

    def test_rejects_markdown_artifact_id_that_differs_from_heading(self):
        with self.assertRaisesRegex(ValueError, "does not match metadata id"):
            validate_markdown_artifact_metadata(
                "# Role Artifact: engineer\n\n"
                "- `id`: `different-role`\n"
                "- `version`: `1.0.0`\n"
                "- `scope`: `shared`\n"
            )

    def test_validates_serialized_artifact_schemas_and_cross_references(self):
        summary = validate_framework_artifacts(valid_artifacts())
        self.assertEqual(summary, {"artifacts": 10, "types": 10})

    def test_rejects_unresolved_published_reference(self):
        artifacts = valid_artifacts()
        artifacts[2]["published_artifacts"]["role"] = ["missing-role"]
        with self.assertRaisesRegex(ValueError, "unresolved published_artifacts reference role:missing-role"):
            validate_framework_artifacts(artifacts)

    def test_rejects_duplicate_logical_identity(self):
        artifacts = valid_artifacts()
        artifacts.append(copy.deepcopy(artifacts[0]))
        with self.assertRaisesRegex(ValueError, "duplicate artifact: role:engineer"):
            validate_framework_artifacts(artifacts)

    def test_rejects_invalid_scope_during_schema_validation(self):
        artifacts = valid_artifacts()
        artifacts[0]["scope"] = "global"
        with self.assertRaises(ValidationError):
            validate_framework_artifacts(artifacts)

    def test_rejects_overlay_broader_than_target_scope(self):
        artifacts = [
            {"artifact_type": "role", "id": "target", "version": "1.0.0", "scope": "team", "mission": "Target.", "responsibilities": ["work"]},
            {"artifact_type": "role", "id": "replacement", "version": "1.0.0", "scope": "shared", "mission": "Replacement.", "responsibilities": ["work"]},
            {"artifact_type": "overlay", "id": "overlay", "version": "1.0.0", "scope": "organization", "operation": "replace", "target_artifact_type": "role", "target_artifact_id": "target", "replacement_artifact_type": "role", "replacement_artifact_id": "replacement"},
        ]
        with self.assertRaisesRegex(ValueError, "broader than its target scope"):
            validate_framework_artifacts(artifacts)

    def test_add_overlay_declares_added_artifact_without_existing_target(self):
        artifacts = [
            {"artifact_type": "role", "id": "added", "version": "1.0.0", "scope": "team", "mission": "Added role.", "responsibilities": ["work"]},
            {"artifact_type": "overlay", "id": "add-role", "version": "1.0.0", "scope": "team", "operation": "add", "added_artifact_type": "role", "added_artifact_id": "added"},
        ]
        self.assertEqual(validate_framework_artifacts(artifacts), {"artifacts": 2, "types": 2})


if __name__ == "__main__":
    unittest.main()
