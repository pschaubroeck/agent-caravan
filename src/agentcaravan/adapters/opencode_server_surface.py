"""Bounded OpenCode v1.18.33 server approval gate.

This surface controls one exact shell action in a fresh session. It returns a
native approval receipt, not a complete Agent Caravan conformance result.
Independent review, role, and verification claims need separate evidence.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterator, Protocol
from urllib.parse import quote, urlsplit
from urllib.request import ProxyHandler, Request, build_opener

from .opencode_execution_surface import OpenCodeExecutionRequest


class OpenCodeServerSurfaceError(RuntimeError):
    """The server did not provide enough evidence to safely continue."""

    def __init__(self, message: str, *, partial_receipt: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.partial_receipt = partial_receipt


@dataclass(frozen=True)
class ApprovalDecision:
    """External decision supplied by a trusted caller after the native ask."""

    task_id: str
    run_id: str
    session_id: str
    permission_id: str
    action: str
    approved: bool
    actor: str
    decided_at: str
    evidence_id: str


class OpenCodeServerTransport(Protocol):
    def get(self, path: str) -> Any: ...

    def post(self, path: str, body: dict[str, Any]) -> Any: ...

    def events(self) -> Iterator[dict[str, Any]]: ...


class HttpOpenCodeServerTransport:
    """Minimal local HTTP/SSE client for a caller-managed OpenCode server."""

    def __init__(self, base_url: str, *, timeout_seconds: float = 300) -> None:
        parsed = urlsplit(base_url)
        if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise OpenCodeServerSurfaceError("OpenCode server URL must be local HTTP")
        if parsed.username or parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise OpenCodeServerSurfaceError("OpenCode server URL must be a bare local origin")
        if timeout_seconds <= 0:
            raise OpenCodeServerSurfaceError("timeout_seconds must be positive")
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        # The endpoint is restricted to loopback. Do not let HTTP_PROXY or
        # similar environment settings route approval traffic elsewhere.
        self._opener = build_opener(ProxyHandler({}))

    def get(self, path: str) -> Any:
        return self._json("GET", path)

    def post(self, path: str, body: dict[str, Any]) -> Any:
        return self._json("POST", path, body)

    def _json(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = Request(
            self.base_url + path,
            data=data,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method=method,
        )
        try:
            with self._opener.open(request, timeout=self.timeout_seconds) as response:
                raw = response.read()
        except Exception as error:
            raise OpenCodeServerSurfaceError(f"OpenCode {method} {path} failed") from error
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError as error:
            raise OpenCodeServerSurfaceError(f"OpenCode {method} {path} returned invalid JSON") from error

    def events(self) -> Iterator[dict[str, Any]]:
        request = Request(self.base_url + "/event", headers={"Accept": "text/event-stream"})
        try:
            with self._opener.open(request, timeout=self.timeout_seconds) as response:
                data: list[str] = []
                for raw_line in response:
                    line = raw_line.decode("utf-8").rstrip("\r\n")
                    if line.startswith("data:"):
                        data.append(line[5:].lstrip())
                    elif not line and data:
                        try:
                            event = json.loads("\n".join(data))
                        except json.JSONDecodeError as error:
                            raise OpenCodeServerSurfaceError("invalid OpenCode SSE event") from error
                        if not isinstance(event, dict):
                            raise OpenCodeServerSurfaceError("invalid OpenCode SSE event shape")
                        yield event
                        data = []
        except OpenCodeServerSurfaceError:
            raise
        except Exception as error:
            raise OpenCodeServerSurfaceError("OpenCode event stream failed") from error


class OpenCodeServerApprovalSurface:
    """Observe an ask, obtain one scoped decision, and verify the action result."""

    _POLICY = {"*": "deny", "read": "allow", "glob": "allow", "grep": "allow", "list": "allow", "bash": "ask"}

    def __init__(
        self,
        *,
        transport: OpenCodeServerTransport,
        model: str,
        agent: str,
        action: str,
        decide: Callable[[dict[str, Any]], ApprovalDecision],
        max_events: int = 500,
    ) -> None:
        if not model or "/" not in model or not agent or not action.strip() or max_events <= 0:
            raise OpenCodeServerSurfaceError("model, agent, action, and positive max_events are required")
        raise OpenCodeServerSurfaceError(
            "OpenCode server approvals are disabled: the server event/API contract cannot "
            "authenticate the human decision maker or distinguish a competing local responder"
        )
        self.transport = transport
        self.model = model
        self.agent = agent
        self.action = action
        self.decide = decide
        self.max_events = max_events

    def execute(self, request: OpenCodeExecutionRequest) -> dict[str, Any]:
        health = self.transport.get("/global/health")
        if not isinstance(health, dict) or health.get("healthy") is not True or health.get("version") != "1.18.33":
            raise OpenCodeServerSurfaceError("expected a healthy OpenCode v1.18.33 server")
        config = self.transport.get("/config")
        agents = config.get("agent") if isinstance(config, dict) else None
        selected = agents.get(self.agent) if isinstance(agents, dict) else None
        if not isinstance(selected, dict) or selected.get("permission") != self._POLICY:
            raise OpenCodeServerSurfaceError("selected agent must have the exact bounded permission policy")

        native = self.transport.post("/session", {"title": f"Agent Caravan {request.task_id} {request.run_id}"})
        session_id = native.get("id") if isinstance(native, dict) else None
        if not isinstance(session_id, str) or not session_id:
            raise OpenCodeServerSurfaceError("OpenCode did not return a session ID")
        stream = self.transport.events()
        first = next(stream, None)
        if not isinstance(first, dict) or first.get("type") != "server.connected":
            raise OpenCodeServerSurfaceError("OpenCode event stream was not connected before prompting")

        provider, model_id = self.model.split("/", 1)
        payload = {
            "agent": self.agent,
            "model": {"providerID": provider, "modelID": model_id},
            "parts": [{"type": "text", "text": self._prompt(request)}],
        }
        self.transport.post(f"/session/{quote(session_id, safe='')}/prompt_async", payload)
        ask: dict[str, Any] | None = None
        pending_permission_id: str | None = None
        decision: ApprovalDecision | None = None
        replied: dict[str, Any] | None = None
        applied: dict[str, Any] | None = None
        permission_response_attempted = False
        observed: list[dict[str, Any]] = []
        idle = False
        try:
            for index, event in enumerate(stream):
                if index >= self.max_events:
                    raise OpenCodeServerSurfaceError("OpenCode event limit reached")
                if not isinstance(event, dict) or not isinstance(event.get("type"), str):
                    raise OpenCodeServerSurfaceError("invalid OpenCode event")
                event = {**event, "observed_at": datetime.now(timezone.utc).isoformat()}
                props = event.get("properties")
                if not isinstance(props, dict):
                    continue
                if props.get("sessionID") != session_id:
                    continue
                observed.append(event)
                kind = event["type"]
                if kind == "permission.asked":
                    permission_id = props.get("id")
                    if isinstance(permission_id, str) and permission_id:
                        pending_permission_id = permission_id
                    command = (props.get("metadata") or {}).get("command")
                    tool = props.get("tool")
                    if (
                        ask is not None
                        or props.get("permission") != "bash"
                        or command != self.action
                        or not isinstance(permission_id, str)
                        or not event.get("id")
                        or not isinstance(tool, dict)
                        or not tool.get("messageID")
                        or not tool.get("callID")
                    ):
                        raise OpenCodeServerSurfaceError("unexpected or unattributed permission request")
                    ask = event
                    decision = self.decide({
                        "task_id": request.task_id,
                        "run_id": request.run_id,
                        "session_id": session_id,
                        "permission_id": permission_id,
                        "action": command,
                        "native_event_id": event.get("id"),
                        "native_tool": tool,
                    })
                    self._validate_decision(decision, request, session_id, permission_id)
                    asked_at = datetime.fromisoformat(event["observed_at"])
                    decided_at = datetime.fromisoformat(decision.decided_at.replace("Z", "+00:00"))
                    if not asked_at < decided_at <= datetime.now(timezone.utc):
                        raise OpenCodeServerSurfaceError("approval decision is not after the observed request")
                    response = "once" if decision.approved else "reject"
                    permission_response_attempted = True
                    ok = self.transport.post(
                        f"/session/{quote(session_id, safe='')}/permissions/{quote(permission_id, safe='')}",
                        {"response": response},
                    )
                    if ok is not True:
                        raise OpenCodeServerSurfaceError("OpenCode did not accept the scoped permission response")
                elif kind == "permission.replied":
                    if ask is None or replied is not None or props.get("requestID") != ask["properties"]["id"]:
                        raise OpenCodeServerSurfaceError("unmatched OpenCode permission reply")
                    if props.get("reply") != ("once" if decision and decision.approved else "reject"):
                        raise OpenCodeServerSurfaceError("OpenCode permission reply differs from the decision")
                    if not event.get("id"):
                        raise OpenCodeServerSurfaceError("OpenCode permission reply lacks native event ID")
                    if decision is None or datetime.fromisoformat(event["observed_at"]) < datetime.fromisoformat(decision.decided_at.replace("Z", "+00:00")):
                        raise OpenCodeServerSurfaceError("permission reply predates the decision")
                    replied = event
                    pending_permission_id = None
                elif kind == "message.part.updated":
                    part = props.get("part")
                    if not isinstance(part, dict) or part.get("type") != "tool":
                        continue
                    state = part.get("state")
                    if (
                        isinstance(state, dict)
                        and state.get("status") == "completed"
                        and isinstance(state.get("input"), dict)
                        and state["input"].get("command") == self.action
                    ):
                        if not (decision and decision.approved and replied) or part.get("callID") != ask["properties"]["tool"]["callID"]:
                            raise OpenCodeServerSurfaceError("protected action completed without the matched approval")
                        if not event.get("id"):
                            raise OpenCodeServerSurfaceError("protected action lacks native event ID")
                        if datetime.fromisoformat(event["observed_at"]) <= datetime.fromisoformat(replied["observed_at"]):
                            raise OpenCodeServerSurfaceError("protected action did not follow the reply")
                        applied = event
                elif kind == "session.status" and isinstance(props.get("status"), dict) and props["status"].get("type") == "idle":
                    idle = True
                    break
            if not idle or ask is None or decision is None or replied is None:
                raise OpenCodeServerSurfaceError("OpenCode session ended without a complete approval exchange")
            if decision.approved and applied is None:
                raise OpenCodeServerSurfaceError("approved action has no matching completed tool event")
            if not decision.approved and applied is not None:
                raise OpenCodeServerSurfaceError("rejected action was applied")
            exit_code = self._exit_code(applied)
            return {
                "task_id": request.task_id,
                "run_id": request.run_id,
                "opencode_session_id": session_id,
                "version": "1.18.33",
                "requested_model": self.model,
                "action": self.action,
                "permission_request": ask,
                "external_decision": {**decision.__dict__, "provenance": "caller-attested"},
                "permission_reply": {**replied, "provenance": "runtime-observed"},
                "action_completion": applied,
                "action_invocation_status": "completed" if applied is not None else "not-observed",
                "command_exit_status": (
                    "passed" if exit_code == 0 else "failed" if exit_code is not None else "unverified"
                ),
                "command_exit_code": exit_code,
                "native_events": (
                    observed if self._capture_content(request) else self._summarize_events(observed)
                ),
                "human_reviewed": False,
                "full_conformance": "unverified",
            }
        except Exception as error:
            partial = None
            if decision is not None and decision.approved and permission_response_attempted:
                partial = {
                    "task_id": request.task_id,
                    "run_id": request.run_id,
                    "opencode_session_id": session_id,
                    "action": self.action,
                    "permission_request": ask,
                    "external_decision": {**decision.__dict__, "provenance": "caller-attested"},
                    "permission_response_attempted": True,
                    "permission_reply": {**replied, "provenance": "runtime-observed"} if replied else None,
                    "action_completion": applied,
                    "action_invocation_status": "completed" if applied is not None else "indeterminate",
                    "command_exit_status": "indeterminate",
                    "native_events": (
                        observed if self._capture_content(request) else self._summarize_events(observed)
                    ),
                    "outcome": "indeterminate-post-approval",
                    "human_reviewed": False,
                    "full_conformance": "unverified",
                }
            # A pending ask must not survive an interrupted or invalid receipt.
            try:
                if pending_permission_id is not None:
                    self.transport.post(
                        f"/session/{quote(session_id, safe='')}/permissions/{quote(pending_permission_id, safe='')}",
                        {"response": "reject"},
                    )
                self.transport.post(f"/session/{quote(session_id, safe='')}/abort", {})
            except Exception:
                pass
            if partial is not None:
                raise OpenCodeServerSurfaceError(
                    "OpenCode approval run has an indeterminate post-approval outcome",
                    partial_receipt=partial,
                ) from error
            raise

    @staticmethod
    def _exit_code(completion: dict[str, Any] | None) -> int | None:
        if completion is None:
            return None
        part = completion.get("properties", {}).get("part", {})
        state = part.get("state", {}) if isinstance(part, dict) else {}
        metadata = state.get("metadata", {}) if isinstance(state, dict) else {}
        code = metadata.get("exit") if isinstance(metadata, dict) else None
        return code if isinstance(code, int) and not isinstance(code, bool) else None

    def _prompt(self, request: OpenCodeExecutionRequest) -> str:
        return (
            "Run the supplied Agent Caravan task. You may inspect files with the read tool. "
            "Do not use bash for inspection, including git status. Your first and only bash "
            "call must use the exact Action command below and wait for its permission decision. "
            "Do not alter, prefix, suffix, or combine that command with another command. "
            "If permission is rejected, stop. Do not claim human "
            "review, independent verification, roles, or approvals from your own text. "
            f"Task ID: {request.task_id}. Run ID: {request.run_id}. "
            f"Action: {self.action}. Portable plan: "
            + json.dumps(request.prepared.get("plan", {}), sort_keys=True)
        )

    @staticmethod
    def _capture_content(request: OpenCodeExecutionRequest) -> bool:
        prepared = request.prepared if isinstance(request.prepared, dict) else {}
        runtime = prepared.get("runtime", {})
        observability = runtime.get("observability", {}) if isinstance(runtime, dict) else {}
        value = observability.get("capture_content", False) if isinstance(observability, dict) else False
        if not isinstance(value, bool):
            raise OpenCodeServerSurfaceError("capture_content observability setting must be boolean")
        return value

    @staticmethod
    def _summarize_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        summaries = []
        for event in events:
            summary = {key: event[key] for key in ("type", "id", "observed_at") if key in event}
            properties = event.get("properties")
            if isinstance(properties, dict):
                retained = {
                    key: properties[key]
                    for key in ("sessionID", "id", "permission", "requestID", "reply")
                    if isinstance(properties.get(key), (str, int, float, bool))
                }
                tool = properties.get("tool")
                if isinstance(tool, dict):
                    retained["tool"] = {
                        key: tool[key] for key in ("messageID", "callID")
                        if isinstance(tool.get(key), (str, int, float, bool))
                    }
                part = properties.get("part")
                if isinstance(part, dict):
                    retained_part = {
                        key: part[key] for key in ("id", "type", "callID")
                        if isinstance(part.get(key), (str, int, float, bool))
                    }
                    state = part.get("state")
                    if isinstance(state, dict) and isinstance(state.get("status"), str):
                        retained_part["status"] = state["status"]
                    retained["part"] = retained_part
                if retained:
                    summary["properties"] = retained
            summaries.append(summary)
        return summaries

    def _validate_decision(
        self,
        decision: ApprovalDecision,
        request: OpenCodeExecutionRequest,
        session_id: str,
        permission_id: str,
    ) -> None:
        if not isinstance(decision, ApprovalDecision):
            raise OpenCodeServerSurfaceError("approval callback must return an ApprovalDecision")
        if (decision.task_id, decision.run_id, decision.session_id, decision.permission_id, decision.action) != (
            request.task_id, request.run_id, session_id, permission_id, self.action
        ):
            raise OpenCodeServerSurfaceError("approval decision scope does not match the native request")
        if not isinstance(decision.approved, bool) or not decision.actor.strip() or not decision.evidence_id.strip():
            raise OpenCodeServerSurfaceError("approval decision lacks actor or evidence identity")
        try:
            timestamp = datetime.fromisoformat(decision.decided_at.replace("Z", "+00:00"))
        except ValueError as error:
            raise OpenCodeServerSurfaceError("approval decision timestamp is invalid") from error
        if timestamp.tzinfo is None:
            raise OpenCodeServerSurfaceError("approval decision timestamp needs a timezone")


__all__ = [
    "ApprovalDecision",
    "HttpOpenCodeServerTransport",
    "OpenCodeServerApprovalSurface",
    "OpenCodeServerSurfaceError",
]
