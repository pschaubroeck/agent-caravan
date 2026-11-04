# Codex parallel scheduling pilot

This adapter-owned pilot runs the shared
`dependency-wait-with-independent-work` scenario through bounded, read-only
Codex CLI stage invocations. The controller dispatches the design-answer and
independent-analysis work items concurrently, keeps implementation waiting on
the design item, and dispatches implementation only after the design receipt
completes.

The controller records invocation start and completion around the Codex process
and retains native thread IDs. It does not accept a model-reported timeline.
The shared normalizer checks work-item lifecycle, dependency ordering, timestamp
coverage, provenance, and whether independent work overlapped the wait.

Run from the repository root with the project package available:

```text
PYTHONPATH=src python3 tests/conformance/experiments/parallel-scheduling/run_codex.py \
  --evidence-dir tests/conformance/experiments/parallel-scheduling
```

The runner refuses to overwrite either output file. It requires the Codex CLI to be authenticated and records the installed
CLI version. The retained timeline contains event metadata and thread IDs, not
prompts, reports, tool payloads, or reasoning.

Generated evidence remains local to the operator. Review its contents before
sharing it because it includes runtime session identifiers and timestamps.

This pilot verifies this Codex controller path and scenario only. It does not
establish that every Codex surface or another runtime supports the same
behavior. Other adapters should run the same portable scenario and emit their
own scoped records.
