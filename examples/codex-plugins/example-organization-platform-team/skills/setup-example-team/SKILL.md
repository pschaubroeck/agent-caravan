---
name: setup-example-team
description: Help install or inspect the versioned Example Organization catalog and team snapshot included with this plugin.
---

Use this skill when someone asks how to use the Example Organization team artifacts packaged with this plugin.

The plugin contains a versioned snapshot of the Example Organization catalog and its Platform and Product caravans. It does not synchronize with the shared catalog repository. To receive later changes, install a newer plugin version.

Before installing:

1. Confirm that Agent Caravan is installed and that the user has chosen the profile root where organization sources should live.
2. Explain that installation copies the snapshot into `sources/example-organization/` under that profile root.
3. Do not overwrite existing catalog or team files. The installer fails if the destination organization directory already exists; inspect and resolve that conflict deliberately before retrying.
4. Run the bundled installer only after the user asks to install the snapshot. The command is `python3 <plugin-root>/scripts/install_snapshot.py --profile-root <profile-root>`.
5. After installation, point the Agent Caravan profile at the copied source directory and select organization `example-organization` and the caravan that matches the task.

When someone asks how to discover this plugin from a repository checkout, tell them to run `codex plugin marketplace add ./examples/codex-plugins` from the repository root, then install `example-organization-platform-team` from that marketplace. Registering the marketplace and installing the plugin do not install the team artifacts into an Agent Caravan profile; use the opt-in installer above for that step.

To check whether the packaged copy matches the canonical repository example, run `python3 <plugin-root>/scripts/check_snapshot.py` from a repository checkout. This check reads files only. It requires the canonical source artifacts at `examples/example-organization/organizations/example-organization-catalog.json`, `examples/example-organization/caravans/platform-team.json`, and `examples/example-organization/caravans/product-team.json`.

Keep local preferences and overrides in the user's own profile. Shared team changes belong in the canonical catalog repository and should be reviewed there before a new plugin snapshot is released.
