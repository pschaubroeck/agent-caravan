---
type: Concept
title: Agent Caravan Framework Vocabulary
description: Definitions for organizational and runtime terms used by Agent Caravan.
---

# Agent Caravan Framework Vocabulary

Agent Caravan keeps organizational concepts separate from executable runtime
concepts.

| Term | Meaning |
| --- | --- |
| organization | A sharing, ownership, and governance boundary |
| caravan | A durable group applying a caravan template to an organization's ownership boundary |
| responsibility | A reusable organizational responsibility with decision rights and constraints |
| caravan template | A reusable definition of responsibility composition, workflow, debates, gates, and coverage |
| domain knowledge | Broad durable product, platform, or technology knowledge |
| capability knowledge | Narrow durable knowledge owned by a caravan |
| configuration override | A scoped change to another artifact, applied through explicit precedence rules |
| validation rules | Checks used to assess artifact structure, references, and resolved configurations |
| resolved caravan | The composed and validated caravan configuration presented to a runtime |
| workflow | Portable stages and responsibility-activation behavior, defined by an execution profile artifact |
| execution topology | Runtime-neutral pattern for sequencing, delegation, handoff, graph, concurrency, or human gates |
| runtime integration | Capability truth for an AI runtime |
| runtime mapping | Mapping from framework meaning to runtime-native constructs |
| tool requirement | Runtime-neutral authority, side-effect, approval, and evidence expectation for a capability |
| evidence requirement | Required proof associated with a stage, role, tool, approval, or completion condition |
| execution event | Normalized state transition or runtime observation correlated to a task, session, or run |
| checkpoint | Portable resumable position tied to a task, stage, and execution provenance |
| idempotency record | Evidence that a repeated operation was recognized and did not duplicate a side effect |
| normalized execution result | Runtime-neutral semantic outcome used to compare adapter behavior |
| task | A bounded objective with plan, decisions, evidence, and outputs |
| session | Runtime state associated with one active task interaction |
| run | One execution attempt or resumable processing instance |
| handoff | Structured transfer of work between activated runtime lanes |
| policy | Guardrail, approval, authorization, or termination rule |
| artifact | A produced or referenced work result with provenance |

An executable runtime worker, agent, crew member, node, or graph participant is
not automatically an Agent Caravan responsibility. Runtime mappings may map a responsibility to one
worker, several workers, a prompt, a graph node, or a sequential simulation.

The current JSON contracts retain existing machine names, including `role`,
`team-blueprint`, `team-instance`, `domain-pack`, `specialization-pack`,
`overlay`, `runtime-adapter`, `runtime-profile`, and `execution-profile`.
Use these literal names in serialized artifacts and existing CLI options.
An individual binding is part of a runtime mapping; it is not a replacement
for the whole mapping.

A workflow is portable by default. Runtime-specific realization belongs
in the selected runtime mapping and integration projection.
