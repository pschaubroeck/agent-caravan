---
name: agent-caravan-builder
description: Help an AI assistant set up or update runtime-neutral Agent Caravan organizations and teams, configure optional Agent Observability capture, then build advanced framework artifacts when needed. Use when configuring a team, enabling local workflow markers, adding persistent knowledge or instructions, composing a resolved team configuration, or adapting the framework to another AI runtime.
---

# Organization Framework Builder

## Overview

Use this skill to create or modify framework artifacts without coupling the organizational model to a storage provider, version-control system, or AI runtime. Keep reusable semantics in framework artifacts and place vendor-specific behavior only in runtime integrations and bindings.

AI-guided setup and update is one optional path through Agent Caravan. Users
can also enter directly at the operation they need: author, validate, resolve,
adapt, or inspect artifacts. Do not make a setup journey a prerequisite for
those tasks. The user should not need to learn Agent Caravan CLI commands to
configure a team. Use the CLI when it provides the safest persistence or
validation path, and explain the files that were created or changed.

## AI-Guided Setup And Update

Use this workflow when a user asks to set up, configure, or update a team.

### 1. Inspect Before Asking: Discover Configured Sources

- Locate the active Agent Caravan profile using the configured profile context;
  do not choose an organization from an arbitrary filename or directory order.
- Establish what sources the profile configures (for example, the active
  organization catalog, framework catalog, package roots, or workspace paths).
  Inspect only those sources and their referenced artifacts. Do not search
  arbitrary directories or select an organization, team, or ownership boundary
  by filename, display-name similarity, or discovery order.
- From those sources, inventory candidate caravans and their referenced
  blueprints, attached domain and capability knowledge, overlays, runtime
  profile, and existing team authoring workspace. Include artifact IDs and
  source/provenance where available. Inspect existing team Markdown as
  starter, blank, or user-customized; do not treat a directory name as proof
  that it belongs to a team.
- Report whether the organization and team already exist. For each plausible
  candidate, explain the match and its gaps using configured artifact data
  (such as mission, blueprint, ownership, attached knowledge, and required
  decisions). If no candidate can be grounded in configured sources, say so
  instead of inferring one.
- Recommend **reuse**, **extend**, or **create** and explain why. Reuse a
  suitable existing composition; extend it only when a known artifact needs
  an explicit change; create a new identity only when the requested team is
  distinct or no suitable configured candidate exists. Surface missing
  identity, ownership, or runtime decisions before asking the user to decide.
- Show coverage findings for the candidate when available, including the
  requirement, satisfying role or missing item, and provenance. Report
  structural validity, composition coverage, runtime capability realization,
  runtime verification, and task behavior as separate evidence. A missing
  runtime test means **unverified**, not unsupported. State a capability as
  unsupported only when the relevant configured adapter documents that
  limitation; do not generalize a limitation on one execution path to all
  runtimes.
- If profile resolution fails before coverage findings can be shown, use the
  resolver's available diagnostics path. When the checkout CLI is available,
  `agent-caravan resolve --diagnostics --root <profile-root>` optionally emits
  structured findings (including `team_coverage` for coverage failures) along
  with the failure status. This is a read-only diagnostic aid, not a required
  setup step or a replacement for guided explanation; report the non-zero
  resolution result accurately.
- Tell the user what is already present, what would be reused, and what
  remains undecided before asking questions. Reuse known values; do not ask
  the user to re-enter them.
- Preserve existing organization, team, blueprint, and runtime values unless
  the user requests a change.

### 2. Ask Only For Missing Decisions

- Ask concise questions one at a time.
- Ask for an organization or team name only when it is missing or ambiguous.
- When the only viable blueprint is `information-technology-core-team`, use it
  without asking the user to choose it.
- Reuse an existing runtime mapping. For a new profile, use the configured
  starter runtime only when the user has not selected another runtime.
- Do not ask for ownership scope during basic setup. Ownership and overlays
  are advanced configuration decisions.
- Treat repositories, services, and workspaces as optional descriptive work
  surfaces. They do not enforce repository ownership.
- Ask before replacing an existing artifact or discarding existing content.

### 3. Preview Before Writing

Show the selected candidate and recommendation, proposed organization, team,
blueprint, attached knowledge, overlays, runtime, authoring workspace, and
files to create or update. Identify which artifact IDs and values are reused,
which are new, and which optional values remain unset. Show the expected
coverage and runtime evidence changes where relevant. Stop if the user
identifies an ambiguity or does not approve the proposed write.

### 4. Persist The Starter Configuration

- Use the existing initialization/configuration CLI when it safely creates or
  updates the local profile. The CLI is a persistence and diagnostic tool, not
  the user's required mental model.
- Create the first team from the shared blueprint rather than copying shared
  roles or templates into the organization source.
- For an existing candidate, preserve its stable IDs and existing composition
  unless the user approved a specific change. Do not create a parallel team
  solely because a similar team name or directory was found.
- Create or update the standard team Markdown files in the team authoring
  workspace.
