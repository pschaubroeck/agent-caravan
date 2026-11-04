# Configuration Override: sample-product-engineer-ii

## Identity

- `artifact_type`: `overlay`
- `id`: `sample-product-engineer-ii`
- `name`: `Example Product Engineer II Overlay`
- `version`: `1.0.0`
- `scope`: `team`
- `operation`: `replace`
- `priority`: `100`

## Target

- `target_artifact_type`: `team-instance`
- `target_artifact_id`: `sample-product-workflows-team`
- `target_role_id`: `engineer`

## Change

- `replacement_role_id`: `engineer-ii`
- `replacement_artifact_type`: `role`
- `reason`: Use a more experienced implementation lane for the Product Workflows Team while preserving the shared blueprint and other role responsibilities.
- `preserved_coverage`: implementation ownership, automated tests, code-adjacent documentation, blocker reporting, and technical debate participation
- `compatibility_statement`: `engineer-ii` extends `engineer` and preserves implementation ownership, review participation, and blocker authority.

## Boundary Rules

- applies only to `sample-product-workflows-team`
- does not modify `information-technology-core-team` globally
- does not replace product, technical, architecture, quality, or release responsibilities
- does not grant release or sign-off authority to Engineer II

## Validation Hints

- the target team resolves the replacement role
- required implementation coverage and debate participation remain valid
- the Integrations Team does not inherit this overlay unless it selects it
