# Portable Execution Plan Specification

## Purpose

A portable execution plan is the runtime-neutral handoff between resolved
Agent Caravan semantics and a concrete execution runtime. It describes what
must happen, which organizational roles are responsible, and which controls
and evidence apply. It does not describe how a runtime implements the work.

The plan is produced from a resolved organization, team, workflow,
and task. It is suitable for Codex, workflow engines, hosted agent products,
or a sequential human-assisted runtime.

## Runtime-Neutral Boundary

A portable plan must not contain runtime-specific agents, prompts, skills, MCP
servers, graph nodes, runtime integration objects, or storage paths. Runtime
adapters may add those details in their projections. Organization-specific
systems such as work trackers and source-control platforms may appear only as
generic references or scoped extensions; the foundation does not interpret
their provider-specific behavior.

The intended flow is:

```text
resolved Agent Caravan profile -> portable execution plan -> runtime adapter
```

## Required Shape

Every plan must include:

- `artifact_type`: `portable-execution-plan`
- stable `id`, `version`, and `scope`
- task identity and objective
- resolved organization, team, blueprint, and workflow identity
- role assignments with participation semantics
- ordered or conditional execution steps
- structured handoff communication rules
- policy and approval requirements
- completion and termination requirements

Plans may also include `knowledge_context.layers`, an ordered shared list of
selected domain and capability knowledge. Each layer carries its artifact
identity and version, plus any portable purpose, knowledge surface, trusted
source references, loading guidance, and role-specific guidance supplied by
the artifact. Domain layers precede team specialization layers. The plan keeps
these shared layers once; adapters make them available to assigned roles and
apply `role_guidance` only to its matching role.

Any artifact may provide explicit `documentation_references` with a URI and
optional media type, title, and purpose. Selected domain and specialization
references are carried on their knowledge layers. Role references are carried
on the matching `role_assignments` entry alongside its `source_chain`, which
identifies the role lineage that contributed the guidance, and `role_version`,
which identifies the effective role version. References preserve provenance
but do not contain document content. Adapters must treat them as
supplemental and retrieve them only when allowed by `policy.knowledge_access`;
they must not fetch arbitrary URLs automatically or let Markdown override the
machine-readable artifact contract.

`context.team_context.knowledge_sources` remains a separate supplemental list.
Adapters apply it after the selected pack layers, preserving its declared
order; it is not copied into `knowledge_context`.

Knowledge layers carry curated guidance and source references, not copies of
the referenced documents. Adapters must honor `policy.knowledge_access` when
retrieving external sources. `knowledge_context` is optional so consumers can
continue to read plans created before it was introduced.

Tasks may include generic external references, metadata, and namespaced
extensions. A reference identifies a `system_type`, `reference_type`, and
opaque `identifier`; it does not require the foundation to know which product
provides that system. Organization profiles may attach provider-specific
details in metadata or extensions and enforce their own policies there.

## Execution Steps

Steps are semantic instructions, not runtime nodes. Supported step kinds are:

- `task`: work performed by one or more roles
- `message`: structured communication between roles
- `handoff`: transfer of responsibility and evidence
- `artifact`: expected production or review of an artifact
- `state-update`: update to task, session, or run state
- `tool-request`: request for an external capability
- `approval-request`: request for human or policy approval
- `result`: successful work output
- `failure`: unsuccessful work output or blocked condition
- `completion`: terminal evidence and status

The initial projection may represent workflow stages as `task` steps. Adapters
must preserve their order, role ownership, conditions, and expected outputs.

## Capability Negotiation

The plan may declare generic required or preferred capabilities. The runtime
adapter evaluates those requirements and reports native, adapted,
externalized, or unsupported behavior. Degradation must never be silently
discarded from the runtime result.

When a workflow requires a minimum capability level, the plan carries
`capability_requirements.support_levels`. For example, a plan that requires
independent role workers can declare `parallel_lane_execution: native`.
Runtime-specific worker IDs and dispatch transports remain outside the plan;
the adapter records them only in its projection and execution evidence.

## State And Evidence

The plan defines required evidence and completion outputs but does not require
a database, checkpoint store, message bus, or durable runtime. The selected
runtime may externalize state and evidence while preserving task, session, run,
handoff, approval, and artifact identity contracts.

The plan may carry structured `termination.success_criteria`. If present, the
normalized result includes a `workflow_assessment` tied to the task and plan,
and to the session and run when available. Each criterion is `met`, `not-met`,
`unverified`, or `not-applicable`, with a rationale and references to
identified execution evidence. Missing assessments remain `unverified`;
unresolved conditions, degraded execution, or a non-completed run prevent an
aggregate `met` result. This report evaluates the selected team workflow for
that execution. Comparative value against another process requires a
user-defined baseline and is outside this contract.

## Execution Topology And Tool Requirements

Plans may carry the resolved execution topology as a runtime-neutral object.
The topology describes sequencing, ownership, handoff, concurrency, graph, or
human-gated behavior without naming a runtime implementation.

Topology may include bounded `work_items` with stable IDs, an owning role,
stage, purpose, dependencies, and an activation condition. Dependencies must
reference declared items, point to the same or an earlier stage, and form an
acyclic graph. An item with no unresolved dependencies is ready. Conditional
items reported `not-applicable` satisfy their downstream dependencies.
Adapters should schedule ready work without waiting for unrelated items. If a
running item needs an answer, the coordinator records the dependency wait,
continues other ready items, and resumes only the affected work when the answer
arrives. Runtime capability limits may require sequential fallback; the receipt
must report the actual realization.

`execution_events` may record `kind: work-item` lifecycle events with the
`work_item_id`, `role_id`, `stage_id`, dependency IDs matching the planned item,
and an optional `worker_ref`. Each event declares `evidence_source` as
`adapter-observed`, `runtime-receipt`, `agent-reported`, or `simulated`; a
`runtime-receipt` includes at least one `evidence_refs` entry. A timestamp
should accompany each event when the harness exposes one. Supported states are
`queued`, `started`, `waiting`, `resumed`, `completed`, `not-applicable`,
`failed`, and `cancelled`. These
bounded records support wait-duration and scheduling checks without capturing
prompts, hidden reasoning, or tool payloads. Missing or unattributable
timestamps leave timing unverified. Agent Caravan validates the declared source
and event sequence; it does not independently establish that an adapter's
observation or receipt is authentic. Scheduling conformance is `pass` only when
the complete lifecycle is timestamped and all events are adapter-observed or
tied to runtime receipts. Agent-reported and simulated timelines can support
contract tests but remain `unverified` as runtime evidence.

Plans may also carry generic `tool_requirements` and `evidence_requirements`.
Tool requirements describe side-effect class, permission boundary, approval,
usage limits, and expected evidence. Evidence requirements identify the proof
needed for a stage or completion condition. Provider-specific tool names,
transports, traces, and storage paths remain runtime-profile concerns.

## Extension Rules

Organizations and teams may derive plans with additional steps, role
assignments, policies, and outputs. A derived plan must preserve required role
coverage, mandatory approvals, and completion evidence unless an explicit
validated policy allows the change.
