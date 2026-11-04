# Runtime Mapping: kiro-ide-information-technology-core-team

## Purpose

- `id`: `kiro-ide-information-technology-core-team`
- `name`: `Kiro IDE Information Technology Core Team Binding`
- `version`: `1.0.0`
- `scope`: `shared`
- `target_adapter_id`: `kiro-ide-agent-runtime`
- `mission`: Bind the default seven-role caravan template to the Kiro desktop IDE while preserving its portable role and workflow meaning.
- `summary`: One primary Kiro IDE session coordinates the task, invokes configured Kiro subagents only for authorized lanes, and records operator-observed handoffs and verification evidence.

## Target Scope

- `applies_to_artifact_ids`: `information-technology-core-team`, `program-manager`, `product-owner`, `tech-owner`, `engineer`, `quality-engineer`, `software-architect`, `release-manager`
- `applies_to_artifact_types`: `team-blueprint`, `role`
- `binding_scope_type`: `team-binding`

## Runtime Mapping

- `information-technology-core-team`: one primary Kiro chat session following the selected Agent Caravan workflow
- `program-manager`: sequencing, governance, and approval tracking
- `product-owner`: requirements, success criteria, and acceptance input
- `tech-owner`: technical approach and decomposition
- `engineer`: bounded implementation lane
- `quality-engineer`: focused verification and evidence
- `software-architect`: structural review and escalation
- `release-manager`: release and pipeline operations only when requested

Map a role to a Kiro custom agent only when that lane is authorized by the portable plan. Kiro's native agent selection and subagent facilities are runtime constructs; they do not redefine Agent Caravan role responsibilities. The coordinating session retains shared decisions and joins results.

## Capability Contract

- `required_capabilities`: `structured_output_contracts`, `dynamic_context_loading`, `local_command_execution`, `code_editing`, `tool_approval_gates`, `role_handoff`
- `preferred_capabilities`: `execution_trace`, `tool_permission_scoping`, `reasoning_effort_control`, `parallel_lane_execution`
- `capability_support_requirements`: `subagent_delegation: native`
- `optional_capabilities`: `background_execution`, `durable_memory`, `browser_interaction`, `human_confirmation_points`
- `forbidden_capabilities`: none

## Fallback And Degradation Model

- When a role-specific Kiro custom agent is absent, the primary session may perform the work only if the portable plan allows serial execution; record the fallback.
- If Kiro does not expose an attributable worker/session reference, report the work as model-reported and do not claim a native handoff or parallel lane.
- If a permission prompt or human decision cannot be attributed, stop approval-dependent actions.
- If persistent memory is unavailable, carry the minimum necessary state in an explicit Agent Caravan handoff summary.
- Treat IDE activity as operator-visible evidence, not a complete machine-readable execution trace.

## Permission And Safety Notes

Use Kiro capability rules at the narrowest practical scope. Preserve `ask` or `deny` for sensitive operations unless an explicitly authorized task requires otherwise. The skill and profile explain routing but do not enforce permissions. Release, deployment, remote mutation, and production authority remain outside ordinary engineer work.

## Observability Notes

Record the Kiro IDE version, Agent Caravan task/plan/session identifiers, selected custom-agent names, attributable worker references, decision evidence, and concise verification results when available. Mark missing fields as unavailable. Do not retain credentials, hidden reasoning, or unbounded transcripts.

## Validation Hints

- Resolve this profile against `kiro-ide-agent-runtime` and the core caravan template.
- Confirm the Kiro skill appears in the IDE for the target workspace.
- Verify permission prompts, subagent handoffs, and completion criteria in a bounded workspace before making stronger conformance claims.
- Keep CLI headless and Kiro Web evidence out of the IDE conformance record.

## Optional Observability Policy

`execution.observability` defaults to disabled and, when enabled, local
metadata. Remote export and content capture require explicit configuration.
Operator-visible IDE activity is not a complete trace collector, and
requested model or reasoning settings do not establish effective settings.
