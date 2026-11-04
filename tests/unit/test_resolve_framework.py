import copy
import json
import tempfile
import unittest
from pathlib import Path

from agentcaravan.bundle_sources import BundleSourceError, InMemoryBundleSource, LocalJsonBundleSource
from agentcaravan.execution_plan import build_portable_execution_plan
from agentcaravan.org_framework_layout import DEFAULT_CONFIG, SUBDIRECTORIES, bootstrap
from agentcaravan.profile import ProfileError, load_profile
from agentcaravan.resolve_framework import (
    AmbiguousOverlayError,
    FrameworkResolver,
    ResolutionError,
    resolve_source,
    resolve_profile,
    resolve_bundle,
)
from tools.init_agentcaravan import _refresh_repository_sources


FIXTURE = Path(__file__).parents[1] / "fixtures" / "sample-product-engineer-ii.json"


def load_fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class FrameworkResolverTests(unittest.TestCase):
    def test_resolver_reports_missing_selected_team(self):
        bundle = load_fixture()
        bundle["context"].pop("team_instance_id")

        with self.assertRaisesRegex(ResolutionError, "active profile has no selected team"):
            resolve_bundle(bundle)

    def test_resolves_effective_engineer_ii_role(self):
        bundle = load_fixture()

        result = resolve_bundle(bundle)

        self.assertEqual(result["status"], "pass")
        evidence = result["validation_evidence"]
        self.assertEqual(evidence["team_coverage"]["status"], "pass")
        self.assertEqual(
            evidence["runtime_capability_compatibility"]["status"], "pass"
        )
        self.assertEqual(evidence["runtime_verification"]["status"], "unverified")
        self.assertEqual(evidence["task_behavior_evaluation"]["status"], "not-evaluated")
        implementation = next(
            item for item in evidence["team_coverage"]["requirements"]
            if item["name"] == "implementation"
        )
        self.assertEqual(implementation["satisfied_by"][0]["role_id"], "engineer-ii")
        self.assertEqual(
            implementation["satisfied_by"][0]["source"],
            {
                "kind": "overlay-replacement",
                "artifact_id": "sample-product-engineer-ii",
                "replaces_role_id": "engineer",
            },
        )
        self.assertEqual(result["runtime"]["runtime_profile_id"], bundle["context"]["runtime_profile_id"])
        self.assertNotIn("binding_id", result["runtime"])
        self.assertEqual(result["role_replacements"], {"engineer": "engineer-ii"})
        self.assertEqual(
            result["effective_team"]["core_roles"],
            [
                "program-manager",
                "product-owner",
                "tech-owner",
                "engineer-ii",
                "quality-engineer",
                "software-architect",
                "release-manager",
            ],
        )
        self.assertEqual(result["effective_team"]["debate_participants"]["review resolution debate"][0], "engineer-ii")
        self.assertIn("engineer-ii", result["effective_team"]["documentation_ownership"])
        self.assertNotIn("engineer", result["effective_team"]["documentation_ownership"])
        self.assertEqual(result["effective_roles"][3]["source_chain"], ["engineer", "engineer-ii"])

    def test_custom_adapter_repository_guidance_uses_partial_profile_override(self):
        bundle = load_fixture()
        adapter = next(item for item in bundle["artifacts"] if item["artifact_type"] == "runtime-adapter")
        previous_id = adapter["id"]
        custom_id = "my-custom-codex-adapter"
        adapter["id"] = custom_id
        adapter["repository_guidance"] = {
            "native_files": ["AGENTS.md"],
            "discovery": "automatic",
            "reference_policy": "entrypoint-only",
        }
        runtime_profile = next(item for item in bundle["artifacts"] if item["artifact_type"] == "runtime-profile")
        runtime_profile["target_adapter_id"] = custom_id
        catalog = next(item for item in bundle["artifacts"] if item["artifact_type"] == "organization-catalog")
        catalog["published_artifacts"]["runtime-adapter"] = [
            custom_id if artifact_id == previous_id else artifact_id
            for artifact_id in catalog["published_artifacts"]["runtime-adapter"]
        ]
        team = next(item for item in bundle["artifacts"] if item["artifact_type"] == "team-instance")
        team["runtime_defaults"] = [custom_id]
        bundle["context"]["runtime_adapter_id"] = custom_id
        bundle["adapter_overrides"] = {
            custom_id: {"repository_guidance": {"native_files": ["TEAM_GUIDANCE.md"]}}
        }

        result = resolve_bundle(bundle)

        self.assertEqual(
            result["runtime"]["repository_guidance"],
            {
                "canonical_file": "AGENTS.md",
                "native_files": ["TEAM_GUIDANCE.md"],
                "discovery": "automatic",
                "reference_policy": "entrypoint-only",
            },
        )

    def test_resolver_rejects_unsupported_adapter_override_fields(self):
        bundle = load_fixture()
        adapter_id = bundle["context"]["runtime_adapter_id"]
        bundle["adapter_overrides"] = {adapter_id: {"repository_guidance": {"unknown": True}}}

        with self.assertRaisesRegex(ResolutionError, "unsupported repository_guidance override fields"):
            resolve_bundle(bundle)

    def test_resolver_preserves_selected_knowledge_artifact_content(self):
        bundle = load_fixture()
        domain = next(item for item in bundle["artifacts"] if item["artifact_type"] == "domain-pack")
        specialization = next(item for item in bundle["artifacts"] if item["artifact_type"] == "specialization-pack")
        domain["purpose"] = "Shared product context."
        domain["trusted_sources"] = ["https://docs.example.org/product"]
        specialization["knowledge_surface"] = ["partner contracts"]
        specialization["role_guidance"] = {"engineer": "Preserve idempotency."}

        result = resolve_bundle(bundle)

        self.assertEqual(result["domain_packs"][0]["purpose"], "Shared product context.")
        self.assertEqual(result["domain_packs"][0]["trusted_sources"], ["https://docs.example.org/product"])
        self.assertEqual(result["specialization_packs"][0]["knowledge_surface"], ["partner contracts"])
        self.assertEqual(result["specialization_packs"][0]["role_guidance"]["engineer"], "Preserve idempotency.")

    def test_resolution_does_not_mutate_base_template(self):
        bundle = load_fixture()
        template = next(
            artifact
            for artifact in bundle["artifacts"]
            if artifact["artifact_type"] == "team-blueprint"
        )
        original_roles = copy.deepcopy(template["core_roles"])

        resolve_bundle(bundle)

        self.assertEqual(template["core_roles"], original_roles)

    def test_team_workspace_must_be_confined_to_active_profile(self):
        bundle = load_fixture()
        team = next(artifact for artifact in bundle["artifacts"] if artifact["artifact_type"] == "team-instance")
        team["team_context"] = {"authoring_workspace": "../outside"}
        with tempfile.TemporaryDirectory() as temporary:
            bundle["profile_root"] = temporary
            with self.assertRaisesRegex(ResolutionError, "under the profile teams directory"):
                resolve_bundle(bundle)

    def test_team_workspace_must_not_be_absolute(self):
        bundle = load_fixture()
        team = next(artifact for artifact in bundle["artifacts"] if artifact["artifact_type"] == "team-instance")
        team["team_context"] = {"authoring_workspace": "/tmp/unrelated-team"}
        with tempfile.TemporaryDirectory() as temporary:
            bundle["profile_root"] = temporary
            with self.assertRaisesRegex(ResolutionError, "must be relative"):
                resolve_bundle(bundle)

    def test_equal_priority_overlays_are_ambiguous(self):
        bundle = load_fixture()
        bundle["artifacts"].append(
            {
                "artifact_type": "overlay",
                "id": "conflicting-engineer-overlay",
                "version": "1.0.0",
                "scope": "team",
                "operation": "replace",
                "priority": 100,
                "target_artifact_type": "team-instance",
                "target_artifact_id": "sample-product-integrations-team",
                "target_role_id": "engineer",
                "replacement_artifact_type": "role",
                "replacement_role_id": "engineer",
            }
        )
        catalog = next(
            artifact
            for artifact in bundle["artifacts"]
            if artifact["artifact_type"] == "organization-catalog"
        )
        catalog["published_artifacts"]["overlay"].append("conflicting-engineer-overlay")
        bundle["artifacts"][
            next(
                index
                for index, artifact in enumerate(bundle["artifacts"])
                if artifact["artifact_type"] == "team-instance"
            )
        ]["role_overlays"].append("conflicting-engineer-overlay")

        with self.assertRaises(AmbiguousOverlayError):
            resolve_bundle(bundle)

    def test_unsupported_required_capability_fails(self):
        bundle = load_fixture()
        binding = next(
            artifact
            for artifact in bundle["artifacts"]
            if artifact["artifact_type"] == "runtime-profile"
        )
        binding["required_capabilities"].append("unsupported-capability")

        with self.assertRaisesRegex(
            ResolutionError,
            "runtime profile requires unsupported capabilities: unsupported-capability",
        ):
            resolve_bundle(bundle)

    def test_native_capability_support_requirement_rejects_adapted_runtime(self):
        bundle = load_fixture()
        binding = next(
            artifact
            for artifact in bundle["artifacts"]
            if artifact["artifact_type"] == "runtime-profile"
        )
        binding["capability_support_requirements"] = {"parallel_lane_execution": "native"}

        with self.assertRaisesRegex(ResolutionError, "requires native"):
            resolve_bundle(bundle)

    def test_add_and_suppress_optional_role(self):
        bundle = load_fixture()
        bundle["artifacts"].extend(
            [
                {
                    "artifact_type": "role",
                    "id": "incident-coordinator",
                    "version": "1.0.0",
                    "scope": "organization",
                },
                {
                    "artifact_type": "overlay",
                    "id": "add-incident-coordinator",
                    "version": "1.0.0",
                    "scope": "team",
                    "operation": "add",
                    "priority": 10,
                    "target_artifact_type": "team-instance",
                    "target_artifact_id": "sample-product-integrations-team",
                    "added_artifact_type": "role",
                    "added_artifact_id": "incident-coordinator",
                    "target_collection": "core_roles",
                },
                {
                    "artifact_type": "overlay",
                    "id": "suppress-incident-coordinator",
                    "version": "1.0.0",
                    "scope": "team",
                    "operation": "suppress",
                    "priority": 20,
                    "target_artifact_type": "team-instance",
                    "target_artifact_id": "sample-product-integrations-team",
                    "suppressed_artifact_type": "role",
                    "suppressed_artifact_id": "incident-coordinator",
                    "reason": "Keep the optional lane disabled for this team variant.",
                },
                {
                    "artifact_type": "overlay",
                    "id": "extend-optional-incident-references",
                    "version": "1.0.0",
                    "scope": "team",
                    "operation": "extend",
                    "priority": 15,
                    "target_artifact_type": "team-instance",
                    "target_artifact_id": "sample-product-integrations-team",
                    "changes": {
                        "stage_owners": ["incident-coordinator"],
                        "triggered_debates": ["optional incident review"],
                        "debate_participants": {
                            "optional incident review": ["incident-coordinator"]
                        },
                    },
                },
            ]
        )
        catalog = next(
            artifact
            for artifact in bundle["artifacts"]
            if artifact["artifact_type"] == "organization-catalog"
        )
        catalog["published_artifacts"]["role"].append("incident-coordinator")
        catalog["published_artifacts"]["overlay"].extend(
            [
                "add-incident-coordinator",
                "extend-optional-incident-references",
                "suppress-incident-coordinator",
            ]
        )
        team_instance = next(
            artifact
            for artifact in bundle["artifacts"]
            if artifact["artifact_type"] == "team-instance"
        )
        team_instance["role_overlays"].extend(
            [
                "add-incident-coordinator",
                "extend-optional-incident-references",
                "suppress-incident-coordinator",
            ]
        )

        result = resolve_bundle(bundle)

        self.assertNotIn("incident-coordinator", result["effective_team"]["core_roles"])
        self.assertNotIn("incident-coordinator", result["effective_team"]["stage_owners"])
        self.assertEqual(
            result["effective_team"]["debate_participants"]["optional incident review"],
            [],
        )
        self.assertEqual(result["validation_evidence"]["team_coverage"]["status"], "pass")
        incident_source = next(
            item["source"]
            for item in result["validation_evidence"]["team_coverage"]["effective_role_sources"]
            if item["role_id"] == "engineer-ii"
        )
        self.assertEqual(incident_source["kind"], "overlay-replacement")
        self.assertEqual(
            [detail["operation"] for detail in result["overlay_details"]],
            ["add", "extend", "suppress", "replace"],
        )

    def test_extend_changes_effective_team_without_mutating_template(self):
        bundle = load_fixture()
        bundle["artifacts"].append(
            {
                "artifact_type": "overlay",
                "id": "extend-enrollment-team",
                "version": "1.0.0",
                "scope": "team",
                "operation": "extend",
                "priority": 200,
                "target_artifact_type": "team-instance",
                "target_artifact_id": "sample-product-integrations-team",
                "changes": {"team_variant": "senior-implementation-lane"},
            }
        )
        catalog = next(
            artifact
            for artifact in bundle["artifacts"]
            if artifact["artifact_type"] == "organization-catalog"
        )
        catalog["published_artifacts"]["overlay"].append("extend-enrollment-team")
        team_instance = next(
            artifact
            for artifact in bundle["artifacts"]
            if artifact["artifact_type"] == "team-instance"
        )
        team_instance["role_overlays"].append("extend-enrollment-team")

        result = resolve_bundle(bundle)

        self.assertEqual(result["effective_team"]["team_variant"], "senior-implementation-lane")
        template = next(
            artifact
            for artifact in bundle["artifacts"]
            if artifact["artifact_type"] == "team-blueprint"
        )
        self.assertNotIn("team_variant", template)

    def test_extend_role_provenance_tracks_the_overlay_that_added_each_role(self):
        bundle = load_fixture()
        blueprint = next(
            artifact for artifact in bundle["artifacts"]
            if artifact["artifact_type"] == "team-blueprint"
        )
        original_roles = list(blueprint["core_roles"])
        added_roles = ["security-reviewer", "risk-analyst"]
        bundle["artifacts"].extend(
            [
                {
                    "artifact_type": "role",
                    "id": role_id,
                    "version": "1.0.0",
                    "scope": "organization",
                }
                for role_id in added_roles
            ]
            + [
                {
                    "artifact_type": "overlay",
                    "id": "extend-security-reviewer",
                    "version": "1.0.0",
                    "scope": "team",
                    "operation": "extend",
                    "priority": 300,
                    "target_artifact_type": "team-instance",
                    "target_artifact_id": "sample-product-integrations-team",
                    "changes": {"core_roles": original_roles + [added_roles[0]]},
                },
                {
                    "artifact_type": "overlay",
                    "id": "extend-risk-analyst",
                    "version": "1.0.0",
                    "scope": "team",
                    "operation": "extend",
                    "priority": 400,
                    "target_artifact_type": "team-instance",
                    "target_artifact_id": "sample-product-integrations-team",
                    "changes": {"core_roles": original_roles + added_roles},
                },
            ]
        )
        catalog = next(
            artifact for artifact in bundle["artifacts"]
            if artifact["artifact_type"] == "organization-catalog"
        )
        catalog["published_artifacts"]["role"].extend(added_roles)
        catalog["published_artifacts"]["overlay"].extend(
            ["extend-security-reviewer", "extend-risk-analyst"]
        )
        team_instance = next(
            artifact for artifact in bundle["artifacts"]
            if artifact["artifact_type"] == "team-instance"
        )
        team_instance["role_overlays"].extend(
            ["extend-security-reviewer", "extend-risk-analyst"]
        )

        result = resolve_bundle(bundle)

        sources = {
            item["role_id"]: item["source"]
            for item in result["validation_evidence"]["team_coverage"]["effective_role_sources"]
        }
        self.assertEqual(
            sources["security-reviewer"],
            {"kind": "overlay-extend", "artifact_id": "extend-security-reviewer"},
        )
        self.assertEqual(
            sources["risk-analyst"],
            {"kind": "overlay-extend", "artifact_id": "extend-risk-analyst"},
        )

    def test_higher_priority_overlay_wins(self):
        bundle = load_fixture()
        bundle["artifacts"].extend(
            [
                {
                    "artifact_type": "role",
                    "id": "engineer-iii",
                    "version": "1.0.0",
                    "scope": "organization",
                    "extends": "engineer",
                    "purpose": "Owns senior implementation decisions.",
                },
                {
                    "artifact_type": "overlay",
                    "id": "higher-priority-engineer-iii",
                    "version": "1.0.0",
                    "scope": "team",
                    "operation": "replace",
                    "priority": 200,
                    "target_artifact_type": "team-instance",
                    "target_artifact_id": "sample-product-integrations-team",
                    "target_role_id": "engineer",
                    "replacement_artifact_type": "role",
                    "replacement_role_id": "engineer-iii",
                },
            ]
        )
        catalog = next(
            artifact
            for artifact in bundle["artifacts"]
            if artifact["artifact_type"] == "organization-catalog"
        )
        catalog["published_artifacts"]["role"].append("engineer-iii")
        catalog["published_artifacts"]["overlay"].append("higher-priority-engineer-iii")
        team_instance = next(
            artifact
            for artifact in bundle["artifacts"]
            if artifact["artifact_type"] == "team-instance"
        )
        team_instance["role_overlays"].append("higher-priority-engineer-iii")

        result = resolve_bundle(bundle)

        self.assertEqual(result["role_replacements"]["engineer"], "engineer-iii")
        engineer = next(role for role in result["effective_roles"] if role["id"] == "engineer-iii")
        self.assertEqual(engineer["source_chain"], ["engineer", "engineer-iii"])
        self.assertEqual(engineer["role"]["purpose"], "Owns senior implementation decisions.")
        self.assertEqual(
            result["provenance"]["overlay_order"],
            ["sample-product-engineer-ii", "higher-priority-engineer-iii"],
        )

        reordered_bundle = copy.deepcopy(bundle)
        reordered_bundle["artifacts"].reverse()
        reordered_team = next(
            artifact
            for artifact in reordered_bundle["artifacts"]
            if artifact["artifact_type"] == "team-instance"
        )
        reordered_team["role_overlays"].reverse()
        reordered_result = resolve_bundle(reordered_bundle)
        reordered_engineer = next(
            role for role in reordered_result["effective_roles"] if role["id"] == "engineer-iii"
        )

        self.assertEqual(reordered_result["role_replacements"], result["role_replacements"])
        self.assertEqual(reordered_engineer, engineer)
        self.assertEqual(
            reordered_result["provenance"]["overlay_order"],
            result["provenance"]["overlay_order"],
        )

    def test_required_adapted_capability_is_degraded_or_blocked_by_profile(self):
        bundle = load_fixture()
        binding = next(
            artifact
            for artifact in bundle["artifacts"]
            if artifact["artifact_type"] == "runtime-profile"
        )
        binding["required_capabilities"].append("parallel_lane_execution")

        with self.assertRaises(ResolutionError):
            resolve_bundle(bundle)

        bundle["context"]["validation_profile_id"] = "local-experimental"
        result = resolve_bundle(bundle)

        self.assertEqual(result["status"], "degraded")
        self.assertIn("parallel_lane_execution:adapted", result["runtime"]["degraded_capabilities"])
        self.assertEqual(
            result["validation_evidence"]["runtime_capability_compatibility"]["status"],
            "degraded",
        )
        self.assertEqual(result["validation_evidence"]["runtime_verification"]["status"], "unverified")

    def test_suppressing_required_role_fails_coverage(self):
        bundle = load_fixture()
        bundle["artifacts"].append(
            {
                "artifact_type": "overlay",
                "id": "suppress-required-quality-engineer",
                "version": "1.0.0",
                "scope": "team",
                "operation": "suppress",
                "priority": 200,
                "target_artifact_type": "team-instance",
                "target_artifact_id": "sample-product-integrations-team",
                "suppressed_artifact_type": "role",
                "suppressed_artifact_id": "quality-engineer",
                "reason": "Invalid test suppression.",
            }
        )
        catalog = next(
            artifact
            for artifact in bundle["artifacts"]
            if artifact["artifact_type"] == "organization-catalog"
        )
        catalog["published_artifacts"]["overlay"].append("suppress-required-quality-engineer")
        team_instance = next(
            artifact
            for artifact in bundle["artifacts"]
            if artifact["artifact_type"] == "team-instance"
        )
        team_instance["role_overlays"].append("suppress-required-quality-engineer")

        with self.assertRaises(ResolutionError) as raised:
            resolve_bundle(bundle)
        report = raised.exception.diagnostics["team_coverage"]
        self.assertEqual(report["status"], "fail")
        self.assertIn(
            {"kind": "coverage-requirement", "name": "quality"},
            report["issues"],
        )
        self.assertIn(
            {
                "kind": "mandatory-debate",
                "name": "solution + testability debate",
                "missing_role_ids": ["quality-engineer"],
            },
            report["issues"],
        )
        self.assertIn(
            {
                "kind": "suppressed-role-reference",
                "path": "coverage_requirements.quality",
                "role_id": "quality-engineer",
            },
            report["issues"],
        )
        self.assertIn(
            {
                "kind": "suppressed-role-reference",
                "path": "debate_participants.solution + testability debate",
                "role_id": "quality-engineer",
            },
            report["issues"],
        )
        self.assertIn(
            {"kind": "blocking-lane", "role_id": "quality-engineer"},
            report["issues"],
        )

    def test_role_inheritance_cycles_are_rejected(self):
        bundle = load_fixture()
        bundle["artifacts"].extend(
            [
                {
                    "artifact_type": "role",
                    "id": "cycle-a",
                    "version": "1.0.0",
                    "scope": "organization",
                    "extends": "cycle-b",
                },
                {
                    "artifact_type": "role",
                    "id": "cycle-b",
                    "version": "1.0.0",
                    "scope": "organization",
                    "extends": "cycle-a",
                },
            ]
        )

        resolver = FrameworkResolver(bundle)

        with self.assertRaises(ResolutionError):
            resolver._effective_role(resolver.artifact("role", "cycle-a"))

    def test_custom_validation_profile_artifact_controls_degradation(self):
        bundle = load_fixture()
        bundle["context"]["validation_profile_id"] = "custom-team-profile"
        bundle["artifacts"].extend(
            [
                {
                    "artifact_type": "validation-profile",
                    "id": "custom-team-profile",
                    "version": "1.0.0",
                    "scope": "team",
                    "policy": {"allow_degraded": True},
                }
            ]
        )
        binding = next(
            artifact
            for artifact in bundle["artifacts"]
            if artifact["artifact_type"] == "runtime-profile"
        )
        binding["required_capabilities"].append("parallel_lane_execution")
        catalog = next(
            artifact
            for artifact in bundle["artifacts"]
            if artifact["artifact_type"] == "organization-catalog"
        )
        catalog["published_artifacts"]["validation-profile"] = ["custom-team-profile"]

        result = resolve_bundle(bundle)

        self.assertEqual(result["validation_profile_id"], "custom-team-profile")
        self.assertEqual(result["status"], "degraded")

    def test_local_json_source_resolves_through_storage_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bundle.json"
            path.write_text(json.dumps(load_fixture()), encoding="utf-8")

            result = resolve_source(LocalJsonBundleSource(path))

        self.assertEqual(result["context"]["team_instance_id"], "sample-product-integrations-team")

    def test_in_memory_source_has_same_resolution_contract(self):
        result = resolve_source(InMemoryBundleSource(load_fixture()))

        self.assertEqual(result["role_replacements"], {"engineer": "engineer-ii"})

    def test_local_json_source_rejects_missing_or_invalid_files(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = LocalJsonBundleSource(Path(directory) / "missing.json")
            invalid_path = Path(directory) / "invalid.json"
            invalid_path.write_text("not json", encoding="utf-8")
            invalid = LocalJsonBundleSource(invalid_path)

            with self.assertRaises(BundleSourceError):
                missing.load()
            with self.assertRaises(BundleSourceError):
                invalid.load()

    def test_org_framework_bootstrap_creates_repeatable_local_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "org-framework"

            bootstrap(root)

            self.assertEqual(set(path.name for path in root.iterdir()), set(SUBDIRECTORIES) | {"config.json"})
            self.assertEqual(json.loads((root / "config.json").read_text()), DEFAULT_CONFIG)

            config = {"custom": "preserve-me"}
            (root / "config.json").write_text(json.dumps(config), encoding="utf-8")
            bootstrap(root)

            self.assertEqual(json.loads((root / "config.json").read_text()), config)

    def test_reinitialization_refreshes_managed_repository_sources(self):
        config = {
            "sources": [
                "/old/checkout/resources/core/agentcaravan-core-team.json",
                "/external/catalog",
            ],
            "managed_sources": {
                "agentcaravan_repository": {
                    "root": "/old/checkout",
                    "paths": ["/old/checkout/resources/core/agentcaravan-core-team.json"],
                }
            },
        }

        _refresh_repository_sources(config, Path("/new/checkout"))

        self.assertIn("/external/catalog", config["sources"])
        self.assertNotIn("/old/checkout/resources/core/agentcaravan-core-team.json", config["sources"])
        self.assertIn("/new/checkout/resources/core/agentcaravan-core-team.json", config["sources"])
        self.assertEqual(config["managed_sources"]["agentcaravan_repository"]["root"], "/new/checkout")

    def test_profile_loads_bundle_files_from_configured_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "org-framework"
            source = root / "sources" / "example"
            source.mkdir(parents=True)
            bundle = load_fixture()
            (source / "bundle.json").write_text(json.dumps(bundle), encoding="utf-8")
            (root / "config.json").write_text(
                json.dumps(
                    {
                        "sources": ["sources/example"],
                        "active_context": bundle["context"],
                    }
                ),
                encoding="utf-8",
            )

            profile = load_profile(root)

        self.assertEqual(profile["context"], bundle["context"])
        self.assertEqual(len(profile["artifacts"]), len(bundle["artifacts"]))

    def test_profile_rejects_duplicate_artifact_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "org-framework"
            source = root / "sources" / "example"
            source.mkdir(parents=True)
            role = {"artifact_type": "role", "id": "engineer", "version": "1.0.0", "scope": "organization"}
            (source / "one.json").write_text(json.dumps(role), encoding="utf-8")
            (source / "two.json").write_text(json.dumps(role), encoding="utf-8")
            (root / "config.json").write_text(json.dumps({"sources": ["sources/example"]}), encoding="utf-8")

            with self.assertRaises(ProfileError):
                load_profile(root)

    def test_profile_rejects_malformed_configured_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "org-framework"
            source = root / "sources" / "example"
            source.mkdir(parents=True)
            (source / "broken.json").write_text("{", encoding="utf-8")
            (root / "config.json").write_text(json.dumps({"sources": ["sources/example"]}), encoding="utf-8")

            with self.assertRaises(ProfileError):
                load_profile(root)

    def test_profile_resolution_uses_active_context(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "org-framework"
            source = root / "sources" / "example"
            source.mkdir(parents=True)
            bundle = load_fixture()
            (source / "bundle.json").write_text(json.dumps(bundle), encoding="utf-8")
            adapter_id = bundle["context"]["runtime_adapter_id"]
            guidance_override = {adapter_id: {"repository_guidance": {"native_files": ["TEAM_GUIDANCE.md"]}}}
            (root / "config.json").write_text(
                json.dumps({
                    "sources": ["sources/example"],
                    "active_context": bundle["context"],
                    "adapter_overrides": guidance_override,
                }),
                encoding="utf-8",
            )

            result = resolve_profile(root)

        self.assertEqual(result["context"]["team_instance_id"], "sample-product-integrations-team")
        self.assertEqual(
            result["runtime"]["repository_guidance"]["native_files"],
            ["TEAM_GUIDANCE.md"],
        )

    def test_execution_profile_is_validated_and_returned_when_selected(self):
        bundle = load_fixture()
        profile_path = Path(__file__).parents[2] / "resources" / "execution" / "workflows" / "information-technology-core-team-feature-delivery.json"
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        profile["runtime_profile_id"] = bundle["context"]["runtime_profile_id"]
        policy_path = Path(__file__).parents[2] / "resources" / "execution" / "policies" / "information-technology-core-team-safety-policy.json"
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        bundle["artifacts"].append(profile)
        bundle["artifacts"].append(policy)
        catalog = next(artifact for artifact in bundle["artifacts"] if artifact["artifact_type"] == "organization-catalog")
        catalog["published_artifacts"]["execution-profile"] = [profile["id"]]
        catalog["published_artifacts"]["policy"] = [policy["id"]]
        bundle["context"]["execution_profile_id"] = profile["id"]

        result = resolve_bundle(bundle)

        self.assertEqual(result["context"]["execution_profile_id"], profile["id"])
        self.assertEqual(result["execution_profile"]["topology"]["mode"], "coordinator-worker")
        self.assertEqual(result["policies"][0]["id"], policy["id"])
        self.assertEqual(result["knowledge_access"]["external_sources"], "enabled")
        plan = build_portable_execution_plan(result, {"task_id": "feature-profile", "objective": "validate the feature profile"})
        self.assertEqual(len(plan["execution_topology"]["work_items"]), 7)

    def test_dependency_approval_experiment_profile_resolves_from_experiment_bundle(self):
        root = Path(__file__).parents[2]
        bundle = load_fixture()
        profile = json.loads(
            (root / "tests" / "conformance" / "experiments" / "dependency-approval" / "execution-profile.json").read_text(encoding="utf-8")
        )
        policy = json.loads(
            (root / "resources" / "execution" / "policies" / "information-technology-core-team-safety-policy.json").read_text(encoding="utf-8")
        )
        bundle["artifacts"].extend([profile, policy])
        catalog = next(item for item in bundle["artifacts"] if item["artifact_type"] == "organization-catalog")
        catalog["published_artifacts"].setdefault("execution-profile", []).append(profile["id"])
        catalog["published_artifacts"].setdefault("policy", []).append(policy["id"])
        bundle["context"]["execution_profile_id"] = profile["id"]

        result = resolve_bundle(bundle)

        self.assertEqual(result["context"]["execution_profile_id"], "dependency-approval-experiment")
        self.assertEqual(result["execution_profile"]["team_blueprint_id"], "information-technology-core-team")
        self.assertEqual(
            [item["id"] for item in result["execution_profile"]["stages"]],
            ["need-assessment", "candidate-assessment", "independent-review", "dependency-change", "human-approval", "verification", "rejection", "completion"],
        )
        self.assertIn("information-technology-core-team-safety-policy", [item["id"] for item in result["policies"]])

    def test_execution_profile_cannot_reference_an_unresolved_role(self):
        bundle = load_fixture()
        profile = {
            "artifact_type": "execution-profile",
            "id": "invalid-profile",
            "version": "1.0.0",
            "scope": "team",
            "team_blueprint_id": "information-technology-core-team",
            "entry_roles": ["missing-role"],
            "activation_policy": {"primary_roles": ["engineer"]},
            "topology": {"mode": "sequential"},
            "stages": [{"id": "implementation", "roles": ["engineer"], "output": "code"}],
            "termination": {"success_conditions": ["done"], "failure_conditions": ["blocked"]},
            "escalation": {"technical": "tech-owner"}
        }
        bundle["artifacts"].append(profile)
        catalog = next(artifact for artifact in bundle["artifacts"] if artifact["artifact_type"] == "organization-catalog")
        catalog["published_artifacts"]["execution-profile"] = [profile["id"]]
        bundle["context"]["execution_profile_id"] = profile["id"]

        with self.assertRaises(ResolutionError):
            resolve_bundle(bundle)

    def test_runtime_profile_must_declare_support_for_selected_workflow(self):
        bundle = load_fixture()
        profile = {
            "artifact_type": "execution-profile",
            "id": "other-workflow",
            "version": "1.0.0",
            "scope": "shared",
            "team_blueprint_id": "information-technology-core-team",
            "entry_roles": ["tech-owner"],
            "activation_policy": {"primary_roles": ["engineer"]},
            "topology": {"mode": "sequential"},
            "stages": [{"id": "implementation", "roles": ["engineer"], "output": "code"}],
            "termination": {"success_conditions": ["done"], "failure_conditions": ["blocked"]},
            "escalation": {"technical": "tech-owner"}
        }
        bundle["artifacts"].append(profile)
        binding = next(artifact for artifact in bundle["artifacts"] if artifact["artifact_type"] == "runtime-profile")
        binding["execution_profile_ids"] = ["different-workflow"]
        catalog = next(artifact for artifact in bundle["artifacts"] if artifact["artifact_type"] == "organization-catalog")
        catalog["published_artifacts"]["execution-profile"] = [profile["id"]]
        bundle["context"]["execution_profile_id"] = profile["id"]

        with self.assertRaises(ResolutionError):
            resolve_bundle(bundle)

    def test_runtime_profile_execution_settings_require_expected_shapes(self):
        bundle = load_fixture()
        binding = next(artifact for artifact in bundle["artifacts"] if artifact["artifact_type"] == "runtime-profile")
        binding["execution"] = {"tools": "not-a-list"}

        with self.assertRaises(ResolutionError):
            resolve_bundle(bundle)

    def test_policy_cannot_assign_approval_to_an_unresolved_role(self):
        bundle = load_fixture()
        policy = {
            "artifact_type": "policy",
            "id": "invalid-policy",
            "version": "1.0.0",
            "scope": "team",
            "policy_type": "approval",
            "input_validation": {"required": []},
            "tool_authorization": {"default": "bounded"},
            "approval_requirements": [
                {"trigger": "remote_mutation", "approval_lane": "missing-role", "on_missing": "block"}
            ],
            "retry": {"default_max_attempts": 1, "denied_action_max_attempts": 0},
            "escalation": {"unresolved": "tech-owner"},
            "termination": {
                "success_conditions": ["approved"],
                "failure_conditions": ["denied"],
                "unresolved_conditions": ["pending"]
            }
        }
        bundle["artifacts"].append(policy)
        catalog = next(artifact for artifact in bundle["artifacts"] if artifact["artifact_type"] == "organization-catalog")
        catalog["published_artifacts"]["policy"] = [policy["id"]]
        bundle["context"]["policy_ids"] = [policy["id"]]

        with self.assertRaises(ResolutionError):
            resolve_bundle(bundle)

    def test_policy_normalizes_approved_knowledge_sources(self):
        bundle = load_fixture()
        policy_path = Path(__file__).parents[2] / "resources" / "execution" / "policies" / "information-technology-core-team-safety-policy.json"
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        policy["id"] = "approved-knowledge-policy"
        policy["knowledge_access"] = {
            "external_sources": "approved_sources",
            "approved_sources": [
                "https://git.example.org/",
                {"id": "sample-product-docs", "source": "https://docs.example.org/products/"},
            ],
        }
        bundle["artifacts"].append(policy)
        catalog = next(artifact for artifact in bundle["artifacts"] if artifact["artifact_type"] == "organization-catalog")
        catalog["published_artifacts"]["policy"] = [policy["id"]]
        bundle["context"]["policy_ids"] = [policy["id"]]

        result = resolve_bundle(bundle)

        self.assertEqual(result["knowledge_access"]["external_sources"], "approved_sources")
        self.assertEqual(
            result["knowledge_access"]["approved_sources"],
            [
                {"source": "https://git.example.org/"},
                {"id": "sample-product-docs", "source": "https://docs.example.org/products/"},
            ],
        )

    def test_policy_rejects_invalid_knowledge_access_source_entry(self):
        bundle = load_fixture()
        policy_path = Path(__file__).parents[2] / "resources" / "execution" / "policies" / "information-technology-core-team-safety-policy.json"
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        policy["id"] = "invalid-knowledge-policy"
        policy["knowledge_access"] = {
            "external_sources": "approved_sources",
            "approved_sources": [{"id": "missing-source"}],
        }
        bundle["artifacts"].append(policy)
        catalog = next(artifact for artifact in bundle["artifacts"] if artifact["artifact_type"] == "organization-catalog")
        catalog["published_artifacts"]["policy"] = [policy["id"]]
        bundle["context"]["policy_ids"] = [policy["id"]]

        with self.assertRaises(ResolutionError):
            resolve_bundle(bundle)


if __name__ == "__main__":
    unittest.main()
