---
type: Reference
title: Codex Dependency Experiment Controller
description: Implementation plan for running the dependency experiment through the existing Codex adapter.
---

# Codex dependency experiment controller

## Scope

Use the existing Codex adapter and the dependency experiment's portable profile,
case pack, and pinned candidate inputs. Implementation stays under
`tests/conformance/experiments/dependency-approval/`. This adds experiment
execution and evidence collection, not another adapter or shared framework.

## Slice 1: execution and evidence

- Goal: run separately attributed role stages and normalize their external evidence.
- Owners: stage worker owns `codex_stage_runner.py` and its tests; assembler worker
  owns `codex_result_builder.py` and its tests; main session owns the resumable
  driver, approved-action runner, contracts, and integration.
- Acceptance: use the existing Codex adapter, retain actual native thread IDs and
  lifecycle events, omit reasoning, demote model claims, reject mismatched or
  incomplete native receipts, and expose explicit external approval enforcement.
- Focused validation: runner, assembler, driver, and action tests including
  wrong identity, malformed traces, failed commands, stale decisions, input
  changes on resume, and missing evidence.
- Dependencies: existing bundles, adapter surfaces, shared comparator.
- Exit: `enterprise-reviewer` review resolved, `quality-gate` preflight/full/focused
  checks pass, intended experiment boundaries confirmed, commit.

## Slice 2: live stage assessment and protected action

- Goal: execute both candidates through separate Codex role invocations using
  requested GPT-6.1 Sol and disposable repositories.
- Owner: main session; independent local checks run separately from model reports.
- Acceptance: opaque task/run IDs, pinned facts, no rejection-candidate install
  or edit, human technical-need/review attestations linked to the actual reports,
  an exact-action approval request before dispatch, and retained approved-action
  controller command evidence plus independent manifest/install/runtime checks.
- Validation: observe native version/thread/report structure and timestamps,
  verify unchanged reject manifest, verify exact accept diff and wheel hash.
- Dependencies: slice 1 committed; narrowly authorized live data transfer and
  actual human decisions. Existing OpenCode decisions are not relabeled.
- Exit: all stages have real receipts and required scoped attestations. A genuine
  human decision is a checkpoint; no workflow-value questionnaire is required.

## Slice 3: conformance and comparison

- Goal: run both fully attributed Codex results through the existing comparator
  and compare their portable semantics with the recorded OpenCode results.
- Owners: main session integration/report; `enterprise-reviewer` evidence review;
  `quality-gate` final integrated checks.
- Acceptance: both cases pass without changing case expectations; runtime
  differences remain explicit, including external Codex approval enforcement,
  no claimed native delegation, and historical OpenCode model differences.
- Validation: shared cases, attributed order/provenance, full/focused repository
  gates, and evidence-backed comparison report.
- Dependencies: complete live receipts and human completion endorsements.
- Exit: review findings corrected, gates pass, report committed. No controlled
  model/performance parity claim unless matched-model repetitions exist.

## Operational boundaries

Independent implementation lanes run in parallel with disjoint file ownership.
No GitLab mutation is needed, so the GitLab operator is unassigned. Source facts
stay historical and pinned. Human gates surface in the main chat after concrete
reports exist. Failed native actions remain failures rather than being inferred
successful from model text or later repository state.

The approved manifest edit is executed directly by the external controller as a
pinned argv command after validating the attributed human decision. Codex role
stages remain read-only invocations through the existing adapter. This is
external enforcement, not a native Codex permission exchange or a Codex-executed
write. The receipt identifies the controller operation separately from native
Codex threads. Resume pins the complete resolved bundle in addition to case
and candidate inputs.

## Completion record

All three slices completed on September 30, 2026. The controller implementation
was reviewed and committed as `065e85f`. Both live cases retained separately
observed native role stages and freshly scoped human attestations. The accept
case retained the approved controller action and independent manifest, wheel,
isolated-install, and runtime checks. Both Codex cases passed the unchanged
shared comparator with zero mismatches. Retained OpenCode receipts also passed
reevaluation; complete prepared portable plans and selected normalized outcomes
compare equal. See the [comparison report](codex-opencode-comparison.md) for
evidence locations and limits. Additional matched-model runs are optional work
for a controlled model comparison, rather than remaining work in this plan.
