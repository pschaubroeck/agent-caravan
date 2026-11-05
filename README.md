# Agent Caravan

Agent Caravan is a runtime-neutral framework for defining, composing, validating, and adapting AI organizations and teams.

## Spend Less Time Rebuilding AI Workflows

Agent Caravan helps developers reuse the parts of AI-assisted engineering that
are usually scattered across prompts, scripts, and team conventions. Define
responsibilities, workflows, domain knowledge, and policies once, then compose
them into a caravan you can inspect, validate, and adapt across projects and AI
runtimes.

For developers, that means a clearer way to:

- reuse workflows instead of recreating agent instructions for each project;
- keep responsibilities, project knowledge, and runtime-specific setup separate;
- track task plans, handoffs, and completion evidence; and
- experiment with AI team structure without tying the framework's core model to one runtime.

Agent Caravan defines and validates the portable team model; the selected AI
harness remains responsible for executing the work.

The repository contains the framework specifications, reference roles and team artifacts, domain and specialization examples, runtime profiles, shareable skills, and the first machine-readable resolution prototype.

The [catalog manifest](catalog-manifest.json) indexes the reference distribution. Git tags identify releases; GitHub Actions verifies changes but does not publish packages.

The repository is also the canonical source for the shareable [Agent Caravan skills](skills/), including Codex, OpenCode, and Kiro IDE orchestration entry points. Runtime installation is deliberately separate so a Codex, Droid, Claude, SDK, broker, or other consumer can choose its own adapter and installation mechanism.

For product requirements, installation, setup, and supported user workflows,
start with the [Agent Caravan user guide](docs/user-guide.md).
If you are contributing to this repository, use the separate
[repository setup guide](docs/getting-started.md).

### Working with an AI assistant

Start with the user guide when setting up or using Agent Caravan. For code or
catalog changes, ask the assistant to inspect the relevant specification,
existing artifact, and tests before editing. Keep changes within the artifact
boundaries in [`AGENTS.md`](AGENTS.md), preserve stable machine identifiers, and
run the focused repository checks for the change. Use the skills in [`skills/`](skills/)
for setup, validation, resolution, and runtime-specific guidance; they describe
the framework but do not replace the host runtime's permissions or execution
capabilities.

Keep plans for one-off tasks in the issue, pull request, or working conversation.
When work produces durable decisions or evidence, record those in the relevant
maintainer or experiment report, then remove the completed task plan.

Browse the [examples index](examples/README.md) for the generic coworker-sharing scenario, its Codex plugin package, and separately labeled organization-specific references.

See the [documentation home](docs/README.md) for the ordered guide, concepts,
reference, integration, research, and design-note documentation.

## Repository Layout

- `src/agentcaravan/`: normalized resolver, storage boundary, and local profile utilities
- `src/agentcaravan/foundation/`: runtime-neutral foundation namespace
- `src/agentcaravan/adapters/`: runtime adapter namespace and compatibility projections
- `src/agentcaravan/bootstrap/`: local profile and packaged-source setup namespace
- `src/agentcaravan/execution_plan.py`: portable execution-plan construction
- `src/agentcaravan/codex_adapter.py`: Codex-specific execution-brief projection
- `tests/`: resolver, manifest, and integration verification
- `resources/core/`: default roles and Information Technology Core Team template
- `resources/runtime/`: AI-platform adapters and reusable runtime profiles
- `resources/specifications/`: runtime-neutral framework and artifact contracts
- execution-layer specifications for workflows, state separation, and role handoffs
- reusable execution policies for approvals, tool boundaries, retries, and escalation
- `examples/`: runnable scenarios built from fictional organizations and products
- `examples/sample-organization/`: fictional organization catalog, teams, domains, specializations, overlays, and resolved examples
- `docs/`: repository-specific framework concepts, schemas, runtime bridges, conformance, and contributor reference; AI-facing operating instructions are under `skills/`
- `docs/integrations/codex-adapter.md`: first concrete runtime adapter walkthrough
- `skills/`: shareable Agent Caravan builder, validator, resolver, and runtime-adapter skill sources
- `tools/`: repository maintenance and documentation synchronization helpers
- `catalog-manifest.json`: reference catalog contents and logical entry points

