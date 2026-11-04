---
name: agent-caravan-validator
description: Validate Agent Caravan artifacts and resolved configurations for identity, references, scope, composition, responsibility coverage, knowledge ownership, source layering, and runtime mapping compatibility. Use when reviewing framework changes, checking a new organization or caravan, preparing publication, or running a quality gate before runtime use.
---

# Organization Framework Validator

## Overview

Use this skill as a read-only quality gate for AI organization framework artifacts. Inspect the selected artifact set, resolve references and composition, report findings with evidence, and do not silently repair invalid artifacts.

## Workflow

### 1. Establish The Validation Boundary

- Locate the framework root and read its logical artifact model, applicable format specifications, and validation rules or framework validation guidance.
- Identify the selected organization catalog, caravan, caravan template, domain knowledge, capability knowledge, runtime integration, and runtime mappings in scope.
- Validate the smallest meaningful artifact set first; expand to all published artifacts only when requested or when cross-reference resolution requires it.
- Treat storage, Git, filesystem layout, and runtime vendor as implementation details unless the selected artifact explicitly makes them part of its contract.

### 2. Validate Identity And Scope

- Confirm each artifact declares `artifact_type`, stable `id`, `version` or revision, and `scope`.
- Confirm IDs are unique within their artifact type and that references identify the intended artifact type when names overlap.
- Confirm inheritance, replacement, and overlay relationships are explicit and resolvable.
- Confirm scopes are compatible with the requested sharing boundary: shared, organization, team, local, or session.
- Flag an artifact that embeds provider-specific behavior in a runtime-neutral type.

### 3. Resolve References And Composition

- Confirm organization catalogs publish or can resolve every selected artifact.
- Confirm each caravan references an existing caravan template and organization catalog.
- Confirm each capability knowledge artifact references an existing owner caravan and parent domain where required.
- Confirm domain and specialization loading order is deterministic: broad domain context before narrower specialization context, followed by task-specific context.
- Confirm configuration overrides do not silently suppress required coverage or create ambiguous replacements.
- Confirm a shared caravan template can be reused by multiple caravans without shared mutable team state.

### 4. Check Team Coverage

- Confirm all required roles resolve in the selected caravan template or valid replacements.
- Confirm mandatory debates retain their required participants.
- Confirm blocking lanes remain represented and limited to legitimate ownership boundaries.
- Confirm product, technical, implementation, quality, architecture, program, and release responsibilities remain distinguishable.
- Confirm documentation ownership and governance handoffs remain covered.
- For role variants such as `engineer-ii`, verify that extension changes are explicit and required responsibility coverage is preserved.

### 5. Check Domain And Specialization Boundaries

- Confirm domain knowledge describes broad, reusable context rather than one ticket's temporary decisions.
- Confirm capability knowledge is narrower than its parent domain and contains durable caravan-owned knowledge.
- Confirm two teams with the same template can have different owned surfaces, source priorities, workflows, and terminology.
- Flag duplicated or contradictory guidance that should belong in the parent domain instead of one specialization.
- Confirm source tiers distinguish authoritative durable sources from operational evidence and volatile notes.

### 6. Check Runtime Compatibility

- Confirm every runtime mapping targets an existing runtime integration.
- Confirm the integration declares the capabilities and constraints relied upon by the mapping.
- Confirm required capabilities are supported natively, adapted, or explicitly externalized with acceptable fallback behavior.
- Confirm runtime-native constructs do not redefine framework role or team semantics.
- Confirm permission, approval, observability, and degraded-mode expectations are explicit.
- Confirm a runtime mapping does not grant authority outside the resolved organization, team, domain, or repository boundary.

## Finding Model

Report findings before any summary, ordered by impact:

- `blocker`: resolution is impossible, required coverage is missing, or safety/authority boundaries are broken
- `high`: a published or runtime-ready configuration is materially inconsistent or ambiguous
- `medium`: composition, source priority, or validation weakness could cause incorrect behavior
- `low`: documentation, naming, or maintainability issue that does not currently block resolution

Each finding should include:

- severity
- artifact and stable ID
- evidence, preferably a field or reference
- why the issue matters
- the smallest recommended correction

## Validation Result

End with:

- `Passed`: checks that succeeded
- `Failed`: blocking or material findings
- `Skipped`: checks outside the requested boundary
- `Unverified`: checks that require unavailable storage, source, runtime, or human confirmation
- `Assumptions`: interpretation choices made during resolution

Do not call a configuration valid when required references or runtime capabilities remain unverified. Distinguish “no findings in the inspected scope” from “fully validated.”

## Safety And Mutation Boundary

- Keep validation read-only by default.
- Do not edit artifacts, publish catalogs, update Jira or Confluence, modify GitLab, or change runtime configuration unless the user explicitly requests remediation or publication after findings are reported.
- Do not treat a validation pass as authorization to execute implementation, release, deployment, or infrastructure actions.
