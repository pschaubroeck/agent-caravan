# Runtime Adapters

Runtime adapters consume portable execution plans and project them into a
concrete AI runtime. Adapter code may know about its target runtime, but must
not redefine Agent Caravan organization, workflow, policy, or portable-plan
semantics.

The current Codex implementation remains available at
`agentcaravan.codex_adapter` and is also exposed through
`agentcaravan.adapters.codex`.

`agentcaravan.adapters.codex.run_codex_conformance_suite` is the runtime
bridge. It prepares one Codex brief per scenario, creates task/session/run
records, invokes a caller-supplied execution surface, and normalizes the
returned result. The preferred surface consumes a
`CodexExecutionRequest`; the request carries the prepared plan, Codex brief,
execution identities, and optional persistence store. `DryRunCodexExecutor`
exercises that boundary without claiming that a live Codex task or separate
role agents ran.

For one operator task, use `agentcaravan.adapters.codex.run_codex_task` with
the same request/surface boundary. The CLI's `agent-caravan run --dry-run`
command is the reference wrapper around this single-task API.

`agentcaravan.adapters.opencode` provides an independent preparation and
conformance bridge for OpenCode. Its `OpenCodeExecutionRequest` carries the
portable plan projection and the same task/session/run identities. The
`OpenCodeCliExecutionSurface` targets v1.18.33 and permits read-only work;
it rejects unsupported approval, delegation, and write claims. See the
[OpenCode integration guide](../../../docs/integrations/opencode-adapter.md)
for the approval-capable surface and evidence limits.

Pass `LocalJsonExecutionStore(<root>)` when task/session/run state should be
written to the local implementation layout. The store writes atomically to
`<root>/<task-id>/`, including a new `runs/<run-id>.json` for each attempt and
`completion.json` for the normalized result. Persistence is opt-in so library
calls and conformance tests do not unexpectedly write to a user's home
directory.

The store validates record identity and required state fields before writing.
Use the read-only operator check after a run, resume, or external recovery:

```text
agent-caravan validate-session --task-id example-feature-001
```

The command reports whether `task.json`, `session.json`, every run record, and
`completion.json` form one coherent evidence set. It returns a non-zero status
when a file is missing, malformed, or has mismatched task/session/plan
identity.
