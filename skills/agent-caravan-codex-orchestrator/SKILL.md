---
name: agent-caravan-codex-orchestrator
description: Help implementors use an active Agent Caravan team for bounded implementation work in Codex. Use when discovering the active team, inspecting repository guidance, coordinating role debates and native subagents, enforcing quality and approval gates, or producing execution evidence.
---

# Agent Caravan Codex Orchestrator

## Purpose

Use this skill as the Codex-facing entry point for executing work through an Agent Caravan team. Preserve the framework's organization, team, role, knowledge, debate, approval, quality, and release boundaries while allowing the user to continue using normal Codex task workflows.

This skill orchestrates. It does not redefine roles, resolve artifact composition itself, or grant permissions.

In user-facing terminology the configured team is a caravan and each framework
role is a responsibility. The execution contract still uses `role` in artifact
types, field names, and role-turn evidence; retain those identifiers.

## AI-First Implementation Workflow

The normal implementor experience is a natural-language request to the active
AI harness. The implementor should not need to learn Agent Caravan CLI commands
to use a configured team.

A canonical request is:

```text
Use my active Agent Caravan team to implement this change.

First inspect the active team context and repository guidance. Explain which
roles will participate and why. Create a bounded implementation plan, delegate
the appropriate roles, make the smallest useful change, run focused tests, and
report the completed workflow, handoffs, persisted evidence, and any
unverified conditions. Do not claim runtime behavior that cannot be verified.
```

For this workflow:

1. Discover the active profile, team Markdown context, repository guidance, and
   requested repository or product boundary before planning.
2. Resolve and validate the selected Agent Caravan configuration. Stop on
   ambiguous identity, missing coverage, unsupported capabilities, or unsafe
   permission boundaries.
   Read `runtime.repository_guidance` from the resolved configuration. Use its
   `native_files`, `discovery`, and `reference_policy` values when inspecting
   repository instructions; profile-local adapter overrides take precedence
   over packaged adapter defaults. If the harness does not load a declared
   file automatically, read it explicitly.
3. Explain the bounded objective, participating roles, file ownership, and
   focused verification before implementation.
4. Follow the portable plan's execution topology. Keep stages ordered, and
   parallelize only explicitly declared lanes; when parallel execution is
   unavailable, use the declared serial fallback. Skip unrelated roles rather
   than activating the whole team.
5. Implement the smallest useful change, preserving repository guidance and
   user changes.
6. Run focused tests, then broader gates when appropriate to the change.
7. Return a concise completion report with the evidence and limitations below.

When the portable plan declares `termination.success_criteria`, assess every
criterion in the normalized result with its declared ID and assessor role, a
status (`met`, `not-met`, `unverified`, or `not-applicable`), a concise
rationale, and resolvable evidence references. Leave unsupported or missing
assessments unverified. Runtime completion alone does not establish workflow
success, and this report does not compare Agent Caravan with a user's prior
process.

The role workflow is runtime-neutral at the plan level. Native worker names,
reasoning settings, delegation APIs, and instruction projection belong to the
selected runtime integration. Never claim native delegation, effective reasoning,
or durable persistence when the runtime did not provide evidence for it.

### Required implementor report

The final report must identify:

- the objective and files changed;
- planned roles and roles actually delegated;
- completed role turns, worker references, and role-to-role handoffs when
  available;
- tests and verification gates that ran, including results;
- team guidance that influenced the work;
- persisted task, session, plan, run, and completion evidence;
- degraded, unresolved, or unverified conditions; and
- the next action or human decision required.

For a read-only or no-change task, report that no implementation occurred. Do
not present projected role participation as completed delegated work.

## Runtime Boundary

Use this entry point only in a Codex harness with the resolved
`codex-agent-runtime` adapter. OpenCode also discovers `~/.agents/skills/`;
discovery of this skill there does not make it an OpenCode entry point. In
OpenCode, use `agent-caravan-opencode-orchestrator` with a matching active team.
If the harness and resolved adapter disagree, stop before creating execution
records or dispatching workers and report the mismatch.

- Agent Caravan artifacts define organizational meaning.
- `agent-caravan-resolver` determines the effective configuration.
- `agent-caravan-validator` checks artifact and resolved-view integrity.
- This skill maps the resolved configuration onto Codex agents, skills, tools, prompts, and task handoffs.
- Codex capability limits, approvals, and native versus externalized behavior come from the selected Codex runtime integration and runtime mapping.

