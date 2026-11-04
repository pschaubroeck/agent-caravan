"""Externally approved pinned manifest action executed directly by the controller."""

from __future__ import annotations

import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

class CodexActionError(ValueError):
    """A failed action with bounded evidence that prevents silent redispatch."""

    def __init__(self, receipt: dict[str, Any]) -> None:
        super().__init__("approved controller action did not produce a trustworthy completed receipt")
        self.receipt = receipt


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("approval timestamp needs a timezone")
    return parsed


def manifest_action() -> str:
    """Return the experiment's one pinned dependency edit as an exact command."""
    program = (
        'from pathlib import Path; p=Path("pyproject.toml"); s=p.read_text(); '
        'marker=\'requires-python = ">=3.10"\'; '
        'assert s.count(marker)==1 and "dependencies =" not in s; '
        'p.write_text(s.replace(marker, marker+\'\\ndependencies = ["jsonschema==4.26.0"]\', 1))'
    )
    return shlex.join(["python3", "-c", program])


def validate_decision(pending: dict[str, Any], decision: dict[str, Any]) -> None:
    for field in ("task_id", "run_id", "request_id", "action"):
        if decision.get(field) != pending.get(field):
            raise ValueError("human approval does not match the pending exact action")
    if (decision.get("kind") != "human-approval" or decision.get("source") != "human-reviewed"
            or decision.get("status") != "passed" or decision.get("approved") is not True
            or decision.get("owner_role") != "program-manager"
            or not isinstance(decision.get("actor"), str) or not decision["actor"]
            or decision.get("evidence_id") != "human-approval-evidence-1"
            or f"controller-request:{pending['request_id']}" not in decision.get("references", [])):
        raise ValueError("exact action needs a scoped human approval attestation")
    when = _time(decision["attested_at"])
    if not _time(pending["requested_at"]) < when <= datetime.now(timezone.utc):
        raise ValueError("human approval predates its request or is in the future")


def validate_controller_action_receipt(receipt: dict[str, Any], action: str) -> dict[str, Any]:
    """Validate attributed direct execution without claiming native Codex action."""
    if (not isinstance(receipt, dict) or action != manifest_action()
            or receipt.get("action") != action
            or receipt.get("command_argv") != shlex.split(action)
            or receipt.get("execution_method") != "controller-direct-argv"
            or receipt.get("execution_source") != "directly-observed-by-agentcaravan"
            or receipt.get("enforcement") != "external-controller-before-dispatch"
            or type(receipt.get("command_exit_code")) is not int
            or receipt["command_exit_code"] != 0 or receipt.get("command_exit_status") != "passed"
            or not isinstance(receipt.get("controller_execution_id"), str)
            or receipt["controller_execution_id"] != str(receipt.get("request_id")) + ":action"
            or any(key in receipt for key in ("native_thread_id", "native_jsonl_events", "requested_model", "version"))):
        raise ValueError("action receipt does not establish the exact controller execution")
    return receipt


class CodexApprovedActionRunner:
    """Dispatch only after an attributed external controller decision."""

    def __init__(self, *, cwd: str | Path, model: str, executable: str = "codex",
                 timeout_seconds: float = 180, run: Callable = subprocess.run) -> None:
        if timeout_seconds <= 0:
            raise ValueError("controller action needs a positive timeout")
        self.cwd = Path(cwd)
        self.timeout_seconds, self._run = timeout_seconds, run

    def execute(self, pending: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
        validate_decision(pending, decision)
        if pending.get("action") != manifest_action():
            raise ValueError("controller may dispatch only the pinned manifest action")
        if pending.get("plan_id") != f"{pending['task_id']}-execution-plan":
            raise ValueError("approved action has a different portable plan")
        argv = shlex.split(manifest_action())
        started = _now()
        receipt = {
            **{key: pending[key] for key in ("task_id", "run_id", "plan_id", "request_id", "action", "requested_at")},
            "external_decision": {
                **{key: decision[key] for key in ("task_id", "run_id", "request_id", "action", "actor", "approved", "evidence_id")},
                "decided_at": decision["attested_at"], "provenance": "caller-attested",
            },
            "started_at": started, "execution_source": "directly-observed-by-agentcaravan",
            "enforcement": "external-controller-before-dispatch",
            "execution_method": "controller-direct-argv", "command_argv": argv,
            "controller_execution_id": pending["request_id"] + ":action",
        }
        try:
            completed = self._run(argv, cwd=str(self.cwd), capture_output=True, text=True,
                                  check=False, timeout=self.timeout_seconds, shell=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            receipt.update(completed_at=_now(), status="indeterminate-post-dispatch",
                           command_exit_status="indeterminate", command_exit_code=None, error_type=type(error).__name__)
            raise CodexActionError(receipt) from error
        receipt.update(completed_at=_now(), command_exit_code=completed.returncode,
                       command_exit_status="passed" if completed.returncode == 0 else "failed")
        if completed.returncode != 0:
            receipt["status"] = "failed"
            raise CodexActionError(receipt)
        return receipt
