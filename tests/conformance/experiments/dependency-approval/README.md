# Dependency approval experiment

This is a runtime-neutral, experiment-specific case pack for the first live dependency-approval study. It contains exactly two cases: `dependency-approval-accept` and `dependency-approval-reject`. The format follows the existing conformance scenario envelope (`scenario_version`, `scenarios`, `task`, and `expected`) and can be loaded independently of the shared scenario catalog.

## Experiment execution profile

`execution-profile.json` is the session-scoped portable profile for both cases. Supply it to framework resolution as an `execution-profile` artifact in the experiment's resolver bundle, select it with `context.execution_profile_id: "dependency-approval-experiment"`, and include it in the experiment-local organization catalog's published artifacts. The profile targets the existing Information Technology Core Team blueprint and references its existing safety policy; it does not bind to a runtime. Keep this registration in the experiment input bundle rather than publishing the experiment profile in the shared catalog. Package identities and all license, vulnerability, maintenance, compatibility, and footprint criteria remain pinned external run inputs; the profile intentionally defines none of them.

## Candidate eligibility

These criteria give “accept” and “reject” a defined basis and prevent the agent from inventing thresholds during a run. Use the organization's actual policy when evaluating organizational fit. To test the workflow without organization-specific policy, use explicit, pre-agreed experiment criteria and label them as experiment-defined; such a run says nothing about compliance with the organization's policy. In either mode, criteria must be pinned before execution.

The cases intentionally contain no package identity, release, current package fact, or invented policy threshold. Before either case is run, its external candidate-evidence input must be populated and pinned with the exact candidate/release and artifact hash; the documented project need; compatibility; license evidence and its governing criterion; dated vulnerability evidence and threshold; maintenance evidence and criterion; dependency footprint; and source references with collection times. The acceptance candidate must satisfy the pre-agreed hard criteria. The rejection candidate must fail at least one meaningful pre-agreed hard criterion, with that failure independently evidenced. A case is ineligible if required evidence, governing criteria, or provenance is missing or mutable.

Candidate identities and evidence belong to the experiment run inputs, not this reusable case definition. Do not install or add the rejection candidate. Use a disposable repository and only permit dependency-manifest changes after recorded human approval in the accept case. Agent Caravan has no runtime dependency lockfile; do not add one solely for this experiment. Verify the resolved installation in an isolated target outside the repository and retain its package-manager report as evidence. The reject case stops after the independently verified hard-criterion failure and review, records the rejection with Program Manager participation, and leaves the dependency manifest unchanged. Because that candidate is ineligible, the reject case must not request or deny dependency approval.

## Semantic expectations

The role IDs and stage IDs name organizational responsibilities and workflow semantics; they do not prescribe a runtime's agents, workers, tools, UI, or execution model. The expected `active_roles`, `completed_stages`, handoffs, approvals, events, evidence, and artifact records describe the behavior to observe through an adapter.

The profile makes its human-approval stage conditional on candidate eligibility. The accept case requires approval evidence; the reject case ends after review and rejection, so the profile does not impose an unconditional approval-evidence requirement.

`required_event_order` uses ordered `{kind, status}` pairs. Timestamps and event provenance are supplied by the normalized execution result. `required_evidence_records` are partial evidence-record matches; `require_references: true` requires each matched record to have source references. Case-required `source` values distinguish `human-reviewed`, `reported-by-external-tool`, and `independently-verified` evidence. Other provenance values may be used where appropriate, as listed below. An evidence record with status `passed` means the evidence assertion/record is successfully substantiated. In the reject case, `failed-hard-criterion` with evidence status `passed` means the failure of the candidate criterion is substantiated; the `candidate-assessment` event carries the failed decision. No approval record is expected for that ineligible candidate.

In the accept case, the required dependency-manifest artifact record must be modified, sourced as `independently-verified`, and include references that attribute the change. The package-manager resolution report and isolated installation result are evidence, not repository lockfile changes. In the reject case, any recorded dependency-manifest artifact is forbidden, regardless of its status; the candidate must not appear as an added, modified, removed, or otherwise recorded dependency artifact.

