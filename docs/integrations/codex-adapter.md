---
type: Reference
title: Codex Adapter Walkthrough
description: Developer guide to integrating and verifying the Agent Caravan Codex bridge.
---

# Codex Adapter Walkthrough

This guide is for developers integrating or verifying the Agent Caravan Codex
bridge. It describes preparation, execution boundaries, evidence, and
conformance.

If you want to use an existing team in Codex, start with the product
[Getting Started](../getting-started.md)
and [Running Work](../developer-examples.md#start-a-real-implementation-through-an-ai-harness)
guides. They explain assistant-led setup and execution; the Python examples
below are for bridge development.

## Contents

- [Prerequisites](#prerequisites)
- [Initialize the local profile](#1-initialize-the-local-profile)
- [Resolve the active context](#2-resolve-the-active-context)
- [Create the Codex execution brief](#3-create-the-codex-execution-brief)
- [Execute through the skill](#4-execute-through-the-skill)
- [Cross the Codex execution surface](#5-cross-the-codex-execution-surface)
- [Role-appropriate reasoning](#role-appropriate-reasoning)
- [Review the result](#6-verify-the-result)
- [Run adapter conformance](#7-run-adapter-conformance)
- [Related documentation](#related-documentation)

## Prerequisites

Start with an installed Agent Caravan package or a working source checkout.
The initialization step below prepares the local organization, team, and Codex
skills. Resolve that context before preparing an execution request. Live
execution and conformance also require a Codex execution surface that implements the boundary described in
section 5; importing the adapter does not supply that surface.

The bridge works within an ordinary Codex task. The runtime remains responsible
for native invocation and the tools available to that task.

Codex remains the initialization default. For custom destinations and upgrades,
see [skill installation examples](../reference/packaging-and-distribution.md#install-and-refresh-skills).

## 1. Initialize The Local Profile

From the cloned Agent Caravan repository:

```text
make init
```

Choose or create the organization and starter team. The checkout path uses the
same starter semantics as the package CLI and installs the required Codex
skills. For a compact first setup, the installed package can create both
boundaries together:

```text
agent-caravan init --organization "Example Organization" \
  --team "Platform Team"
```

Use the builder skill afterward for additional teams, domain knowledge,
specializations, role overlays, ownership metadata, or other advanced
configuration.

## 2. Resolve The Active Context

```text
make resolve
```

Resolution must succeed before execution. The resolved result identifies the
organization, team, effective roles, specialization, runtime integration, runtime
profile, workflow, policies, and any degraded capabilities.

## 3. Create The Codex Execution Brief

The adapter consumes the resolved result and a task objective. It produces a
Codex-facing brief, but does not execute commands or mutate remote state:

```python
from agentcaravan.adapters.codex import prepare_codex_execution

prepared = prepare_codex_execution(
    resolved,
    {"task_id": "sample-product-work-item-123", "objective": "Implement the approved enrollment change"},
)
plan = prepared["plan"]
brief = prepared["projection"]
```

Preparation validates the portable plan before producing the Codex projection.
The brief supplies role lanes, stage checkpoints, structured handoff and
completion-record requirements, approval boundaries, and capability
degradation. The Codex orchestration skill uses that brief while the user
continues working through an ordinary Codex task.

The skill should create initial records with
`agentcaravan.foundation.build_execution_records` and final evidence with
`agentcaravan.foundation.build_completion_record`. Both include the portable
`plan_id`, allowing the task, session, run, and completion evidence to be
correlated without requiring Agent Caravan to choose a persistence provider.

The brief also carries the effective `knowledge_access` policy. External
knowledge defaults to `enabled`, can be restricted to `approved_sources`, or
can be disabled. Approved sources may be written as strings or as objects with
an optional `id` and required `source`:

```json
{
  "knowledge_access": {
    "external_sources": "approved_sources",
    "approved_sources": [
      "https://git.example.org/",
      {"id": "sample-product-docs", "source": "https://docs.example.org/products/sample-product/"}
    ]
  }
}
```

This controls external knowledge retrieval only. It does not grant remote
write access, bypass connector authentication, or replace approval boundaries.

## 4. Execute Through The Skill

Invoke `agent-caravan-codex-orchestrator` for the task. It should:

1. Confirm the selected organization, team, specialization, and task boundary.
2. Conduct the solution and testability debate before implementation.
3. Use the smallest effective role set and dispatch independent role lanes to
   native Codex subagents by default.
4. Create structured handoffs and pause at approval boundaries.
5. Run quality and product-acceptance checks, then produce completion evidence.

The completion evidence must declare how role work was realized. Each native
role lane must include the runtime's opaque worker reference. If the current
Codex surface cannot create native role sub-agents, block or obtain explicit
authorization before reporting `simulated-sequential` with
`native_subagents: false`. Include concise role turns, decisions, handoffs,
verification evidence, and unresolved conditions; role names alone are not
evidence that a team workflow occurred.

When the portable plan declares `termination.success_criteria`, return a
`workflow_assessment.criteria` entry for each criterion. Each entry identifies
the declared `criterion_id`, a status (`met`, `not-met`, `unverified`, or
`not-applicable`), the `assessor_role_id`, a concise rationale, and
`evidence_refs` that resolve to identified records in the result. The framework
defaults omitted assessments to `unverified`; `status: completed` is not proof
that workflow criteria were met. Do not assess comparison with the user's
existing process.

The adapter maps framework roles onto task-scoped Codex subagents. It does not
create permanently running workers, and it does not move role meaning into
Codex-specific artifacts.

### Repository behavior and worker identity

The orchestrator should read the repository's local guidance before making
changes. `AGENTS.md`, contribution instructions, and project documentation
remain authoritative for repository behavior; the resolved team adds durable
team context around them. The orchestrator should keep changes bounded, run
focused checks, and pause for approval before remote writes or deployment.

The framework role is the portable identity. Codex worker names, display labels,
and opaque worker references are runtime details and are not guaranteed to use
the role's human-readable name. A completion report should include the worker
reference when Codex exposes it, but must not invent one when it does not.

## 5. Cross The Codex Execution Surface

The preferred runtime boundary is an explicit `CodexExecutionRequest`:

```python
from agentcaravan.adapters.codex import run_codex_conformance_suite
from agentcaravan.session_store import LocalJsonExecutionStore

suite = run_codex_conformance_suite(
    resolved,
    scenarios,
    live_codex_surface,
    store=LocalJsonExecutionStore("~/.agents/agent-caravan/sessions"),
)
```

`live_codex_surface` implements `execute(request)` and owns Codex-native task
invocation, routing, pauses, and runtime traces. Agent Caravan owns the request
envelope, task/session/run identity, portable result normalization, and
conformance comparison. The local store is optional and records only bounded
task, session, run, and normalized completion payloads; it does not store
credentials, hidden reasoning, or unbounded transcripts.

The same boundary is available as a safe operator smoke test:

```text
agent-caravan run --dry-run \
  --objective "Demonstrate the configured feature-delivery flow"
```

The command generates a readable task ID when `--task-id` is omitted, uses the
active profile, stores records under its local `sessions/` directory, and
validates the persisted evidence before returning success. A stable external
ID can still be supplied with `--task-id`. It is intentionally not a live
Codex launcher; use the `agent-caravan-codex-orchestrator` skill for actual
implementation work.

For a harness-neutral task transfer, the foundation also exposes
`build_task_handoff` and the CLI provides `agent-caravan handoff`. The command
derives a validated handoff from the portable execution plan, includes the
selected team/runtime context and next action, persists it with existing
session evidence, and returns the persisted artifact as `handoff_path` along
with its enclosing `session_path`. It does not invoke Codex or any other
runtime.

## Role-Appropriate Reasoning

Execution profiles may declare runtime-neutral reasoning levels: `focused`,
`standard`, and `deep`. The portable execution plan resolves these by role and
stage. The Codex projection maps them to `low`, `medium`, and `high` reasoning
effort respectively when native control is available.

The policy precedence is stage override, role default, then profile default.
These settings apply to delegated role workers; the coordinating task keeps
the operator-selected reasoning setting. If a runtime cannot control worker
reasoning effort, the adapter must report that capability as degraded instead
of claiming the requested setting was applied.

Execution evidence records the requested semantic level, the mapped Codex
value, dispatch acceptance, and the effective value when the runtime reports
it. A delegated worker with an opaque runtime reference is recorded with
`dispatch_status: accepted`, while its reasoning remains
`telemetry_status: unverified` unless the runtime directly reports the
effective setting. Dry runs remain `dispatch_status: not-attempted`.

Agent Caravan does not parse private Codex diagnostic logs to fill this gap.
Those logs can be useful for local troubleshooting, but they are not portable
runtime evidence and are not part of the adapter contract.

The `agent-caravan run` JSON summary exposes this as a bounded
`reasoning_evidence` array containing stage and role identity, requested
semantic and runtime values, evidence status, dispatch status, telemetry
status, and an opaque `worker_ref` only when one is available. It does not
include hidden reasoning, prompts, transcripts, or private runtime logs.
When a runtime reports only part of the prepared plan, normalization adds the
unreported assignments as `unverified` plan projections in plan order; this
keeps missing telemetry visible without treating it as observed execution.

Execution topology is profile-driven. Stages remain ordered, and only lanes
listed in `execution_topology.parallel_lanes` may run concurrently. If parallel
lane execution is unavailable, follow `serial_fallback.lane_ids` in order.
When reporting `native-parallel`, include a
`parallel_lane_evidence` entry for each dispatched lane role, mapping its lane
ID, stage, role, and opaque worker reference. The normalizer derives the
`parallel_lane_ids` summary and checks those entries against the declared
topology and matching role turns. The result records topology conformance; a
parallel run without this lane-to-worker telemetry is marked unverified rather
than assumed to match the plan. To verify that distinct lanes actually
overlapped in execution, include timezone-aware `started_at` and `completed_at`
timestamps on the lane evidence. The separate `parallel_timing_conformance`
verdict is `pass` only when at least two lane intervals overlap; missing timing
is `unverified`, non-overlapping or invalid timing is `failed`, and non-parallel
runs are `not-applicable`. If no runtime dispatch or worker turns occurred,
`topology_conformance` is also `not-applicable`; it does not report a pass for a
task that never ran. This keeps lane authorization and worker identity
distinct from proof of concurrent execution. CLI `agent-caravan run --debug --dry-run` opts
into a concise dispatch trace. Debug
output is omitted by default and excludes prompts, transcripts, and hidden
reasoning. It also reports preferred role IDs separately from plan assignments
and observed role turns; preferences are guidance and do not themselves change
role activation.

## 6. Verify The Result

The task should leave evidence under:

```text
~/.agents/agent-caravan/sessions/<task-id>/
```

At minimum, the completion record should identify the selected context,
decisions, handoffs, approvals, changed artifacts, validation evidence,
degraded capabilities, and unresolved conditions.

Validate the persisted evidence before treating the task as complete or
resuming it after an interruption:

```text
agent-caravan validate-session --task-id sample-product-work-item-123
```

This is a read-only integrity check. It catches missing files, malformed JSON,
and task/session/run/plan identity drift without making Agent Caravan
responsible for the underlying storage provider.

## 7. Run Adapter Conformance

The Codex bridge supplies the projected brief to the execution surface and
normalizes its returned result against the portable execution-result contract:

```python
from agentcaravan.adapters.codex import run_codex_conformance_suite

suite = run_codex_conformance_suite(resolved, scenarios, execute_codex_scenario)
suite.raise_for_failures()
```

`execute_codex_scenario` remains supported as a compatibility callback. New
execution surfaces should implement `execute(request)` and consume the
explicit `CodexExecutionRequest` described above.

For ordered conformance assertions, return portable `execution_events` with
timezone-aware timestamps, evidence references, and the task and run IDs from
`request.records`. The adapter adds those Agent Caravan-owned task, session, and
run IDs to the normalized result. Preserve any Codex-native task, run, and trace
identifiers as runtime metadata or evidence references; do not substitute them
for the portable IDs. An event that cannot be attributed to the current task
and run, or cannot be tied to evidence, cannot satisfy a conformance assertion.
The shared case definition and assertions remain runtime-neutral.

## Related Documentation

- [Runtime integration contract](../reference/runtime-integration.md) for portable runtime boundaries.
- [OpenCode adapter integration](opencode-adapter.md) for a second runtime binding.
- [Codex and OpenCode comparison](codex-opencode-comparison.md) for recorded conformance results.
