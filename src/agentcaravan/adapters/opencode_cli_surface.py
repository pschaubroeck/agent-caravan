"""Read-only, single-request OpenCode v1 CLI execution surface.

The CLI permission policy is an application-level boundary, not an OS sandbox.
Approval-gated writes require a separately designed interactive surface.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Callable

from .opencode_execution_surface import OpenCodeExecutionRequest
from ._process import run_with_process_group_timeout


class OpenCodeCliSurfaceError(RuntimeError):
    """OpenCode could not produce a trustworthy single-request receipt."""


class OpenCodeCliExecutionSurface:
    """Run one read-only request with OpenCode and retain raw JSONL events."""

    _READ_ONLY_PERMISSION = {
        "*": "deny",
        "read": {
            "*": "allow",
            "*.env": "deny",
            "*.env.*": "deny",
            ".env": "deny",
            ".env.*": "deny",
            "*.env.example": "allow",
            ".env.example": "allow",
        },
        "glob": "allow",
        "grep": "deny",
        "list": "allow",
        "edit": "deny",
        "bash": "deny",
        "task": "deny",
        "external_directory": "deny",
    }
    _READ_TOOLS = frozenset({"read", "glob", "list"})

    def __init__(
        self,
        *,
        cwd: str | Path,
        model: str,
        executable: str = "opencode",
        mode: str = "read-only",
        timeout_seconds: float = 900,
        run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        if mode != "read-only":
            raise OpenCodeCliSurfaceError(
                "OpenCode CLI surface supports only read-only execution; "
                "approval-gated writes require an interactive surface"
            )
        if not isinstance(model, str) or not re.fullmatch(r"[^\s/]+/[^\s/]+", model):
            raise OpenCodeCliSurfaceError("model must be a provider/model identifier")
        if timeout_seconds <= 0:
            raise OpenCodeCliSurfaceError("timeout_seconds must be positive")
        self.cwd = Path(cwd)
        self.model = model
        self.executable = executable
        self.timeout_seconds = timeout_seconds
        self._run = run

    def execute(self, request: OpenCodeExecutionRequest) -> dict[str, Any]:
        prompt = self._build_prompt(request)
        # Inline config has the final runtime-override precedence in OpenCode v1.
        # Reassert deny rules even if the user's project config permits writes.
        safe_agent = "agentcaravan-readonly"
        config = {
            "permission": self._READ_ONLY_PERMISSION,
            "default_agent": safe_agent,
            "agent": {
                safe_agent: {
                    "mode": "primary",
                    "permission": self._READ_ONLY_PERMISSION,
                },
            },
        }
        env = {**os.environ, "OPENCODE_CONFIG_CONTENT": json.dumps(config)}
        argv = [
            self.executable, "--pure", "run", "--agent", safe_agent,
            "--format", "json", "--model", self.model, prompt,
        ]
        try:
            version_result = run_with_process_group_timeout(
                self._run,
                [self.executable, "--version"],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
                cwd=str(self.cwd),
                env=env,
            )
            if version_result.returncode != 0:
                raise OpenCodeCliSurfaceError("OpenCode version query failed")
            version = version_result.stdout.strip()
            if not re.fullmatch(r"(?:opencode\s+)?1\.18\.33", version, re.IGNORECASE):
                raise OpenCodeCliSurfaceError(f"unsupported OpenCode version: {version!r}")
            self._verify_effective_permissions(env)
            completed = run_with_process_group_timeout(
                self._run,
                argv,
                capture_output=True,
                text=True,
                check=False,
                timeout=self.timeout_seconds,
                cwd=str(self.cwd),
                env=env,
            )
        except subprocess.TimeoutExpired as error:
            raise OpenCodeCliSurfaceError("OpenCode CLI invocation timed out") from error
        except OSError as error:
            raise OpenCodeCliSurfaceError(f"OpenCode CLI could not be started: {error}") from error

        if completed.returncode != 0:
            diagnostic = completed.stderr.strip()[-1500:]
            suffix = f": {diagnostic}" if diagnostic else ""
            raise OpenCodeCliSurfaceError(
                f"OpenCode CLI exited with status {completed.returncode}{suffix}"
            )
        events = self._parse_jsonl(completed.stdout)
        self._audit_read_only_events(events)
        session_ids = {event.get("sessionID") for event in events}
        if len(session_ids) != 1 or not next(iter(session_ids)):
            raise OpenCodeCliSurfaceError("OpenCode JSONL must have one sessionID")
        result = self._final_result(events)
        plan = request.prepared.get("plan", {})
        if result.get("task_id") != request.task_id or result.get("plan_id") != plan.get("id"):
            raise OpenCodeCliSurfaceError("OpenCode result identity does not match the request")
        unsupported = [
            name for name in ("approvals", "role_turns", "handoffs", "execution_events")
            if result.get(name)
        ]
        run = result.get("run")
        if isinstance(run, dict) and run.get("events"):
            unsupported.append("run.events")
        if unsupported:
            raise OpenCodeCliSurfaceError(
                "read-only CLI cannot substantiate claimed " + ", ".join(unsupported)
            )
        realization = result.get("execution_realization")
        if not isinstance(realization, dict) or (
            realization.get("native_subagents")
            or realization.get("parallel_lane_ids")
            or realization.get("delegation")
            or realization.get("mode") not in {"native-sequential", "simulated-sequential", "unreported"}
        ):
            raise OpenCodeCliSurfaceError("read-only CLI cannot substantiate native delegation")
        result = self._demote_claim_provenance(result)
        result["metadata"] = (
            dict(result["metadata"]) if isinstance(result.get("metadata"), dict) else {}
        )
        for unsupported_key in ("human_reviewed", "independently_verified", "native_delegation_observed"):
            result["metadata"].pop(unsupported_key, None)
        result["metadata"] = {
            **result["metadata"],
            "opencode_cli": {
                "session_id": next(iter(session_ids)),
                "version": version,
                "requested_model": self.model,
                "model_identity_provenance": "requested-only",
                "native_jsonl_events": (
                    events if self._capture_content(request) else self._summarize_events(events)
                ),
                "final_result_provenance": "reported-by-opencode",
                "human_reviewed": False,
                "independently_verified": False,
                "permission_boundary": "application-level-read-only",
            },
        }
        return result

    def _verify_effective_permissions(self, env: dict[str, str]) -> None:
        try:
            checked = run_with_process_group_timeout(
                self._run,
                [self.executable, "debug", "config"],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
                cwd=str(self.cwd),
                env=env,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise OpenCodeCliSurfaceError(
                "could not verify OpenCode's effective read-only permissions before dispatch"
            ) from error
        if checked.returncode != 0:
            raise OpenCodeCliSurfaceError(
                "could not verify OpenCode's effective read-only permissions before dispatch"
            )
        try:
            effective = json.loads(checked.stdout)
        except (json.JSONDecodeError, TypeError) as error:
            raise OpenCodeCliSurfaceError(
                "OpenCode did not expose machine-readable effective permissions"
            ) from error
        agent = effective.get("agent", {}).get("agentcaravan-readonly") if isinstance(effective, dict) else None
        experimental = effective.get("experimental", {}) if isinstance(effective, dict) else {}
        if (
            not isinstance(effective, dict)
            or effective.get("permission") != self._READ_ONLY_PERMISSION
            or effective.get("default_agent") != "agentcaravan-readonly"
            or not isinstance(agent, dict)
            or agent.get("mode") != "primary"
            or agent.get("permission") != self._READ_ONLY_PERMISSION
            or (isinstance(experimental, dict) and experimental.get("policies"))
            or effective.get("policies")
        ):
            raise OpenCodeCliSurfaceError(
                "OpenCode's effective permissions do not match the required read-only policy"
            )

    @classmethod
    def _audit_read_only_events(cls, events: list[dict[str, Any]]) -> None:
        for event in events:
            event_type = event["type"]
            if event_type.startswith("permission."):
                raise OpenCodeCliSurfaceError("read-only CLI encountered a permission event")
            if event_type in {"error", "session.error"}:
                raise OpenCodeCliSurfaceError("OpenCode CLI reported a runtime error")
            part = event.get("part")
            if isinstance(part, dict) and part.get("type") == "tool":
                tool = part.get("tool")
                if tool not in cls._READ_TOOLS:
                    raise OpenCodeCliSurfaceError(
                        f"read-only CLI used unsupported tool: {tool!r}"
                    )

    @staticmethod
    def _capture_content(request: OpenCodeExecutionRequest) -> bool:
        prepared = request.prepared if isinstance(request.prepared, dict) else {}
        runtime = prepared.get("runtime", {})
        observability = runtime.get("observability", {}) if isinstance(runtime, dict) else {}
        value = observability.get("capture_content", False) if isinstance(observability, dict) else False
        if not isinstance(value, bool):
            raise OpenCodeCliSurfaceError("capture_content observability setting must be boolean")
        return value

    @staticmethod
    def _summarize_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        summaries = []
        for event in events:
            summary = {"type": event["type"], "sessionID": event["sessionID"]}
            for key in ("id", "timestamp"):
                value = event.get(key)
                if isinstance(value, (str, int, float, bool)):
                    summary[key] = value
            part = event.get("part")
            if isinstance(part, dict):
                for key in ("id", "type", "tool"):
                    value = part.get(key)
                    if isinstance(value, (str, int, float, bool)):
                        summary[f"part_{key}"] = value
                state = part.get("state")
                if isinstance(state, dict) and isinstance(state.get("status"), str):
                    summary["part_status"] = state["status"]
            summaries.append(summary)
        return summaries

    @staticmethod
    def _build_prompt(request: OpenCodeExecutionRequest) -> str:
        scenario = request.scenario if isinstance(request.scenario, dict) else {}
        prepared = request.prepared if isinstance(request.prepared, dict) else {}
        payload = {
            "scenario_id": scenario.get("id"),
            "task": scenario.get("task", {}),
            "portable_execution_plan": prepared.get("plan", {}),
            "opencode_projection": request.projection,
        }
        return (
            "Execute the supplied Agent Caravan read-only task. Do not modify files or "
            "run commands. Return only a normalized-execution-result JSON object. "
            "Report only work performed in this invocation. Do not claim human review, "
            "independent verification, or native delegation without evidence.\n"
            + json.dumps(payload, sort_keys=True, ensure_ascii=False)
        )

    @staticmethod
    def _parse_jsonl(stdout: str) -> list[dict[str, Any]]:
        if not stdout.strip():
            raise OpenCodeCliSurfaceError("OpenCode CLI returned no JSONL events")
        events = []
        for number, line in enumerate(stdout.splitlines(), 1):
            try:
                event = json.loads(line)
            except json.JSONDecodeError as error:
                raise OpenCodeCliSurfaceError(f"malformed OpenCode JSONL at line {number}") from error
            if not isinstance(event, dict) or not isinstance(event.get("type"), str):
                raise OpenCodeCliSurfaceError(f"invalid OpenCode JSONL event at line {number}")
            if not isinstance(event.get("sessionID"), str) or not event["sessionID"]:
                raise OpenCodeCliSurfaceError(f"OpenCode JSONL event lacks sessionID at line {number}")
            events.append(event)
        return events

    @staticmethod
    def _final_result(events: list[dict[str, Any]]) -> dict[str, Any]:
        parts = [
            event.get("part", {}).get("text")
            for event in events
            if event.get("type") == "text" and isinstance(event.get("part"), dict)
        ]
        if not parts or not all(isinstance(part, str) for part in parts):
            raise OpenCodeCliSurfaceError("OpenCode JSONL lacks a final text result")
        try:
            result = json.loads("".join(parts))
        except json.JSONDecodeError as error:
            raise OpenCodeCliSurfaceError("OpenCode final text is not JSON") from error
        if not isinstance(result, dict) or result.get("artifact_type") != "normalized-execution-result":
            raise OpenCodeCliSurfaceError("OpenCode final text is not a normalized execution result")
        required = {"version", "task_id", "plan_id", "status", "active_roles", "completed_stages", "decisions", "execution_realization", "role_turns", "handoffs", "approvals", "artifacts", "evidence", "verification", "failures", "retries", "idempotency_records", "degraded_capabilities", "unresolved_conditions"}
        if not required.issubset(result):
            raise OpenCodeCliSurfaceError("OpenCode result is missing required fields")
        return result

    @staticmethod
    def _demote_claim_provenance(value: Any) -> Any:
        if isinstance(value, list):
            return [OpenCodeCliExecutionSurface._demote_claim_provenance(item) for item in value]
        if not isinstance(value, dict):
            return value
        result = {
            key: OpenCodeCliExecutionSurface._demote_claim_provenance(item)
            for key, item in value.items()
        }
        if "source" in result:
            result["source"] = "reported-by-opencode"
        if result.get("evidence_source") in {"human-reviewed", "independently-verified"}:
            result["evidence_source"] = "reported-by-opencode"
        return result


__all__ = ["OpenCodeCliExecutionSurface", "OpenCodeCliSurfaceError"]
