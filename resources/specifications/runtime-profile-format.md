# Runtime Mapping Specification Format

## Purpose

This document defines the reusable specification for a framework `runtime-profile` artifact.

A runtime mapping is the artifact that maps resolved framework meaning onto a specific runtime integration.

It answers questions such as:

- how a framework role is realized in one runtime
- how a caravan template is realized in one runtime
- which runtime capabilities are required for that mapping
- what constraints or fallbacks apply in that runtime
- what implementation-specific constructs are attached to framework artifacts

The runtime mapping is the layer where implementation detail is allowed to appear, but only in service of mapping already-defined framework artifacts onto a selected runtime.

## Design Goals

- keep framework meaning separate from implementation detail
- support multiple runtime products for the same framework artifacts
- allow one runtime to have multiple binding strategies
- support partial or degraded runtime mappings explicitly
- make runtime compatibility machine-checkable

## What A Runtime Mapping Defines

A runtime mapping defines:

- the target runtime integration
- which framework artifacts it applies to
- which runtime-native constructs represent those artifacts
- required and preferred capabilities for the mapping
- fallback behavior for degraded support
- implementation notes and known limitations

## What A Runtime Mapping Does Not Define

A runtime mapping does not define:

- the framework role itself
- the framework team structure itself
- the domain-pack structure itself
- the logical overlay model
- the runtime integration's capability vocabulary

Those are defined elsewhere in the framework.

## Relationship To Other Artifacts

A runtime mapping depends on:

- [logical-artifact-overlay-model.md](logical-artifact-overlay-model.md)
- [runtime-capability-adapter-spec.md](runtime-capability-adapter-spec.md)
- [role-spec-format.md](role-spec-format.md)
- [team-blueprint-format.md](team-blueprint-format.md)
- [framework-validation-spec.md](framework-validation-spec.md)

It should never be treated as a replacement for any of those artifact types.

## Binding Scope

A runtime mapping may target one or more framework artifact types.

Common binding scopes:

- one role
- one caravan template
- one domain-pack-aware role variant
- one full resolved team shape

The framework should allow fine-grained bindings, but the binding artifact must declare what it actually targets.

## Binding Identity Model

Every runtime mapping should include:

- `id`
- `name`
- `version`
- `scope`
- `target_adapter_id`

Optional identity fields:

- `extends`
- `replaces`
- `tags`

## Required Sections

### 1. Purpose

Defines:

- binding identity
- intended runtime target
- summary of what the binding covers

### 2. Target Scope

Defines:

- which framework artifact IDs this binding applies to
- which artifact types are in scope
- whether the binding is role-level, team-level, or mixed

### 3. Runtime Mapping

Defines:

- the runtime-native construct type used for each targeted framework artifact
- mapping notes for how the framework artifact is represented

Examples of runtime-native constructs might include:

- agent
- prompt
- flow
- profile
- tool bundle
- graph node
- connector-backed assistant
- broker-managed worker

These are examples only. The framework does not standardize one set of runtime-native constructs.

### 4. Capability Contract

Defines:

- required capabilities
- preferred capabilities
- optional capabilities
- forbidden capabilities

These must use the framework runtime capability vocabulary.

### 5. Fallback And Degradation Model

Defines:

- what happens if preferred capabilities are unavailable
- what happens if the runtime can only satisfy the binding in adapted or externalized form
- what degraded mode is acceptable for this binding

### 6. Permission And Safety Notes

Defines:

- expected permission model
- approval expectations
- important safety constraints or caveats

### 7. Observability Notes

Defines:

- what execution visibility is expected
- what evidence or traceability is assumed for this binding

### 8. Validation Hints

Defines:

- invariants that the binding must preserve
- known compatibility assumptions
- validation notes specific to this binding

### 9. Optional Execution Settings

Bindings may provide runtime-specific defaults for an workflow without
making those settings part of the runtime-neutral team or role definitions:

- `execution.model_profile`
- `execution.instructions`
- `execution.tools`
- `execution.skills`
- `execution.workspace`
- `execution.output_schema`
- `execution.guardrails`
- `execution.persistence`
- `execution.limits`

These settings are advisory unless the adapter declares support. A binding must
not use them to bypass role permissions, approval gates, or execution-profile
termination and escalation rules.

### 10. Execution Projection

A runtime mapping may declare `execution_profile_ids` to identify the portable
workflows it supports. It may also include `execution_projection` describing
how generic workflow concepts map to runtime constructs. The projection may
mention runtime-specific tasks, nodes, agents, graphs, prompts, tools, or
checkpoints; those concepts must remain in the runtime mapping rather than the
portable execution workflow.

## Optional Sections

Depending on the runtime and scope, a binding may also include:

- domain-attachment notes
- memory/state notes
- orchestration notes
- degraded-mode examples
- publication notes
- deprecation notes

## Recommended Field Model

### Identity

- `id`
- `name`
- `version`
- `scope`
- `target_adapter_id`
- `extends` optional
- `replaces` optional

### Purpose

- `mission`
- `summary`

### Target Scope

- `applies_to_artifact_ids`
- `applies_to_artifact_types`
- `binding_scope_type`

### Runtime Mapping

- `runtime_constructs`
- `mapping_notes`

### Capability Contract

- `required_capabilities`
- `preferred_capabilities`
- `optional_capabilities`
- `forbidden_capabilities`

### Fallback And Degradation Model

- `fallback_rules`
- `degraded_modes`
- `unsupported_paths`

### Permission And Safety Notes

- `permission_model`
- `approval_expectations`
- `safety_constraints`

### Observability Notes

- `trace_expectations`
- `evidence_expectations`

