# Agent Caravan Engine

This package contains the Agent Caravan resolver and the distributable core
framework resources. From a checkout, install it with `python -m pip install -e .`
to make the `agent-caravan` command available. A package registry release is
not required for this checkout workflow.

## Package Boundaries

- `agentcaravan.foundation`: runtime-neutral source, profile, and execution-plan contracts
- `agentcaravan.adapters`: projections into concrete AI runtimes
- `agentcaravan.bootstrap`: local profile and packaged-source setup
- `agentcaravan.cli`: the installed command-line entry point

The flat modules remain supported compatibility entry points while the package
boundaries mature. Foundation code must remain independent of runtime,
storage-provider, Jira, GitLab, and organization-specific assumptions.

Skill copies installed by `agent-caravan init --runtime codex`,
`agent-caravan init --runtime opencode`, or `agent-caravan init --runtime kiro`
carry an Agent Caravan management marker. Valid markers must identify the expected skill
and installation format, including a valid SHA-256 content fingerprint.
Unmarked directories are preserved unless their content exactly matches the
packaged skill, allowing unchanged legacy installs to be adopted safely.
Modified managed copies require confirmation. Replacement is staged and
renamed with rollback protection, so copy, marker-write, or final-rename
failures do not remove the existing skill. Malformed markers and symlinks are
treated as unmanaged and preserved.

Codex remains the default runtime. Each setup installs the four shared skills
and the selected runtime's orchestrator, and remembers its skill destination
for refresh and status. OpenCode defaults to `~/.config/opencode/skills`;
Kiro IDE defaults to `~/.kiro/skills`; Codex defaults to `~/.agents/skills`.
Kiro uses its native IDE skills harness and has no CLI execution bridge.
Existing Codex management markers and the legacy `managed_skill_root`
configuration remain supported.

Kiro integration uses the IDE's native Agent Skills harness with packaged
runtime metadata; it does not use a Kiro CLI execution bridge.

The engine accepts a normalized JSON artifact bundle. JSON is only the prototype interchange format; the framework does not require JSON, files, Git, or any other storage mechanism. Storage adapters translate provider-native records into the logical bundle contract defined in `resources/specifications/artifact-bundle-spec.md`.

Run it from the repository root with:

```text
PYTHONPATH=src python3 -m agentcaravan.resolve_framework \
  tests/fixtures/sample-product-engineer-ii.json
```

After an optional editable installation, the same package can be imported
without setting `PYTHONPATH`.

The local profile bootstrap utility is available as:

```text
PYTHONPATH=src python3 -m agentcaravan.org_framework_layout
```

The installed CLI can create the first organization and team together:

```text
agent-caravan init --organization "Example Organization" \
  --team "Platform Team" \
  --ownership-boundary "shared platform services" \
  --runtime codex
```

This starter path creates an organization catalog and a caravan boundary
(`team-instance` in the existing artifact format). It reuses the shared
caravan template and leaves domain knowledge, capability knowledge, and
configuration overrides explicit.

The Codex adapter's plan projection remains runtime-specific and caller
controlled. Given a resolved bundle and task,
`agentcaravan.adapters.codex.prepare_codex_execution` validates and prepares
the portable plan, then emits role lanes, stage checkpoints, approval
boundaries, and completion requirements for the Codex orchestration skill.
The preferred execution boundary is
`agentcaravan.adapters.codex.CodexExecutionRequest`, which carries the
prepared plan, Codex brief, and task/session/run records to an injected
Codex execution surface. `agentcaravan.session_store.LocalJsonExecutionStore`
provides opt-in local persistence under the reference sessions layout.
The installed `agent-caravan run --dry-run` command is the reference
single-task operator path through these APIs.
Use `agentcaravan.foundation.build_execution_records` and
`agentcaravan.foundation.build_completion_record` to correlate runtime
evidence to the plan. Use the normalized result helpers in
`agentcaravan.foundation` for interruption, checkpoint resume, idempotent
replay, and degraded capability results. The adapter does not launch live
tasks or provide a universal launcher; the dry-run CLI path is an explicit
reference smoke test. See `docs/integrations/codex-adapter.md`.
