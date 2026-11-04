"""Optional telemetry policy and record associations across runtime boundaries."""

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from jsonschema.exceptions import ValidationError

from agentcaravan.adapters.codex import prepare_codex_execution, run_codex_task
from agentcaravan.adapters.opencode import prepare_opencode_execution, run_opencode_task
from agentcaravan.conformance import load_conformance_scenarios, run_conformance_suite
from agentcaravan.execution_result import normalize_execution_result
from agentcaravan.execution_plan import build_portable_execution_plan
from agentcaravan import observability as observability_adapter
from agentcaravan.resolve_framework import ResolutionError, resolve_bundle
from agentcaravan.schema_validation import validate_artifact
from agentcaravan.session_store import LocalJsonExecutionStore
from tests.unit.test_conformance import DEPENDENCY_CASES, dependency_reference_executor, prepared_execution
from tests.unit.test_opencode_adapter import resolved_runtime
from tests.unit.test_resolve_framework import load_fixture


ROOT = Path(__file__).parents[2]
DEFAULT_POLICY = {"enabled": False, "export": "local", "capture_content": False}


def runtime_artifacts(bundle):
    adapter = next(item for item in bundle["artifacts"] if item["artifact_type"] == "runtime-adapter")
    profile = next(item for item in bundle["artifacts"] if item["artifact_type"] == "runtime-profile")
    return adapter, profile


