# Example Organization Team Catalog Codex Plugin

This Codex plugin distributes a versioned snapshot of the Example Organization
catalog with its Platform and Product teams. The catalog is also used by the
[coworker-sharing scenario](../../coworker-sharing/README.md) and
[organization-coordination example](../../org-coordination/README.md). The
catalog repository remains the collaborative source of truth. Installing this
plugin gives a coworker a snapshot; it does not sync automatically when the
catalog changes.

## Try it from this repository

From the repository root, register the local marketplace directory:

```text
codex plugin marketplace add ./examples/codex-plugins
```

The marketplace file is at
[`../.agents/plugins/marketplace.json`](../.agents/plugins/marketplace.json),
and it points to this plugin directory. Install
`example-organization-platform-team` from the marketplace in Codex. Marketplace
installation makes the plugin skill available; it does not modify an
Agent Caravan profile or copy organization artifacts into a profile.

## Install the team snapshot

After Agent Caravan is installed and you have chosen a profile root, ask the
`setup-example-team` skill to install the team snapshot. The skill invokes the
bundled installer only on request. The equivalent command is:

```text
python3 <installed-plugin-root>/scripts/install_snapshot.py --profile-root <profile-root>
```

The installer creates `sources/example-organization/` under the profile root
and stops if that directory already exists. It does not merge with or replace
existing files. Then configure the profile to load that source and select
organization `example-organization` and the team you want, such as
`example-organization-platform-team` or `example-organization-product-team`.
Keep personal preferences and overrides in the profile's local configuration.

## Update and validate

The plugin snapshot is versioned. Coworkers receive later changes by installing
a newer plugin version. Shared changes belong in the canonical catalog and
should be reviewed there before refreshing the packaged snapshot.

From a repository checkout, check that the package still matches the canonical
artifacts with:

```text
python3 examples/codex-plugins/example-organization-platform-team/scripts/check_snapshot.py
```

This check is read-only and compares the packaged JSON artifacts byte-for-byte
with the matching files under `examples/example-organization/`.
