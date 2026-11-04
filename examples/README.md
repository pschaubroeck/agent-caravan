# Agent Caravan Examples

These examples pair readable guidance with artifacts and runnable checks. The
examples use fictional organizations and products so the framework guidance
can be reused without implying a vendor or customer-specific structure.

## Choose an example

| Example | What it demonstrates | Start here |
| --- | --- | --- |
| First organization and team | Configure one organization and a team from the shared blueprint | [Product Getting Started](../docs/getting-started.md) |
| Coworker team sharing | Resolve one shared team from separate local profiles, then collaborate through the shared catalog source | [Coworker-sharing scenario](coworker-sharing/README.md) |
| Codex team package | Install a versioned snapshot of that same team through a repository marketplace | [Codex plugin example](codex-plugins/example-organization-platform-team/README.md) |
| Organization coordination | Use a cookbook-owned map to route work among separately resolved teams | [Organization coordination](org-coordination/README.md) |
| Sample organization catalog | Read illustrative artifact models for multiple teams, ownership, and specialization | [Sample organization examples](sample-organization/README.md) |

The coworker-sharing scenario and Codex plugin use the same canonical artifacts
under [`example-organization/`](example-organization/). The catalog is the
collaborative source of truth; the plugin is a packaged snapshot that users
upgrade when they want a newer version.

## Runnable scenarios

Run the coworker-sharing example from the repository root:

```text
python3 examples/coworker-sharing/run.py
```

The script uses temporary profile roots and does not modify the active local
Agent Caravan profile. Integration tests check the shared source, independent
profile roots, and plugin snapshot against the canonical artifacts.

To try the local Codex marketplace example, register the checked-in marketplace
root with `codex plugin marketplace add ./examples/codex-plugins`, then install
the Example Organization Platform Team plugin from that marketplace. This is a
repository-hosted example marketplace, not a public Plugins Directory listing.

Print the organization-coordination example's routing plan from the repository
root:

```text
python3 examples/org-coordination/run.py
```

This is a deterministic dry run. It validates that the map points to published
caravans and prints the proposed handoffs; a harness performs any live
team resolution or work dispatch separately.

## Example conventions

- Keep reusable organization artifacts under `examples/<organization>/`.
- Keep scenario runners and coworker profile templates under the scenario that
  demonstrates them.
- Keep runtime-specific distribution wrappers, such as the Codex plugin,
  separate from the runtime-neutral organization artifacts.
- Keep organization hierarchy and cross-team routing maps inside their cookbook
  example. A harness interprets these maps; they are not Agent Caravan artifacts.
- Link documentation to runnable files and tests instead of maintaining a
  second prose-only copy of the example.
