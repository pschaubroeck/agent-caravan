# Runtime Capability And Adapter Specification

## Purpose

This document defines the runtime-facing contract for the AI team framework.

It describes:

- the runtime-neutral capabilities the framework cares about
- how runtime integrations should expose those capabilities
- how runtime mappings should map framework artifacts to a specific runtime
- what the resolved framework instance must provide to an implementation

This specification exists to keep the framework portable across AI products, SDKs, orchestration systems, and broker platforms.

It intentionally does not assume:

- Codex
- OpenAI
- Anthropic
- Google
- Microsoft
- AWS
- Droid
- any specific agent product, SDK, prompt format, or tool protocol

## Design Goals

- keep the framework runtime-agnostic
- express runtime needs as capabilities, not vendor nouns
- support both simple and sophisticated runtimes
- support direct model runtimes and higher-level agent platforms
- allow partial capability support with explicit constraints
- enable deterministic validation of runtime compatibility

## Core Principle

Framework artifacts should describe meaning.
Runtime integrations should describe implementation.

Examples:

- a `tech-owner` role defines technical responsibility and decision rights
- a runtime integration defines whether the runtime can support delegation, bounded write access, approvals, or long-running execution
- a runtime mapping maps the `tech-owner` role onto whatever constructs the runtime uses

The framework should never require a role to know whether the implementation uses:

- prompts
- agents
- subagents
- MCP
- tools
- flows
- profiles
- skills
- connectors
- action groups
- graphs

## Implementation And Verification Ownership

Agent Caravan owns the portable capability vocabulary, adapter-facing contracts,
portable plan and result semantics, and checks that those contracts are
internally coherent. A runtime integration owns the runtime-specific implementation,
dependencies, installation behavior, and verification of behavior on named
runtime products and execution surfaces. Portable conformance does not establish
live runtime compatibility. Runtime verification must identify the tested
version, surface, material configuration, scenario, result, and evidence
provenance. Use the portable [runtime verification record](runtime-verification-record-spec.md)
to report that scope; its evidence references are descriptive and are not
authenticated by Agent Caravan.

Repository and package layout are implementation choices. This repository may
contain reference adapter implementations; the framework contract does not
require adapters to ship with Agent Caravan. Adapters may be distributed and
verified independently without changing the portable contract.

Those are runtime concerns.

## Runtime Model

The framework should model runtimes through three logical concepts:

- `runtime-capability-model`
- `runtime-adapter`
- `runtime-profile`

### `runtime-capability-model`

Defines the generic capability vocabulary used by the framework.

### `runtime-adapter`

Declares how a specific runtime satisfies, approximates, or lacks those capabilities.

Repository guidance uses a portable `AGENTS.md` entry point by default. A
runtime integration may declare its native repository instruction files and how
they are discovered under `repository_guidance`:

```json
{
  "repository_guidance": {
    "native_files": ["AGENTS.md"],
    "discovery": "automatic",
    "reference_policy": "follow-explicit-links"
  }
}
```

`AGENTS.md` is Agent Caravan's portable canonical file. `native_files` and
`discovery` are adapter-specific: adapters may list another filename or
runtime-native location, and declare whether the harness loads it
automatically or the binding must read it explicitly. When the native file
differs from the canonical file, the binding is responsible for mapping the
canonical guidance into the declared native mechanism; the framework does not
copy or rewrite repository files. `reference_policy` defaults to
`follow-explicit-links`: read the entry point first and follow its references
as needed, without crawling unrelated repository content.

The reference implementation supports profile-local values in
`config.json` under `adapter_overrides.<adapter-id>.repository_guidance`.
Those values override only the named fields on the selected adapter, so a user
can customize one harness without editing or duplicating its shared adapter.
`<adapter-id>` is the exact `id` of the selected `runtime-adapter` artifact;
the rule is identical for repository-supplied and custom adapters. The
selected adapter must be present in the profile's configured artifact sources.

### `runtime-profile`

Maps resolved framework artifacts such as roles or teams onto one runtime integration.

## Runtime Classes

The framework should support several broad runtime classes.

### Direct Model Runtime

A thin environment where execution is mostly prompt-plus-tools with little native orchestration.

Examples:

- raw model API usage
- simple chat wrapper

### Agent SDK Or Native Agent Runtime

A runtime with first-class agent loops, tools, delegation, or session concepts.

Examples:

- agent SDKs
- coding-agent runtimes
- CLI agent environments

### Low-Code Or Managed Agent Platform

A runtime that emphasizes flows, connectors, managed actions, and hosted knowledge.