Do not claim parallel execution, durable memory, remote mutation, or autonomous delegation unless the active Codex surface and runtime mapping actually provide it.

Every orchestrated task must declare its execution realization in the
completion receipt. Use task-scoped native subagents for role assignments when
available, but do not infer parallel execution from subagent availability. In
the current Codex surface, use the native subagent tools
(`multi_agent_v1__spawn_agent`, `multi_agent_v1__wait_agent`, and
`multi_agent_v1__send_input`) only in the topology-authorized batches. Dispatch
the declared serial fallback in order when parallel execution is unavailable.
Use `native-parallel` or `native-sequential` only after dispatch evidence
supports it. Do not use `create_thread` for role lanes; that creates a
user-owned task rather than a subagent.

Execution diagnostics are off by default. Include them only when the task
explicitly requests Agent Caravan debug/diagnostic output; report role/stage,
dispatch status, worker reference when available, preferred-role guidance and
actual plan assignments, planned lanes, observed execution mode, and topology
conformance. Treat preferred roles as guidance, not proof of why a role was
selected. Never include prompts, transcripts, or hidden reasoning in diagnostics.

When reporting `native-parallel`, include one
`execution_realization.parallel_lane_evidence` entry per participating lane
role, with its `lane_id`, `stage_id`, `role_id`, and opaque `worker_ref`. The
normalizer derives `parallel_lane_ids` and checks each entry against the plan
and matching role turn. Do not claim a lane ran in parallel without this
lane-to-worker evidence.

If native subagent tools are unavailable, do not represent one agent's role
perspectives as independent subagents. Follow the profile's supported fallback
or report the task blocked when no fallback is declared.

## Context Selection

Select context in this order:

1. Explicit organization, team, role, runtime, or specialization named by the user.
2. Explicit task-local context supplied in the current request.
3. Active context in `~/.agents/agent-caravan/config.json`.
4. A clearly documented repository or project default.

Do not discover arbitrary files under `~/.agents/agent-caravan/` and treat them as active artifacts. Source selection must be explicit. If required context is ambiguous, state the candidates and ask for clarification before execution.

## Orchestration Workflow

### 1. Establish The Execution Boundary

- Identify the requested outcome, repository or product boundary, and intended role lane.
- Determine whether the request is planning, implementation, review, verification, release, or framework maintenance.
- Identify actions that would mutate local, remote, deployment, production, Jira, Confluence, GitLab, or runtime state.
- Keep task-local facts separate from durable organization or team knowledge.

### 2. Resolve And Validate

- Load the active implementation profile from `~/.agents/agent-caravan/config.json`
  when no task-local context is supplied. The profile's `sources` entries are
  explicit artifact files or directories; do not scan arbitrary local files.
- Invoke or follow `agent-caravan-resolver` to resolve the selected organization, team, roles, domains, specializations, overlays, runtime integration, and runtime mapping.
- Invoke or follow `agent-caravan-validator` before runtime execution when the configuration is new, changed, organization-shared, or runtime-production scoped.
- Stop on unresolved required references, missing role coverage, ambiguous overlays, unsupported required capabilities, or unsafe permission boundaries.
- Record degraded or unverified conditions instead of silently compensating for them.

### 2A. Create Runtime State

Before creating runtime records, prepare the task through the installed
Agent Caravan package. The portable plan is the execution boundary; do not
reconstruct role activation or workflow stages directly in a Codex prompt:

```python
from agentcaravan.adapters.codex import prepare_codex_execution

prepared = prepare_codex_execution(resolved, task)
plan = prepared["plan"]
codex_brief = prepared["projection"]
```

The portable `plan` must remain runtime-neutral. Use `codex_brief` only for
Codex instructions and delegation. Generic task references, including Jira or
GitLab references, remain task context; Agent Caravan core does not interpret
their provider APIs.

When an workflow is selected, create concise runtime records under:

```text
~/.agents/agent-caravan/sessions/<task-id>/
  task.json
  session.json
  runs/<run-id>.json
  handoffs/
  artifacts/
  completion.json
```

- `task.json` records the objective, selected context, plan, decisions, evidence, approvals, blockers, and produced artifacts.
- `session.json` records the runtime interaction, active roles, execution
  realization, concise role turns, and structured handoff summaries.
- Each attempt gets a new `runs/<run-id>.json`; retries must not overwrite prior run evidence.
- Do not store credentials, hidden reasoning, or unbounded transcripts in these records.
- If the runtime cannot write local session files, emit the same structured records in the task result and disclose the degraded persistence mode.

