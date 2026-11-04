# Runtime Integration Conformance Specification

## Purpose

Adapter conformance verifies that a runtime preserves Agent Caravan semantics
when it projects a portable execution plan into runtime-native constructs. It
does not require identical traces, prompts, graphs, agents, tools, or state
stores.

## Adapter Boundary

The conformance boundary is:

```text
resolved Agent Caravan semantics
  -> portable execution plan
  -> capability negotiation
  -> runtime adapter
  -> normalized semantic result
```

The portable plan may contain only generic concepts: task, role assignment,
stage, message, handoff, artifact, state update, tool request, approval
request, result, failure, and completion. The normalized result contract is
defined in `resources/schemas/execution-result.schema.json` and is the
adapter-facing semantic comparison surface.

It must not contain LangGraph nodes, CrewAI tasks, AutoGen agents, Codex
prompts, Agno objects, or another vendor's native object model.

When a plan includes `knowledge_context`, an adapter must make each selected
layer available to every assigned role, preserve the declared layer order, and
apply role-specific guidance only to the matching role. Retrieval from
`trusted_sources` remains subject to the plan's `policy.knowledge_access`.
Supplemental `context.team_context.knowledge_sources` follow the pack layers
and retain their declared order.

Artifact `documentation_references` are explicit supplemental references.
Adapters preserve their association with the source role assignment or
knowledge layer and may retrieve them only when permitted by
`policy.knowledge_access`. They are not fetched by the resolver, and linked
Markdown does not override machine-readable artifact semantics.

Every harness integration should test this projection with multiple ordered
layers, distinct role guidance, supplemental team sources, and a restrictive
knowledge-access policy. It should also continue to accept a legacy plan that
omits `knowledge_context`. These projection checks do not establish live
runtime conformance; report that separately based on harness evidence.

## Required Scenarios

Every adapter should be evaluated against the shared scenarios under
`tests/conformance/scenarios.json`:

- simple sequential execution
- technical handoff
- quality review
- human approval
- failed tool call
- resumable task
- completion evidence
- tool permission boundary
- interrupted run
- checkpoint resume
- idempotent side-effect replay
- degraded capability fallback

## Semantic Result

An adapter result should normalize to:

- scenario ID
- task status
- active roles
- completed stages
- handoffs and their statuses
- approval requests and decisions
- artifacts and evidence
- failures, retries, and escalations
- state-resume identity when applicable
- capability degradation
- checkpoint identity and resumability
- idempotency status and side-effect count
- completion record

Runtime-specific traces remain valuable evidence, but they are supplemental.
They must not be used to redefine the expected semantic outcome.

## Capability Handling

Adapters must report each required capability as `native`, `adapted`,
`externalized`, or `unsupported`. Unsupported required capabilities fail the
scenario. Adapted or externalized capabilities may pass only when the selected
policy permits degradation and the normalized result records it.

## Conformance Does Not Require

- a universal launcher
- a common workflow engine
- one agent per role
- durable persistence
- a particular message bus, database, or model provider
- identical execution traces across runtimes

## Optional Telemetry Conformance

Preserve optional `metadata.observability` associations without changing semantic
outcomes when telemetry is missing or optional collection fails. Explicitly
required observability capabilities retain normal capability handling. A trace
reference alone cannot satisfy required native stage receipts, role reports,
verification, or controller approval evidence. Requested settings remain distinct
from independently observed effective model and reasoning settings.
