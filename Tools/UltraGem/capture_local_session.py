"""Capture one bounded Factory-local authoring session without assuming ledger shape."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import factory_local_authoring as authoring
from profile_compatibility import PROFILE_IDS


def summarize_ledger(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Return stable labels for status rows and event-only rows alike."""
    if not isinstance(entries, list):
        raise TypeError("ledger entries must be a list")
    labels: list[str] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise TypeError(f"ledger entry {index} must be an object")
        label = entry.get("status") or entry.get("event") or "UNCLASSIFIED"
        labels.append(str(label))
    return {"entryCount": len(entries), "labels": labels}


def _write_new(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write((json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def capture_cancel_resume(project_root: Path, output_relative: str, profile_id: str,
                         seed_start: int) -> dict[str, Any]:
    """Run two local previews, cancel after the first, resume, and persist a ledger."""
    if profile_id not in PROFILE_IDS:
        raise ValueError("unsupported game profile")
    root = project_root.resolve(strict=True)
    run = root / output_relative
    authoring.start_run(root, output_relative, [profile_id], attempts_per_profile=2,
                        seed_start=seed_start, width=6, height=6, colors=3)
    ledger: list[dict[str, Any]] = []
    requested = False

    def cancel_after_first(progress: dict[str, Any]) -> None:
        nonlocal requested
        if progress["completed"] == 1 and not requested:
            requested = True
            authoring.request_cancel(run)
            ledger.append({"event": "CANCEL_REQUESTED", "completed": 1})

    started = time.monotonic()
    cancelled = authoring.run_session(root, output_relative, progress_callback=cancel_after_first)
    ledger.append({"status": cancelled["status"], "candidateCount": len(cancelled["records"])})
    if cancelled["status"] != "CANCELLED" or len(cancelled["records"]) != 1:
        raise RuntimeError("capture did not stop at the expected durable cancel boundary")
    completed = authoring.run_session(root, output_relative, resume=True)
    ledger.append({"status": completed["status"], "candidateCount": len(completed["records"])})
    if completed["status"] != "COMPLETED" or len(completed["records"]) != 2:
        raise RuntimeError("capture did not resume to the configured candidate count")

    result = {
        "result": "CAPTURED_LOCAL_SAMPLE_ONLY",
        "profileId": profile_id,
        "seedStart": seed_start,
        "status": completed["status"],
        "candidateCount": len(completed["records"]),
        "elapsedSeconds": round(time.monotonic() - started, 6),
        "ledgerSummary": summarize_ledger(ledger),
        "ledger": ledger,
        "engineStatus": "BLOCKED_ENG_M24",
        "engineQualifiedCampaignLevels": 0,
    }
    _write_new(run / "capture-ledger.json", {"entries": ledger})
    _write_new(run / "capture-result.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-relative", required=True)
    parser.add_argument("--profile", choices=PROFILE_IDS, required=True)
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        result = capture_cancel_resume(args.project_root, args.output_relative, args.profile, args.seed)
        sys.stdout.write(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n")
        return 0
    except (OSError, ValueError, RuntimeError, TypeError) as exc:
        sys.stderr.write(f"capture_error: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