Use `build_execution_records` for the initial task, session, and run records so
each record carries the portable `plan_id`. Use `build_completion_record` for
the final completion evidence so the result remains traceable to the same
plan. These helpers return dictionaries; the Codex runtime decides where and
how to persist them.

### 3. Run The Technical Breakdown

Before implementation, coordinate the required `solution + testability debate`:

- `product-owner`: product intent, user outcome, UX, acceptance criteria
- `tech-owner`: technical approach, decomposition, feasibility, implementation ownership
- `quality-engineer`: testability, automation, TDD strategy, quality risks, UAT approach

Activate `software-architect` when a cross-system change, architectural guardrail departure, structural risk, or material maintainability tradeoff is present. Until then, continue independent scope, technical breakdown, and quality-preparation work without waiting for architecture input. The product-owner should challenge product outcomes and UX, not dictate technical implementation; the tech-owner owns the routine technical solution.

Do not begin implementation until the debate produces a viable direction or the user explicitly accepts an unresolved decision.

Dispatch one bounded subagent for each independent participating role lane.
Record one concise role turn for each lane with the role, stage, status,
summary, and opaque `worker_ref` returned by the runtime. A role turn must not
contain hidden reasoning or an unbounded transcript. When a worker reference
is returned, execution evidence should record dispatch acceptance separately
from effective runtime telemetry. Do not infer effective reasoning from the
worker output or from private runtime logs. Record the resulting decision
separately.

### 4. Route Execution

Use the narrowest effective role lane while preserving supporting roles:

- `program-manager`: intake, dependencies, security-review routing, process obligations, follow-up
- `product-owner`: product scope, UX, acceptance criteria, UAT input
- `tech-owner`: technical breakdown, implementation coordination, technical pushback
- `engineer` or role variant: implementation and code-adjacent documentation
- `quality-engineer`: test strategy, automation, verification, quality evidence, UAT support
- `software-architect`: structural review and architecture decisions
- `release-manager`: merge request, pipeline, release, and promotion mechanics

Use native subagents for role assignments when supported. Send only the
resolved role instructions, task boundary, relevant evidence, and expected
output to each lane. Integrate results at their declared dependency or gate,
not at an unrelated batch boundary. Use parallel native subagents only when
the portable plan explicitly authorizes them. Preserve the coordinator's
approval and permission boundary across every lane.

#### Codex native delegation procedure

For this Codex adapter, native subagent delegation is the default execution
path:

1. Read `brief.capability_requirements.support_levels` and confirm the
   selected runtime satisfies the native delegation requirement.
2. Build one bounded prompt per independent role lane. Include only the task
   boundary, resolved role instructions, relevant evidence, allowed tools,
   expected structured output, and explicit read/write limits.
   Select the lane's reasoning setting from `brief.reasoning_assignments` for
   the current stage and role. Pass the projected `codex_reasoning_effort` to
   the native spawn call when supported. The coordinator's own reasoning
   setting is not changed by this policy.
3. Call `multi_agent_v1__spawn_agent` in the same delegation batch only for
   lanes the portable plan explicitly authorizes to run in parallel. Dispatch
   other roles sequentially. Keep each lane's file ownership and side-effect
   scope explicit.
4. Schedule ready portable work items. Do not wait for an entire lane batch
   when unrelated work is ready: record a lane or work-item wait against its
   dependency, continue other ready work, and resume only the affected item
   after the dependency resolves. Use `multi_agent_v1__wait_agent` when no
   useful ready work remains or when a required gate blocks all remaining work.
   Follow the declared serial fallback when parallel scheduling is unavailable.
5. Record the returned agent ID as the role turn's opaque `worker_ref`; record
   only a bounded summary, status, evidence references, and structured output.
6. Convert each completed lane into a portable role turn and handoff. The
   coordinator remains responsible for merging results, resolving conflicts,
   approvals, and final verification.

When the plan includes `execution_topology.work_items`, dispatch only items
whose dependencies are complete or not applicable. Record `kind: work-item`
events for `queued`, `started`, `waiting`, `resumed`, `completed`,
`not-applicable`, `failed`, or `cancelled` states as they occur. Include the
work item, role, stage, dependency references, worker reference, and timestamps
when exposed by the runtime. Do not claim
non-blocking scheduling or measured wait duration without attributable event
evidence. Keep other ready items moving while a role awaits an answer.

