---
type: Reference
title: OpenCode Adapter Integration
description: Developer guide to building or evaluating an OpenCode binding for Agent Caravan.
---

# OpenCode Adapter Integration

This guide is for developers building or evaluating an OpenCode binding for
Agent Caravan. It covers the runtime boundary, evidence requirements, and the
recorded comparison with Codex.

The [OpenCode runtime artifact](../../resources/runtime/integrations/opencode-agent-runtime.md)
declares the capability surface targeted at OpenCode v1.18.33. The declaration
alone does not establish conformance. Use an installed OpenCode runtime, an
Agent Caravan execution plan, and an explicitly selected provider and model.
Check native event fields against the installed binary before claiming support.

## Contents

- [Install the OpenCode entry point](#install-the-opencode-entry-point)
- [Integration boundary](#integration-boundary)
- [Mapping and evidence](#mapping-and-evidence)
- [Comparison with Codex](#comparison-with-codex)
- [Local experiment context](#local-experiment-context)
- [Related documentation](#related-documentation)

## Install The OpenCode Entry Point

Run these commands from a repository checkout.

```text
python3 -m pip install .
agent-caravan init --runtime opencode --root ~/.agents/agent-caravan-opencode
agent-caravan status --root ~/.agents/agent-caravan-opencode
agent-caravan validate
agent-caravan resolve --root ~/.agents/agent-caravan-opencode
```

The separate profile root keeps an existing Codex team intact. Initialization
installs the four shared skills and `agent-caravan-opencode-orchestrator` under
`~/.config/opencode/skills/`. Load that entry point with OpenCode's native
`skill` tool and use a matching resolved OpenCode team. OpenCode also discovers
`~/.agents/skills/`; a discovered Codex orchestrator remains Codex-specific.
See [installation and refresh examples](../reference/packaging-and-distribution.md#install-and-refresh-skills)
for custom roots, upgrades, and preserved local copies.

The local starter selects `team-shared` validation unless the profile already
has an explicit validation policy. OpenCode's adapted required capabilities
produce a `degraded` resolution with named limits; they are not reported as
native. Existing stricter validation policies remain in effect. Initialization
resolves the proposed team before writing profile or skill changes and stops
if its capabilities do not meet that policy, preserving the existing setup.
Select a compatible runtime or deliberately review the team's validation
policy before retrying; setup never weakens an existing policy automatically.

`agent-caravan run --dry-run` prepares Codex only. OpenCode skill installation
does not create a live execution binding or change OpenCode permissions. Use
the native harness with the orchestration skill or provide the execution
surface below, and retain observed evidence for capability claims.

## Integration Boundary

Agent Caravan owns the portable execution plan, task/session/run identities, conformance cases, normalized result, and approval criteria. An OpenCode binding owns agent configuration, native invocation, permission handling, and translation of runtime events. It must consume a runtime-neutral request rather than the Codex-specific `CodexExecutionRequest` or Codex brief.

OpenCode documents two useful execution surfaces:

- `opencode run --format json` emits machine-readable events for a non-interactive run. Start here when inspecting a read-only or rejected case.
- The server API provides sessions, an event stream, and permission responses. Use this surface for a case that must stop for a human decision and then resume.

The CLI read-only surface now uses a dedicated restricted agent, `--pure`, and a preflight check of the effective permissions before dispatch. It also rejects permission events and disallowed tools, denies `.env` reads and content search, and retains event content only when `capture_content` is enabled. This remains an application-level restriction, not an operating-system sandbox.

The server API exposes sessions, events, and permission responses, but the current approval surface is disabled. The v1.18.33 event/API contract does not authenticate the decision maker or prevent a competing local process from responding to a pending permission request. Do not use that surface to claim human-approved execution until those controls are available and verified. The exact CLI and permission behavior must still be checked against the installed v1.18.33 binary before a live adapter claims support. See the official [CLI](https://opencode.ai/docs/cli/), [server](https://opencode.ai/docs/server/), and [permission](https://opencode.ai/docs/permissions/) documentation.

## Mapping And Evidence

The binding should map portable roles to configured OpenCode agents and invoke subagents only for authorized lanes. OpenCode supports primary agents, subagents, and child sessions, but a completion record needs the child session reference and matching role-turn evidence before claiming native delegation. Parallel lane conformance also needs overlapping intervals. See [OpenCode agents](https://opencode.ai/docs/agents/).

The prepared OpenCode request projects optional `knowledge_context.layers`
once as shared context. A binding should make each layer available to every
assigned role in the declared order, then make
`supplemental_knowledge_sources` available in their declared order. Apply a
layer's `role_guidance` only to the role named by its key. The request also
preserves `policy.knowledge_access` as `knowledge_access`; use that policy when
deciding whether and how to retrieve `trusted_sources`. The projection carries
references and curated guidance, not copies of external source documents.
These are harness-neutral request semantics; this integration guide does not
claim live OpenCode enforcement or verification.

Persist bounded evidence: Agent Caravan task/session/run/plan IDs, OpenCode version and session IDs, provider and exact model ID, summarized tool and permission events, timestamps, evidence references, and normalized outcomes. Retain actor-attributed approval decisions only after an authenticated approval surface is implemented. Exclude credentials, hidden reasoning, and unbounded transcripts.

When the portable plan declares `termination.success_criteria`, include one
evidence-linked assessment for each criterion in the runtime result. Use only
declared criterion IDs and assessor roles. Missing or unsupported evidence
remains `unverified`; a completed runtime session does not by itself establish
workflow success. Do not report a comparison with the user's previous process.

For the dependency-approval acceptance case, configure the protected action to ask. A global allow policy or automatic permission acceptance does not establish a human decision. Record the approval request and response, their scope and order, and whether the action occurred after the approval. Keep the separate human evaluation rubric outside the adapter's self-reported outcome.

## Comparison With Codex

Use the same case pack, criteria, candidate evidence, and normalized conformance contract for both bindings. Pin OpenCode v1.18.33 and the provider/model for each run. Matching the model and provider reduces a comparison confound; if they differ, report that difference alongside the result. A successful OpenCode run would support a two-harness parity claim for these cases, not a claim about all harnesses.

## Local Experiment Context

The local study operator had OpenAI GPT-6 Astra, Sol, and Luna and local Ollama
Qwen models available in OpenCode. Those choices describe the experiment
environment; each execution must record its actual provider and model ID.

The local OpenCode study recorded both dependency cases passing on September 30, 2026, using the staged runner, attributed external receipts, and server approval helper. Both complete Codex cases subsequently passed the same case pack, and retained OpenCode receipts passed reevaluation. The [adapter comparison](codex-opencode-comparison.md) records tested portable conformance, different native versus external approval enforcement, and the model-history limits. Controlled model and performance parity remain unverified.

## Related Documentation

- [Runtime integration contract](../reference/runtime-integration.md) for portable runtime boundaries.
- [Codex adapter walkthrough](codex-adapter.md) for the Codex bridge.
- [Codex and OpenCode comparison](codex-opencode-comparison.md) for tested cases and comparison limits.
