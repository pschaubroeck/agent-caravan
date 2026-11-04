# Foundation

This namespace groups runtime-neutral Agent Caravan contracts and source
loading utilities. Original flat module paths remain supported for
compatibility while the package boundary evolves.

Foundation code must not depend on Codex, Jira, GitLab, a particular storage
provider, or a concrete execution runtime.

The foundation exposes `prepare_execution` for building a validated portable
plan, plus `build_execution_records` and `build_completion_record` for
traceable task evidence. Runtime adapters may add a projection; the Codex
adapter exposes `prepare_codex_execution` to pair the portable plan with a
Codex-specific brief without changing the plan itself.
