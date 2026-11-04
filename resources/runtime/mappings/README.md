# Runtime Mapping Examples

This directory contains reusable platform-level `runtime-profile` examples for the Agent Caravan default core team.

These examples are intended to make the abstract binding format more operational by showing how real framework artifacts can be mapped onto different runtime shapes.

Current examples:

- `codex-desktop-information-technology-core-team`
  - concrete team-binding example for the current local Codex-style coding-agent runtime
- `opencode-information-technology-core-team`
  - concrete local team-binding example for the OpenCode adapter; execution evidence and version limits are documented separately
- `kiro-ide-information-technology-core-team`
  - Kiro IDE team binding using the native orchestrator skill, custom agents, permissions, and operator-visible evidence
- `codex-desktop-sample-product-engineer`
  - concrete domain-aware role binding for `engineer` in the `sample-product` domain
- `codex-desktop-sample-product-team`
  - concrete resolved-instance binding across organization, team, domain, and persistent specialization layers
- `codex-desktop-sample-product-engineer-ii`
  - concrete role-variant binding activated through a team-scoped overlay
- `broker-gateway-information-technology-core-team`
  - illustrative broker/gateway team-binding example for a Droid-like or similar managed broker runtime

Notes:

- The Codex examples target the Codex desktop execution surface. Adapter capability levels describe expected realization; this inventory does not establish a version-scoped verification result for every listed capability.
- The OpenCode example targets its own adapter and execution surfaces. Two dependency-approval cases passed on OpenCode v1.18.33 in the documented staged-runner configuration on September 30, 2026. Those results do not establish verification for every listed capability, provider/model, or OpenCode setup.
- The Kiro IDE example targets the desktop app and uses its native IDE skill harness. An operator-reported smoke check on Kiro IDE 1.2.56 on October 12, 2026 covered skill loading, profile selection, a denied permission prompt, and read-only subagent results. Broader conformance remains unverified; the repository does not retain the session evidence.
- The broker/gateway example is intentionally illustrative and unverified against a particular product. It is not a factual statement about any one vendor product's exact implementation.
- These are example bindings only. They do not replace the runtime integration specification or the need for adapter-specific validation.
- The Sample Product example demonstrates that one caravan template can be reused by multiple persistent caravans with different capability knowledge.

Runtime capability realization and verification evidence are separate. The
labels in an adapter (for example, `native`, `adapted`, `externalized`, and
`unsupported`) describe how a capability is realized for the named runtime
surface. They do not state whether a specific product version, configuration,
and scenario has been tested. Missing verification means unverified, not
incompatible; see the [runtime integration evidence guidance](../../../docs/reference/runtime-integration.md#capability-realization-and-verification-evidence).
