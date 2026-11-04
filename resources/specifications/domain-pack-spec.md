# Domain Knowledge Specification

## Purpose

This document defines the reusable specification for a domain knowledge.

A domain knowledge is a scoped knowledge attachment that can be combined with a stable role model, such as the Information Technology Core Team operating model, to produce domain-specialized agents or execution flows.

The domain knowledge is not the domain knowledge itself. It is the curated control layer that tells the system:

- what the domain is
- where the domain's trusted knowledge lives
- which sources are more authoritative than others
- how to load context for different kinds of work
- how the base roles should adapt inside the domain

## Design Goals

- keep the base role model reusable across teams and organizations
- keep domain knowledge modular and replaceable
- separate canonical sources from volatile sources
- prefer live source loading over large local knowledge dumps
- make specialization composable as `role + domain`
- support both whole-repo and partial-repo domains
- allow domain knowledge to grow incrementally without forcing a full knowledge-base build

## What A Domain Knowledge Is

A domain knowledge is a curated domain index and execution guide.

It should describe:

- domain identity
- domain scope
- relevant code and documentation surfaces
- source trust order
- context loading order
- common workflows
- role-specific domain behavior
- known risks and terminology
- future enrichment points

## What A Domain Knowledge Is Not

A domain knowledge is not:

- a dump of all repo documentation
- a mirror of Confluence or Jira
- a full architecture document
- a persistent cache of every source artifact
- a replacement for live source inspection

If the pack starts accumulating large amounts of copied source material, it is drifting out of scope.

## Reuse Model

The reusable framework should be split into two layers.

### Shared Layer

Reusable across teams:

- team operating model
- role definitions
- debate-flow model
- blocking-authority model
- domain-pack specification
- role + domain composition pattern

### Local Layer

Specific to an organization, product area, or platform:

- actual domain knowledge
- repo paths and GitLab groups
- Confluence spaces and architecture pages
- Jira projects, epics, labels, and issue conventions
- environment URLs and operational tooling
- organization-specific approval or governance rules

## Composition Model

The recommended specialization pattern is:

- base role behavior from the team operating model
- domain behavior from the domain knowledge

Examples:

- `sample-product-engineer`
- `sample-product-tech-owner`
- `enrollment-quality-engineer`
- `servicenow-integration-software-architect`

This keeps role semantics stable while allowing the knowledge surface to vary.

## Required Sections

Every domain knowledge should include the following sections.

### 1. Purpose

Explain what the pack is for and which broader operating model it extends.

### 2. Domain Definition

Minimum fields:

- `domain name`
- `domain type`
- `scope`
- `primary workspace root` when applicable

Optional fields:

- `canonical gitlab group`
- `primary jira project`
- `primary confluence space`
- `runtime environments`

### 3. Domain Intent

Explain what the domain functionally is.

This should answer questions such as:

- Is it a product area, platform, service family, integration surface, or workflow?
- Is it one repository, a GitLab group, a Confluence space, or a slice of a monorepo?
- Why does it deserve domain-specific treatment?

### 4. Repository Topology

Describe the relevant repo structure.

This can be:

- one repo with named directories
- several repos in one GitLab group
- a mixed repo + service + infra ecosystem

This section should help an agent know where code likely lives before searching blindly.

### 5. Repo-Local Instruction Sources

Identify repo-local instruction files or equivalent sources such as:

- `AGENTS.md`
- internal guidance files
- repo-local operating notes

These should be called out explicitly because they often change how tools or environments should be handled.

### 6. Confluence Knowledge Hubs

Identify the Confluence roots that matter most.

Examples:

- architecture inventory pages
- domain-space overviews
- operational runbooks
- reference documentation trees

When possible, distinguish:

- architecture anchors
- operational/how-to anchors
- reference/detail anchors

### 7. Canonical Source Loading Order

Define the recommended order for loading context during execution.

This should answer:

- what to read first
- what to read only when needed
- what lower-trust sources should come last

### 8. Source Priority

Define source trust tiers.

Typical pattern:

- Tier 1: canonical and durable
- Tier 2: operational and situational
- Tier 3: volatile and weakly governed

