# Framework Validation Specification

## Purpose

This document defines the validation model for the AI team framework.

It describes:

- what must be validated
- how validation should be layered
- which failures should block use or publication
- how degraded states should be represented
- what a valid resolved framework instance must prove

This specification is for validating the framework itself, not just validating code executed by roles within the framework.

## Design Goals

- validate framework artifacts independently of storage mechanism
- validate resolved configurations, not only raw inputs
- detect broken references and unsafe overrides early
- distinguish hard failures from degraded compatibility
- support both strict shared-catalog publication and local experimentation
- make framework regression visible as the system evolves

## Core Principle

Validation must happen at multiple layers.

It is not enough to check:

- that a file exists
- that a schema parses
- that a runtime integration is syntactically valid

The framework must also validate that the resolved configuration is coherent, complete, compatible, and safe enough for the intended use.

## Validation Layers

The framework should validate in five layers.

### 1. Artifact Validation

Checks whether an individual artifact is structurally valid.

Examples:

- required fields exist
- field values match allowed formats
- section presence is acceptable
- declared artifact type is valid

### 2. Reference And Relationship Validation

Checks whether artifacts refer to each other correctly.

Examples:

- referenced role IDs exist
- referenced domain knowledge exist
- referenced runtime integrations exist
- inheritance targets exist
- caravan templates reference valid roles

### 3. Overlay And Resolution Validation

Checks whether overlays and precedence rules produce a deterministic resolved result.

The required overlay fields, operation contracts, precedence, and provenance expectations are defined in [overlay-spec.md](overlay-spec.md).

Examples:

- precedence is unambiguous
- override operations are legal
- suppressed artifacts do not break required behavior
- replacements are type-compatible
- circular inheritance is absent

### 4. Runtime Compatibility Validation

Checks whether the resolved framework instance can be satisfied by the selected runtime integration and bindings.

Examples:

- required capabilities are supported
- constraints do not invalidate required behavior
- permission assumptions are satisfiable
- fallback behavior is well-defined where needed

### 5. Behavioral And Regression Validation

Checks whether the framework behaves as expected on representative scenarios.

Examples:

- routing resolves the right roles and domains
- debates activate when expected
- blocking authority resolves correctly
- runtime degradation is reported correctly
- previously valid example configurations remain valid

Resolved-view examples should be retained for representative configurations so changes to overlay or precedence rules can be compared over time.

## Validation Targets

The framework should validate at least these logical units:

- individual artifacts
- catalogs
- overlays
- resolved caravans
- resolved role + domain compositions
- resolved runtime instances
- published shared configurations

## Validation Rules

Validation strictness should be profile-based.

Recommended validation rules:

- `local-experimental`
- `team-shared`
- `organization-shared`
- `runtime-production`

Different profiles may permit or forbid different conditions.

Example:

- a local profile may allow incomplete runtime mappings
- an organization-shared profile should not

## Failure Classes

The framework should classify validation results clearly.

### `pass`

All required checks succeed.

### `degraded`

The configuration is usable, but one or more non-blocking expectations are not fully met.

Examples:

- only preferred non-observability runtime capabilities are missing
- optional linked context is unavailable
- non-observability runtime support is weaker than preferred

### `warn`

The configuration is still valid, but likely needs attention soon.

Examples:

- known gap documented but not yet harmful
- deprecated field usage
- stale but still valid source anchors

### `fail`

The configuration is invalid for the selected validation rules.

Examples:

- broken references
- unresolved precedence
- missing required roles
- incompatible runtime mapping

## Artifact Validation Rules

At minimum, artifact validation should check:

- artifact type is recognized
- stable ID is present
- scope is present where required
- required sections exist
- required fields are populated
- field types are valid
- duplicate IDs are rejected within the applicable namespace

## Reference Validation Rules

At minimum, relationship validation should check:

- all referenced artifact IDs resolve
- referenced artifact types match expectations
- inheritance references valid compatible parents
- caravan templates reference valid roles
- runtime mappings reference valid adapters and applicable artifacts
- domain guidance references valid base role IDs where required

## Overlay Validation Rules

At minimum, overlay validation should check:

- overlay operation is recognized
- target artifact exists when required
- `extend` does not create cycles
- `replace` uses a compatible artifact type
- `suppress` does not remove required coverage silently
- precedence rules can resolve a single winning view

## Resolved Instance Validation Rules

