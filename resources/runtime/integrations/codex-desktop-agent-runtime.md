# Runtime Integration: codex-desktop-agent-runtime

## Purpose

- `adapter id`: `codex-desktop-agent-runtime`
- `runtime name`: `Codex Desktop`
- `version`: `1.1.0`
- `runtime class`: `agent SDK or native agent runtime`
- `scope`: `local`
- `mission`: Describe the observed capabilities and constraints of the current Codex desktop coding-agent runtime for use by framework bindings.
- `summary`: This adapter models Codex Desktop as an operator-visible coding-agent runtime with tool execution, local file mutation, bounded remote integration through approved tools, and explicit approval boundaries for sensitive side effects.

## Capability Realization And Verification Scope

The levels below describe the adapter's capability realization mapping for the
Codex Desktop surface; they are not a verification report. The repository
provides a Codex execution bridge and a CLI dry-run, while live runtime work
depends on an injected execution surface or the Codex harness workflow. This
adapter inventory does not pin a Codex product version or claim that every
listed capability has been exercised in a particular configuration. Treat
capabilities without scenario-specific evidence as unverified, not
unsupported. See the [runtime integration evidence guidance](../../../docs/reference/runtime-integration.md#capability-realization-and-verification-evidence)
and [Codex adapter walkthrough](../../../docs/integrations/codex-adapter.md).

## Supported Capabilities

### Execution

- `interactive_execution`: `native`
- `stepwise_execution`: `native`
- `streaming_output`: `native`
- `background_execution`: `adapted`
- `long_running_execution`: `adapted`
- `checkpoint_resume`: `adapted`

### Delegation

- `role_handoff`: `native`
- `subagent_delegation`: `native`
- `parallel_lane_execution`: `native`
- `supervisor_worker_pattern`: `native`
- `explicit_escalation`: `native`

### Tools And Actions

- `local_command_execution`: `native`
- `api_call_execution`: `adapted`
- `browser_interaction`: `adapted`
- `document_editing`: `adapted`
- `code_editing`: `native`
- `tool_result_structuring`: `native`
- `tool_permission_scoping`: `adapted`

### Knowledge And Context

- `context_window_only`: `native`
- `document_attachment_support`: `native`
- `dynamic_context_loading`: `native`
- `knowledge_source_registration`: `adapted`
- `retrieval_augmented_context`: `adapted`
- `structured_memory_store`: `externalized`

### Repository Guidance

- portable canonical entry point: `AGENTS.md`
- native entry point: `AGENTS.md`, discovered automatically by Codex
- read the entry point first and follow its explicit links as needed

### State And Memory

- `session_state`: `native`
- `ephemeral_memory`: `native`
- `durable_memory`: `adapted`
- `cross_run_context_persistence`: `adapted`
- `workflow_state_graph`: `externalized`

### Safety And Permissions

- `tool_approval_gates`: `native`
- `human_confirmation_points`: `native`
- `permission_profiles`: `adapted`
- `write_restrictions`: `native`
- `network_restrictions`: `adapted`
- `environment_isolation`: `adapted`

### Observability

- `execution_trace`: `native`
- `step_logging`: `native`
- `tool_call_audit`: `native`
- `handoff_traceability`: `adapted`
- `run_metadata`: `native`
- `reasoning_effort_telemetry`: `unsupported` through the public native delegation boundary

### Determinism And Control

- `structured_output_contracts`: `native`
- `schema_validated_io`: `adapted`
- `policy_enforced_routing`: `adapted`
- `deterministic_flow_nodes`: `externalized`
- `state_machine_orchestration`: `externalized`

## Constraints

- native task-scoped subagent lanes are available through the current Codex execution surface; the orchestrator must explicitly dispatch and join them rather than simulate role turns
- durable memory and cross-run persistence depend on surrounding framework artifacts, runtime features, or local storage patterns rather than one guaranteed native memory substrate
- remote system access is mediated by available tools, connectors, and approval boundaries
- some integrations are surfaced through skills, plugins, or external connectors rather than one uniform built-in tool model

## Permission Model

- local repository mutation is supported directly
- remote mutation should be treated as approval-gated unless an explicitly authorized workflow says otherwise
- destructive local operations should remain opt-in and visible
- integrations may carry their own narrower approval or access boundaries

## Observability Model

- the operator can inspect commentary, command output, file mutations, and tool-call results
- execution is observable at the task level, though some delegated or wrapped workflows may summarize intermediate internal behavior rather than expose every micro-step
- native delegation can provide dispatch acceptance and an opaque worker reference, but it does not provide a portable post-hoc effective reasoning setting
- local runtime diagnostics may expose deeper provider-specific records; those records are not part of the Agent Caravan evidence contract
- validation and release evidence should be surfaced explicitly by the binding or workflow, not assumed

## Known Gaps

- no guarantee of fully native workflow-graph orchestration
- no guarantee of globally shared durable memory across all tasks
- no guarantee that every enterprise system is reachable without an external connector or companion access path
- no guarantee that every multi-role pattern maps cleanly to a permanently running role agent; lanes are task-scoped subagents

## Compatibility Notes

This adapter is a strong fit for:

- coding-centric teams
- artifact-driven planning and execution
- approval-aware development flows
- explicit role routing within one operator-visible task or a small set of coordinated tasks

It is a weaker fit for:

- fully opaque autonomous background organizations
- graph-native orchestration patterns that require strict native workflow nodes
- environments that demand guaranteed always-on persistent worker identities for every role

## Validation Hints

- verify that bindings requiring `local_command_execution`, `code_editing`, or `tool_approval_gates` target this adapter successfully
- treat `durable_memory` and `policy_enforced_routing` as support-level-sensitive capabilities rather than assuming ideal native behavior
- require explicit degraded-mode rules when a binding leans on adapted or externalized capabilities; do not silently replace native subagents with simulated perspectives

## Optional Observability Limits

Existing support levels are unchanged and do not imply complete telemetry or an
Agent Caravan collector. Optional associations use `metadata.observability`; this
increment implements no emitter or exporter. Missing optional collection does not
fail execution or conformance. Required semantic receipts remain validated;
requested settings do not prove independently observed effective settings.