This helps the system avoid over-weighting chat fragments or stale notes when stronger sources exist.

### 9. High-Signal Source Anchors

List the most important concrete starting points.

Examples:

- top-level recipes folder
- architecture page
- deployment guide
- testing guide
- specific repo README

This section should be selective. It is not meant to list everything.

### 10. Linked Context Anchors

List additional useful source systems or pages that complement the primary hubs.

Examples:

- linked Confluence pages
- linked Jira epics
- wiki pages
- documentation repos

### 11. Domain Workflows

Define common work patterns inside the domain.

Examples:

- infrastructure work
- backend work
- frontend work
- database work
- test/validation work
- reporting/analytics work

Each workflow should tell the agent where to start and what to check next.

### 12. Environment And Tooling Conventions

Capture important domain-specific operational rules such as:

- account/profile naming
- environment naming
- standard helper tools
- deployment tools
- inspection-first conventions

### 13. Domain Risks And Failure Modes

Call out the mistakes that domain specialists are most likely to make.

Examples:

- cross-repo drift
- hidden environment assumptions
- broken deployment sequencing
- stale docs
- security or approval traps
- test blind spots

### 14. Role-Specific Domain Guidance

Describe how each base role behaves differently in this domain.

At minimum, cover:

- `program-manager`
- `product-owner`
- `tech-owner`
- `engineer`
- `quality-engineer`
- `software-architect`
- `release-manager`

This section should adapt the role to the domain without redefining the role globally.

### 15. Suggested Activation Pattern

Define when to use the pack.

Examples:

- any repo under a given GitLab group
- work involving a specific Confluence space
- work touching certain subsystems
- any request labeled for a product area

### 16. Known Gaps

Be explicit about what the pack does not yet know well.

This prevents false confidence and creates a place to track future enrichment.

### 17. Summary

End with a short description of what the pack now enables.

## Optional Sections

Depending on the domain, a pack may also include:

- domain glossary
- major integrations
- data ownership boundaries
- quality or compliance hotspots
- stakeholder map
- refresh triggers
- live-site inspection guidance
- segmentation rules for partial-repo domains

## Domain Types

The format should support several domain shapes.

### GitLab Group Domain

Use when a domain spans multiple related repositories in one namespace.

Example:

- `sample-product`

### Single-Repository Segment Domain

Use when the domain is a bounded slice of one larger repo.

Example:

- a subsystem inside `Sample Product`

### Product Or Capability Domain

Use when the domain is defined more by feature/capability than repo boundaries.

Examples:

- enrollment
- eligibility
- billing
- document-delivery

### Integration Domain

Use when the domain is defined by system boundaries and contracts.

Examples:

- ServiceNow integration
- data-lake export flows
- partner APIs

## Loading Rules

The pack should be read first, then used to decide what live sources to inspect.

Recommended behavior:

1. Read the domain knowledge
2. Determine work type
3. Load the highest-priority sources for that work type
4. Load deeper or lower-tier sources only as needed
5. Keep context bounded to the task rather than ingesting the whole domain

## Maintenance Rules

Domain knowledge should be:

- concise enough to stay readable
- specific enough to be operationally useful
- updated when key source locations or workflows change
- enriched gradually from real work, not speculative documentation efforts

Do not expand a pack just because more information exists.
Expand it when the new information improves routing, source trust, or execution quality.

## Authoring Guidance

When writing a new domain knowledge:

1. Start from the smallest useful domain definition.
2. Prefer concrete source anchors over broad generalization.
3. Name authoritative sources explicitly.
4. Separate architecture sources from operational sources when both exist.
5. Distinguish observed facts from inferred guidance when needed.
6. Avoid copying large blocks of source content into the pack.
7. Leave clear known gaps instead of pretending the pack is complete.

## Example Relationship

The first concrete example of this format is:

- [sample-product-domain-pack.md](../../examples/sample-organization/domain-knowledge/sample-product.md)

That file is an instance of this specification, not the specification itself.

## Summary

The domain-pack specification provides a reusable way to attach scoped, trusted, domain-specific knowledge to a stable AI team operating model.

It enables specialization without forcing every team to share the same repos, docs, naming, or runtime environment.
