---
name: agent-caravan-opencode-orchestrator
description: Execute bounded implementation work through an active Agent Caravan team in OpenCode, preserving the portable plan, role handoffs, approval boundaries, and execution evidence.
---

# Agent Caravan OpenCode Orchestrator

In user-facing terminology the configured team is a caravan and each framework
role is a responsibility. The execution contract still uses `role` in artifact
types, field names, and role-turn evidence; retain those identifiers.

## Runtime boundary

Use this skill only in an OpenCode harness with a resolved
`opencode-agent-runtime` adapter. If the active team uses another runtime,
report the mismatch before writing execution records or dispatching workers.
Select or create a matching team explicitly; skill discovery cannot change its
runtime mapping. Codex work uses `agent-caravan-codex-orchestrator`.

Agent Caravan owns organizational meaning, portable plans, role assignments,
approval criteria, and normalized evidence. OpenCode owns agent configuration,
native tools, sessions, permissions, and provider/model selection. Installing
this skill grants no permissions and creates no native agents. Do not change
OpenCode permission or provider configuration merely to make a task run.

## Discover and prepare

Inspect repository guidance and the active Agent Caravan profile with
`agent-caravan status`, `agent-caravan resolve`, and `agent-caravan validate`.
Load the shared resolver or validator skill through the native OpenCode
`skill` tool when needed. Check team identity, knowledge scope, runtime mapping,
role coverage, and capability degradation before implementation.

Use `runtime.repository_guidance` from the resolved configuration to select
repository instruction files and follow its discovery and reference policies.
Profile-local adapter overrides take precedence over packaged defaults. Read
declared files explicitly when OpenCode does not load them automatically.

Prepare the task using the installed package and the resolved configuration:

```python
from agentcaravan.adapters.opencode import prepare_opencode_execution

prepared = prepare_opencode_execution(resolved, task)
plan = prepared["plan"]
projection = prepared["projection"]
```

The task must satisfy the shared task contract. Preserve the portable plan and
use the projection for OpenCode instructions. Preparation does not execute a
runtime: its execution realization remains unreported until dispatch evidence
exists. `agent-caravan run --dry-run` is a Codex projection command; do not use
it to prepare OpenCode work. `agent-caravan handoff` can persist a portable
handoff without launching a runtime.
Inspect `agent-caravan handoff --help` for its task and role arguments.

When `projection.knowledge_context.layers` is present, provide those shared
layers to every assigned role in their declared order. Then provide
`projection.supplemental_knowledge_sources` in list order. Apply each layer's
`role_guidance` only to the matching role. Treat `trusted_sources` as
references; retrieve them only as permitted by `projection.knowledge_access`.
Keep shared layer content common to the team rather than copying it into
individual role instructions. This projection describes the portable contract;
it does not establish that a live OpenCode harness has been verified to enforce
it.

## Execute bounded role work

Explain the objective, participating roles, file ownership, ordered stages,
work-item dependencies, and focused verification. Schedule ready work items
without waiting for unrelated items. If an item needs another role's answer,
record the dependency wait and continue independent ready work; resume the
affected item when the answer arrives. Follow the plan's serial fallback when
the selected runtime cannot do this. Map roles to available OpenCode agents
and native subagent/session tools only when the selected runtime and live
surface support them. Keep reviewers independent when the plan requires it.
Never invent an agent, tool, child session, or provider/model capability.

Retain observed session and worker references, role turns, work-item lifecycle
events, handoffs, tool results, approval decisions, and verification evidence.
Record conditional items that do not apply as `not-applicable` when that state
is observable.
A role label alone does not prove delegation; parallel execution also needs
overlapping dispatch intervals, and wait duration needs attributable
waiting/resumed timestamps. Requested reasoning levels are distinct from
observed settings.
Do not infer effective reasoning from output or hidden runtime logs.

Stop at unresolved identity, required unsupported capability, missing approval,
or failed mandatory gate. Obtain the task-authorized decision before a
protected action; do not auto-accept native permission requests. Preserve user
changes and run only the verification appropriate to the authorized task.

If a caller supplies an `OpenCodeExecutionSurface` implementing
`execute(request)`, `agentcaravan.adapters.opencode.run_opencode_task` can
execute and normalize the prepared task with an optional execution record
store. A skill installation does not supply this live binding. Within an
ordinary OpenCode session, use the actual native surface and disclose any
missing normalization or persistence rather than fabricating receipts.

## Completion evidence

Report the objective and changed files, planned and completed role work,
observed worker/session references and handoffs, approval outcomes, checks and
results, persisted evidence locations, and degraded or unverified conditions.
Distinguish a prepared plan from executed work. Persist bounded evidence only
when the active surface permits it; otherwise include it in the result and
state the persistence limitation. Exclude credentials, hidden reasoning, and
unbounded transcripts.

When the portable plan declares `termination.success_criteria`, include one
assessment for each criterion in the normalized result, using its declared ID
and assessor role, a status (`met`, `not-met`, `unverified`, or
`not-applicable`), a concise rationale, and evidence references that resolve to
identified result records. Leave missing or unsupported assessments
unverified. Runtime completion alone does not establish workflow success, and
the assessment does not compare Agent Caravan with a user's prior process.
