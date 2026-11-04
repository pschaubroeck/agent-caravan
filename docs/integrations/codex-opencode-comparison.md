---
type: Research
title: Codex and OpenCode Dependency Experiment Comparison
description: Comparison of Codex and OpenCode adapter behavior for dependency approval scenarios.
---

# Codex and OpenCode dependency experiment comparison

## Scope and acceptance

This comparison evaluates adapter behavior against the two dependency-approval
cases. Human ratings of workflow value are not an adapter acceptance gate.
Results apply to each experiment binding together with its controller and
external evidence collection.

Both bindings must preserve the same portable execution contract and use the
same pinned candidate evidence and experiment-defined criteria. A live parity
claim requires both complete cases to pass through each binding with attributed
runtime, human-decision, artifact, and verification evidence. Projection tests,
read-only probes, and historical prose reports cannot replace those executions.

## Portable contract

The experiment has independent resolver bundles for the actual Codex and OpenCode
runtime artifacts. Both resolve and prepare successfully. The complete portable
plans compare equal, including task, responsibility assignments, stages,
communication, topology, reasoning, capabilities, policy, tools, evidence,
termination, and required outputs. Runtime-specific projections remain outside
that portable plan.

The regression lives in
`tests/conformance/experiments/dependency-approval/test_bundle.py`.

## Observed execution boundary

The local OpenCode study recorded passing accept and reject cases on September
30, 2026. Those results include the scoped human attestations, independent
checks, native session receipts, and the protected-action approval exchange.
The accept result retains an approved command that failed because of sandbox
access and its exact controller-authorized successful retry. The original human
decision remains separate from controller authorization.

The current Codex CLI surface performs a single invocation. It preserves native
JSONL thread evidence and treats model-generated evidence as `reported-by-codex`.
The experiment now adds a staged controller and separately observed role
sessions around that surface. It has no native permission request/reply
collector. Its caller-supplied
workspace-write approval record is bound to scenario/task/plan/run, but does not
observe an exact-action native approval exchange.

Earlier local Codex role reports did not retain native receipt identities or
execution metadata. They remain historical context rather than controlled
comparison evidence.

## Comparison matrix

| Requirement | OpenCode study | Codex CLI with experiment controller |
|---|---|---|
| Portable plan preservation | Pass | Pass; full-plan equality tested |
| Requested model identity | Preserved per stage/approval | Explicit optional model pin now recorded |
| Effective model identity | Not independently established | Unverified; requested identity is not telemetry |
| Complete accept/reject study | Both passing; retained receipts reevaluated | Both passing with scoped human completion endorsements |
| Separate role-stage evidence | Native stage sessions retained | Experiment controller retains separate native threads |
| Human review attribution | Scoped external attestations retained | Experiment assembler validates scoped external attestations |
| Protected-action approval | Native permission events plus scoped human decision | External controller validates exact-action approval before direct argv execution; no native exchange |
| Changed artifact and isolated installation | Independently checked in accept study | Approved sole manifest edit and fresh isolated installation independently checked |
| Reject no-change/no-install outcome | Recorded for completed reject study | Passing reject case; clean checkout and tool-free native receipts |

## Live probe findings and corrections

Codex CLI 0.159.0 was invoked with requested model `gpt-6.1-sol` after explicit
approval for the evidence transfer. A bounded HELLO probe succeeded. The first
two read-only case invocations timed out at five minutes each; those attempts
do not establish a model-availability failure or a conformance result.

Shorter, tool-free single-invocation probes exposed an output-contract gap:
the surface validated required result fields and enum values without supplying
that contract in its prompt. Missing collections and invented execution or
degradation modes were rejected. The prompt now supplies the canonical
`execution-contracts.schema.json` definitions and required envelope fields.
Validation remains strict, and model-authored evidence remains demoted.

After this correction, both final probes returned valid normalized results with
native Codex thread identities. Both reported `blocked`, with Engineer assessment
stages only. The shared comparator correctly rejected them for missing complete
responsibility coverage, handoffs, externally attributed human/independent
evidence, and required ordered events; accept also lacked approval and the
verified manifest change. This is observed incomplete execution, not two passing
Codex experiments or proof that Codex itself cannot support the workflow.

These probes are integration diagnostics, not complete substitute experiments.
The pinned inputs are historical September 29 snapshots; no candidate facts
were selectively refreshed for one harness.

## Completed comparison and limits

Both complete Codex cases passed the existing shared comparator with zero
mismatches on September 30, 2026. The retained OpenCode receipts also passed
reevaluation through the same current case pack, without new OpenCode runtime
calls. Complete prepared portable plans compare equal for each case using a
common comparison task identity. Selected normalized outcomes also compare
equal: completion status, completed stages, active roles, handoffs, candidate
decisions, artifact kinds/statuses, and ordered required events.

