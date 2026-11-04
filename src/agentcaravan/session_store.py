"""Reference local persistence for task, session, run, and completion records.

The Agent Caravan contracts do not require a filesystem store. This module is
the small local implementation used by the Codex adapter when a caller opts
into the repository's ``~/.agents/agent-caravan/sessions`` convention.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Protocol

from .session_validation import (
    SessionValidationError,
    validate_completion_payload,
    validate_persisted_records,
)
from .handoff import TaskHandoffError, validate_task_handoff


class SessionStoreError(ValueError):
    """Raised when execution state cannot be safely persisted."""


class ExecutionRecordStore(Protocol):
    """Persistence boundary for runtime-owned execution evidence."""

    def write_records(self, task_id: str, records: dict[str, dict[str, Any]]) -> None:
        """Write task, session, and one run record."""
        ...

    def write_completion(self, task_id: str, completion: dict[str, Any]) -> None:
        """Write the normalized terminal or interim completion payload."""
        ...


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$")


def _safe_id(value: str, field: str) -> str:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise SessionStoreError(f"{field} must be a filesystem-safe identifier")
    return value


class LocalJsonExecutionStore:
    """Persist concise execution records under an explicit local sessions root."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser()

    @classmethod
    def default(cls) -> "LocalJsonExecutionStore":
        """Build the reference implementation's default local store."""
        return cls(Path("~/.agents/agent-caravan/sessions").expanduser())

    def write_records(self, task_id: str, records: dict[str, dict[str, Any]]) -> None:
        task_key = _safe_id(task_id, "task_id")
        try:
            report = validate_persisted_records(task_key, records)
        except (TypeError, ValueError) as exc:
            raise SessionStoreError(str(exc)) from exc
        if not report["valid"]:
            raise SessionStoreError("; ".join(report["issues"]))

        task_record = records["task"]
        session_record = records["session"]
        run_record = records["run"]
        session_id = _safe_id(session_record["session_id"], "session_id")
        run_id = _safe_id(run_record["run_id"], "run_id")
        handoffs = self._collect_handoffs(task_key, records)

        task_root = self.root / task_key
        runs_root = task_root / "runs"
        with self._task_lock(task_root):
            self._recover_pending(task_root)
            self._write_records_locked(task_key, records, task_root, runs_root, handoffs)

    @staticmethod
    def _collect_handoffs(
        task_key: str, records: dict[str, dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        """Validate input-local handoff consistency before creating the task directory."""
        handoffs: dict[str, dict[str, Any]] = {}
        for record in (records["task"], records["session"], records["run"]):
            record_handoffs = record.get("handoffs", [])
            if not isinstance(record_handoffs, list):
                continue
            for handoff in record_handoffs:
                if not isinstance(handoff, dict):
                    continue
                if handoff.get("artifact_type") == "task-handoff":
                    try:
                        # Persisted task.plan contains only a plan ID/status
                        # reference. Plan-aware validation happens when the
                        # handoff is built or the normalized result is checked.
                        validate_task_handoff(handoff, task_id=task_key)
                    except TaskHandoffError as exc:
                        raise SessionStoreError(str(exc)) from exc
                handoff_id = handoff.get("handoff_id")
                if isinstance(handoff_id, str) and _SAFE_ID.fullmatch(handoff_id):
                    previous = handoffs.get(handoff_id)
                    if previous is not None and previous != handoff:
                        raise SessionStoreError(
                            f"divergent handoff payloads share handoff_id: {handoff_id}"
                        )
                    handoffs[handoff_id] = handoff
        return handoffs

    def _write_records_locked(
        self,
        task_key: str,
        records: dict[str, dict[str, Any]],
        task_root: Path,
        runs_root: Path,
        handoffs: dict[str, dict[str, Any]],
    ) -> None:
        task_record = records["task"]
        session_record = records["session"]
        run_record = records["run"]
        session_id = _safe_id(session_record["session_id"], "session_id")
        run_id = _safe_id(run_record["run_id"], "run_id")
        self._assert_existing_identity(
            task_root / "task.json",
            {"task_id": task_key},
            "task record",
        )
        self._assert_existing_identity(
            task_root / "session.json",
            {"session_id": session_id, "task_id": task_key},
            "session record",
        )
        self._assert_existing_identity(
            runs_root / f"{run_id}.json",
            {"run_id": run_id, "session_id": session_id, "task_id": task_key},
            "run record",
        )

        for handoff_id, handoff in handoffs.items():
            self._assert_existing_payload(
                task_root / "handoffs" / f"{handoff_id}.json",
                handoff,
                f"handoff {handoff_id}",
            )
        self._preserve_run_history(runs_root / f"{run_id}.json", run_record)
        writes = [
            ("task.json", task_record),
            ("session.json", session_record),
            (f"runs/{run_id}.json", run_record),
        ]
        for handoff in handoffs.values():
            handoff_id = handoff.get("handoff_id")
            if isinstance(handoff_id, str) and _SAFE_ID.fullmatch(handoff_id):
                writes.append((f"handoffs/{handoff_id}.json", handoff))
        self._preserve_lifecycle(task_root / "task.json", task_record, "task", {
            "active": 0, "blocked": 1, "completed": 2, "cancelled": 2,
        })
        self._preserve_lifecycle(task_root / "session.json", session_record, "session", {
            "active": 0, "paused": 1, "failed": 1, "completed": 2, "cancelled": 2,
        })
        self._commit_batch(task_root, writes)

    def write_completion(self, task_id: str, completion: dict[str, Any]) -> None:
        task_key = _safe_id(task_id, "task_id")
        try:
            validate_completion_payload(completion, task_id=task_key)
        except SessionValidationError as exc:
            raise SessionStoreError(str(exc)) from exc
        task_root = self.root / task_key
        with self._task_lock(task_root):
            self._recover_pending(task_root)
            self._assert_existing_completion(task_root / "completion.json", completion)
            self._commit_batch(task_root, [("completion.json", completion)])

    @staticmethod
    @contextmanager
    def _task_lock(task_root: Path):
        """Serialize writers for one task across processes on POSIX and Windows."""
        task_root.mkdir(parents=True, exist_ok=True)
        with (task_root / ".write.lock").open("a+") as lock_file:
            try:
                import fcntl
            except ImportError:
                import msvcrt

                lock_file.seek(0)
                if not lock_file.read(1):
                    lock_file.write("\0")
                    lock_file.flush()
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)

                def unlock() -> None:
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

                def unlock() -> None:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            try:
                yield
            finally:
                unlock()

    @classmethod
    def _commit_batch(cls, task_root: Path, writes: list[tuple[str, dict[str, Any]]]) -> None:
        """Journal a multi-file update so the next writer can finish it after a crash."""
        journal = task_root / ".pending-write.json"
        cls._write_json(journal, {"writes": [{"path": path, "payload": payload} for path, payload in writes]})
        cls._recover_pending(task_root)

    @classmethod
    def _recover_pending(cls, task_root: Path) -> None:
        journal = task_root / ".pending-write.json"
        pending = cls._read_existing_json(journal, "pending write journal")
        if pending is None:
            return
        writes = pending.get("writes")
        if not isinstance(writes, list):
            raise SessionStoreError("cannot recover pending write: journal writes must be an array")
        for item in writes:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not isinstance(item.get("payload"), dict):
                raise SessionStoreError("cannot recover pending write: invalid journal entry")
            relative = Path(item["path"])
            if relative.is_absolute() or ".." in relative.parts:
                raise SessionStoreError("cannot recover pending write: unsafe journal path")
            cls._write_json(task_root / relative, item["payload"])
        journal.unlink(missing_ok=True)

    @classmethod
    def _preserve_run_history(cls, path: Path, run_record: dict[str, Any]) -> None:
        existing = cls._read_existing_json(path, "run record")
        if existing is None:
            return
        old_status = existing.get("status")
        new_status = run_record.get("status")
        if old_status in {"completed", "failed", "cancelled", "degraded", "interrupted"} and old_status != new_status:
            raise SessionStoreError(f"terminal run status cannot change: {old_status} -> {new_status}")
        if old_status != "active" and old_status == new_status and existing != run_record:
            raise SessionStoreError("terminal run evidence is immutable")
        for field in ("evidence", "role_turns", "handoffs", "verification", "checkpoints", "idempotency_records", "reasoning_evidence"):
            old_values = existing.get(field)
            new_values = run_record.get(field)
            if isinstance(old_values, list) and isinstance(new_values, list):
                run_record[field] = old_values + [value for value in new_values if value not in old_values]

    @classmethod
    def _preserve_lifecycle(
        cls, path: Path, record: dict[str, Any], label: str, status_rank: dict[str, int]
    ) -> None:
        existing = cls._read_existing_json(path, f"{label} record")
        if existing is None:
            return
        old_status = existing.get("status")
        new_status = record.get("status")
        old_rank = status_rank.get(old_status)
        new_rank = status_rank.get(new_status)
        if old_rank is not None and new_rank is not None and new_rank < old_rank:
            # A retry can add a new run without moving the task/session summary
            # backward. A later successful run may still advance it to complete.
            record["status"] = old_status
        elif old_rank == new_rank == 2 and old_status != new_status:
            raise SessionStoreError(f"terminal {label} status cannot change: {old_status} -> {new_status}")

    @staticmethod
    def _read_existing_json(path: Path, label: str) -> dict[str, Any] | None:
        try:
            raw = path.read_text(encoding="utf-8")
            payload = json.loads(raw)
        except FileNotFoundError:
            return None
        except (OSError, json.JSONDecodeError) as exc:
            raise SessionStoreError(f"cannot safely replace existing {label}: {exc}") from exc
        if not isinstance(payload, dict):
            raise SessionStoreError(f"cannot safely replace existing {label}: payload must be an object")
        return payload

    @classmethod
    def _assert_existing_identity(
        cls, path: Path, expected: dict[str, str], label: str
    ) -> None:
        existing = cls._read_existing_json(path, label)
        if existing is None:
            return
        mismatches = [
            field for field, value in expected.items() if existing.get(field) != value
        ]
        if mismatches:
            raise SessionStoreError(
                f"existing {label} has conflicting identity: {', '.join(mismatches)}"
            )

    @classmethod
    def _assert_existing_payload(
        cls, path: Path, payload: dict[str, Any], label: str
    ) -> None:
        existing = cls._read_existing_json(path, label)
        if existing is not None and existing != payload:
            raise SessionStoreError(f"existing {label} has a divergent payload")

    @classmethod
    def _assert_existing_completion(cls, path: Path, completion: dict[str, Any]) -> None:
        existing = cls._read_existing_json(path, "completion")
        if existing is None or existing == completion:
            return
        existing_run_id = cls._completion_run_id(existing)
        completion_run_id = cls._completion_run_id(completion)
        if existing_run_id and completion_run_id and existing_run_id != completion_run_id:
            return
        raise SessionStoreError("existing completion has a divergent payload")

    @staticmethod
    def _completion_run_id(completion: dict[str, Any]) -> str | None:
        metadata = completion.get("metadata")
        execution_records = metadata.get("execution_records") if isinstance(metadata, dict) else None
        run = execution_records.get("run") if isinstance(execution_records, dict) else None
        run_id = run.get("run_id") if isinstance(run, dict) else None
        return run_id if isinstance(run_id, str) and run_id else None

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary_path = handle.name
                json.dump(payload, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, path)
            temporary_path = None
        finally:
            if temporary_path:
                try:
                    os.unlink(temporary_path)
                except FileNotFoundError:
                    pass


__all__ = ["ExecutionRecordStore", "LocalJsonExecutionStore", "SessionStoreError"]
