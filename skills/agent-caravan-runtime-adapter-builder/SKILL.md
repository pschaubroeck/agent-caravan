---
name: agent-caravan-runtime-adapter-builder
description: Build runtime-neutral integrations and mappings for AI runtimes such as Codex, Droid, Claude, agent SDKs, brokers, or workflow engines. Use when mapping responsibilities, caravans, and knowledge onto a runtime, documenting capability support, defining fallbacks, or checking permissions and observability.
---

# Organization Framework Runtime Integration Builder

## Overview

Use this skill to connect Agent Caravan to a specific runtime without moving runtime-specific assumptions into responsibilities, caravan templates, domain knowledge, or capability knowledge. Build the runtime integration first, then create one or more runtime mappings for the framework configurations the runtime will execute. The machine-readable artifact types remain `runtime-adapter` and `runtime-profile`.

## Workflow

### 1. Discover The Framework And Runtime Context

- Locate the framework root and read the runtime capability adapter specification, runtime mapping format, logical artifact model, and validation guidance.
- Identify the runtime product, version or release boundary, execution surface, and intended operating scope.
- Inspect authoritative runtime documentation, available configuration, and representative execution behavior before making capability claims.
- Separate observed capability from product marketing, assumptions, or a desired future capability.

### 2. Define The Runtime Integration

Create a `runtime-adapter` artifact with:

- stable `id`, name, version, scope, and runtime class
- capability levels for execution, delegation, tools, knowledge, state, safety, observability, and control
- capability status such as `native`, `adapted`, `externalized`, or `unsupported`
- runtime constraints and permission boundaries
- evidence or assumptions supporting important capability claims

Use the adapter to describe capability truth, not team meaning. A Codex adapter, for example, may describe task delegation, local command execution, approval gates, and externalized durable memory without redefining what an engineer or software architect means.

### 3. Define The Runtime Mapping

Create a `runtime-profile` for the resolved framework scope:

- identify `target_adapter_id`
- declare targeted artifact IDs and artifact types
- select a binding scope such as `role-binding`, `team-binding`, `domain-aware-role-binding`, or `resolved-instance-binding`
- map each framework artifact to a runtime-native construct
- declare required, preferred, optional, and forbidden capabilities
- document context loading, role routing, handoffs, and orchestration behavior

One runtime integration may support many mappings. For example, the same Codex integration can serve a core caravan mapping and a Sample Product caravan mapping. A mapping can contain individual bindings; those bindings remain distinct entries within the `runtime-profile` artifact.

### 4. Model Degradation And Fallbacks

For every required or preferred capability that is not native:

- state whether it is adapted or externalized
- define the fallback behavior
- identify what evidence is lost or what manual step is introduced
- state when the degraded mode is unacceptable and execution must stop

Do not hide unsupported behavior behind generic language such as “the runtime handles it.” Serial execution, manual handoffs, external memory, or human-triggered remote actions should be explicit.

### 5. Define Safety And Observability

- Specify local versus remote permissions and which actions require confirmation.
- Preserve framework ownership boundaries when assigning tools, agents, profiles, or connectors.
- Prevent a runtime mapping from turning an engineer lane into unrestricted release, infrastructure, or production authority.
- Document expected traces, handoff summaries, decision records, approval evidence, and verification outputs.
- Document observability coverage, attribution gaps, content exposure, and export limits. Missing optional telemetry is advisory even in strict validation; enforce compatibility when a workflow explicitly requires observability.
- Use optional `metadata.observability` associations without fetching opaque references. Keep telemetry separate from mandatory reports, receipts, verification, and approvals.
- Default `execution.observability` to disabled and, when enabled, local metadata. Remote export and content capture require explicit configuration. Policy does not imply collector implementation or local model calls.

### 6. Validate The Integration

- Confirm the adapter and binding IDs are stable and resolvable.
- Confirm every binding capability requirement is supported natively, adapted, or explicitly externalized by the adapter.
- Confirm runtime constructs do not redefine framework role or team semantics.
- Confirm target organization, team, domain, and specialization artifacts resolve.
- Confirm permission, approval, fallback, and observability expectations are explicit.
- Use `agent-caravan-validator` for the final artifact and reference checks when available.

## Design Rules

- Keep the adapter reusable across organizations and caravans when the runtime capability surface is the same.
- Create a new binding when the resolved team, domain, specialization, permission boundary, or orchestration strategy changes.
- Do not create separate adapters for every team; adapters describe runtimes, bindings describe applications of runtimes.
- Do not claim runtime support based only on a framework requirement. Measure or document the runtime behavior first.
- Prefer a truthful degraded binding over a falsely complete native mapping.
- Keep vendor-specific prompts, agent names, profiles, tool bundles, and graph nodes in binding artifacts or runtime-owned configuration.

## Output Expectations

Summarize:

- the adapter created or changed and its evidence boundary
- the bindings created or changed and their target framework scope
- native, adapted, externalized, and unsupported capabilities
- permission and approval implications
- unresolved compatibility assumptions and recommended validation work

Do not install runtimes, publish bindings, mutate remote configuration, or execute deployment or production actions unless the user explicitly requests those actions.