class ObservabilityTests(unittest.TestCase):
    def test_enabled_runtime_adapters_emit_local_workflow_markers(self):
        class Identity:
            def __init__(self, namespace, logical_id):
                self.namespace = namespace
                self.logical_id = logical_id
                self.key = f"{namespace}:{logical_id}"

        class Selector:
            def __init__(self, scope, identity):
                self.scope = scope
                self.identity = identity

        class Policy:
            def __init__(self, include):
                self.include = include

            @classmethod
            def load(cls, path):
                return cls(path)

        class Store:
            instances = []

            def __init__(self, path, *, policy, harness):
                self.path = path
                self.policy = policy
                self.harness = harness
                self.calls = []
                self.last_storage_error = None
                self.__class__.instances.append(self)

            def start(self, kind, identity, **kwargs):
                self.calls.append(("start", kind, identity, kwargs))
                return {"recorded": True, "filtered": False,
                        "trace_id": "1" * 32, "span_id": "2" * 16}

            def finish(self, trace_id, span_id, *, outcome):
                self.calls.append(("finish", trace_id, span_id, outcome))
                return {"recorded": True}

        with patch.object(observability_adapter, "_load_components",
                          return_value=(Identity, Policy, Selector, Store)):
            for adapter_id, run in (("codex-desktop-agent-runtime", run_codex_task),
                                    ("opencode-agent-runtime", run_opencode_task)):
                with self.subTest(adapter=adapter_id), tempfile.TemporaryDirectory() as temporary:
                    Store.instances.clear()
                    resolved = resolved_runtime(adapter_id)
                    resolved["runtime"]["observability"] = {**DEFAULT_POLICY, "enabled": True}

                    class Surface:
                        def execute(self, request):
                            return {"status": "completed", "completed_stages": ["inspection"]}

                    result = run(resolved, {"task_id": "task-1", "objective": "inspect"}, Surface(),
                                 store=LocalJsonExecutionStore(temporary),
                                 session_id="session-1", run_id="run-1")
                    store = Store.instances[-1]
                    self.assertEqual(store.harness, "agentcaravan")
                    self.assertEqual(store.calls[0][1], "workflow")
                    self.assertEqual(store.calls[0][2].key, "agentcaravan:workflow")
                    self.assertEqual(store.calls[0][3]["session_id"], "session-1")
                    self.assertEqual(store.calls[0][3]["invocation_id"], "run-1")
                    self.assertEqual(store.calls[1][-1], "ok")
                    metadata = result["metadata"]
                    self.assertEqual(metadata["observability_capture"], {"state": "recorded"})
                    self.assertEqual(metadata["observability"]["references"],
                                     [f"agent-observability:{'1' * 32}/{'2' * 16}"])
                    self.assertEqual(metadata["observability"]["correlation"]["task_id"], "task-1")
                    persisted = json.loads((Path(temporary) / "task-1/runs/run-1.json").read_text())
                    self.assertEqual(persisted["metadata"]["observability"], metadata["observability"])

    def test_missing_optional_package_does_not_change_runtime_result(self):
        for adapter_id, run in (("codex-desktop-agent-runtime", run_codex_task),
                                ("opencode-agent-runtime", run_opencode_task)):
            with self.subTest(adapter=adapter_id):
                resolved = resolved_runtime(adapter_id)
                resolved["runtime"]["observability"] = {**DEFAULT_POLICY, "enabled": True}

                class Surface:
                    def execute(self, request):
                        return {"status": "completed", "completed_stages": ["inspection"]}

                with patch.object(observability_adapter, "_load_components",
                                  side_effect=ImportError("optional package not installed")):
                    result = run(resolved, {"task_id": "task-1", "objective": "inspect"}, Surface())
                self.assertEqual(result["status"], "completed")
                self.assertEqual(result["metadata"]["observability_capture"], {
                    "state": "failed", "diagnostic": "adapter_unavailable",
                })

    def test_optional_trace_gap_does_not_block_strict_resolution(self):
        bundle = load_fixture()
        bundle["context"]["validation_profile_id"] = "organization-shared"
        adapter, _ = runtime_artifacts(bundle)
        for value in (None, "unsupported"):
            with self.subTest(support=value):
                if value is None:
                    adapter["capabilities"].pop("execution_trace", None)
                else:
                    adapter["capabilities"]["execution_trace"] = value
                resolved = resolve_bundle(bundle)
                self.assertEqual(resolved["status"], "pass")
                self.assertEqual(resolved["runtime"]["degraded_capabilities"], [])
                self.assertEqual(resolved["runtime"]["observability_gaps"], ["preferred:execution_trace:unsupported"])
                self.assertEqual(resolved["runtime"]["observability"], DEFAULT_POLICY)

    def test_required_trace_remains_blocking(self):
        for requirement in ("required_capabilities", "capability_support_requirements"):
            with self.subTest(requirement=requirement):
                bundle = load_fixture()
                adapter, profile = runtime_artifacts(bundle)
                adapter["capabilities"].pop("execution_trace")
                if requirement == "required_capabilities":
                    profile[requirement].append("execution_trace")
                else:
                    profile[requirement] = {"execution_trace": "adapted"}
                with self.assertRaisesRegex(ResolutionError, "execution_trace"):
                    resolve_bundle(bundle)

    def test_required_workflow_observability_and_support_floor_are_checked(self):
        for requirement in ("required_capabilities", "capability_support_requirements", "workflow-native"):
            with self.subTest(requirement=requirement):
                bundle = load_fixture()
                adapter, profile = runtime_artifacts(bundle)
                workflow = json.loads((ROOT / "resources/execution/workflows/information-technology-core-team-basic-work.json").read_text())
                if requirement == "required_capabilities":
                    adapter["capabilities"].pop("execution_trace")
                    workflow[requirement] = ["execution_trace"]
                else:
                    adapter["capabilities"]["execution_trace"] = "adapted"
                    if requirement == "workflow-native":
                        workflow["capability_support_requirements"] = {"execution_trace": "native"}
                    else:
                        profile[requirement] = {"execution_trace": "native"}
                        workflow[requirement] = {"execution_trace": "adapted"}
                bundle["artifacts"].append(workflow)
                catalog = next(item for item in bundle["artifacts"] if item["artifact_type"] == "organization-catalog")
                catalog["published_artifacts"].setdefault("execution-profile", []).append(workflow["id"])
                bundle["context"]["execution_profile_id"] = workflow["id"]
                with self.assertRaisesRegex(ResolutionError, "execution_trace"):
                    resolve_bundle(bundle)

    def test_workflow_required_capabilities_rejects_malformed_declarations(self):
        for required in ("execution_trace", None, [None], [""]):
            with self.subTest(required=required):
                bundle = load_fixture()
                workflow = json.loads((ROOT / "resources/execution/workflows/information-technology-core-team-basic-work.json").read_text())
                workflow["required_capabilities"] = required
                bundle["artifacts"].append(workflow)
                catalog = next(item for item in bundle["artifacts"] if item["artifact_type"] == "organization-catalog")
                catalog["published_artifacts"].setdefault("execution-profile", []).append(workflow["id"])
                bundle["context"]["execution_profile_id"] = workflow["id"]
                with self.assertRaisesRegex(ResolutionError, "required_capabilities"):
                    resolve_bundle(bundle)
                with self.assertRaises(ValidationError):
                    validate_artifact(workflow, ROOT / "resources/schemas/execution-profile.schema.json")

    def test_policy_defaults_and_explicit_remote_content_settings(self):
        for configured, expected in (
            ({"enabled": True}, {**DEFAULT_POLICY, "enabled": True}),
            ({"enabled": True, "export": "remote", "destination_ref": "operator-export", "capture_content": True},
             {"enabled": True, "export": "remote", "destination_ref": "operator-export", "capture_content": True}),
        ):
            bundle = load_fixture()
            _, profile = runtime_artifacts(bundle)
            profile["execution"] = {"observability": configured}
            before = deepcopy(bundle)
            self.assertEqual(resolve_bundle(bundle)["runtime"]["observability"], expected)
            self.assertEqual(bundle, before)

    def test_unknown_workflow_requirement_fails_and_adapter_defined_capability_can_pass(self):
        for requirement in ("required_capabilities", "capability_support_requirements"):
            with self.subTest(requirement=requirement):
                bundle = load_fixture()
                adapter, _ = runtime_artifacts(bundle)
                workflow = json.loads((ROOT / "resources/execution/workflows/information-technology-core-team-basic-work.json").read_text())
                capability = "runtime_trace_export"
                workflow[requirement] = [capability] if requirement == "required_capabilities" else {capability: "native"}
                bundle["artifacts"].append(workflow)
                catalog = next(item for item in bundle["artifacts"] if item["artifact_type"] == "organization-catalog")
                catalog["published_artifacts"].setdefault("execution-profile", []).append(workflow["id"])
                bundle["context"]["execution_profile_id"] = workflow["id"]
                with self.assertRaisesRegex(ResolutionError, capability):
                    resolve_bundle(bundle)
                adapter["capabilities"][capability] = "native"
                self.assertEqual(resolve_bundle(bundle)["status"], "pass")

    def test_workflow_cannot_weaken_runtime_observability_support_floor(self):
        resolved = resolved_runtime()
        resolved["runtime"]["capability_support_requirements"] = {"execution_trace": "native"}
        resolved["execution_profile"]["capability_support_requirements"] = {"execution_trace": "adapted"}
        plan = build_portable_execution_plan(resolved, {"task_id": "task-1", "objective": "inspect"})
        self.assertEqual(plan["capability_requirements"]["support_levels"]["execution_trace"], "native")

    def test_invalid_policy_fails_before_dispatch(self):
        for settings in (None, [], {"enabled": "true"}, {"capture_content": 1},
                         {"export": []}, {"export": "remote"}, {"destination_ref": ""}):
            with self.subTest(settings=settings):
                bundle = load_fixture()
                _, profile = runtime_artifacts(bundle)
                profile["execution"] = {"observability": settings}
                with self.assertRaisesRegex(ResolutionError, "observability"):
                    resolve_bundle(bundle)

    def test_policy_reaches_both_requests_without_changing_the_portable_plan(self):
        for adapter_id, prepare in (("codex-desktop-agent-runtime", prepare_codex_execution),
                                    ("opencode-agent-runtime", prepare_opencode_execution)):
            with self.subTest(adapter=adapter_id):
                resolved = resolved_runtime(adapter_id)
                task = {"task_id": "task-1", "objective": "inspect"}
                baseline = prepare(resolved, task)
                policy = {**DEFAULT_POLICY, "enabled": True}
                resolved["runtime"]["observability"] = policy
                configured = prepare(resolved, task)
                self.assertEqual(configured["plan"], baseline["plan"])
                self.assertEqual(configured["projection"]["observability"], policy)
                self.assertEqual(baseline["projection"]["observability"], DEFAULT_POLICY)

    def test_associations_survive_normalization_and_local_round_trip(self):
        association = {"references": ["runtime-owned:trace-1"],
                       "correlation": {"role_id": "engineer", "stage_id": "inspection", "run_id": "runtime-run"}}
        for adapter_id, run in (("codex-desktop-agent-runtime", run_codex_task),
                                ("opencode-agent-runtime", run_opencode_task)):
            with self.subTest(adapter=adapter_id), tempfile.TemporaryDirectory() as temporary:
                raw = {"status": "completed", "completed_stages": ["inspection"], "run": {"run_id": "runtime-run"},
                       "metadata": {"observability": association, "unrelated": "preserved"},
                       "evidence": [{"kind": "inspection", "status": "passed", "metadata": {"observability": association}}],
                       "execution_events": [{"kind": "inspection", "status": "completed", "metadata": {"observability": association}}]}
                original = deepcopy(raw)

                class Surface:
                    def execute(self, request):
                        request.records["run"]["metadata"] = {"existing": "kept"}
                        self_policy = request.prepared["projection"]["observability"]
                        if self_policy != DEFAULT_POLICY:
                            raise AssertionError(self_policy)
                        return raw

                result = run(resolved_runtime(adapter_id), {"task_id": "task-1", "objective": "inspect"},
                             Surface(), store=LocalJsonExecutionStore(temporary), session_id="session-1", run_id="run-1")
                self.assertEqual(raw["metadata"]["observability"], original["metadata"]["observability"])
                telemetry = result["metadata"]["observability"]
                self.assertEqual(telemetry["references"], association["references"])
                self.assertEqual(telemetry["correlation"]["run_id"], "run-1")
                self.assertEqual(telemetry["correlation"]["session_id"], "session-1")
                self.assertEqual(telemetry["correlation"]["role_id"], "engineer")
                self.assertEqual(result["metadata"]["unrelated"], "preserved")
                self.assertEqual(result["execution_events"][0]["metadata"]["observability"], association)
                self.assertEqual(result["evidence"][0]["metadata"]["observability"], association)
                task_root = Path(temporary) / "task-1"
                persisted = json.loads((task_root / "runs" / "run-1.json").read_text())
                completion = json.loads((task_root / "completion.json").read_text())
                self.assertEqual(persisted["metadata"], {"existing": "kept", "observability": telemetry})
                self.assertEqual(completion["metadata"]["observability"], telemetry)
                validate_artifact(persisted, ROOT / "resources/schemas/run-record.schema.json")
                validate_artifact(completion, ROOT / "resources/schemas/execution-result.schema.json")

    def test_association_schema_preserves_extensions_and_rejects_invalid_references(self):
        result = normalize_execution_result(prepared_execution(), {"status": "completed"})
        schema = ROOT / "resources/schemas/execution-result.schema.json"
        validate_artifact(result, schema)
        result["metadata"] = {"existing": {"anything": True}, "observability": {
            "references": ["runtime:trace"], "correlation": {"role_id": "engineer", "runtime_session": "native-1"},
            "extension": "future-runtime",
        }}
        with patch("urllib.request.urlopen", side_effect=AssertionError("references must not be fetched")):
            validate_artifact(result, schema)
        result["metadata"]["observability"]["references"] = [""]
        with self.assertRaises(ValidationError):
            validate_artifact(result, schema)

    def test_run_level_association_survives_adapter_persistence(self):
        association = {"references": ["runtime:run-trace"]}
        for adapter_id, run in (("codex-desktop-agent-runtime", run_codex_task),
                                ("opencode-agent-runtime", run_opencode_task)):
            with self.subTest(adapter=adapter_id), tempfile.TemporaryDirectory() as temporary:
                class Surface:
                    def execute(self, request):
                        return {"status": "completed", "completed_stages": ["inspection"], "run": {"metadata": {
                            "observability": association, "runtime_extension": "not copied",
                        }}}

                result = run(resolved_runtime(adapter_id), {"task_id": "task-1", "objective": "inspect"},
                             Surface(), store=LocalJsonExecutionStore(temporary), session_id="session-1", run_id="run-1")
                persisted = json.loads((Path(temporary) / "task-1/runs/run-1.json").read_text())
                self.assertEqual(persisted["metadata"]["observability"], result["metadata"]["observability"])
                self.assertEqual(persisted["metadata"]["observability"]["references"], association["references"])
                self.assertNotIn("runtime_extension", persisted["metadata"])

    def test_optional_telemetry_does_not_change_conformance_or_replace_evidence(self):
        scenarios = load_conformance_scenarios(DEPENDENCY_CASES)
        for telemetry in (None, {"references": ["native:trace"]}, {"collection_status": "failed"}):
            def execute(scenario):
                result = dependency_reference_executor(scenario)
                if telemetry is not None:
                    result.setdefault("metadata", {})["observability"] = telemetry
                return result
            suite = run_conformance_suite(scenarios, execute, prepared=prepared_execution)
            self.assertTrue(suite.passed, suite.failures)

        def missing_semantic_evidence(scenario):
            result = dependency_reference_executor(scenario)
            result["evidence"] = []
            result["approvals"] = []
            for event in result["execution_events"]:
                event.pop("evidence_refs", None)
                event["metadata"] = {"observability": {"references": ["native:approval-trace"]}}
            return result
        suite = run_conformance_suite(scenarios, missing_semantic_evidence, prepared=prepared_execution)
        self.assertFalse(suite.passed)
        self.assertTrue(any("cannot be attributed" in mismatch for case in suite.failures for mismatch in case.mismatches))


if __name__ == "__main__":
    unittest.main()
