"""Resumable dependency experiment controller using the existing Codex adapter."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentcaravan.adapters.codex import prepare_codex_execution, run_codex_conformance_suite
from agentcaravan.resolve_framework import resolve_bundle


HERE = Path(__file__).resolve().parent
CASE_STAGES = {
    "dependency-approval-accept": ("need-assessment", "candidate-assessment", "independent-review",
                                 "dependency-change", "human-approval", "verification", "completion"),
    "dependency-approval-reject": ("need-assessment", "candidate-assessment", "independent-review",
                                 "rejection", "completion"),
}
ROLES = {"need-assessment": "engineer", "candidate-assessment": "engineer", "independent-review": "tech-owner",
         "dependency-change": "engineer", "human-approval": "program-manager", "verification": "engineer",
         "rejection": "program-manager", "completion": "program-manager"}


def _module(name: str):
    spec = importlib.util.spec_from_file_location(f"dependency_codex_{name}", HERE / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _save(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


class CodexExperimentDriver:
    """Advance one role stage, then stop at the actual external evidence gate."""

    def __init__(self, *, state_dir: str | Path, workspace: str | Path, model: str = "gpt-6.1-sol",
                 executable: str = "codex", runner=None, action_runner=None) -> None:
        self.state_dir, self.workspace = Path(state_dir), Path(workspace).resolve()
        self.model, self.executable = model, executable
        self.stage_module = _module("codex_stage_runner")
        self.action_module = _module("codex_action")
        self.runner = runner or self.stage_module.CodexStageRunner(cwd=self.workspace, model=model, executable=executable)
        self.action_runner = action_runner or self.action_module.CodexApprovedActionRunner(cwd=self.workspace, model=model, executable=executable)

    def case_dir(self, case_id: str) -> Path:
        if case_id not in CASE_STAGES:
            raise ValueError("unknown dependency experiment case")
        return self.state_dir / case_id

    def _identity(self, case_id: str) -> dict[str, str]:
        path = self.case_dir(case_id) / "identity.json"
        pinned = {"workspace": str(self.workspace), "requested_model": self.model,
                  "resolved_bundle_sha256": hashlib.sha256(json.dumps(
                      resolve_bundle(_module("bundle").build_codex_bundle()),
                      sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                  **{name: hashlib.sha256((HERE / filename).read_bytes()).hexdigest()
                     for name, filename in (("candidate_inputs_sha256", "inputs/candidate-evidence.json"),
                                            ("case_pack_sha256", "cases.json"),
                                            ("execution_profile_sha256", "execution-profile.json"))}}
        if path.exists():
            identity = json.loads(path.read_text())
            if any(identity.get(key) != value for key, value in pinned.items()):
                raise ValueError("saved run workspace, model, or pinned inputs changed")
            if any(not isinstance(identity.get(key), str) or not identity[key]
                   for key in ("task_id", "run_id", "session_id")):
                raise ValueError("saved experiment identity is invalid")
            return identity
        token = uuid4().hex
        manifest = self.workspace / "pyproject.toml"
        identity = {"task_id": f"dependency-evaluation-{token}", "run_id": f"run-{token}",
                    "session_id": f"session-{token}",
                    "baseline_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest() if manifest.exists() else None,
                    **pinned}
        _save(path, identity)
        return identity

    def _external(self, case_id: str) -> dict[str, Any]:
        path = self.case_dir(case_id) / "external-receipts.json"
        value = json.loads(path.read_text()) if path.exists() else {}
        if not isinstance(value, dict):
            raise ValueError("external receipts must be an object")
        return value

    def _stages(self, case_id: str) -> dict[str, dict[str, Any]]:
        identity, result = self._identity(case_id), {}
        seen = set()
        missing = False
        for stage in CASE_STAGES[case_id]:
            path = self.case_dir(case_id) / "stages" / f"{stage}.json"
            if not path.exists():
                missing = True
                continue
            if missing:
                raise ValueError("saved stage order contains a gap")
            receipt = json.loads(path.read_text())
            self.stage_module.validate_codex_stage_receipt(receipt)
            if any(receipt.get(key) != identity[key] for key in ("task_id", "run_id")) or (
                receipt["stage_id"] != stage or receipt["role_id"] != ROLES[stage]
                or receipt["requested_model"] != self.model or receipt["session_id"] in seen
            ):
                raise ValueError("saved stage does not match this run or repeats a thread")
            if result and datetime.fromisoformat(receipt["started_at"].replace("Z", "+00:00")) <= datetime.fromisoformat(list(result.values())[-1]["completed_at"].replace("Z", "+00:00")):
                raise ValueError("saved stages overlap or are out of order")
            seen.add(receipt["session_id"])
            result[stage] = receipt
        return result

    def _has(self, external: dict[str, Any], identity: dict[str, str], collection: str, kind: str) -> bool:
        values = external.get(collection, [])
        source, actor, clock = ("human-reviewed", "actor", "attested_at") if collection == "human_attestations" else ("independently-verified", "verifier", "verified_at")
        if not isinstance(values, list):
            raise ValueError("external receipt collection must be a list")
        matches = [item for item in values if isinstance(item, dict) and item.get("kind") == kind]
        if not matches:
            return False
        if len(matches) != 1:
            raise ValueError("duplicate external evidence kind")
        item = matches[0]
        if (any(item.get(key) != identity[key] for key in ("task_id", "run_id"))
                or item.get("source") != source or item.get("status") != "passed"
                or not item.get(actor) or not item.get("evidence_id") or not item.get("references")):
            raise ValueError("external evidence has a different scope or unsupported provenance")
        when = datetime.fromisoformat(item[clock].replace("Z", "+00:00"))
        if when.tzinfo is None or when > datetime.now(timezone.utc):
            raise ValueError("external evidence timestamp is invalid")
        return True

    def _gate(self, case_id: str, stage: str, external: dict[str, Any], identity: dict[str, str], stages: dict) -> str | None:
        requirements = []
        if stage == "candidate-assessment":
            requirements = [("human_attestations", "technical-need"), ("verification_receipts", "compatibility-assessment")]
            if case_id.endswith("reject"):
                requirements.append(("verification_receipts", "failed-hard-criterion"))
        elif stage in {"dependency-change", "rejection"}:
            requirements = [("human_attestations", "independent-review")]
        elif stage == "completion" and case_id.endswith("accept"):
            requirements = [("verification_receipts", "verification")]
        for collection, kind in requirements:
            if not self._has(external, identity, collection, kind):
                return kind
            if collection == "human_attestations":
                item = next(item for item in external[collection] if item["kind"] == kind)
                source_stage = stages["need-assessment" if kind == "technical-need" else "independent-review"]
                if (f"codex-thread:{source_stage['session_id']}" not in item["references"]
                        or datetime.fromisoformat(item["attested_at"].replace("Z", "+00:00"))
                        < datetime.fromisoformat(source_stage["completed_at"].replace("Z", "+00:00"))
                        or (kind == "independent-review" and item.get("disposition") != case_id.rsplit("-", 1)[-1])):
                    raise ValueError("human evidence does not review this completed native stage")
        if stage == "verification":
            if not external.get("approval_receipt"):
                return "approved-action"
            if not external.get("artifact_receipts"):
                return "independent-manifest-receipt"
        return None

    def _pending(self, case_id: str, identity: dict[str, str]) -> dict[str, Any]:
        path = self.case_dir(case_id) / "pending-approval.json"
        resolved = resolve_bundle(_module("bundle").build_codex_bundle())
        plan = prepare_codex_execution(resolved, {"task_id": identity["task_id"], "objective": "Assess the pinned dependency candidate."})["plan"]
        expected = {key: identity[key] for key in ("task_id", "run_id", "session_id")}
        expected.update(plan_id=plan["id"], action=self.action_module.manifest_action(),
                        baseline_manifest_sha256=identity["baseline_manifest_sha256"])
        if path.exists():
            pending = json.loads(path.read_text())
            if any(pending.get(key) != value for key, value in expected.items()):
                raise ValueError("pending approval has a different exact action scope")
            return pending
        pending = {**expected, "request_id": f"request-{uuid4().hex}", "requested_at": datetime.now(timezone.utc).isoformat(),
                   "enforcement": "external-controller-before-dispatch"}
        _save(path, pending)
        return pending

    def advance(self, case_id: str) -> dict[str, Any]:
        identity, stages, external = self._identity(case_id), self._stages(case_id), self._external(case_id)
        if case_id.endswith("reject") and (external.get("approval_receipt") or external.get("artifact_receipts")):
            raise ValueError("reject run cannot contain approval or changed artifacts")
        inputs = json.loads((HERE / "inputs/candidate-evidence.json").read_text())
        candidate = next(c for c in inputs["candidates"] if c["case_id"] == case_id)
        candidate = {key: value for key, value in candidate.items()
                     if key not in {"case_id", "expected_disposition", "criterion_results", "installation_prohibited", "approval"}}
        for stage in CASE_STAGES[case_id]:
            if stage in stages:
                continue
            needed = self._gate(case_id, stage, external, identity, stages)
            if needed == "approved-action":
                pending = self._pending(case_id, identity)
                failure = self.case_dir(case_id) / "failed-action.json"
                if failure.exists():
                    return {"status": "waiting-for-action-resolution", "stage_id": stage, "receipt": str(failure)}
                if self._has(external, identity, "human_attestations", "human-approval"):
                    decision = next(item for item in external["human_attestations"] if item["kind"] == "human-approval")
                    self.action_module.validate_decision(pending, decision)
                    if hashlib.sha256((self.workspace / "pyproject.toml").read_bytes()).hexdigest() != pending["baseline_manifest_sha256"]:
                        raise ValueError("dependency manifest changed since this run's baseline")
                    try:
                        receipt = self.action_runner.execute(pending, decision)
                        self.action_module.validate_controller_action_receipt(receipt, pending["action"])
                        if (any(receipt.get(key) != pending[key]
                            for key in ("task_id", "run_id", "plan_id", "request_id", "action", "requested_at"))):
                            raise ValueError("action runner returned an invalid scope")
                    except Exception as error:
                        _save(failure, {"task_id": identity["task_id"], "run_id": identity["run_id"],
                            "status": "indeterminate-post-dispatch", "error_type": type(error).__name__,
                            "receipt": getattr(error, "receipt", None)})
                        raise
                    external["approval_receipt"] = receipt
                    _save(self.case_dir(case_id) / "external-receipts.json", external)
                    return {"status": "action-completed", "stage_id": "dependency-change", "receipt": receipt}
                return {"status": "waiting-for-human-approval", "stage_id": stage, "request": pending}
            if needed:
                return {"status": "waiting-for-external-receipt", "stage_id": stage, "needed": needed}
            previous = list(stages.values())[-1] if stages else None
            context = {"candidate": candidate, "criteria": inputs["criteria"],
                       "previous_stage": {key: previous[key] for key in ("stage_id", "session_id", "report")} if previous else None,
                       "external_receipts": {key: external.get(key, []) for key in
                                             ("human_attestations", "verification_receipts", "artifact_receipts")}}
            receipt = self.runner.execute(task_id=identity["task_id"], run_id=identity["run_id"],
                stage_id=stage, role_id=ROLES[stage], instruction=f"Assess only {stage}; distinguish supplied evidence from your observations.", context=context)
            self.stage_module.validate_codex_stage_receipt(receipt)
            if (any(receipt.get(key) != identity[key] for key in ("task_id", "run_id"))
                    or receipt["stage_id"] != stage or receipt["role_id"] != ROLES[stage]
                    or receipt["requested_model"] != self.model
                    or receipt["session_id"] in {item["session_id"] for item in stages.values()}):
                raise ValueError("stage runner returned a different identity or repeated thread")
            _save(self.case_dir(case_id) / "stages" / f"{stage}.json", receipt)
            return {"status": "stage-completed", "stage_id": stage,
                    "receipt": str(self.case_dir(case_id) / "stages" / f"{stage}.json")}
        return {"status": "stages-completed"}

    def evaluate(self, case_id: str):
        identity, stages, external = self._identity(case_id), self._stages(case_id), self._external(case_id)
        if len(stages) != len(CASE_STAGES[case_id]):
            raise ValueError("all native role stages must complete before evaluation")
        resolved = resolve_bundle(_module("bundle").build_codex_bundle())
        scenario = next(s for s in json.loads((HERE / "cases.json").read_text())["scenarios"] if s["id"] == case_id)
        scenario = {**scenario, "task": {**scenario["task"], "task_id": identity["task_id"]}}
        inputs = json.loads((HERE / "inputs/candidate-evidence.json").read_text())
        builder = _module("codex_result_builder")

        class ReceiptSurface:
            def execute(self, request):
                return builder.build_codex_dependency_result(request, case_id=case_id,
                    stage_receipts=list(stages.values()), candidate_inputs=inputs,
                    human_attestations=external.get("human_attestations", []),
                    approval_receipt=external.get("approval_receipt"),
                    verification_receipts=external.get("verification_receipts", []),
                    artifact_receipts=external.get("artifact_receipts", []))

        return run_codex_conformance_suite(resolved, [scenario], ReceiptSurface(),
            run_id_factory=lambda _: identity["run_id"], session_id_factory=lambda _: identity["session_id"])
