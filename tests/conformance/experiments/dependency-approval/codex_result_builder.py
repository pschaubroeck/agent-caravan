"""Assemble dependency-approval conformance results from attributed receipts.

The caller supplies trusted controller receipts. Codex-authored prose is never
accepted as a human decision, independent check, role turn, or handoff.
"""

from __future__ import annotations

from datetime import datetime
import importlib.util
from pathlib import Path
import shlex
from typing import Any, Iterable

from agentcaravan.adapters.codex_execution_surface import CodexExecutionRequest

_SPEC = importlib.util.spec_from_file_location("dependency_codex_stage_validator", Path(__file__).with_name("codex_stage_runner.py"))
assert _SPEC and _SPEC.loader
_RUNNER = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_RUNNER)
validate_codex_stage_receipt = _RUNNER.validate_codex_stage_receipt
_ACTION_SPEC = importlib.util.spec_from_file_location("dependency_codex_action_validator", Path(__file__).with_name("codex_action.py"))
assert _ACTION_SPEC and _ACTION_SPEC.loader
_ACTION = importlib.util.module_from_spec(_ACTION_SPEC)
_ACTION_SPEC.loader.exec_module(_ACTION)
manifest_action = _ACTION.manifest_action
validate_controller_action_receipt = _ACTION.validate_controller_action_receipt


class DependencyResultError(ValueError):
    """A receipt is missing or cannot support the claimed result."""


_STAGES = {
    "dependency-approval-accept": (
        "need-assessment", "candidate-assessment", "independent-review",
        "dependency-change", "human-approval", "verification", "completion",
    ),
    "dependency-approval-reject": (
        "need-assessment", "candidate-assessment", "independent-review",
        "rejection", "completion",
    ),
}
_STAGE_ROLES = {
    "need-assessment": "engineer", "candidate-assessment": "engineer",
    "independent-review": "tech-owner", "dependency-change": "engineer",
    "human-approval": "program-manager", "verification": "engineer",
    "rejection": "program-manager", "completion": "program-manager",
}
_EXTERNAL_KINDS = {
    "candidate-identity": "identity",
    "license-assessment": "identity",
    "vulnerability-assessment": "advisories",
    "maintenance-assessment": "identity",
    "dependency-footprint": "identity",
}


def _time(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise DependencyResultError(f"{label} needs a timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise DependencyResultError(f"{label} has an invalid timestamp") from error
    if parsed.tzinfo is None:
        raise DependencyResultError(f"{label} needs a timezone")
    return parsed


def _required(record: dict[str, Any], fields: Iterable[str], label: str) -> None:
    if not isinstance(record, dict) or any(not record.get(field) for field in fields):
        raise DependencyResultError(f"{label} is missing required fields")


def _scoped(record: dict[str, Any], request: CodexExecutionRequest, label: str) -> None:
    _required(record, ("task_id", "run_id"), label)
    if (record["task_id"], record["run_id"]) != (request.task_id, request.run_id):
        raise DependencyResultError(f"{label} has a different task or run")


def _refs(record: dict[str, Any], label: str) -> list[str]:
    refs = record.get("references")
    if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) or not ref for ref in refs):
        raise DependencyResultError(f"{label} needs source references")
    return refs


