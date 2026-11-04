# Execution Handoffs

This directory contains reusable handoff examples or runtime-neutral handoff
templates. Agent Caravan has two distinct handoff contracts:

- A role handoff is a lightweight sender-role to receiver-role transfer.
- A task handoff is a complete task-scoped execution transfer that includes
  plan identity and selected execution context.

Use `resources/schemas/handoff.schema.json` for role handoffs and
`resources/schemas/task-handoff.schema.json` for task handoffs. A handoff
transfers bounded work between activated lanes and does not grant permissions
or approval authority.
