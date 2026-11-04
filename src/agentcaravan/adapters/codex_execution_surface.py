"""Explicit Codex execution request and surface contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from ..session_store import ExecutionRecordStore


@dataclass
class CodexExecutionRequest:
    """Complete input envelope crossing from Agent Caravan into Codex."""

    scenario: dict[str, Any]
    prepared: dict[str, Any]
    brief: dict[str, Any]
    records: dict[str, dict[str, Any]]
    store: ExecutionRecordStore | None = None

    @property
    def task_id(self) -> str:
        return self.records["task"]["task_id"]

    @property
    def session_id(self) -> str:
        return self.records["session"]["session_id"]

    @property
    def run_id(self) -> str:
        return self.records["run"]["run_id"]


class CodexExecutionSurface(Protocol):
    """Runtime-specific execution boundary for a prepared Codex request."""

    def execute(self, request: CodexExecutionRequest) -> dict[str, Any]:
        """Invoke Codex or a truthful simulation and return a raw result."""
        ...


class LegacyCodexExecutionSurface:
    """Adapt the original ``(scenario, brief)`` callback shape."""

    def __init__(self, callback: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]) -> None:
        self.callback = callback

    def execute(self, request: CodexExecutionRequest) -> dict[str, Any]:
        return self.callback(request.scenario, request.brief)


__all__ = ["CodexExecutionRequest", "CodexExecutionSurface", "LegacyCodexExecutionSurface"]
