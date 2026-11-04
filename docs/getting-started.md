---
type: Guide
title: Getting Started in the Agent Caravan Repository
description: Set up a local Agent Caravan checkout and use its CLI and verification commands.
---

# Getting Started in the Agent Caravan Repository

This page is for contributors setting up a local checkout and using its CLI
and verification commands. For product requirements, package installation,
organization and team setup, user workflows, execution, and handoff, use the
[installation and refresh examples](reference/packaging-and-distribution.md#install-and-refresh-skills)
and the [Agent Caravan user guide](user-guide.md) for the product workflow.

## Contents

- [Requirements](#requirements)
- [Set up a development checkout](#set-up-a-development-checkout)
- [Initialize a local profile](#initialize-a-local-profile)
- [Run repository checks](#run-repository-checks)
- [Use the checkout CLI](#use-the-checkout-cli)
- [Next steps](#next-steps)

## Requirements

- Python 3.10 or newer.
- Git and a local Agent Caravan checkout.
- A project virtual environment with the checkout and its declared dependencies
  installed, as shown below.

The package metadata and Python entry point are defined in
[`pyproject.toml`](../pyproject.toml). The project installs the `agent-caravan`
command and pins its runtime dependency set there.

## Set up a development checkout

From the repository root, create and activate a virtual environment, then
install the checkout in editable mode:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Editable installation makes the `agent-caravan` command available while using
the code in this checkout. It also installs the runtime dependencies declared
in `pyproject.toml`, including `jsonschema`. Check dependency consistency:

```sh
python -m pip check
```

Activate `.venv` again in each new terminal session before running repository
commands. Confirm the command and package validation are available:

```text
agent-caravan --help
agent-caravan validate
```

If you only need to run the repository's interactive initializer, editable
installation is not required; `make init` runs the checkout source directly.
Its declared runtime dependencies must still be installed in the active Python
environment.

## Initialize a local profile

Run the interactive initializer only when you want a real local profile for
development or CLI investigation:

```text
make init
# Select OpenCode instead of the default Codex:
make init RUNTIME=opencode
# Select Kiro IDE:
make init RUNTIME=kiro
```

The target invokes `tools/init_agentcaravan.py` with this checkout on
`PYTHONPATH`. It creates or selects an organization and starter team, resolves
the profile, and installs required managed skills for the selected runtime.
Codex is the default and uses `~/.agents/skills/`; OpenCode uses
`~/.config/opencode/skills/`; Kiro IDE uses `~/.kiro/skills/`. Profile data
lives under
`~/.agents/agent-caravan/`. An existing team with a conflicting runtime
requires an explicit matching team choice or a separate profile root. Existing
skill links and unmanaged paths are preserved. Managed skill copies are refreshed;
locally modified managed copies require confirmation before replacement. See the
[Agent Caravan user guide](user-guide.md)
for user-facing setup choices and the complete supported workflow.

Existing profile data under `~/.agents/org-framework/` is not moved. To keep
using it, pass `--root ~/.agents/org-framework` to profile commands.

## Run repository checks

Run these checks from the repository root with the development environment
active. If this is a new terminal session:

```sh
source .venv/bin/activate
```

Setting `PYTHONPATH=src` makes the checkout source importable; it does not
install dependencies. If a test reports `ModuleNotFoundError` for `jsonschema`,
confirm that `.venv` is active and rerun `python -m pip install -e .` followed
by `python -m pip check`.

Run the fast preflight before committing:

```text
make preflight
```

It checks catalog-manifest JSON syntax and compiles the Python source. Run the
focused framework checks when changes affect behavior, artifacts, or package
contents:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 -m json.tool catalog-manifest.json > /dev/null
```

The Makefile also provides `make validate`, `make resolve`, `make cli-smoke`,
and `make package-smoke`; inspect [`Makefile`](../Makefile) for the exact
commands. The package smoke test builds and installs a wheel locally and does
not publish it.

## Use the checkout CLI

After editable installation, the command is available as `agent-caravan`. From
the checkout, these read-only or validation commands are useful while
developing:

```text
agent-caravan --help
agent-caravan validate
agent-caravan status
agent-caravan resolve
```

`status` and `resolve` inspect the active local profile. If no profile is
initialized, run `make init` or consult the [Agent Caravan user
guide](user-guide.md)
for product setup guidance. For isolated profile paths, see the
[Local Profile Layout reference](reference/local-profile-layout.md).

## Next steps

- [Agent Caravan user guide](user-guide.md) for the product guide and user workflow
  — requirements, package installation, setup, user workflows, examples, and
  handoff.
- [Overview](concepts/overview.md) — framework scope and boundaries.
- [Runtime integration](reference/runtime-integration.md) — source-backed
  integration behavior and runtime support.
- [Repository instructions](../AGENTS.md) — artifact boundaries and required
  development checks.
