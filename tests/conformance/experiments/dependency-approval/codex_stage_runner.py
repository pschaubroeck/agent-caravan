"""Bounded experiment stages using the existing Codex adapter and CLI surface."""
from __future__ import annotations

import json
import importlib.util
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from agentcaravan.adapters.codex import run_codex_task
from agentcaravan.adapters.codex_cli_surface import CodexCliExecutionSurface, CodexCliSurfaceError
from agentcaravan.resolve_framework import resolve_bundle


def build_codex_bundle():
    """Load the sibling experiment bundle without changing the import path."""
    specification = importlib.util.spec_from_file_location(
        "dependency_approval_codex_bundle", Path(__file__).with_name("bundle.py")
    )
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module.build_codex_bundle()


class CodexStageError(ValueError):
    """A bounded invocation could not provide a trustworthy stage receipt."""


def validate_codex_stage_receipt(receipt):
    """Validate native lifecycle and the report against the actual final message."""
    events = receipt.get("native_jsonl_events")
    if not isinstance(events, list) or not events:
        raise CodexStageError("missing native events")
    lifecycle = []
    for event in events:
        if not isinstance(event, dict):
            raise CodexStageError("invalid native event")
        kind = event.get("type")
        if kind in {"thread.started", "turn.started", "turn.completed"}:
            lifecycle.append(kind)
        elif kind in {"item.started", "item.updated", "item.completed"}:
            item = event.get("item")
            if lifecycle != ["thread.started", "turn.started"] or not isinstance(item, dict) or item.get("type") != "agent_message":
                raise CodexStageError("stage used a tool or unsupported item")
        else:
            raise CodexStageError("stage reported an error or unsupported event")
    if lifecycle != ["thread.started", "turn.started", "turn.completed"] or events[0].get("type") != "thread.started" or events[-1].get("type") != "turn.completed":
        raise CodexStageError("invalid native thread lifecycle")
    thread = events[0].get("thread_id")
    if not isinstance(thread, str) or not thread or thread != receipt.get("session_id"):
        raise CodexStageError("native thread identity mismatch")
    try:
        result = CodexCliExecutionSurface._final_result(events)
    except CodexCliSurfaceError as error:
        raise CodexStageError("invalid native final result") from error
    metadata = result.get("metadata")
    report = metadata.get("stage_report") if isinstance(metadata, dict) else None
    if not isinstance(report, str) or not report.strip() or report != receipt.get("report"):
        raise CodexStageError("native final stage report mismatch")
    if result.get("task_id") != receipt.get("task_id") or result.get("plan_id") != receipt.get("plan_id"):
        raise CodexStageError("native final identity mismatch")
    for field in ("task_id", "run_id", "stage_id", "role_id", "plan_id"):
        if not isinstance(receipt.get(field), str) or not receipt[field].strip():
            raise CodexStageError(f"missing {field}")
    try:
        start, end = [datetime.fromisoformat(receipt[field].replace("Z", "+00:00")) for field in ("started_at", "completed_at")]
        if start.tzinfo is None or end.tzinfo is None or end <= start:
            raise ValueError()
    except (KeyError, ValueError, AttributeError) as error:
        raise CodexStageError("invalid controller timestamps") from error
    expected = {"version": "0.159.0", "requested_model": "gpt-6.1-sol", "effective_model": None,
                "receipt_source": "directly-observed-by-agentcaravan", "report_source": "reported-by-codex",
                "permission_boundary": "sandbox-read-only"}
    if any(receipt.get(key) != value for key, value in expected.items()):
        raise CodexStageError("invalid stage provenance or runtime pin")
    return receipt


class CodexStageRunner:
    def __init__(self, *, cwd, model, executable="codex", timeout_seconds=180, run=subprocess.run):
        if model != "gpt-6.1-sol" or timeout_seconds <= 0:
            raise CodexStageError("stage requires gpt-6.1-sol and positive timeout")
        self.cwd, self.model, self.executable = Path(cwd), model, executable
        self.timeout_seconds, self._run = timeout_seconds, run

    def execute(self, *, task_id, run_id, stage_id, role_id, instruction, context=None):
        if any(not isinstance(value, str) or not value.strip() for value in (task_id, run_id, stage_id, role_id, instruction)):
            raise CodexStageError("stage identity and instruction are required")
        if context is not None and not isinstance(context, dict):
            raise CodexStageError("context must be an object")
        try:
            version = self._run([self.executable, "--version"], capture_output=True, text=True,
                                check=False, timeout=30, cwd=str(self.cwd))
            if version.returncode or not re.fullmatch(r"(?:codex(?:-cli)?\s+)?0\.159\.0", version.stdout.strip()):
                raise CodexStageError("unsupported Codex CLI version")
            def bounded_run(argv, **kwargs):
                argv = [*argv[:2], "--ignore-user-config", "--ignore-rules", "--ephemeral",
                        "-c", 'approval_policy="never"', "-c", 'model_reasoning_effort="medium"', *argv[2:]]
                completed = self._run(argv, **kwargs)
                # Never persist provider diagnostics or reasoning content.
                if completed.returncode:
                    raise CodexStageError(f"Codex stage exited with status {completed.returncode}")
                events = CodexCliExecutionSurface._parse_jsonl(completed.stdout)
                events = [event for event in events if not (isinstance(event.get("item"), dict) and event["item"].get("type") == "reasoning")]
                return subprocess.CompletedProcess(argv, 0, "\n".join(json.dumps(event) for event in events), "")
            resolved = resolve_bundle(build_codex_bundle())
            if resolved.get("status") not in {"pass", "degraded"}:
                raise CodexStageError("Codex experiment bundle did not resolve")
            task = {"task_id": task_id, "objective": "Perform only the supplied current stage",
                    "requested_action": "read-only stage report", "stage_id": stage_id, "role_id": role_id,
                    "instruction": "Perform only this current stage as the specified role. Use no tools, commands, subagents, edits, or permission requests. Return plain nonempty prose in metadata.stage_report of the normalized result. Do not claim human approval or independent verification. " + instruction,
                    "context": context or {}}
            started = datetime.now(timezone.utc).isoformat()
            result = run_codex_task(resolved, task, CodexCliExecutionSurface(cwd=self.cwd, executable=self.executable,
                                    model=self.model, sandbox="read-only", timeout_seconds=self.timeout_seconds,
                                    run=bounded_run), run_id=run_id)
            ended = datetime.now(timezone.utc).isoformat()
        except (subprocess.TimeoutExpired, OSError, CodexCliSurfaceError) as error:
            raise CodexStageError("Codex stage failed to start or timed out") from error
        metadata = result.get("metadata", {})
        native = metadata.get("codex_cli", {})
        receipt = {"task_id": task_id, "run_id": run_id, "stage_id": stage_id, "role_id": role_id,
                   "plan_id": result["plan_id"], "session_id": native.get("thread_id"),
                   "report": metadata.get("stage_report"), "native_jsonl_events": native.get("native_jsonl_events"),
                   "requested_model": self.model, "effective_model": None, "version": "0.159.0",
                   "started_at": started, "completed_at": ended, "receipt_source": "directly-observed-by-agentcaravan",
                   "report_source": "reported-by-codex", "permission_boundary": "sandbox-read-only"}
        return validate_codex_stage_receipt(receipt)