The accept case requires a `program-manager` approval-lane decision by the `program-manager` role and links that approval record to a `human-reviewed` evidence record by evidence ID. It first expects a `dependency-change/blocked-until-approved` event, followed by `approval/approved` and the applied change. Its `event_order_constraints` also asserts that every matching `dependency-change/applied` event follows the approval event. Compared events must be attributable to the same task and run, include evidence references, and have timestamps. This exercises the approval gate without treating a policy-denied action as an expected successful rejection.

The shared conformance comparator evaluates required evidence, artifact and approval records, forbidden artifact and event records, and ordered, attributed execution events. These scenarios define expected behavior; they do not imply that a live execution has occurred or passed.

## Intended outcomes

- **Accept:** complete need and candidate assessment, independent review, recorded human approval, one scoped dependency-manifest change, an isolated resolved installation, and passing verification.
- **Reject:** complete assessment and independent review, evidence for one failed hard criterion, Program Manager records rejection without requesting or denying approval, no dependency-manifest change, and no candidate installation.

Both are workflow outcomes, not assertions that any candidate currently meets or fails a real organization's policy. A blocked, unavailable, unverified, or simulated run must not be reported as live conformance success.

## Adapter readiness

The case definitions use the shared `load_conformance_scenarios` and `run_conformance_suite` contract; an adapter supplies its own executor and preparation function. The repository includes Codex and OpenCode adapter bridges. The OpenCode CLI surface is limited to read-only work; approval-dependent execution requires its server/API surface and an attributed human decision. Both complete Codex cases and the retained OpenCode receipts passed the same case pack on September 30, 2026, preserving equal prepared portable plans and selected normalized outcomes. Codex's experiment controller executes the approved pinned edit directly; OpenCode retains native permission and command events. Controlled model/performance parity and equivalent native enforcement are not established. The Codex dry-run test intentionally remains non-conformant because it cannot produce the required candidate evidence, human approval, dependency changes, or verification. It checks truthful adapter behavior and case-pack wiring only; it is not experiment evidence. See the [adapter comparison](../../../../docs/integrations/codex-opencode-comparison.md) for completed results and execution limits.

For OpenCode, `bundle.py` assembles an experiment-local resolver input without publishing the experiment profile in the shared catalog. `OpenCodeStageRunner` records one read-only role stage from native CLI JSONL events. `result_builder.py` accepts those stage receipts, pinned candidate inputs, independent verification receipts, explicit human attestations, and, for the accept case, a matching native approval receipt and verified manifest change. It rejects missing or mismatched provenance. The historical approval in `inputs/candidate-evidence.json` does not authorize a new OpenCode run.

`run_opencode.py` advances one read-only stage per call and saves its native receipt under a caller-selected state directory outside the repository. It pauses for `external-receipts.json` when a stage needs human or independently verified evidence. Its controller keeps the accept/reject case labels; model prompts use opaque task and run IDs and omit expected disposition and precomputed criterion results. `evaluate(case_id)` calls the shared OpenCode conformance suite only after all stage and external receipts exist. The caller supplies the native approval exchange separately for the accept case.

An explicit `allowed_previous_models` list permits resuming after an operator-directed model change. New stages must use the current model; saved model identities remain intact. Such a run is not a controlled comparison of one model across adapters.

After a known failed approved command, `approval_receipt` may contain `initial_receipt` and `retry_receipts`. Each retry must reference the exact original human approval, task, run, and action, use fresh native identifiers, and follow the previous attempt. Controller authorization is derived from the original approval; it is not another human decision. The result retains the original failure and retry history.

The planned experiment requires both cases to execute through real runtime surfaces in each compared binding. A dry-run, reference fixture, partial run, or unavailable runtime capability may validate wiring or expose a blocker, but does not count as either case's experiment result.

```python
from agentcaravan.foundation import load_conformance_scenarios, run_conformance_suite

cases = load_conformance_scenarios(
    "tests/conformance/experiments/dependency-approval/cases.json"
)
suite = run_conformance_suite(cases, adapter_executor, prepared=prepare_scenario)
suite.raise_for_failures()
```

