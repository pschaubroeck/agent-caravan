"""Stable namespace for runtime-neutral Agent Caravan foundation contracts.

The original flat module paths remain supported. These exports provide a
clearer ownership boundary without requiring a breaking package move.
"""

from ..bundle_sources import BundleSource, BundleSourceError, InMemoryBundleSource, LocalJsonBundleSource
from ..execution_plan import ExecutionPlanError, build_portable_execution_plan, validate_portable_execution_plan
from ..handoff import TaskHandoffError, build_task_handoff, validate_task_handoff
from ..conformance import (
    ConformanceCaseResult,
    ConformanceError,
    ConformanceSuiteResult,
    load_conformance_scenarios,
    run_conformance_scenario,
    run_conformance_suite,
)
from ..execution_result import (
    ExecutionResultError,
    build_checkpoint_resume_result,
    build_degraded_result,
    build_idempotent_replay_result,
    build_interrupted_result,
    normalize_execution_result,
    validate_execution_realization,
    validate_normalized_execution_result,
)
from ..orchestration import (
    OrchestrationError,
    build_completion_record,
    build_execution_records,
    prepare_execution,
)
from ..profile import ProfileError, load_config, load_profile, load_source
from ..session_store import ExecutionRecordStore, LocalJsonExecutionStore, SessionStoreError
from ..session_validation import (
    SessionValidationError,
    validate_completion_payload,
    validate_persisted_records,
    validate_session_directory,
)

__all__ = [
    "BundleSource", "BundleSourceError", "ExecutionPlanError", "ExecutionResultError",
    "ExecutionRecordStore", "LocalJsonExecutionStore", "SessionStoreError", "SessionValidationError",
    "ConformanceCaseResult", "ConformanceError", "ConformanceSuiteResult",
    "InMemoryBundleSource", "LocalJsonBundleSource", "ProfileError",
    "build_completion_record", "build_execution_records", "build_portable_execution_plan",
    "build_checkpoint_resume_result", "build_degraded_result", "build_idempotent_replay_result",
    "build_interrupted_result", "normalize_execution_result", "validate_execution_realization", "validate_normalized_execution_result",
    "load_conformance_scenarios", "run_conformance_scenario", "run_conformance_suite",
    "load_config", "load_profile", "OrchestrationError", "prepare_execution",
    "load_source", "validate_portable_execution_plan",
    "TaskHandoffError", "build_task_handoff", "validate_task_handoff",
    "validate_completion_payload", "validate_persisted_records", "validate_session_directory",
]