This establishes conformance to these two tested portable cases across the two
bindings. Their runtime evidence and enforcement mechanisms remain different.
The OpenCode accept case changed from GPT-6 Sol to GPT-6.1 Sol, and its reject
case used GPT-6 Sol. All new Codex stages requested GPT-6.1 Sol. These histories
cannot establish controlled model or performance parity. Requested model pins
also do not independently establish effective-model identity.

The experiment-local Codex staged runner and attributed receipt assembler are
implemented, using independent Codex-native validation. They preserve opaque
task/run identities, separate role invocations, timestamps, scoped human
decisions, and independent artifact/runtime checks. Resume pins the complete
resolved framework bundle and candidate inputs. Failed or uncertain actions
block automatic repetition. The reviewed implementation passed preflight,
237 repository tests (five skips), and 46 focused experiment tests.

Both live need-assessment, candidate-assessment, and Tech Owner review stages
completed using requested GPT-6.1 Sol, each in a separate native thread. The
operator endorsed the technical-need baseline and both candidate decisions:
eligible jsonschema and rejected fastjsonschema under the pinned criteria.
Their reports assess supplied evidence; they are not independently collected
source or wheel checks. The complete reject case passed the shared comparator
with zero mismatches after the operator endorsed its completion.

The accept case received request-scoped human approval. Its external controller
executed only the pinned manifest command, and independent checks confirmed the
sole addition of `dependencies = ["jsonschema==4.26.0"]`. The pinned wheel hash
matched, and a fresh isolated environment installed that wheel and its four
base dependencies. All ten baseline Draft 2020-12 schemas passed schema checks;
a valid portable plan passed and an invalid local sibling-reference instance
failed. One remote reference resolution request was refused, with zero network
calls under network guards. Three current-source schema integration tests also
passed in the fresh environment. The baseline checkout lacks the later
Agent Caravan schema-validation module, so these integration tests are explicitly
separate from the baseline-schema harness. Runtime checks used Python 3.14.4;
they do not establish execution coverage across every supported Python version.

All seven accept-case role stages completed, and the operator endorsed the
specific completion report before its passing comparator evaluation. A
supplemental independent check
explicitly observed and asserted zero calls to five guarded network APIs; its
later timestamp is separate from the primary verification receipt used by the
model verification stage.
OpenCode-native receipts and old human attestations must not be relabeled as
fresh Codex evidence. The protected-action gate must explicitly distinguish
external controller enforcement from a native permission exchange.

The planned implementation, live execution, and conformance comparison slices
are complete. A controlled model comparison would require additional
matched-model OpenCode runs. Broad harness compatibility, equivalent native
enforcement, and workflow-value improvement remain outside this experiment's
claims. Human workflow-value ratings are optional. No new shared evaluation
abstraction is justified by these two cases.

## Reproduction gates

```text
make preflight
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests/conformance/experiments/dependency-approval -p 'test_*.py' -v
python3 -m json.tool catalog-manifest.json
git diff --check
```

Private native receipts remain in the operator-approved external experiment
directory. They are not embedded in the shared catalog or installed runtime
configuration.

Within its `comparison-codex-6.1` subtree, the evidence index is:

| Observation | Retained source |
|---|---|
| Initial timeout outcomes | `summary.json`, both initial case JSON files, and `run-initial-comparison.py` with the 300-second limit |
| HELLO connection result | `connectivity-probe.json` |
| Missing envelope fields | `bounded-readonly-retry/summary.json` and native case receipts |
| Invalid execution/degradation values | `contract-envelope-retry/summary.json` and native case receipts |
| Final normalized blocked results | `schema-contract-retry/summary.json` and native case receipts |
| Cross-adapter matrix and limitations | `comparison-summary.json` |
| Separate Codex role stages and scoped external evidence | `staged-experiment/dependency-approval-{accept,reject}/` |
| Human-readable candidate and Tech Owner reports | `staged-experiment/candidate-review.md` |
| Exact approved action and reject completion | `staged-experiment/action-and-rejection-review.md` |
| Fresh acceptance checks and limits | `staged-experiment/dependency-approval-accept/independent-verification.json` |
| Supplemental observed network counters and retained harness | `staged-experiment/dependency-approval-accept/network-verification-supplement.json`, `independent-runtime-harness.py` |
| Human-readable accept completion report | `staged-experiment/accept-completion-review.md` |
| Both final Codex conformance results | `staged-experiment/dependency-approval-{accept,reject}/conformance-results.json` |
| Retained OpenCode receipt reevaluation | `staged-experiment/opencode-{accept,reject}-receipt-reevaluation.json` |
| Final portable-plan/outcome comparison and limits | `staged-experiment/final-comparison-summary.json` |
