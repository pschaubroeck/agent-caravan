# Agent Caravan Repository Instructions

## Scope

This repository is the canonical source for the Agent Caravan framework specifications, reference catalog artifacts, resolver prototype, and shareable Agent Caravan skills.

Keep the framework runtime-neutral and storage-agnostic. Git and GitLab are the current distribution implementation, not requirements imposed on the framework contract.

## Artifact Boundaries

- Put reusable responsibility semantics in `resources/core/responsibilities/`.
- Put reusable team composition and workflow in `resources/core/caravan-templates/`.
- Put durable organization-specific ownership in `examples/<organization>/caravans/`.
- Put organization-specific product or platform knowledge in `examples/<organization>/domain-knowledge/`.
- Put narrower team-owned knowledge in `examples/<organization>/capability-knowledge/`.
- Put organization-specific scoped changes in `examples/<organization>/configuration-overrides/`.
- Put runtime capability truth in `resources/runtime/integrations/`.
- Put reusable runtime profiles in `resources/runtime/mappings/`; organization-specific profiles belong under the relevant organization example.
- Keep local overrides and sessions outside the repository under `~/.agents/agent-caravan/`.

## Skill Sources

The `skills/agent-caravan-*` directories are shareable product skill sources. Package installation bundles these sources; explicit initialization installs the shared skills and selected runtime orchestrator. Codex defaults to `~/.agents/skills/`; OpenCode defaults to `~/.config/opencode/skills/`.

When changing a skill, preserve the distinction between framework semantics, runtime adapter behavior, and local operator configuration.

## Verification

Run the fast preflight gate before committing:

```text
make preflight
```

Run the focused framework gates before treating changes as complete:

```text
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 -m json.tool catalog-manifest.json > /dev/null
```

## Local Initialization

Use `make init` for interactive Codex setup or `make init RUNTIME=opencode`
for OpenCode. Default writes belong under `~/.agents/agent-caravan/` and the
selected runtime skill location (`~/.agents/skills/` for Codex or
`~/.config/opencode/skills/` for OpenCode); explicit CLI roots override these
locations. It must ask before replacing an existing organization or
skill link, and must refuse to remove a non-symlink skill path.

Validate changed skills with the available skill-authoring validator when the local runtime provides it. Do not install dependencies or mutate remote GitLab, Confluence, Jira, or runtime state as part of local verification.

## Change Discipline

- Preserve stable artifact IDs and explicit artifact versions.
- Do not add package release versions to `catalog-manifest.json`; release identity belongs to tags or distribution artifacts.
- Do not silently change published role meaning through runtime profiles or local overlays.
- Record unresolved source, ownership, compatibility, or validation assumptions in the relevant artifact or documentation.