At minimum, resolved instances should prove:

- all required roles exist
- the selected caravan template resolves fully
- mandatory debates still have participants
- blocking responsibilities remain covered
- required domains are attached
- unresolved placeholders are absent

## Runtime Validation Rules

At minimum, runtime compatibility validation should check:

- selected runtime integration exists
- selected runtime mapping exists
- all required capabilities are satisfiable
- forbidden capabilities are not violated
- critical constraints are surfaced
- fallback behavior exists for degraded but allowed paths
- effective permission model is not contradictory

## Coverage Validation Rules

The framework should also check semantic coverage, not only structure.

Examples:

- every caravan template has an implementation role
- every caravan template has a quality role or equivalent quality coverage
- every mandatory debate has all required responsibility lanes covered
- every blocking model still has a resolution path

This helps catch structurally valid but operationally weak configurations.

## Scenario Validation

Scenario-based validation should be part of the framework.

Scenarios are not implementation-specific prompts. They are structured expected-behavior examples.

Example scenario types:

- standard ticket execution
- cross-domain implementation
- architecture-heavy change
- high-risk validation flow
- reduced local team configuration
- alternate runtime compatibility case

For each scenario, the framework should be able to assert:

- which roles activate
- which domains attach
- which debates trigger
- which runtime constraints matter
- whether the configuration is valid, degraded, or invalid

## Regression Validation

The framework should maintain representative example configurations as regression fixtures.

Examples:

- default 7-role team
- Sample Product team specialization
- local overlay with additional role variant such as `engineer-ii`
- minimal local team with suppressed roles
- alternate runtime mapping examples

These fixtures should be revalidated whenever the framework changes.

## Publication Validation

Shared or published artifacts should meet stricter validation requirements than local experiments.

Recommended publication checks:

- no unresolved warnings that would materially confuse consumers
- stable IDs and versions are present
- references resolve without local-only dependencies unless explicitly declared
- validation rules passes at the intended publication level

## Known-Gap Handling

The framework should allow known gaps to be declared without pretending the configuration is complete.

A known gap may be acceptable when:

- the gap is explicit
- it does not break required behavior for the selected profile
- degraded status is surfaced

A known gap should fail validation when:

- it blocks a required capability
- it invalidates a mandatory responsibility path
- it makes runtime mapping impossible

## Validation Output Model

Validation results should be structured.

Recommended output fields:

- target artifact or resolved instance ID
- validation rules
- overall status
- failures
- degraded items
- warnings
- unresolved assumptions
- evidence or check references

This should make it possible to automate gating without hiding useful diagnostic detail.

## Minimum Quality Gates

Before a framework change is treated as acceptable, it should at minimum pass:

- artifact validation
- reference validation
- overlay/resolution validation
- resolved-instance validation
- runtime compatibility validation for targeted runtimes
- regression fixtures for representative examples

## Recommended Stronger Gates

For mature or shared environments, add:

- scenario validation
- publication validation
- source-anchor freshness checks
- role coverage checks
- deprecated-field enforcement

## Storage And Runtime Independence

Validation should operate on logical artifacts and resolved instances.

It should not depend on:

- one file layout
- Git history
- one repository host
- one runtime vendor

Those may provide implementation evidence, but they are not the validation contract.

## Relationship To Existing Framework Artifacts

This specification validates artifacts created under:

- [logical-artifact-overlay-model.md](logical-artifact-overlay-model.md)
- [domain-pack-spec.md](domain-pack-spec.md)
- [runtime-capability-adapter-spec.md](runtime-capability-adapter-spec.md)
- [Information Technology Core Team Operating Model](../../docs/concepts/core-team-operating-model.md)
- [sample-product-domain-pack.md](../../examples/sample-organization/domain-knowledge/sample-product.md)

## Summary

The framework validation specification defines what the framework must prove before a configuration should be trusted.

It turns framework quality from an informal expectation into an explicit contract spanning artifacts, overlays, resolved instances, runtime compatibility, and regression behavior.

## Optional Observability Validation

Missing preferred observability capabilities are advisory warnings, not blocking
degradation, even under strict validation. Missing or failed optional telemetry
must not fail execution or conformance. Explicitly required observability uses
normal compatibility enforcement. Validate `execution.observability` types,
local metadata defaults, and explicit remote destination and content-capture
configuration; valid policy does not prove a collector exists.
