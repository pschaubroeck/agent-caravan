---
type: Guide
title: AI-Assisted Local Runtime Integration and Profile Authoring
description: Guide to authoring private runtime integrations and profiles with an AI harness.
---

# AI-Assisted Local Runtime Integration And Profile Authoring

Use an AI harness with the Agent Caravan builder and runtime-adapter-builder
skills to create a private runtime integration. The AI inspects the selected
runtime's documentation and source, drafts the adapter and profile artifacts,
explains its capability claims, then resolves and validates the proposed
binding. The implementor chooses the runtime and confirms its intended scope.

The examples in this guide describe that authoring workflow. They do not
define a specific vendor integration, publish artifacts to the shared project,
or claim a tested executable adapter. Agent Caravan's skills guide an AI
harness; Agent Caravan does not itself discover runtimes or run an AI authoring
agent.

## Prompt The AI Authoring Workflow

Give the harness the runtime product, version or release boundary, execution
surface, intended Agent Caravan team, and the sources it may inspect. Ask it to
use the runtime-adapter-builder workflow. For example:

```text
Use the Agent Caravan runtime-adapter-builder workflow to prepare a private
runtime integration for <runtime product, version, and execution surface>.
Inspect the current runtime documentation, available configuration, and
implementation evidence. Target <team or role scope> in my local Agent Caravan
profile.

Determine whether this needs a new runtime integration or only a runtime mapping
that reuses an existing adapter. Draft the required local artifacts with
stable IDs and scope `local`. For every capability claim, distinguish observed
behavior from documentation and assumptions. Include constraints, permission
boundaries, fallbacks, evidence expectations, and unsupported paths. Do not
weaken the selected execution profile's capability requirements to make the
binding resolve.

Show me the proposed artifacts and local profile changes before writing. Keep
them outside the shared project. Then resolve and validate the local binding,
and report any capability gaps or unresolved evidence. Do not implement an
executable runtime bridge unless I ask for that separately.
```

The AI should return:

- a reasoned decision about reusing or creating a runtime integration;
- a `runtime-adapter` artifact describing capability truth and constraints;
- a `runtime-profile` artifact mapping the chosen framework scope to the
  adapter;
- source evidence and assumptions behind important capability levels;
- a preview of local source/configuration changes; and
- resolution and validation results, including degraded or unsupported
  capabilities.

The AI should ask about missing runtime or team choices instead of guessing,
preserve existing artifact IDs, and preview local writes before making them.
Use the [runtime capability and adapter specification](../../resources/specifications/runtime-capability-adapter-spec.md)
and [runtime mapping format](../../resources/specifications/runtime-profile-format.md)
as the artifact contracts.

## Keep The Artifacts Local

The reference implementation loads JSON artifacts from source paths listed in
`~/.agents/agent-caravan/config.json` under `sources`. A source may be a JSON
file or a directory containing artifact JSON files. Local artifacts need
unique `(artifact_type, id)` pairs and must be published by the selected
organization catalog before the resolver can select them. Set the local
adapter and profile IDs in `active_context` when they are ready to use.

The resolver rejects duplicate artifact IDs rather than choosing a winner by
source order. Although the local profile layout documents an `overrides/`
directory, the current loader does not automatically scan it; configure its
source path explicitly if that is where the local artifacts are kept. See the
[local profile layout](../reference/local-profile-layout.md) and
[profile loader](../../src/agentcaravan/profile.py).

## Know What The Adapter Artifact Does

The runtime integration and profile are declarative framework artifacts. They
describe capabilities, mappings, requirements, and fallbacks. They do not
load or execute arbitrary runtime-specific code.

If the selected runtime needs a new execution bridge, that is a separate
implementation step. The bridge must consume the resolved plan and return
task-attributed results that meet the portable execution contract. Existing
surfaces such as the [Codex execution surface](../../src/agentcaravan/adapters/codex_execution_surface.py)
show where runtime-specific code connects to Agent Caravan. If the runtime is
already supported and only its model or provider configuration changes, a
local runtime mapping may be sufficient; capability claims still need to be
checked against that configuration.

## Validate The Binding

Before using the local integration, have the AI verify that:

- the selected organization catalog publishes the adapter and profile IDs;
- the runtime mapping targets the selected adapter and framework artifacts;
- each required capability meets its minimum support level;
- the selected workflow's capability requirements are satisfied;
- fallbacks preserve required role, approval, and termination boundaries; and
- evidence supports the adapter's capability claims.

Resolution checks the declared contract. It does not prove runtime behavior;
that requires execution through the bridge and adapter-specific conformance
evidence.
