# Runtime Mapping: codex-desktop-sample-product-team

## Purpose

- `id`: `codex-desktop-sample-product-team`
- `name`: `Codex Desktop Example Product Team Binding`
- `version`: `1.0.0`
- `scope`: `organization`
- `target_adapter_id`: `codex-desktop-agent-runtime`
- `extends`: `codex-desktop-information-technology-core-team`
- `mission`: Bind the shared caravan template to the Example Product Workflows Team and its durable product context.
- `summary`: Demonstrate composition across catalog, team, domain, and specialization layers.

## Target Scope

- `applies_to_artifact_ids`: `sample-organization-technology-catalog`, `sample-product-workflows-team`, `information-technology-core-team`, `sample-product`, `sample-product-workflows-specialization`
- `applies_to_artifact_types`: `organization-catalog`, `team-instance`, `team-blueprint`, `domain-pack`, `specialization-pack`
- `binding_scope_type`: `resolved-instance-binding`

## Resolution Context

- `organization_catalog_id`: `sample-organization-technology-catalog`
- `team_instance_id`: `sample-product-workflows-team`
- `team_blueprint_id`: `information-technology-core-team`
- `domain_pack_ids`: `sample-product`
- `specialization_pack_ids`: `sample-product-workflows-specialization`

## Runtime Mapping

- catalog: publication and artifact-discovery boundary
- caravan: durable ownership and routing context
- blueprint: coordinating task with logical responsibility lanes
- domain and specialization: broad product context followed by team-owned guidance
- roles: realized through role instructions, routing, and stage ownership

## Capability Contract

- `required_capabilities`: `structured_output_contracts`, `dynamic_context_loading`, `local_command_execution`, `code_editing`, `role_handoff`, `tool_approval_gates`
- `preferred_capabilities`: `parallel_lane_execution`, `durable_memory`, `execution_trace`, `document_attachment_support`, `tool_permission_scoping`
- `optional_capabilities`: `browser_interaction`, `api_call_execution`, `background_execution`
- `forbidden_capabilities`: none

## Fallback And Safety

- if parallel lanes are unavailable, run role discussions serially and retain decisions
- if durable memory is unavailable, refer to the specialization and record durable decisions there
- surface missing context that could change ownership or contracts
- remote mutations and deployment remain separately gated; team knowledge does not grant permissions
