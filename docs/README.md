---
type: Directory Index
title: Agent Caravan Documentation
description: Index of Agent Caravan product documentation and repository implementation references.
---

# Agent Caravan Documentation

## Product documentation

For product requirements, installation, user setup, execution and handoff, and
worked user examples, start with the [Agent Caravan user guide](user-guide.md).
This repository documents the framework model and this reference implementation.

## Repository and implementation reference

Use this documentation when you are working in the Agent Caravan repository or
need implementation-specific detail:

1. [Overview](concepts/overview.md) — purpose, scope, and system boundaries.
2. [Framework concepts](concepts/framework-concepts.md) — the mental model and
   artifact layers.
3. [Artifact model](concepts/artifact-model.md) — configuration objects and
   references.
4. [Team and domain design](concepts/team-and-domain-design.md) — composition
   guidance for framework artifacts.
5. [Runtime integration](reference/runtime-integration.md) — implemented
   adapters, profiles, and integration boundaries.
6. [Validation model](reference/validation-model.md) — validation layers and
   what each check establishes.
7. [Packaging and distribution](reference/packaging-and-distribution.md) —
   repository and package distribution details.

Related references:

- [Repository getting started](getting-started.md) — Python checkout setup,
  local CLI access, and contributor checks.
- [Developer examples](developer-examples.md) — supplemental artifact-authoring
  and harness examples. Use these examples alongside the getting started guide.
- [Local profile layout](reference/local-profile-layout.md) — local sources,
  overrides, sessions, and cache.
- [Codex adapter](integrations/codex-adapter.md) — the concrete Codex
  integration.
- [Core team operating model](concepts/core-team-operating-model.md) — the
  default team’s intent and workflow.
- [Local adapter and profile examples](integrations/local-adapter-profile-examples.md)
  — AI-assisted authoring of local runtime artifacts and their validation
  boundaries.
- [Framework vocabulary](concepts/vocabulary.md) — framework terminology.

The framework specifications and canonical artifacts live under
[`resources/`](../resources/). Shareable AI-facing skill sources live under
[`skills/`](../skills/); they are not automatically installed into a runtime.

Local Markdown filenames are concise and linked from this index. Use the repository pages for framework semantics, implementation evidence, and contributor workflows.

## Repository documentation areas

- `concepts/` — framework mental models and artifact design.
- `reference/` — implementation and integration reference.
- `integrations/` — runtime-specific implementation walkthroughs.
- `maintainers/` — internal design notes and research, not product guidance.
- `getting-started.md` — repository and CLI setup for contributors.
- `user-guide.md` — installation, setup, and everyday product workflows.
- `developer-examples.md` — supplemental artifact-authoring and harness
  examples.

For repository tasks, also read the root [`AGENTS.md`](../AGENTS.md), which
defines artifact boundaries and verification commands.

Maintainer references:

- [Configuration and design notes](maintainers/configuration-and-design-notes.md)
  — non-normative proposals and unresolved configuration, runtime-boundary,
  evidence, and conformance questions.
- [Open-source alternatives](maintainers/open-source-alternatives.md) —
  research reference, not product guidance or onboarding.
