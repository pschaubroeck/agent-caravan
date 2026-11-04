# Normalized Artifact Bundle Specification

## Purpose

This document defines the prototype machine-readable interchange contract used by the framework resolver.

The bundle is a transport shape, not a storage requirement. A catalog adapter may construct the same logical bundle from files, GitLab, GitHub, Confluence, a database, an API, or another source.

Storage adapters expose one logical operation: `load() -> bundle`. The resolver must not depend on how that operation retrieves or assembles the artifacts.

## Bundle Shape

```json
{
  "context": {
    "organization_catalog_id": "...",
    "team_instance_id": "...",
    "runtime_adapter_id": "...",
    "runtime_profile_id": "...",
    "execution_profile_id": "...",
    "validation_profile_id": "organization-shared"
  },
  "artifacts": []
}
```

Required bundle fields:

- `context`
- `artifacts`

Required context fields:

- `organization_catalog_id`
- `team_instance_id`
- `runtime_profile_id`

`runtime_adapter_id` may be omitted when the selected caravan declares one runtime default. `validation_profile_id` defaults to `organization-shared`.

## Common Artifact Fields

Every artifact must include:

- `artifact_type`
- `id`
- `version`
- `scope`

IDs are unique within an artifact type. References should use both artifact type and ID when the same ID may exist in multiple namespaces.

Supported prototype artifact types:

- `organization-catalog`
- `role`
- `team-blueprint`
- `team-instance`
- `domain-pack`
- `specialization-pack`
- `overlay`
- `runtime-adapter`
- `runtime-profile`
- `execution-profile`
- `policy`
- `validation-profile`

## Required Relationships

- organization catalogs publish selected artifact IDs under `published_artifacts`
- caravans reference `team_blueprint_id`
- caravans may reference `role_overlays`, `domain_packs`, `specialization_packs`, and `runtime_defaults`
- role variants may reference a base role with `extends`
- capability knowledge may reference `owner_team_instance_id` and `parent_domain_pack_id`
- runtime mappings reference `target_adapter_id`
- workflows reference a caravan template or caravan and may reference a runtime mapping

## Caravan Template Fields

The resolver consumes these fields when present:

- `core_roles`
- `mandatory_debates`
- `debate_participants`
- `blocking_lanes`
- `documentation_ownership`
- `coverage_requirements`

Additional fields are preserved in the resolved effective team.

## Overlay Fields

Every overlay must follow [overlay-spec.md](overlay-spec.md).

The prototype currently applies overlays targeting a selected `team-instance`:

- `replace`: `target_role_id`, `replacement_artifact_type`, `replacement_role_id`
- `add`: `added_artifact_type`, `added_artifact_id`, `target_collection`
- `extend`: `changes`
- `suppress`: `suppressed_artifact_type`, `suppressed_artifact_id` or `target_role_id`

All overlays may include `priority`. Scope precedence is `shared -> organization -> team -> local -> session`; higher priority wins within the same scope after lower-priority changes are applied.

## Runtime Fields

Runtime integrations expose capability statuses under `capabilities`.

Allowed statuses are:

- `native`
- `adapted`
- `externalized`

Runtime bindings declare at least `target_adapter_id` and may declare:

- `required_capabilities`
- `preferred_capabilities`
- `optional_capabilities`
- `forbidden_capabilities`
- optional execution settings for model/profile, instructions, tools, workspace, output schema, guardrails, persistence, and runtime limits

Required capabilities that are adapted or externalized produce a degraded result. Unsupported required capabilities fail resolution.

## Validation Rules

The prototype provides these default profiles:

- `local-experimental`: degraded runtime capabilities are allowed
- `team-shared`: degraded runtime capabilities are allowed but reported
- `organization-shared`: degraded runtime capabilities fail resolution
- `runtime-production`: degraded runtime capabilities fail resolution

A `validation-profile` artifact may override the default policy with a `policy` object. The selected profile is recorded in the resolved output.

## Resolved Output

The resolver emits JSON containing:

- resolution status and validation rules
- selected context
- effective team and roles
- applied overlays and role replacements
- attached domains and specializations
- runtime compatibility result
- provenance and overlay order

The output is an explainable resolved view, not a runtime execution command or authorization grant.

Domain and specialization artifacts may provide structured portable knowledge
fields: `purpose`, `domain_intent`, `knowledge_surface`, `trusted_sources`,
`loading_guidance`, and a `role_guidance` map from role IDs to guidance. The
resolver preserves selected artifacts in the resolved result so execution-plan
builders can project these fields without depending on a particular storage
provider. Omitted fields remain omitted from the portable plan.