Examples:

- enterprise copilots
- managed agent builders

### Broker Or Gateway Agent Platform

A runtime that fronts multiple models or execution surfaces and exposes its own agent abstraction.

Examples:

- multi-model agent products
- internal enterprise AI gateways

### Orchestration Framework

A runtime where the implementation is assembled from lower-level execution nodes, graphs, or workflows.

Examples:

- graph-based agent orchestration
- workflow engines with AI steps

## Capability Categories

The framework should express capabilities in categories rather than product-specific features.

### 1. Execution Capabilities

These describe how work can run.

Examples:

- `interactive_execution`
- `background_execution`
- `long_running_execution`
- `stepwise_execution`
- `streaming_output`
- `checkpoint_resume`

### 2. Delegation Capabilities

These describe whether and how work can be handed off.

Examples:

- `role_handoff`
- `subagent_delegation`
- `parallel_lane_execution`
- `supervisor_worker_pattern`
- `explicit_escalation`

### 3. Tool And Action Capabilities

These describe the runtime's ability to interact with external systems.

Examples:

- `local_command_execution`
- `api_call_execution`
- `browser_interaction`
- `document_editing`
- `code_editing`
- `tool_result_structuring`
- `tool_permission_scoping`

### 4. Knowledge And Context Capabilities

These describe how the runtime handles knowledge loading and retrieval.

Examples:

- `context_window_only`
- `retrieval_augmented_context`
- `document_attachment_support`
- `knowledge_source_registration`
- `dynamic_context_loading`
- `structured_memory_store`

### 5. State And Memory Capabilities

These describe continuity across steps or sessions.

Examples:

- `session_state`
- `durable_memory`
- `ephemeral_memory`
- `workflow_state_graph`
- `cross_run_context_persistence`

### 6. Safety And Permission Capabilities

These describe how the runtime constrains risky behavior.

Examples:

- `tool_approval_gates`
- `human_confirmation_points`
- `permission_profiles`
- `write_restrictions`
- `network_restrictions`
- `environment_isolation`

### 7. Observability Capabilities

These describe whether execution can be inspected or audited.

Examples:

- `execution_trace`
- `step_logging`
- `tool_call_audit`
- `handoff_traceability`
- `run_metadata`

### 8. Determinism And Control Capabilities

These describe whether the runtime can enforce structure beyond freeform prompting.

Examples:

- `structured_output_contracts`
- `deterministic_flow_nodes`
- `schema_validated_io`
- `state_machine_orchestration`
- `policy_enforced_routing`

## Capability Levels

Each capability should be represented with a support level.

Recommended levels:

- `native`
  - directly supported by the runtime

- `adapted`
  - supported through wrapper logic or adapter composition

- `externalized`
  - not native, but can be satisfied outside the runtime by surrounding infrastructure

- `unsupported`
  - not reasonably available

This distinction matters because a framework role may require a capability strongly enough that `unsupported` is unacceptable.

## Adapter Responsibilities

A `runtime-adapter` should define:

- runtime identity
- runtime class
- supported capability set
- capability support levels
- capability constraints
- execution limits
- safety/permission model
- known incompatibilities
- repository-guidance file mapping and discovery behavior, when supported

The adapter should describe the runtime honestly, including partial or awkward support.

## Binding Responsibilities

A `runtime-profile` should define:

- which framework artifacts it applies to
- which runtime integration it targets
- required capabilities
- optional capabilities
- fallback behavior when optional capabilities are missing
- unsupported framework features for that runtime
- role-to-runtime mapping rules

This is where implementors define how a role such as `tech-owner` or `quality-engineer` is realized in one runtime.

## Capability Requirement Model

Framework artifacts should be able to express runtime expectations in a portable way.

Recommended requirement levels:

- `required`
- `preferred`
- `optional`
- `forbidden`

Examples:

- a runtime mapping may require `tool_approval_gates`
- a caravan template may prefer `role_handoff`
- a local experimental flow may treat `durable_memory` as optional
- a secure workflow may forbid unrestricted `network_restrictions = none`

## Capability Constraints

Capabilities are not only present or absent. They may be constrained.

Examples:

- delegation only works serially, not in parallel
- tools exist, but only through fixed connectors
- memory exists, but only within one session
- approval gates exist, but only for certain tool classes
- background execution exists, but only through external job runners

Adapters should model those limitations explicitly.

## Required Adapter Sections

Every runtime integration should include at least:

- `adapter id`
- `runtime name`
- `runtime class`
- `supported capabilities`
- `capability levels`
- `constraints`
- `permission model`
- `observability model`
- `known gaps`

