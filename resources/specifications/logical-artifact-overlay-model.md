# Logical Artifact And Overlay Resolution Model

## Purpose

This document defines the storage-agnostic logical model for the AI team framework.

It describes:

- which artifact types exist
- how they relate to each other
- how shared and local variants can coexist
- how overrides are resolved
- what a runtime integration should receive as final input

This model intentionally does not require:

- Git
- a filesystem
- a database
- a specific repository host
- Codex
- any specific AI runtime or vendor

It defines the framework's logical contract, not its physical implementation.

## Design Goals

- be storage-agnostic
- be VCS-agnostic
- be runtime-agnostic
- support organization-shared, team-shared, and local artifacts simultaneously
- allow extension, replacement, and narrowing of roles, teams, and domains
- resolve overlays deterministically
- validate the resolved configuration independently of where it came from
- support future multi-team and multi-runtime organizations

## Core Model

The framework is composed from a small set of logical artifact types.

### Primary Artifact Types

- `role`
- `team-blueprint`
- `domain-pack`
- `runtime-adapter`
- `runtime-profile`

### Supporting Artifact Types

- `organization-catalog`
- `team-instance`
- `specialization-pack`
- `overlay`
- `validation-profile`

Not every implementation must expose each artifact as a separate stored unit, but the logical model must still support them.

## Artifact Definitions

### `role`

A `role` defines a reusable responsibility pattern.

It should express concepts such as:

- mission
- ownership boundaries
- required inputs
- outputs
- blocking authority
- debate participation
- handoff behavior
- approval limits

A `role` is runtime-neutral.
It must not assume a specific prompt file, tool, model, or vendor.

### `team-blueprint`

A `team-blueprint` defines a reusable team shape.

It should express concepts such as:

- included roles
- default stage flow
- mandatory debates
- optional debates
- escalation patterns
- blocking model
- documentation expectations

A `team-blueprint` may reference roles directly or reference role variants.

### `domain-pack`

A `domain-pack` defines a reusable scoped-knowledge attachment.

It should express concepts such as:

- domain identity
- scope
- authoritative sources
- loading order
- workflow map
- environment/tooling conventions
- role-specific domain guidance

A `domain-pack` modifies how work is performed in a domain without redefining the core role semantics globally.

### `runtime-adapter`

A `runtime-adapter` defines how a specific implementation environment exposes capabilities.

Examples:

- Codex
- Claude Code
- OpenAI Agents SDK
- Gemini CLI
- Copilot Studio
- LangGraph
- Droid

The adapter should describe the runtime's capabilities and constraints, not the team's business meaning.

### `runtime-profile`

A `runtime-profile` maps framework artifacts to a specific runtime integration.

Examples:

- which framework role maps to which runtime construct
- which capabilities are required
- which tools, profiles, or prompts are attached
- what permission envelope applies
- which handoffs or delegation mechanisms are available

This is where implementors can bind roles to agents, skills, profiles, prompts, tools, flows, or other runtime-specific constructs.

### `organization-catalog`

An `organization-catalog` is a curated collection of reusable artifacts available within some sharing boundary.

Examples:

- company-wide role catalog
- team-wide domain-pack catalog
- shared runtime-profile catalog

It is a logical publication boundary, not a required storage primitive.

The framework must support one to many `organization-catalog` instances rather than assuming one global organization root.

### `team-instance`

A `team-instance` is a persistent application of a `team-blueprint` within a specific operating boundary.

It should express concepts such as:

- owning organization or catalog context
- selected caravan template
- attached role variants or overlays
- attached domain knowledge
- owned code or service boundaries
- runtime selection defaults

A `team-instance` allows many teams to share one team shape without becoming the same team logically.

### `specialization-pack`

A `specialization-pack` is a persistent scoped knowledge layer narrower than a general domain knowledge.

It should express concepts such as:

