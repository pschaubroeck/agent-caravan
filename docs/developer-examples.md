---
type: Guide
title: Developer Examples
description: Supplemental examples for authoring Agent Caravan artifacts and integrating AI harnesses.
---

# Developer Examples

This page contains supplemental, advanced examples for artifact authoring and
AI-harness integration with Agent Caravan. It is not the canonical product
onboarding guide. For requirements, package installation, initial setup, and
the supported user workflow, start with the [Agent Caravan user guide](user-guide.md).
For Python checkout setup and contributor checks, see [Repository Getting
Started](getting-started.md).

The examples below preserve implementation detail that is useful when you are
extending framework artifacts or integrating a harness. They assume familiarity
with the product setup path and should not be read as a separate onboarding
sequence.

## Contents

- [Before you start](#before-you-start)
- [Example map](#example-map)
- [Discover a team before configuring it](#discover-a-team-before-configuring-it)
- [Create a reusable role or role variant](#create-a-reusable-role-or-role-variant)
- [Customize a role for one team](#customize-a-role-for-one-team)
- [Customize each team Markdown file](#customize-each-team-markdown-file)
- [Participation guidance](#participation-guidance)
- [Use or switch between configured teams](#use-or-switch-between-configured-teams)
- [Make Agent Caravan the default task workflow](#make-agent-caravan-the-default-task-workflow)
- [Wire Agent Caravan into a harness](#wire-agent-caravan-into-a-harness)
- [Check, resolve, validate, and dry-run](#check-resolve-validate-and-dry-run)
- [Start a real implementation through an AI harness](#start-a-real-implementation-through-an-ai-harness)
- [Coordinate work across an organization](#coordinate-work-across-an-organization)
- [Add advanced configuration](#add-advanced-configuration)
- [Export a runtime-neutral handoff](#export-a-runtime-neutral-handoff)
- [Common setup and validation problems](#common-setup-and-validation-problems)

## Before you start

Make the Agent Caravan skills available to your AI harness. The shareable skill
sources are in [`skills/`](../skills/). The Python package bundles them;
explicit `agent-caravan init` installs the selected runtime set. See the
[installation examples](reference/packaging-and-distribution.md#install-and-refresh-skills).
Use the builder for setup and customization, the resolver to inspect effective
configuration, and the validator to check framework artifacts. For
implementation work, use the orchestrator skill where the harness supports
its workflow.

| Skill | Use it for |
| --- | --- |
| [`agent-caravan-builder`](../skills/agent-caravan-builder/SKILL.md) | Create or update an organization and team, preserving existing sources and Markdown. |
| [`agent-caravan-resolver`](../skills/agent-caravan-resolver/SKILL.md) | Inspect how catalogs, caravans, responsibilities, knowledge, configuration overrides, and runtime settings compose. |
| [`agent-caravan-validator`](../skills/agent-caravan-validator/SKILL.md) | Check artifact identity, references, scope, coverage, and runtime compatibility. |
| [`agent-caravan-codex-orchestrator`](../skills/agent-caravan-codex-orchestrator/SKILL.md) | Run implementation work through an active Agent Caravan team in Codex. |
| [`agent-caravan-opencode-orchestrator`](../skills/agent-caravan-opencode-orchestrator/SKILL.md) | Run implementation work through a matching active team in OpenCode. |

The default local profile is `~/.agents/agent-caravan`. For the manual or
scripting workflow from a checkout, see the repository
[CLI guide](getting-started.md#use-the-checkout-cli).

## Example map

The repository's [examples index](../examples/README.md) connects the setup,
sharing, distribution, and orchestration examples. The [coworker-sharing
scenario](../examples/coworker-sharing/README.md) uses a generic organization
and runnable profile files to show two coworkers resolving one shared team
catalog. Its [Codex plugin package](../examples/codex-plugins/example-organization-platform-team/README.md)
distributes a versioned snapshot of those same artifacts. The
[organization-coordination example](../examples/org-coordination/README.md)
shows a harness using an example-owned organization map to route work among
separately resolved teams. These examples use the fictional Sample Organization and Sample Product to
show generic team composition and specialization patterns. The [sample
catalog](../examples/sample-organization/README.md) contains the corresponding
artifacts.

These examples assume an active team and focus on deeper customization and
harness integration. For first-time setup, re-running setup, or adding a team,
start with the [user guide](user-guide.md). Expand a CLI equivalent only when you want to perform the supported command-line steps yourself; the hidden commands assume the default profile.

## Discover a team before configuring it

**When to use:** before initial setup or when changing an existing team, to
understand what is already configured and what should be reused.

```text
Inspect only the active Agent Caravan profile's configured sources. List
candidate caravans, templates, knowledge, overrides, runtime mappings, and
workspaces. Explain fit, gaps, and missing decisions from artifact
evidence. Recommend reuse, extend, or create; show coverage and provenance
when available. Do not write yet.
```

**Expected result:** a no-write inventory tied to configured sources, with a
reasoned recommendation and any unresolved choices. If several candidates
match, the assistant presents them instead of selecting by filename or name
similarity. If no configured candidate fits, it says so and can proceed to the
fresh-profile starter path after the user supplies missing decisions.

**Changed files:** none. This is a discovery step; the CLI remains the
persistence and validation path when it is the safest way to apply an approved
configuration. Existing IDs and user-authored workspace content should be
preserved.

**Evidence:** report artifact structure and team coverage separately from
runtime capability realization, verification, and task behavior. Mark an
untested runtime as unverified; only state that a capability is unsupported
when the applicable adapter documents that limitation.

## Create a reusable role or role variant

**When to use:** a responsibility is reusable across teams, or an existing role
needs a deliberate variant with different authority or expectations.

```text
Create a reusable role named release-coordinator for release planning,
readiness checks, and handoff coordination. Inspect existing roles first,
choose the correct shared or organization scope, show the complete artifact
and references before writing, then resolve and validate it.
```

For a variation of an existing role:

```text
Create an engineer-ii role variant by extending engineer. Preserve the base
engineer coverage, document the changed expectations and authority, show the
role artifact and affected team references, then validate the result.
```

**Expected result:** a stable role artifact with an explicit ID, version,
responsibility semantics, scope, and validation hints. A role variant retains
the coverage of the role it extends unless the change is explicitly modeled.

**Changed files:** the role artifact, organization publication lists when the
role is organization-scoped, and explicit team or blueprint references when
the role is composed into a team.

**Validation:** ask the resolver to show where the role is composed and ask the
validator to check identity, references, scope, coverage, and required
workflow participation.

**Does not enforce:** creating a role does not add it to every team, change a
caravan template automatically, grant permissions, or create a native harness
worker.

### Role-authoring checklist

Use the AI assistant to prepare both parts of the artifact before writing:

1. Create the human-readable role artifact under
   `resources/core/responsibilities/<role-id>.md` for a shared role, or under the
   organization’s example scope for organization-specific behavior.
2. Include stable identity (`id`, `name`, `version`, `scope`, and
   `role_type`), mission, summary, ownership boundaries, outputs, operating
   model, decision rights, runtime capabilities, and validation hints.
3. Add the compact machine-readable role projection to the applicable core or
   organization catalog, including the same ID, version, scope, mission, and
   responsibilities.
4. Publish the role ID only in the catalog that should make it available.
5. Do not add the role to a caravan template or caravan unless the request
   explicitly composes it there.
6. Show the complete Markdown artifact, machine-readable projection, and
   affected references before writing them.

The reusable field definitions are in the [role specification](../resources/specifications/role-spec-format.md),
and the existing artifact layout is shown in the [core role README](../resources/core/responsibilities/README.md).

For a first role, ask the assistant to produce the proposed files and a
reference diff, then use `agent-caravan resolve` to inspect the selected
composition and the Agent Caravan Validator skill to review the custom artifacts
after approval. `agent-caravan validate` checks serialized artifact schemas,
selected cross-artifact references, and packaged skill presence; it does not
resolve all semantic coverage or verify runtime behavior. The current CLI does not author roles or replace semantic
review by the Agent Caravan validator skill.

<details>
<summary>CLI equivalent (validation after authoring)</summary>

There is no general CLI authoring command for roles. After creating the
machine-readable role and its explicit references, inspect the active profile
and check packaged resources separately. Use the Validator skill for custom
artifact review:

```sh
agent-caravan resolve
agent-caravan validate
```

</details>

## Customize a role for one team

**When to use:** the role already exists, but one team needs extra guidance for
its work. Put the team-specific behavior in its capability knowledge; leave the
shared role unchanged. Create or extend a role only when the responsibility or
decision rights should be reusable across teams.

Example: customize the existing `engineer` role for customer-facing workflows.
The sample specialization lives at
[`sample-product-workflows-specialization.md`](../examples/sample-organization/capability-knowledge/sample-product-workflows-specialization.md).
Add concrete, role-specific instructions under `Role Guidance`:

```markdown
- `engineer`: trace a reported issue through the user-visible workflow and
  state transitions; add regression coverage for the affected behavior, and
  include accessibility checks when the change affects an interaction. Ask
  `tech-owner` before changing a shared contract.
```

Use this workflow:

1. Find the caravan and confirm it owns the workflow. Reuse its existing
   specialization if one fits; otherwise create one with that team as owner.
2. Edit the specialization's `Role Guidance` with observable actions and
   boundaries. Put repository paths, commands, and local conventions in its
   knowledge/loading guidance, not in the shared role.
3. Attach the specialization to the caravan's `specialization_packs` and
   publish its ID in the organization catalog when using loadable JSON
   artifacts. Do not add it to unrelated teams.
4. Resolve the team and inspect that the specialization is present alongside
   the unchanged `engineer` role. Validate artifact IDs, references, scope,
   and coverage; then try a representative task and check that the guidance
   leads to the expected actions.

The `sample-organization` files linked above are readable Markdown
illustrations, not loadable catalog artifacts. For executable examples of
composition, see the JSON caravans and the
[coworker-sharing scenario](../examples/coworker-sharing/README.md). A
specialization guides role behavior but does not itself create a runtime agent
or enforce permissions; bind runtime-specific prompts, tools, and capabilities
in a runtime mapping.

## Customize each team Markdown file

**When to use:** after starter setup, when durable team context should guide
future tasks without changing the reusable blueprint.

```text
Help me update the active team’s Markdown files for its current work. Preview
the edits I choose, preserve everything else, then resolve and validate.
```

| File | Example content | How it guides work |
| --- | --- | --- |
| `caravan.md` | Team mission and purpose | Frames why the team exists. |
| `repositories.md` | Repositories, services, or workspaces | Points an implementor toward relevant work surfaces. |
| `knowledge.md` | Trusted documentation and instruction sources | Identifies references to load, subject to runtime and policy access. |
| `working-agreements.md` | Review and collaboration practices | Records durable team expectations. |
| `instructions.md` | Team-specific AI guidance | Adds reusable guidance for AI-assisted tasks. |
| `responsibilities.md` | Preferred role IDs and participation guidance | Expresses preferences among roles available to the resolved team. |

Use small, durable entries rather than copying a task prompt into every file:

```markdown
<!-- caravan.md -->
Support reliable AI-assisted technology delivery and engineering quality.

<!-- repositories.md -->
- `/Users/me/workspace/example-service` — primary implementation workspace

<!-- knowledge.md -->
- `docs/getting-started.md` — Agent Caravan setup and workflow guidance

<!-- working-agreements.md -->
- Prefer small, verifiable changes; run focused tests before review.

<!-- instructions.md -->
- Inspect repository guidance before editing and report anything unverified.

<!-- responsibilities.md -->
- `tech-owner`
- `quality-engineer`

## Participation guidance

Prefer `tech-owner` for solution shaping and `quality-engineer` for focused verification.
```

The paths and references above are examples, not automatic access grants. Keep
repository-specific facts in the repository's own guidance when they should
travel with that repository. Keep durable team behavior here when it should
apply across workspaces.

**Expected result:** each durable decision appears in the narrowest matching
file and is included in team context during resolution or execution.
Changes to `responsibilities.md` take effect in the next profile resolution; subsequent
execution uses the refreshed context. Participation guidance informs the
harness but does not change role assignments in the execution plan.

**Changed files:** only the selected Markdown files and, if the authoring
workflow parses them into profile state, the matching team-instance context.

**Validation:** ask the resolver to confirm that it reads the updated team
context, then ask the validator to report any artifact or reference issues.

**Does not enforce:** repository listings are contextual work surfaces, not
access or ownership controls. Knowledge entries are references, not proof
their contents were loaded. Role preferences do not replace blueprint duties,
execution-profile stages, reviewers, or approval policy.

<details>
<summary>CLI equivalent (manual edit and check)</summary>

There is no CLI command that reviews or edits all six files. Edit the selected
files in `~/.agents/agent-caravan/caravans/<team-id>/`, then resolve the profile:

```sh
agent-caravan resolve
```

To configure a non-active team explicitly, use its stable ID:

```sh
agent-caravan configure --team-id <team-id>
agent-caravan status --json
agent-caravan resolve
```

For a source checkout or an isolated profile, keep the same `--root` on every
profile command. Run these from the Agent Caravan checkout after creating the
profile:

```sh
PYTHONPATH=src python3 -m agentcaravan.cli configure --root /path/to/profile
PYTHONPATH=src python3 -m agentcaravan.cli status --root /path/to/profile --json
PYTHONPATH=src python3 -m agentcaravan.cli resolve --root /path/to/profile
PYTHONPATH=src python3 -m agentcaravan.cli validate
```

`status`, `resolve`, and `configure` inspect the selected profile. `validate` checks the packaged or checkout resources and does not
select a profile, so it does not take `--root`.

</details>

## Use or switch between configured teams

**When to use:** an organization has multiple teams and a task should use one
specific team’s context.

```text
Use the Platform Team from my active Agent Caravan organization for this task.
First confirm the selected organization, caravan, template, and runtime mapping.
If Platform Team is not active, explain how to select it before planning work.
Do not silently use another team.
```

**Expected result:** the harness confirms the effective team before planning
and reports the team context used for the task. Team-specific Markdown and
knowledge are loaded only from the selected composition.

**Changed files:** team selection may update the active local profile; a task
request by itself should not modify shared team artifacts.

**Validation:** compare `team_id`, blueprint, runtime mapping, and resolved
team documents in the profile result before allowing implementation to begin.

**Does not enforce:** a team preference in a prompt cannot override an
ambiguous profile, unsupported runtime binding, approval policy, or repository
access boundary.

<details>
<summary>CLI checks</summary>

```sh
agent-caravan init \
  --organization "Example Organization" \
  --team "Platform Team"
agent-caravan status --json
agent-caravan resolve
```

When the team already exists, `init` reuses its stable ID and updates the
active profile when its runtime matches the selected runtime. A conflicting
runtime requires a matching team or separate profile root. `--team-id` is
optional for normal use; provide it only when a team has a custom ID or the name needs explicit disambiguation.

</details>

## Make Agent Caravan the default task workflow

**When to use:** Agent Caravan should be applied to ordinary implementation
requests without developers repeating the full workflow prompt.

Put a concise default instruction in the harness’s persistent instruction
layer, while keeping the shared wording runtime-neutral. It should invoke the
active Agent Caravan team for ordinary implementation tasks:

```text
Use the active Agent Caravan team for implementation work. Inspect team context
and repository guidance. Explain roles, make a bounded plan, use available
role and handoff capabilities, make the smallest change, run focused tests,
and report roles, handoffs, changed files, validation, and anything unverified.
```

**Expected result:** a normal request such as “fix the parser bug” triggers
team discovery, repository-guidance inspection, bounded planning, role
participation, focused verification, and an evidence-based completion report.

**Changed files:** the harness’s persistent instruction file or configuration,
not the Agent Caravan framework artifacts. Runtime-specific installation belongs
in the selected adapter or harness integration.

**Validation:** start a small read-only or documentation task without naming
Agent Caravan in the task prompt. Confirm that the harness discovers the active
team, reports its role workflow, and does not claim unsupported capabilities.

**Does not enforce:** a persistent instruction is a routing/default behavior,
not a permission grant. It cannot override an explicit user request, missing
team configuration, repository guidance, runtime limitations, or approval
boundaries.

For a harmless acceptance check, start a task without naming Agent Caravan:

```text
Improve one small piece of developer documentation. Inspect repository
guidance and team context first. State the roles and bounded plan. Use native
sub-agents and handoffs when available. Run focused checks and report files,
validation, and anything unverified. Do not push, open an MR, or deploy.
```

Good evidence includes the selected team, execution mode, participating roles,
worker references when exposed, handoffs, changed files, focused tests, and
unverified conditions. Role names alone do not prove that native workers ran.

## Wire Agent Caravan into a harness

**When to use:** installing the skills and persistent instructions that make
the default workflow available to a specific AI harness.

```text
Configure this harness to use Agent Caravan by default. Inspect available
skills and the active profile. Show which persistent instruction or skill
configuration you would update. Keep shared workflow runtime-neutral; put
harness-specific wiring in the adapter layer. Preserve unrelated instructions.
```

For Codex, install or refresh the shareable Agent Caravan skills under the
configured skill root and use `agent-caravan-codex-orchestrator` as the
runtime-specific execution entry point. For OpenCode, use
`agent-caravan init --runtime opencode` and
`agent-caravan-opencode-orchestrator` with a matching team. Codex remains the
default runtime. Other harnesses should map the same
portable team context, plan, role turns, handoffs, and completion evidence to
their own capability boundary.

**Expected result:** the harness can discover the builder, resolver, validator,
and appropriate execution skill; ordinary implementation requests can invoke
the configured workflow; and the harness reports when native delegation or
persistence is unavailable.

**Changed files:** harness-local instructions and installed skill locations;
shared Agent Caravan artifacts should remain runtime-neutral.

**Validation:** run a harmless task through the harness and confirm the active
team, role workflow, and capability limitations are reported. Then inspect the
resolved profile separately to prove the framework configuration is valid.

**Does not enforce:** installing a skill does not prove that the harness will
delegate native workers, apply reasoning settings, persist evidence, or grant
external access. Those capabilities require runtime evidence.

<details>
<summary>Codex-specific reference</summary>

See [Codex adapter walkthrough](integrations/codex-adapter.md) for the
runtime-specific installation, projection, native delegation, and evidence
path. Keep those details out of shared team Markdown and portable artifacts.

</details>

## Check, resolve, validate, and dry-run

**When to use:** checking setup health, inspecting effective composition, or
confirming that a sample task can produce valid evidence without starting a
real implementation.

```text
Check my active Agent Caravan profile and explain any unresolved configuration.
Then run a truthful dry-run for “Demonstrate the configured flow” and report
the result and evidence path. Don’t start a live task.
```

**Expected result:** the assistant reports profile health, effective
composition, artifact validation, and—if the reference dry-run is available—a
task result with independently validated task, session, run, and completion
evidence.

**Changed files:** profile inspection, resolution, and artifact validation are
read-only. A dry-run writes evidence under the configured sessions directory.

**Validation:** review the resolver and validator reports separately. Confirm
that any dry-run is identified as simulated and that its persisted evidence
passes session validation.

**Does not enforce:** a dry-run does not call a model, launch a live harness,
verify external source truth, or prove runtime behavior. Resource validation,
profile resolution, and session validation cover different objects.

The Agent Caravan validator skill checks the selected artifacts; the CLI
`validate` command checks installed framework resources. These checks are not
interchangeable.

<details>
<summary>CLI equivalent</summary>

```sh
agent-caravan status
agent-caravan resolve
agent-caravan validate
agent-caravan run --dry-run --task-id example-feature-001 \
  --objective "Demonstrate the configured flow"
agent-caravan validate-session --task-id example-feature-001
```

If you repeat `example-feature-001`, add the next unused `--attempt <number>`
or a unique `--run-id <run-id>` to preserve earlier evidence.

These commands use the default local profile and sessions location. Use
`--root` and, for `run` or `validate-session`, `--sessions-root` only when
you are intentionally working with an isolated or alternate profile.

</details>

## Start a real implementation through an AI harness

**When to use:** the team is configured and you want your selected AI harness
to do implementation work.

```text
Use my active Agent Caravan team to implement:

<real change for this repository>

Inspect guidance and team context. State roles and plan, use sub-agents and
handoffs when possible, make a small change, run focused checks, report files,
validation, and gaps. Do not push or deploy.
```

Replace the placeholder with a real, repository-relevant objective. The
assistant should ask for clarification rather than invent an implementation
when the objective does not match the repository.

For Codex, the `agent-caravan-codex-orchestrator` skill describes the native
workflow. Another harness can map the same portable plan and team context to
the role and handoff capabilities it supports.

**Expected result:** the harness inspects the selected team and repository,
plans the work, implements through available capabilities, and reports actual
verification evidence.

**Changed files:** files required by the task and task-scoped evidence when
the harness supports or is configured to persist it.

**Validation:** ask the harness to run checks appropriate to the change,
report exact outcomes, and validate persisted evidence when available.

**Does not enforce:** the prompt does not launch a particular harness, create
native role workers in every runtime, grant permissions, or guarantee durable
evidence. The active runtime integration and policy define those capabilities
and approval boundaries.

The harness should not silently treat a role as a permanent agent. Roles are
portable responsibilities; worker names and display labels are runtime-owned.
The framework can request role-appropriate reasoning levels, but effective
reasoning is unverified unless the runtime reports it directly.

There is no CLI command for live implementation. The CLI can export a handoff
for another harness, but that does not execute the task; see [Export a
runtime-neutral handoff](#export-a-runtime-neutral-handoff).

## Coordinate work across an organization

**When to use:** a request crosses team ownership boundaries and the harness
needs to propose which teams should handle each part.

Ask your AI harness:

```text
Use the organization map in examples/org-coordination to plan this request:
add a customer preference setting that needs a product workflow change and
a shared API update. Show which teams own each part, resolve each through
Agent Caravan, and present the handoff plan before starting work.
```

The map groups the Example Organization's Platform and Product teams under
Engineering. It records example reporting relationships, ownership areas,
specialties, and an explicitly authored scenario route. The runner accepts
`--map`, `--catalog`, `--team-dir`, and `--scenario` options so the recipe can
be run against another sidecar dataset; without options, it uses the checked-in
example. It validates hierarchy references and prints the selected route
without launching agents. Reporting labels remain descriptive metadata.

**Expected result:** the harness proposes that Product define and integrate
the customer-facing workflow while Platform handles the shared API change. It
resolves each selected team separately and shows the planned handoffs. If the
request does not match a clear ownership rule, it asks for clarification.

**Changed files:** none during the walkthrough. The checked-in organization
map and runner are example inputs; resolving teams uses the selected profile.

**Validation:** run `python3 examples/org-coordination/run.py` and compare its
dry-run route with the selected scenario in the map. For another dataset, pass
its map, catalog, team directory, and scenario with the runner options. Ask the
harness to resolve each selected team and report its ID and ownership boundary
before approving the work plan.

**Does not enforce:** The map is orchestration input, not an Agent Caravan
artifact. Reporting fields do not grant permissions or create manager
relationships in the framework. The runner prints a route.
It does not invoke a model, dispatch work, or implement a cross-team workflow.
Hierarchy and specialties do not automatically choose teams; every route is
defined explicitly in the selected scenario.

## Add advanced configuration

**When to use:** the team needs durable knowledge or composition beyond the
starter blueprint. Names and filenames do not attach advanced layers
automatically.

```text
Add a team-owned workflow specialization under the Sample Product
domain. Check the existing artifacts, show me the proposed changes, then
resolve and validate them.
```

Inspect the catalog, team, domain, and specialization sources before creating
anything. Reuse an existing matching artifact and its stable identity instead
of creating a duplicate because a name or filename looks different.

| Layer | Use it for | Does not mean |
| --- | --- | --- |
| Domain knowledge | Broad product, platform, or technology context and trusted source indexes | A ticket's temporary facts, an access grant, or automatic attachment by name |
| Capability knowledge | Narrower durable knowledge owned by a caravan and attached after its broad domain | A second caravan template or a replacement for parent domain context |
| Configuration override | A scoped add, extend, replace, or suppress operation on resolved composition | An informal preference or a change selected by filename; precedence and required coverage must resolve |
| Runtime integration | Capability truth, constraints, and support levels for a runtime class | Caravan responsibilities or workflow semantics |
| Runtime mapping | Maps resolved artifacts to a runtime integration and its constructs | A capability guarantee unsupported by the integration, or an execution workflow |
| Workflow | Runtime-neutral stages, responsibility activation, topology, escalation, evidence, and termination | A harness-specific runtime binding or permission beyond policy |

**Expected result:** selected artifacts are explicitly published or referenced
at the appropriate catalog, team, or local scope, resolve in the intended
order, and pass applicable identity, scope, coverage, and runtime checks.

**Changed files:** the relevant organization catalog, caravan, and new or
updated artifacts in the appropriate shared, organization, team, or local
source. Local overrides and session state belong under
`~/.agents/agent-caravan/`, not in shared artifact sources.

**Validation:** for checked-in repository examples, use the repository's
example resolver and validator to inspect the composed view and report
identity, reference, scope, coverage, and runtime-compatibility findings. For
an active local profile, use `agent-caravan resolve` to resolve that profile.
These paths validate different scopes. Review unresolved or degraded
conditions and the relevant specifications in `resources/specifications/`.

**Does not enforce:** resolution checks declared composition, not the truth or
freshness of external knowledge, repository access, or unobserved runtime
capabilities. The CLI is a separate authoring and diagnostic path; see the
[CLI guide](getting-started.md#use-the-checkout-cli) for its supported commands.

<details>
<summary>CLI checks after authoring</summary>

There is no general CLI command for authoring these advanced artifact types.
After editing their source artifacts, resolve the active profile only when the
artifacts are connected to that profile:

```sh
agent-caravan resolve
```

For checked-in repository examples, use the repository-provided example
resolver and validator instead of treating the active local profile as proof
that the example composition is published correctly.

</details>

## Export a runtime-neutral handoff

**When to use:** preparing a structured task for another harness or operator
to receive without launching a runtime.

```text
Prepare a runtime-neutral handoff for implementing <task>, from tech-owner to
engineer. Validate it and tell me where it was exported.
```

Replace `<task>` with a specific, bounded objective and requested outcome. If
you have not set up a local Agent Caravan profile yet, start with the product
[Getting Started guide](getting-started.md).

**Expected result:** a validated, runtime-neutral handoff artifact and its
task-scoped evidence, or a clear report that this harness cannot persist the
export.

**Changed files:** the handoff artifact and related task, session, and run
evidence under the configured sessions location when persistence is available.

**Validation:** ask the assistant to validate the exported artifact against
the canonical task-handoff schema and handoff contract. Confirm task and plan
identity, role boundary, and validation status.

**Does not enforce:** export does not transport, accept, or execute the
handoff. The receiving harness owns those steps and any updated evidence. A
handoff does not grant permissions or approvals or start a live run.

<details>
<summary>CLI equivalent</summary>

With a configured default profile, the CLI generates task and handoff IDs and
uses the default sessions location. For an isolated profile, pass the same
`--root` and `--sessions-root` to both export and validation commands.

```sh
agent-caravan handoff \
  --objective "Implement the requested change" \
  --requested-action "Inspect, implement, verify, and report" \
  --sender-role tech-owner \
  --receiver-role engineer
```

</details>

## Common setup and validation problems

**When to use:** setup, resolution, or evidence checks do not match the
expected result.

Ask the assistant to diagnose a specific issue using the relevant skills:

```text
Help diagnose this Agent Caravan resolution error: <paste the message>. Explain
the smallest safe fix and how to check it.
```

| Symptom | Ask the assistant to check | Does not establish |
| --- | --- | --- |
| No active team is reported | Inspect the active profile and organization catalog; identify whether a team must be selected or created. | That a catalog automatically creates a team. |
| A team Markdown file appears unchanged | Check the active team's authoring workspace and preserve existing file content before proposing an edit. | That a separate synchronization command is needed. |
| A domain, specialization, or overlay is missing | Check stable artifact IDs, catalog publication, explicit team references, ownership, and overlay precedence. | That names or directory placement attach an artifact. |
| Resolution fails or is degraded | Explain unresolved references and capability support; identify a safe correction or permitted fallback. | That a partial result is fully compatible. |
| Session validation cannot find evidence | Check that the same profile, task ID, and sessions location are used. | That profile resolution checks session files. |
| Dry-run output is mistaken for a live task | Explain the execution realization and identify the selected harness for real work. | That a model or external system was called. |
| The task uses the wrong team | Inspect the active profile and confirm `organization_id`, `team_id`, blueprint, and runtime mapping before planning. | That a team mentioned in a prompt overrides an ambiguous profile. |
| Native workers are not visible | Check the runtime execution mode and whether worker references were reported. | That a role name alone proves delegation. |
| Reasoning settings are unclear | Review requested values, dispatch status, and telemetry status in the evidence. | That a requested level was effective when telemetry is unavailable. |

**Expected result:** the problem is tied to a specific profile, artifact,
reference, or evidence path, with a bounded next step.

**Changed files:** diagnosis is read-only. Follow-up edits should be limited
to the affected local profile or shared artifact and previewed before writing.

**Validation:** ask the resolver or validator to repeat the relevant check
after the correction. Mark external source or runtime behavior as unverified
when it was not checked.

**Does not enforce:** a successful check only supports the scope it reports;
it does not prove repository authorization, external source accuracy, or live
harness behavior.

<details>
<summary>CLI diagnostics</summary>

```sh
agent-caravan status
agent-caravan resolve
agent-caravan validate-session --task-id <task-id>
```

For an isolated profile, add the same `--root` and `--sessions-root` used by
the corresponding `run` command.

For product setup and package-access troubleshooting, see the [central
Agent Caravan user guide](user-guide.md) for the product workflow.

</details>
