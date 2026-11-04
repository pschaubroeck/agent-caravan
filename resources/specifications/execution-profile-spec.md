# Workflow Specification

## Purpose

An workflow defines how a selected Agent Caravan team performs a class
of work. It is optional. Organizations and teams remain valid without one, and
an workflow must not redefine role responsibilities, team governance,
knowledge ownership, or runtime capabilities.

The profile is a workflow contract. A runtime mapping decides how that contract
is realized by a specific AI runtime.

## Required Identity

Every workflow must include:

- `artifact_type`: `execution-profile`
- stable `id`
- artifact `version`
- `scope`
- `team_blueprint_id` or `team_instance_id`
- `entry_roles`
- `activation_policy`
- `topology`
- `termination`
- `escalation`

Profiles may reference reusable guardrails with `policy_ids`. Policies are
resolved and validated after role activation is composed.

An workflow may additionally include `runtime_profile_id` when it is
intended for one binding. A profile selected for a caravan must target
that instance or its caravan template.

## Reasoning Policy

Profiles may declare a runtime-neutral `reasoning_policy` for delegated role
work. The supported levels are:

- `focused`: routine, well-bounded work
- `standard`: normal implementation and analysis
- `deep`: ambiguity, architecture, risk, or quality-critical work

The policy may define a profile `default`, `role_defaults`, and
`stage_overrides`. Stage overrides take precedence over role defaults, which
take precedence over the profile default. Runtime integrations translate these
semantic levels into provider-specific controls or report the capability as
degraded when equivalent control is unavailable. The policy does not control
the coordinator's operator-selected reasoning setting.

A task may supply a same-shaped `task.reasoning_policy` override for one
execution. This is merged over the selected profile policy and is preserved in
the portable plan as task-local context.

## Activation Policy

The profile must distinguish roles that are always active from roles activated
only when a condition applies:

```json
{
  "entry_roles": ["tech-owner"],
  "activation_policy": {
    "primary_roles": ["engineer"],
    "supporting_roles": ["quality-engineer"],
    "mandatory_reviewers": ["software-architect"],
    "conditional_roles": {
      "product-owner": "product scope, UX, or acceptance criteria are unclear",
      "program-manager": "governance, dependency, sequencing, or approval work is present",
      "release-manager": "merge, pipeline, release, or promotion work is requested"
    }
  }
}
```

The absence of a role from the active set does not remove that role from the
team. It only means the role is not activated for the current task.

## Topology

Supported logical modes are:

- `sequential`: stages run in declared order
- `parallel`: independent lanes may run concurrently when the runtime supports it
- `handoff`: one role produces a structured handoff to another role
- `loop`: a stage repeats until its exit condition is met
- `coordinator`: one role coordinates other active lanes
- `coordinator-worker`: a coordinator retains task ownership while delegating bounded work
- `graph`: stages and transitions are represented as an explicit directed graph
- `group-chat`: active roles collaborate through a shared conversation boundary
- `concurrent-fanout`: independent lanes run concurrently and join at a declared barrier
- `human-gated`: execution pauses at one or more approval or information checkpoints
- `remote-agent`: work crosses an explicit external-agent or A2A boundary

Profiles may combine modes. They must declare a serial fallback when they rely
on optional parallel execution.

Profiles may also declare:

- `task_ownership`: whether the caller, receiver, application code, or bounded model routing owns the task
- `handoff_semantics`: whether a handoff transfers ownership, retains caller ownership, or varies by edge
- `supported_modes`: topology variants an adapter may select without changing team meaning

Profiles may describe bounded `work_items` inside their stages. Each item has
an ID, owning role, purpose, optional same-or-earlier-stage dependencies, and
an optional activation condition. The dependency graph must be acyclic. A
runtime schedules an item once its dependencies complete; a `not-applicable`
conditional item satisfies downstream dependencies. It should dispatch ready
items while unrelated items are waiting. A runtime may split task-specific
work further, but must retain role ownership and approval boundaries.

