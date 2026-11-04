# Catalog Manifest

`catalog-manifest.json` is the reference implementation's catalog index. It describes what the Agent Caravan catalog contains and how a consumer can locate its logical artifact categories.

## What It Does

The manifest declares:

- catalog identity
- artifact category roots
- framework specification documents
- organizations, catalogs, and teams included in the distribution
- runtime adapters and validation profiles made available
- shareable Agent Caravan skill sources
- machine-readable starter bundles for the shared core team and Codex runtime
- reusable execution workflows
- reusable execution policy artifacts
- runtime adapter walkthroughs
- the reference implementation's local profile

The manifest is not a resolver input, runtime profile, authorization document, or storage requirement. A provider may translate this manifest and its artifacts into another catalog representation.

## What It Does Not Do

The manifest intentionally does not contain a package release version. Release identity is supplied by the distribution mechanism, such as a Git tag, GitLab generic artifact, registry entry, or another provider-specific identity.

Artifact-level versions remain valid where the artifact specification requires them for replacement, compatibility, or provenance.

## Repository Layout

The directory names in this repository are the Agent Caravan reference implementation profile:

```text
catalog-manifest.json
resources/core/responsibilities/
resources/core/caravan-templates/
resources/core/agentcaravan-core-team.json
examples/sample-organization/caravans/
examples/sample-organization/domain-knowledge/
examples/sample-organization/capability-knowledge/
examples/sample-organization/organizations/
examples/sample-organization/configuration-overrides/
resources/runtime/integrations/
resources/runtime/mappings/
resources/runtime/agentcaravan-codex-runtime.json
examples/sample-organization/runtime-mappings/
skills/
src/agentcaravan/
resources/specifications/
resources/execution/workflows/
resources/execution/policies/
resources/execution/state/
resources/schemas/
docs/
  getting-started.md
  concepts/
  reference/
  integrations/
  maintainers/
```

Other implementations may use different physical storage, provided they preserve the logical artifact identities, relationships, and validation expectations.
