"""Resolver and portable contract checks, without claiming live conformance."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from agentcaravan.resolve_framework import resolve_bundle
from agentcaravan.adapters.opencode import prepare_opencode_execution
from agentcaravan.adapters.codex import prepare_codex_execution


MODULE_PATH = Path(__file__).with_name("bundle.py")
SPEC = importlib.util.spec_from_file_location("dependency_approval_bundle", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
bundle_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bundle_module)


class OpenCodeExperimentBundleTests(unittest.TestCase):
    def test_codex_and_opencode_prepare_equivalent_portable_contracts(self) -> None:
        task = {"task_id": "comparison-test", "objective": "Assess candidate"}
        plans = []
        for build, prepare, adapter_id, profile_id in (
            (bundle_module.build_opencode_bundle, prepare_opencode_execution,
             "opencode-agent-runtime", bundle_module.RUNTIME_PROFILE_ID),
            (bundle_module.build_codex_bundle, prepare_codex_execution,
             "codex-desktop-agent-runtime", bundle_module.CODEX_RUNTIME_PROFILE_ID),
        ):
            with self.subTest(adapter=adapter_id):
                bundle = build()
                result = resolve_bundle(bundle)
                self.assertIn(result["status"], {"pass", "degraded"})
                self.assertEqual(result["context"]["runtime_adapter_id"], adapter_id)
                self.assertEqual(result["context"]["runtime_profile_id"], profile_id)
                self.assertIn(profile_id, bundle["artifacts"][0]["published_artifacts"]["runtime-profile"])
                prepared = prepare(result, task)
                self.assertEqual(prepared["runtime"]["adapter_id"], adapter_id)
                plans.append(prepared["plan"])

        # Runtime projections live outside the portable plan. Compare its full
        # contract, including topology, reasoning, capabilities, and task context.
        self.assertEqual(plans[0], plans[1])

    def test_resolves_experiment_profile_without_mutating_shared_runtime(self) -> None:
        bundle = bundle_module.build_opencode_bundle()
        result = resolve_bundle(bundle)

        self.assertIn(result["status"], {"pass", "degraded"})
        self.assertEqual(result["validation_profile_id"], "local-experimental")
        self.assertEqual(result["context"]["runtime_adapter_id"], "opencode-agent-runtime")
        self.assertEqual(result["context"]["execution_profile_id"], "dependency-approval-experiment")
        self.assertEqual(result["context"]["runtime_profile_id"], bundle_module.RUNTIME_PROFILE_ID)
        prepared = prepare_opencode_execution(result, {"task_id": "experiment-test", "objective": "Assess candidate"})
        self.assertIn("completion record", prepared["plan"]["required_outputs"])

        catalog = bundle["artifacts"][0]
        self.assertIn(
            "dependency-approval-experiment",
            catalog["published_artifacts"]["execution-profile"],
        )
        self.assertIn(
            bundle_module.RUNTIME_PROFILE_ID,
            catalog["published_artifacts"]["runtime-profile"],
        )


if __name__ == "__main__":
    unittest.main()
