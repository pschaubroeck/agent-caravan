# Runtime Integration: kiro-ide-agent-runtime

## Purpose

- `adapter id`: `kiro-ide-agent-runtime`
- `runtime name`: `Kiro IDE`
- `version`: `1.0.0`
- `runtime class`: `interactive coding-agent runtime`
- `scope`: `shared`
- `mission`: Describe Kiro IDE's documented capabilities and constraints for Agent Caravan bindings.
- `summary`: Model the Kiro desktop IDE as an operator-visible coding-agent harness. This artifact is based on official IDE documentation and does not assert live conformance for a specific installation.

The Kiro IDE shares a core agent engine with Kiro CLI and Web, but this adapter targets the desktop IDE experience. It does not invoke Kiro CLI or automate the Kiro UI.

## Supported Capabilities

### Execution

- `interactive_execution`: `native`
- `stepwise_execution`: `native` through interactive Specs and reviewed checkpoints
- `streaming_output`: `native` in the IDE chat and work surfaces
- `background_execution`: `adapted` through Kiro workflows
- `long_running_execution`: `adapted` through managed workflows and sessions
- `checkpoint_resume`: `adapted`; Kiro checkpoints and rewind are runtime-owned

### Delegation

- `role_handoff`: `adapted` through explicit Agent Caravan handoff summaries and Kiro custom-agent selection
- `subagent_delegation`: `native` through Kiro subagents
- `parallel_lane_execution`: `native` through Kiro's documented parallel subagents
- `supervisor_worker_pattern`: `adapted` through the primary Kiro agent and explicit subagent assignments
- `explicit_escalation`: `native` through IDE permission prompts and operator decisions

### Tools And Actions

- `local_command_execution`: `native`, subject to Kiro permission rules and the user's environment
- `api_call_execution`: `adapted` through configured MCP servers or other approved integrations
- `browser_interaction`: `adapted` through configured tools
- `document_editing`: `native` through workspace file tools
- `code_editing`: `native`
- `tool_result_structuring`: `adapted` through Agent Caravan instructions and result validation
- `tool_permission_scoping`: `native` through capability-based permission rules

### Knowledge And Context

- `context_window_only`: `native`
- `document_attachment_support`: `native` through workspace context and resources
- `dynamic_context_loading`: `native` through Steering, resources, and project context
- `knowledge_source_registration`: `adapted` through resources and MCP configuration
- `retrieval_augmented_context`: `adapted` through built-in knowledge and configured tools
- `structured_memory_store`: `externalized`

### Repository Guidance

- portable canonical entry point: `AGENTS.md`
- native entry points: workspace `AGENTS.md` and Kiro Steering files under
  `.kiro/steering/`, discovered automatically
- read the entry point first and follow its explicit links as needed

### State And Memory

- `session_state`: `native`
- `ephemeral_memory`: `native`
- `durable_memory`: `adapted` through Kiro-managed session and memory features
- `cross_run_context_persistence`: `adapted` through Kiro resources or explicit Agent Caravan handoffs
- `workflow_state_graph`: `externalized` to Agent Caravan workflow and task records

### Safety And Permissions

- `tool_approval_gates`: `native` through interactive Kiro permission prompts
- `human_confirmation_points`: `native` when an operator responds to an IDE prompt
- `permission_profiles`: `native` through user, workspace, and custom-agent rules
- `write_restrictions`: `native` through file and shell capability permissions
- `network_restrictions`: `adapted` through capability rules and the surrounding environment
- `environment_isolation`: `externalized` to the user's workspace and operating-system controls

### Observability

- `execution_trace`: `adapted` from operator-visible session and workflow evidence
- `step_logging`: `adapted` from IDE activity and user-retained evidence
- `tool_call_audit`: `adapted` from hook events or explicit session evidence
- `handoff_traceability`: `adapted` through Agent Caravan role-turn and handoff records
- `run_metadata`: `adapted` by recording app version, selected model when visible, and Agent Caravan task identifiers
- `reasoning_effort_telemetry`: `externalized`; a selected effort setting is not proof of effective inference settings

### Determinism And Control

- `structured_output_contracts`: `adapted` through prompting and validation
- `schema_validated_io`: `adapted` through Agent Caravan validation
- `policy_enforced_routing`: `adapted` through the Agent Caravan skill and Kiro agent configuration
- `deterministic_flow_nodes`: `adapted` through Kiro Specs or Workflows
- `state_machine_orchestration`: `externalized` to Agent Caravan workflow semantics

## Constraints And Evidence Boundary

- This adapter describes Kiro IDE. CLI headless behavior, Web sessions, and Mobile are separate execution surfaces and are outside this binding.
- **Local bounded verification (operator-reported):** On 2026-10-12, Kiro IDE `1.2.56` passed checks for workspace skill discovery and explicit activation, resolved adapter/profile IDs, an approval prompt and denied write under `.kiro/agents/`, and two read-only subagent results.
- The verification was reported by the operator; the repository does not retain a Kiro transcript, worker references, or timestamps. Treat it as a successful smoke check, not comprehensive conformance or machine-readable execution evidence. In particular, parallel overlap is not established by retained timing data.
- Kiro's UI and session data are runtime-owned. An Agent Caravan skill can instruct the agent and operator, but does not create a native SDK or independently observe every IDE event.
- Custom-agent and project configuration can expose the same workspace access as the user's Kiro session. Limit tools and permissions to the task boundary; do not rely on skill text alone as an enforcement mechanism.
- Kiro subagents run with their configured tools and permissions. Record worker references and role turns only when Kiro or the operator provides attributable evidence.

## Permission Model

- Kiro's capability-based permissions support `allow`, `ask`, and `deny`; deny rules override less restrictive rules.
- Interactive IDE permission prompts can provide a human decision point. Retain the requested action, decision, scope, and attribution in Agent Caravan evidence when approval is required.
- Do not treat an agent's statement that a human approved an action as approval evidence.
- Local repository changes remain subject to operating-system and workspace permissions. Remote changes, deployments, and production actions require the appropriate explicit authorization.

## Compatibility Notes

- Install `agent-caravan-kiro-orchestrator` under Kiro's global skill directory or a project `.kiro/skills/` directory. This skill is the app-native entry point; it relies on Kiro's own chat, Specs, permissions, and subagent facilities.
- Map Agent Caravan role IDs to Kiro custom agents only in runtime configuration. Custom agent names do not change portable role meaning.
- Kiro's Specs provide a product-native requirements/design/tasks flow. Use them where helpful, while preserving the selected Agent Caravan workflow and its authority boundaries.

## Validation Hints

- Confirm the Kiro IDE app version and that the selected workspace's skill is loaded.
- Extend the smoke check to custom-agent mapping, hooks, Specs, state persistence, and additional permission scopes before claiming those capabilities conform.
- Preserve visible Kiro session or worker references and timestamps for future conformance runs. Do not infer parallel timing from multiple delegated results.
- Validate the Agent Caravan profile against `kiro-ide-agent-runtime` and use the same portable conformance cases as other harnesses where the IDE can produce attributable evidence.

## Sources

- [Kiro IDE overview and shared agent features](https://kiro.dev/docs/editor/codebase-indexing/)
- [Kiro subagents](https://kiro.dev/docs/custom-agents/subagents/)
- [Kiro custom-agent configuration](https://kiro.dev/docs/ide/whats-new-v1/agent-config/)
- [Kiro IDE permissions](https://kiro.dev/docs/ide/whats-new-v1/permissions/)
- [Kiro Agent Skills](https://kiro.dev/docs/skills/)
- [Kiro Hooks](https://kiro.dev/docs/hooks/)
