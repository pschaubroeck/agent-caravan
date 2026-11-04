---
type: Reference
title: Kiro IDE Adapter
description: Integration reference for the Agent Caravan runtime integration and team profile targeting Kiro IDE.
---

# Kiro IDE Adapter

## Scope

This integration targets the Kiro desktop IDE and its native agent harness.
It packages a Kiro IDE runtime integration, a team profile, and an
`agent-caravan-kiro-orchestrator` skill. It does not require or invoke Kiro
CLI.

The capability mapping is based on official Kiro documentation and has not
been exercised in an authenticated Kiro installation.

## Install

Install Agent Caravan and initialize a Kiro profile:

```text
agent-caravan init --runtime kiro --root ~/.agents/agent-caravan-kiro
agent-caravan status --root ~/.agents/agent-caravan-kiro
agent-caravan validate
agent-caravan resolve --root ~/.agents/agent-caravan-kiro
```

The installer places shared Agent Caravan skills and the Kiro orchestrator in
`~/.kiro/skills/`. For one workspace only, use a project `.kiro/skills/`
directory with `--skill-root`. The selected root must be discoverable by the
Kiro IDE. Setup installs skill files and resolves local configuration; it does
not launch Kiro, sign in, or change IDE permissions.

Open the intended workspace in Kiro, confirm the
`agent-caravan-kiro-orchestrator` skill is available, and use that skill as the
entry point for Agent Caravan-governed work. Kiro Specs can add a requirements,
design, and tasks checkpoint where useful. They do not replace the selected
Agent Caravan workflow.

## Capability Mapping

The adapter is [`kiro-ide-agent-runtime`](../../resources/runtime/integrations/kiro-ide-agent-runtime.md).
The starter binding is
[`kiro-ide-information-technology-core-team`](../../resources/runtime/mappings/kiro-ide-information-technology-core-team.md).
Both preserve the portable team roles and report adapted capabilities as
degraded under the `team-shared` validation rules. A stricter profile already
selected by the operator remains in force.

Kiro documentation describes native IDE skills, custom agents, permission
rules, hooks, subagents, and parallel subagent execution. The profile maps
Agent Caravan roles to Kiro agents only when the portable plan authorizes those
lanes. Missing attributable worker or approval evidence must remain a stated
limitation; visible IDE activity is not a complete execution trace.

## Portable Team Knowledge

The portable execution-plan contract is framework-neutral. When a plan includes
`knowledge_context.layers`, the Kiro orchestrator instructions require the
coordinating agent to make those shared layers available to every role assigned
to the task. Apply domain layers before specialization layers, and apply each
layer's `role_guidance` only to its matching role. Apply supplemental
`context.team_context.knowledge_sources` after pack layers, in listed order.
Knowledge layers carry curated guidance and source references; they do not
embed source documents. Retrieval from external sources must follow
`policy.knowledge_access`.

This repository contains Kiro integration guidance, but no local Kiro code
bridge that consumes portable plan JSON or enforces this projection. The
contract is intended to apply across harnesses, while Kiro's live behavior for
shared knowledge delivery and retrieval policy remains unverified. The manual
smoke check described below did not test knowledge consumption.

## Verification Status

`agent-caravan validate` checks packaged Agent Caravan resources, and
`agent-caravan resolve` checks the selected local profile. In a bounded Kiro IDE
`1.2.56` session on 2026-10-12, the operator reported successful checks for
workspace skill discovery and explicit activation, correct resolved runtime
IDs, a permission prompt and denied write under `.kiro/agents/`, and two
read-only subagent results. This was a manual smoke check; the repository does
not retain the session transcript, worker references, or timestamps. It does
not establish comprehensive conformance, and parallel overlap cannot be
independently confirmed from retained evidence. Run further bounded checks for
custom-agent mapping, hooks, Specs, state persistence, and other permission
scopes before claiming those capabilities conform.

The current `agent-caravan run --dry-run` surface is Codex-only. Kiro IDE work
uses the native Kiro harness and the Agent Caravan Kiro orchestrator skill;
portable plan execution through a repository-local Kiro bridge is not
implemented.

## Official Kiro Documentation

- [Agent Skills](https://kiro.dev/docs/skills/)
- [Custom agents](https://kiro.dev/docs/ide/whats-new-v1/agent-config/)
- [Subagents](https://kiro.dev/docs/custom-agents/subagents/)
- [Hooks](https://kiro.dev/docs/hooks/)
- [IDE permissions](https://kiro.dev/docs/ide/whats-new-v1/permissions/)
- [IDE and agent features](https://kiro.dev/docs/editor/codebase-indexing/)