- Preserve existing Markdown files and user edits. Create only missing files
  unless the user explicitly asks to replace content.
- Keep local profile state and sessions outside the repository.

### 5. Explain And Validate

Explain the purpose of each team Markdown file:

- `caravan.md`: mission and practical scope.
- `repositories.md`: commonly used repositories, services, and workspaces.
- `knowledge.md`: trusted documentation and instruction sources.
- `working-agreements.md`: durable implementation and review expectations.
- `instructions.md`: durable team-specific AI instructions.
- `responsibilities.md`: preferred roles and participation guidance.

Then resolve and validate the effective configuration. Report the validation
status, authoring workspace, changed files, remaining optional configuration,
and the next useful AI action. Report structural validity and composition
coverage separately from runtime capability realization and runtime
verification. An untested runtime remains unverified; do not describe it as
unsupported without adapter evidence for the capability and execution path
in question. Distinguish durable team guidance from runtime-specific projection
and temporary task/session evidence.

### Optional Agent Observability Setup

Only configure Agent Observability when the user asks to enable or inspect it;
it is not part of baseline team initialization. Agent Caravan's Codex and
OpenCode adapters can record local workflow start/finish markers through the
optional `agent-observability` Python package. This covers the Agent Caravan
workflow dispatch boundary only; it does not measure individual roles, agents,
skills, models, or tools.

When enabling it:

1. Inspect the active runtime mapping and its source. Keep the change in the
user's local profile configuration; do not edit a packaged shared profile or
organization catalog to enable one user's capture.
2. Check that the Agent Caravan Python environment can import
`agent_observability.sessions.SessionStore` and that the host is POSIX. The
package is optional and the marker store requires POSIX advisory locks. If
either prerequisite is absent, explain that Agent Caravan execution still works
but markers cannot be recorded. Do not silently install packages or guess an
unverified package source.
3. Preview setting `execution.observability.enabled` to `true`, with
`export: local` and `capture_content: false`. Remote export and content capture
are not implemented by this adapter. Preserve other profile fields and follow
the normal preview-before-write rule.
4. Resolve the active profile after the change. Explain that markers use
`~/.agent-observability/observations.jsonl` by default; `AWO_STORE` changes the
local store path and `AWO_POLICY` optionally supplies an Agent Observability
collection policy. Without `AWO_POLICY`, Agent Caravan selects the active
workflow identity.
5. Do not launch a workflow solely to test capture unless the user requests a
smoke run. On the next ordinary execution, check for
`metadata.observability_capture.state == "recorded"` and the associated opaque
reference. A missing package or store failure reports a capture diagnostic and
does not fail the Agent Caravan workflow.

The base Agent Caravan package does not depend on Agent Observability. Installing
the optional package in the same Python environment is necessary only when the
user wants workflow markers recorded.

### 6. Offer Optional Team Customization

After starter setup, tell the user when the team is valid but still generic and
offer an optional customization pass. Do not make this a required `init`
question or block ordinary use of the team.

When the user accepts:

1. Inspect all six team Markdown files and classify each as blank, starter
   content, or user-customized.
2. Ask concise questions one at a time only for the areas the user wants to
   change. Use these subjects and file boundaries:
   - team purpose and practical scope -> `caravan.md`
   - useful repositories, services, and workspaces -> `repositories.md`
   - trusted documentation and instruction sources -> `knowledge.md`
   - durable implementation and review practices -> `working-agreements.md`
   - team-specific AI behavior -> `instructions.md`
   - preferred role participation -> `responsibilities.md`
3. Explain that repositories and workspaces provide context; they do not
   enforce repository ownership.
4. Explain that preferred roles guide participation only among roles allowed by
   the resolved blueprint and workflow. They do not replace role
   responsibilities, mandatory stages, reviewers, or approval policy.
5. Show a file-by-file preview of proposed changes before writing anything.
6. Preserve existing user-authored content and update only approved files.
7. Resolve and validate after writing, then report changed files, execution
   effects, remaining optional configuration, and unresolved conditions.

If the user declines customization, leave the starter Markdown unchanged and
continue with the normal validation and next-action report.

### 7. Advanced Customization

For requests beyond starter setup, guide the user to the relevant Markdown
file or framework artifact. Prefer editing the team's Markdown files for team
mission, work surfaces, knowledge, working agreements, instructions, and role
guidance. Use machine-readable framework artifacts for shared roles, blueprints,
domains, specializations, overlays, adapters, and runtime mappings.

Do not introduce repository ownership enforcement merely because a repository
is listed as a work surface. Do not put runtime-specific behavior in shared
team guidance.

## Artifact Authoring Workflow

### 0. Establish Organization Ownership

- For advanced organization-scoped artifacts, ask which organization owns the
  artifact before creating or changing any role, team, domain, specialization,
  overlay, adapter, or binding. This is not a reason to repeat a known team
  choice during ordinary setup.
- If multiple organizations are available in the active profile, do not choose
  one by filename or discovery order.
- Before replacing an existing artifact, identify its stable artifact ID and
  ask whether to update it in place or create a new artifact identity.
