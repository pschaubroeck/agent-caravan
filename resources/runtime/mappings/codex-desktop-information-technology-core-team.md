# Runtime Mapping: codex-desktop-information-technology-core-team

## Purpose

- `id`: `codex-desktop-information-technology-core-team`
- `name`: `Codex Desktop Information Technology Core Team Binding`
- `version`: `1.1.0`
- `scope`: `local`
- `target_adapter_id`: `codex-desktop-agent-runtime`
- `mission`: Bind the default seven-role organizational caravan template onto the current Codex desktop coding-agent runtime.
- `summary`: This binding realizes `information-technology-core-team` as one coordinating Codex task that can delegate work across role-specialized lanes, use local tools, and preserve approval boundaries for side effects.

## Target Scope

- `applies_to_artifact_ids`:
  - `information-technology-core-team`
  - `program-manager`
  - `product-owner`
  - `tech-owner`
  - `engineer`
  - `quality-engineer`
  - `software-architect`
  - `release-manager`
- `applies_to_artifact_types`:
  - `team-blueprint`
  - `role`
- `binding_scope_type`: `team-binding`

## Runtime Mapping

- `runtime_constructs`:
  - `information-technology-core-team`
  - one coordinating Codex task that dispatches scoped native subagents for independent role lanes and retains stage ownership and debate routing
  - `program-manager`
    - planning and coordination lane expressed through structured task management, artifact routing, and approval tracking
  - `product-owner`
    - requirements and acceptance-criteria lane expressed through scoped discovery, documentation synthesis, and UAT framing
  - `tech-owner`
    - decomposition and technical decision lane expressed through repo inspection, implementation planning, and review-resolution orchestration
  - `engineer`
    - implementation lane expressed through direct repository editing, command execution, and verification follow-through
  - `quality-engineer`
    - verification lane expressed through targeted gate execution, evidence capture, and readiness assessment
  - `software-architect`
    - structural review lane expressed through architecture-focused analysis and escalation guidance
  - `release-manager`
    - GitLab and release-operations lane expressed through bounded remote operations and pipeline/release inspection
- `mapping_notes`:
  - the team is coordinated through one active task that owns the plan and joins task-scoped subagent lanes; it does not require permanently running agents
  - role specialization is implemented through dedicated child-agent instructions and structured result collection
  - debate stages are represented as explicit multi-role reasoning checkpoints rather than invisible internal chain-of-thought transitions

## Capability Contract

- `required_capabilities`:
  - `structured_output_contracts`
  - `dynamic_context_loading`
  - `local_command_execution`
  - `code_editing`
  - `tool_approval_gates`
  - `role_handoff`
- `preferred_capabilities`:
  - `execution_trace`
  - `tool_call_audit`
  - `document_editing`
  - `tool_permission_scoping`
  - `reasoning_effort_control`
  - `parallel_lane_execution`
- `capability_support_requirements`:
  - `subagent_delegation`: `native`
- `optional_capabilities`:
  - `background_execution`
  - `durable_memory`
  - `browser_interaction`
  - `human_confirmation_points`
- `forbidden_capabilities`:
  - none

## Fallback And Degradation Model

- `fallback_rules`:
  - follow the workflow topology; use its declared serial fallback when optional parallel lane execution is unavailable
  - if `durable_memory` is unavailable, require each stage owner to restate the current decision state in the active task artifacts
  - if `background_execution` is unavailable, long-running release or verification operations remain human-triggered from the active task
  - if `document_editing` is limited, produce markdown-ready artifacts locally and externalize final publication to a supported connector path
- `degraded_modes`:
  - serial execution of optional lanes in the profile-declared order when parallel lane execution is unavailable
  - manual handoff summaries in place of native cross-run memory
- `unsupported_paths`:
  - autonomous unapproved remote mutation across Jira, Confluence, GitLab, or production systems

## Permission And Safety Notes

- `permission_model`:
  - bounded local write access is acceptable for implementation lanes
  - remote writes require explicit user approval or an approved workflow boundary
  - sensitive environment mutation should remain outside the default team binding unless separately authorized
  - external knowledge access defaults to enabled and may be restricted by the active policy to approved sources or disabled
- `approval_expectations`:
  - Confluence, Jira, GitLab, deployment, and other remote side effects require explicit confirmation when the active workflow treats them as mutations
  - destructive local actions remain opt-in and should not be inferred from general implementation authority
- `safety_constraints`:
  - the runtime must preserve approval boundaries even when one task is operating across multiple roles
  - role specialization must not bypass role-legitimate blocking or debate paths

## Observability Notes

- `trace_expectations`:
  - commentary updates, command execution output, file diffs, and tool-call records should be visible to the operator
  - delegated or parallel lanes should return concise handoff summaries before merge back into the main task
- `evidence_expectations`:
  - implementation lanes should surface changed files, verification results, and unresolved risks
  - release-oriented lanes should surface pipeline state, branch status, and promotion evidence

## Validation Hints

- `invariants`:
  - every activated role lane is attributable to a task-scoped subagent reference
  - delegated role lanes receive the resolved reasoning level when the runtime supports native control
  - reasoning evidence distinguishes accepted dispatch from runtime-observed effective settings
  - mandatory debate flows remain explicit
  - product, implementation, quality, architecture, and release authority remain distinct
- `compatibility_assumptions`:
  - the runtime can safely combine local repo work, command execution, and structured role-routing inside one operator-visible task
  - the runtime can externalize approvals without losing operator control
- `validation_notes`:
  - verify that all core team stages map to an observable runtime behavior
  - verify that approval-requiring operations are still blocked at the right boundary
  - verify that `release-manager` responsibilities do not silently collapse into unrestricted `engineer` authority

## Optional Observability Policy

`execution.observability` defaults to disabled; enabling it defaults to local
metadata. Remote export and content capture require explicit configuration.
Preferred observability gaps remain advisory under strict validation. Optional
`metadata.observability` associations do not substitute for required reports,
receipts, verification, or approval evidence.
