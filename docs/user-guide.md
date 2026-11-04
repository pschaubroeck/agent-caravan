---
type: Guide
title: Agent Caravan User Guide
description: Install Agent Caravan, configure a caravan, and use it with a supported AI runtime.
---

# Agent Caravan User Guide

Use Agent Caravan to define a reusable group of AI responsibilities, its
working knowledge, and how it maps to an AI runtime. This guide takes you from
a local checkout to a configured caravan that you can inspect and use with
your AI assistant.

## Contents

- [Requirements](#requirements)
- [Install from a checkout](#install-from-a-checkout)
- [Set up your first caravan](#set-up-your-first-caravan)
- [Add working context](#add-working-context)
- [Use the caravan for work](#use-the-caravan-for-work)
- [CLI checks and dry-run](#cli-checks-and-dry-run)
- [Troubleshooting](#troubleshooting)
- [Next steps](#next-steps)

## Requirements

- Python 3.10 or newer and a local checkout of this repository.
- An AI runtime that can load the supplied skills for AI-guided setup and
  work. The supplied runtime integrations include Codex, OpenCode, and Kiro
  IDE; their actual capabilities and permissions depend on the runtime.
- Permission to install the Python dependencies declared in
  [`pyproject.toml`](../pyproject.toml) and to write your local profile and
  chosen runtime's skill directory.

The project is installed from the checkout below. A public package registry
release is not required or assumed.

## Install from a checkout

From the repository root, create a virtual environment and install the
project:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
agent-caravan --help
```

The last command shows the available commands. Activate `.venv` in a new
terminal before using the installed CLI. The package bundles the skill sources;
initialization installs the shared skills and the selected runtime's
orchestrator.

## Set up your first caravan

Initialize the local profile and install skills for your runtime. Codex is
the default; choose the applicable command:

```sh
agent-caravan init --runtime codex
# Or use: agent-caravan init --runtime opencode
# Or use: agent-caravan init --runtime kiro
```

Follow the prompts to select or create an organization and caravan. The
initializer previews the choice before creating it. It uses the shared
Information Technology Core Team template as the starter. Existing content
and unmanaged skill paths are preserved; review any replacement prompt before
continuing.

The default profile is `~/.agents/agent-caravan/`. Skills are installed under
`~/.agents/skills/` for Codex, `~/.config/opencode/skills/` for OpenCode, or
`~/.kiro/skills/` for Kiro IDE. If your runtime does not immediately show the
skills, refresh its skill discovery according to that runtime's workflow.
Initialization does not move an older `~/.agents/org-framework/` profile; to
use one, supply its path with `--root` to profile commands.

Once the skills are available, ask your assistant to inspect and help refine
the active setup:

```text
Use the agent-caravan-builder skill to inspect my active profile. Explain the
selected caravan, suggest any missing context, and preview changes before
writing them. Then resolve and validate the configuration.
```

The assistant should report the selected configuration, any files changed,
and unresolved choices. To check it yourself, run `agent-caravan status` and
`agent-caravan resolve`. The former reports the active profile; the latter
shows its resolved composition. A successful resolution does not prove that
every runtime capability has been tested.

## Add working context

Ask the builder to add the context your caravan needs, or use the interactive
CLI:

```sh
agent-caravan configure
agent-caravan resolve
```

The active caravan's authoring files live under
`~/.agents/agent-caravan/caravans/<caravan-id>/` by default:

| File | Use |
| --- | --- |
| `caravan.md` | Mission and practical scope. |
| `repositories.md` | Relevant repositories, services, and workspaces. |
| `knowledge.md` | Trusted documentation and instruction sources. |
| `working-agreements.md` | Durable collaboration and review practices. |
| `instructions.md` | Reusable caravan-specific AI guidance. |
| `responsibilities.md` | Preferred IDs and participation guidance. |

Use durable, scoped guidance and preserve existing content when editing. A
listed repository or knowledge source is context; it does not grant access or
prove the runtime loaded that source. Responsibility preferences inform
participation but do not replace the template's duties or execution policy.

## Use the caravan for work

In a supported AI runtime, ask its Agent Caravan orchestrator to apply the
active caravan to a concrete task. For example:

```text
Use my active Agent Caravan caravan to improve one small piece of developer
documentation in this repository. Inspect applicable guidance, explain your
plan, make the change, and report the checks you ran. Do not push or deploy.
```

Give the assistant a real task and review its proposed plan and results. The
runtime determines which native workers, handoffs, permissions, and evidence
are available. Agent Caravan defines and resolves the configuration; it does
not itself guarantee that a harness launches workers or completes the task.
See [Developer Examples](developer-examples.md) for setup, customization,
handoff, and runtime-specific examples.

## CLI checks and dry-run

These commands inspect the default profile and installed resources:

```sh
agent-caravan status
agent-caravan resolve
agent-caravan validate
```

`status` inspects the active profile, `resolve` composes its selected
configuration, and `validate` checks framework resources. They cover
different scopes. `validate` does not select a profile or accept `--root`.

For a Codex profile, a simulated task can write local session evidence without
calling a model or starting live implementation:

```sh
agent-caravan run --dry-run --task-id example-feature-001 \
  --objective "Demonstrate the configured flow"
agent-caravan validate-session --task-id example-feature-001
```

The second command checks the saved task/session evidence. For repeated runs,
use a new task ID or an unused `--attempt` value to preserve prior evidence.
The reference CLI dry-run is Codex-only; live work uses the selected runtime's
orchestrator. A handoff can be exported using `agent-caravan handoff`, but
exporting it does not launch a runtime or execute a task.

For an alternate profile, pass the same `--root` to each profile command and
the same `--sessions-root` to `run` and `validate-session` if you override the
session location. Use `agent-caravan <command> --help` for supported options.

## Troubleshooting

- **The command is missing:** activate the virtual environment where the
  checkout was installed and rerun `agent-caravan --help`.
- **A Python dependency is missing:** with that environment active, rerun
  `python -m pip install -e .` from the checkout and `python -m pip check`.
- **No active caravan appears:** run `agent-caravan status`, check the profile
  root, and rerun initialization with the intended runtime if needed.
- **The selected runtime conflicts with an existing caravan:** use the
  existing caravan's runtime, select or create a matching caravan, or use a
  separate profile root. Do not overwrite a configuration just to silence the
  error.
- **Resolution fails:** run `agent-caravan resolve --diagnostics` and inspect
  the reported artifact references and configuration; the resolver skill can
  help explain the results.
- **Session evidence is not found:** use the task ID, profile root, and
  sessions root from the original run when validating it.

## Next steps

- Follow [Developer Examples](developer-examples.md) for deeper scenarios.
- Review [Runtime Integration](reference/runtime-integration.md) for runtime
  capabilities, evidence, and limitations.
- Use [Getting Started in the Repository](getting-started.md) for contributor
  setup and repository verification.
