# Policy Artifact Specification

## Purpose

A `policy` artifact defines guardrails and approval behavior for an execution
profile. Policies constrain what an activated workflow may do; they do not grant
permissions, redefine role responsibilities, or replace runtime approval
mechanisms.

## Required Identity

Every policy must include:

- `artifact_type`: `policy`
- stable `id`
- artifact `version`
- `scope`
- `policy_type`
- `input_validation`
- `tool_authorization`
- `approval_requirements`
- `retry`
- `escalation`
- `termination`

Recommended `policy_type` values are `guardrail`, `approval`, `quality`, and
`termination`. A policy may combine these concerns when they share ownership
and lifecycle.

## Input And Tool Controls

`input_validation` describes required task facts, trusted sources, and
conditions that block execution. `tool_authorization` describes allowed tool
classes and explicitly sensitive operations. A policy should prefer deny-by-
default behavior for operations that mutate remote, production, security, or
release state.

`knowledge_access` controls whether external knowledge sources may be loaded.
The framework default is `enabled`; an organization or deployment may override
it with `approved_sources` or `disabled` without changing the knowledge-pack
format.

```json
{
  "knowledge_access": {
    "external_sources": "approved_sources",
    "approved_sources": [
      "https://git.example.org/",
      {"id": "sample-product-docs", "source": "https://docs.example.org/products/sample-product/"}
    ]
  }
}
```

Approved-source entries may be strings or objects. Strings are shorthand for a
source object; object entries require `source` and may optionally include `id`.
The source value is provider-neutral and is interpreted by the runtime or
connector. An empty approved-source set fails closed in `approved_sources`
mode. Knowledge access never grants remote mutation permission.

```json
{
  "input_validation": {"required": ["objective", "repository"], "block_on_ambiguity": true},
  "tool_authorization": {
    "default": "bounded",
    "sensitive_operations": ["remote_mutation", "deployment", "production_change"]
  }
}
```

## Approval Requirements

Each approval requirement must identify the trigger, approver or approval lane,
and behavior when approval is absent:

```json
{
  "trigger": "new_dependency_or_integration",
  "approval_lane": "program-manager",
  "requires_human_confirmation": true,
  "on_missing": "block"
}
```

Allowed `on_missing` values are `block`, `escalate`, and `defer`. Approval
requirements do not imply that a role can approve its own work or bypass a
runtime's native authorization boundary.

## Retry, Escalation, And Termination

Policies must define bounded retry behavior and an escalation path. Retry is
not permission to repeat a denied or unsafe action. Termination conditions must
cover success, failure, and unresolved approval or quality states.

Role references in `approval_lane` and `escalation` must resolve in the selected
effective team. Human approval may be represented by `human` where no role is
the approver.

## Composition

Execution profiles reference policies using `policy_ids`. Policies are applied
in declared order. Conflicting policies at the same scope must be rejected or
resolved by an explicit priority mechanism; discovery order is never a winner.

The most restrictive applicable control wins for a sensitive operation. A
runtime mapping may project a policy into native guardrails, but may not weaken
it without an explicit derived policy and validation decision.
