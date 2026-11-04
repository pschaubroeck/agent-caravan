"""Live, read-only Codex CLI stages with controller-observed timestamps."""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from agentcaravan.adapters._process import run_with_process_group_timeout
from agentcaravan.adapters.codex import prepare_codex_execution
from agentcaravan.adapters.codex_cli_surface import CodexCliExecutionSurface
from agentcaravan.resolve_framework import resolve_bundle


HERE = Path(__file__).resolve().parent
DEPENDENCY_EXPERIMENT = HERE.parent / "dependency-approval"


def _codex_bundle() -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location(
        "parallel_scheduling_codex_bundle", DEPENDENCY_EXPERIMENT / "bundle.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load shared Codex experiment bundle")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_codex_bundle()


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class CodexStageRunner:
    """Run one read-only role stage and retain only identity/timing metadata."""

    def __init__(self, *, cwd: str | Path, model: str, executable: str = "codex",
                 timeout_seconds: float = 300, run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run):
        if not isinstance(model, str) or not model.strip() or timeout_seconds <= 0:
            raise ValueError("model and positive timeout are required")
        self.cwd = Path(cwd)
        self.model = model
        self.executable = executable
        self.timeout_seconds = timeout_seconds
        self._run = run

    def execute(self, *, task_id: str, run_id: str, stage_id: str, role_id: str,
                instruction: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        version_result = self._run(
            [self.executable, "--version"], capture_output=True, text=True,
            check=False, timeout=30, cwd=str(self.cwd),
        )
        match = re.fullmatch(r"codex-cli\s+(\d+\.\d+\.\d+)", version_result.stdout.strip())
        if version_result.returncode != 0 or match is None:
            raise RuntimeError("could not establish the Codex CLI version")
        runtime_version = match.group(1)

        resolved = resolve_bundle(_codex_bundle())
        profile = deepcopy(resolved["execution_profile"])
        profile["entry_roles"] = [role_id]
        profile["activation_policy"] = {
            "primary_roles": [],
            "supporting_roles": [],
            "mandatory_reviewers": [],
        }
        profile["stages"] = [{
            "id": stage_id,
            "roles": [role_id],
            "mode": "sequential",
            "output": "bounded read-only stage report",
        }]
        profile["evidence_requirements"] = []
        profile["required_outputs"] = ["bounded read-only stage report"]
        profile["tool_requirements"] = []
        resolved["execution_profile"] = profile
        task = {
            "task_id": task_id,
            "objective": "Perform only the supplied read-only work item.",
            "requested_action": "read-only stage report",
            "stage_id": stage_id,
            "role_id": role_id,
            "instruction": instruction,
            "context": context or {},
        }
        prepared = prepare_codex_execution(resolved, task)
        role = next(item for item in resolved["effective_roles"] if item["id"] == role_id)
        prompt = (
            "Perform only the supplied Agent Caravan stage as the specified role. "
            "Use no tools, commands, subagents, edits, or permission requests. "
            "Return one JSON object containing a concise, nonempty stage_report. "
            "Do not claim independent verification.\n"
            + json.dumps({
                "stage_id": stage_id,
                "role": role,
                "instruction": instruction,
                "context": context or {},
                "portable_execution_plan": prepared["plan"],
                "runtime_brief": prepared["projection"],
            }, sort_keys=True, ensure_ascii=False)
        )
        output_schema = {
            "type": "object",
            "required": ["stage_report"],
            "properties": {"stage_report": {"type": "string", "minLength": 1}},
            "additionalProperties": False,
        }

        started_at = _timestamp()
        with tempfile.TemporaryDirectory(prefix="agentcaravan-stage-") as temporary:
            schema_path = Path(temporary) / "stage-report.schema.json"
            schema_path.write_text(json.dumps(output_schema), encoding="utf-8")
            argv = [
                self.executable,
                "exec",
                "--ignore-user-config",
                "--ignore-rules",
                "--ephemeral",
                "--skip-git-repo-check",
                "-c", 'approval_policy="never"',
                "-c", 'model_reasoning_effort="medium"',
                "--model", self.model,
                "--json",
                "--sandbox", "read-only",
                "--output-schema", str(schema_path),
                "-",
            ]
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
        completed_at = _timestamp()
        if completed.returncode != 0:
            diagnostic = completed.stderr.strip()[-1500:]
            suffix = f": {diagnostic}" if diagnostic else ""
            raise RuntimeError(f"Codex stage exited with status {completed.returncode}{suffix}")

        events = CodexCliExecutionSurface._parse_jsonl(completed.stdout)
        filtered = [
            event for event in events
            if not (isinstance(event.get("item"), dict) and event["item"].get("type") == "reasoning")
        ]
        lifecycle = []
        for event in filtered:
            kind = event.get("type")
            if kind in {"thread.started", "turn.started", "turn.completed"}:
                lifecycle.append(kind)
            elif kind in {"item.started", "item.updated", "item.completed"}:
                item = event.get("item")
                if (
                    lifecycle != ["thread.started", "turn.started"]
                    or not isinstance(item, dict)
                    or item.get("type") != "agent_message"
                ):
                    raise RuntimeError("Codex stage used a tool or unsupported native item")
            else:
                raise RuntimeError("Codex stage reported an unsupported native event")
        if lifecycle != ["thread.started", "turn.started", "turn.completed"]:
            raise RuntimeError("Codex stage lacked a complete native thread lifecycle")

        thread_ids = [event.get("thread_id") for event in filtered if event.get("type") == "thread.started"]
        messages = [
            event.get("item", {}).get("text")
            for event in filtered
            if event.get("type") == "item.completed"
            and isinstance(event.get("item"), dict)
            and event["item"].get("type") == "agent_message"
        ]
        if len(thread_ids) != 1 or not isinstance(thread_ids[0], str) or not thread_ids[0]:
            raise RuntimeError("Codex stage did not provide exactly one native thread identity")
        if not messages or not isinstance(messages[-1], str):
            raise RuntimeError("Codex stage did not provide a final structured response")
        try:
            stage_result = json.loads(messages[-1])
        except json.JSONDecodeError as error:
            raise RuntimeError("Codex stage response was not valid JSON") from error
        report = stage_result.get("stage_report") if isinstance(stage_result, dict) else None
        if not isinstance(report, str) or not report.strip():
            raise RuntimeError("Codex stage did not return a nonempty stage report")

        return {
            "task_id": task_id,
            "run_id": run_id,
            "stage_id": stage_id,
            "role_id": role_id,
            "session_id": thread_ids[0],
            "started_at": started_at,
            "completed_at": completed_at,
            "version": runtime_version,
            "report": report,
            "receipt_source": "directly-observed-by-agentcaravan",
            "report_source": "reported-by-codex",
            "permission_boundary": "sandbox-read-only",
        }
