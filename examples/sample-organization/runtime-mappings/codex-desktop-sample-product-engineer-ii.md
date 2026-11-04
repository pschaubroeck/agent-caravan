# Runtime Mapping: codex-desktop-sample-product-engineer-ii

## Purpose

- `id`: `codex-desktop-sample-product-engineer-ii`
- `name`: `Codex Desktop Example Product Engineer II Binding`
- `version`: `1.0.0`
- `scope`: `organization`
- `target_adapter_id`: `codex-desktop-agent-runtime`
- `extends`: `codex-desktop-sample-product-team`
- `mission`: Bind the Engineer II overlay to implementation work for the Product Workflows Team.
- `summary`: Demonstrate a scoped role replacement without changing the shared blueprint or another team.

## Target Scope

- `applies_to_artifact_ids`: `sample-product-workflows-team`, `sample-product-engineer-ii`, `engineer-ii`
- `applies_to_artifact_types`: `team-instance`, `overlay`, `role`
- `binding_scope_type`: `resolved-instance-binding`

## Runtime Mapping

- realize `engineer-ii` as the implementation lane for the selected team
- preserve the team's other responsibility lanes and mandatory decision participants
- keep the overlay bounded to `sample-product-workflows-team`

## Capability Contract

- `required_capabilities`: `dynamic_context_loading`, `local_command_execution`, `code_editing`, `tool_approval_gates`
- `preferred_capabilities`: `execution_trace`, `parallel_lane_execution`
- `forbidden_capabilities`: none

## Safety Notes

Engineer II receives implementation responsibilities only. This binding grants no release, production, architecture, product, or quality-signoff authority.
