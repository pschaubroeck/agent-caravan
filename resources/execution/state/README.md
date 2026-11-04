# Execution State

Execution state is runtime/session material, not durable organization or team
knowledge. The reference local profile stores it under:

```text
~/.agents/agent-caravan/sessions/<task-id>/
  task.json
  session.json
  runs/<run-id>.json
  handoffs/<handoff-id>.json
  artifacts/
  completion.json
```

The runtime may store equivalent records elsewhere. These paths are the local
implementation profile only. Records must retain task, session, run, role,
runtime, and artifact provenance when those values are available.

Completed records should also expose the execution realization (for example,
`simulated-sequential` with `native_subagents: false`), concise role turns,
decisions, handoffs, and verification evidence. This makes the difference
between a projected workflow and an actually delegated workflow inspectable.

When the selected workflow declares `termination.success_criteria`,
the normalized completion result includes a `workflow_assessment` for that
execution. It reports each criterion as `met`, `not-met`, `unverified`, or
`not-applicable`, with a rationale and evidence references. The report carries
task and plan identity plus session and run identity when available. Missing
assessments, unresolved conditions, degraded execution, and non-completed runs
must not be reported as workflow success. It does not compare Agent Caravan with
the user's prior process.

Do not store credentials, hidden model reasoning, or unbounded conversation
transcripts in these records. Store concise decisions, evidence, tool results,
approvals, unresolved questions, and handoff summaries.

Optional `metadata.observability` carries opaque references and available
Agent Caravan correlation IDs. Preserve associations and unrelated metadata without
fetching references. Missing telemetry does not invalidate semantic evidence.
Observability defaults to disabled; enabling it defaults to local metadata.
Remote export and content capture require explicit configuration.

Run records store adapter execution events in the versioned
`agentFoundryEvent` envelope defined by `execution-contracts.schema.json`.
The envelope carries event identity, timestamp and its source, severity, source
adapter, event type, outcome, available task/session/run/role/stage IDs, and
redacted attributes. Original adapter events remain in normalized execution
results; the persisted envelope keeps unrecognized adapter fields under
`attributes.native_fields`. Events missing a source timestamp are marked
`timestamp_source: agentcaravan_observed` so consumers can distinguish
observation time from runtime time. Older run records using `executionEvent`
remain valid.

The CLI writes command output to stdout and useful logs to stderr. Logging is
INFO-level text by default; `config.json` can set `logging.level` and
`logging.format` (`text` or `json`), with per-command `--log-level` and
`--log-format` overrides. JSON logs use the same event envelope. `run
--events-jsonl <path>` writes run boundary events and available adapter events
to a separate JSON Lines file, independently of stdout and stderr. Content-like
attributes such as prompts, responses, and tool output are redacted by default.
No external telemetry service is required.