## Local State

The reference implementation keeps its default local profile outside this
repository under:

```text
~/.agents/agent-caravan/
```

For local profile setup and use, follow the
[Agent Caravan user guide](docs/user-guide.md).
Contributors can use `make init` (Codex default), `make init RUNTIME=opencode`,
or `make init RUNTIME=kiro`
to initialize a local profile from the checkout; Kiro IDE skills default to
`~/.kiro/skills/`. See the [repository setup guide](docs/getting-started.md).

The framework does not require GitLab, Git, JSON, or any particular storage provider. This repository is the Agent Caravan reference distribution and can be mirrored or consumed through another provider.

### GitHub Actions and packaging

GitHub Actions runs preflight, tests, example resolution, CLI smoke, and the
isolated installed-wheel smoke check on Python 3.10 and 3.14. The workflow does
not publish packages. `pyproject.toml` contains package metadata and
`agentcaravan.scripts` supplies the local verification commands.

Build and test tooling is pinned in the requirements files and build-system
metadata. Run the checks before distributing a package.

## Using Skills

The Python package bundles the skill sources. Setup installs the shared skills
and the selected runtime's orchestrator. Codex remains the default, with skills
under `~/.agents/skills/`; OpenCode uses `~/.config/opencode/skills/`, and Kiro
IDE uses `~/.kiro/skills/` by default.
Setup shows the runtime and destination. See
[installation and refresh examples](docs/reference/packaging-and-distribution.md#install-and-refresh-skills)
for custom roots, upgrades, preserved local edits, and using both runtimes.

## Contributing

Keep changes focused on the appropriate artifact boundary, update the catalog manifest when published roots or entries change, and run the verification commands below. Use Git tags or the selected distribution provider for release identity rather than adding a package version to the manifest.

## Verification

First complete the [development checkout setup](docs/getting-started.md#set-up-a-development-checkout)
and activate its virtual environment in your current terminal. The commands
below assume the checkout and its declared dependencies are installed there;
`PYTHONPATH=src` alone does not install them.

For a fast local gate before committing:

```text
PYTHONPATH=src python3 -m agentcaravan.scripts manifest
PYTHONPATH=src python3 -m agentcaravan.scripts compile
```

This checks manifest JSON syntax and Python compilation only. It does not run
AI review, access network services, or mutate local or remote state.

For the isolated-profile CLI golden path, run:

```text
PYTHONPATH=src python3 -m agentcaravan.scripts cli-smoke
```

This exercises starter initialization, Markdown configuration, root-aware
status guidance, dry-run evidence, and independent session validation using
temporary directories. `make cli-smoke` is the equivalent developer shortcut
used by GitHub Actions.

To validate the published-package boundary without network access:

```text
make package-smoke
```

This builds a wheel from a temporary repository copy, installs it into a
temporary isolated target directory with `--no-index`, and runs the
installed-wheel checks in `package_tests/`. These checks run separately from
the source-checkout unit and integration suite. Temporary build and installation
files are removed when the command completes. The active Python environment must be
Python 3.10 or newer and already contain the pinned `setuptools`,
`setuptools-scm`, and `wheel` build tools; the command does not download build
dependencies.

For full repository verification:

```text
PYTHONPATH=src python3 -m agentcaravan.scripts tests
PYTHONPATH=src python3 -m agentcaravan.scripts resolve-example
```

The complete local verification command is:

```text
PYTHONPATH=src python3 -m agentcaravan.scripts validate
```

The `Makefile` remains as a convenience wrapper for these commands and retains
setup-oriented targets such as `make init`. The script commands are the
canonical local validation interface. GitHub Actions runs these repository checks on supported Python versions.
