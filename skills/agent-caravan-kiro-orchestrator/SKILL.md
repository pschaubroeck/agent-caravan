---
name: agent-caravan-kiro-orchestrator
description: Orchestrate bounded Agent Caravan work in the Kiro IDE using its native chat, Specs, permissions, and subagents.
---

# Agent Caravan Kiro IDE Orchestrator

In user-facing terminology the configured team is a caravan and each framework
role is a responsibility. The execution contract still uses `role` in artifact
types, field names, and role-turn evidence; retain those identifiers.

Use this skill as the Kiro IDE entry point for work governed by an Agent Caravan team. The portable plan owns role meaning, workflow order, approvals, and success criteria. Kiro features are runtime constructs used to carry out that plan.

## Runtime Boundary

- This entry point targets the Kiro desktop IDE. It does not launch or depend on Kiro CLI.
- Resolve the active Agent Caravan organization, team, runtime mapping, and workflow using the selected local profile and its configured sources.
- Confirm that the resolved runtime integration is `kiro-ide-agent-runtime`. If the selected harness or adapter differs, stop and report the mismatch.
- Use the installed Kiro IDE workspace and its permission prompts. Do not infer permissions from a role name, skill, or agent description.
- Use `runtime.repository_guidance` from the resolved configuration to select repository instruction files and follow its discovery and reference policies. Profile-local adapter overrides take precedence over packaged defaults; explicitly read files that Kiro does not load automatically.

## Execution

1. Inspect the task, active team, repository guidance, and relevant workspace context.
2. Validate the resolved configuration and build a runtime-neutral execution plan. Preserve its stages, role assignments, approval requirements, and termination criteria.
3. Apply the portable `knowledge_context.layers` to every role assigned to the task. Keep the shared layers once in the plan and make them available to each assigned role. Apply domain layers before specialization layers, and apply `role_guidance` only to the matching role. Then apply supplemental `context.team_context.knowledge_sources` in their listed order.
   When retrieving external sources, follow `policy.knowledge_access`; the plan carries curated guidance and references, not copies of source documents. If a runtime cannot provide the required shared context or enforce the retrieval policy, report the limitation and use an authorized fallback or stop as the plan requires.
4. Explain the planned role lanes and file ownership before making changes.
5. Use Kiro Specs when the task benefits from a requirements/design/tasks checkpoint. A Spec supplements the Agent Caravan plan and does not replace its workflow or approval rules.
6. Use Kiro custom agents or subagents only for work authorized by the portable plan. Give each work item a narrow objective, disjoint ownership, and required evidence. Dispatch ready work while unrelated items wait on dependencies; resume only the affected item when its answer arrives. Follow the plan's declared serial fallback when the harness cannot do this.
7. Keep shared decisions, integration, approval checks, and completion assessment in the coordinating session.
8. Run the focused repository checks required by the task and report the exact commands and outcomes.

## Permissions And Evidence

- Follow Kiro's current capability permissions. Preserve `ask` or `deny` for protected actions unless the task has authorized a narrower operation and the operator approves it in Kiro.
- For an approval-dependent action, retain the requested action, decision, actor, scope, and order when the IDE exposes them. If attribution is unavailable, stop that action and report the missing evidence.
- Do not claim a subagent ran, a work item ran in parallel, or a human approved an action based only on model text. Record work-item lifecycle (including `not-applicable` conditional items), Kiro worker references, dependency references, and timestamps only when they are visible and attributable.
- Record the app version, selected agent/model when visible, task and plan IDs, handoffs, decisions, and concise verification results when available.
- Never retain credentials, hidden reasoning, or unbounded transcripts in Agent Caravan records.
- Kiro IDE activity is operator-visible evidence, not a complete machine-readable trace. Mark missing evidence as unavailable.
- The Kiro orchestrator instructions describe how to consume portable knowledge; a repository-local Kiro code bridge and live knowledge-consumption conformance are not present. Do not imply that the Kiro harness has been verified to apply these instructions correctly.

## Completion Report

Report the objective, selected team and runtime mapping, roles actually involved, decisions and handoffs, files changed, focused validation results, approvals, and unresolved conditions. Distinguish Kiro-reported results from independently verified checks. Do not claim live Kiro conformance unless the runtime behavior was exercised and its evidence retained.
