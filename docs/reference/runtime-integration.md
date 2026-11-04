---
type: Reference
title: Runtime Integration
description: How the Agent Caravan framework connects to AI runtimes and records integration evidence.
---

# Runtime Integration

## Purpose

This page explains how the framework connects to actual AI runtimes.

## Contents

- [Runtime-neutral core](#runtime-neutral-core)
- [Runtime integrations](#runtime-integrations)
- [Runtime mappings](#runtime-mappings)
- [Why adapters and bindings are separate](#why-adapters-and-bindings-are-separate)
- [Intended runtime classes](#intended-runtime-classes)
- [Repository examples and evidence](#repository-examples-and-evidence)
- [Capability realization and verification evidence](#capability-realization-and-verification-evidence)
- [Degraded runtime support](#degraded-runtime-support)
- [Integration guidance](#runtime-integration-guidance)
- [Local adapter and profile examples](../integrations/local-adapter-profile-examples.md)
- [Optional observability](#optional-observability)
- [Event and log output](#event-and-log-output)

## Runtime-Neutral Core

The framework itself does not assume one vendor or one runtime style.

It does not require:

- Codex
- one model provider
- one agent SDK
- one storage system
- one execution environment

Instead, it defines capabilities generically and maps them later.

The runtime layer is also not limited to one organization or one team. The same runtime integration may be reused across many organizations, many caravans, and many specialization layers.

## Runtime Integrations

A runtime integration describes what a runtime can do.

### Repository Guidance

Agent Caravan uses root `AGENTS.md` as the portable repository-guidance entry
point. Adapters may change the native file convention per harness through
`repository_guidance`; the resolver includes that declaration in its runtime
result for bindings to consume. The current adapter defaults are:

| Harness | Canonical file | Native files | Discovery |
| --- | --- | --- | --- |
| Codex Desktop | `AGENTS.md` | `AGENTS.md` | Automatic |
| OpenCode | `AGENTS.md` | `AGENTS.md` | Automatic |
| Kiro IDE | `AGENTS.md` | `AGENTS.md`, `.kiro/steering/**/*.md` | Automatic |

Bindings should read the entry point first and follow its explicit links as
needed. If a future harness uses a different native filename, its adapter
declares that filename and the binding maps the portable guidance into the
harness mechanism. Agent Caravan does not rewrite repository guidance files.
Users can override these adapter defaults in the local profile's single
`config.json` using `adapter_overrides.<adapter-id>.repository_guidance`.

It expresses capability support in neutral terms such as:

- execution
- delegation
- tools and actions
- knowledge and context
- memory and state
- safety and permissions
- observability
- determinism and control

## Runtime Mappings

A runtime mapping maps framework artifacts to a runtime integration.

This is the layer where implementation-specific constructs appear.

Examples:

- one role maps to one runtime agent
- one role maps to a prompt and tool bundle
- one team maps to a flow or orchestrated graph
- one domain-aware role maps to a specialized worker inside a broker platform

## Why Adapters And Bindings Are Separate

The separation matters because:

- a runtime may support many possible binding strategies
- the same framework role may need different mappings in different runtimes
- the same runtime may be used by different teams with different constraints

The adapter defines capability truth.
The binding defines implementation mapping.

This matters for scaling because:

- one adapter may serve many organizations
- one organization may publish many team bindings
- one caravan template may have several team-instance-specific bindings
- one product domain may have several specialization-aware bindings for different owned slices

## Intended Runtime Classes

The artifact model can describe integrations for runtime classes such as:

- direct model runtimes
- agent SDKs or native agent runtimes
- low-code or managed agent platforms
- broker/gateway agent platforms
- orchestration frameworks

This describes the model's intended scope; it does not mean that an executable
bridge or tested binding exists for every class. Evidence for the current
repository examples is summarized below.

Agent Caravan's minimum verification covers the implemented structural and
reference checks for machine-readable artifacts, selected-profile resolution,
and conformance of normalized plans and results. It does not prove that a live
runtime performed the reported work. Runtime-specific verification belongs to
the adapter implementation and should record its runtime version, execution
surface, material configuration, scenario, result, and evidence provenance.
Adapter code and dependencies may be maintained separately from Agent Caravan;
the current repository examples do not prescribe a distribution layout.

## Repository Examples And Evidence

| Runtime example | What exists in this repository | Verification evidence and scope |
| --- | --- | --- |
| Codex Desktop | A runtime integration artifact, reusable runtime mappings, a Codex execution bridge, and a simulated CLI dry-run surface. | The repository provides a bridge and a Codex-specific dry-run surface; live work uses an injected execution surface or the Codex harness workflow. The evidence summary here does not specify a product version or establish runtime-wide conformance. |
| OpenCode | A runtime integration artifact and profile, dedicated CLI/server execution surfaces, and a bounded dependency-approval conformance study. | A historical study reported two dependency-approval cases passing on OpenCode v1.18.33 on September 30, 2026, using the staged runner, attributed external receipts, and server approval helper. This does not verify every declared capability or every provider/model/configuration, nor establish that the same approval surface is currently available. |
| Kiro IDE | A runtime integration artifact and profile plus an IDE-native Agent Skills orchestration entry point. | An operator-reported smoke check on Kiro IDE 1.2.56 on October 12, 2026 covered skill loading, profile selection, a denied permission prompt, and read-only subagent results. Broader conformance and retained execution traces are not established. This adapter targets the IDE; no Kiro CLI bridge is provided here. |
| Broker or gateway | An illustrative team runtime mapping. | This example has no matching runtime-adapter artifact or executable bridge in this repository. Its capability mapping is illustrative and unverified against a particular product. |

These examples document the repository's current artifacts and evidence, not
an exhaustive list of runtimes Agent Caravan can describe or integrate with.
An unlisted or unverified runtime is not thereby incompatible.

For details, see the [Codex adapter walkthrough](../integrations/codex-adapter.md),
the [OpenCode adapter integration](../integrations/opencode-adapter.md),
the [Kiro IDE adapter integration](../integrations/kiro-ide-adapter.md), and
the [runtime mapping inventory](../../resources/runtime/mappings/README.md).

An adopter may use other runtime types, for example:

- direct AI vendors
- coding-agent products
- internal enterprise agent gateways
- orchestration-first systems

## Capability Realization And Verification Evidence

Keep capability realization separate from verification status. Runtime adapter
capability levels such as `native`, `adapted`, `externalized`, and
`unsupported` describe how a specific capability is realized for the adapter's
declared runtime and execution path. They are not test results. For example,
`adapted` may describe a capability implemented through a companion service;
whether a particular binding and configuration was tested is a separate fact.

Verification status describes evidence for a specific runtime product and
version, execution surface, configuration (including provider and model when
relevant), and scenario. Use `verified` only for the scope directly covered by
evidence, and `unverified` when evidence is absent or insufficient. Lack of
verification does not mean unsupported. Reserve `unsupported` or `degraded`
for an evidenced limitation of a named capability or execution path; state
that scope and its evidence. A runtime product may have both verified and
unverified capabilities, or different realization levels across surfaces.

When recording verification, include the product/version, surface, material
configuration, scenario or conformance case, result, date and provenance, and
references to retained evidence where available. Operator-reported checks
should be identified as such and should not imply retained machine-readable
traces. A successful scenario verifies only that scenario and its stated
conditions, not every capability in the adapter.

Use the portable [runtime verification record](../../resources/specifications/runtime-verification-record-spec.md)
to report those fields. `agent-caravan validate-verification-record <path>`
checks the record structure and returns its stated scope. It does not retrieve,
authenticate, or independently validate the referenced runtime evidence.
The dependency-wait scheduling scenario can be exercised with Codex CLI. The generic single-request CLI surfaces reject model-supplied
work-item timelines, so the experimental controller records dispatch intervals
around separate read-only CLI invocations. See the [Codex parallel scheduling pilot](../../tests/conformance/experiments/parallel-scheduling/README.md) for instructions and evidence boundaries.
This verifies that controller path and scenario only.

## Degraded Runtime Support

Not every runtime will support every capability equally well.

The framework therefore expects bindings to document:

- fallbacks
- degraded modes
- evidenced unsupported capabilities or paths

Resolution may report degradation when a required capability is adapted or
externalized under the selected validation policy. That is distinct from
whether the specific configuration has been verified. Missing verification
should be surfaced as `unverified` evidence; it should not by itself cause an
unsupported or degraded capability claim. This keeps the implementation
honest while leaving runtime integration open to additional products and
surfaces.

## Runtime Integration Guidance

When creating a runtime integration:

1. define the runtime integration first
2. describe capability support honestly
3. create role or team bindings second
4. validate the binding against the adapter
5. record capability limitations and verification evidence separately

For private integrations that should not be added to the shared catalog, see
[Local Adapter And Profile Examples](../integrations/local-adapter-profile-examples.md).

Adapters should also consume the optional `context.team_context` fields from a
portable execution plan. The stable team-guidance fields are `instructions`,
`preferred_roles`, and `role_guidance`. Adapters may project them into their
native instruction or routing model, but must preserve the resolved blueprint
workflow, role coverage, approval boundaries, and termination rules.

Plans may additionally include `knowledge_context.layers` for selected domain
and team capability knowledge. Adapters should expose those shared layers to
all assigned roles, apply each layer's role guidance only to the matching role,
and follow `policy.knowledge_access` when retrieving the listed sources.

## Optional Observability

`metadata.observability` associations retain opaque references and correlation
IDs. When enabled, Agent Caravan's Codex and OpenCode adapters can emit a local
workflow start/finish marker through the optional Agent Observability Python
package. This covers the workflow dispatch boundary Agent Caravan owns; it does
not infer individual role, agent, skill, model, or tool invocations.

`execution.observability` defaults to disabled. To collect workflow markers,
install Agent Caravan and Agent Observability in the same Python 3.10+ environment
on a POSIX system, then set the runtime mapping's
`execution.observability.enabled` to `true`.
Markers are written locally to `~/.agent-observability/observations.jsonl` by
default. `AWO_STORE` selects another local JSONL store and `AWO_POLICY` selects an
Agent Observability collection policy; without `AWO_POLICY`, Agent Caravan selects
the current workflow identity. Remote export and content capture are not
implemented by this adapter. The adapter never sends prompts, responses, or tool
content, and a missing package or storage failure is reported as capture status
without changing the workflow result. Normalized results and run records retain
the opaque marker reference and task/session/run correlation IDs.

This policy remains separate from the local CLI event and log output described
below. Ordinary runtime calls may use remote providers.

Mandatory workflow reports, receipts, verification, and approvals remain semantic
evidence independent of telemetry. See the [runtime mapping](../../resources/specifications/runtime-profile-format.md)
and [task/session state](../../resources/specifications/task-session-state-spec.md)
specifications for field definitions.

## Event and Log Output

The CLI writes command results to stdout and diagnostic logs to stderr. It uses
INFO-level text logs by default. The local profile's `config.json` accepts
`logging.level` and `logging.format` (`text` or `json`); command-line
`--log-level` and `--log-format` options override those settings. JSON logs and
persisted run events share the versioned Agent Caravan event envelope. Adapters
may retain their original runtime events in normalized results while the run
record stores the portable envelopes. Use `run --events-jsonl <path>` to capture
run boundary and available adapter events in a separate JSON Lines file. The
envelope preserves source attribution, outcome, available correlation IDs, and
adapter-specific attributes while redacting content-like values by default.
This output is local and does not require Agent Caravan-specific observability or
any external consumer.
