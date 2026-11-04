# Capability Knowledge: sample-product-integrations-specialization

## Identity

- `artifact_type`: `specialization-pack`
- `id`: `sample-product-integrations-specialization`
- `name`: `Example Product Integrations Team Specialization`
- `version`: `1.0.0`
- `scope`: `team`
- `owner_team_instance_id`: `sample-product-integrations-team`
- `parent_domain_pack_id`: `sample-product`

## Purpose

Give every role in the Product Integrations Team durable context about partner contracts and reliable data exchange without changing shared role or team semantics.

## Owned Knowledge Surface

- partner interface contracts, schemas, and version compatibility
- field mappings, validation, retries, and idempotency behavior
- integration monitoring, failure handling, and reconciliation
- partner-specific tests, certification evidence, and support documentation

## Trusted Sources

- repository-local instructions in owned repositories
- source code, schemas, and tests for owned integrations
- integration contract references at `https://docs.example.org/sample-product/integrations`
- current work-item requirements and acceptance criteria
- environment evidence when required to establish integration behavior

## Loading Guidance

1. load the parent `sample-product` domain knowledge
2. identify the partner contract and owning integration
3. read local instructions, schemas, and contract references
4. inspect existing mapping, retry, and monitoring behavior
5. add request-specific requirements
6. use environment inspection only when it resolves material uncertainty

## Role Guidance

- `product-owner`: connect partner capabilities and limits to product outcomes
- `tech-owner`: preserve interface contracts and identify consumer impacts early
- `software-architect`: assess integration boundaries, coupling, and version strategy
- `quality-engineer`: verify schema, failure, retry, and reconciliation cases
- `engineer`: follow established integration patterns and preserve idempotent behavior
- `program-manager`: coordinate partner dependencies and certification commitments
- `release-manager`: confirm partner-aware rollout sequencing and rollback evidence

## Persistence Rules

- update durable contracts, source priority, and recurring integration conventions here
- keep request-specific decisions with the work item unless they become durable guidance
- reference stable contract sources for material implementation decisions

## Validation Hints

- remain narrower than the parent product domain
- do not redefine core roles
- keep customer-facing workflow design in the Workflows specialization
