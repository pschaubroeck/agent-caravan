"""OpenCode execution request boundary, independent of other runtimes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from ..session_store import ExecutionRecordStore


@dataclass
class OpenCodeExecutionRequest:
    """A prepared portable task and its OpenCode projection."""

    scenario: dict[str, Any]
    prepared: dict[str, Any]
    projection: dict[str, Any]
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


class OpenCodeExecutionSurface(Protocol):
    """Execute one request and return a raw normalized result with native evidence."""

    def execute(self, request: OpenCodeExecutionRequest) -> dict[str, Any]:
        ...


__all__ = ["OpenCodeExecutionRequest", "OpenCodeExecutionSurface"]
