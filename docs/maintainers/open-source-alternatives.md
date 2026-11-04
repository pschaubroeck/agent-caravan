---
type: Research
title: Open Source Alternatives
description: Comparison of agent runtimes and products for designing, configuring, distributing, or operating agent teams.
---

# Open Source Alternatives

## Purpose

This document compares Agent Caravan with both executable agent runtimes and
products that help people design, configure, distribute, or operate agent
teams. The goal is not to select a new runtime or copy a competitor's product.
It is to identify useful patterns, clarify the competitive boundary, find
configuration and onboarding improvements, and keep responsibilities outside
Agent Caravan where appropriate.

Research snapshot: October 13, 2026. Product capabilities and host support
change quickly; verify the linked project documentation before making adoption
or compatibility decisions.

## Contents

- [Executive summary](#executive-summary)
- [Comparison matrix](#comparison-matrix)
- [Cross-product patterns](#cross-product-patterns-worth-adopting)
- [Team-building and harness product comparison](#team-building-and-harness-products)
- [Runtime product findings](#product-specific-findings)
- [Team-building and harness product findings](#team-building-and-harness-product-findings)
- [Non-goals](#non-goals-confirmed-by-the-research)
- [Recommended next step](#recommended-next-step)

## Executive Summary

The landscape has two related layers. Runtime frameworks execute agents and
workflows. Team-building and harness products generate or distribute the
agents, skills, instructions, and workflows that a particular runtime uses.
Both are relevant comparisons: the first tests Agent Caravan's adapter boundary;
the second tests whether its model is easy to create, adopt, distribute, and
improve.

In the projects reviewed here, no product presents the complete Agent Caravan
combination of organization catalogs, durable role meaning, reusable team
blueprints, team ownership instances, scoped knowledge, overlays, runtime
adapters, and explainable cross-artifact resolution. That is a positioning
hypothesis from public project documentation, not proof that no comparable
implementation exists.

The closest newly identified analogue is [AgentPal](https://github.com/AgentPal/AgentPal):
it has reusable teams, role-aware participants, knowledge and skills, workflow
contracts, asset preflight, and closure checks across Codex and Claude Code.
Its own README describes v0.6 as ready for guided user testing, not production
ready, and says the host runtime still performs execution. This makes it the
best direct comparison for Agent Caravan's team setup and operating model, while
Agent Caravan's stronger distinction is its explicit organization artifact
layers, ownership instances, scope composition, and resolver.

Two other findings test different parts of the boundary: [Agent Layer](https://agent-layer.dev/)
focuses on repo-local cross-harness configuration and dispatch, while
[AgentDef](https://github.com/agentdef/agentdef) proposes a portable definition
format for individual agents. Neither, from its published scope, describes
Agent Caravan's complete organization and team composition model.

Agent Caravan should therefore remain above these products:

```text
Agent Caravan
  organization meaning, ownership, knowledge boundaries, policy, resolution
        |
        v
Runtime adapter/profile
  execution topology, model/tool calls, state, checkpoints, deployment
        |
        v
Runtime product
  Codex, CrewAI, LangGraph, Microsoft Agent Framework, ADK, or another runtime
```

This diagram shows the execution layering, not the entire product ecosystem.
Team builders, workflow kits, and catalogs can author or package artifacts at
the boundary between Agent Caravan and a runtime.

The strongest shared design lesson is to separate four concerns:

1. durable organizational meaning
2. runtime execution topology
3. task and execution state
4. evidence, evaluation, and governance

## Comparison Matrix

| Product | Primary strength | Closest Agent Caravan mapping | Recommended relationship |
|---|---|---|---|
| [CrewAI](https://docs.crewai.com/core-concepts/Agents) | Role-shaped crews, tasks, processes, and event-driven flows | Runtime role, team execution, task contracts, flow topology | Future adapter target; not a replacement for organization artifacts |
| [MetaGPT](https://github.com/FoundationAgents/MetaGPT) | Software-company simulation, SOPs, roles, actions, and message routing | Role, action, team workflow, message envelope | Useful compatibility target; do not adopt the software-company metaphor as the core ontology |
| [AutoGen](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/index.html) | AgentChat teams, group chat, handoffs, graph execution, and Magentic-One | Runtime team topology and collaboration patterns | Legacy compatibility target; prefer current Microsoft Agent Framework for new integrations |
| [Microsoft Agent Framework](https://learn.microsoft.com/en-us/agent-framework/overview/) | Typed workflows, executors, edges, sessions, checkpoints, and human-in-the-loop | Runtime integration, workflow, evidence mapping | High-value future adapter target |
| [LangGraph](https://docs.langchain.com/oss/python/langgraph/graph-api) / [Deep Agents](https://docs.langchain.com/oss/python/deepagents/customization) | Stateful graphs, coordinator-worker execution, persistence, interrupts, skills, and subagents | Execution topology, runtime state, skills, and checkpoints | High-value runtime substrate and adapter target |
| [Google ADK](https://adk.dev/) | Agent hierarchies, graph workflows, sessions, artifacts, evaluation, and deployment | Runtime integration and mapping, and remote-agent boundary | Future adapter target; keep Google hosting concerns outside the core |
| [LlamaIndex](https://developers.llamaindex.ai/python/llamaagents/workflows/) | Data-centric agents, typed events, workflows, handoffs, and durable execution | Domain-context adapter, workflow topology, execution evidence | Strong adapter target for knowledge-heavy teams |
| [PydanticAI](https://pydantic.dev/docs/ai/core-concepts/agent/) | Typed agents, capabilities, dependencies, structured output, instrumentation, and evaluation | Runtime mapping, capability bundle, typed role binding | Useful typed runtime target; pin versions explicitly |
| [Haystack](https://docs.haystack.deepset.ai/docs/pipelines) | Typed pipelines, agents, toolsets, state, hooks, tracing, and evaluation | Runtime graph, tool manifest, state and evidence mapping | Strong adapter target for pipeline and retrieval workflows |
| [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/agents/) | Agents, tools, handoffs, agents-as-tools, guardrails, sessions, approvals, and tracing | Runtime mapping, handoff policy, tool policy, session/evidence mapping | Useful adapter target; not the organization model |

### Team-building and harness products

These products are closer to Agent Caravan's setup and authoring experience
than most runtime SDKs. They are not all direct substitutes: some generate a
single-harness team, some provide a ready-made workflow, and others distribute
a component catalog.

| Product | Primary strength | Closest Agent Caravan mapping | Recommended relationship |
|---|---|---|---|
| [BMad Method and BMad Builder](https://github.com/bmad-code-org/BMAD-METHOD) | End-to-end software delivery method with specialized perspectives, workflows, durable context, and a builder for skills, workflows, and agents | Caravan template, responsibility artifacts, domain guidance, and builder | Study its guided creation and right-sized process; preserve Agent Caravan's broader organization model |
| [RevFactory Harness](https://github.com/revfactory/harness) | Generates Claude Code agent definitions, skills, and orchestration from a project description; includes verification and harness evolution | Caravan template, runtime mapping, skill projection, validation | Closest team-architecture factory; useful generation and feedback patterns, but its output targets Claude Code |
| [agents-team](https://github.com/fadymondy/agents-team) | Claude Code team generator with agent/skill evaluation and structured multi-agent meetings | Builder workflow and artifact validation | Strong example of making generation measurable; currently describes itself as an initial v0.1 release |
| [Compound Engineering](https://github.com/EveryInc/compound-engineering-plugin) | Reusable brainstorm-plan-build-review-learn workflow packaged as skills for many coding-agent hosts | Team workflow, runtime skills, and learning loop | Study workflow discovery and distribution; it does not model organization ownership or team composition |
| [Superpowers](https://github.com/obra/superpowers) | Composable software-development methodology, including specification, planning, TDD, and subagent-driven implementation across coding agents | Workflow stages, skills, and role participation | Study clear, opinionated user guidance; its scope is software delivery rather than organization configuration |
| [Everything Claude Code](https://github.com/affaan-m/ECC) | Broad harness operations toolkit covering agents, skills, hooks, rules, memory, setup, and security across several hosts | Runtime mappings, skills, policies, and installation | Study setup/update and host adaptation; documented capability parity varies by runtime |
| [wshobson/agents](https://github.com/wshobson/agents) | Large multi-harness catalog of plugins, agents, skills, and commands with host-specific adaptation | Artifact catalog, packaging, and runtime projections | Study discovery and distribution; a component marketplace is not an organization/team composition model |
| [Agent Harness](https://github.com/SUNRNEHUI/agent-harness) | Runtime-neutral intent-to-contract, bounded delegation, durable handoff, and evidence-based acceptance | Portable execution plan, handoff, and completion evidence | Study portable execution contracts; its focus is task execution rather than organization and team catalogs |
| [AgentPal](https://github.com/AgentPal/AgentPal) | Role-aware Pals and Team Packs, team-first discovery, asset preflight, execution contracts, and closure checks for Codex and Claude Code | Caravans, role/knowledge/skill composition, setup workflow, and completion evidence | Closest direct product comparison; study discovery and evidence gates. It is currently a guided-testing project and leaves execution to the host runtime |
| [Agent Layer](https://agent-layer.dev/) | Repo-local source of truth for multi-harness configuration, portable skill sync, and bounded cross-agent dispatch | Runtime projections, skill distribution, and cross-runtime execution boundary | Study its single-source setup and dispatch lifecycle; it focuses on project configuration and execution, not durable organization semantics |
| [AgentDef](https://github.com/agentdef/agentdef) | Draft framework-independent specification for modular, portable individual agent definitions, with validation and importers | Reusable role/agent definition and runtime adaptation | Track as a standards neighbor; it specifies agents, not organizational ownership, team composition, or scope resolution |
| [Codex Orchestrator](https://github.com/zm2231/codex-orchestrator) | Executable role-based teams, persistent Codex/Claude agents, worktree isolation, supervision, and feature/review workflows | Runtime execution topology, role bindings, QA, and evidence | Study isolation and workflow enforcement; it is an orchestrator that runs agents, rather than a runtime-neutral organization framework |
| [OpenCode Agent Orchestration Kit](https://github.com/jcarlosrodicio/opencode-agent-orchestration-kit) | OpenCode-centered software delivery workflows with phase-owned agents, durable bounded loops, review, and local safety contracts | Single-harness runtime mapping, workflow topology, and process skills | Study phase ownership and review contracts; its process and agent configuration target OpenCode |

## Cross-Product Patterns Worth Adopting

### Role is not the same as agent

Across the products, an executable agent usually combines instructions, model
settings, tools, memory, and runtime behavior. That is more implementation
detail than an Agent Caravan role should contain.

Agent Caravan roles should continue to define responsibility, authority,
coverage, blocking rights, debate participation, and documentation ownership.
A runtime binding may compile one role into one agent, several agents, a
prompt/tool bundle, or a governed perspective inside one coordinating task.

### Team shape is not the same as execution topology

CrewAI distinguishes Crews from Flows. Microsoft Agent Framework distinguishes
agents from workflows. OpenAI distinguishes handoffs, agents-as-tools, and code
orchestration. LangGraph separates graph infrastructure from the Deep Agents
harness.

Agent Caravan should add an explicit execution-topology vocabulary without
moving topology into the caravan template's responsibility semantics:

- sequential stages
- coordinator/worker
- handoff
- graph workflow
- group conversation
- concurrent fan-out/fan-in
- human-gated checkpoint
- remote-agent or A2A boundary

### Knowledge needs explicit scope and lifecycle

Crew-level versus agent-level knowledge, LlamaIndex resources, ADK artifacts,
Haystack toolsets, LangGraph skills, and Microsoft skills all reinforce the
need to distinguish:

- durable organization or team knowledge
- runtime-loaded capabilities
- per-task context
- per-run state
- cross-run memory

Agent Caravan's domain and capability knowledge should remain durable,
versioned, owned knowledge artifacts. Runtime skills, toolsets, indexes, and
memory stores should be adapter projections unless explicitly promoted through
the builder workflow.

### Handoff and delegation are different

The reviewed runtimes repeatedly distinguish:

- handoff: control and task ownership move to another agent
- agents-as-tools: a coordinator retains ownership and calls a specialist
- code orchestration: application logic controls the next step

Agent Caravan should model this distinction in workflows and handoff
contracts instead of treating every delegated call as the same operation.

### Evidence is a first-class runtime concern, but not only a runtime concern

The products expose useful runtime evidence through events, traces, spans,
messages, run results, checkpoints, sessions, and evaluation records. Their
evidence generally does not explain which organization, team, role, overlay,
policy, or knowledge pack authorized the behavior.

Agent Caravan should correlate runtime evidence to its resolved configuration,
while leaving trace collection and persistence to the adapter/runtime.

### Team creation should not require learning the full artifact model

Team builders turn a short product or project description into a previewable
set of roles, skills, instructions, and workflows. Agent Caravan already has a
starter setup and AI-guided builder skill, but its richer artifact vocabulary
can still be an adoption cost. Keep the complete model authoritative while
offering a small guided setup as one optional path; expose domains,
specializations, overlays, and advanced policy decisions when the user needs
them. Preserve direct entry points for users who want to author, validate,
resolve, adapt, or inspect artifacts without following a setup journey.

### Generated teams need quality checks

The harness builders treat generated agent quality as part of the workflow,
using linting, evaluation rubrics, dry runs, or behavioral checks. Agent Caravan
validates artifact structure and resolved composition, which is necessary but
does not by itself prove that a projected team behaves well on representative
tasks. Consider adding task-level evaluations while keeping structural
validation, runtime conformance, and work-quality evaluation as distinct
results.

### Distribution is part of the adoption experience

Skills-first plugins and catalogs reduce the distance between finding a useful
workflow and loading it in a harness. Agent Caravan's package and bootstrap CLI
provide a reusable core installation path. Explore native plugin/catalog
distribution where it reduces friction, but keep those packaging formats in
runtime-specific projections rather than making one host's format canonical.

### Portability needs a visible compatibility report

Multi-harness products show that shared source material can be adapted to
different hosts, while also documenting host-specific capability differences.
Agent Caravan should report the evidence for each runtime and configuration:
what has been verified, what appears compatible but remains untested, and which
specific capabilities have known limitations. Reserve labels such as degraded
or unsupported for a demonstrated capability or execution path; absence of a
verified adapter is not evidence that a runtime cannot work. Where projection
is exercised, show whether important role, approval, and completion semantics
survive it. A list of verified configurations alone is not a boundary on
potential compatibility.

### Reuse existing teams before generating new ones

AgentPal's Team Pack First Discovery makes reuse an explicit first step before
creating or redesigning a team. Agent Caravan's builder should likewise inspect
existing organization, team, and specialization artifacts before proposing
new ones, then show what it selected and which responsibilities remain
uncovered. This complements artifact validation: reuse and coverage are setup
decisions, not only schema checks.

### Separate portable definitions from running orchestrators

AgentDef describes a portable structure for an individual agent; Agent Layer
projects repo-local source into several harnesses and can dispatch work; Codex
Orchestrator and OAK implement concrete execution workflows. These are related
but different product layers. Agent Caravan should keep its source ontology
portable, make projections and compatibility gaps inspectable, and leave live
task scheduling to an adapter or external orchestrator unless that becomes an
explicit product goal.

## Product-Specific Findings

### CrewAI

CrewAI is the closest conceptual comparison because it uses role-shaped agents,
crews, tasks, processes, and flows. Its configuration is more execution-focused:
agent persona, goal, tools, knowledge, model, task assignment, and process.

Useful patterns:

- explicit task context dependencies
- expected-output and structured-result contracts
- distinction between autonomous crews and precise flows
- shared crew knowledge versus role-specific knowledge
- explicit manager-led delegation

Do not copy the mixing of role identity, prompt persona, task assignment, and
runtime settings into one object.

### MetaGPT

MetaGPT is the closest organizational metaphor: an AI software company driven
by roles, actions, SOPs, environments, messages, and shared memory.

Useful patterns:

- explicit SOP and action vocabulary
- message causality and routing
- environment observation/action boundaries
- budget and checkpoint concepts

Do not make “software company” the Agent Caravan ontology. Preserve the more
general organization and team model so the framework can represent product,
operations, research, or governance teams.

### AutoGen and Microsoft Agent Framework

AutoGen is now primarily a compatibility and migration concern; Microsoft
directs new work toward Microsoft Agent Framework. The newer framework adds
typed executors and edges, sessions, middleware, checkpoints, and built-in
sequential, concurrent, handoff, group-chat, and Magentic orchestrations.

Useful patterns:

- agent versus workflow distinction
- executor and edge terminology
- agent session and checkpoint/resume semantics
- request/response human gates
- explicit handoff versus agent-as-tool behavior

Agent Caravan should target Microsoft Agent Framework before adding a new AutoGen
integration, while retaining an explicit legacy migration profile if needed.

### LangGraph and Deep Agents

LangGraph is low-level stateful orchestration infrastructure. Deep Agents is a
harness built on top of it with planning, filesystem/context management,
skills, memory, subagents, and human approval.

Useful patterns:

- framework versus runtime versus harness distinction
- thread, checkpoint, store, and context isolation
- coordinator-worker topology
- progressive disclosure for skills
- separate short-term state from cross-thread memory

Agent Caravan should not absorb graph scheduling, checkpoint implementation,
filesystem backends, or subagent transport.

### Google ADK

ADK provides agents, subagents, graph and dynamic workflows, sessions, state,
memory, artifacts, evaluation, and deployment. Gemini Enterprise adds an
agent-registration and discovery boundary, but that is not equivalent to an
organization catalog.

Useful patterns:

- local subagent versus remote A2A agent
- explicit graph versus dynamic orchestration
- typed node outputs and execution events
- pause/resume and human-input states
- discovery metadata separated from execution

Keep hosting, autoscaling, IAM, networking, and managed registry behavior in
the runtime integration.

### LlamaIndex

LlamaIndex is especially relevant for knowledge-heavy teams. Its typed events,
resources, context, workflow steps, handoffs, durable execution, and
observability provide a strong model for runtime evidence and data access.

Useful patterns:

- typed events with explicit start and stop boundaries
- context versus runtime resource separation
- agent-as-tool orchestration
- human-input events
- explicit at-least-once and idempotency contracts

Do not treat retrieval indexes, connectors, or runtime context as durable
organization knowledge without an explicit promotion step.

### PydanticAI

PydanticAI reinforces typed dependencies, reusable capabilities, structured
outputs, agent specifications, instrumentation, step persistence, and
evaluation datasets.

Useful patterns:

- agent specifications as runtime configuration
- capability and toolset composition
- typed dependency/context schemas
- structured output contracts
- deterministic testing and trace-based evaluation

Agent Caravan should distinguish runtime configuration overrides from its own
governed overlay model. A runtime override must not silently change ownership or
permissions.

### Haystack

Haystack provides typed components, directed pipelines, loop-based agents,
toolsets, skill toolsets, runtime state, hooks, tracing, and evaluation.

Useful patterns:

- typed component input/output contracts
- explicit exit and safety limits
- narrow specialist interfaces
- progressive disclosure through skill toolsets
- lifecycle hooks and human approval
- secure deserialization allowlists

Pipeline YAML or runtime tool overrides should not become Agent Caravan's
organizational source of truth.

### OpenAI Agents SDK

The SDK provides a clear runtime vocabulary: Agent, Runner, handoff,
agents-as-tools, tool, MCP server, context, guardrail, session, RunResult,
RunState, interruption, and trace/span.

Useful patterns:

- handoff versus manager-retained delegation
- blocking guardrails before side effects
- least-privilege MCP/tool access
- explicit approval and resumable interruption
- separation of task, session, run, and trace state

Agent Caravan should compile into these runtime objects when an OpenAI adapter is
selected, but should not treat an SDK Agent or session as a durable role or
domain boundary.

## Team-Building and Harness Product Findings

The products below compete most directly for the user's setup and workflow
attention. The findings are based on their published descriptions and
documentation; they are not hands-on usability or implementation evaluations.

### AgentPal

AgentPal is the strongest direct comparison found in the expanded search. Its
Pal model combines identity, responsibility, knowledge, skills, workflow,
memory, evaluations, boundaries, and collaboration rules. Team Packs bundle
team metadata, roster, knowledge, skills, workflows, runbooks, memory, and
evals. Its documented flow checks for an existing Team Pack, performs asset
preflight, creates a workflow execution contract, and checks closure and
assignment integrity. Thin bindings target Codex and Claude Code.

Useful patterns:

- search for a reusable team before creating one
- report selected team, open roles, loaded assets, and missing assets
- make execution and verification states explicit, including skipped or blocked work
- bind projects to shared team assets without copying the full library

Tradeoff for Agent Caravan: AgentPal's concepts overlap substantially with
team setup and operational evidence, so comparison should be against its
actual artifact and resolver model rather than only its runtime support. Its
README says v0.6 is ready for guided user testing, is not production ready, and
does not execute work itself. Agent Caravan's advantage is a more explicit,
general organization model with reusable role semantics, blueprints, owned
caravans, scoped domains/specializations, overlays, and resolution.
AgentPal's strongest challenge is its legible team-first operating flow.

### Agent Layer

Agent Layer provides one repo-local source for instructions, skills, approvals,
and MCP configuration, then syncs or launches supported coding agents from
that source. Its Agent Dispatch feature lets agents assign bounded work across
providers, with lifecycle tracking and durable Markdown evidence.

Useful patterns:

- one project-level source of truth with generated host-specific configuration
- visible client capability differences and dispatch lifecycle
- reusable skills imported from Git repositories while retaining local edits

Tradeoff for Agent Caravan: Agent Layer solves project configuration and
cross-provider dispatch. It does not document the same durable organization,
role ownership, caravan template, and scope-composition semantics. Study its
operator experience and projection model without turning Agent Caravan into a
dispatch daemon.

### AgentDef

AgentDef is a draft, framework-independent specification for defining portable
individual agents. It defines identity, instructions, skills, workflows,
memory, tools, runtime, evaluation, and telemetry areas, with manifests,
conformance checks, and importers for several ecosystems.

Useful patterns:

- normative conformance rules with machine-readable validation errors
- explicit semantic-versus-framework implementation separation
- import reports that preserve information and document conversion limits

Tradeoff for Agent Caravan: AgentDef's unit is an agent package. It does not
define an organization's ownership structure, a team's durable membership,
scoped domain composition, overlays, or the resolution of those artifacts.
Keep an eye on the spec's evolution and consider interoperability mappings
where its agent unit overlaps Agent Caravan projections.

### Codex Orchestrator

Codex Orchestrator is an executable orchestrator for persistent Codex and
Claude agents. It defines roles and sandbox settings in TOML, supports
architect/implementer/reviewer/QA/planner responsibilities, provides built-in
feature and bugfix workflows, and isolates write agents in Git worktrees.

Useful patterns:

- bind roles to explicit tools, sandbox permissions, and runtime backends
- enforce review outcomes and workflow deliverables
- isolate concurrent write work and make merge-back conditional on approval

Tradeoff for Agent Caravan: this product owns live agent lifecycle and
orchestration. Agent Caravan describes the source organization and runtime
contract. Treat orchestrators as potential execution targets and learn from
their role-to-runtime bindings, without absorbing their process manager or
workflow engine.

### OpenCode Agent Orchestration Kit

OAK is an OpenCode-focused software engineering harness with phase-specific
agents, versioned workflows, skills, bounded loops, independent review, and
local safety contracts. Its documented workflow can be used with OpenCode
alone.

Useful patterns:

- assign each delivery phase to an explicit owner
- retain workflow state and bound retry/iteration loops
- make independent review a visible completion stage

Tradeoff for Agent Caravan: OAK offers a concrete single-harness execution
experience and software delivery process. Agent Caravan can represent the
team and project knowledge that informs such a process, but does not itself
provide OAK's workflow runner or OpenCode-native setup.

### BMad Method and BMad Builder

BMad combines an end-to-end software delivery method with specialized roles,
workflow guidance, and a Builder that creates skills, workflows, and agents.
Its documentation describes stable v6.12 and a v7 preview alpha as of this
research snapshot.

Useful patterns:

- guide users from a task to the appropriate amount of planning
- preserve product and technical decisions as durable context
- make agent/workflow creation a first-class workflow
- offer modules for narrower needs instead of requiring every capability

Tradeoff for Agent Caravan: BMad is centered on software development and its own
method. Agent Caravan can serve wider organization/team models, but should make
its starter path as concrete and guided.

### RevFactory Harness

Harness v2 is a Claude Code team-architecture factory. It analyzes a project,
selects an execution mode and team pattern, generates agents and skills,
orchestrates them, and includes verification and an evolution workflow.

Useful patterns:

- inspect an existing setup before generating or extending it
- choose orchestration from workflow shape rather than team size
- generate the runtime artifacts users need to run the team
- turn usage feedback into explicit updates to the harness

Tradeoff for Agent Caravan: Harness is tied to Claude Code and emits its native
project files. Agent Caravan's differentiator remains its portable source model
and the ability to keep organization meaning separate from that projection.

### agents-team

This Claude Code plugin generates a complete project team from a product
description, provides a structured multi-agent meeting, and evaluates generated
agents and skills. Its README describes the project as v0.1.

Useful patterns:

- show the generated files and role count as an immediate result
- lint each generated agent before finishing setup
- make evaluation criteria and failures visible to the user

Tradeoff for Agent Caravan: the generator is Claude-specific and its generated
directory is its primary result. Agent Caravan should treat generated runtime
files as projections from validated source artifacts.

### Compound Engineering

Compound Engineering distributes a reusable development loop through skills
that run on many agent hosts. Its focus is to make each engineering task
benefit from research, planning, review, and retained learning.

Useful patterns:

- package a coherent workflow as composable skills
- provide host-specific installation guidance
- preserve lessons from completed work for later tasks

Tradeoff for Agent Caravan: the product centers on a workflow and learning loop,
not a durable organization catalog or team ownership model.

### Superpowers

Superpowers provides an opinionated software-development methodology through
composable skills, from clarifying intent through planning, TDD, and delegated
implementation. Its README lists support for a broad range of coding agents.

Useful patterns:

- make the workflow legible from the moment a coding session begins
- provide detailed, actionable procedures for common engineering tasks
- keep the skill set reusable across several hosts

Tradeoff for Agent Caravan: the methodology is intentionally focused on software
delivery. Agent Caravan should borrow clarity and usability without turning its
framework into a competing SDLC method.

### Everything Claude Code

ECC is a broad harness optimization and operations toolkit. It combines
skills, agents, commands, hooks, rules, memory, setup tooling, and security
features, and documents differences between host integrations.

Useful patterns:

- treat install, update, repair, and uninstall as product workflows
- make runtime-specific capability differences explicit
- connect reusable instructions with security and quality controls

Tradeoff for Agent Caravan: ECC's breadth creates a large configuration surface
and centers on harness behavior. Agent Caravan should prefer a smaller guided
path and keep runtime-specific mechanics in adapters.

### wshobson/agents

This repository provides a large catalog of agent plugins and skills, with
source content and installation adaptations for multiple coding tools.

Useful patterns:

- make reusable components easy to browse and select
- maintain a shared source while adapting host-specific formats
- publish capability and installation differences by host

Tradeoff for Agent Caravan: catalogs distribute components but do not by
themselves define team ownership, composition precedence, or organizational
provenance. Agent Caravan can complement a catalog by supplying those semantics.

### Agent Harness

Agent Harness is a portable skill focused on intent alignment, execution
contracts, continuity across session boundaries, and evidence-based acceptance.

Useful patterns:

- turn rough intent into reviewable scope and acceptance criteria
- scale durable state and audit controls to the task's risk
- carry task ownership and handoff evidence across runtimes

Tradeoff for Agent Caravan: it addresses the execution of a task, not the durable
definition of teams and organizations. Its contract and handoff ideas are
relevant to Agent Caravan's execution layer.

## Non-Goals Confirmed By The Research

Agent Caravan should not become:

- a model/provider abstraction library
- a tool or MCP execution framework
- a graph scheduler
- a RAG or indexing platform
- a memory database
- a tracing or evaluation vendor
- a deployment/autoscaling platform
- an IAM or network-security control plane
- a prompt-only agent registry

It may define contracts and adapter requirements for these capabilities, but the
implementation belongs to the selected runtime or an adjacent platform.

## Recommended Next Step

Use the companion design-decision document to turn runtime-framework findings
into schema and adapter-conformance work:

[Configuration and Design Notes](configuration-and-design-notes.md)

For product and onboarding work, consider an optional guided team-creation
path alongside direct entry points for authoring, validation, resolution,
runtime adaptation, and inspection. Also consider generated-artifact
evaluation, explicit runtime compatibility evidence, and native distribution
options. These are research recommendations, not approved implementation
commitments.
