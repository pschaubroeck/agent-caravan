# Handoff Contract Specification

## Purpose

A handoff is the portable unit of work transferred between activated roles or
runtime lanes. It makes role transitions and task execution transfers
inspectable without requiring a particular agent framework, message bus, or
orchestration engine.

Agent Caravan distinguishes two contracts:

- A **role handoff** is a lightweight transfer between a sender role and a
  receiver role. It describes the bounded request and its immediate inputs,
  outputs, validation, and status. It does not carry the complete execution
  plan or selected runtime context.
- A **task handoff** is a complete task-scoped execution artifact. It carries
  task and plan identity, selected context, role assignments, execution
  topology, capability requirements, blockers, and the role-to-role request.
  It is the contract used when a receiver is taking over execution of a
  portable task plan.

The machine-readable contracts are `resources/schemas/handoff.schema.json`
for role handoffs and `resources/schemas/task-handoff.schema.json` for task
handoffs. The `artifact_type` discriminator is `role-handoff` or
`task-handoff`, respectively. `artifact_type` is optional in the role-handoff
schema so existing legacy role handoffs without a discriminator remain valid;
new role handoffs should include it. A task handoff must always include its
`task-handoff` discriminator.

These are separate artifacts, not interchangeable schema aliases. A role
handoff may refer to a task through `task_id`, but it does not become a task
handoff merely by adding task-related fields. Conversely, a task handoff is
not a substitute for a minimal role-transfer record when the complete task
execution context is not being transferred.

## Required Fields

### Role handoff

```json
{
  "artifact_type": "role-handoff",
  "handoff_id": "...",
  "task_id": "...",
  "sender_role": "tech-owner",
  "receiver_role": "engineer",
  "objective": "...",
  "requested_action": "...",
  "inputs": [],
  "expected_outputs": [],
  "evidence": [],
  "validation": {"status": "pending", "checks": []},
  "unresolved_questions": [],
  "approvals": [],
  "status": "ready"
}
```

For backward compatibility, legacy role handoffs may omit `artifact_type`.

### Task handoff

Task handoffs use the stricter schema and include the complete task execution
context. A representative shape is:

```json
{
  "artifact_type": "task-handoff",
  "version": "1.0.0",
  "handoff_id": "task-1-handoff-1",
  "task_id": "task-1",
  "plan_id": "task-1-execution-plan",
  "selected_context": {},
  "role_assignments": [],
  "execution_topology": {},
  "capability_requirements": {},
  "sender_role": "tech-owner",
  "receiver_role": "engineer",
  "objective": "...",
  "requested_action": "...",
  "inputs": [],
  "expected_outputs": [],
  "next_action": "...",
  "validation": {"status": "pending", "checks": []},
  "evidence": [],
  "approvals": [],
  "unresolved_questions": [],
  "blockers": [],
  "status": "ready"
}
```

Role-handoff required fields are `handoff_id`, `task_id`, `sender_role`,
`receiver_role`, `objective`, `requested_action`, `inputs`,
`expected_outputs`, `validation`, and `status`. Task-handoff required fields
are defined by `resources/schemas/task-handoff.schema.json` and include the
additional task execution context shown above.

## Statuses

Allowed handoff statuses are:

- `draft`
- `ready`
- `accepted`
- `blocked`
- `completed`
- `rejected`

The receiver may reject a handoff when required inputs are missing, the request
exceeds the receiver's role boundary, or the requested action conflicts with a
team or runtime guardrail.

## Evidence And Approvals

Evidence entries should identify the source, observation, owner, and validation
status. Approval entries should identify the approval type, decision-maker or
required human, status, and timestamp when the runtime can provide one.

The portable evidence and approval shapes are defined in
`resources/schemas/execution-contracts.schema.json`. Runtime-specific evidence
may add fields, but it must preserve the portable identity, status, owner, and
source relationships.

A handoff is not authorization to perform a remote, destructive, release, or
production action. Those actions remain subject to the active approval policy.

## Completion

The sender or receiver should update the handoff with the resulting output,
validation evidence, unresolved questions, and final status. Runtime-specific
messages may wrap this contract, but must preserve its logical fields.
