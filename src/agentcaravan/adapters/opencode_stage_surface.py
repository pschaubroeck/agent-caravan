"""Read-only OpenCode CLI stage execution with native event provenance.

This surface reports one observed invocation. It does not create approvals,
role turns, handoffs, or a normalized conformance result.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ._process import run_with_process_group_timeout


class OpenCodeStageError(RuntimeError):
    """A stage did not produce a trustworthy read-only OpenCode receipt."""


class OpenCodeStageRunner:
    """Invoke one role and stage through OpenCode v1.18.33 CLI JSONL mode."""

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
        capture_content: bool = False,
        timeout_seconds: float = 900,
        run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        if not isinstance(model, str) or not re.fullmatch(r"[^\s/]+/[^\s/]+", model):
            raise OpenCodeStageError("model must be a provider/model identifier")
        if timeout_seconds <= 0:
            raise OpenCodeStageError("timeout_seconds must be positive")
        if not isinstance(capture_content, bool):
            raise OpenCodeStageError("capture_content must be boolean")
        self.cwd = Path(cwd)
        self.model = model
        self.executable = executable
        self.capture_content = capture_content
        self.timeout_seconds = timeout_seconds
        self._run = run

    def execute(
        self,
        *,
        task_id: str,
        run_id: str,
        stage_id: str,
        role_id: str,
        instruction: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        identifiers = (task_id, run_id, stage_id, role_id)
        if any(not isinstance(value, str) or not value.strip() for value in identifiers):
            raise OpenCodeStageError("task_id, run_id, stage_id, and role_id are required")
        if not isinstance(instruction, str) or not instruction.strip():
            raise OpenCodeStageError("instruction is required")
        if context is not None and not isinstance(context, dict):
            raise OpenCodeStageError("context must be an object")

        prompt = self._build_prompt(task_id, run_id, stage_id, role_id, instruction, context)
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
            version_call = run_with_process_group_timeout(
                self._run,
                [self.executable, "--version"],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
                cwd=str(self.cwd),
                env=env,
            )
            if version_call.returncode != 0:
                raise OpenCodeStageError("OpenCode version query failed")
            version = version_call.stdout.strip()
            if not re.fullmatch(r"(?:opencode\s+)?1\.18\.33", version, re.IGNORECASE):
                raise OpenCodeStageError(f"unsupported OpenCode version: {version!r}")
            self._verify_effective_permissions(env)
            started_at = self._now()
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
            completed_at = self._now()
        except subprocess.TimeoutExpired as error:
            raise OpenCodeStageError("OpenCode stage invocation timed out") from error
        except OSError as error:
            raise OpenCodeStageError(f"OpenCode CLI could not be started: {error}") from error

        if completed.returncode != 0:
            diagnostic = completed.stderr.strip()[-1500:]
            suffix = f": {diagnostic}" if diagnostic else ""
            raise OpenCodeStageError(
                f"OpenCode stage exited with status {completed.returncode}{suffix}"
            )
        events = self._parse_jsonl(completed.stdout)
        session_ids = {event["sessionID"] for event in events}
        if len(session_ids) != 1:
            raise OpenCodeStageError("OpenCode stage must have exactly one native sessionID")
        self._reject_unsupported_events(events)
        report = self._final_text(events)
        return {
            "task_id": task_id,
            "run_id": run_id,
            "stage_id": stage_id,
            "role_id": role_id,
            "report": report,
            "session_id": next(iter(session_ids)),
            "native_jsonl_events": events if self.capture_content else self._summarize_events(events),
            "requested_model": self.model,
            "model_identity_provenance": "requested-only",
            "version": version,
            "started_at": started_at,
            "completed_at": completed_at,
            "native_started_at": events[0].get("timestamp"),
            "native_completed_at": events[-1].get("timestamp"),
            "provenance": "reported-by-opencode",
            "receipt_source": "directly-observed-by-agentcaravan",
            "report_source": "reported-by-opencode",
            "permission_boundary": "application-level-read-only",
        }

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
            raise OpenCodeStageError(
                "could not verify OpenCode's effective read-only permissions before dispatch"
            ) from error
        if checked.returncode != 0:
            raise OpenCodeStageError(
                "could not verify OpenCode's effective read-only permissions before dispatch"
            )
        try:
            effective = json.loads(checked.stdout)
        except (json.JSONDecodeError, TypeError) as error:
            raise OpenCodeStageError(
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
            raise OpenCodeStageError(
                "OpenCode's effective permissions do not match the required read-only policy"
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _build_prompt(
        task_id: str,
        run_id: str,
        stage_id: str,
        role_id: str,
        instruction: str,
        context: dict[str, Any] | None,
    ) -> str:
        payload = {
            "task_id": task_id,
            "run_id": run_id,
            "stage_id": stage_id,
            "role_id": role_id,
            "instruction": instruction,
            "context": context or {},
        }
        return (
            "Perform only this Agent Caravan stage as the specified role. Read-only: "
            "do not edit files, run shell commands, invoke subagents, or request permissions. "
            "Return a stage report as plain text. Describe evidence you actually inspected "
            "and give source references. Do not claim human review, human approval, "
            "independent verification, or native delegation.\n"
            + json.dumps(payload, sort_keys=True, ensure_ascii=False)
        )

    @staticmethod
    def _parse_jsonl(stdout: str) -> list[dict[str, Any]]:
        if not isinstance(stdout, str) or not stdout.strip():
            raise OpenCodeStageError("OpenCode stage returned no JSONL events")
        events = []
        for number, line in enumerate(stdout.splitlines(), 1):
            try:
                event = json.loads(line)
            except json.JSONDecodeError as error:
                raise OpenCodeStageError(f"malformed OpenCode JSONL at line {number}") from error
            if not isinstance(event, dict) or not isinstance(event.get("type"), str):
                raise OpenCodeStageError(f"invalid OpenCode JSONL event at line {number}")
            if not isinstance(event.get("sessionID"), str) or not event["sessionID"]:
                raise OpenCodeStageError(f"OpenCode JSONL lacks sessionID at line {number}")
            events.append(event)
        return events

    @classmethod
    def _reject_unsupported_events(cls, events: list[dict[str, Any]]) -> None:
        for event in events:
            event_type = event["type"]
            if event_type.startswith("permission."):
                raise OpenCodeStageError("read-only stage encountered a permission event")
            if event_type in {"error", "session.error"}:
                raise OpenCodeStageError("OpenCode stage reported a runtime error")
            part = event.get("part")
            if isinstance(part, dict) and part.get("type") == "tool":
                tool = part.get("tool")
                if tool not in cls._READ_TOOLS:
                    raise OpenCodeStageError(f"read-only stage used unsupported tool: {tool!r}")

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
    def _final_text(events: list[dict[str, Any]]) -> str:
        parts = [
            event["part"].get("text")
            for event in events
            if event["type"] == "text"
            and isinstance(event.get("part"), dict)
            and event["part"].get("type") == "text"
        ]
        if not parts or not all(isinstance(part, str) for part in parts):
            raise OpenCodeStageError("OpenCode stage returned no text report")
        report = "".join(parts).strip()
        if not report:
            raise OpenCodeStageError("OpenCode stage report is empty")
        return report

__all__ = ["OpenCodeStageRunner", "OpenCodeStageError"]
