# Runtime Integrations

This directory contains concrete `runtime-adapter` artifacts for the AI organization framework.

Current adapters:

- [`codex-desktop-agent-runtime`](codex-desktop-agent-runtime.md)
  - concrete adapter for the current Codex desktop coding-agent runtime used in this workspace
- [`opencode-agent-runtime`](opencode-agent-runtime.md)
  - OpenCode capability artifact paired with the repository's OpenCode CLI and server execution surfaces
- [`kiro-ide-agent-runtime`](kiro-ide-agent-runtime.md)
  - Kiro IDE capability artifact paired with the app-native Agent Caravan orchestrator skill

These declarative artifacts describe capability claims and constraints that
`runtime-profile` artifacts target. Runtime-specific execution may use an
executable bridge under `src/agentcaravan/adapters/` or a native harness skill.
The Kiro IDE integration uses the latter and does not launch Kiro CLI. See
the [Kiro IDE guide](../../../docs/integrations/kiro-ide-adapter.md) and the
[OpenCode integration guide](../../../docs/integrations/opencode-adapter.md).

Capability levels in an adapter describe the realization of a named capability
for its stated runtime and surface. They do not indicate whether Agent Caravan
has verified that capability in a particular setup. Verification must be
scoped separately to the product version, execution surface, relevant
configuration, and scenario, with evidence and provenance recorded where
available. An unverified capability is not thereby unsupported. See the
[runtime integration guide](../../../docs/reference/runtime-integration.md#capability-realization-and-verification-evidence)
for the reporting distinction.
