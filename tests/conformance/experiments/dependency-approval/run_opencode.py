"""Resumable, read-only OpenCode stage driver for the dependency experiment.

Human attestations, the native approval exchange, and independent verification
are supplied as separate receipts. This driver never infers them from model text.
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentcaravan.adapters.opencode import run_opencode_conformance_suite
from agentcaravan.adapters.opencode_stage_surface import OpenCodeStageRunner
from agentcaravan.resolve_framework import resolve_bundle


HERE = Path(__file__).resolve().parent
CASE_STAGES = {
    "dependency-approval-accept": (
        "need-assessment", "candidate-assessment", "independent-review",
        "dependency-change", "human-approval", "verification", "completion",
    ),
    "dependency-approval-reject": (
        "need-assessment", "candidate-assessment", "independent-review",
        "rejection", "completion",
    ),
}
ROLES = {
    "need-assessment": "engineer", "candidate-assessment": "engineer",
    "independent-review": "tech-owner", "dependency-change": "engineer",
    "human-approval": "program-manager", "verification": "engineer",
    "rejection": "program-manager", "completion": "program-manager",
}


def _local_module(name: str):
    spec = importlib.util.spec_from_file_location(f"dependency_approval_{name}", HERE / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OpenCodeExperimentDriver:
    """Advance one observed stage at a time and evaluate a fully receipted case."""

    def __init__(
        self, *, state_dir: str | Path, workspace: str | Path, model: str,
        executable: str = "opencode", runner: OpenCodeStageRunner | None = None,
        allowed_previous_models: tuple[str, ...] = (),
    ) -> None:
        self.state_dir = Path(state_dir)
        self.workspace = Path(workspace)
        self.model = model
        if (isinstance(allowed_previous_models, str)
                or any(not isinstance(item, str) or not item for item in allowed_previous_models)):
            raise ValueError("allowed previous models must be explicit nonempty model IDs")
        self.allowed_previous_models = frozenset(allowed_previous_models)
        self.runner = runner or OpenCodeStageRunner(
            cwd=self.workspace, model=model, executable=executable,
        )

    def _identity(self, case_id: str) -> dict[str, str]:
        path = self.case_dir(case_id) / "identity.json"
        if path.exists():
            identity = json.loads(path.read_text(encoding="utf-8"))
            if (not isinstance(identity, dict)
                    or any(not isinstance(identity.get(key), str) or not identity[key]
                           for key in ("task_id", "run_id", "session_id"))):
                raise ValueError("saved experiment identity is invalid")
            return identity
        token = uuid4().hex
        identity = {
            "task_id": f"dependency-evaluation-{token}",
            "run_id": f"run-{token}",
            "session_id": f"session-{token}",
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as output:
            json.dump(identity, output, indent=2, sort_keys=True)
            output.write("\n")
        return identity

    def case_dir(self, case_id: str) -> Path:
        if case_id not in CASE_STAGES:
            raise ValueError(f"unknown dependency case: {case_id}")
        return self.state_dir / case_id

    def _stage_path(self, case_id: str, stage_id: str) -> Path:
        return self.case_dir(case_id) / "stages" / f"{stage_id}.json"

    def _external(self, case_id: str) -> dict[str, Any]:
        path = self.case_dir(case_id) / "external-receipts.json"
        if not path.exists():
            return {}
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("external-receipts.json must be an object")
        return value

    def _stages(self, case_id: str) -> dict[str, dict[str, Any]]:
        result = {}
        identity = self._identity(case_id)
        for stage_id in CASE_STAGES[case_id]:
            path = self._stage_path(case_id, stage_id)
            if path.exists():
                receipt = json.loads(path.read_text(encoding="utf-8"))
                if (receipt.get("task_id") != identity["task_id"]
                        or receipt.get("run_id") != identity["run_id"]
                        or receipt.get("stage_id") != stage_id
                        or receipt.get("role_id") != ROLES[stage_id]
                        or receipt.get("requested_model") not in {self.model, *self.allowed_previous_models}
                        or receipt.get("version") != "1.18.33"
                        or receipt.get("receipt_source") != "directly-observed-by-agentcaravan"
                        or not self._observed_stage(receipt)):
                    raise ValueError(f"saved {stage_id} receipt does not match this run")
                result[stage_id] = receipt
        return result

    @staticmethod
    def _observed_stage(receipt: dict[str, Any]) -> bool:
        events = receipt.get("native_jsonl_events")
        session = receipt.get("session_id")
        if not isinstance(session, str) or not session or not isinstance(events, list) or not events:
            return False
        if any(not isinstance(event, dict) or event.get("sessionID") != session for event in events):
            return False
        if not any(event.get("type") == "step_finish" for event in events):
            return False
        return any(
            event.get("type") == "text" and isinstance(event.get("part"), dict)
            and event["part"].get("type") == "text"
            for event in events
        )

    @staticmethod
    def _has(receipts: dict[str, Any], collection: str, kind: str) -> bool:
        values = receipts.get(collection, [])
        return isinstance(values, list) and any(
            isinstance(item, dict) and item.get("kind") == kind for item in values
        )

    def _missing_gate(self, case_id: str, stage_id: str, external: dict[str, Any]) -> str | None:
        if stage_id == "candidate-assessment":
            if not self._has(external, "human_attestations", "technical-need"):
                return "human technical-need attestation"
            if not self._has(external, "verification_receipts", "compatibility-assessment"):
                return "independent compatibility receipt"
            if case_id.endswith("reject") and not self._has(
                external, "verification_receipts", "failed-hard-criterion"
            ):
                return "independent failed-hard-criterion receipt"
        if stage_id in {"dependency-change", "rejection"} and not self._has(
            external, "human_attestations", "independent-review"
        ):
            return "human independent-review attestation"
        if stage_id == "verification":
            if not isinstance(external.get("approval_receipt"), dict):
                return "native approval receipt"
            if not external.get("artifact_receipts"):
                return "independent manifest receipt"
        if stage_id == "completion":
            if case_id.endswith("accept") and not self._has(
                external, "verification_receipts", "verification"
            ):
                return "independent verification receipt"
        return None

    def advance(self, case_id: str) -> dict[str, str]:
        """Run the next stage, or report the external gate without repeating stages."""
        stages = self._stages(case_id)
        external = self._external(case_id)
        candidate_inputs = json.loads(
            (HERE / "inputs" / "candidate-evidence.json").read_text(encoding="utf-8")
        )
        candidate = next(
            item for item in candidate_inputs["candidates"] if item["case_id"] == case_id
        )
        candidate_for_stage = {
            key: value for key, value in candidate.items()
            if key not in {"case_id", "expected_disposition", "criterion_results", "installation_prohibited"}
        }
        identity = self._identity(case_id)
        for stage_id in CASE_STAGES[case_id]:
            if stage_id in stages:
                continue
            gate = self._missing_gate(case_id, stage_id, external)
            if gate:
                return {"status": "waiting-for-external-receipt", "stage_id": stage_id, "needed": gate}
            previous = list(stages.values())[-1] if stages else None
            context = {
                "candidate": candidate_for_stage,
                "criteria": candidate_inputs["criteria"],
                "previous_stage": {
                    "stage_id": previous["stage_id"],
                    "session_id": previous["session_id"],
                    "report": previous["report"],
                } if previous else None,
                "external_receipt_kinds": {
                    key: [item.get("kind") for item in external.get(key, [])]
                    for key in ("human_attestations", "verification_receipts", "artifact_receipts")
                },
            }
            receipt = self.runner.execute(
                task_id=identity["task_id"], run_id=identity["run_id"],
                stage_id=stage_id, role_id=ROLES[stage_id],
                instruction=f"Assess the {stage_id} stage; report only observed facts.",
                context=context,
            )
            if (receipt.get("task_id") != identity["task_id"]
                    or receipt.get("run_id") != identity["run_id"]
                    or receipt.get("stage_id") != stage_id
                    or receipt.get("role_id") != ROLES[stage_id]
                    or receipt.get("requested_model") != self.model
                    or receipt.get("version") != "1.18.33"
                    or receipt.get("receipt_source") != "directly-observed-by-agentcaravan"
                    or not self._observed_stage(receipt)):
                raise ValueError(f"runner returned an invalid {stage_id} receipt")
            path = self._stage_path(case_id, stage_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(".json.tmp")
            temporary.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            os.replace(temporary, path)
            return {"status": "stage-completed", "stage_id": stage_id, "receipt": str(path)}
        return {"status": "stages-completed", "stage_id": ""}

    def evaluate(self, case_id: str):
        """Run the shared case pack only after all case receipts are present."""
        stages = self._stages(case_id)
        if len(stages) != len(CASE_STAGES[case_id]):
            raise ValueError("all read-only stages must complete before evaluation")
        external = self._external(case_id)
        for key in ("human_attestations", "verification_receipts"):
            if not isinstance(external.get(key), list):
                raise ValueError(f"{key} must be supplied externally")
        if case_id.endswith("accept") and (
            not isinstance(external.get("approval_receipt"), dict)
            or not isinstance(external.get("artifact_receipts"), list)
        ):
            raise ValueError("accept case needs external approval and artifact receipts")

        builder = _local_module("result_builder")
        bundle = _local_module("bundle")
        resolved = resolve_bundle(bundle.build_opencode_bundle())
        if resolved.get("status") not in {"pass", "degraded"}:
            raise ValueError("OpenCode experiment bundle did not resolve")
        scenario = next(
            item for item in json.loads((HERE / "cases.json").read_text(encoding="utf-8"))["scenarios"]
            if item["id"] == case_id
        )
        scenario = {**scenario, "task": {**scenario["task"], "task_id": self._identity(case_id)["task_id"]}}
        candidate_inputs = json.loads(
            (HERE / "inputs" / "candidate-evidence.json").read_text(encoding="utf-8")
        )

        class ReceiptSurface:
            def execute(self, request):
                return builder.build_opencode_dependency_result(
                    request, case_id=case_id,
                    stage_receipts=[stages[stage] for stage in CASE_STAGES[case_id]],
                    candidate_inputs=candidate_inputs,
                    human_attestations=external["human_attestations"],
                    approval_receipt=external.get("approval_receipt"),
                    verification_receipts=external["verification_receipts"],
                    artifact_receipts=external.get("artifact_receipts", []),
                )

        return run_opencode_conformance_suite(
            resolved, [scenario], ReceiptSurface(),
            run_id_factory=lambda _: self._identity(case_id)["run_id"],
            session_id_factory=lambda _: self._identity(case_id)["session_id"],
        )


__all__ = ["OpenCodeExperimentDriver"]
