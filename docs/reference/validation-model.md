---
type: Reference
title: Validation Model
description: Validation layers in Agent Caravan and the evidence established by each check.
---

# Validation Model

## Purpose

This page explains how the framework validates itself.

This is separate from validating code or work output produced by roles inside
the framework.

## Contents

- [Why the framework needs validation](#why-the-framework-needs-validation)
- [Validation layers](#validation-layers)
- [Keep validation claims separate](#keep-validation-claims-separate)
- [Validation rules](#validation-rules)
- [Result classes](#result-classes)
- [What must be validated](#what-must-be-validated)
- [Scenarios and regression](#scenarios-and-regression)
- [Behavior evaluation pilot](#behavior-evaluation-pilot)
- [Publication quality](#publication-quality)
- [Current implementation](#current-implementation)

## Why The Framework Needs Validation

The framework is not just documentation. It is a configurable system expected
to:

- resolve artifacts correctly
- preserve role coverage
- support overlays safely
- bind to runtimes coherently
- remain stable as it grows

That means the framework itself needs quality gates.

## Validation Layers

The validation model separates these questions. The current implementation
supports only some of these surfaces; see [Current Implementation](#current-implementation)
for its present scope:

- artifact structure and references: are artifacts well-formed and linked
  correctly?
- resolved team coverage: does the effective composition meet its required
  role, debate, and ownership obligations?
- runtime capability compatibility: can a configured adapter realize the
  capabilities requested by a profile?
- runtime verification evidence: which runtime, version, execution surface,
  configuration, and scenario have actually been exercised?
- task-level work-quality evaluation: does a produced result meet the specific
  task's acceptance criteria and quality rubric?

## Keep Validation Claims Separate

Do not treat one validation result as evidence for another. Passing artifact
validation does not establish team coverage. A resolved team that satisfies
coverage does not establish runtime compatibility. A capability declared
`native`, `adapted`, or `externalized` describes how an adapter realizes that
capability; it is not proof that the realization has been verified on every
runtime version or execution surface. Missing runtime evidence means
`unverified`, not `unsupported`.

Runtime conformance tests check execution semantics and the evidence needed to
support those semantics, such as handoff, approval, or completion behavior. They
do not establish the quality of work produced for a task. That requires a
separate evaluation against task-specific acceptance criteria, using the
relevant output and review evidence. A task evaluation must not be inferred from
structural validation, coverage, or runtime conformance results.

## Validation Rules

Validation is expected to vary by use case.

Example validation scopes:

- `local-experimental`
- `team-shared`
- `organization-shared`
- `runtime-production`

This allows experimentation without lowering the quality bar for shared or
published artifacts.

## Result Classes

Each validation layer has its own result. These general validation outcomes do
not replace the task-evaluation statuses described below:

- `pass`
- `degraded`
- `warn`
- `fail`

This allows a resolved instance to be usable but visibly weaker when some
non-critical expectations are not fully met.

## What Must Be Validated

At a minimum, the framework should validate:

- artifact structure
- references between artifacts
- configuration override legality
- deterministic resolution
- required role coverage
- required debate coverage
- runtime capability compatibility
- regression fixtures for representative examples
- task-level output quality for selected pilot scenarios, assessed separately
  from framework regression

## Scenarios And Regression

The framework is expected to support scenario-based validation for cases such as:

- standard ticket execution
- architecture-heavy change
- cross-domain implementation
- reduced local team shape
- alternate runtime compatibility case

These scenarios help prove the framework still behaves as expected after
changes.

Framework regression checks and task-output evaluation answer different
questions. Regression checks exercise framework behavior against expected
contracts; they do not by themselves grade the work produced for a user task.

## Behavior Evaluation Pilot

Task-level work-quality evaluation is a separate, small pilot. Begin with a few
representative tasks and criteria that reviewers can apply consistently. For
each evaluation, record the task and its acceptance criteria, the evidence
expected for each criterion, the evidence actually reviewed, the result, and
the evaluator or evaluation method. Keep every result tied to its scenario and
evidence; a small sample is not a general benchmark or a broad claim about team
quality.

For each criterion, record `pass`, `partial`, `fail`, or `not-evaluated`.
`not-evaluated` means no task output was assessed; it is not a pass. Keep these
task-evaluation statuses separate from framework validation results. The
illustrative contract in
[`tests/fixtures/representative-task-evaluation-pilot.json`](../../tests/fixtures/representative-task-evaluation-pilot.json)
lists acceptance criteria and expected evidence while explicitly recording
that no evaluation took place. This fixture is for discussion; it is neither a
machine-checked schema nor a result from an execution.

## Publication Quality

Shared artifacts should pass stricter validation than local experiments.

That includes:

- stable IDs and versions
- resolved references
- no material gaps hidden as soft warnings
- appropriate validation rules for the publication scope

## Current Implementation

The reference implementation now provides concrete validation surfaces:

- `agent-caravan validate` checks schemas for serialized portable artifacts in
  the catalog manifest's machine-readable bundles and files, execution
  workflows, policies, portable plan examples, and execution state templates.
  It validates all declared JSON Schemas, checks inventory coverage for scoped
  machine-readable and Markdown artifact roots, verifies Markdown artifact
  identity/version/scope metadata, checks distribution snapshot parity, and
  checks unique logical identities, selected references, and packaged skill
  source presence. Its JSON output lists coverage and checks it did not
  perform.
- `agent-caravan resolve` reports the effective active configuration, role
  coverage with provenance, and runtime capability compatibility. It reports
  runtime verification as `unverified` until scenario-specific execution
  evidence is attached, and task behavior as `not-evaluated` until an
  evaluation is run. These evidence states are distinct from whether a
  configured capability is supported by the selected adapter.
- `agent-caravan resolve --diagnostics` includes structured team coverage
  findings when resolution fails because a required role is missing.
- `agent-caravan validate-session` checks persisted task, session, run, and
  completion evidence for identity and linkage integrity.
- `agent-caravan validate-verification-record <path>` checks one adapter-produced
  runtime verification record against the portable schema and reports its
  scenario scope. It does not retrieve or authenticate evidence references.
- The Codex stage controller can run the dependency-wait scenario. It records controller-observed lifecycle
  timestamps across separate read-only CLI invocations; instructions are in [`parallel-scheduling`](../../tests/conformance/experiments/parallel-scheduling/README.md).
  This evidence is limited to that controller path and scenario.
- `make validate` runs the repository's resolver, packaging, orchestration,
  profile, and artifact regression suite.

These checks do not currently evaluate the quality of outputs produced by a
team for representative tasks. The pilot fixture documents a possible
task-level evaluation record; it is not wired into `make validate` and does not
claim that an evaluation has been run.

The repository gate checks the declared artifact inventory and portable
contracts. It does not run live runtime scenarios or assess task output
quality. Adapter implementations own runtime-specific execution and evidence
collection; task output quality requires a separate evaluation against task
acceptance criteria.
