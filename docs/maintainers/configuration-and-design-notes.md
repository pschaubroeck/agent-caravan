---
type: Reference
title: Configuration and Design Notes
description: Historical rationale and proposals for Agent Caravan configuration and implementation design.
---

# Configuration and Design Notes

> Status: historical design note. This document records the rationale and
> proposals for an earlier implementation slice. Consult the specifications and
> integration guides for current contracts and runtime support.

## Purpose

This document records proposed decisions for Agent Caravan's configuration model
and implementation roadmap.

Some proposals are encoded in the framework specifications, schemas, resolver,
Codex projection, and conformance fixtures. Items described as future work or
open questions still require an explicit decision and implementation before
they should be treated as framework guarantees.

## Contents

- [Organization meaning](#decision-1-agent-caravan-owns-organization-meaning)
- [Team shape and execution topology](#decision-2-separate-team-shape-from-execution-topology)
- [Progressive configuration](#decision-3-preserve-the-artifact-model-add-progressive-configuration)
- [Execution topology contract](#decision-4-add-a-first-class-execution-topology-contract)
- [Canonical execution contracts](#decision-5-define-canonical-execution-contracts)
- [Tools and access](#decision-6-expand-capability-contracts-to-include-tools-and-access)
- [Knowledge, skills, and task context](#decision-7-treat-durable-knowledge-runtime-skills-and-task-context-differently)
- [Resolved output](#decision-8-resolver-output-must-explain-more-than-role-selection)
- [Integration conformance](#decision-9-runtime-integration-conformance-is-the-integration-boundary)
- [Runtime versioning and validation](#decision-10-version-and-validate-the-runtime-boundary)
- [Historical implementation scope](#historical-implementation-scope)
- [Open questions](#open-questions)

## Decision 1: Agent Caravan Owns Organization Meaning

Agent Caravan owns the durable meaning of:

- organizations and publication boundaries
- roles and responsibility semantics
- reusable caravan templates
- team ownership instances
- domain and specialization knowledge boundaries
- overlays and composition precedence
- approval, governance, and coverage obligations
- effective-configuration provenance

Runtimes own execution of that meaning.

### Consequence

An executable runtime agent is a projection of a role, not the role itself.
Runtime prompts, tools, models, sessions, and memory must not silently redefine
role authority or team ownership.

## Decision 2: Separate Team Shape From Execution Topology

Team blueprints define responsibility, stages, debates, blocking lanes,
documentation, and governance. They do not prescribe one runtime execution
topology.

Runtime profiles should declare one or more supported topologies:

- `sequential`
- `coordinator-worker`
- `handoff`
- `graph`
- `group-chat`
- `concurrent-fanout`
- `human-gated`
- `remote-agent`

### Consequence

The same Information Technology Core Team may be executed as one coordinating
Codex task, a Microsoft typed workflow, a LangGraph graph, a CrewAI Flow, or an
OpenAI handoff/agents-as-tools design without changing its organizational
meaning.

## Decision 3: Preserve The Artifact Model, Add Progressive Configuration

The detailed artifact model remains the source of truth. The user-facing setup
path should become simpler by deriving detailed artifacts from a small starter
configuration.

The starter configuration should ask for:

```text
organization
team name and ownership boundary
team blueprint
domain knowledge
specialization knowledge
runtime
approval policy
```

The builder or bootstrap layer may derive catalog publication lists, default
runtime mappings, standard policies, and empty optional collections.

### Consequence

Expert users can edit individual artifacts. New users can configure a team
without understanding every internal artifact type first.

## Decision 4: Add A First-Class Execution Topology Contract

Execution profiles should explicitly describe:

- topology type
- task ownership behavior
- routing behavior
- concurrency behavior
- handoff semantics
- termination conditions
- human approval points
- retry and compensation behavior
- checkpoint and resume expectations
- supported runtime capabilities

The topology contract must distinguish:

- `handoff`: the receiving lane owns the task
- `agent-as-tool`: the caller retains task ownership
- `code-orchestrated`: application logic chooses the next lane
- `model-routed`: a model chooses the next lane within declared bounds

## Decision 5: Define Canonical Execution Contracts

Agent Caravan should standardize runtime-neutral shapes for:

- event/message envelopes
- role-to-role handoffs
- stage outputs
- blockers and block resolution
- approval requests and decisions
- task, session, run, and step identity
- checkpoint and resume state
- completion records

Every contract should support:

- stable IDs
- source and target role/team context
- artifact and version references
- causal or parent-run references
- validation status
- unresolved or degraded conditions

### Consequence

Adapters can normalize MetaGPT messages, LlamaIndex events, Haystack state,
PydanticAI runs, or OpenAI run items into common Agent Caravan evidence without
forcing Agent Caravan to own their storage or tracing implementations.

## Decision 6: Expand Capability Contracts To Include Tools And Access

Runtime capability contracts should cover more than model and orchestration
features. They should be able to declare:

- tool and MCP server identity
- tool version and source
- data-access scope
- side-effect class
- permission boundary
- approval requirement
- timeout, retry, and concurrency limits
- cost or usage limits
- audit and evidence expectations

Tool and MCP manifests should be referenced by runtime mappings or policies,
not embedded into reusable role semantics.

## Decision 7: Treat Durable Knowledge, Runtime Skills, And Task Context Differently

Agent Caravan should use these distinctions:

| Concept | Durable? | Owner | Purpose |
|---|---:|---|---|
| Domain pack | Yes | Organization or shared catalog | Broad product/platform knowledge |
| Specialization pack | Yes | Team instance | Narrow team-owned knowledge |
| Runtime skill/toolset | Usually | Runtime binding | Executable capability or progressive disclosure |
| Task context | No | Current task | Issue, repository, document, or environment evidence |
| Session state | Temporary/persistent by runtime | Runtime | Conversation and execution continuity |
| Cross-run memory | Optional | Runtime or approved knowledge source | Reusable learned context |

Promotion from task context or runtime memory into a durable pack must be an
explicit builder operation.

## Decision 8: Resolver Output Must Explain More Than Role Selection

The resolved view should eventually include:

- effective organization, team, roles, and ownership
- applied overlays and precedence decisions
- knowledge loading order
- execution topology
- effective tools and capabilities
- approval and permission boundaries
- task/session/run evidence strategy
- adapter and runtime-profile mapping
- degraded, skipped, ambiguous, or unverified conditions

The resolver must preserve source artifact IDs and versions for every effective
role, policy, knowledge layer, tool manifest, and runtime construct.

## Decision 9: Runtime Integration Conformance Is The Integration Boundary

An adapter should prove that it can:

1. consume a resolved Agent Caravan configuration
2. realize the declared roles and topology
3. enforce or externalize permission and approval boundaries
4. preserve handoff and task-ownership semantics
5. emit correlated execution evidence
6. report unsupported or degraded capabilities
7. map runtime failures and interruptions to framework state

An adapter does not need to expose every runtime feature. It must be explicit
about unsupported features and safe fallbacks.

## Decision 10: Version And Validate The Runtime Boundary

Runtime profiles must pin or constrain:

- runtime product and version
- adapter version
- model/provider assumptions
- supported capability maturity
- preview or experimental features
- serialization and persistence compatibility

Validation should include conformance fixtures for:

- role replacement and provenance
- tool permission enforcement
- approval and interruption/resume
- handoff versus agent-as-tool ownership
- checkpoint replay and idempotency
- structured output validation
- trace and evidence correlation
- degraded capability handling

## Historical Implementation Scope

The slice described here used the Codex adapter and did not add another
runtime. The repository has since added a bounded OpenCode integration; see
[Runtime Integration](../reference/runtime-integration.md) for current support.

Implemented in the slice described here:

1. Execution-topology and canonical execution-contract schemas.
2. Resolver and portable-plan validation for topology, tools, permissions,
   approvals, and evidence requirements.
3. Codex projection and orchestration records that preserve those contracts.
4. A compact starter setup that creates an organization catalog and first team
   instance without guessing durable domain knowledge.
5. Runtime-neutral conformance fixtures for interruption, checkpoint resume,
   idempotent side effects, and degraded capability fallback.

Follow-up proposals recorded at that time (not a current delivery commitment):

1. Add conformance harness support that compares adapter output against the
   normalized result contract.
2. Revisit one optional adapter only after the runtime-neutral contracts are
   stable.

## Open Questions

- Resolved since this note: the framework uses a separate optional
  [`execution-profile`](../../resources/specifications/execution-profile-spec.md)
  artifact for portable workflow behavior. Runtime-specific realization remains
  in the [runtime mapping](../../resources/specifications/runtime-profile-format.md).
- Are tool and MCP manifests shared framework artifacts, runtime-profile
  artifacts, or policy-owned artifacts?
- Which evidence is required for `local-experimental`, `team-shared`,
  `organization-shared`, and `runtime-production` validation rules?
- Should runtime skills be cataloged as first-class artifacts or remain
  adapter-owned resources referenced by ID?
- What is the minimum portable checkpoint contract that does not assume a
  particular runtime's replay semantics?
