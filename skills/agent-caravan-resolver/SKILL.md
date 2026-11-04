---
name: agent-caravan-resolver
description: Resolve an effective Agent Caravan configuration from catalogs, caravan templates, caravans, responsibilities, knowledge, configuration overrides, runtime integrations, and mappings. Use when preparing a caravan for execution, explaining effective assignments and permissions, or producing a runtime-ready resolved view.
---

# Organization Framework Resolver

## Overview

Use this skill to turn a set of framework artifacts into one explainable effective configuration. Resolution is composition, not copying: preserve artifact identity and provenance, apply deterministic precedence, and surface conflicts or degraded conditions instead of guessing.

## Inputs

Collect the smallest complete set of inputs required by the requested resolution. The literal artifact types below remain part of the machine-readable contract:

- one or more base `organization-catalog` artifacts
- selected organization context
- selected `team-instance`
- referenced `team-blueprint`
- referenced base `role` artifacts and valid role variants
- selected `domain-pack` artifacts
- selected `specialization-pack` artifacts
- applicable `overlay` artifacts
- selected `runtime-adapter`
- applicable `runtime-profile`
- selected `validation-profile`

Do not assume that a filename, directory, Git repository, or vendor workspace is the source of identity. Resolve by stable artifact IDs and declared relationships.

## Resolution Workflow

### 1. Select The Operating Context

- Identify the organization catalog and sharing boundary.
- Identify the caravan and confirm its ownership boundary.
- Identify the work domain, narrower specialization, and runtime target.
- Separate durable framework context from temporary task context; task context is attached last.

### 2. Collect And Verify Base Artifacts

- Load the selected caravan template and its responsibility references.
- Load the selected caravan and its attached domain knowledge, capability knowledge, configuration overrides, and runtime defaults.
- Resolve every referenced responsibility, knowledge artifact, integration, and mapping.
- Stop and report unresolved required references before producing a runtime-ready result.

### 3. Apply Inheritance And Scope Precedence

Apply broad-to-narrow composition:

1. shared artifacts
2. organization artifacts
3. team artifacts
4. local artifacts
5. session artifacts

Within each scope, use declared priority. If two same-scope configuration overrides conflict without deterministic precedence, report an ambiguity instead of choosing by discovery order.

### 4. Resolve The Caravan Shape

- Start with the caravan template's roles, stage flow, debates, blocking model, documentation ownership, and governance rules.
- Apply valid role extensions while preserving base identity relationships.
- Apply `add`, `extend`, `replace`, and `suppress` overlays according to the overlay specification.
- For role replacement, resolve the effective role identity and verify preserved responsibility, debate, blocking, and documentation coverage.
- Keep the base template unchanged in the resolved provenance record.

### 5. Attach Domain Knowledge

- Attach broad domain knowledge before narrower capability knowledge.
- Confirm each capability knowledge artifact belongs to the selected caravan or an explicitly permitted broader scope.
- Preserve source priority and loading order from each pack.
- When preparing a portable execution plan, carry selected packs into the optional `knowledge_context.layers` field in domain-then-specialization order. Keep each shared layer once and retain its identity, version, trusted sources, loading guidance, and role-specific guidance when supplied.
- Keep `context.team_context.knowledge_sources` separate and apply it after pack layers in its declared order. Every harness must provide shared layers to assigned roles, apply role guidance only to its matching role, and honor `policy.knowledge_access` when retrieving sources.
- Attach task-specific Jira, repository, Confluence, SharePoint, chat, email, or environment context only after durable knowledge.
- Surface contradictory or stale source guidance instead of silently merging it.

### 6. Resolve Runtime Integration

- Select the runtime integration from the requested runtime or team default.
- Select the binding that matches the effective team, domain, specialization, overlay, and permission boundary.
- Confirm the adapter can satisfy the binding's required capabilities natively, through an explicit adaptation, or through an allowed externalized path.
- Resolve runtime-native agents, skills, profiles, prompts, tools, flows, or connectors only at this final layer.
- Preserve approval gates and do not infer runtime authority from role membership alone.

### 7. Validate The Resolved View

Use `agent-caravan-validator` when available. At minimum, check:

- all required roles resolve
- mandatory debate participants remain covered
- blocking and documentation responsibilities remain covered
- organization, team, domain, specialization, overlay, adapter, and binding references resolve
- overlay precedence is deterministic
- forbidden permissions are not introduced
- required runtime capabilities are satisfiable
- unresolved placeholders and ambiguous winners are absent

## Resolved View Contract

Produce an explainable result containing:

- selected organization catalog and context
- selected caravan and base caravan template
- effective roles and role provenance
- effective stages, debates, blockers, documentation, and governance rules
- attached domain and capability knowledge in loading order
- applied overlays, skipped overlays, and conflict decisions
- selected runtime integration and binding
- effective capabilities, permissions, approvals, and fallbacks
- validation rules and result
- unresolved, degraded, skipped, or unverified conditions

## Provenance Rules

- Every effective role, permission, knowledge layer, and runtime construct should be traceable to an artifact ID and version.
- Record both the base value and the overlay or inheritance operation that changed it.
- Record why an overlay won, why another was skipped, or why a conflict blocked resolution.
- Do not collapse different artifact types with the same ID into one unqualified reference.

## Failure Behavior

- `blocker`: stop resolution when a required reference, role, coverage obligation, permission boundary, or runtime capability cannot be resolved safely.
- `ambiguous`: stop when competing same-scope changes have no declared winner.
- `degraded`: continue only when the validation rules permit the missing capability or evidence, and record the fallback.
- `unverified`: continue only when the unresolved fact is non-critical and clearly marked for human or later source verification.

Never resolve by silently preferring the newest file, the closest filename, or the last artifact discovered.

## Safety And Mutation Boundary

- Resolution is read-only by default.
- Do not edit source artifacts, publish catalogs, update Jira or Confluence, modify GitLab, or change runtime configuration unless explicitly requested.
- A resolved view is not authorization to execute implementation, release, deployment, infrastructure, or production actions.
