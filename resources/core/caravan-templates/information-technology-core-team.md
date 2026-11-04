# Caravan Template Artifact: information-technology-core-team

## Purpose

- `id`: `information-technology-core-team`
- `name`: `Information Technology Core Team`
- `version`: `1.1.0`
- `scope`: `local`
- `mission`: Provide the default seven-role AI development team shape for planning, implementation, validation, architectural review, and release execution.
- `summary`: This is the default organizational core caravan template derived from the current Information Technology Core Team operating model.

## Team Composition

- `core_roles`:
  - `program-manager`
  - `product-owner`
  - `tech-owner`
  - `engineer`
  - `quality-engineer`
  - `software-architect`
  - `release-manager`
- `optional_roles`:
  - none in the base template
- `required_coverage`:
  - process/governance coordination
  - product intent and scope definition
  - technical planning and decomposition
  - implementation ownership
  - quality and readiness ownership
  - structural/architectural escalation
  - release and promotion mechanics
- `replacement_rules`:
  - any role may be replaced only if equivalent coverage is preserved
  - `software-architect` and `release-manager` may be omitted only if the resolved configuration still preserves their required coverage or explicitly narrows the operating model

## Stage Flow

- `stages`:
  - intake and triage
  - product definition
  - solution and testability debate
  - technical breakdown
  - implementation
  - validation
  - architectural review when structural or cross-system risk is triggered
  - review resolution when disputed
  - release flow
  - closeout and follow-up
- `stage_owners`:
  - `program-manager`
  - `product-owner`
  - `product-owner`, `tech-owner`, `quality-engineer`
  - `tech-owner`
  - `engineer`
  - `quality-engineer`
  - `software-architect`
  - `engineer`, `tech-owner`, `software-architect`
  - `release-manager`
  - `program-manager`
- `stage_outputs`:
  - routed and triaged work
  - scoped requirements and acceptance criteria
  - aligned solution and testability direction
  - engineering-ready technical breakdown
  - working implementation
  - readiness evidence
  - architectural guidance or approval as needed
  - resolved review direction
  - merge/pipeline/release outcome
  - tracked follow-up and closure state

## Debate Model

- `mandatory_debates`:
  - `solution + testability debate`
  - `review resolution debate`
- `triggered_debates`:
  - `scope debate`
  - `risk debate`
  - `priority debate`
  - `technical debt debate`
- `debate_participants`:
  - `solution + testability debate`: `product-owner`, `tech-owner`, `quality-engineer`
  - `review resolution debate`: `engineer`, `tech-owner`, `software-architect`
  - `scope debate`: `product-owner`, `tech-owner`
  - `risk debate`: `quality-engineer`, `tech-owner`, `software-architect`
  - `priority debate`: `program-manager`, `product-owner`, `tech-owner`
  - `technical debt debate`: `engineer`, `tech-owner`, `product-owner`, `software-architect`
- `debate_purposes`:
  - `solution + testability debate`: align product intent, technical feasibility, and testability before implementation; involve `software-architect` when a structural trigger applies
  - `review resolution debate`: resolve disputed review feedback and converge on a viable solution
  - `scope debate`: reconcile requested outcomes with realistic implementation scope
  - `risk debate`: evaluate meaningful quality, structural, or operational risk
  - `priority debate`: resolve sequencing or competing-work conflicts
  - `technical debt debate`: evaluate shortcuts or deferred cleanup with future cost

## Blocking Model

- `blocking_lanes`:
  - `program-manager`
  - `product-owner`
  - `tech-owner`
  - `engineer`
  - `quality-engineer`
  - `software-architect`
  - `release-manager`
- `blocking_guardrails`:
  - roles may block only inside their legitimate ownership boundary
  - preference-only disagreements should not become blocks
  - unresolved blocks should have an escalation or debate path
- `block_resolution_notes`:
  - use debate flows first when disagreement is substantive
  - escalate to broader coordination or human review when the role-level resolution path is exhausted

## Documentation Model

- `documentation_ownership`:
  - `program-manager`: process-state and approval-routing visibility
  - `product-owner`: product-facing clarification and release-oriented narrative
  - `tech-owner`: design notes and engineering expectations
  - `engineer`: code-adjacent documentation
  - `quality-engineer`: verification evidence and readiness rationale
  - `software-architect`: architecture guidance and structural decision records
  - `release-manager`: delivery-state and release-status artifacts

## Governance Notes

- `governance_rules`:
  - new dependencies, integrations, or external tools may trigger security or governance obligations
  - the team should route these through `program-manager` after identification by the relevant technical lane
- `governance_handoffs`:
  - `tech-owner` identifies the need
  - `program-manager` routes and tracks the approval path
  - implementing roles proceed only where safe within that constraint

## Runtime Expectations

- `required_capabilities`:
  - `structured_output_contracts`
  - `dynamic_context_loading`
- `preferred_capabilities`:
  - `role_handoff`
  - `execution_trace`
  - `result_structuring`
- `optional_capabilities`:
  - `background_execution`
  - `durable_memory`
  - `human_confirmation_points`

## Validation Hints

- `invariants`:
  - the base team must preserve all seven responsibility lanes unless a narrower derived team explicitly redefines coverage
  - mandatory debates must preserve participant coverage
  - implementation, quality, and product ownership must remain distinct
- `coverage_expectations`:
  - all core roles should resolve in the default template
  - blocking, debate, and documentation coverage should all remain complete
- `validation_notes`:
  - overlays that remove or replace roles must preserve required coverage and mandatory debate participation
  - ready work may continue while unrelated work waits on a role handoff; only unresolved decisions inside the owning role's blocking boundary gate dependent work
