# Runtime Integration: opencode-agent-runtime

## Purpose

- `adapter id`: `opencode-agent-runtime`
- `runtime name`: `OpenCode`
- `version`: `1.1.0`
- `runtime class`: `interactive coding-agent runtime`
- `scope`: `local`
- `mission`: Describe OpenCode's documented execution capabilities and the evidence required to bind Agent Caravan work to them.
- `tested runtime target`: `OpenCode v1.18.33`; the operator reports this version and the availability of OpenAI GPT-6 Astra, Sol, and Luna and local Ollama Qwen models. Model availability is configuration evidence, not execution evidence.

This artifact describes the runtime. Team roles, experiment criteria, and approval policy remain in their portable artifacts and bindings.

## Supported Capabilities

Capability status below describes the documented OpenCode surface; it is not
evidence that every capability has been exercised through Agent Caravan. The
repository implements bounded CLI and server execution surfaces for OpenCode
v1.18.33. The dependency-approval study completed both accept and reject cases
with passing results, but those cases do not establish every capability below
or compatibility with every OpenCode configuration. See the
[integration guide](../../../docs/integrations/opencode-adapter.md) and
[Codex/OpenCode comparison](../../../docs/integrations/codex-opencode-comparison.md)
for the tested scope and limits.

### Execution

- `interactive_execution`: `native`
- `stepwise_execution`: `native`
- `streaming_output`: `native`
- `background_execution`: `adapted` through a caller-managed process or server session
- `long_running_execution`: `adapted` through a caller-managed session
- `checkpoint_resume`: `adapted` through session persistence; a portable checkpoint contract remains external

### Delegation

- `role_handoff`: `adapted` through configured agents and explicit Agent Caravan handoff records
- `subagent_delegation`: `native` through OpenCode subagents and task invocation
- `parallel_lane_execution`: `adapted`; distinct child sessions alone do not prove overlap
- `supervisor_worker_pattern`: `adapted` through a primary agent and invoked subagents
- `explicit_escalation`: `adapted` through permission requests and the binding's approval policy

### Tools And Actions

- `local_command_execution`: `native` through the command tool, subject to permissions
- `api_call_execution`: `adapted` through configured tools or external integration
- `browser_interaction`: `adapted` through configured tools or external integration
- `document_editing`: `adapted` through file tools
- `code_editing`: `native`
- `tool_result_structuring`: `adapted` through event and result normalization
- `tool_permission_scoping`: `native` through `allow`, `ask`, and `deny` rules

### Knowledge And Context

- `context_window_only`: `native`
- `document_attachment_support`: `adapted` through supported prompt and file inputs
- `dynamic_context_loading`: `native` through file and tool reads
- `knowledge_source_registration`: `adapted` through configured tools and sources
- `retrieval_augmented_context`: `adapted` through configured tools and sources
- `structured_memory_store`: `externalized`

### State And Memory

- `session_state`: `native`
- `ephemeral_memory`: `native`
- `durable_memory`: `adapted` through retained sessions or an external store
- `cross_run_context_persistence`: `adapted` through explicit handoffs or an external store
- `workflow_state_graph`: `externalized`

### Safety And Permissions

- `tool_approval_gates`: `native` through `ask` permission rules
- `human_confirmation_points`: `adapted`; a permission response is evidence of a human decision only when its actor and event provenance are recorded
- `permission_profiles`: `native` through agent and project configuration
- `write_restrictions`: `native` through edit and command permissions
- `network_restrictions`: `adapted` through tool permissions and environment controls
- `environment_isolation`: `externalized` to the operator's worktree or sandbox

### Observability

- `execution_trace`: `adapted` from JSON event output or the server event stream
- `step_logging`: `adapted` from runtime events
- `tool_call_audit`: `adapted` from tool and permission events
- `handoff_traceability`: `adapted` using child session references plus Agent Caravan handoffs
- `run_metadata`: `adapted` by recording OpenCode version, provider, model, session IDs, and Agent Caravan task/run IDs
- `reasoning_effort_telemetry`: `unsupported` until the target runtime exposes verifiable effective settings

### Determinism And Control

- `structured_output_contracts`: `adapted` through prompting and validation
- `schema_validated_io`: `adapted` through Agent Caravan validation
- `policy_enforced_routing`: `adapted` through binding configuration and permission rules
- `deterministic_flow_nodes`: `externalized`
- `state_machine_orchestration`: `externalized`

## Repository Guidance

The portable canonical entry point is `AGENTS.md`. OpenCode discovers project
`AGENTS.md` files automatically. The adapter declares `AGENTS.md` as its native
file and follows explicit references from it as needed. A future adapter can
declare another native filename or location; its binding must map the portable
guidance into that mechanism.

## Constraints And Evidence Boundary

- OpenCode's CLI documents non-interactive `run` with JSON event output. Its server documents session APIs, an event stream, and permission replies. The first CLI integration slice is read-only and fails closed for writes; attributed approval/resume needs a later server/API slice. The adapter must verify the exact event shapes on v1.18.33 before claiming conformance.
- OpenCode documents primary agents, subagents, and child sessions. A role lane is `native` only when its child session or worker reference can be linked to the task, run, role turn, and handoff. A configured agent name or generated answer alone is insufficient.
- A `native-parallel` claim additionally requires distinct lane references and overlapping timezone-aware start/end intervals. Without timing evidence, report timing as unverified.
- The operator's model picker shows OpenAI and Ollama choices. Record the provider, exact model ID, and configuration for each run; displayed names alone do not establish equivalent model behavior across harnesses.
- Do not use permissive automation flags or a global `allow` rule as evidence of human approval. For a human-gated case, retain the request, decision, actor attribution, scope, timestamps, and evidence references.
- A model's statement that approval occurred is reported-by-agent evidence. Human-reviewed evaluation remains a separate record.

## Permission Model

- The binding declares required tool access and applies narrow `ask` or `deny` rules at the OpenCode boundary.
- The conformance acceptance case must stop at the dependency installation boundary, surface the exact requested action, and resume only after a recorded decision.
- A denied request must leave the protected action unexecuted. A missing or unverifiable decision cannot satisfy an approval assertion.
- Repository and sandbox permissions remain in force independently of OpenCode configuration.

## Compatibility Notes

This adapter can serve multiple organization and team bindings. Each binding must map portable role IDs to OpenCode agent configuration without changing role meaning. A local Ollama run can test adapter mechanics; a comparison against Codex should pin the same provider and model where possible and disclose any model difference.

## Validation Hints

- Pin OpenCode `v1.18.33` and capture its actual provider/model identifiers and event schema before implementing a live binding.
- Prove event attribution across Agent Caravan task, session, run, and plan IDs and OpenCode session and child session IDs.
- Use the same runtime-neutral conformance cases and normalized result contract as the Codex bridge. Do not import a Codex-named request or projection into this binding.
- Exercise read-only, reject, and human-approved acceptance paths, then evaluate harness parity separately from the human rubric.

## Sources

- [OpenCode agents and subagents](https://opencode.ai/docs/agents/)
- [OpenCode permissions](https://opencode.ai/docs/permissions/)
- [OpenCode CLI](https://opencode.ai/docs/cli/)
- [OpenCode server API](https://opencode.ai/docs/server/)

## Optional Observability Limits

Existing support levels are unchanged and do not imply complete telemetry or an
Agent Caravan collector. Optional associations use `metadata.observability`; this
increment implements no emitter or exporter. Missing optional collection does not
fail execution or conformance. Required semantic receipts remain validated;
requested settings do not prove independently observed effective settings.
