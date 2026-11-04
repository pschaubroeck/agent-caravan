# Caravan Template Specification Format

## Purpose

This document defines the reusable specification for a framework `team-blueprint` artifact.

A caravan template is the artifact that assembles roles into an operating team shape. It defines:

- which roles participate
- how work flows through the team
- which debates are mandatory
- which debates are conditional
- how blocking authority is distributed
- how documentation and governance expectations are organized

The caravan template is:

- runtime-neutral
- storage-agnostic
- VCS-agnostic
- compatible with overlays and local variants

It defines organizational operating structure, not implementation wiring.

## Design Goals

- make teams first-class reusable artifacts
- keep role semantics separate from team semantics
- support multiple default team shapes across one framework
- support local suppression, substitution, and extension of roles
- make workflow and debate expectations machine-checkable later

## What A Caravan Template Defines

A caravan template defines:

- team identity
- included roles
- required role coverage
- stage flow
- debate model
- blocking model
- documentation model
- governance notes

## What A Caravan Template Does Not Define

A caravan template does not define:

- domain-specific source trees
- runtime mappings
- storage layout
- vendor prompts or agents
- repo paths
- one specific AI product implementation

Those belong in domain knowledge, runtime mappings, or packaging layers.

## Team Identity Model

Every caravan template should include:

- `id`
- `name`
- `version`
- `scope`

Optional identity fields:

- `extends`
- `replaces`
- `tags`

## Required Sections

### 1. Purpose

Defines:

- mission of the team shape
- summary of where this caravan template is intended to be used

### 2. Team Composition

Defines:

- included role IDs
- optional role IDs
- required coverage expectations
- replacement allowances

### 3. Stage Flow

Defines:

- default operating stages
- which roles are primary in each stage
- expected outputs or transitions between stages

### 4. Debate Model

Defines:

- mandatory debates
- triggered debates
- required participants for each debate
- purpose of each debate

### 5. Blocking Model

Defines:

- which role lanes can block
- blocking guardrails
- resolution expectations when a block occurs

### 6. Documentation Model

Defines:

- which role lanes are expected to maintain which documentation categories

### 7. Governance Notes

Defines:

- cross-cutting governance or approval expectations
- handoff or escalation guidance that applies at team level rather than role level

### 8. Runtime Expectations

Defines:

- required team-level capabilities
- preferred team-level capabilities
- optional team-level capabilities

These should use the framework runtime capability vocabulary.

### 9. Validation Hints

Defines:

- invariants the caravan template must preserve
- coverage expectations
- validation notes for overlays or replacements

## Optional Sections

Depending on the team, a template may also include:

- domain compatibility notes
- minimum viable team variant notes
- specialist lane activation notes
- deprecation notes
- publication notes

## Recommended Field Model

### Identity

- `id`
- `name`
- `version`
- `scope`
- `extends` optional
- `replaces` optional

### Purpose

- `mission`
- `summary`

### Team Composition

- `core_roles`
- `optional_roles`
- `required_coverage`
- `replacement_rules`

### Stage Flow

- `stages`
- `stage_owners`
- `stage_outputs`

### Debate Model

- `mandatory_debates`
- `triggered_debates`
- `debate_participants`
- `debate_purposes`

### Blocking Model

- `blocking_lanes`
- `blocking_guardrails`
- `block_resolution_notes`

### Documentation Model

- `documentation_ownership`

### Governance Notes

- `governance_rules`
- `governance_handoffs`

### Runtime Expectations

- `required_capabilities`
- `preferred_capabilities`
- `optional_capabilities`

### Validation Hints

- `invariants`
- `coverage_expectations`
- `validation_notes`

## Team Composition Rules

- every referenced role ID must resolve to a valid responsibility artifact
- suppressed roles must not break required coverage unless replaced
- replacements must preserve required coverage and debate participation
- optional roles may be absent if their responsibility lane is not required

## Inheritance And Replacement

### `extends`

Use when one caravan template is a structured variant of another.

Example:

- a minimal local caravan template extends a fuller shared caravan template

### `replaces`

Use when a caravan template is intended to stand in for another template in a resolved configuration.

Example:

- a team-specific override replacing a generic shared template

## Validation Rules

At minimum, team-blueprint validation should check:

- identity fields exist
- required sections exist
- all referenced role IDs resolve
- stage flow is complete
- mandatory debates have participants
- required coverage is preserved
- blocking coverage exists

## Stronger Validation Rules

Recommended additional checks:

- documentation ownership covers the expected categories
- governance notes align with role responsibilities
- runtime expectations are valid capability identifiers
- overlay changes do not silently remove mandatory debate participants

## Relationship To Existing Artifacts

This spec works with:

- [role-spec-format.md](role-spec-format.md)
- [logical-artifact-overlay-model.md](logical-artifact-overlay-model.md)
- [runtime-capability-adapter-spec.md](runtime-capability-adapter-spec.md)
- [framework-validation-spec.md](framework-validation-spec.md)

## Summary

The team-blueprint specification turns team operating models into first-class framework artifacts.

It allows roles to be assembled into reusable team shapes that can later be specialized by domains, overlays, and runtime mappings without collapsing team design into implementation detail.
