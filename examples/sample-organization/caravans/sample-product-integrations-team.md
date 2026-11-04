# Caravan: sample-product-integrations-team

## Identity

- `artifact_type`: `team-instance`
- `id`: `sample-product-integrations-team`
- `name`: `Example Product Integrations Team`
- `version`: `1.0.0`
- `scope`: `organization`
- `organization_catalog_id`: `sample-organization-technology-catalog`
- `team_blueprint_id`: `information-technology-core-team`

## Purpose

Own external partner contracts, data mappings, and reliable exchange of information with Example Product.

## Ownership Boundary

- `product_domain`: `sample-product`
- `owned_surfaces`:
  - partner API and file exchange contracts
  - data mappings, validation, retries, and integration monitoring
  - integration-specific tests, certification scenarios, and documentation
- `adjacent_surfaces`:
  - customer workflow behavior depending on partner data
  - shared platform services and release controls owned elsewhere
- `out_of_scope`:
  - customer-facing workflow design and application behavior
  - organization-wide release policy

## Composition

- `base_team_blueprint`: `information-technology-core-team`
- `role_overlays`: none
- `domain_packs`: `sample-product`
- `specialization_packs`: `sample-product-integrations-specialization`
- `runtime_defaults`: `codex-desktop-agent-runtime`

## Operating Rules

- retain the base blueprint's role responsibilities and decision workflow
- own partner contracts and integration implementation within the listed surfaces
- agree explicit contracts and handoffs when partner data changes alter customer workflows
- keep durable integration knowledge in the specialization, not in individual work items

## Validation Hints

- the selected specialization resolves to this team
- integration knowledge remains distinct from workflow-owned knowledge
- cross-team changes identify contract owner, validation evidence, and handoff
