# Specifications

These documents define the runtime-neutral Agent Caravan contracts. They describe artifact identity, composition, validation, runtime adaptation, and packaging without requiring a particular runtime or storage provider.

Specifications are normative design inputs; examples and reference artifacts live elsewhere under `examples/` and `resources/`.

The execution-layer specifications are:

- `execution-profile-spec.md`: optional workflow and role-activation contract
- `portable-execution-plan-spec.md`: runtime-neutral handoff from resolved semantics to an adapter
- `task-session-state-spec.md`: separation of durable knowledge from task and runtime state
- `handoff-contract-spec.md`: portable role-to-role work transfer contract
- `serialization-format.md`: canonical JSON and Markdown documentation boundary
- `policy-spec.md`: guardrail, approval, retry, escalation, and termination contract
- session and run schemas define runtime attempt and interaction state
- `adapter-conformance-spec.md`: shared semantic scenarios for runtime integrations
