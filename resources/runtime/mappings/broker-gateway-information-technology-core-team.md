# Runtime Mapping: broker-gateway-information-technology-core-team

## Purpose

- `id`: `broker-gateway-information-technology-core-team`
- `name`: `Broker Gateway Information Technology Core Team Binding`
- `version`: `1.1.0`
- `scope`: `shared`
- `target_adapter_id`: `broker-gateway-managed-agent-runtime`
- `mission`: Provide an illustrative team-binding for `information-technology-core-team` on a managed broker or gateway agent runtime.
- `summary`: This example shows how the core team could map onto a broker-style runtime that fronts multiple models or downstream executors, while preserving role boundaries, approval checkpoints, and externalized engineering execution where needed.

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
    - one supervisor flow or orchestration graph managing role-specific worker profiles
  - `program-manager`
    - broker-managed coordination worker
  - `product-owner`
    - broker-managed requirements and acceptance worker
  - `tech-owner`
    - broker-managed technical planning worker
  - `engineer`
    - downstream coding worker or connected execution runtime
  - `quality-engineer`
    - broker-managed verification coordinator with optional downstream gate runners
  - `software-architect`
    - broker-managed review and escalation worker
  - `release-manager`
    - broker-managed release-operations worker with connector-scoped actions
- `mapping_notes`:
  - this binding assumes the broker runtime is strongest at routing, policy, approvals, and orchestration
  - code editing and command execution may be native, adapted, or fully externalized depending on the actual runtime product
  - the engineer and release lanes may attach to downstream execution surfaces while still remaining logically inside the team binding

## Capability Contract

- `required_capabilities`:
  - `structured_output_contracts`
  - `role_handoff`
  - `supervisor_worker_pattern`
  - `policy_enforced_routing`
  - `human_confirmation_points`
- `preferred_capabilities`:
  - `dynamic_context_loading`
  - `tool_permission_scoping`
  - `execution_trace`
  - `tool_call_audit`
  - `background_execution`
- `optional_capabilities`:
  - `durable_memory`
  - `parallel_lane_execution`
  - `code_editing`
  - `local_command_execution`
- `forbidden_capabilities`:
  - none

## Fallback And Degradation Model

- `fallback_rules`:
  - if `code_editing` or `local_command_execution` is unavailable natively, externalize the engineer lane to an attached coding runtime and return evidence to the broker flow
  - if `parallel_lane_execution` is weak, run role debates serially under one supervisor state machine
  - if `durable_memory` is limited, persist state in explicit framework artifacts or broker-visible workflow records
  - if a workflow explicitly requires `execution_trace`, enforce support or an accepted fallback; optional trace gaps remain advisory
- `degraded_modes`:
  - routing-and-approval-first orchestration with downstream execution runtimes
  - serial multi-role orchestration instead of concurrent workers
- `unsupported_paths`:
  - opaque multi-step release or engineering execution with no recoverable evidence trail

## Permission And Safety Notes

- `permission_model`:
  - permissions should be scoped per worker or connector path rather than globally across the entire team
  - side-effecting operations should default to confirmation-gated or policy-gated execution
- `approval_expectations`:
  - release, deployment, ticket mutation, and documentation publication actions should remain explicitly surfaced to the operator or enterprise policy layer
- `safety_constraints`:
  - the broker must not collapse all role permissions into one unrestricted execution identity
  - downstream coding or release executors must inherit only the minimum permissions required for their lane

## Observability Notes

- `trace_expectations`:
  - supervisor decisions, worker handoffs, and connector actions should be traceable
  - any downstream executor usage should be visible as an explicit handoff, not an invisible implementation detail
- `evidence_expectations`:
  - the resolved team state should show which worker handled which stage
  - code, review, and release outputs should be attributable to a specific worker or downstream executor

## Validation Hints

- `invariants`:
  - all seven responsibility lanes remain logically present even if some are externalized
  - debate and blocking flows remain explicit and attributable
  - policy and approval enforcement remain stronger than or equal to the base team requirements
- `compatibility_assumptions`:
  - the runtime supports explicit worker routing and can preserve auditability across handoffs
  - the runtime can attach downstream executors without erasing operator control
- `validation_notes`:
  - verify that the engineer and release lanes either have native execution support or an explicit downstream executor contract
  - verify that role-level permission boundaries remain enforceable after orchestration expansion
  - verify explicitly required observability support while treating optional gaps as advisory

## Optional Observability Policy

`execution.observability` defaults to disabled; enabling it defaults to local
metadata. Remote export and content capture require explicit configuration.
Preferred observability gaps remain advisory under strict validation. Optional
`metadata.observability` associations do not substitute for required reports,
receipts, verification, or approval evidence.