## Required Binding Sections

Every runtime mapping should include at least:

- `binding id`
- `target adapter id`
- `applies to artifact ids`
- `required capabilities`
- `preferred capabilities`
- `fallback behavior`
- `role/runtime mapping notes`
- `validation notes`

## Resolution Model

Runtime resolution should happen after framework roles, teams, and domains are resolved.

Recommended order:

1. Resolve roles
2. Resolve caravan template
3. Attach domain knowledge
4. Apply overlays
5. Select runtime integration
6. Apply runtime mappings
7. Validate capability compatibility
8. Produce resolved runtime instance

The runtime should consume the resolved runtime instance, not the raw catalogs.

## Resolved Runtime Instance

A resolved runtime instance should contain:

- resolved team structure
- resolved role definitions
- resolved domain attachments
- selected runtime integration
- resolved runtime mappings
- effective capability view
- effective constraints
- validation result

This is the portable handoff point between the framework and an actual implementation.

## Compatibility Rules

Compatibility should be checked explicitly.

### Compatible

All required capabilities are satisfied at acceptable support levels.

### Degraded

Required capabilities are satisfied, but one or more preferred capabilities are missing or only weakly supported.

This may still be acceptable depending on validation policy.

### Incompatible

One or more required capabilities are unsupported or violated by constraints.

This should fail resolution for that runtime mapping.

## Multi-Runtime Support

The framework should support multiple adapters and bindings simultaneously.

Examples:

- one organization uses a shared role catalog with both Codex and Droid adapters
- one team uses a managed enterprise platform while another uses a graph-based orchestrator
- one local user tests a new runtime mapping without changing shared artifacts

The framework should not assume one global runtime.

## Capability Examples By Role

The framework should allow roles to imply capability pressure without hardwiring vendor implementations.

### `engineer`

Often pressures:

- code editing
- local command execution
- validation triggering
- bounded write permissions

### `tech-owner`

Often pressures:

- planning support
- repository inspection
- delegation or handoff support
- structured reasoning artifacts

### `quality-engineer`

Often pressures:

- verification execution
- environment inspection
- evidence capture
- result structuring

### `software-architect`

Often pressures:

- broad context loading
- documentation access
- review-oriented reasoning
- escalation visibility

These are illustrative tendencies, not hard-coded runtime rules.

## Framework Independence Rules

The framework should not require a runtime to expose named concepts such as:

- `agent`
- `skill`
- `profile`
- `prompt file`
- `subagent`
- `flow`
- `graph node`
- `connector`
- `action group`

Adapters may use any of those internally, but the framework contract should remain capability-based.

## Validation Expectations

Adapters and bindings should be validated separately from general artifact validity.

Minimum checks:

- required sections present
- referenced adapter exists
- referenced artifact IDs exist
- capability names are valid
- support levels are valid
- required capabilities are satisfiable

Recommended additional checks:

- scenario-based compatibility tests
- degraded-mode reporting
- permission-model sanity checks
- observability coverage checks

## Packaging Independence

Neither adapters nor bindings require a specific packaging model.

They may be stored in:

- files
- repos
- databases
- registries
- API services
- generated config bundles

The framework only requires that they can be loaded and resolved logically.

## Relationship To Existing Framework Artifacts

This specification works with:

- [logical-artifact-overlay-model.md](logical-artifact-overlay-model.md)
  - defines the artifact, scope, and overlay model

- [Information Technology Core Team Operating Model](../../docs/concepts/core-team-operating-model.md)
  - provides the current team semantics that runtime mappings would eventually target

- [domain-pack-spec.md](domain-pack-spec.md)
  - defines the domain attachment format that runtimes must receive in resolved form

## Summary

The runtime capability and adapter specification defines the portable boundary between framework meaning and runtime implementation.

It allows the framework to remain stable while different teams or organizations bind the same roles, teams, and domains to different AI products, SDKs, orchestrators, or broker platforms.

## Optional Observability Boundary

Observability is optional unless a workflow or binding explicitly requires its
capabilities. Missing or failed optional telemetry must not fail execution,
strict validation, or conformance. Existing support levels apply to required
capabilities. Document coverage, attribution gaps, content exposure, and export
limits: `execution_trace` does not imply complete step or model-setting telemetry.
Agent Caravan owns no collector, storage engine, vendor, or baseline metric schema.
Native observability and compatible external solutions may implement support.
Detailed telemetry cannot replace mandatory semantic reports, stage receipts,
verification, or approval evidence.