- Keep the organization catalog's publication lists synchronized with newly
  created artifacts.

### 1. Discover The Framework Context

- Locate the framework root and read its artifact model, relevant format specification, and validation guidance before editing.
- Determine whether the requested change is shared, organization-scoped, team-scoped, local, or temporary.
- Identify the existing organization catalog, caravan template, caravan, domain knowledge, capability knowledge, or runtime integration that should be extended.
- Do not assume the framework is stored in Git, a particular directory, or one global organization.

### 2. Select The Artifact Boundary

- Use an `organization-catalog` for a publication or sharing boundary.
- Use a responsibility (`role`) for reusable responsibility semantics.
- Use a caravan template (`team-blueprint`) for reusable composition and workflow shape.
- Use a caravan (`team-instance`) for a durable group applying a template to a product or ownership boundary.
- Use domain knowledge (`domain-pack`) for broad product, platform, service, or technology knowledge.
- Use capability knowledge (`specialization-pack`) for persistent knowledge narrower than a domain and owned by a caravan.
- Use a configuration override (`overlay`) for scoped add, extend, replace, or suppress behavior.
- Use a runtime integration (`runtime-adapter`) for capability truth about one AI runtime.
- Use a runtime mapping (`runtime-profile`) for mapping resolved framework artifacts onto that integration.

The parenthesized values are current machine-readable artifact types; retain
them when writing artifacts even though user-facing terminology has changed.

### 3. Preserve Composition Boundaries

- Prefer composition over copying. Reuse a caravan template across many caravans and attach different domain or capability knowledge.
- Keep role meaning independent from domain knowledge and runtime constructs.
- Keep team ownership and persistent knowledge in the caravan and capability knowledge, not in a forked role or template.
- Add a role variant such as `engineer-ii` by extending `engineer`; preserve required coverage and explicitly document changed authority or expectations.
- Create a new artifact identity when the semantic object is distinct. Keep an existing ID stable when revising the same object.

### 4. Write The Artifact

- Follow the applicable format specification and include stable identity fields: `artifact_type`, `id`, `version`, and `scope`.
- State purpose, composition, ownership, source or loading guidance, governance, and validation hints appropriate to the artifact type.
- Use stable artifact IDs for references. Do not use filenames, URLs, or provider-specific paths as logical identity.
- Keep examples concrete enough to resolve but do not invent authoritative product facts when the artifact is illustrative.
- For a new organization, create its first caravan as machine-readable
  JSON in the selected organization's source boundary. Start from the shared
  `information-technology-core-team` template and ask only for the missing
  team identity. Attach a runtime integration or binding only when the selected
  runtime requires it; do not assume Codex is the framework contract.
- Update the organization's `published_artifacts` lists and the local profile's `active_context` after creating the caravan. Do not duplicate shared roles or templates into the organization source.
- For runtime mappings, declare `target_adapter_id`, target artifact types, capability contract, permission boundaries, fallback behavior, and observability expectations.

For the first caravan, the minimum machine-readable shape is:

```json
{
  "artifact_type": "team-instance",
  "id": "<organization>-<team>",
  "version": "1.0.0",
  "scope": "organization",
  "name": "<team display name>",
  "team_blueprint_id": "information-technology-core-team",
  "role_overlays": [],
  "domain_packs": [],
  "specialization_packs": [],
  "runtime_defaults": ["codex-desktop-agent-runtime"]
}
```

For a new caravan, collect the organization and team ID/name before
writing this artifact. Treat ownership boundary and runtime selection as
explicit advanced decisions only when they are needed. Ask separately before
replacing an existing caravan.

### 5. Resolve And Check The Change

- Confirm every referenced artifact ID exists in the selected sharing boundary.
- Confirm caravans reference a valid caravan template and organization catalog.
- Confirm capability knowledge reference a valid owner caravan and parent domain where required.
- Confirm required roles, mandatory debates, blocking lanes, and documentation coverage remain intact.
- Confirm role variants preserve the coverage they replace or extend.
- Confirm runtime mappings target an existing adapter and do not grant permissions beyond the resolved team boundary.
- Run the repository or framework validator when available. If no validator exists, perform focused structural and reference checks and report the limitation.

## Decision Rules

- If the request changes responsibility semantics, update a role.
- If it changes shared workflow or debate behavior, update a caravan template.
- If it changes one team's ownership, update a caravan.
- If it adds durable team-owned knowledge, update or add a capability knowledge.
- If it changes broad product or platform context, update a domain knowledge.
- If it changes how a runtime realizes the framework, update an adapter or binding, not the core artifacts.
- If the user wants a temporary exception, prefer an overlay or session-scoped artifact over changing a shared artifact.

## Output Expectations

- Summarize the artifacts created or changed and why each boundary was selected.
- Identify unresolved source, ownership, validation, or runtime assumptions.
- Distinguish durable framework changes from illustrative examples and temporary task context.
- Do not publish or mutate remote catalogs, Jira, Confluence, GitLab, or runtime configuration unless the user explicitly requests that action.
