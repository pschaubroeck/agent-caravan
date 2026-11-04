# Coordinate work across an organization

This cookbook example shows how an orchestration layer can use an organization
map to route work among existing Agent Caravan caravans. The map groups
teams under **Example Organization → Technology → Engineering**, records example
specialties and ownership, and includes illustrative `reports_to` labels.

The map is cookbook orchestration input. It is not an Agent Caravan artifact and
Agent Caravan does not resolve it or enforce its reporting lines, ownership,
permissions, routing, or handoffs. The runner validates the map's hierarchy and
team references, then prints a deterministic dry run; it does not call a model,
launch a runtime, or dispatch work. `reports_to` and `coordinator` are
descriptive labels only.

## Try the dry run

From the repository root, run:

```text
python3 examples/org-coordination/run.py
```

The runner checks that each referenced caravan is published by the Example
Organization catalog and has a matching team-instance JSON file. It also checks
that units and parent relationships are valid, and that the hierarchy has no
cycles. It then prints the default `shared-preferences-change` route.

## Reuse the sidecar

Pass your own map, catalog, team-instance directory, and scenario ID to the
runner. Paths are read from the current working directory when relative:

```text
python3 examples/org-coordination/run.py \
  --map ./organization/organization-map.json \
  --catalog ./organization/organization-catalog.json \
  --team-dir ./organization/team-instances \
  --scenario shared-api-change
```

The map must explicitly define each scenario's ordered route. Unit hierarchy,
team specialties, ownership, and reporting labels do not automatically select
teams or generate handoffs. The options all default to the checked-in example,
so the original command still works as shown above.

The default route is:

1. Product defines the customer behavior and workflow, then hands the agreed API
   contract to Platform.
2. Platform supports the shared API and returns its contract and integration
   guidance to Product.
3. Product integrates the API and completes the customer-facing workflow.

An AI harness can use this map as input, resolve each selected team with
Agent Caravan separately, and coordinate the listed handoffs. The harness is
responsible for interpreting this map and deciding whether to run the work.

The sidecar map uses the `team_instance_id` values from
`examples/example-organization/organizations/example-organization-catalog.json`
and team-instance artifacts under `examples/example-organization/caravans/`.