### Validation Hints

- `invariants`
- `compatibility_assumptions`
- `validation_notes`

## Binding Scope Types

The binding should declare which kind of mapping it represents.

Recommended values:

- `role-binding`
- `team-binding`
- `domain-aware-role-binding`
- `resolved-instance-binding`

### `role-binding`

Maps one or more framework roles to runtime-native constructs.

### `team-binding`

Maps a caravan template to runtime-native orchestration or grouping concepts.

### `domain-aware-role-binding`

Maps a role in a domain-sensitive way without redefining the role itself.

### `resolved-instance-binding`

Maps a specific resolved team/domain/runtime combination.

## Runtime Mapping Model

The mapping section should be explicit about how a framework artifact appears in the runtime.

Examples:

- one role maps to one runtime agent
- one role maps to one prompt plus one tool bundle
- one team maps to one orchestrated flow with distinct worker nodes
- one role maps to a broker-managed worker class inside a gateway platform

The binding must not assume that every runtime uses one-agent-per-role semantics.

## Capability Requirement Rules

Binding capability requirements should be interpreted using the capability levels from the runtime integration.

Examples:

- a required capability may be acceptable as `native` or `adapted`
- a stricter binding may require `native` support specifically
- a weaker binding may accept `externalized` support for some preferred capabilities

Bindings should declare when support-level distinctions matter.

Use `capability_support_requirements` when the binding depends on a minimum
support level. For example:

```yaml
capability_support_requirements:
  subagent_delegation: native
  parallel_lane_execution: native
```

The resolver must reject a binding whose adapter provides a weaker level than
the declared requirement. This keeps a runtime-neutral requirement such as
independent role workers separate from the runtime-specific mechanism used to
create them.

## Fallback Rules

Fallback rules should be explicit rather than implied.

Examples:

- if `parallel_lane_execution` is unavailable, degrade to serial delegation
- if `durable_memory` is unavailable, require explicit context reload each run
- if a workflow explicitly requires `execution_trace`, enforce support or an accepted fallback; optional trace gaps remain advisory

This prevents degraded behavior from becoming invisible.

## Permission Model Rules

Bindings should declare what kind of permission environment they assume.

Examples:

- read-only runtime
- bounded local write
- bounded remote mutation
- human approval required for side effects
- externalized permission enforcement

The binding should not grant permissions itself. It should only declare the assumption or requirement.

## Observability Rules

Bindings should state what level of visibility is expected for safe operation.

Examples:

- step-level trace available
- tool call audit available
- only final output visible
- external logging required

This matters because some team behaviors are harder to trust in opaque runtimes.

## Inheritance And Replacement

Bindings may also use `extends` and `replaces`.

### `extends`

Use when one binding is a structured specialization of another.

Example:

- a domain-aware binding extends a generic role binding

### `replaces`

Use when one binding is intended to substitute for another in a resolved view.

Example:

- a local runtime mapping replacing a shared default binding

## Validation Rules

At minimum, runtime-profile validation should check:

- identity fields exist
- target adapter exists
- targeted framework artifact IDs exist
- binding scope type is valid
- capability identifiers are valid
- fallback rules are defined where degraded support is allowed
- forbidden capabilities do not contradict the selected adapter

## Stronger Validation Rules

Recommended additional checks:

- runtime-native construct mappings are present for every targeted artifact
- permission assumptions align with the adapter's declared permission model
- explicitly required observability assumptions are satisfiable
- degraded modes are explicit instead of silent
- child bindings preserve parent invariants

## Relationship To Resolved Runtime Instances

Runtime bindings do not directly replace runtime integrations.

The resolution path should be:

1. resolve framework artifacts
2. select runtime integration
3. apply runtime mappings
4. validate compatibility
5. produce resolved runtime instance

The runtime mapping is therefore one layer in the path, not the final product itself.

## Human Maintenance Guidance

Bindings should stay concrete and implementation-aware, but still scoped.

Recommended practice:

- keep mapping notes specific
- avoid re-documenting the runtime integration in full
- avoid redefining the framework role
- state degraded behavior explicitly
- keep runtime-native naming clear but bounded to the binding section

## Example Relationship To Current Framework

This format is intended to support future bindings such as:

- Codex bindings for `program-manager`, `tech-owner`, or `engineer`
- a Droid binding for an organizational caravan template
- a low-code platform binding for a reduced team flow
- a domain-aware `sample-product` engineer binding in one runtime

## Summary

The runtime-profile specification defines how framework meaning is attached to a concrete runtime.

It keeps roles, teams, and domains portable while allowing implementors to map them onto whatever runtime-native constructs, permission models, and degraded modes their chosen AI platform actually supports.

## Optional Observability Policy

Profiles may declare `execution.observability` with `enabled` (boolean, default
`false`), `export` (`local` or `remote`, default `local`), `capture_content`
(boolean, default `false`), and optional nonempty opaque `destination_ref`.
Remote export requires explicit `export: remote` and `destination_ref`.
Enabling observability defaults to local metadata; prompt, response, tool-output,
and other content capture requires explicit `capture_content: true`.

The Codex and OpenCode Agent Caravan adapters emit local workflow start/finish
markers through the optional Agent Observability package when enabled. This
measures only the Agent Caravan-owned workflow dispatch boundary; it does not
claim per-role, agent, skill, model, or tool coverage. The adapter does not
implement remote export or content capture. Local telemetry does not imply local
runtime providers or model calls. Required workflow reports and receipts remain
validated independently. Preferred observability gaps are advisory even in
strict validation; explicit requirements use normal capability and
minimum-support enforcement.
