# Resolved View: sample-product-engineer-ii

## Resolution Status

- `status`: `illustrative; machine execution not verified`
- `validation_profile`: `organization-shared`
- `resolution_note`: This Markdown view describes the expected composition; it is not output from an automated resolver.

## Selected Context

- `organization_catalog_id`: `sample-organization-technology-catalog`
- `team_instance_id`: `sample-product-workflows-team`
- `team_blueprint_id`: `information-technology-core-team`
- `domain_pack_ids`: `sample-product`
- `specialization_pack_ids`: `sample-product-workflows-specialization`
- `overlay_ids`: `sample-product-engineer-ii`
- `runtime_adapter_id`: `codex-desktop-agent-runtime`
- `runtime_profile_id`: `codex-desktop-sample-product-engineer-ii`

## Effective Roles

The seven responsibility lanes come from `information-technology-core-team`. The `engineer` lane is replaced by `engineer-ii` through `sample-product-engineer-ii`; all other lanes retain their blueprint roles.

## Effective Team Behavior

- team workflow and decisions: inherited from the shared blueprint
- implementation lane: `engineer-ii`
- product context: load `sample-product`, then `sample-product-workflows-specialization`
- cross-team integration changes: agree contract ownership and hand off to `sample-product-integrations-team`
- release, product, architecture, and quality decisions remain with their designated roles

## Knowledge Loading Order

1. `sample-organization-technology-catalog`
2. `sample-product-workflows-team`
3. `information-technology-core-team`
4. `sample-product`
5. `sample-product-workflows-specialization`
6. request-specific repository and work-item context

## Overlay Resolution

- overlay: `sample-product-engineer-ii`, operation `replace`, priority `100`
- target: `team-instance:sample-product-workflows-team`, role `engineer`
- replacement: `role:engineer-ii`
- result: the workflow team uses Engineer II; the shared blueprint and Integrations Team remain unchanged

## Runtime Resolution

- adapter: `codex-desktop-agent-runtime`
- binding: `codex-desktop-sample-product-engineer-ii`
- implementation construct: Codex implementation lane with Engineer II context
- fallback: use the base Engineer mapping if the runtime cannot preserve distinct role identity
- permissions: bounded implementation authority; no additional release, production, architecture, product, or quality-signoff authority

## Validation Notes

Artifact references and overlay semantics are documented for illustration. Automated parsing, machine resolution, and live runtime behavior are not verified by this view.
