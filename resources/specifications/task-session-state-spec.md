# Task And Session State Specification

## Purpose

Agent Caravan separates durable organizational knowledge from temporary work
state. This prevents a task conversation, generated artifact, or runtime cache
from silently becoming organization or team knowledge.

## State Layers

### Durable Knowledge

Organization, team, role, domain, specialization, overlay, runtime integration,
runtime mapping, and execution-profile artifacts. These require explicit
artifact ownership and publication.

### Task State

The task-specific objective, scope, plan, decisions, assumptions, evidence,
approvals, blockers, and requested outputs. Task state may be persisted but is
not durable team knowledge by default.

### Thread And Run State

Conversation messages, intermediate reasoning summaries, active lane state,
retry counters, tool results, and runtime checkpoints. A portable checkpoint
must retain task identity, resumability, stage position, and provenance. This
state belongs to a runtime session and may be unavailable across runs.

### Long-Term Memory

Facts or preferences intentionally promoted for reuse across tasks. Promotion
requires an explicit memory policy and must identify source, owner, scope, and
validation status. Long-term memory is not automatically equivalent to a domain
or capability knowledge.

### Artifacts

Code changes, plans, test evidence, decisions, reports, generated documents,
and external references produced by a task. Artifacts should retain provenance
back to the task and relevant handoffs.

## Promotion Rules

- task or thread state must not become durable knowledge implicitly
- generated artifacts must not become long-term memory without an explicit promotion decision
- durable knowledge changes require the normal artifact ownership and validation path
- caches and runtime checkpoints are non-authoritative
- unresolved or stale evidence must remain marked as such

## Minimum Task Record

```json
{
  "task_id": "...",
  "objective": "...",
  "selected_context": {},
  "plan": [],
  "decisions": [],
  "evidence": [],
  "approvals": [],
  "blockers": [],
  "artifacts": [],
  "status": "active"
}
```

## Session And Run Records

A session identifies one runtime interaction for a task. A run identifies one
execution attempt within that session. A retry creates a new run record rather
than overwriting the previous run.

Session records should include `session_id`, `task_id`, selected context,
runtime identity, active roles, status, and timestamps. Run records should
include `run_id`, `session_id`, `task_id`, workflow, runtime mapping,
status, attempt number, events, checkpoints, idempotency records, and available
metrics. A retry or resume creates a new run record; it must not overwrite the
prior run's evidence.

The schemas under `resources/schemas/` define the reference implementation
shape. Portable evidence, approval, and execution-event entries use the shared
contracts in `resources/schemas/execution-contracts.schema.json`. Runtime
providers may add fields but must preserve these identities and relationships.

When a workflow declares structured success criteria, the normalized completion
result may include a `workflow_assessment`. It is scoped to that task and plan,
and includes session and run IDs when available, so retries remain distinguishable.
The assessment cites identified evidence and reports unsupported criteria as
`unverified`; it is not a comparison against a prior process.

## Optional Telemetry Associations

Results, events, evidence, and run records may carry `metadata.observability`.
Its `references` array contains nonempty opaque strings; references are never
automatically fetched. Optional `correlation` may contain nonempty string IDs:
`task_id`, `session_id`, `run_id`, `plan_id`, `role_id`, `stage_id`,
`execution_profile_id`, `runtime_profile_id`, and `runtime_adapter_id`, where
available. Preserve unrelated metadata keys. Native runtime identities remain
runtime-owned and must not be substituted for Agent Caravan identifiers.
References must not contain credentials or captured content. Missing associations
are valid; persist supplied associations without imposing completion requirements.
Detailed telemetry remains separate from semantic execution evidence, and this
convention defines no storage or metric schema.

When persisting a run, adapters use available Agent Caravan identities from the
created run record to populate or reconcile correlation fields. Supplied role
and stage IDs remain available where the run record does not identify them.
Adapters retain the result's association, or the association on its `run` record
when result-level metadata does not supply one; unrelated runtime run metadata
is not copied into the adapter-created run record.