- team-specific owned surfaces inside a broader domain
- subdomain-specific trusted sources
- long-lived implementation conventions
- team-specific workflow or escalation knowledge
- durable role guidance for one owned slice of a system

This is the preferred way to model durable team knowledge differences inside a larger shared product such as Sample Product.

### `overlay`

An `overlay` modifies existing artifacts or defines additional artifacts within a narrower scope.

The required overlay fields and conflict rules are defined in [overlay-spec.md](overlay-spec.md).

An overlay may:

- add a new artifact
- extend an existing artifact
- replace an existing artifact
- suppress an existing artifact from a given resolved view

### `validation-profile`

A `validation-profile` defines which rules must pass for a resolved framework instance.

Examples:

- strict shared-catalog publishing rules
- local experimental rules
- production runtime-profile rules

## Identity Model

Every logical artifact should have a stable identity.

Minimum identity concepts:

- `artifact_type`
- `id`
- `version` or equivalent revision marker
- `scope`

Recommended identity behavior:

- IDs remain stable across storage implementations
- IDs are unique within artifact type
- versions are explicit when artifacts are published/shared
- local experiments may use looser revision semantics if still uniquely resolvable

## Scope Model

The framework should support multiple scopes simultaneously.

### Standard Scopes

- `shared`
  - reusable across an organization or community

- `organization`
  - published for one company or equivalent boundary

- `team`
  - published for one team or subgroup

- `local`
  - private or user-specific

- `session`
  - temporary, ad hoc, or ephemeral

These names are logical categories, not mandatory storage partitions.

## Overlay Operations

The framework should support four basic overlay operations.

### `add`

Create a new artifact in a narrower or peer scope.

Example:

- add `engineer-ii`

### `extend`

Inherit an existing artifact and modify selected fields while preserving the base identity relationship.

Example:

- `engineer-ii` extends `engineer`

### `replace`

Substitute one artifact with another in a resolved view.

Example:

- replace `software-architect` with a differently scoped local architecture role

### `suppress`

Remove an otherwise available artifact from a resolved view without deleting it globally.

Example:

- suppress `release-manager` in a minimal local team

Overlay application must preserve deterministic precedence and must produce an explainable resolved view. An overlay cannot silently win a conflict merely because it was discovered later.

## Resolution Model

The framework should resolve artifacts into a final view before execution.

### Resolution Inputs

A resolved view may depend on:

- one or more base catalogs
- selected organization context
- one or more overlays
- selected caravan
- selected caravan template
- selected domains
- selected capability knowledge
- selected runtime integration
- selected runtime mappings
- selected validation rules

### Resolution Output

The output should be a fully resolved framework instance.

At minimum it should contain:

- resolved roles
- resolved team structure
- resolved domain attachments
- resolved specialization attachments
- resolved runtime mappings
- resolved validation expectations

This resolved instance is what runtimes or tooling should consume.

## Default Precedence Model

Unless an implementation explicitly defines otherwise, the recommended precedence is:

1. `shared`
2. `organization`
3. `team`
4. `local`
5. `session`

Narrower scope wins when a conflict is valid and allowed.

## Conflict Rules

The framework should distinguish between:

- valid override
- ambiguous override
- invalid conflict

### Valid Override

Occurs when the model explicitly allows a narrower artifact to modify or replace a broader one.

### Ambiguous Override

Occurs when two applicable artifacts compete and the framework cannot determine precedence or intent safely.

This should fail resolution.

### Invalid Conflict

Occurs when an overlay violates structural rules.

Examples:

- circular inheritance
- replacing an artifact with incompatible type
- suppressing a required artifact without replacing its responsibility
- contradictory required role references

This should fail validation.

## Reference Model

Artifacts should reference each other by logical identity, not by storage path.

Examples:

- a caravan template references roles by role ID
- a runtime mapping references role IDs and adapter IDs
- a domain knowledge references role IDs in role-specific guidance

Paths, URLs, or storage locators may appear as payload data inside an artifact, but artifact relationships themselves should not depend on physical location.

