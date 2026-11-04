# Runtime Verification Record Specification

## Purpose

This specification defines a portable record for reporting a runtime integration's
verification of one named scenario under one recorded set of conditions. The
record lets Agent Caravan validate the report's structure and scope while
leaving execution and evidence collection to the adapter that owns the runtime
integration.

The schema is
[`runtime-verification-record.schema.json`](../schemas/runtime-verification-record.schema.json).

## Record Scope

Every record identifies:

- the adapter and its implementation version
- the runtime product and version
- the execution surface, such as a CLI, SDK, hosted service, or broker endpoint
- material configuration, expressed as non-secret settings or a safe
  configuration fingerprint
- one scenario and its version, plus capability identifiers exercised by that
  scenario when known
- the outcome, record date, evidence provenance, and evidence references

An outcome applies only to the named scenario, runtime version, execution
surface, adapter version, and recorded configuration. It does not establish
general runtime compatibility, prove other scenarios, or establish that every
capability associated with the adapter works.

Configuration details must not contain credentials, tokens, personal data, or
other secrets. Secret-like configuration key names (such as `token`, `password`,
`credential`, and `api_key`) are rejected by the schema. This is a naming guard,
not secret scanning: the record producer remains responsible for ensuring
values and fingerprints do not disclose secrets or personal data. When settings
cannot safely be disclosed, record a stable fingerprint and identify the
fingerprint algorithm. The fingerprint should cover the material configuration
relevant to reproducing this scenario.

## Outcomes And Evidence

`result.status` is one of:

- `pass`: the named scenario met its stated expectations under the recorded
  conditions
- `fail`: the named scenario did not meet its expectations
- `degraded`: the scenario completed with a documented limitation or allowed
  degradation
- `unverified`: the available run or evidence cannot establish whether the
  scenario passed

`unsupported` is not a verification outcome. It describes a capability support
level in a runtime integration declaration. A missing verification record or an
`unverified` outcome does not mean the runtime or capability is unsupported.
Likewise, a failed scenario is evidence about that scenario and those
conditions; it is not by itself a general incompatibility claim.

Passing, failing, and degraded outcomes require at least one evidence
reference. An unverified record may have no evidence references, but should
explain the evidence gap in its summary or limitations. Evidence references
may identify adapter test output, runtime receipts, trace artifacts, or an
operator's observation record. Agent Caravan checks that references are
provided where required; it does not retrieve, authenticate, or independently
validate those sources.

The provenance kind records how the evidence was produced or observed. It is
descriptive metadata, not a trust assertion. In particular, labeling a source
`runtime-receipt` does not authenticate the receipt or prove which process
created it.

## Ownership And Use

The adapter implementation owns running the scenario, collecting runtime
evidence, and recording runtime-specific version and surface details. Agent Caravan
owns the portable schema and may validate record shape and references. A
consumer should preserve the record's scope when displaying or aggregating
results, and must not promote one scenario result into a universal compatibility
claim.

The format does not prescribe a repository layout, test runner, evidence store,
or runtime launch mechanism. Adapter implementations may live in this
repository or in separate repositories.
