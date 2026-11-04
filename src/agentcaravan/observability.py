"""Optional Agent Observability markers for Agent Caravan-owned run boundaries."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from .telemetry import log_event


_LOGGER = logging.getLogger("agentcaravan.observability")
_DEFAULT_STORE = Path.home() / ".agent-observability" / "observations.jsonl"


def _load_components():
    """Load the optional Agent Observability package only for enabled runs."""
    from agent_observability.model import AssetIdentity
    from agent_observability.policy import CollectionPolicy, Selector
    from agent_observability.sessions import SessionStore

    return AssetIdentity, CollectionPolicy, Selector, SessionStore


def _marker_outcome(status: str) -> str:
    if status == "completed":
        return "ok"
    if status == "failed":
        return "error"
    if status == "cancelled":
        return "cancelled"
    return "unknown"


class RunObservation:
    """Best-effort lifecycle marker for one Agent Caravan workflow dispatch."""

    def __init__(self, context: dict[str, str], *, state: str, diagnostic: str | None = None):
        self.context = context
        self.state = state
        self.diagnostic = diagnostic
        self.store: Any = None
        self.handle: dict[str, str] | None = None
        self.finished = False

    @classmethod
    def start(cls, prepared: dict[str, Any], records: dict[str, dict[str, Any]]) -> RunObservation | None:
        runtime = prepared.get("runtime", {})
        settings = runtime.get("observability", {}) if isinstance(runtime, dict) else {}
        if not isinstance(settings, dict) or settings.get("enabled") is not True:
            return None

        run = records.get("run", {})
        context = {
            key: str(run[key])
            for key in ("task_id", "session_id", "run_id")
            if run.get(key) is not None
        }
        observation = cls(context, state="pending")
        if settings.get("export", "local") != "local":
            observation.state = "unavailable"
            observation.diagnostic = "remote_export_not_supported"
            return observation
        if settings.get("capture_content", False) is True:
            observation.state = "unavailable"
            observation.diagnostic = "content_capture_not_supported"
            return observation

        profile_id = run.get("execution_profile_id") or run.get("runtime_profile_id")
        if not isinstance(profile_id, str) or not profile_id:
            profile_id = run.get("runtime_adapter_id") or "workflow"
        try:
            AssetIdentity, CollectionPolicy, Selector, SessionStore = _load_components()
            identity = AssetIdentity("agentcaravan", profile_id)
            policy_path = os.environ.get("AWO_POLICY")
            policy = (
                CollectionPolicy.load(policy_path)
                if policy_path
                else CollectionPolicy(include=(Selector("workflow", identity.key),))
            )
            store_path = os.environ.get("AWO_STORE") or str(_DEFAULT_STORE)
            observation.store = SessionStore(store_path, policy=policy, harness="agentcaravan")
            started = observation.store.start(
                "workflow",
                identity,
                session_id=context.get("session_id"),
                invocation_id=context.get("run_id"),
                evidence="caller_declared",
            )
            if started.get("filtered"):
                observation.state = "filtered"
                return observation
            if not started.get("recorded"):
                observation.state = "failed"
                observation.diagnostic = observation.store.last_storage_error or "start_not_recorded"
                return observation
            observation.handle = {
                "trace_id": started["trace_id"],
                "span_id": started["span_id"],
            }
            observation.state = "recording"
        except Exception as error:
            observation.state = "failed"
            observation.diagnostic = "adapter_unavailable" if isinstance(error, ImportError) else "start_failed"
        return observation

    def finish(self, outcome: str) -> None:
        if self.state != "recording" or self.store is None or self.handle is None or self.finished:
            return
        self.finished = True
        try:
            result = self.store.finish(
                self.handle["trace_id"], self.handle["span_id"], outcome=outcome
            )
            if result.get("recorded"):
                self.state = "recorded"
            elif result.get("filtered"):
                self.state = "filtered"
                self.handle = None
            else:
                self.state = "failed"
                self.diagnostic = self.store.last_storage_error or "finish_not_recorded"
        except Exception:
            self.state = "failed"
            self.diagnostic = "finish_failed"

    def attach(self, *targets: dict[str, Any]) -> None:
        try:
            if self.diagnostic:
                log_event(
                    _LOGGER,
                    "agentcaravan.observability.capture_gap",
                    severity="WARNING",
                    context=self.context,
                    attributes={"diagnostic": self.diagnostic},
                )
            for target in targets:
                metadata = target.setdefault("metadata", {})
                if not isinstance(metadata, dict):
                    metadata = {}
                    target["metadata"] = metadata
                capture = {"state": self.state}
                if self.diagnostic:
                    capture["diagnostic"] = self.diagnostic
                metadata["observability_capture"] = capture

                if self.state != "recorded" or self.handle is None:
                    continue
                association = metadata.get("observability")
                association = dict(association) if isinstance(association, dict) else {}
                references = association.get("references", [])
                references = list(references) if isinstance(references, list) else []
                reference = f"agent-observability:{self.handle['trace_id']}/{self.handle['span_id']}"
                if reference not in references:
                    references.append(reference)
                association["references"] = references
                correlation = association.get("correlation", {})
                correlation = dict(correlation) if isinstance(correlation, dict) else {}
                for key in ("task_id", "session_id", "run_id"):
                    if key in self.context:
                        correlation.setdefault(key, self.context[key])
                association["correlation"] = correlation
                metadata["observability"] = association
        except Exception:
            # Optional capture must never change the Agent Caravan run outcome.
            self.state = "failed"
            self.diagnostic = "association_failed"


__all__ = ["RunObservation", "_marker_outcome"]