## Composition Model

The framework should resolve behavior through composition.

### Recommended Composition Order

1. Resolve base roles
2. Apply role overlays
3. Resolve caravan template
4. Resolve caravan
5. Apply team overlays
6. Attach one or more domain knowledge
7. Attach one or more capability knowledge
8. Apply domain and specialization overlays
9. Resolve runtime integration
10. Apply runtime mappings
11. Run validation rules

This order keeps business semantics ahead of runtime implementation details.

## Domain Attachment Model

Domains should be attachable without redefining the underlying team.

Recommended pattern:

- team behavior comes from `team-blueprint + resolved roles`
- specialized behavior comes from `domain-pack`
- persistent owned-slice behavior comes from `specialization-pack`
- execution implementation comes from `runtime-profile`

This allows the same role to behave differently in `sample-product` versus `Sample Product` without becoming a different core role.

## Multi-Organization And Multi-Team Model

The framework must support many organizations and many teams simultaneously.

Recommended interpretation:

- `organization-catalog` defines a publication boundary, not a singleton root
- `team-blueprint` defines a reusable shape, not one concrete team
- `team-instance` defines one durable operating team using that shape
- `domain-pack` defines broad domain knowledge
- `specialization-pack` defines persistent team-specific knowledge inside that domain

This allows patterns such as:

- multiple organizations reusing one public base role catalog
- one organization publishing many caravans with the same caravan template
- one product domain with several team-owned capability knowledge
- one team carrying several persistent capability knowledge for different owned subsystems

## Runtime Model

Runtimes should consume resolved framework instances through capability-oriented contracts.

The framework should not assume that a runtime exposes:

- custom agents
- prompt files
- skills
- MCP
- subagents
- flows
- memory

Instead, the framework should define what is needed logically, and the runtime integration should declare whether and how it can satisfy those needs.

## Validation Model

Validation should happen on the resolved view, not only on raw artifacts.

### Minimum Validation Areas

- schema validity
- required field presence
- reference integrity
- inheritance validity
- overlay legality
- precedence determinism
- resolved team completeness
- resolved runtime-profile completeness

### Strongly Recommended Validation Areas

- scenario-based routing tests
- debate/escalation simulation
- domain attachment sanity checks
- role responsibility coverage checks
- runtime capability compatibility checks

## Packaging Independence

This logical model does not require any particular packaging mechanism.

Implementors may use:

- local files
- Git repositories
- GitHub
- GitLab
- object storage
- document databases
- relational databases
- APIs
- generated artifacts
- mixed systems

The framework should only require that the artifacts can be loaded, identified, resolved, and validated.

## Conventions Versus Requirements

The framework may recommend conventions such as:

- one artifact per document
- human-readable formats
- stable naming
- explicit versions
- grouping by artifact type

But those remain conventions, not mandatory requirements.

## Relationship To Existing Artifacts

Current artifacts created in this workspace map into this logical model as follows:

- [Information Technology Core Team Operating Model](../../docs/concepts/core-team-operating-model.md)
  - currently functions as an early `team-blueprint` plus role-boundary reference

- [domain-pack-spec.md](domain-pack-spec.md)
  - defines the reusable `domain-pack` specification

- [sample-product-domain-pack.md](../../examples/sample-organization/domain-knowledge/sample-product.md)
  - is a concrete `domain-pack` instance

This document sits above those artifacts and defines how they can coexist in a generalized framework.

## Long-Term Implication

This model supports the growth path you described:

- one personal AI team
- multiple domain-specialized teams
- shared organization catalogs
- local/private experimentation
- multiple runtime implementations
- future "AI company" style structures built on the same framework

## Summary

The logical artifact and overlay model defines the framework's portable core.

It separates meaning from storage, meaning from runtime, and shared structure from local customization.

That is what allows the framework to be reusable across organizations, teams, local experiments, and AI runtime ecosystems without locking itself to Codex, Git, or any specific storage system.
