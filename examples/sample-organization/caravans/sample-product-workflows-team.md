# Caravan: sample-product-workflows-team

## Identity

- `artifact_type`: `team-instance`
- `id`: `sample-product-workflows-team`
- `name`: `Example Product Workflows Team`
- `version`: `1.0.0`
- `scope`: `organization`
- `organization_catalog_id`: `sample-organization-technology-catalog`
- `team_blueprint_id`: `information-technology-core-team`

## Purpose

Own customer-facing product workflows and their behavior across the Example Product experience.

## Ownership Boundary

- `product_domain`: `sample-product`
- `owned_surfaces`:
  - customer and administrator workflow behavior
  - workflow state transitions and user-facing application modules
  - workflow-specific tests, acceptance scenarios, and documentation
- `adjacent_surfaces`:
  - partner integrations when workflow behavior depends on exchanged data
  - shared platform services and release controls owned elsewhere
- `out_of_scope`:
  - partner-specific transport, mapping, and retry implementation
  - organization-wide release policy

## Composition

- `base_team_blueprint`: `information-technology-core-team`
- `role_overlays`: `sample-product-engineer-ii`
- `domain_packs`: `sample-product`
- `specialization_packs`: `sample-product-workflows-specialization`
- `runtime_defaults`: `codex-desktop-agent-runtime`

## Operating Rules

- retain the base blueprint's role responsibilities and decision workflow
- own decisions within the listed customer workflow surfaces
- agree explicit contracts and handoffs when a change crosses into integration ownership
- keep durable workflow knowledge in the specialization, not in individual work items

## Validation Hints

- all seven responsibility lanes from the selected blueprint remain available
- the selected specialization resolves to this team
- cross-team work records the workflow-to-integration contract
