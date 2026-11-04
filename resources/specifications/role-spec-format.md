# Role Specification Format

## Purpose

This document defines the reusable specification for a framework `role` artifact.

A responsibility artifact represents one stable responsibility pattern in the framework. It is the core unit used by:

- caravan templates
- domain knowledge
- overlays
- runtime mappings
- validation rules

The role specification is:

- runtime-neutral
- storage-agnostic
- VCS-agnostic
- compatible with inheritance and overrides

It defines organizational meaning, not implementation details.

## Design Goals

- keep roles understandable to humans
- make roles precise enough for validation
- support base roles and role variants
- support replacements and specialist roles
- separate role meaning from runtime implementation
- preserve stable identity across overlays and bindings

## What A Role Defines

A role defines:

- why the role exists
- what it owns
- what it does not own
- what inputs it needs
- what outputs it produces
- what decisions it can make
- where it can block
- which debates it participates in
- how it hands off work
- what runtime capabilities it pressures

## What A Role Does Not Define

A role does not define:

- prompts
- model selection
- Codex agent names
- tool bindings
- skill paths
- profile names
- filesystem locations
- repo locations
- vendor-specific implementation details

Those belong in runtime mappings or packaging conventions, not in the responsibility artifact itself.

## Role Identity Model

Every responsibility artifact should include:

- `id`
- `name`
- `version`
- `scope`
- `role_type`

Optional identity fields:

- `extends`
- `replaces`
- `tags`

Roles may also declare `documentation_references` to associate supplemental
Markdown or other documentation with the role. References are metadata and do
not alter role semantics. The resolver carries them with the role assignment;
runtime integrations decide whether and how to retrieve them under the active
knowledge-access policy.

### Identity Requirements

- `id` must be stable
- `id` must be unique among role artifacts in the applicable resolved namespace
- `version` should be explicit for shared or published roles
- `scope` must align with the framework scope model

## Role Types

Every role should declare one of the following types.

### `base`

A foundational reusable role.

Examples:

- `engineer`
- `product-owner`
- `tech-owner`

### `variant`

A role that extends a base role while narrowing or broadening its responsibility pattern.

Examples:

- `engineer-ii`
- `senior-quality-engineer`

### `replacement`

A role intended to substitute for another role in some resolved configurations.

Examples:

- a locally adapted architecture role replacing `software-architect`

### `specialist`

A role used for a narrower specialized lane.

Examples:

- `data-engineer`
- `security-engineer`
- `integration-architect`

## Required Sections

Every responsibility artifact should include the following sections.

### 1. Purpose

Defines:

- mission
- short reason the role exists

### 2. Responsibilities

Defines:

- what the role owns
- what the role does not own
- expected outputs or produced artifacts

### 3. Operating Model

Defines:

- required inputs
- handoff triggers
- working style
- approval limits

### 4. Decision Rights

Defines:

- what the role can block
- what the role cannot block
- escalation authority
- debate participation

### 5. Runtime Expectations

Defines:

- required capabilities
- preferred capabilities
- optional capabilities
- forbidden capabilities when relevant

These should use the framework runtime capability vocabulary rather than vendor-specific terms.

### 6. Validation Hints

Defines:

- invariants that extensions must preserve
- coverage expectations
- role-specific validation notes

## Optional Sections

Depending on the role, an artifact may also include:

- domain compatibility notes
- team-blueprint compatibility notes
- documentation expectations
- known constraints
- deprecation notes
- publication notes

## Recommended Field Model

The role specification should logically contain at least these fields.

### Identity

- `id`
- `name`
- `version`
- `scope`
- `role_type`
- `extends` optional
- `replaces` optional

### Purpose

- `mission`
- `summary`

### Responsibilities

- `owns`
- `does_not_own`
- `produces`

### Operating Model

- `required_inputs`
- `handoff_triggers`
- `working_style`
- `approval_limits`

### Decision Rights

- `can_block`
- `cannot_block`
- `debate_participation`
- `escalation_authority`

### Runtime Expectations

- `required_capabilities`
- `preferred_capabilities`
- `optional_capabilities`
- `forbidden_capabilities`

