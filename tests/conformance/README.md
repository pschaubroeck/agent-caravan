# Adapter Conformance Scenarios

The scenarios in `scenarios.json` are runtime-neutral semantic test cases. An
adapter implementation consumes each scenario's task and expected result, runs
it through its own runtime projection, and compares the normalized semantic
result. Native traces may differ; role, handoff, approval, failure, resume, and
completion semantics should not. The shared scenarios also cover tool
permission boundaries, interrupted runs, checkpoint resume, idempotent
side-effect replay, and declared degraded-capability fallbacks.

The reusable harness is available through `agentcaravan.foundation`:

```python
from agentcaravan.foundation import load_conformance_scenarios, run_conformance_suite

scenarios = load_conformance_scenarios("tests/conformance/scenarios.json")
suite = run_conformance_suite(scenarios, adapter_executor, prepared=prepare_scenario)
suite.raise_for_failures()
```

With `prepared` supplied, the executor returns a runtime result payload and the
harness normalizes it against the prepared portable plan. Without `prepared`,
the executor must return an already normalized execution result.
