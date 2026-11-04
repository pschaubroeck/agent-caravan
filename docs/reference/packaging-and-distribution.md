---
type: Reference
title: Packaging and Distribution
description: Implemented package-first distribution model and boundaries for local organization state.
---

# Packaging and Distribution

## Purpose

This page explains the implemented package-first distribution model and the boundaries around local organization state.

## Contents

- [Current recommendation](#current-recommendation)
- [Recommended packaging model](#recommended-packaging-model)
- [Implemented package-first distribution](#implemented-package-first-distribution)
- [Additional distribution layers](#additional-distribution-layers)
- [Shared marketplace](#recommendation-on-the-shared-marketplace)
- [Long-term shape](#recommended-long-term-shape)
- [Packaging principles](#packaging-principles)
- [Local profile](#reference-implementation-local-profile)
- [Current state](#current-state)
- [Documentation ownership](#documentation-ownership)
- [Future distribution work](#future-distribution-work)
- [Dependency policy](#dependency-policy)

## Current Recommendation

The framework should be treated as a **logical product with reference implementations**, not as one Codex-specific asset.

That means there should be a separation between:

- the **framework specification layer**
- the **reference artifact catalog**
- the **runtime-specific integrations and mappings**

## Recommended Packaging Model

### 1. Framework Specification Layer

This is the vendor-neutral shared layer.

It should include:

- responsibility specification
- caravan template specification
- domain knowledge specification
- logical configuration override and resolution model
- runtime integration model
- runtime mapping model
- validation model

This is the part that should remain portable across runtimes and storage systems.

### 2. Reference Artifact Catalog

This is the reusable example or starter layer.

It should include:

- core responsibility artifacts
- one or more default caravan templates
- reference domain knowledge such as `sample-product`
- example configuration overrides

This is the part that helps adopters start quickly.

### 3. Runtime-Specific Distribution Layer

This is the implementation-facing layer.

It should include:

- runtime integrations
- runtime mappings
- vendor-specific guidance
- runtime-specific packaging where useful

This is where Codex-specific, Droid-specific, or other runtime-specific distribution patterns should live.

## Implemented Package-First Distribution

The reference implementation now provides a self-contained Python package for
the reusable Agent Caravan core. From a checkout, install the package and use
its bootstrap CLI:

```text
python3 -m pip install .
agent-caravan init --runtime codex
agent-caravan validate
agent-caravan resolve
```

The installed package includes the shared core team and runtime resources, the
feature-delivery workflow and safety policy, and the shareable Agent Caravan
skills. `agent-caravan init` creates or reuses the local profile, materializes
the packaged core under `~/.agents/agent-caravan/sources/_agentcaravan-core`,
and preserves user-owned organization sources and configuration according to
the bootstrap safeguards.

The package is self-contained for the shared framework core. The repository remains
the contributor source, full reference catalog, documentation source, and place
for organization examples that are not part of the shared package.

### Install And Refresh Skills

Codex remains the default. Explicit runtime selection makes the installation
intent visible:

```text
agent-caravan init --runtime codex
agent-caravan status
agent-caravan validate
agent-caravan resolve
```

For a first OpenCode team, use a separate profile root if your default profile
already contains a Codex team:

```text
agent-caravan init --runtime opencode --root ~/.agents/agent-caravan-opencode
agent-caravan status --root ~/.agents/agent-caravan-opencode
agent-caravan validate
agent-caravan resolve --root ~/.agents/agent-caravan-opencode
```

For a Kiro IDE profile, use its native skills location:

```text
agent-caravan init --runtime kiro --root ~/.agents/agent-caravan-kiro
agent-caravan status --root ~/.agents/agent-caravan-kiro
agent-caravan resolve --root ~/.agents/agent-caravan-kiro
```

Initialization creates or reuses a profile and starter team and installs four
shared skills: `agent-caravan-builder`, `agent-caravan-resolver`,
`agent-caravan-validator`, and `agent-caravan-runtime-adapter-builder`. It adds
`agent-caravan-codex-orchestrator` for Codex or
`agent-caravan-opencode-orchestrator` for OpenCode or
`agent-caravan-kiro-orchestrator` for Kiro IDE.

| Runtime | Default skill destination | Execution entry point |
| --- | --- | --- |
| Codex | `~/.agents/skills/` | `agent-caravan-codex-orchestrator` |
| OpenCode | `~/.config/opencode/skills/` | `agent-caravan-opencode-orchestrator` |
| Kiro IDE | `~/.kiro/skills/` | `agent-caravan-kiro-orchestrator` |

Override the destination explicitly when your harness uses a different root:

```text
agent-caravan init --runtime opencode --root ~/.agents/agent-caravan-opencode --skill-root ~/.config/opencode/skills
```

A custom root must be discoverable by the chosen harness. `status` reports the
selected runtime, configured destination, and required skill state. `validate`
checks packaged resources; `resolve` checks the selected profile composition.
New OpenCode setup uses the `team-shared` validation rules, which allow its
declared adapted capabilities and reports them as `degraded`. A stricter
validation rule set already selected by the user is preserved; setup does not
relax it automatically. Initialization resolves the proposed team before
writing profile or skill changes. If the selected runtime cannot meet the
validation policy, setup stops with an actionable error and preserves the
existing profile and skills. Select a compatible runtime or deliberately
review the team's validation policy before retrying; initialization never
weakens an existing policy automatically. Review the reported capability limits
before execution.
`status` does not prove that a running harness has loaded the skills. In OpenCode, confirm
that `agent-caravan-opencode-orchestrator` appears in the native `skill` tool
and load it with `skill({ name: "agent-caravan-opencode-orchestrator" })`.
OpenCode also discovers `~/.agents/skills/`. When both installations exist,
check for duplicate shared skill names across discovery locations and keep
managed copies at the same package version. A custom shared root can avoid
duplicating the four neutral skills; initialize both runtimes with
`--skill-root ~/.agents/skills` if that shared discovery arrangement suits
your setup. The orchestrators check the harness and
resolved adapter before execution. See [OpenCode skill discovery](https://opencode.ai/docs/skills/).

After updating the checkout, reinstall the package from the repository root and
rerun initialization for each configured runtime/profile to refresh its managed
skill copies:

```text
python3 -m pip install --upgrade .
agent-caravan init --runtime codex
agent-caravan init --runtime opencode --root ~/.agents/agent-caravan-opencode
agent-caravan status
agent-caravan status --root ~/.agents/agent-caravan-opencode
```

The installer preserves unmanaged directories and existing symlinks. It
refreshes unchanged managed copies and asks before replacing locally modified
managed copies. Inspect reported preserved paths when troubleshooting stale
skills; upgrading the package alone does not refresh every installed copy.

From a repository checkout, use `make init` for Codex,
`make init RUNTIME=opencode` for OpenCode, or `make init RUNTIME=kiro` for Kiro
IDE. These run checkout source directly; editable installation is not
required. Use the CLI options above when you need a separate profile root or
custom destination.

An existing active team with a different runtime must be selected or replaced
explicitly with a matching team; initialization fails before changing that
team implicitly. A separate profile root is useful for keeping both runtime
setups available. Setup installs skills and resolves configuration; it does
not launch either harness or modify its permissions. `agent-caravan run
--dry-run` currently prepares Codex only. OpenCode uses its orchestration skill
or the supplied execution-surface integration described in the
[OpenCode adapter guide](../integrations/opencode-adapter.md). Kiro IDE uses
its native Agent Skills harness as described in the
[Kiro IDE adapter guide](../integrations/kiro-ide-adapter.md); the package does
not invoke Kiro CLI.

### Packaged Core And Local Organization Boundary

The distribution boundary is intentionally split:

- **Packaged shared core:** reusable roles, the core caravan template, runtime
  adapter/profile resources, execution workflow and policy, and the supported
  shareable skills.
- **Local organization artifacts:** organization catalogs, caravans,
  domain and capability knowledge, overlays, local configuration, and user
  overrides. These remain local so each organization and team can own its
  context without changing the shared package.

The package installs shared resources into a managed local source directory so
the resolver can compose them with organization-specific sources. Package
updates may refresh that managed directory; they must not replace user-owned
organization artifacts or local overrides.

## Additional Distribution Layers

The package-first model still supports additional distribution layers when they
serve a real consumer:

### Shared Framework Catalog

A shared catalog containing:

- framework specs
- responsibility artifacts
- caravan template artifacts
- domain-pack artifacts
- validation rules

This should be vendor-neutral and not depend on one AI runtime ecosystem.

### Runtime Integration Packs

Separate packages for:

- Codex
- Droid
- other runtime ecosystems as needed

This prevents the whole framework from becoming “the Codex version of the framework.”

## Recommendation On The Shared Marketplace

My recommendation is:

- **do not make the entire framework itself depend on the shared marketplace**
- **do use the shared marketplace later for runtime-specific adapter packs where that makes sense**

Why:

- the framework core is broader than one runtime
- the marketplace is likely best for runtime-facing artifacts, skills, adapters, or implementation bundles
- the core model should remain portable even if a consumer does not use the marketplace at all

So the marketplace can be part of the distribution strategy, but it should not become the framework's canonical definition layer.

## Recommended Long-Term Shape

Long term, I recommend thinking about the framework as:

- **core framework specification**
- **reference catalog**
- **runtime integration packs**
- **optional organizational overlays**

That structure supports:

- organization-wide sharing
- team-specific specialization
- local experimentation
- multiple runtime implementations

## Packaging Principles

Whatever packaging mechanism is chosen, it should preserve:

- stable IDs
- explicit versions
- clear scope boundaries
- logical artifact separation
- validation before publication

The packaging mechanism itself may vary.

Examples:

- files
- repos
- APIs
- registries
- marketplace entries
- mixed distribution

## Reference Implementation Local Profile

For the reference implementation, local state is conventionally created at:

```text
~/.agents/agent-caravan/
```

This directory contains implementation-local configuration, source materializations, durable local overrides, temporary sessions, and regenerable caches. It is intentionally outside any shared catalog repository so local overrides are not committed accidentally.

The directory may be created on first use. Its naming and layout are requirements of the reference implementation, not requirements imposed on all framework adopters.

## Current State

GitHub Actions verifies the package and repository on Python 3.10 and 3.14.
It does not publish a package. The package can be built locally with the pinned
build tools; `pyproject.toml` contains its metadata and `agentcaravan.scripts`
provides the verification commands.

The built package contains the reusable core resources and supported skills
listed above. It does not contain organization-specific catalogs, team
instances, domain knowledge, specializations, overlays, or local overrides. Those
artifacts are created or maintained in the local profile and composed with the
managed package source at runtime.

For contributor workflows, the repository remains available for `make init`,
full catalog work, examples, documentation changes, and package development.
Consumers do not need to clone the repository merely to install or bootstrap
the shared core.

## Documentation Ownership

The repository contains the [documentation index](../README.md),
[getting started guide](../getting-started.md), and
[developer examples](../developer-examples.md), alongside framework
specifications, reference artifacts, and integration contracts.

## Future Distribution Work

The following options are not part of the current package contract. They are
maintainer planning topics and should not be read as promised features.

### Complete Reference-Catalog Release Bundle

The core package is implemented and intentionally excludes organization-specific
reference examples and repository documentation. A future release may publish
the full catalog, examples, documentation, or additional runtime packs as a
separate GitLab generic artifact, release archive, marketplace package, or
another provider-specific format. Any such bundle must remain separate from the
framework contract's storage-neutral model and must preserve the packaged-core
versus local-organization boundary.

### Stronger Framework Validation

The repository has useful regression tests, but a future validation slice
should add explicit machine-checked coverage for:

- schema and reference validation across all published resources
- overlay and precedence edge cases
- runtime capability negotiation and degradation reporting
- adapter conformance scenarios such as handoff, approval, failure, resume,
  and completion evidence

This should strengthen the existing gates without requiring every adopter to
use the same validation toolchain.

### Portable Execution State

The reference implementation already records local task, session, run, and
handoff evidence and validates saved session records. It also defines portable
checkpoint, approval, and completion contracts, with bounded conformance
fixtures and adapter evidence. These records do not constitute a durable
execution engine or a hosted persistence service.

Further work may broaden resumability and persistence across runtime integrations.
Any durable state support must remain capability-dependent rather than
mandatory for every runtime. See [Runtime Integration](runtime-integration.md)
for the implemented adapter boundaries and [the task/session state
specification](../../resources/specifications/task-session-state-spec.md) for
the evidence contract.

### Additional Runtime Integrations

The repository includes Codex and OpenCode execution bridges, plus a Kiro IDE
native-skill integration. A bounded Kiro IDE smoke check passed skill loading,
profile selection, a denied permission prompt, and subagent delegation; broader
conformance remains unverified. OpenCode support is bounded by its configured runtime,
provider, model, and evidenced conformance cases; it is not a guarantee for
every OpenCode setup.

Add other coding-agent products, hosted agent platforms, or orchestration
frameworks when a real workflow requires them. Each adapter must preserve the
runtime-neutral semantic model and report unsupported or degraded capabilities
explicitly. See [Runtime Integration](runtime-integration.md) for the current
inventory.

### Shared Catalog And Skill Distribution

The reference repository currently supplies reusable catalogs and skill source
artifacts. A later distribution slice may provide organization-wide catalogs,
runtime-specific skill packs, marketplace entries, or other discoverable
packages. These mechanisms should improve sharing without making one registry,
Git provider, marketplace, or runtime a framework requirement.

### Explicitly Out Of Scope For This Roadmap

The following are not deferred requirements:

- a universal runtime launcher
- a mandatory Git or GitLab storage model
- a mandatory database, vector store, or message bus
- activating every role for every task
- packaging every runtime's native concepts into the core framework

### Dependency Policy

Agent Caravan's runtime dependencies are declared in `pyproject.toml`. Its build and test tooling is exact-pinned in `requirements.txt` and
`test-requirements.txt`, with matching build-isolation pins in `pyproject.toml`.
Automated dependency upgrades should change those declarations as one reviewable
unit and must pass the full quality, package-build, test, and resolution gates.
