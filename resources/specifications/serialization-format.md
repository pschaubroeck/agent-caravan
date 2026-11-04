# Machine-Readable Artifact Serialization

## Canonical Form

Agent Caravan uses JSON as the canonical machine-readable serialization for
artifacts consumed by the resolver, validators, and runtime integrations. JSON is a
transport and interchange choice for this reference implementation, not a
requirement that every catalog provider store files as JSON.

Every machine-readable artifact must preserve its stable `artifact_type`, `id`,
`version`, and `scope` fields. Providers may translate JSON to another
representation as long as logical identity, relationships, and validation
semantics are preserved.

## Markdown Documentation

Markdown files under `resources/`, `examples/`, and `docs/` are explanatory or
human-maintained reference documentation unless explicitly identified as a
machine-readable source. Markdown role and team documents must not be assumed
to be resolver input.

When a machine-readable artifact and Markdown explanation describe the same
concept:

- JSON is authoritative for runtime composition and validation
- Markdown explains intent, operating guidance, and human context
- changes to responsibility semantics must update both when both are published
- validators should identify missing or stale companion documentation where a
  catalog requires it

Any artifact may declare a `documentation_references` array. Each entry has a
required `uri` and may include `media_type`, `title`, and `purpose`. A URI may
identify a web document or a path understood by the artifact's source provider.
For Markdown, declare `media_type: text/markdown`. These entries link
supplemental human guidance to the artifact; they do not make Markdown a
machine-readable artifact or instruct the resolver to fetch it. Runtime
adapters may retrieve referenced documents only under the active
`knowledge_access` policy. Machine-readable artifact fields remain authoritative
if the guidance conflicts with them.

## Bundles And Individual Files

A JSON file may contain one artifact object or an `artifacts` list. A source
directory may contain multiple individual artifact files and bundles. Artifact
IDs, not filenames, are the logical references.
