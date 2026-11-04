# Runtime Mapping: codex-desktop-sample-platform-engineer

## Purpose

- `id`: `codex-desktop-sample-platform-engineer`
- `name`: `Codex Desktop Sample Platform Engineer Binding`
- `version`: `1.0.0`
- `scope`: `local`
- `target_adapter_id`: `codex-desktop-agent-runtime`
- `extends`: `codex-desktop-information-technology-core-team`
- `mission`: Bind the base Engineer role to Codex for generic shared-platform implementation work.
- `summary`: Demonstrate domain-aware context loading for fictional platform work without real organization or infrastructure details.

## Target Scope

- `applies_to_artifact_ids`: `engineer`, `sample-product`
- `applies_to_artifact_types`: `role`, `domain-pack`
- `binding_scope_type`: `domain-aware-role-binding`

## Runtime Mapping

- `engineer`: one bounded coding lane in the selected repository
- `sample-product`: shared product and platform context relevant to the requested change
- begin with repository instructions and durable architecture sources, then inspect code and tests
- record material evidence used for decisions and validation

## Capability Contract

- `required_capabilities`: `dynamic_context_loading`, `local_command_execution`, `code_editing`, `tool_approval_gates`
- `preferred_capabilities`: `document_attachment_support`, `execution_trace`, `retrieval_augmented_context`
- `optional_capabilities`: `background_execution`, `durable_memory`
- `forbidden_capabilities`: none

## Fallback And Safety

- if source browsing is unavailable, use supplied durable documentation and record the limitation
- surface unresolved ownership or contract questions before changing shared interfaces
- bounded local code changes do not imply authority to mutate remote systems or environments
