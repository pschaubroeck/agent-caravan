"""Vendor-neutral event records and CLI logging for Agent Caravan."""

from __future__ import annotations

import json
import logging
import re
import sys
import uuid
from datetime import datetime, timezone
from typing import Any


EVENT_SCHEMA_VERSION = "1.0.0"
_REDACT_KEY = re.compile(
    r"password|secret|token|authorization|prompt|response|content|tool_output|stdout|stderr|raw_text|body",
    re.IGNORECASE,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if _REDACT_KEY.search(str(key)) else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def event_record(
    event_type: str,
    *,
    source: str = "agentcaravan",
    severity: str = "INFO",
    outcome: str | None = None,
    context: dict[str, Any] | None = None,
    attributes: dict[str, Any] | None = None,
    timestamp: str | None = None,
    event_id: str | None = None,
) -> dict[str, Any]:
    """Build the common event envelope used for logs and execution events."""
    record: dict[str, Any] = {
        "schema_version": EVENT_SCHEMA_VERSION,
        "event_id": event_id or str(uuid.uuid4()),
        "timestamp": timestamp or _now(),
        "severity": severity.upper(),
        "source": source,
        "event_type": event_type,
        "attributes": _redact(attributes or {}),
    }
    if outcome is not None:
        record["outcome"] = outcome
    for key in ("task_id", "session_id", "run_id", "role_id", "stage_id"):
        value = (context or {}).get(key)
        if value is not None:
            record[key] = value
    return record


def normalize_execution_events(
    events: list[dict[str, Any]], *, source: str, context: dict[str, Any]
) -> list[dict[str, Any]]:
    """Wrap adapter events in the portable envelope while preserving their fields."""
    normalized = []
    for event in events:
        known = {
            "event_id", "timestamp", "severity", "source", "event_type", "kind", "status", "outcome",
            "task_id", "session_id", "run_id", "role_id", "stage_id", "attributes",
        }
        attributes = dict(event.get("attributes", {})) if isinstance(event.get("attributes"), dict) else {}
        attributes["native_fields"] = _redact({key: value for key, value in event.items() if key not in known})
        if "kind" in event:
            attributes["native_kind"] = event["kind"]
        native_type = event.get("event_type") or event.get("kind")
        if native_type:
            attributes["native_event_type"] = native_type
        severity = str(event.get("severity", "INFO")).upper()
        if severity not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            attributes["native_severity"] = event.get("severity")
            severity = "INFO"
        timestamp = event.get("timestamp")
        timestamp_source = "runtime"
        if timestamp is not None:
            try:
                parsed_timestamp = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
                if parsed_timestamp.tzinfo is None:
                    raise ValueError("timestamp has no timezone")
                timestamp = parsed_timestamp.isoformat().replace("+00:00", "Z")
            except ValueError:
                attributes["source_timestamp"] = timestamp
                timestamp = None
                timestamp_source = "agentcaravan_observed"
        else:
            timestamp_source = "agentcaravan_observed"
        event_source = event.get("source")
        if not isinstance(event_source, str) or not event_source:
            if event_source is not None:
                attributes["native_source"] = event_source
            event_source = source
        record = event_record(
            "agentcaravan.runtime.event",
            source=event_source,
            severity=severity,
            outcome=event.get("outcome", event["status"]),
            context={key: event.get(key, context.get(key)) for key in
                     ("task_id", "session_id", "run_id", "role_id", "stage_id")},
            attributes=attributes,
            timestamp=timestamp or _now(),
            event_id=event.get("event_id"),
        )
        record["timestamp_source"] = timestamp_source
        normalized.append(record)
    return normalized


class _EventJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        event = getattr(record, "agentcaravan_event", None)
        if not isinstance(event, dict):
            event = event_record(
                getattr(record, "event_type", "agentcaravan.log"),
                severity=record.levelname,
                attributes={"message": record.getMessage()},
            )
        return json.dumps(event, sort_keys=True, separators=(",", ":"))


class _EventTextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        event = getattr(record, "agentcaravan_event", {})
        event_type = event.get("event_type", getattr(record, "event_type", "agentcaravan.log"))
        identity = " ".join(
            f"{key}={event[key]}" for key in ("task_id", "session_id", "run_id") if event.get(key)
        )
        suffix = f" [{identity}]" if identity else ""
        return f"{_now()} {record.levelname} {event_type}{suffix}: {record.getMessage()}"


def configure_logging(level: str, output_format: str) -> None:
    """Replace Agent Caravan logger handlers with one predictable stderr handler."""
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(_EventJsonFormatter() if output_format == "json" else _EventTextFormatter())
    root = logging.getLogger("agentcaravan")
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level))
    root.propagate = False


def log_event(
    logger: logging.Logger,
    event_type: str,
    *,
    severity: str = "INFO",
    source: str = "agentcaravan",
    outcome: str | None = None,
    context: dict[str, Any] | None = None,
    attributes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event = event_record(
        event_type,
        source=source,
        severity=severity,
        outcome=outcome,
        context=context,
        attributes=attributes,
    )
    logger.log(getattr(logging, severity.upper()), event_type, extra={"agentcaravan_event": event})
    return event
