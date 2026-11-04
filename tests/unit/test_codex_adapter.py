import json
import tempfile
import unittest
from pathlib import Path

from agentcaravan.codex_adapter import (
    CodexAdapterError,
    project_execution_brief,
    project_resolved_execution_brief,
)
from agentcaravan.execution_plan import ExecutionPlanError, build_portable_execution_plan, validate_portable_execution_plan
from agentcaravan.adapters.codex import (
    CodexExecutionRequest,
    DryRunCodexExecutor,
    project_execution_brief as namespaced_project_execution_brief,
    run_codex_conformance_suite,
    run_codex_task,
)
from agentcaravan.conformance import load_conformance_scenarios
from agentcaravan.session_store import LocalJsonExecutionStore


ROOT = Path(__file__).parents[2]
DEPENDENCY_CASES = ROOT / "tests" / "conformance" / "experiments" / "dependency-approval" / "cases.json"
DEPENDENCY_PROFILE = ROOT / "tests" / "conformance" / "experiments" / "dependency-approval" / "execution-profile.json"


class CodexAdapterTests(unittest.TestCase):
    def test_selected_team_knowledge_is_shared_and_role_guidance_stays_scoped(self):
        resolved = {
            "status": "pass",
            "context": {
                "organization_catalog_id": "example-org",
                "team_instance_id": "integrations-team",
                "team_blueprint_id": "blueprint",
                "execution_profile_id": "workflow",
            },
            "effective_roles": [
                {
                    "id": "engineer", "source_chain": ["engineer", "engineer-ii"],
                    "role": {"version": "1.2.0", "documentation_references": [
                        {"uri": "https://gitlab.example.org/team/roles/engineer.md", "media_type": "text/markdown", "purpose": "Local engineering workflow"}
                    ]},
                },
                {"id": "quality-engineer", "source_chain": ["quality-engineer"]},
            ],
            "execution_profile": {
                "entry_roles": ["engineer"],
                "activation_policy": {"primary_roles": ["engineer"], "supporting_roles": ["quality-engineer"]},
                "stages": [{"id": "implementation", "roles": ["engineer", "quality-engineer"]}],
                "communication": {}, "escalation": {}, "required_outputs": ["completion record"],
            },
            "domain_packs": [{
                "id": "product-domain", "version": "1.0.0", "scope": "organization",
                "purpose": "Shared product context.",
                "knowledge_surface": ["product terminology"],
                "trusted_sources": ["https://docs.example.org/product"],
                "documentation_references": [
                    {"uri": "https://docs.example.org/product/overview.md", "media_type": "text/markdown"}
                ],
                "loading_guidance": ["Load product context before the team specialization."],
            }],
            "specialization_packs": [{
                "id": "integration-team-knowledge", "version": "1.0.0", "scope": "team",
                "owner_team_instance_id": "integrations-team", "parent_domain_pack_id": "product-domain",
                "knowledge_surface": ["partner contracts"],
                "role_guidance": {"engineer": "Preserve idempotency.", "quality-engineer": "Test retry behavior."},
            }],
            "knowledge_access": {"external_sources": "approved_sources", "approved_sources": ["https://docs.example.org/product"]},
        }

        plan = build_portable_execution_plan(resolved, {"task_id": "task-knowledge", "objective": "Implement integration"})
        brief = project_execution_brief(plan)

        self.assertEqual(
            [layer["id"] for layer in plan["knowledge_context"]["layers"]],
            ["product-domain", "integration-team-knowledge"],
        )
        self.assertEqual(plan["knowledge_context"], brief["knowledge_context"])
        self.assertEqual(
            plan["role_assignments"][0]["documentation_references"][0]["uri"],
            "https://gitlab.example.org/team/roles/engineer.md",
        )
        self.assertEqual(plan["role_assignments"][0]["role_version"], "1.2.0")
        self.assertEqual(brief["role_lanes"][0]["source_chain"], ["engineer", "engineer-ii"])
        self.assertEqual(
            brief["role_lanes"][0]["documentation_references"],
            plan["role_assignments"][0]["documentation_references"],
        )
        self.assertEqual(
            plan["knowledge_context"]["layers"][0]["documentation_references"][0]["media_type"],
            "text/markdown",
        )
        self.assertTrue(any("supplemental guidance" in instruction for instruction in brief["instructions"]))
        self.assertEqual(len(brief["knowledge_context"]["layers"]), 2)
        self.assertIn("Apply knowledge_context layers", " ".join(brief["instructions"]))
        self.assertEqual(brief["knowledge_access"]["external_sources"], "approved_sources")

        resolved["specialization_packs"][0]["owner_team_instance_id"] = "another-team"
        with self.assertRaisesRegex(ExecutionPlanError, "belongs to another-team"):
            build_portable_execution_plan(resolved, {"task_id": "task-knowledge", "objective": "Implement integration"})

    def test_conditional_activation_roles_are_assigned_in_the_portable_plan(self):
        resolved = {
            "status": "pass",
            "context": {"organization_catalog_id": "example-org", "team_blueprint_id": "blueprint", "execution_profile_id": "workflow"},
            "effective_roles": [
                {"id": "engineer", "source_chain": ["engineer"]},
                {"id": "release-manager", "source_chain": ["release-manager"]},
            ],
            "execution_profile": {
                "entry_roles": ["engineer"],
                "activation_policy": {"primary_roles": ["engineer"], "conditional_roles": {"release-manager": "release was requested"}},
                "stages": [{"id": "implementation", "roles": ["engineer"]}],
                "communication": {}, "escalation": {}, "required_outputs": ["completion record"],
            },
        }

        plan = build_portable_execution_plan(resolved, {"task_id": "task-1", "objective": "x"})

        release_assignment = next(item for item in plan["role_assignments"] if item["role_id"] == "release-manager")
        self.assertEqual(release_assignment["participation"], "supporting")

    def test_execution_topology_parallel_lanes_require_valid_stages_and_fallback(self):
        resolved = {
            "status": "pass",
            "context": {"organization_catalog_id": "example-org", "team_blueprint_id": "blueprint", "execution_profile_id": "workflow"},
            "effective_roles": [{"id": "engineer", "source_chain": ["engineer"]}],
            "execution_profile": {
                "entry_roles": ["engineer"],
                "activation_policy": {"primary_roles": ["engineer"]},
                "stages": [{"id": "implementation", "roles": ["engineer"]}],
                "topology": {
                    "mode": "sequential",
                    "parallel_lanes": [{"id": "impl", "stage_id": "implementation", "role_ids": ["engineer"], "purpose": "independent implementation"}],
                    "serial_fallback": {"mode": "run-in-order", "lane_ids": ["impl"]},
                },
                "communication": {}, "escalation": {}, "required_outputs": ["completion record"],
            },
        }
        plan = build_portable_execution_plan(resolved, {"task_id": "task-1", "objective": "x"})
        self.assertEqual(plan["execution_topology"]["parallel_lanes"][0]["id"], "impl")
        resolved["execution_profile"]["topology"]["parallel_lanes"][0]["stage_id"] = "missing"
        with self.assertRaisesRegex(ExecutionPlanError, "known stage"):
            build_portable_execution_plan(resolved, {"task_id": "task-1", "objective": "x"})

    def test_work_item_topology_requires_valid_acyclic_dependencies(self):
        resolved = {
            "status": "pass",
            "context": {"organization_catalog_id": "example-org", "team_blueprint_id": "blueprint", "execution_profile_id": "workflow"},
            "effective_roles": [{"id": "engineer", "source_chain": ["engineer"]}],
            "execution_profile": {
                "entry_roles": ["engineer"],
                "activation_policy": {"primary_roles": ["engineer"]},
                "stages": [{"id": "implementation", "roles": ["engineer"]}],
                "topology": {
                    "mode": "coordinator-worker",
                    "work_items": [
                        {"id": "design", "stage_id": "implementation", "role_id": "engineer", "purpose": "Design"},
                        {"id": "implement", "stage_id": "implementation", "role_id": "engineer", "purpose": "Implement", "depends_on": ["design"]},
                    ],
                },
                "communication": {}, "escalation": {}, "required_outputs": ["completion record"],
            },
        }
        plan = build_portable_execution_plan(resolved, {"task_id": "task-1", "objective": "x"})
        self.assertEqual([item["id"] for item in plan["execution_topology"]["work_items"]], ["design", "implement"])

        resolved["execution_profile"]["topology"]["work_items"][0]["depends_on"] = ["implement"]
        with self.assertRaisesRegex(ExecutionPlanError, "acyclic"):
            build_portable_execution_plan(resolved, {"task_id": "task-1", "objective": "x"})

    def test_legacy_execution_topology_fallback_remains_compatible(self):
        resolved = {
            "status": "pass",
            "context": {"organization_catalog_id": "example-org", "team_blueprint_id": "blueprint", "execution_profile_id": "workflow"},
            "effective_roles": [{"id": "engineer", "source_chain": ["engineer"]}],
            "execution_profile": {
                "entry_roles": ["engineer"],
                "activation_policy": {"primary_roles": ["engineer"]},
                "stages": [{"id": "implementation", "roles": ["engineer"]}],
                "topology": {"mode": "sequential", "parallel_optional": ["old optional lane"], "serial_fallback": "run optional work sequentially"},
                "communication": {}, "escalation": {}, "required_outputs": ["completion record"],
            },
        }
        plan = build_portable_execution_plan(resolved, {"task_id": "legacy-task", "objective": "x"})
        self.assertEqual(plan["execution_topology"]["serial_fallback"], "run optional work sequentially")

    def test_resolves_role_defaults_and_stage_overrides(self):
        resolved = {
            "status": "pass",
            "context": {
                "organization_catalog_id": "example-org",
                "team_blueprint_id": "information-technology-core-team",
                "execution_profile_id": "feature-delivery",
            },
            "effective_roles": [
                {"id": "tech-owner", "source_chain": ["tech-owner"]},
                {"id": "software-architect", "source_chain": ["software-architect"]},
                {"id": "quality-engineer", "source_chain": ["quality-engineer"]},
                {"id": "engineer", "source_chain": ["engineer"]},
            ],
            "execution_profile": {
                "entry_roles": ["tech-owner"],
                "activation_policy": {
                    "primary_roles": ["engineer"],
                    "supporting_roles": ["quality-engineer"],
                    "mandatory_reviewers": ["software-architect"],
                },
                "stages": [
                    {"id": "solution", "roles": ["tech-owner", "software-architect", "quality-engineer"]},
                    {"id": "implementation", "roles": ["engineer"]},
                ],
                "reasoning_policy": {
                    "default": "standard",
                    "role_defaults": {"tech-owner": "deep", "engineer": "focused"},
                    "stage_overrides": {"solution": {"quality-engineer": "deep"}},
                },
                "communication": {},
                "escalation": {},
                "required_outputs": ["completion record"],
            },
        }

        plan = build_portable_execution_plan(resolved, {"task_id": "task-1", "objective": "x"})
        assignments = {(item["stage_id"], item["role_id"]): item for item in plan["reasoning_assignments"]}
        self.assertEqual(assignments[("solution", "tech-owner")]["level"], "deep")
        self.assertEqual(assignments[("solution", "quality-engineer")]["level"], "deep")
        self.assertEqual(assignments[("solution", "quality-engineer")]["source"], "stage-override")
        self.assertEqual(assignments[("implementation", "engineer")]["level"], "focused")
        self.assertNotIn("codex_reasoning_effort", str(plan))

        brief = project_execution_brief(plan)
        codex_assignments = {(item["stage_id"], item["role_id"]): item for item in brief["reasoning_assignments"]}
        self.assertEqual(codex_assignments[("solution", "quality-engineer")]["codex_reasoning_effort"], "high")

    def test_rejects_reasoning_policy_role_not_in_team(self):
        resolved = {
            "status": "pass",
            "context": {
                "organization_catalog_id": "example-org",
                "team_blueprint_id": "information-technology-core-team",
                "execution_profile_id": "feature-delivery",
            },
            "effective_roles": [{"id": "engineer", "source_chain": ["engineer"]}],
            "execution_profile": {
                "entry_roles": ["engineer"],
                "activation_policy": {"primary_roles": ["engineer"]},
                "stages": [{"id": "implementation", "roles": ["engineer"]}],
                "reasoning_policy": {"role_defaults": {"quality-engineer": "deep"}},
                "communication": {},
                "escalation": {},
                "required_outputs": ["completion record"],
            },
        }
        with self.assertRaises(ExecutionPlanError):
            build_portable_execution_plan(resolved, {"task_id": "task-1", "objective": "x"})

    def test_task_reasoning_policy_overrides_profile_policy(self):
        resolved = {
            "status": "pass",
            "context": {
                "organization_catalog_id": "example-org",
                "team_blueprint_id": "information-technology-core-team",
                "execution_profile_id": "feature-delivery",
            },
            "effective_roles": [{"id": "engineer", "source_chain": ["engineer"]}],
            "execution_profile": {
                "entry_roles": ["engineer"],
                "activation_policy": {"primary_roles": ["engineer"]},
                "stages": [{"id": "implementation", "roles": ["engineer"]}],
                "reasoning_policy": {"default": "standard", "role_defaults": {"engineer": "standard"}},
                "communication": {},
                "escalation": {},
                "required_outputs": ["completion record"],
            },
        }

        plan = build_portable_execution_plan(
            resolved,
            {
                "task_id": "task-1",
                "objective": "x",
                "reasoning_policy": {"stage_overrides": {"implementation": {"engineer": "focused"}}},
            },
        )
        assignment = plan["reasoning_assignments"][0]
        self.assertEqual(assignment["level"], "focused")
        self.assertEqual(assignment["source"], "stage-override")
        self.assertEqual(plan["task"]["reasoning_policy"]["stage_overrides"]["implementation"]["engineer"], "focused")

    def test_projects_resolved_execution_profile_into_codex_brief(self):
        resolved = {
            "status": "pass",
            "context": {
                "organization_catalog_id": "example-org",
                "team_instance_id": "example-team",
                "team_blueprint_id": "information-technology-core-team",
                "runtime_profile_id": "codex-profile",
                "execution_profile_id": "feature-delivery",
            },
            "effective_team": {"id": "information-technology-core-team"},
            "team_context": {
                "mission": "Own platform delivery.",
                "work_surfaces": ["platform-api"],
                "knowledge_sources": ["repo-local README"],
                "working_agreements": "Test before review.",
                "instructions": "Prefer small, verifiable changes.",
                "preferred_roles": ["engineer", "quality-engineer"],
                "role_guidance": "Engineering leads implementation; quality reviews evidence.",
                "authoring_workspace": "caravans/example-team",
            },
            "effective_roles": [
                {"id": "engineer", "source_chain": ["engineer"]},
                {"id": "quality-engineer", "source_chain": ["quality-engineer"]},
            ],
            "runtime": {
                "adapter_id": "codex-desktop-agent-runtime",
                "degraded_capabilities": ["parallel_lane_execution"],
            },
            "execution_profile": {
                "entry_roles": ["tech-owner"],
                "activation_policy": {
                    "primary_roles": ["engineer"],
                    "supporting_roles": ["quality-engineer"],
                    "mandatory_reviewers": [],
                },
                "stages": [{"id": "implementation", "roles": ["engineer"]}],
                "escalation": {"human_approval_required_for": ["release or deployment"]},
                "required_outputs": ["completion record"],
                "topology": {"mode": "coordinator-worker", "task_ownership": "caller-retains"},
                "tool_requirements": [
                    {
                        "id": "repository-inspection",
                        "side_effect_class": "read-only",
                        "approval_required": False,
                    }
                ],
                "evidence_requirements": [{"kind": "completion-record", "required": True}],
            },
        }

        plan = build_portable_execution_plan(resolved, {"task_id": "task-1", "objective": "Ship a feature"})
        without_preferences = dict(resolved)
        without_preferences["team_context"] = {**resolved["team_context"], "preferred_roles": []}
        baseline_plan = build_portable_execution_plan(
            without_preferences,
            {"task_id": "task-1", "objective": "Ship a feature"},
        )
        self.assertEqual(plan["role_assignments"], baseline_plan["role_assignments"])
        brief = project_execution_brief(plan)
        self.assertEqual(namespaced_project_execution_brief(plan), brief)

        self.assertEqual(brief["artifact_type"], "codex-execution-brief")
        self.assertEqual(plan["artifact_type"], "portable-execution-plan")
        self.assertNotIn("runtime", plan)
        self.assertEqual([lane["role_id"] for lane in brief["role_lanes"]], ["tech-owner", "engineer", "quality-engineer"])
        self.assertEqual(brief["stage_checkpoints"][0]["stage_id"], "implementation")
        self.assertEqual(brief["approval_boundaries"], ["release or deployment"])
        self.assertEqual(brief["knowledge_access"]["external_sources"], "enabled")
        self.assertEqual(brief["knowledge_access"]["approved_sources"], [])
        self.assertEqual(brief["execution_topology"]["mode"], "coordinator-worker")
        self.assertIn("capability_requirements", brief)
        self.assertIn("Prefer small, verifiable changes.", brief["instructions"])
        self.assertIn("Team working agreements: Test before review.", brief["instructions"])
        self.assertTrue(any("prioritize these team-preferred roles: engineer, quality-engineer." in item for item in brief["instructions"]))
        self.assertTrue(any("Team role participation guidance: Engineering leads implementation; quality reviews evidence." in item for item in brief["instructions"]))
        self.assertEqual(brief["team_guidance"]["preferred_roles"], ["engineer", "quality-engineer"])
        self.assertEqual(
            brief["team_guidance"]["role_guidance"],
            "Engineering leads implementation; quality reviews evidence.",
        )
        self.assertEqual(plan["context"]["team_context"]["work_surfaces"], ["platform-api"])
        self.assertNotIn("authoring_workspace", plan["context"]["team_context"])
        self.assertNotIn("documents", plan["context"]["team_context"])
        self.assertEqual(plan["context"]["team_context"]["preferred_roles"], ["engineer", "quality-engineer"])
        self.assertEqual(brief["tool_requirements"][0]["id"], "repository-inspection")
        self.assertEqual(brief["evidence_requirements"][0]["kind"], "completion-record")
        self.assertEqual(brief["result_contract"], "resources/schemas/execution-result.schema.json")

    def test_compatibility_projection_builds_plan_before_codex_projection(self):
        resolved = {
            "status": "pass",
            "context": {
                "organization_catalog_id": "example-org",
                "team_instance_id": "example-team",
                "team_blueprint_id": "information-technology-core-team",
                "runtime_profile_id": "codex-profile",
                "execution_profile_id": "feature-delivery",
            },
            "effective_team": {"id": "information-technology-core-team"},
            "effective_roles": [],
            "runtime": {"adapter_id": "codex-desktop-agent-runtime", "degraded_capabilities": []},
            "execution_profile": {
                "entry_roles": ["engineer"],
                "activation_policy": {"primary_roles": ["engineer"]},
                "stages": [{"id": "implementation", "roles": ["engineer"]}],
                "escalation": {},
                "required_outputs": ["completion record"],
            },
        }

        brief = project_resolved_execution_brief(resolved, {"task_id": "task-1", "objective": "Ship a feature"})

        self.assertEqual(brief["plan_id"], "task-1-execution-plan")
        self.assertEqual(brief["runtime_profile_id"], "codex-profile")

    def test_codex_conformance_bridge_projects_brief_and_normalizes_result(self):
        resolved = {
            "status": "pass",
            "context": {
                "organization_catalog_id": "example-org",
                "team_instance_id": "example-team",
                "team_blueprint_id": "information-technology-core-team",
                "runtime_profile_id": "codex-profile",
                "execution_profile_id": "feature-delivery",
            },
            "effective_roles": [{"id": "engineer", "source_chain": ["engineer"]}],
            "runtime": {"adapter_id": "codex-desktop-agent-runtime", "degraded_capabilities": []},
            "execution_profile": {
                "entry_roles": ["engineer"],
                "activation_policy": {"primary_roles": ["engineer"]},
                "stages": [{"id": "implementation", "roles": ["engineer"]}],
                "communication": {"requires_structured_handoff": True, "allowed_role_handoffs": []},
                "escalation": {},
                "required_outputs": ["completion record"],
            },
        }
        scenarios = [{
            "id": "codex-bridge",
            "task": {"task_id": "task-1", "objective": "Run one projected task"},
            "expected": {"status": "completed", "active_roles": ["engineer"], "completed_stages": ["implementation"], "failure_count": 0},
        }]
        seen = {}

        def executor(_, brief):
            seen["artifact_type"] = brief["artifact_type"]
            seen["result_contract"] = brief["result_contract"]
            return {"status": "completed", "active_roles": ["engineer"], "completed_stages": ["implementation"]}

        suite = run_codex_conformance_suite(resolved, scenarios, executor)

        self.assertTrue(suite.passed)
        self.assertEqual(seen["artifact_type"], "codex-execution-brief")
        self.assertEqual(seen["result_contract"], "resources/schemas/execution-result.schema.json")
        self.assertEqual(suite.cases[0].result["task_id"], "task-1")

        dry_suite = run_codex_conformance_suite(resolved, scenarios, DryRunCodexExecutor())
        self.assertTrue(dry_suite.passed)
        self.assertEqual(dry_suite.cases[0].result["metadata"]["execution_mode"], "dry-run")
        self.assertEqual(
            dry_suite.cases[0].result["execution_realization"]["mode"],
            "simulated-sequential",
        )
        self.assertFalse(dry_suite.cases[0].result["execution_realization"]["native_subagents"])
        self.assertEqual(dry_suite.cases[0].result["role_turns"][0]["status"], "unverified")
        self.assertEqual(dry_suite.cases[0].result["metadata"]["execution_records"]["run"]["status"], "completed")
        self.assertTrue(dry_suite.cases[0].result["reasoning_evidence"])
        self.assertEqual(dry_suite.cases[0].result["reasoning_evidence"][0]["status"], "unverified")

        with tempfile.TemporaryDirectory() as temporary:
            requests = []

            class Surface:
                def execute(self, request):
                    requests.append(request)
                    return {
                        "status": "completed",
                        "active_roles": ["engineer"],
                        "completed_stages": ["implementation"],
                        "execution_events": [
                            {
                                "event_id": f"{request.task_id}-step-1",
                                "kind": "workflow-step",
                                "status": "completed",
                                "task_id": request.task_id,
                                "timestamp": "2026-10-01T10:00:00Z",
                            }
                        ],
                        "run": {"run_id": "codex-native-run"},
                        "metadata": {"execution_records": {"source": "codex-native"}},
                    }

            persisted_suite = run_codex_conformance_suite(
                resolved,
                scenarios,
                Surface(),
                store=LocalJsonExecutionStore(temporary),
            )
            self.assertTrue(persisted_suite.passed)
            self.assertIsInstance(requests[0], CodexExecutionRequest)
            self.assertEqual(requests[0].task_id, "task-1")
            self.assertEqual(persisted_suite.cases[0].result["run"]["run_id"], requests[0].run_id)
            self.assertEqual(persisted_suite.cases[0].result["run"]["session_id"], requests[0].session_id)
            self.assertEqual(persisted_suite.cases[0].result["run"]["runtime_run_id"], "codex-native-run")
            self.assertEqual(
                persisted_suite.cases[0].result["metadata"]["runtime_execution_records"],
                {"source": "codex-native"},
            )
            task_root = Path(temporary) / "task-1"
            self.assertTrue((task_root / "task.json").exists())
            self.assertTrue((task_root / "session.json").exists())
            self.assertTrue((task_root / "runs" / "task-1-codex-run-1.json").exists())
            self.assertTrue((task_root / "completion.json").exists())

            resumed_suite = run_codex_conformance_suite(
                resolved,
                scenarios,
                Surface(),
                store=LocalJsonExecutionStore(temporary),
                run_id_factory=lambda _: "task-1-codex-run-2",
            )
            self.assertTrue(resumed_suite.passed, resumed_suite.failures)
            self.assertTrue((task_root / "runs" / "task-1-codex-run-1.json").exists())
            self.assertTrue((task_root / "runs" / "task-1-codex-run-2.json").exists())

            task_result = run_codex_task(
                resolved,
                {"task_id": "task-2", "objective": "Run one persisted task"},
                Surface(),
                store=LocalJsonExecutionStore(temporary),
            )
            task_completion = json.loads((Path(temporary) / "task-2" / "completion.json").read_text())
            task_state = json.loads((Path(temporary) / "task-2" / "task.json").read_text())
            run_state = json.loads((Path(temporary) / "task-2" / "runs" / "task-2-codex-run-1.json").read_text())
            self.assertEqual(task_result["metadata"]["execution_records"]["run"]["run_id"], "task-2-codex-run-1")
            self.assertEqual(task_result["metadata"]["runtime_execution_records"], {"source": "codex-native"})
            self.assertEqual(task_completion["metadata"]["execution_records"]["run"]["run_id"], "task-2-codex-run-1")
            self.assertEqual(task_completion["metadata"]["runtime_execution_records"], {"source": "codex-native"})
            self.assertEqual(task_state["execution_events"], task_result["execution_events"])
            self.assertEqual(run_state["execution_events"], task_result["execution_events"])

    def test_requires_execution_profile_and_codex_runtime(self):
        with self.assertRaises(CodexAdapterError):
            project_resolved_execution_brief({"status": "pass", "runtime": {}}, {"task_id": "task-1", "objective": "x"})

    def test_dependency_case_pack_remains_nonconformant_on_codex_dry_run(self):
        profile = json.loads(DEPENDENCY_PROFILE.read_text(encoding="utf-8"))
        profile["required_outputs"] = ["completion record"]
        role_ids = ["engineer", "tech-owner", "program-manager"]
        resolved = {
            "status": "pass",
            "context": {
                "organization_catalog_id": "example-org",
                "team_instance_id": "example-team",
                "team_blueprint_id": "information-technology-core-team",
                "runtime_profile_id": "codex-profile",
                "execution_profile_id": profile["id"],
            },
            "effective_roles": [{"id": role_id, "source_chain": [role_id]} for role_id in role_ids],
            "runtime": {"adapter_id": "codex-desktop-agent-runtime", "degraded_capabilities": []},
            "execution_profile": profile,
        }

        suite = run_codex_conformance_suite(
            resolved,
            load_conformance_scenarios(DEPENDENCY_CASES),
            DryRunCodexExecutor(),
        )

        self.assertFalse(suite.passed)
        self.assertEqual([case.scenario_id for case in suite.cases], ["dependency-approval-accept", "dependency-approval-reject"])
        for case in suite.cases:
            self.assertEqual(case.result["metadata"]["execution_mode"], "dry-run")
            self.assertFalse(case.passed)
            self.assertTrue(case.mismatches)

    def test_rejects_team_preferred_role_outside_resolved_team(self):
        resolved = {
            "status": "pass",
            "context": {
                "organization_catalog_id": "example-org",
                "team_blueprint_id": "information-technology-core-team",
                "execution_profile_id": "feature-delivery",
            },
            "effective_roles": [{"id": "engineer", "source_chain": ["engineer"]}],
            "team_context": {"preferred_roles": ["unknown-role"]},
            "execution_profile": {
                "entry_roles": ["engineer"],
                "activation_policy": {"primary_roles": ["engineer"]},
                "stages": [{"id": "implementation", "roles": ["engineer"]}],
                "communication": {},
                "escalation": {},
                "required_outputs": ["completion record"],
            },
        }
        with self.assertRaises(ExecutionPlanError):
            build_portable_execution_plan(resolved, {"task_id": "task-1", "objective": "x"})

    def test_portable_plan_rejects_runtime_specific_fields(self):
        with self.assertRaises(ExecutionPlanError):
            validate_portable_execution_plan({"artifact_type": "portable-execution-plan", "runtime": "codex"})

    def test_portable_plan_preserves_organization_specific_references(self):
        resolved = {
            "status": "pass",
            "context": {
                "organization_catalog_id": "example-org",
                "team_blueprint_id": "information-technology-core-team",
                "execution_profile_id": "feature-delivery",
            },
            "effective_roles": [],
            "execution_profile": {
                "entry_roles": ["engineer"],
                "activation_policy": {"primary_roles": ["engineer"]},
                "stages": [{"id": "implementation", "roles": ["engineer"]}],
                "communication": {},
                "escalation": {},
                "required_outputs": ["completion record"],
            },
        }

        plan = build_portable_execution_plan(
            resolved,
            {
                "task_id": "TASK-999999",
                "objective": "Plan a feature",
                "references": [{
                    "system_type": "work-tracker",
                    "reference_type": "work-item",
                    "identifier": "TASK-999999",
                    "provider": "jira",
                }],
                "extensions": {"example-organization": {"team": "delivery"}},
            },
        )

        self.assertEqual(plan["task"]["references"][0]["identifier"], "TASK-999999")
        self.assertEqual(plan["task"]["references"][0]["provider"], "jira")
        self.assertNotIn("jira", plan)

    def test_portable_plan_rejects_unassigned_unconditional_step_role(self):
        resolved = {
            "status": "pass",
            "context": {
                "organization_catalog_id": "example-org",
                "team_blueprint_id": "information-technology-core-team",
                "execution_profile_id": "feature-delivery",
            },
            "effective_roles": [],
            "execution_profile": {
                "entry_roles": ["engineer"],
                "activation_policy": {"primary_roles": ["engineer"]},
                "stages": [{"id": "bad-step", "roles": ["software-architect"]}],
                "communication": {},
                "escalation": {},
                "required_outputs": ["completion record"],
            },
        }
        with self.assertRaises(ExecutionPlanError):
            build_portable_execution_plan(resolved, {"task_id": "task-1", "objective": "x"})

    def test_portable_plan_rejects_approval_required_tool_without_lane(self):
        resolved = {
            "status": "pass",
            "context": {
                "organization_catalog_id": "example-org",
                "team_blueprint_id": "information-technology-core-team",
                "execution_profile_id": "feature-delivery",
            },
            "effective_roles": [],
            "execution_profile": {
                "entry_roles": ["engineer"],
                "activation_policy": {"primary_roles": ["engineer"]},
                "stages": [{"id": "implementation", "roles": ["engineer"]}],
                "communication": {},
                "escalation": {},
                "required_outputs": ["completion record"],
                "tool_requirements": [
                    {"id": "remote-mutation", "side_effect_class": "remote-write", "approval_required": True}
                ],
            },
        }
        with self.assertRaises(ExecutionPlanError):
            build_portable_execution_plan(resolved, {"task_id": "task-1", "objective": "x"})


if __name__ == "__main__":
    unittest.main()
