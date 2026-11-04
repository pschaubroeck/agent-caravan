"""Run the live Codex dependency-wait pilot and retain scoped evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from codex_stage_runner import CodexStageRunner
from controller import build_verification_record, run_scenario
from agentcaravan.schema_validation import validate_artifact


ROOT = Path(__file__).resolve().parents[4]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--workspace", type=Path, default=Path("/private/tmp/agentcaravan-scheduling-pilot"))
    parser.add_argument("--model", default="gpt-6.1-sol")
    parser.add_argument("--executable", default="codex")
    args = parser.parse_args()

    output_dir = args.evidence_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    timeline_path = output_dir / "codex-live-timeline.json"
    record_path = output_dir / "codex-live-verification-record.json"
    if timeline_path.exists() or record_path.exists():
        raise SystemExit(f"refusing to overwrite evidence in {output_dir}")

    token = uuid4().hex
    task_id = f"dependency-wait-{token}"
    run_id = f"codex-parallel-scheduling-{token}"
    runner = CodexStageRunner(
        cwd=args.workspace,
        model=args.model,
        executable=args.executable,
    )
    timeline = run_scenario(runner, task_id=task_id, run_id=run_id)
    runtime_version = timeline["stage_receipts"][0]["version"]
    timeline_path.write_text(
        json.dumps(timeline, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    timeline_digest = hashlib.sha256(timeline_path.read_bytes()).hexdigest()
    evidence_ref = f"repo://{timeline_path.relative_to(ROOT)}#sha256={timeline_digest}"
    record = build_verification_record(
        timeline,
        model=args.model,
        runtime_version=runtime_version,
        evidence_ref=evidence_ref,
        recorded_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    validate_artifact(record, ROOT / "resources/schemas/runtime-verification-record.schema.json")
    status = record["result"]["status"]
    record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "result": status,
        "scenario_id": record["scenario"]["id"],
        "runtime_version": runtime_version,
        "timeline_path": str(timeline_path),
        "record_path": str(record_path),
        "scheduling_conformance": timeline["scheduling_conformance"],
    }, indent=2))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