def _receipt_map(
    receipts: Iterable[dict[str, Any]], request: CodexExecutionRequest,
    *, source: str, time_field: str, actor_field: str,
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in receipts:
        _scoped(item, request, "evidence receipt")
        _required(item, ("kind", "evidence_id", actor_field), "evidence receipt")
        if item.get("source") != source or item.get("status") != "passed":
            raise DependencyResultError(f"{item['kind']} has unsupported provenance or status")
        _time(item.get(time_field), item["kind"])
        _refs(item, item["kind"])
        if item["kind"] in result:
            raise DependencyResultError(f"duplicate {item['kind']} receipt")
        result[item["kind"]] = item
    return result


def _evidence(item: dict[str, Any], *, role: str, stage: str) -> dict[str, Any]:
    return {
        "evidence_id": item["evidence_id"], "kind": item["kind"],
        "status": item["status"], "source": item["source"],
        "references": list(item["references"]), "owner_role": role,
        "stage_id": stage,
        "metadata": {key: item[key] for key in ("actor", "verifier", "attested_at", "verified_at") if key in item},
    }


def _event(
    request: CodexExecutionRequest, *, kind: str, status: str,
    stage: str, role: str, timestamp: str, ref: str, evidence_id: str,
) -> dict[str, Any]:
    return {
        "event_id": f"{request.run_id}:{kind}:{status}",
        "task_id": request.task_id, "run_id": request.run_id,
        "session_id": request.session_id, "stage_id": stage, "role_id": role,
        "kind": kind, "status": status, "timestamp": timestamp,
        "evidence_refs": [evidence_id], "metadata": {"native_ref": ref},
    }


def _approval(receipt, request, attestation, change_ready_at):
    if not isinstance(receipt, dict):
        raise DependencyResultError("accept case needs an external-controller approval receipt")
    _scoped(receipt, request, "approval receipt")
    try:
        validate_controller_action_receipt(receipt, receipt.get("action"))
    except ValueError as error:
        raise DependencyResultError(str(error)) from error
    _required(receipt, ("plan_id", "request_id", "action", "controller_execution_id", "command_argv"), "approval receipt")
    if (receipt["plan_id"] != request.prepared["plan"]["id"]
            or receipt.get("execution_method") != "controller-direct-argv"
            or receipt.get("action") != manifest_action()
            or receipt.get("command_argv") != shlex.split(manifest_action())
            or "native_jsonl_events" in receipt or "native_thread_id" in receipt
            or receipt.get("execution_source") != "directly-observed-by-agentcaravan"
            or receipt.get("enforcement") != "external-controller-before-dispatch"):
        raise DependencyResultError("approval receipt has unsupported scope or provenance")
    decision = receipt.get("external_decision")
    if not isinstance(decision, dict):
        raise DependencyResultError("approval receipt lacks a caller decision")
    for key in ("task_id", "run_id", "request_id", "action"):
        if decision.get(key) != receipt[key]:
            raise DependencyResultError("caller decision differs from controller request")
    if (decision.get("approved") is not True or decision.get("provenance") != "caller-attested"
            or attestation.get("evidence_id") != "human-approval-evidence-1"
            or decision.get("evidence_id") != attestation["evidence_id"]
            or decision.get("actor") != attestation.get("actor")
            or decision.get("decided_at") != attestation.get("attested_at")
            or attestation.get("owner_role") != "program-manager"
            or attestation.get("request_id") != receipt["request_id"]
            or attestation.get("action") != receipt["action"]
            or f"controller-request:{receipt['request_id']}" not in attestation["references"]):
        raise DependencyResultError("human approval does not match the controller decision")
    times = [_time(value, "controller approval") for value in (
        change_ready_at, receipt.get("requested_at"), decision.get("decided_at"),
        receipt.get("started_at"), receipt.get("completed_at"))]
    if not all(left < right for left, right in zip(times, times[1:])):
        raise DependencyResultError("controller approval chronology is invalid")
    if (receipt.get("command_exit_status") != "passed"
            or type(receipt.get("command_exit_code")) is not int
            or receipt["command_exit_code"] != 0):
        raise DependencyResultError("approved command did not finish successfully")
    record = {
        "approval_id": "dependency-approval-1", "trigger": "new_dependency_or_integration",
        "status": "approved", "approval_lane": "program-manager", "decision_maker": "program-manager",
        "evidence_refs": [attestation["evidence_id"]],
        "references": [f"controller-request:{receipt['request_id']}", attestation["evidence_id"]],
        "task_id": request.task_id, "run_id": request.run_id,
        "enforcement": receipt["enforcement"], "request_id": receipt["request_id"],
    }
    return (record, receipt["requested_at"], decision["decided_at"], receipt["completed_at"],
            f"controller-request:{receipt['request_id']}", f"controller-decision:{receipt['request_id']}",
            f"controller-execution:{receipt['controller_execution_id']}")

def build_codex_dependency_result(
    request: CodexExecutionRequest,
    *,
    case_id: str,
    stage_receipts: Iterable[dict[str, Any]],
    candidate_inputs: dict[str, Any],
    human_attestations: Iterable[dict[str, Any]],
    approval_receipt: dict[str, Any] | None = None,
    verification_receipts: Iterable[dict[str, Any]] = (),
    artifact_receipts: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Return raw result only when every case-required claim has an observed source."""
    if case_id not in _STAGES or request.scenario.get("id") != case_id:
        raise DependencyResultError("case identity does not match the prepared request")
    if request.prepared.get("plan", {}).get("task", {}).get("task_id") != request.task_id:
        raise DependencyResultError("prepared task identity does not match the request")
    if candidate_inputs.get("experiment_id") != "dependency-approval" or not candidate_inputs.get("criteria", {}).get("criteria_id"):
        raise DependencyResultError("candidate criteria are not pinned")
    matches = [item for item in candidate_inputs.get("candidates", []) if item.get("case_id") == case_id]
    if len(matches) != 1:
        raise DependencyResultError("candidate input does not identify exactly one case")
    candidate = matches[0]
    _required(candidate, ("name", "version", "artifact", "criterion_results", "evidence"), "candidate")
    _required(candidate["artifact"], ("filename", "sha256"), "candidate artifact")
    if len(candidate["artifact"]["sha256"]) != 64 or any(ch not in "0123456789abcdef" for ch in candidate["artifact"]["sha256"]):
        raise DependencyResultError("candidate artifact SHA-256 is invalid")
    expected_disposition = "accept" if case_id.endswith("accept") else "reject"
    if candidate.get("expected_disposition") != expected_disposition:
        raise DependencyResultError("candidate disposition does not match the case")
    if expected_disposition == "accept" and any(
        status not in {"passed", "passed-with-source-limits"}
        for status in candidate["criterion_results"].values()
    ):
        raise DependencyResultError("accept candidate has an unpassed pinned criterion")

    stages: dict[str, dict[str, Any]] = {}
    for item in stage_receipts:
        _scoped(item, request, "stage receipt")
        _required(item, ("stage_id", "role_id", "session_id", "started_at", "completed_at",
                         "native_jsonl_events", "report", "version", "requested_model"), "stage receipt")
        stage = item["stage_id"]
        try:
            validate_codex_stage_receipt(item)
        except ValueError as error:
            raise DependencyResultError(f"{stage} is not an observed, scoped stage completion: {error}") from error
        if stage not in _STAGES[case_id] or item["role_id"] != _STAGE_ROLES[stage]:
            raise DependencyResultError("stage role or identity is unsupported")
        if _time(item["started_at"], stage) > _time(item["completed_at"], stage):
            raise DependencyResultError(f"{stage} completed before it started")
        if stage in stages:
            raise DependencyResultError(f"duplicate {stage} stage receipt")
        if item.get("plan_id") != request.prepared["plan"]["id"]:
            raise DependencyResultError("stage plan identity differs from request")
        if any(existing["session_id"] == item["session_id"] for existing in stages.values()):
            raise DependencyResultError("stages require separate native threads")
        stages[stage] = {**item, "native_ref": f"codex-thread:{item['session_id']}"}
    if set(stages) != set(_STAGES[case_id]):
        raise DependencyResultError("case is missing required observed stages")

    human = _receipt_map(human_attestations, request, source="human-reviewed", time_field="attested_at", actor_field="actor")
    verified = _receipt_map(verification_receipts, request, source="independently-verified", time_field="verified_at", actor_field="verifier")
    required_human = {"technical-need", "independent-review", "completion"}
    required_verified = {"compatibility-assessment"}
    if expected_disposition == "accept":
        required_human.add("human-approval")
        required_verified.add("verification")
    else:
        required_verified.add("failed-hard-criterion")
    if not required_human <= human.keys() or not required_verified <= verified.keys():
        raise DependencyResultError("case-required human or independent evidence is missing")
    if (human["independent-review"].get("disposition") != expected_disposition
            or human["completion"].get("disposition") != expected_disposition):
        raise DependencyResultError("human review and completion do not establish the case disposition")
    for kind, stage in (("technical-need", "need-assessment"),
                        ("independent-review", "independent-review"),
                        ("completion", "completion")):
        if stages[stage]["native_ref"] not in human[kind]["references"]:
            raise DependencyResultError(f"{kind} attestation does not reference its native stage")
        if _time(human[kind]["attested_at"], kind) < _time(stages[stage]["completed_at"], stage):
            raise DependencyResultError(f"{kind} attestation predates its stage")
    if expected_disposition == "reject" and verified["failed-hard-criterion"]["evidence_id"] not in human["independent-review"]["references"]:
        raise DependencyResultError("reject review does not reference the verified hard failure")
    if _time(stages["candidate-assessment"]["completed_at"], "candidate assessment") >= _time(stages["independent-review"]["started_at"], "independent review"):
        raise DependencyResultError("independent review began before candidate assessment finished")
    if expected_disposition == "reject" and (approval_receipt is not None or tuple(artifact_receipts)):
        raise DependencyResultError("reject case cannot have approval or changed artifacts")

    by_id = {item.get("evidence_id"): item for item in candidate["evidence"] if isinstance(item, dict)}
    def external(kind: str, token: str) -> dict[str, Any]:
        items = [item for item in by_id.values() if token in item.get("evidence_id", "")]
        if len(items) != 1 or items[0].get("source") != "reported-by-external-tool":
            raise DependencyResultError(f"candidate {kind} lacks pinned external evidence")
        item = items[0]
        _refs(item, kind)
        return {
            "evidence_id": f"{case_id}:{kind}", "kind": kind, "status": "passed",
            "source": "reported-by-external-tool", "references": list(item["references"]),
            "owner_role": "engineer", "stage_id": "candidate-assessment",
            "metadata": {"candidate_evidence_id": item["evidence_id"], "collected_on": item.get("collected_on")},
        }

    evidence = [
        _evidence(human["technical-need"], role="engineer", stage="need-assessment"),
        *[external(kind, token) for kind, token in _EXTERNAL_KINDS.items()],
        _evidence(verified["compatibility-assessment"], role="engineer", stage="candidate-assessment"),
        _evidence(human["independent-review"], role="tech-owner", stage="independent-review"),
        _evidence(human["completion"], role="program-manager", stage="completion"),
    ]
    if expected_disposition == "accept":
        evidence += [
            _evidence(human["human-approval"], role="program-manager", stage="human-approval"),
            _evidence(verified["verification"], role="engineer", stage="verification"),
        ]
    else:
        evidence.append(_evidence(verified["failed-hard-criterion"], role="engineer", stage="candidate-assessment"))
    if len({item["evidence_id"] for item in evidence}) != len(evidence):
        raise DependencyResultError("evidence IDs must be unique")

    role_turns = [
        {
            "role_turn_id": f"{request.run_id}:{stage}", "task_id": request.task_id,
            "run_id": request.run_id, "role_id": stages[stage]["role_id"],
            "stage_id": stage, "status": "completed", "summary": "Observed stage completion",
            "worker_ref": stages[stage]["session_id"],
            "started_at": stages[stage]["started_at"], "completed_at": stages[stage]["completed_at"],
        }
        for stage in _STAGES[case_id]
    ]
    # These two transfers are asserted only if both sender and receiver stages
    # have independent controller receipts in chronological order.
    handoffs = []
    for sender, receiver in (("candidate-assessment", "independent-review"), ("independent-review", "rejection" if expected_disposition == "reject" else "human-approval")):
        left, right = stages[sender], stages[receiver]
        if _time(left["completed_at"], sender) >= _time(right["started_at"], receiver):
            raise DependencyResultError("role handoff has no observed chronological boundary")
        if sender == "independent-review" and _time(human["independent-review"]["attested_at"], "independent review") >= _time(right["started_at"], receiver):
            raise DependencyResultError("program manager started before human review attestation")
        handoffs.append({
            "handoff_id": f"{request.run_id}:{sender}:{receiver}",
            "from": left["role_id"], "to": right["role_id"], "status": "completed",
            "task_id": request.task_id, "run_id": request.run_id,
            "references": [left["native_ref"], right["native_ref"]],
        })

    candidate_status = "passed" if expected_disposition == "accept" else "failed"
    candidate_evidence_id = f"{case_id}:candidate-identity"
    events = [
        _event(request, kind="candidate-assessment", status=candidate_status,
               stage="candidate-assessment", role="engineer",
               timestamp=stages["candidate-assessment"]["completed_at"],
               ref=stages["candidate-assessment"]["native_ref"], evidence_id=candidate_evidence_id),
        _event(request, kind="independent-review", status="completed",
               stage="independent-review", role="tech-owner",
               timestamp=human["independent-review"]["attested_at"],
               ref=stages["independent-review"]["native_ref"],
               evidence_id=human["independent-review"]["evidence_id"]),
    ]
    approvals: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    verification: list[dict[str, Any]] = []
    if expected_disposition == "accept":
        change = stages["dependency-change"]
        (approval, blocked_at, approved_at, applied_at,
         blocked_ref, approval_ref, applied_ref) = _approval(
            approval_receipt, request, human["human-approval"], max(change["completed_at"], stages["human-approval"]["completed_at"], key=lambda value: _time(value, "stage")),
        )
        if _time(stages["human-approval"]["completed_at"], "human-approval stage") > _time(human["human-approval"]["attested_at"], "human approval"):
            raise DependencyResultError("human approval predates its observed stage")
        approvals.append(approval)
        events += [
            _event(request, kind="dependency-change", status="blocked-until-approved",
                   stage="dependency-change", role="engineer", timestamp=blocked_at,
                   ref=blocked_ref, evidence_id=candidate_evidence_id),
            _event(request, kind="approval", status="approved", stage="human-approval",
                   role="program-manager", timestamp=approved_at, ref=approval_ref,
                   evidence_id=human["human-approval"]["evidence_id"]),
            _event(request, kind="dependency-change", status="applied", stage="dependency-change",
                   role="engineer", timestamp=applied_at, ref=applied_ref,
                   evidence_id=human["human-approval"]["evidence_id"]),
        ]
        artifact_items = list(artifact_receipts)
        if len(artifact_items) != 1:
            raise DependencyResultError("accept case needs one independently verified manifest receipt")
        artifact = artifact_items[0]
        _scoped(artifact, request, "artifact receipt")
        _required(artifact, ("artifact_id", "kind", "status", "source", "verifier", "verified_at"), "artifact receipt")
        if (artifact["kind"], artifact["status"], artifact["source"]) != ("dependency-manifest", "modified", "independently-verified"):
            raise DependencyResultError("artifact receipt does not verify the dependency manifest")
        _refs(artifact, "artifact receipt")
        if _time(artifact["verified_at"], "artifact receipt") <= _time(applied_at, "applied action"):
            raise DependencyResultError("manifest verification predates the approved action")
        artifacts.append(dict(artifact))
        checked = verified["verification"]
        # One independently checked batch may timestamp both receipts together.
        if _time(checked["verified_at"], "verification") < _time(artifact["verified_at"], "artifact receipt"):
            raise DependencyResultError("verification predates the verified manifest")
        if _time(stages["verification"]["completed_at"], "verification stage") < _time(checked["verified_at"], "verification receipt"):
            raise DependencyResultError("verification evidence postdates the stage")
        events.append(_event(request, kind="verification", status="passed", stage="verification",
                             role="engineer", timestamp=checked["verified_at"],
                             ref=stages["verification"]["native_ref"], evidence_id=checked["evidence_id"]))
        verification.append({"status": "passed", "evidence_refs": [checked["evidence_id"]]})
    else:
        if candidate["criterion_results"].get("draft-2020-12") != "failed" or candidate.get("installation_prohibited") is not True:
            raise DependencyResultError("reject candidate lacks pinned hard-criterion failure")
        failed = verified["failed-hard-criterion"]
        if _time(failed["verified_at"], "failed criterion") > _time(stages["candidate-assessment"]["completed_at"], "candidate assessment"):
            raise DependencyResultError("hard-criterion evidence postdates assessment")
        rejection = stages["rejection"]
        events.append(_event(request, kind="rejection", status="recorded", stage="rejection",
                             role="program-manager", timestamp=rejection["completed_at"],
                             ref=rejection["native_ref"], evidence_id=failed["evidence_id"]))

    ordered = [_time(event["timestamp"], event["kind"]) for event in events]
    if any(left >= right for left, right in zip(ordered, ordered[1:])):
        raise DependencyResultError("required events lack strict observed order")
    if _time(stages["completion"]["completed_at"], "completion") <= ordered[-1]:
        raise DependencyResultError("completion predates the final required event")
    if _time(human["completion"]["attested_at"], "completion attestation") <= ordered[-1]:
        raise DependencyResultError("human completion attestation predates final event")
    return {
        "status": "completed", "active_roles": ["engineer", "tech-owner", "program-manager"],
        "completed_stages": list(_STAGES[case_id]), "execution_realization": {
            "mode": "human-gated" if expected_disposition == "accept" else "native-sequential",
            "native_subagents": False,
        },
        "decisions": [{"kind": "dependency-disposition", "status": expected_disposition,
                       "evidence_refs": [human["independent-review"]["evidence_id"]]}],
        "role_turns": role_turns, "handoffs": handoffs, "approvals": approvals,
        "artifacts": artifacts, "evidence": evidence, "verification": verification,
        "execution_events": events, "failures": [], "retries": [],
        "idempotency_records": [], "degraded_capabilities": [], "unresolved_conditions": [],
        "run": {"run_id": request.run_id, "session_id": request.session_id},
        "metadata": {"case_id": case_id, "candidate": f"{candidate['name']}=={candidate['version']}",
                     "candidate_sha256": candidate["artifact"]["sha256"],
                     "external_controller_approval_receipt": approval_receipt,
                     "native_stage_receipts": [{"stage_id": stage, "session_id": stages[stage]["session_id"],
                                                "report": stages[stage]["report"],
                                                "report_source": stages[stage]["report_source"],
                                                "requested_model": stages[stage]["requested_model"],
                                                "version": stages[stage]["version"],
                                                "native_jsonl_events": stages[stage]["native_jsonl_events"]}
                                               for stage in _STAGES[case_id]]},
    }


__all__ = ["DependencyResultError", "build_codex_dependency_result"]