When a running item needs an answer from another role, record the wait against
the corresponding work item or handoff, then continue any independent ready
work. Resume only the affected item after its dependency resolves. If a runtime
cannot preserve that behavior, it follows the declared fallback and reports
the execution as sequential or unverified rather than claiming non-blocking
parallelism.

## Communication

Profiles must explicitly constrain role communication:

```json
{
  "communication": {
    "allowed_role_handoffs": [
      {"from": "tech-owner", "to": "engineer", "purpose": "implementation breakdown"}
    ],
    "broadcast_roles": [],
    "requires_structured_handoff": true
  }
}
```

Runtime support for communication does not grant additional organizational
authority. Role permissions and approval boundaries remain authoritative.

Communication should distinguish `handoff_semantics` from runtime transport.
An agent-as-tool call normally retains caller ownership; a handoff normally
transfers ownership to the receiver.

## Tool Requirements

Execution profiles may declare generic tool requirements without naming a
provider, SDK, or transport:

```json
{
  "tool_requirements": [
    {
      "id": "repository-inspection",
      "side_effect_class": "read-only",
      "permission_boundary": "selected repository",
      "approval_required": false,
      "evidence_kinds": ["tool-request", "tool-result"]
    }
  ]
}
```

Tool requirements describe expected authority and evidence. Runtime mappings
map them to native tools, MCP servers, skills, or other constructs.

## Evidence Requirements

Profiles may declare the evidence needed to complete each workflow:

```json
{
  "evidence_requirements": [
    {
      "kind": "quality-evidence",
      "required": true,
      "owner_role": "quality-engineer",
      "stage_id": "quality-and-uat"
    }
  ]
}
```

Runtime traces and provider-specific records remain runtime-owned. The adapter
should correlate available records to portable task, session, run, handoff,
approval, and completion identities. Missing optional telemetry is valid.

## Debates, Termination, And Escalation

Profiles may activate team-defined debates conditionally, but may not remove a
mandatory debate without an explicit derived-profile decision and validation.
They must define:

- entry and exit conditions for loops and debates
- successful completion conditions
- maximum iterations or retry count when looping
- unresolved-decision behavior
- escalation role and human-approval behavior
- behavior when a required runtime capability is unavailable

Profiles may supplement human-readable `termination.success_conditions` with
stable, structured `termination.success_criteria`. Each criterion has an `id`,
a concise `description`, and one or more `assessor_roles`. Keep criterion IDs
stable while their meaning is unchanged; changing a criterion's meaning
requires a profile version change. Runtime integrations carry the criteria into
the portable plan and return one evidence-linked assessment per criterion.
The framework validates declared IDs, assessor roles, role execution, and
evidence references; it does not infer whether arbitrary prose is true.

## Outputs And Evidence

Each terminal stage must identify expected outputs and evidence. A runtime may
store the result elsewhere, but the resolved execution record should identify:

- work completed
- decisions reached
- handoffs performed
- validation evidence
- approvals requested or received
- unresolved or degraded conditions

## Non-Requirements

The specification does not require a graph engine, permanent agent per role,
parallel execution, a coordinator role, a message bus, a database, or a
particular model provider.

## Optional Observability

Runtime-owned records may use `metadata.observability` to correlate available
Agent Caravan identities. Missing optional telemetry must not block execution or
conformance; only explicitly required observability invokes compatibility
requirements. Required semantic evidence remains mandatory.

Use optional `required_capabilities` (a list of nonempty capability names) to
require runtime support, including observability, for a workflow. Optional `capability_support_requirements`
maps names to minimum support levels: `native`, `adapted`, `externalized`, or
`unsupported`. Resolution checks explicit workflow requirements together
with the runtime binding, and the portable plan preserves the stronger minimum
when both declare a capability support level. Unknown required names are treated
as unsupported unless the adapter explicitly declares support. These fields do not enable a
collector; the selected implementation must provide any explicitly required
observability and its workflow-required evidence.