### Validation Hints

- `invariants`
- `coverage_expectations`
- `validation_notes`

## Inheritance Model

Roles may inherit from other roles.

### `extends`

Use when a role remains meaningfully the same lane but changes breadth, depth, or seniority.

Example:

- `engineer-ii` extends `engineer`

### Inheritance Rules

- a child role must preserve the parent role's core semantic lane
- a child role may add responsibilities
- a child role may narrow or broaden decision rights
- a child role must not contradict required invariants from the parent
- circular inheritance is invalid

## Replacement Model

Use `replaces` when a role is intended to stand in for another role in a resolved configuration.

Example:

- a local role can replace `software-architect`

### Replacement Rules

- replacements must be type-compatible at the framework level
- replacements must preserve required team coverage
- replacements must not silently drop mandatory debate or blocking coverage

## Decision Rights Model

Decision-right fields are central to the role spec.

### `can_block`

Defines legitimate reasons the role may stop progress.

### `cannot_block`

Defines areas where the role must not use blocking authority.

### `debate_participation`

Defines:

- mandatory debates
- optional debates
- triggered debates

### `escalation_authority`

Defines where the role can escalate concerns or force broader review.

## Runtime Expectation Model

Roles should express capability pressure without binding to one runtime.

Examples:

- `engineer` may require `code_editing` and `local_command_execution`
- `quality-engineer` may prefer `result_structuring` and `environment_inspection`-like capabilities
- `tech-owner` may prefer `role_handoff`, `repository_inspection`, and planning-support capabilities

These are logical expectations only. Actual runtime support is resolved later through adapters and bindings.

## Role Coverage Model

The validation system should be able to reason about role coverage.

A role may optionally declare whether it is:

- `core`
- `optional`
- `replaceable`
- `must_be_covered`

### Interpretation

- `core`
  - expected in the default framework pattern

- `optional`
  - may be absent without invalidating the team

- `replaceable`
  - can be substituted if equivalent coverage exists

- `must_be_covered`
  - the responsibility lane must exist in some form, even if the specific role ID is replaced or suppressed

## Role Compatibility Notes

Roles may optionally define compatibility notes for:

- specific caravan templates
- specific domain knowledge
- specific validation rules

These should be advisory unless promoted into a formal validation rule elsewhere.

## Validation Rules

At minimum, responsibility artifact validation should check:

- required identity fields exist
- `role_type` is valid
- required sections exist
- required lists or structured fields are present
- `extends` target exists when declared
- `replaces` target exists when declared
- no circular inheritance exists
- no incompatible replacement is declared

## Stronger Validation Rules

Recommended additional role checks:

- decision rights are not self-contradictory
- `can_block` and `cannot_block` are meaningfully distinct
- produced outputs align with stated responsibilities
- runtime expectations use valid capability identifiers
- child roles preserve parent invariants

## Human Maintenance Guidance

Roles should remain concise enough to review and evolve.

Recommended practice:

- keep the mission short
- keep ownership boundaries explicit
- avoid embedding process details that belong in caravan templates
- avoid embedding domain details that belong in domain knowledge
- avoid embedding runtime details that belong in bindings

## Relationship To Existing Artifacts

This spec is intended to formalize the role semantics currently described in:

- [Information Technology Core Team Operating Model](../../docs/concepts/core-team-operating-model.md)

It aligns with:

- [logical-artifact-overlay-model.md](logical-artifact-overlay-model.md)
- [runtime-capability-adapter-spec.md](runtime-capability-adapter-spec.md)
- [framework-validation-spec.md](framework-validation-spec.md)

## Example Mapping To Current Roles

This format is intended to represent your current framework roles such as:

- `program-manager`
- `product-owner`
- `tech-owner`
- `engineer`
- `quality-engineer`
- `software-architect`
- `release-manager`

And future variants such as:

- `engineer-ii`
- `data-engineer`
- `security-engineer`

## Summary

The role specification format turns roles into first-class framework artifacts.

It provides enough structure for inheritance, replacement, validation, runtime mapping, and long-term catalog reuse while keeping role definitions independent from any specific storage mechanism or AI runtime.
