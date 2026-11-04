# Capability Knowledge: sample-product-workflows-specialization

## Identity

- `artifact_type`: `specialization-pack`
- `id`: `sample-product-workflows-specialization`
- `name`: `Example Product Workflows Team Specialization`
- `version`: `1.0.0`
- `scope`: `team`
- `owner_team_instance_id`: `sample-product-workflows-team`
- `parent_domain_pack_id`: `sample-product`

## Purpose

Give every role in the Product Workflows Team durable context about customer-facing workflow ownership without changing shared role or team semantics.

## Owned Knowledge Surface

- workflow steps, state transitions, and user-visible outcomes
- application modules and APIs supporting those workflows
- accessibility, validation, and workflow-specific acceptance behavior
- workflow automation, support notes, and product documentation

## Trusted Sources

- repository-local instructions in owned repositories
- source code and tests for owned workflow surfaces
- product and architecture references at `https://docs.example.org/sample-product/workflows`
- current work-item requirements and acceptance criteria
- environment evidence when required to answer a behavior question

## Loading Guidance

1. load the parent `sample-product` domain knowledge
2. identify the target workflow and owning repository or module
3. read local instructions and the relevant product references
4. inspect existing workflow behavior and tests
5. add request-specific requirements
6. use environment inspection only when it resolves material uncertainty

## Role Guidance

- `product-owner`: frame workflow changes through customer and administrator outcomes
- `tech-owner`: preserve workflow contracts and identify dependencies early
- `software-architect`: assess boundaries, state ownership, and migration impact
- `quality-engineer`: choose regression scenarios and evidence for workflow behavior
- `engineer`: trace reported issues through user-visible workflow steps and state transitions; add regression coverage for affected behavior and check accessibility when interactions change; consult `tech-owner` before changing a shared contract
- `program-manager`: coordinate dependencies and unresolved cross-team commitments
- `release-manager`: confirm sequencing and rollback evidence for workflow changes

## Persistence Rules

- update durable ownership, source priority, and workflow conventions here
- keep request-specific decisions with the work item unless they become recurring guidance
- use stable references for claims that materially affect implementation

## Validation Hints

- remain narrower than the parent product domain
- do not redefine core roles
- keep integration-owned transport and partner mapping details in the Integrations specialization
