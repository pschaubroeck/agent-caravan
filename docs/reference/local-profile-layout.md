---
type: Reference
title: Local Agent Caravan Implementation Profile
description: Required local layout for the Agent Caravan reference implementation.
---

# Local Agent Caravan Implementation Profile

## Purpose

This document defines the required local layout for the reference implementation of the organization framework.

## Contents

- [Required root](#required-root)
- [Directory layout](#directory-layout)
- [`config.json`](#configjson)
- [`sources/`](#sources)
- [`overrides/`](#overrides)
- [`sessions/`](#sessions)
- [`cache/`](#cache)
- [`caravans/`](#caravans)
- [Safety rules](#safety-rules)

The framework specification remains storage-agnostic. This layout is the repeatable local convention used by this implementation and may be created automatically on first use.

## Required Root

```text
~/.agents/agent-caravan/
```

Keep the root outside a cloned catalog repository.

This is the default location for new profiles. Existing profiles under
`~/.agents/org-framework/` are left in place; initialization does not migrate
them. Continue using an existing profile by passing its root explicitly, for
example `agent-caravan status --root ~/.agents/org-framework`.

## Directory Layout

```text
~/.agents/agent-caravan/
  config.json
  sources/
  overrides/
  sessions/
  cache/
  caravans/
```

### `config.json`

Stores the active source declarations, selected organization/team/runtime context, and explicitly enabled local overrides.

`adapter_overrides` is the one local place to customize runtime-specific
settings without editing packaged adapter artifacts. It is an optional map
keyed by the exact `id` field in a `runtime-adapter` artifact. For the
currently selected harness, copy `active_context.runtime_adapter_id`; for a
custom adapter, use its declared artifact `id` after confirming that the
adapter is included in the profile's configured sources. Values partially
override that adapter's declarations; omitted fields keep the packaged or
custom adapter defaults. For example, to use a different repository guidance
filename for Codex:

```json
{
  "adapter_overrides": {
    "codex-desktop-agent-runtime": {
      "repository_guidance": {
        "native_files": ["TEAM_GUIDANCE.md"],
        "discovery": "explicit"
      }
    }
  }
}
```

The canonical Agent Caravan file remains `AGENTS.md`; the adapter override
changes the file convention used by that runtime. Supported local runtime
overrides are resolved with the selected adapter and appear under
`runtime.repository_guidance` in the resolved configuration. The
`agent-caravan status` command shows the active adapter and effective
repository-guidance files, discovery mode, and reference policy.

Credentials must not be stored in this file. Source adapters should use the host credential manager or runtime-approved authentication mechanism.

Each `sources` entry may be a local JSON file or directory path, or a Git
checkout declaration:

```json
{
  "type": "git",
  "url": "git@gitlab.example.org:engineering/team-catalog.git",
  "checkout": "../../workspace/team-catalog",
  "subdirectory": "agentcaravan"
}
```

The checkout path is local to each employee and may be absolute or relative to
the profile root. `url` identifies the shared repository; Agent Caravan does
not clone, fetch, or pull it. Resolution reads the current checkout and
reports its commit and dirty state. Employees update their checkout using
their normal Git workflow. `subdirectory` is optional and defaults to the
repository root. Legacy path strings remain supported.

A local JSON source may be one bundle or a directory containing artifact
files. A bundle may contain an `artifacts` list; an individual artifact file
may contain one artifact object. Other JSON files are ignored. Duplicate
`(artifact_type, id)` pairs are rejected rather than selected by discovery
order.

The optional `managed_sources` section records source paths managed by a
bootstrap or adapter. Current package and checkout initialization manages the
local packaged core source; legacy checkout-managed paths may be removed during
migration. It does not control or replace user-owned external sources.

### `sources/`

Stores local materializations or adapter-managed source data. A GitLab checkout may live here, but GitLab is not required by the framework contract.

### `overrides/`

Stores durable user-local artifacts. Include this directory explicitly in
`config.json` sources when you want to load its JSON artifacts; it is not
scanned automatically. The directory name does not give its files precedence
over shared sources. Duplicate `(artifact_type, id)` pairs are still rejected.
Only explicitly selected overlay artifacts modify their referenced targets,
according to the [overlay composition rules](../../resources/specifications/logical-artifact-overlay-model.md).

### `sessions/`

Stores temporary task-specific artifacts. Session artifacts should not be treated as durable team or organization knowledge.

### `caravans/`

Contains the human-facing, runtime-neutral authoring workspaces created by
`agent-caravan configure`. Each team directory contains Markdown files for the
team mission, work surfaces, trusted knowledge sources, and working agreements.
It also contains `instructions.md` for durable AI guidance and `responsibilities.md` for
preferred roles and participation guidance.
The resolver reads those files automatically when the profile is resolved.
After confirmation, `agent-caravan configure` updates the prompted fields in
the Markdown workspace. Absolute checkout paths stay in that profile-local
workspace; the team artifact stores only portable work-surface references.
When the artifact comes from an external Git checkout, configure leaves that
checkout unchanged and stores employee-specific guidance locally. Edit and
commit the shared repository to publish team-wide artifact changes. Configure
preserves `instructions.md`, `responsibilities.md`, and other headings in `caravan.md`; edit
those Markdown files directly to change durable AI instructions or role
guidance.
Runtime integrations decide how that context is projected into execution.

### `cache/`

Stores regenerable normalized bundles, indexes, or retrieval results. Cache contents are not authoritative source artifacts.

## Safety Rules

- local overrides are external to the shared catalog repository by default
- bootstrap must not overwrite an existing `config.json`
- reinitialization may replace only paths recorded under `managed_sources`
- source discovery must be explicit; arbitrary files in the root must not become active artifacts automatically
- promotion into a shared catalog requires an intentional export, validation, and repository contribution
- local and session artifacts must not be published as organization artifacts implicitly
