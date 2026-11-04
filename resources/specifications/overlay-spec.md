# Configuration Override Specification

## Purpose

This document defines the reusable specification for a configuration override, represented by the `overlay` artifact type.

A configuration override is a scoped, explicit modification to a resolved artifact view. It changes how selected artifacts compose without mutating the base artifact or requiring a fork of the broader organization, caravan template, domain, or runtime model. The remaining uses of “overlay” in this specification refer to that same artifact type.

Overlays are storage-agnostic, runtime-neutral, and applicable to any artifact type where the logical artifact model permits composition.

## Required Identity

Every overlay must declare:

- `artifact_type`: `overlay`
- stable `id`
- `name`
- `version` or equivalent revision
- `scope`
- `operation`

Allowed scopes are the framework standard scopes: `shared`, `organization`, `team`, `local`, or `session`.

Allowed operations are:

- `add`
- `extend`
- `replace`
- `suppress`

## Required Sections

### Purpose

State why the overlay exists and what resolved behavior it is intended to change.

### Target

Declare:

- `target_artifact_type`
- `target_artifact_id` when the operation targets an existing artifact
- narrower target selectors when needed, such as `target_role_id` or a field path

An overlay must not rely on its filename or storage location as its target identity.

### Change

Declare the operation-specific fields and the intended result.

### Boundary Rules

State where the overlay applies, what it does not modify, and which required coverage or authority must remain unchanged.

### Validation Hints

State the invariants that prove the overlay is safe to resolve.

## Operation Contracts

### `add`

Use when adding a new artifact to a resolved view.

Required concepts:

- added artifact type
- added artifact ID
- activation scope
- collision behavior if the ID already exists

An `add` must fail rather than silently replace an existing artifact with the same type and ID.

### `extend`

Use when modifying an existing artifact while preserving its identity relationship to a base artifact.

Required concepts:

- base artifact type and ID
- changed fields or additions
- compatibility expectations
- cycle prevention

An `extend` must not change the base artifact globally.

### `replace`

Use when substituting one artifact or responsibility lane in a selected resolved view.

Required concepts:

- target artifact type and ID
- replacement artifact type and ID
- compatibility or preserved-coverage statement
- effective precedence

For role replacement, the replacement must preserve the responsibility coverage required by the target team, including mandatory debate participation and blocking coverage where applicable.

### `suppress`

Use when removing an artifact from a selected resolved view without deleting it from its publication boundary.

Required concepts:

- suppressed artifact type and ID
- reason
- coverage impact
- explicit allowance for the suppression under the selected validation rules

A `suppress` must fail or be reported as degraded when it removes required coverage without an explicit valid replacement or narrowed team model.

When suppressing a role, remove it from optional references such as `optional_roles`, `stage_owners`, and participants in non-mandatory debates. Keep required references available to validation, including `coverage_requirements`, participants in `mandatory_debates`, `blocking_lanes`, and `documentation_ownership`. If suppression leaves a required obligation unsatisfied, resolution must fail with diagnostics naming the field path and suppressed role ID.

## Precedence And Conflicts

Overlay resolution must be deterministic.

The default scope precedence from broadest to narrowest is:

1. `shared`
2. `organization`
3. `team`
4. `local`
5. `session`

Narrower scope may override broader scope only when the operation is legal and explicitly targeted.

Within the same scope:

- explicit `priority` orders overlays from lower to higher; higher priority wins after lower-priority changes are applied
- otherwise, overlays with conflicting operations on the same target must fail as ambiguous
- two overlays may not silently write different values to the same field

An implementation may define a different precedence policy only if it declares that policy in the validation rules and preserves deterministic resolution.

## Resolution Output

Resolving an overlay must produce:

- the selected base artifact identity
- the ordered overlays considered
- the winning operations and their precedence
- the effective artifact or responsibility set
- suppressed or replaced artifacts
- conflicts, degraded conditions, or unresolved references
- provenance sufficient to explain why each effective value won

The final runtime mapping must receive the resolved view, not an unresolved collection of competing overlays.

## Validation Rules

At minimum, validate that:

- the operation is recognized
- target and replacement references resolve
- target and replacement artifact types are compatible
- scope is allowed for the target artifact
- extension and inheritance cycles are absent
- conflicting overlays have deterministic precedence or fail
- required team role, debate, blocking, documentation, and governance coverage remains valid
- role provenance identifies the specific overlay that introduced each role, including roles added by sequential `extend` overlays
- a runtime mapping references the effective artifact identity after overlay resolution