Do not use `create_thread` or `fork_thread` as a substitute for subagents.
Those APIs create or copy user-facing Codex tasks and do not establish the
native worker contract required by this adapter.

### 5. Resolve Review Disagreement

When review feedback is disputed or materially changes the solution, run the `review resolution debate`:

- `engineer`: implementation consequences and concrete alternatives
- `tech-owner`: delivery feasibility and technical tradeoffs
- `software-architect`: structural integrity and long-term fit

Do not blindly apply review comments. Converge on a viable solution, document the decision, and then implement or reject the feedback with evidence.

### 6. Apply Quality And Release Gates

- Involve `quality-engineer` during technical breakdown, not only after development.
- Require verification evidence appropriate to the change.
- Treat product-owner UAT as product acceptance; do not replace it with technical testing.
- Route new dependencies or integrations through `program-manager` security/governance handling.
- Keep release, deployment, and remote mutations behind the selected approval boundary and `release-manager` lane.
- Never infer permission from a role name alone.

For every role-to-role transfer, create a handoff record containing the handoff
and task identifiers, sender and receiver roles, objective, requested action,
inputs, expected outputs, evidence, validation status, unresolved questions,
approvals, blockers, and status. Use
`resources/schemas/handoff.schema.json` as the reference shape. A handoff does
not authorize remote, destructive, release, deployment, or production actions.

## Debate Escalation

Add the following debates when triggered:

- `scope debate`: product-owner and tech-owner when outcome and implementable scope conflict
- `risk debate`: quality-engineer, tech-owner, and software-architect for material delivery, quality, structural, or operational risk
- `priority debate`: program-manager, product-owner, and tech-owner for sequencing or timing conflicts
- `technical debt debate`: engineer, tech-owner, product-owner, and software-architect for shortcuts or deferred cleanup

Debate is a decision mechanism, not ceremony. Keep the record concise: question, competing options, decision, rationale, owner, and follow-up.

## Knowledge Loading

Load durable context in this order:

1. organization catalog and caravan
2. core caravan template and effective roles
3. broad domain knowledge
4. team-owned capability knowledge
5. explicit local overlays
6. task-local repository, Jira, Confluence, SharePoint, chat, email, or environment evidence

When the portable plan includes `knowledge_context.layers`, make every layer
available to all assigned roles in its declared order. Apply
`context.team_context.knowledge_sources` afterward in its listed order. Apply
each layer's `role_guidance` only to its matching role, and follow
`policy.knowledge_access` when retrieving trusted sources. Do not copy shared
knowledge into each role definition.

Prefer authoritative repository instructions and architecture sources over volatile notes. Do not promote task-local discoveries into durable knowledge without an explicit artifact change.

## Completion Record

At the end of an orchestrated task, report:

- task ID, session path, session ID, plan ID, and run IDs from the persisted
  execution records
- selected organization, team, role lane, runtime integration, and runtime mapping
- debates held and decisions reached
- artifacts or code changed
- quality and validation evidence
- approvals requested or received
- unresolved, degraded, or unverified conditions
- execution realization, native-sub-agent availability, role turns, decisions,
  handoffs, and verification evidence
- follow-up owned by program, product, technical, quality, architecture, or release lanes

Update the task, session, and run records with final status, timestamps,
decisions, handoffs, approvals, changed artifacts, validation evidence, and
degraded or unresolved conditions. Write `completion.json` or emit the
equivalent structured result. Completion evidence is task state, not durable
organization knowledge; promoting it into a domain, specialization, role,
policy, or other shared artifact requires an explicit builder workflow.

The final response must surface the persisted task metadata directly. Do not
make the user search the filesystem or infer an Agent Caravan task ID from the
Codex task ID. If records could not be persisted, say so explicitly and emit
the structured result instead.

A resolved configuration or task result is not authorization to perform a release, deployment, production, or remote mutation.

## Failure Behavior

- Stop when required identity, coverage, permission, or runtime capability cannot be resolved safely.
- If initialization has only created an organization catalog and no team is
  active yet, stop and route the user to `agent-caravan-builder` for team
  creation rather than inventing a team.
- Ask before choosing between multiple organizations, teams, specializations, or runtime mappings.
- Use only a fallback declared by the profile when Codex lacks native orchestration; otherwise block and disclose the limitation.
- Never silently substitute a personal skill, agent, profile, or prompt for a declared runtime mapping.