The `adapter_executor` and `prepare_scenario` functions belong to the selected runtime integration; neither belongs in this shared case pack.

## Evaluation separate from conformance

The assertions above check whether the recorded process and repository outcome satisfy the experiment contract. They do not judge whether the dependency decision was technically sound or whether the workflow added value. For each real run, a human evaluator should answer these separately and cite evidence:

This optional workflow study is separate from adapter acceptance and does not block adapter conformance or comparison.

- Was the project need specific, and were plausible alternatives considered?
- Was the candidate evidence complete, current, and tied to the exact release and artifact hash?
- Were the supplied hard criteria applied consistently, with the decision rationale supported by evidence?
- Was the accept or reject decision technically proportionate to the evidence?
- Did team responsibilities, independent review, or policy catch a material issue that an output-only review might have missed? If so, identify it.
- Did the workflow improve decision quality enough to justify its time and coordination cost?

Keep evaluator answers and rationale as a separate human-reviewed evaluation record. Do not convert positive behavioral ratings into conformance passes or treat conformance as proof of decision quality.

## Evidence provenance and extension boundaries

For each material evidence item, identify its provenance as one of `directly-observed-by-agentcaravan`, `reported-by-codex`, `reported-by-external-tool`, `independently-verified`, `derived-by-agentcaravan`, `human-reviewed`, `unavailable`, or `unverified`. Preserve source references, collection times, owner role, and stage where applicable, using evidence `source`, `references`, `owner_role`, `stage_id`, and `metadata` fields. The evidence status vocabulary has no `unavailable` value; encode that provenance in `source` or `metadata`, include the reason, and use `status: unverified` where appropriate. Missing evidence remains missing and is never promoted to verified. Codex-native traces and artifacts remain identifiable through their source and native references when normalized evidence is emitted. Do not infer approvals, role actions, handoffs, enforcement, or policy outcomes from repository state alone.

The optional portable `execution_events` field and its task/run attribution, timestamps, and evidence references address the experiment's specific need to verify event order and approval gating. It is not a generalized harness or evaluation layer. The Codex binding owns role mapping, Codex-specific instructions and execution context, approval interaction, tool availability and invocation, repository access, interruption/resumption/failure behavior, runtime/model metadata, native traces, and translation of Codex evidence. Native Codex run identity is retained alongside Agent Caravan's portable run identity. For any proposed extension, record the specific requirement, why the current shape is insufficient, whether it belongs to the portable contract or Codex binding, whether it is experiment-specific, and what later evidence would justify generalization. No further shared abstraction is justified by this two-case study; revisit generalization only if another independently implemented harness demonstrates the same concrete representation gap.

A successful run can establish conformance for the tested Codex binding, show that this portable intent can be projected into Codex, and provide evidence about whether the team process adds value in these cases. It cannot establish cross-harness conformance, broad runtime compatibility, universal evaluation criteria, production-grade enforcement, or a generalized evaluation platform. Cross-harness claims require this same case pack to pass through a second independently implemented binding.

Behavioral evaluation must use a fixed question set and be recorded separately by human reviewers. Record reviewer rationale, disagreements, and repeat-run stability; do not alter deterministic conformance pass/fail based on these ratings.

## Staged Codex controller

`run_codex.py` advances one role stage through the existing Codex adapter, saves
its native thread and plain report, and resumes without repeating completed
stages. `codex_result_builder.py` assembles only validated native stages and
scoped external receipts for the shared comparator. Candidate and resolved
framework inputs are pinned across resumes.

Human technical-need, review, exact-action, and completion attestations belong
to the specific run. Model reports remain `reported-by-codex`. The manifest
edit uses a pinned direct argv command in the external controller after its
human approval gate; it is not native Codex permission enforcement. Failed or
uncertain actions retain a failure receipt and block automatic repetition.
See the [controller plan](../../../../docs/integrations/codex-experiment-controller-plan.md).
