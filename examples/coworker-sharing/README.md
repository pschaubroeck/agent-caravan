# Coworker sharing example

This runnable example shows two coworkers resolving one shared Example Organization catalog from separate local profile roots. The catalog and caravan are the shared source; each coworker's profile and future local customizations remain separate.

## Run the example

From the repository root, run:

```text
python3 examples/coworker-sharing/run.py
```

The runner creates temporary profile roots, loads the shared organization catalog and the repository's core/runtime resource bundles, and resolves both profiles. It prints each resolution status, the shared catalog/team/blueprint IDs and versions, and each temporary profile root. It does not read or write your real Agent Caravan profile.

The profile JSON files under `profiles/` are templates. Replace the example Git URL with the shared repository URL and `<shared-catalog-checkout>` with that employee's local checkout path. `subdirectory` selects the catalog inside the checkout. Keep `config.json`, overrides, sessions, and other personal state under each employee's own profile root. Agent Caravan reads the current checkout; it does not clone, fetch, or pull. Update it with the normal Git workflow. Resolved output reports the checkout revision and whether it has local changes.

## Share and update the team

1. Clone or update the repository that contains the shared catalog.
2. Point your local profile's Git source at your checkout and the catalog subdirectory. Coworkers may share one checkout or use separate local checkouts.
3. Propose team changes in the shared repository by editing the organization catalog or caravan and submitting them through that repository's normal review process.
4. After an accepted change is available, update your checkout and resolve the team again. Keep personal profile settings and local overrides in your own profile.

The team artifacts are the shared source of truth. The Codex plugin example packages a released snapshot of these same artifacts; coworkers upgrade that package to receive later updates.
