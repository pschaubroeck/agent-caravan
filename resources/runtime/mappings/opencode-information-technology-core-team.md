# Runtime Mapping: opencode-information-technology-core-team

## Purpose

- `id`: `opencode-information-technology-core-team`
- `name`: `OpenCode Information Technology Core Team Binding`
- `version`: `1.1.0`
- `scope`: `shared`
- `target_adapter_id`: `opencode-agent-runtime`
- `mission`: Bind the default seven-role caravan template to OpenCode without changing its portable role meaning.
- `summary`: One coordinating OpenCode session can delegate bounded role lanes to configured subagents and retain Agent Caravan stage, approval, and evidence records.

## Target Scope

- `applies_to_artifact_ids`: `information-technology-core-team`, `program-manager`, `product-owner`, `tech-owner`, `engineer`, `quality-engineer`, `software-architect`, `release-manager`
- `applies_to_artifact_types`: `team-blueprint`, `role`
- `binding_scope_type`: `team-binding`

## Runtime Mapping

- `information-technology-core-team`: one coordinating session with explicit stage checkpoints and authorized child sessions
- `program-manager`: planning, coordination, and approval tracking lane
- `product-owner`: requirements, criteria, and acceptance lane
- `tech-owner`: technical decision and decomposition lane
- `engineer`: bounded implementation lane
- `quality-engineer`: gate execution and evidence lane
- `software-architect`: architecture review and escalation lane
- `release-manager`: release operation and pipeline inspection lane

Each lane maps to a configured OpenCode agent or scoped child session. The configuration supplies runtime instructions and permissions; it does not redefine framework roles. A lane is reported as native delegation only when its child session reference and role turn are recorded. The coordinator owns shared decisions and joins the work.

## Capability Contract

- `required_capabilities`: `structured_output_contracts`, `dynamic_context_loading`, `local_command_execution`, `code_editing`, `tool_approval_gates`, `role_handoff`
- `preferred_capabilities`: `execution_trace`, `tool_permission_scoping`, `reasoning_effort_control`, `parallel_lane_execution`
- `capability_support_requirements`: `subagent_delegation: native`
- `optional_capabilities`: `background_execution`, `durable_memory`, `browser_interaction`, `human_confirmation_points`
- `forbidden_capabilities`: none

## Fallback And Degradation Model

- The first CLI surface is read-only and fails closed for write actions. It cannot satisfy a human approval and resume requirement.
- Approval-dependent execution must wait for a server/API surface that records the request, decision, actor, scope, and event order. A global allow rule or automatic permission acceptance is insufficient.
- If distinct lane references and overlapping intervals are unavailable, follow the workflow's serial fallback and do not claim native parallel timing.
- If durable memory is unavailable, carry explicit Agent Caravan handoff summaries between runs.
- Remote mutation and deployment remain outside this default binding unless the active task and permission boundary explicitly authorize them.

## Permission And Safety Notes

Configured OpenCode `allow`, `ask`, and `deny` permissions constrain tool use. Repository and sandbox permissions continue to apply. Role routing cannot turn the implementation lane into unrestricted release authority. Protected package installation and other approval-gated actions must stop when no attributed decision surface is available.

## Observability Notes

Record Agent Caravan task, session, run, and plan IDs alongside OpenCode version, provider and exact model ID, parent and child session references, tool events, permission events, and bounded handoff evidence. Report whether a field was observed, inferred, or unavailable. Do not persist credentials, hidden reasoning, or unbounded transcripts.

## Validation Hints

- Resolve this profile against `opencode-agent-runtime` and the core caravan template.
- Check the installed v1.18.33 event shapes before interpreting CLI or server output.
- Prove each delegated lane's worker reference and role turn; use timestamps to prove any parallel overlap.
- Keep the same portable cases and result contract across Codex and OpenCode. Full dependency-approval conformance remains unverified until the acceptance approval/resume path exists and all cases run.

## Optional Observability Policy

`execution.observability` defaults to disabled; enabling it defaults to local
metadata. Remote export and content capture require explicit configuration.
Preferred observability gaps remain advisory under strict validation. Optional
`metadata.observability` associations do not substitute for required reports,
receipts, verification, or approval evidence.
