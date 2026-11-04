"""Single-invocation execution surface for the Codex CLI.

This adapter maps one portable Agent Caravan request to ``codex exec``. It does
not implement multi-role orchestration, staged approvals, or experiment policy.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable

from .codex_execution_surface import CodexExecutionRequest
from ._process import run_with_process_group_timeout
from ..org_framework_layout import _bundled_root


class CodexCliSurfaceError(RuntimeError):
    """Raised when the Codex CLI invocation cannot produce a trusted receipt."""


class CodexCliExecutionSurface:
    """Execute a single request with Codex CLI and retain its native events."""

    _RESULT_REQUIRED_FIELDS = frozenset({
        "artifact_type", "version", "task_id", "plan_id", "status", "active_roles",
        "completed_stages", "decisions", "execution_realization", "role_turns",
        "handoffs", "approvals", "artifacts", "evidence", "verification", "failures",
        "retries", "idempotency_records", "degraded_capabilities", "unresolved_conditions",
    })

    def __init__(
        self,
        *,
        cwd: str | Path,
        executable: str = "codex",
        model: str | None = None,
        sandbox: str = "read-only",
        approval_record: dict[str, Any] | None = None,
        timeout_seconds: float = 900,
        run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        if sandbox not in {"read-only", "workspace-write"}:
            raise CodexCliSurfaceError(f"unsupported Codex sandbox: {sandbox}")
        if sandbox == "workspace-write":
            raise CodexCliSurfaceError(
                "workspace-write is unavailable in the noninteractive Codex CLI surface; "
                "a supplied approval record cannot authenticate a human decision"
            )
        if approval_record is not None:
            raise CodexCliSurfaceError(
                "approval records are not accepted by the noninteractive Codex CLI surface"
            )
        if timeout_seconds <= 0:
            raise CodexCliSurfaceError("timeout_seconds must be positive")
        if model is not None and (not isinstance(model, str) or not model.strip() or any(character.isspace() for character in model)):
            raise CodexCliSurfaceError("model must be a nonempty model identifier")
        self.cwd = Path(cwd)
        self.executable = executable
        self.model = model
        self.sandbox = sandbox
        self.timeout_seconds = timeout_seconds
        self._run = run

    def execute(self, request: CodexExecutionRequest) -> dict[str, Any]:
        prompt = self._build_prompt(request)
        schema = {
            "type": "object",
            "required": ["result_json"],
            "properties": {
                "result_json": {"type": "string"},
            },
            "additionalProperties": False,
        }
        try:
            with tempfile.TemporaryDirectory(prefix="agentcaravan-codex-") as temporary:
                schema_path = Path(temporary) / "result.schema.json"
                schema_path.write_text(json.dumps(schema), encoding="utf-8")
                argv = [
                    self.executable,
                    "exec",
                    "--json",
                    "--sandbox",
                    self.sandbox,
                    "--output-schema",
                    str(schema_path),
                    "-",
                ]
                if self.model is not None:
                    argv[2:2] = ["--model", self.model]
                completed = run_with_process_group_timeout(
                    self._run,
                    argv,
                    input=prompt,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=self.timeout_seconds,
                    cwd=str(self.cwd),
                )
        except subprocess.TimeoutExpired as error:
            raise CodexCliSurfaceError("Codex CLI invocation timed out") from error
        except OSError as error:
            raise CodexCliSurfaceError(f"Codex CLI could not be started: {error}") from error

        if completed.returncode != 0:
            diagnostic = completed.stderr.strip()
            try:
                events = self._parse_jsonl(completed.stdout)
            except CodexCliSurfaceError:
                events = []
            failures = [event for event in events if event.get("type") in {"error", "turn.failed"}]
            if failures:
                diagnostic = f"{diagnostic}\n{json.dumps(failures[-1], sort_keys=True)}".strip()
            suffix = f": {diagnostic[-1500:]}" if diagnostic else ""
            raise CodexCliSurfaceError(f"Codex CLI exited with status {completed.returncode}{suffix}")
        events = self._parse_jsonl(completed.stdout)
        thread_ids = [event["thread_id"] for event in events if event.get("type") == "thread.started"]
        if len(thread_ids) != 1 or not thread_ids[0]:
            raise CodexCliSurfaceError("Codex JSONL must contain exactly one thread.started identity")
        result = self._final_result(events)
        if result.get("task_id") != request.task_id or result.get("plan_id") != request.prepared.get("plan", {}).get("id"):
            raise CodexCliSurfaceError("Codex structured result identity does not match the request")

        unsupported = [
            key for key in ("role_turns", "handoffs", "approvals", "execution_events")
            if result.get(key)
        ]
        run_record = result.get("run")
        if isinstance(run_record, dict) and run_record.get("events"):
            unsupported.append("run.events")
        realization = result.get("execution_realization")
        if isinstance(realization, dict) and (
            realization.get("native_subagents")
            or realization.get("parallel_lane_ids")
            or realization.get("delegation")
        ):
            unsupported.append("native delegation")
        if unsupported:
            raise CodexCliSurfaceError(
                "Codex CLI cannot substantiate claimed " + ", ".join(unsupported)
            )

        # Codex output is a runtime report. Preserve the event stream and demote
        # provenance labels that could otherwise be mistaken for human review.
        result = self._demote_claim_provenance(result)
        result["metadata"] = (
            dict(result["metadata"]) if isinstance(result.get("metadata"), dict) else {}
        )
        for unsupported_key in ("human_reviewed", "independently_verified", "native_delegation_observed"):
            result["metadata"].pop(unsupported_key, None)
        result["metadata"] = {
            **result["metadata"],
            "codex_cli": {
                "thread_id": thread_ids[0],
                "sandbox": self.sandbox,
                "native_jsonl_events": (
                    events if self._capture_content(request) else self._summarize_events(events)
                ),
                "final_result_provenance": "reported-by-codex",
                "model_identity": None,
                "requested_model": self.model,
                "human_reviewed": False,
                "independently_verified": False,
            },
        }
        return result

    @staticmethod
    def _capture_content(request: CodexExecutionRequest) -> bool:
        prepared = request.prepared if isinstance(request.prepared, dict) else {}
        runtime = prepared.get("runtime", {})
        observability = runtime.get("observability", {}) if isinstance(runtime, dict) else {}
        value = observability.get("capture_content", False) if isinstance(observability, dict) else False
        if not isinstance(value, bool):
            raise CodexCliSurfaceError("capture_content observability setting must be boolean")
        return value

    @staticmethod
    def _summarize_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        summaries = []
        for event in events:
            summary = {"type": event["type"]}
            for key in ("thread_id", "turn_id", "timestamp"):
                value = event.get(key)
                if isinstance(value, (str, int, float, bool)):
                    summary[key] = value
            item = event.get("item")
            if isinstance(item, dict):
                for key in ("id", "type", "status"):
                    value = item.get(key)
                    if isinstance(value, (str, int, float, bool)):
                        summary[f"item_{key}"] = value
            summaries.append(summary)
        return summaries

    @staticmethod
    def _demote_claim_provenance(value: Any) -> Any:
        if isinstance(value, list):
            return [CodexCliExecutionSurface._demote_claim_provenance(item) for item in value]
        if not isinstance(value, dict):
            return value
        result = {
            key: CodexCliExecutionSurface._demote_claim_provenance(item)
            for key, item in value.items()
        }
        if "source" in result:
            result["source"] = "reported-by-codex"
        if result.get("evidence_source") in {"human-reviewed", "independently-verified"}:
            result["evidence_source"] = "reported-by-codex"
        return result

    @staticmethod
    def _build_prompt(request: CodexExecutionRequest) -> str:
        scenario = request.scenario if isinstance(request.scenario, dict) else {}
        task = scenario.get("task", {})
        prepared = request.prepared if isinstance(request.prepared, dict) else {}
        contracts = json.loads(
            (_bundled_root() / "resources" / "schemas" / "execution-contracts.schema.json")
            .read_text(encoding="utf-8")
        )
        payload = {
            "scenario_id": scenario.get("id"),
            "task": task if isinstance(task, dict) else {},
            "portable_execution_plan": prepared.get("plan", {}),
            "runtime_brief": request.brief,
            "required_result_fields": sorted(CodexCliExecutionSurface._RESULT_REQUIRED_FIELDS),
            "result_contract_schema": {
                "$ref": "#/$defs/normalizedExecutionResult", "$defs": contracts["$defs"],
            },
        }
        return (
            "Execute the single task described by the supplied Agent Caravan plan and brief. "
            "Return one JSON object with a result_json string containing a serialized "
            "normalized-execution-result JSON object with every required field. "
            "Follow result_contract_schema for field types and allowed values, including "
            "execution_realization modes and degraded capabilities. The required_result_fields "
            "list defines the envelope; use empty arrays for "
            "unperformed collection fields and report unsupported work as incomplete or blocked. "
            "Report only work performed in this invocation; do not claim human review or "
            "independent verification unless that evidence is included in the supplied task.\n"
            + json.dumps(payload, sort_keys=True, ensure_ascii=False)
        )

    @staticmethod
    def _parse_jsonl(stdout: str) -> list[dict[str, Any]]:
        if not isinstance(stdout, str) or not stdout.strip():
            raise CodexCliSurfaceError("Codex CLI returned no JSONL events")
        events = []
        for line_number, line in enumerate(stdout.splitlines(), 1):
            try:
                event = json.loads(line)
            except json.JSONDecodeError as error:
                raise CodexCliSurfaceError(f"malformed Codex JSONL at line {line_number}") from error
            if not isinstance(event, dict) or not isinstance(event.get("type"), str):
                raise CodexCliSurfaceError(f"invalid Codex JSONL event at line {line_number}")
            events.append(event)
        return events

    @staticmethod
    def _final_result(events: list[dict[str, Any]]) -> dict[str, Any]:
        messages = [
            event.get("item", {}).get("text")
            for event in events
            if event.get("type") == "item.completed"
            and isinstance(event.get("item"), dict)
            and event["item"].get("type") == "agent_message"
        ]
        if not messages or not isinstance(messages[-1], str):
            raise CodexCliSurfaceError("Codex JSONL did not contain a final structured result")
        try:
            result = json.loads(messages[-1])
        except json.JSONDecodeError as error:
            raise CodexCliSurfaceError("Codex final response is not valid structured JSON") from error
        if isinstance(result, dict) and isinstance(result.get("result_json"), str):
            try:
                result = json.loads(result["result_json"])
            except json.JSONDecodeError as error:
                raise CodexCliSurfaceError("Codex result_json is not valid normalized JSON") from error
        if not isinstance(result, dict) or result.get("artifact_type") != "normalized-execution-result":
            raise CodexCliSurfaceError("Codex final response is not a normalized execution result")
        if not CodexCliExecutionSurface._RESULT_REQUIRED_FIELDS.issubset(result):
            raise CodexCliSurfaceError("Codex final structured result is missing required fields")
        return result


__all__ = ["CodexCliExecutionSurface", "CodexCliSurfaceError"]
