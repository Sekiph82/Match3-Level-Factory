"""Bounded, resumable UltraGem-to-LevelDraft campaign reference workbench.

This is an authoring aid only. Donor statistics and generated drafts are not
MATCH3_ENGINE simulation, accepted campaign content, or release evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
import traceback
import uuid
from collections import Counter
from pathlib import Path
from typing import Any, Callable

import candidate_diversity
import campaign_goal_contract
import leveldraft
from factory_pipeline import ULTRAGEM_REVISION, run_pipeline
from profile_compatibility import PROFILE_IDS, diagnose_profile_compatibility

WORKBENCH_VERSION = 2
MAX_ATTEMPTS_PER_PROFILE = 100
MAX_TOTAL_ATTEMPTS = 500
MAX_RUN_WORK_UNITS = 4096
MAX_BATCH_WORK_UNITS = 512_000
MAX_ARTIFACT_BYTES = 100_000_000
MAX_CANDIDATE_JSON_BYTES = 2_000_000
MAX_TRACEBACK_CHARS = 8192
DEFAULT_NEAR_DUPLICATE_THRESHOLD = 0.95
PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SAFE_RUN_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")


class WorkbenchError(ValueError):
    """Invalid, unsafe, or tampered workbench input."""


def _json_bytes(value: Any, *, pretty: bool = False) -> bytes:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True,
                      indent=2 if pretty else None,
                      separators=None if pretty else (",", ":"),
                      allow_nan=False) + ("\n" if pretty else "")
    return text.encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _write_new(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def _write_new_or_verify(path: Path, content: bytes) -> None:
    """Adopt a byte-identical orphan after a crash without replacing it."""
    if path.exists():
        existing = path.read_bytes()
        if existing == content:
            return
        raise WorkbenchError("existing deterministic artifact differs; refusing overwrite")
    _write_new(path, content)


def _write_run_artifact(output_dir: Path, relative: str, content: bytes) -> None:
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise WorkbenchError("run artifact path is unsafe")
    root = output_dir.resolve()
    destination = (root / relative_path).resolve()
    if not destination.is_relative_to(root):
        raise WorkbenchError("run artifact resolves outside the unique output folder")
    _write_new_or_verify(destination, content)


def _atomic_replace(path: Path, content: bytes) -> None:
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".partial")
    try:
        with temporary.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(config, dict):
        raise WorkbenchError("configuration must be an object")
    required = {"profiles", "attemptsPerProfile", "seedStart", "rows", "columns",
                "colors", "runs", "maxMoves", "candidateTimeoutSeconds",
                "nearDuplicateThreshold"}
    if set(config) != required:
        raise WorkbenchError("configuration has missing or unknown fields")
    profiles = config["profiles"]
    if not isinstance(profiles, list) or not profiles or len(profiles) > len(PROFILE_IDS):
        raise WorkbenchError("profiles must contain 1..5 profile IDs")
    if any(profile not in PROFILE_IDS for profile in profiles) or len(set(profiles)) != len(profiles):
        raise WorkbenchError("profiles must be unique supported game profiles")
    bounds = {
        "attemptsPerProfile": (1, MAX_ATTEMPTS_PER_PROFILE),
        "seedStart": (0, 2**31 - 1 - (len(profiles) - 1) * 100_000 - (MAX_ATTEMPTS_PER_PROFILE - 1)),
        "rows": (6, 12), "columns": (6, 12), "colors": (3, 6),
        "runs": (1, 8), "maxMoves": (1, 40),
        "candidateTimeoutSeconds": (1, 300),
    }
    for name, (minimum, maximum) in bounds.items():
        value = config[name]
        if type(value) is not int or not minimum <= value <= maximum:
            raise WorkbenchError(f"{name} must be an integer in [{minimum}, {maximum}]")
    work_per_candidate = config["runs"] * config["maxMoves"] * 4
    total_attempts = len(profiles) * config["attemptsPerProfile"]
    if work_per_candidate > MAX_RUN_WORK_UNITS:
        raise WorkbenchError("per-candidate work exceeds the existing 4096-step pipeline budget")
    if work_per_candidate * total_attempts > MAX_BATCH_WORK_UNITS:
        raise WorkbenchError("requested batch exceeds the 512000-unit total work budget")
    threshold = config["nearDuplicateThreshold"]
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not math.isfinite(threshold) or not 0.5 <= threshold <= 1:
        raise WorkbenchError("nearDuplicateThreshold must be finite and within [0.5, 1]")
    return {
        "profiles": list(profiles), "attemptsPerProfile": config["attemptsPerProfile"],
        "seedStart": config["seedStart"], "rows": config["rows"],
        "columns": config["columns"], "colors": config["colors"],
        "runs": config["runs"], "maxMoves": config["maxMoves"],
        "candidateTimeoutSeconds": config["candidateTimeoutSeconds"],
        "nearDuplicateThreshold": float(threshold),
    }


def _checkpoint_payload(checkpoint: dict[str, Any]) -> dict[str, Any]:
    payload = dict(checkpoint)
    payload.pop("checkpointSha256", None)
    return payload


def _seal_checkpoint(checkpoint: dict[str, Any]) -> dict[str, Any]:
    checkpoint = dict(checkpoint)
    checkpoint.pop("checkpointSha256", None)
    checkpoint["checkpointSha256"] = _sha256_bytes(_json_bytes(checkpoint))
    return checkpoint


def _read_checkpoint(output_dir: Path, expected_config: dict[str, Any]) -> dict[str, Any]:
    path = output_dir / "checkpoint.json"
    try:
        checkpoint = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkbenchError(f"checkpoint missing or invalid: {exc}") from exc
    supplied_hash = checkpoint.get("checkpointSha256")
    expected_hash = _sha256_bytes(_json_bytes(_checkpoint_payload(checkpoint)))
    if supplied_hash != expected_hash:
        raise WorkbenchError("checkpoint SHA-256 validation failed")
    if checkpoint.get("configuration") != expected_config:
        raise WorkbenchError("resume configuration does not match the original run")
    if checkpoint.get("checkpointVersion") != 2:
        raise WorkbenchError("checkpoint schema is not R02; older checkpoints are read-only and are never migrated")
    if checkpoint.get("workbenchVersion") != WORKBENCH_VERSION:
        raise WorkbenchError(
            f"checkpoint belongs to workbench version {checkpoint.get('workbenchVersion')}; "
            "R01 checkpoints are read-only under R02 and are never migrated or rewritten")
    if checkpoint.get("sourceRevision") != ULTRAGEM_REVISION:
        raise WorkbenchError("checkpoint donor revision is stale")
    if not isinstance(checkpoint.get("records"), list):
        raise WorkbenchError("checkpoint records must be an array")
    for record in checkpoint["records"]:
        path_text = record.get("recordPath")
        if not isinstance(path_text, str) or Path(path_text).is_absolute() or ".." in Path(path_text).parts:
            raise WorkbenchError("checkpoint contains an unsafe artifact path")
        record_path = (output_dir / path_text).resolve()
        if not record_path.is_relative_to(output_dir.resolve()) or not record_path.is_file():
            raise WorkbenchError("checkpoint record is missing or outside the run folder")
        raw = record_path.read_bytes()
        if len(raw) > MAX_CANDIDATE_JSON_BYTES or _sha256_bytes(raw) != record.get("recordSha256"):
            raise WorkbenchError("checkpoint record SHA-256 validation failed")
        try:
            value = json.loads(raw)
            if value.get("attemptStatus") == "FAILED":
                if value.get("engineStatus") != "BLOCKED_ENG_M24" or value.get("sourceGenerated") is not False:
                    raise WorkbenchError("failed attempt record has invalid authority fields")
            else:
                draft = value["draft"]
                leveldraft.loads_strict(leveldraft.dumps_canonical(draft))
                if leveldraft.sha256(draft) != value.get("draftSha256"):
                    raise WorkbenchError("candidate record draft SHA-256 mismatch")
                if draft.get("gameProfileId") != record.get("profileId") or draft.get("seed") != record.get("donorSeed"):
                    raise WorkbenchError("candidate record provenance does not match its LevelDraft")
                diagnosis = campaign_goal_contract.diagnose_donor_goals(draft.get("goals"))
                if value.get("goalContractDiagnosis") != diagnosis:
                    raise WorkbenchError("candidate donor-goal diagnosis is forged or stale")
                if value.get("goalContractEvidence") != campaign_goal_contract.source_evidence(PROJECT_ROOT):
                    raise WorkbenchError("candidate goal-contract source evidence is stale")
                proposal_ref = value.get("localGoalProposal")
                if not isinstance(proposal_ref, dict):
                    raise WorkbenchError("candidate local-goal proposal reference is missing")
                if proposal_ref.get("status") == "CREATED":
                    proposal_path_text = proposal_ref.get("recordPath")
                    if (not isinstance(proposal_path_text, str) or Path(proposal_path_text).is_absolute()
                            or ".." in Path(proposal_path_text).parts
                            or not proposal_path_text.startswith("derived-local-goal-proposals/")):
                        raise WorkbenchError("candidate contains an unsafe local-goal proposal path")
                    proposal_path = (output_dir / proposal_path_text).resolve()
                    if not proposal_path.is_relative_to(output_dir.resolve()) or not proposal_path.is_file():
                        raise WorkbenchError("local-goal proposal is missing or outside the run folder")
                    proposal_raw = proposal_path.read_bytes()
                    if _sha256_bytes(proposal_raw) != proposal_ref.get("recordSha256"):
                        raise WorkbenchError("local-goal proposal artifact SHA-256 validation failed")
                    proposal = json.loads(proposal_raw)
                    campaign_goal_contract.validate_local_goal_proposal(
                        proposal, project_root=PROJECT_ROOT)
                    if (proposal.get("sourceDraftSha256") != record.get("draftSha256")
                            or proposal.get("sourceRecordPath") != record.get("recordPath")
                            or proposal.get("draft", {}).get("gameProfileId") != record.get("profileId")
                            or proposal_ref.get("sourceRecordPath") != record.get("recordPath")
                            or proposal_ref.get("sourceDraftSha256") != record.get("draftSha256")):
                        raise WorkbenchError("local-goal proposal source-to-derived provenance mismatch")
                    if proposal.get("authoredLocalGoalProposalSha256") != proposal_ref.get("draftSha256"):
                        raise WorkbenchError("local-goal proposal draft digest disagrees with its source record")
                elif proposal_ref.get("status") != "NOT_CREATED":
                    raise WorkbenchError("candidate proposal status is invalid")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, leveldraft.DraftError) as exc:
            raise WorkbenchError(f"checkpoint contains an invalid candidate record: {exc}") from exc
    return checkpoint


def _board_similarity(left: dict[str, Any], right: dict[str, Any]) -> tuple[float, int | None]:
    report = candidate_diversity.compare_drafts(left, right)
    changed = report["changedCellCount"]
    if changed is None:
        return 0.0, None
    count = left["width"] * left["height"] * left["layers"]
    return 1 - changed / count, changed


def _reference_observations(pipeline: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for candidate in pipeline.get("referenceStatistics", []):
        policies = candidate.get("statistics", {})
        policy_summary = {}
        for name, value in sorted(policies.items()):
            policy_summary[name] = {
                key: value.get(key) for key in
                ("runSeeds", "movesUsed", "shuffles", "outcomes") if key in value
            }
            if "steps" in value:
                policy_summary[name]["stepObservationCount"] = sum(len(run) for run in value["steps"])
                policy_summary[name]["scoreObservations"] = [
                    [step[0] for step in run if isinstance(step, list) and step]
                    for run in value["steps"]
                ]
        result.append({"seed": candidate.get("seed"), "policies": policy_summary})
    return result


def _draft_coverage(draft: dict[str, Any]) -> dict[str, Any]:
    cells = draft["cells"]
    return {
        "dimensions": {"width": draft["width"], "height": draft["height"], "layers": draft["layers"]},
        "activeCellCount": sum(bool(cell["active"]) for cell in cells),
        "holeCellCount": sum(not cell["active"] for cell in cells),
        "lockedCellCount": sum(bool(cell["active"] and (cell["locked"] or cell["lockDurability"] > 0)) for cell in cells),
        "obstacleCounts": dict(sorted(Counter(cell["obstacleId"] for cell in cells if cell["active"] and cell["obstacleId"]).items())),
        "specialCounts": dict(sorted(Counter(cell["specialId"] for cell in cells if cell["active"] and cell["specialId"]).items())),
        "goals": [{"targetId": goal["targetId"], "targetCount": goal["targetCount"]} for goal in draft["goals"]],
    }


def _run_pipeline_with_timeout(*, timeout_seconds: int, **kwargs: Any) -> dict[str, Any]:
    """Isolate one donor run so cancellation/timeout cannot strand the batch."""
    worker = Path(__file__).with_name("campaign_generation_worker.py")
    request = _json_bytes(kwargs)
    try:
        completed = subprocess.run(
            [sys.executable, str(worker)], input=request, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, cwd=str(worker.parent), timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(f"donor candidate exceeded {timeout_seconds}s timeout") from exc
    if completed.returncode != 0:
        message = completed.stderr.decode("utf-8", errors="replace")[:MAX_TRACEBACK_CHARS]
        message = message.replace(str(PROJECT_ROOT), "<PROJECT_ROOT>").replace(str(PROJECT_ROOT).replace("\\", "/"), "<PROJECT_ROOT>")
        error = WorkbenchError(f"donor worker failed ({completed.returncode}): {message[-1000:]}")
        error.diagnostic_traceback = message
        raise error
    if len(completed.stdout) > MAX_CANDIDATE_JSON_BYTES:
        raise WorkbenchError("donor worker result exceeds 2 MB")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise WorkbenchError("donor worker returned invalid JSON") from exc
    if not isinstance(result, dict):
        raise WorkbenchError("donor worker result must be an object")
    return result


def _result_summary(checkpoint: dict[str, Any], *, status: str) -> dict[str, Any]:
    records = checkpoint["records"]
    proposals = []
    for item in records:
        reference = item.get("localGoalProposal", {})
        if reference.get("status") == "CREATED":
            proposals.append({
                "profileId": item["profileId"], "candidateId": item["candidateId"],
                "attempt": item["attempt"], "donorSeed": item["donorSeed"],
                "sourceDraftSha256": item["draftSha256"],
                "sourceRecordPath": item["recordPath"],
                "sourceRecordSha256": item["recordSha256"],
                **reference,
            })
    local_authorable_unique = sum(item.get("localAuthoringStatus") == "LOCALLY_AUTHORABLE_UNIQUE_PREVIEW_ONLY"
                                  for item in proposals)

    def unresolved_goal(record: dict[str, Any]) -> bool:
        diagnosis = record.get("goalContractDiagnosis", {})
        return bool(diagnosis.get("goals")) and any(
            item.get("localEquivalence") != "ESTABLISHED" for item in diagnosis["goals"])

    by_profile = {}
    for profile in checkpoint["configuration"]["profiles"]:
        entries = [item for item in records if item["profileId"] == profile]
        by_profile[profile] = {
            "generationAttempts": len(entries),
            "sourceBackedCandidateOutputs": sum(item.get("draftSha256") is not None for item in entries),
            "generatedReferenceCandidates": sum(item["localPrefilterStatus"] == "ACCEPTED_FOR_LOCAL_AUTHORING_ONLY" for item in entries),
            "uniqueOwnerReviewCandidates": sum(item["triageStatus"] == "UNIQUE_OWNER_REVIEW_CANDIDATE" for item in entries),
            "rejectedOrDuplicate": sum(item["triageStatus"] != "UNIQUE_OWNER_REVIEW_CANDIDATE" for item in entries),
            "unresolvedGoalRejections": sum(unresolved_goal(item) for item in entries),
            "derivedLocalAuthoringProposals": sum(item.get("localGoalProposal", {}).get("status") == "CREATED" for item in entries),
            "locallyAuthorableUniqueDrafts": sum(item.get("localGoalProposal", {}).get("localAuthoringStatus") == "LOCALLY_AUTHORABLE_UNIQUE_PREVIEW_ONLY" for item in entries),
        }
    return {
        "workbenchVersion": WORKBENCH_VERSION,
        "resultStatus": status,
        "candidateStatusMeaning": "REFERENCE_ONLY; no canonical Engine playability, difficulty, WIN, or release claim",
        "sourceRepository": "JohannesBuchner/ultragem",
        "sourceRevision": checkpoint["sourceRevision"],
        "configuration": checkpoint["configuration"],
        "generationAttempts": len(records),
        "sourceBackedCandidateOutputs": sum(item.get("draftSha256") is not None for item in records),
        "donorOriginalOutputCount": sum(item.get("draftSha256") is not None for item in records),
        "unresolvedGoalRejectionCount": sum(
            item.get("draftSha256") is not None and unresolved_goal(item)
            for item in records),
        "derivedLocalAuthoringProposalCount": len(proposals),
        "locallyAuthorableUniqueDraftCount": local_authorable_unique,
        "localGoalProposals": proposals,
        "goalContractEvidence": next((item.get("goalContractEvidence") for item in records
                                       if item.get("goalContractEvidence")), []),
        "generatedReferenceCandidates": sum(x["localPrefilterStatus"] == "ACCEPTED_FOR_LOCAL_AUTHORING_ONLY" for x in records),
        "uniqueOwnerReviewCandidates": sum(x["triageStatus"] == "UNIQUE_OWNER_REVIEW_CANDIDATE" for x in records),
        "ownerApprovedCandidates": 0,
        "engineQualifiedCampaignLevels": 0,
        "engineStatus": "BLOCKED_ENG_M24",
        "profileResults": by_profile,
        "records": records,
        "structuralDiversity": {
            "sameProfileUniquenessOnly": True,
            "crossProfileCloneCandidates": sum(bool(x.get("crossProfileCloneOf")) for x in records),
            "similarityBasis": "donor-color-renaming-invariant cell structure; goal changes do not reduce board similarity",
            "nearDuplicateThreshold": checkpoint["configuration"]["nearDuplicateThreshold"],
            "limitations": ["Reference comparison is not a gameplay equivalence proof.", "The threshold can reject legitimate small board edits or miss semantically equivalent unrepresented mechanics."],
        },
        "ownerReviewRequired": True,
        "releaseAuthorized": False,
    }


def _write_summary_and_manifest(output_dir: Path, checkpoint: dict[str, Any], status: str) -> dict[str, Any]:
    _artifact_index(output_dir)
    summary = _result_summary(checkpoint, status=status)
    summary_bytes = _json_bytes(summary, pretty=True)
    _atomic_replace(output_dir / "summary.json", summary_bytes)
    manifest_items = []
    for path in sorted(p for p in output_dir.rglob("*") if p.is_file() and p.name not in {"sha256-manifest.json", "checkpoint.json", "run-metrics.json"} and not p.name.endswith(".partial")):
        relative = path.relative_to(output_dir).as_posix()
        raw = path.read_bytes()
        manifest_items.append({"path": relative, "sizeBytes": len(raw), "sha256": _sha256_bytes(raw)})
    manifest = {
        "manifestVersion": 1,
        "sourceRevision": checkpoint["sourceRevision"],
        "configuration": checkpoint["configuration"],
        "files": manifest_items,
        "generatedReferenceCandidates": summary["generatedReferenceCandidates"],
        "uniqueOwnerReviewCandidates": summary["uniqueOwnerReviewCandidates"],
        "ownerApprovedCandidates": 0,
        "engineQualifiedCampaignLevels": 0,
        "engineStatus": "BLOCKED_ENG_M24",
        "releaseAuthorized": False,
    }
    manifest_bytes = _json_bytes(manifest, pretty=True)
    _atomic_replace(output_dir / "sha256-manifest.json", manifest_bytes)
    sums = []
    for item in manifest_items:
        sums.append(f"{item['sha256']}  {item['path']}")
    sums.append(f"{_sha256_bytes(manifest_bytes)}  sha256-manifest.json")
    metrics_path = output_dir / "run-metrics.json"
    if metrics_path.exists():
        sums.append(f"{_sha256_bytes(metrics_path.read_bytes())}  run-metrics.json (timings excluded from deterministic candidate manifest)")
    _atomic_replace(output_dir / "SHA256SUMS.txt", ("\n".join(sums) + "\n").encode("utf-8"))
    return summary


def run_campaign_batch(*, config: dict[str, Any], output_dir: Path | str,
                       resume: bool = False, cancel_file: Path | str | None = None,
                       progress_callback: Callable[[dict[str, Any]], None] | None = None,
                       pipeline_runner: Callable[..., dict[str, Any]] | None = None) -> dict[str, Any]:
    """Run one seeded donor candidate per pipeline invocation and checkpoint it.

    Output folders are caller-created, unique and project-local. Existing run
    contents are read-only on resume; generated files are create-only.
    """
    config = validate_config(config)
    output_dir = Path(output_dir).resolve()
    if not output_dir.is_dir():
        raise WorkbenchError("output directory must already exist and be unique")
    if not _SAFE_RUN_NAME.fullmatch(output_dir.name):
        raise WorkbenchError("output directory must have a simple unique run name")
    cancel_path = Path(cancel_file).resolve() if cancel_file else output_dir / "CANCEL.request"
    config_path = output_dir / "run-config.json"
    checkpoint_path = output_dir / "checkpoint.json"
    if resume:
        checkpoint = _read_checkpoint(output_dir, config)
        if config_path.read_bytes() != _json_bytes({"configuration": config, "sourceRevision": ULTRAGEM_REVISION, "workbenchVersion": WORKBENCH_VERSION}, pretty=True):
            raise WorkbenchError("run configuration file changed")
        if cancel_file is None and cancel_path.exists():
            consumed_marker = output_dir / ("CANCEL.request.consumed-" + uuid.uuid4().hex)
            os.replace(cancel_path, consumed_marker)
        if cancel_file is None and cancel_path.exists():
            consumed_marker = output_dir / ("CANCEL.request.consumed-" + uuid.uuid4().hex)
            os.replace(cancel_path, consumed_marker)
    else:
        if any(path.name != "CANCEL.request" for path in output_dir.iterdir()):
            raise WorkbenchError("new run output directory must be empty")
        run_config = {"configuration": config, "sourceRevision": ULTRAGEM_REVISION, "workbenchVersion": WORKBENCH_VERSION}
        _write_new(config_path, _json_bytes(run_config, pretty=True))
        checkpoint = _seal_checkpoint({
            "checkpointVersion": 2, "workbenchVersion": WORKBENCH_VERSION,
            "sourceRevision": ULTRAGEM_REVISION, "configuration": config,
            "records": [], "attemptsCompleted": 0, "status": "IN_PROGRESS",
        })
        _write_new(checkpoint_path, _json_bytes(checkpoint, pretty=True))

    total = len(config["profiles"]) * config["attemptsPerProfile"]
    if progress_callback:
        progress_callback({"status": checkpoint["status"], "completed": len(checkpoint["records"]),
                           "total": total, "profileId": None, "attempt": 0,
                           "uniqueOwnerReviewCandidates": sum(r["triageStatus"] == "UNIQUE_OWNER_REVIEW_CANDIDATE" for r in checkpoint["records"])})

    records = list(checkpoint["records"])
    existing_by_profile = {profile: sum(r["profileId"] == profile for r in records) for profile in config["profiles"]}
    prior_drafts: dict[str, list[tuple[str, dict[str, Any]]]] = {profile: [] for profile in config["profiles"]}
    prior_local_proposals: dict[str, list[tuple[str, dict[str, Any]]]] = {profile: [] for profile in config["profiles"]}
    all_drafts: list[tuple[str, str, dict[str, Any]]] = []
    for record in records:
        raw = json.loads((output_dir / record["recordPath"]).read_text(encoding="utf-8"))
        if "draft" in raw:
            draft = raw["draft"]
            prior_drafts[record["profileId"]].append((record["candidateId"], draft))
            all_drafts.append((record["profileId"], record["candidateId"], draft))
            proposal_ref = raw.get("localGoalProposal", {})
            if proposal_ref.get("status") == "CREATED":
                proposal_raw = json.loads((output_dir / proposal_ref["recordPath"]).read_text(encoding="utf-8"))
                prior_local_proposals[record["profileId"]].append(
                    (record["candidateId"] + "/local-preview", proposal_raw["draft"]))

    metrics_path = output_dir / "run-metrics.json"
    if resume and metrics_path.exists():
        try:
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkbenchError(f"runtime measurement file is invalid: {exc}") from exc
        if not isinstance(metrics, list):
            raise WorkbenchError("runtime measurements must be an array")
        metrics = metrics[:len(records)]
        while len(metrics) < len(records):
            record = records[len(metrics)]
            metrics.append({"profileId": record["profileId"], "attempt": record["attempt"],
                            "elapsedSeconds": None, "result": "TIMING_NOT_PERSISTED_DURING_INTERRUPTION"})
        _atomic_replace(metrics_path, _json_bytes(metrics, pretty=True))
    else:
        metrics = []

    try:
        for profile_index, profile in enumerate(config["profiles"]):
            first_attempt = existing_by_profile[profile]
            for attempt_index in range(first_attempt, config["attemptsPerProfile"]):
                if cancel_path.exists():
                    checkpoint = _save_checkpoint(checkpoint_path, checkpoint, records, "CANCELLED")
                    if progress_callback:
                        progress_callback({"status": "CANCELLED", "completed": len(records), "total": total,
                                           "profileId": profile, "attempt": attempt_index,
                                           "uniqueOwnerReviewCandidates": _result_summary(checkpoint, status="CANCELLED")["uniqueOwnerReviewCandidates"]})
                    summary = _write_summary_and_manifest(output_dir, checkpoint, "CANCELLED")
                    return summary
                attempt = attempt_index + 1
                seed = config["seedStart"] + profile_index * 100_000 + attempt_index
                started = time.monotonic()
                canonical_draft = None
                draft = None
                pipeline = None
                drafts = None
                nearest = None
                prior = None
                candidate_id = None
                try:
                    run_arguments = {
                        "rows": config["rows"], "columns": config["columns"], "colors": config["colors"],
                        "seed": seed, "candidate_count": 1, "runs": config["runs"],
                        "max_moves": config["maxMoves"], "profile_id": profile, "max_levels": 1,
                    }
                    if pipeline_runner is None:
                        pipeline = _run_pipeline_with_timeout(
                            timeout_seconds=config["candidateTimeoutSeconds"], **run_arguments)
                    else:
                        pipeline = pipeline_runner(**run_arguments)
                    elapsed = time.monotonic() - started
                    drafts = pipeline.get("drafts", [])
                    if pipeline.get("resultStatus") != "REFERENCE_ONLY_UNVERIFIED" or pipeline.get("sourceRevision") != ULTRAGEM_REVISION:
                        raise WorkbenchError("pipeline did not return the pinned reference-only donor result")
                    if len(drafts) != 1:
                        raise WorkbenchError("pipeline must produce exactly one draft for this seed")
                    draft = drafts[0]["draft"]
                    leveldraft.validate(draft)
                    if draft["gameProfileId"] != profile or draft["seed"] != seed or draft["sourceRevision"] != ULTRAGEM_REVISION:
                        raise WorkbenchError("generated draft provenance does not match its request")
                    canonical = leveldraft.dumps_canonical(draft)
                    canonical_draft = leveldraft.loads_strict(canonical)
                    draft_sha = _sha256_bytes(canonical.encode("utf-8"))
                    compat = diagnose_profile_compatibility(canonical_draft)
                    candidate_id = f"{profile}/attempt-{attempt:03d}/seed-{seed}-{draft_sha[:12]}"
                    prior = prior_drafts[profile]
                    nearest = None
                    exact_fingerprint = candidate_diversity.structural_fingerprint(canonical_draft)
                    duplicate_of = None
                    for old_id, old in prior:
                        report = candidate_diversity.compare_drafts(canonical_draft, old)
                        board_similarity, changed_cells = _board_similarity(canonical_draft, old)
                        if (report["similarity"] >= config["nearDuplicateThreshold"] or
                                board_similarity >= config["nearDuplicateThreshold"]):
                            ranked = {"candidateId": old_id, "comparison": report,
                                      "boardSimilarity": round(board_similarity, 8),
                                      "changedCellCount": changed_cells}
                            if nearest is None or max(ranked["comparison"]["similarity"], board_similarity) > nearest["similarityForSelection"]:
                                ranked["similarityForSelection"] = max(report["similarity"], board_similarity)
                                nearest = ranked
                        if report["reason"] == "EXACT_STRUCTURAL_DUPLICATE":
                            duplicate_of = old_id
                            break
                    cross_profile_clone = next((old_id for old_profile, old_id, old in all_drafts
                                                if old_profile != profile and
                                                candidate_diversity.structural_fingerprint(old) == exact_fingerprint), None)
                    if duplicate_of:
                        triage_status, triage_reason = "REJECTED_DUPLICATE", "EXACT_STRUCTURAL_DUPLICATE"
                    elif nearest:
                        triage_status = "REJECTED_NEAR_DUPLICATE"
                        triage_reason = "BOARD_OR_GOAL_NEAR_DUPLICATE"
                    elif compat["localPolicyStatus"] != "ACCEPTED_FOR_LOCAL_AUTHORING_ONLY":
                        triage_status = "REJECTED_PROFILE_COMPATIBILITY"
                        triage_reason = "PROFILE_COMPATIBILITY_UNRESOLVED"
                    else:
                        triage_status, triage_reason = "UNIQUE_OWNER_REVIEW_CANDIDATE", "UNIQUE_REFERENCE_CANDIDATE"
                    relative = f"candidates/{profile}/attempt-{attempt:03d}-{draft_sha[:12]}.json"
                    goal_diagnosis = campaign_goal_contract.diagnose_donor_goals(canonical_draft["goals"])
                    goal_evidence = campaign_goal_contract.source_evidence(PROJECT_ROOT)
                    proposal = campaign_goal_contract.build_local_goal_proposal(
                        source_draft=canonical_draft,
                        source_draft_sha256=draft_sha,
                        source_record_path=relative,
                        source_repository=pipeline["sourceRepository"],
                        source_revision=pipeline["sourceRevision"],
                        source_goal_diagnosis=goal_diagnosis,
                        source_ranking_status=drafts[0]["rankingStatus"],
                        project_root=PROJECT_ROOT)
                    if proposal is None:
                        proposal_ref = {"status": "NOT_CREATED",
                                        "reasonCode": goal_diagnosis.get("reasonCode", "UNRESOLVED_DONOR_GOAL")}
                        proposal_id = None
                        proposal_draft = None
                    else:
                        proposal_draft = proposal["draft"]
                        proposal_id = candidate_id + "/local-preview"
                        proposal_nearest = None
                        proposal_duplicate = None
                        for old_id, old in prior_local_proposals[profile]:
                            compare = candidate_diversity.compare_drafts(proposal_draft, old)
                            board_similarity, changed_cells = _board_similarity(proposal_draft, old)
                            score = max(compare["similarity"], board_similarity)
                            if score >= config["nearDuplicateThreshold"] and (
                                    proposal_nearest is None or score > proposal_nearest["similarity"]):
                                proposal_nearest = {"candidateId": old_id,
                                                    "similarity": round(score, 8),
                                                    "changedCellCount": changed_cells,
                                                    "reason": compare["reason"]}
                            if compare["reason"] == "EXACT_STRUCTURAL_DUPLICATE":
                                proposal_duplicate = old_id
                                break
                        if proposal_duplicate:
                            proposal_uniqueness = "REJECTED_DUPLICATE"
                        elif proposal_nearest:
                            proposal_uniqueness = "REJECTED_NEAR_DUPLICATE"
                        else:
                            proposal_uniqueness = "UNIQUE_LOCAL_PREVIEW_STRUCTURE"
                        proposal["uniqueness"] = {
                            "status": proposal_uniqueness,
                            "duplicateOf": proposal_duplicate,
                            "nearestCandidate": proposal_nearest,
                            "threshold": config["nearDuplicateThreshold"],
                        }
                        if proposal["localAuthoringDiagnostics"]["status"] != "LOCALLY_AUTHORABLE_PREVIEW_ONLY":
                            local_authoring_status = "REJECTED_LOCAL_SAMPLE_COMPATIBILITY"
                        elif proposal_uniqueness != "UNIQUE_LOCAL_PREVIEW_STRUCTURE":
                            local_authoring_status = proposal_uniqueness
                        else:
                            local_authoring_status = "LOCALLY_AUTHORABLE_UNIQUE_PREVIEW_ONLY"
                        proposal["localAuthoringStatus"] = local_authoring_status
                        proposal_relative = (f"derived-local-goal-proposals/{profile}/"
                                             f"attempt-{attempt:03d}-{proposal['authoredLocalGoalProposalSha256'][:12]}.json")
                        proposal_raw = _json_bytes(proposal, pretty=True)
                        if len(proposal_raw) > MAX_CANDIDATE_JSON_BYTES:
                            raise WorkbenchError("derived local-goal proposal exceeds the 2 MB artifact limit")
                        _write_run_artifact(output_dir, proposal_relative, proposal_raw)
                        proposal_ref = {
                            "status": "CREATED", "recordPath": proposal_relative,
                            "recordSha256": _sha256_bytes(proposal_raw),
                            "draftSha256": proposal["authoredLocalGoalProposalSha256"],
                            "sourceRecordPath": relative,
                            "sourceDraftSha256": draft_sha,
                            "localAuthoringStatus": local_authoring_status,
                            "uniquenessStatus": proposal_uniqueness,
                        }
                    pipeline_candidate = pipeline.get("referenceStatistics", [{}])[0]
                    record_body = {
                        "recordVersion": 2,
                        "candidateId": candidate_id,
                        "profileId": profile,
                        "attempt": attempt,
                        "sourceGenerated": True,
                        "generationEvent": "PINNED_ULTRAGEM_FACTORY_PIPELINE",
                        "donorSourceRepository": pipeline["sourceRepository"],
                        "donorRevision": pipeline["sourceRevision"],
                        "donorSeed": seed,
                        "pipelineSeed": pipeline["seed"],
                        "configuration": pipeline["configuration"],
                        "referenceRankingStatus": drafts[0]["rankingStatus"],
                        "referenceDifficultyHypothesis": drafts[0]["difficultyHypothesis"],
                        "goalContractDiagnosis": goal_diagnosis,
                        "goalContractEvidence": goal_evidence,
                        "goalContractStatus": goal_diagnosis["status"],
                        "sourceGoalSummary": " | ".join(
                            f"{item.get('sourceTargetId')} [{item.get('status')}]"
                            for item in goal_diagnosis["goals"]),
                        "localGoalProposal": proposal_ref,
                        "referenceStatistics": _reference_observations({"referenceStatistics": [pipeline_candidate]}),
                        "draftSha256": draft_sha,
                        "structuralFingerprint": exact_fingerprint,
                        "profileCompatibility": compat,
                        "coverage": _draft_coverage(canonical_draft),
                        "localPrefilterStatus": compat["localPolicyStatus"],
                        "triageStatus": triage_status,
                        "triageReason": triage_reason,
                        "duplicateOf": duplicate_of,
                        "nearestCandidate": nearest,
                        "crossProfileCloneOf": cross_profile_clone,
                        "engineStatus": "BLOCKED_ENG_M24",
                        "engineQualified": False,
                        "ownerApproved": False,
                        "draft": canonical_draft,
                    }
                    raw = _json_bytes(record_body, pretty=True)
                    if len(raw) > MAX_CANDIDATE_JSON_BYTES:
                        raise WorkbenchError("candidate record exceeds the 2 MB artifact limit")
                    _write_run_artifact(output_dir, relative, raw)
                    public_record = {
                        "candidateId": candidate_id, "profileId": profile, "attempt": attempt,
                        "donorSeed": seed, "recordPath": relative, "recordSha256": _sha256_bytes(raw),
                        "draftSha256": draft_sha, "structuralFingerprint": exact_fingerprint,
                        "localPrefilterStatus": compat["localPolicyStatus"],
                        "triageStatus": triage_status, "triageReason": triage_reason,
                        "goalContractDiagnosis": goal_diagnosis,
                        "goalContractEvidence": goal_evidence,
                        "goalContractStatus": goal_diagnosis["status"],
                        "sourceGoalSummary": record_body["sourceGoalSummary"],
                        "donorRevision": pipeline["sourceRevision"],
                        "donorSourceRepository": pipeline["sourceRepository"],
                        "localGoalProposal": proposal_ref,
                        "localAuthoringStatus": proposal_ref.get("localAuthoringStatus", "NOT_CREATED"),
                        "duplicateOf": duplicate_of, "crossProfileCloneOf": cross_profile_clone,
                    }
                    if proposal_draft is not None:
                        prior_local_proposals[profile].append((proposal_id, proposal_draft))
                except Exception as exc:
                    elapsed = time.monotonic() - started
                    diagnostic_traceback = getattr(exc, "diagnostic_traceback", "")
                    if not diagnostic_traceback:
                        diagnostic_traceback = traceback.format_exc(limit=32)[-MAX_TRACEBACK_CHARS:]
                        diagnostic_traceback = diagnostic_traceback.replace(str(PROJECT_ROOT), "<PROJECT_ROOT>").replace(str(PROJECT_ROOT).replace("\\", "/"), "<PROJECT_ROOT>")
                    failure = {
                        "recordVersion": 1, "profileId": profile, "attempt": attempt,
                        "donorSeed": seed, "sourceGenerated": False,
                        "attemptStatus": "FAILED", "reasonCode": type(exc).__name__,
                        "error": str(exc)[:1000],
                        "diagnosticTraceback": diagnostic_traceback,
                        "engineStatus": "BLOCKED_ENG_M24",
                    }
                    relative = f"failures/{profile}/attempt-{attempt:03d}-seed-{seed}.json"
                    raw = _json_bytes(failure, pretty=True)
                    _write_run_artifact(output_dir, relative, raw)
                    public_record = {
                        "candidateId": f"{profile}/attempt-{attempt:03d}/seed-{seed}/FAILED",
                        "profileId": profile, "attempt": attempt, "donorSeed": seed,
                        "recordPath": relative, "recordSha256": _sha256_bytes(raw),
                        "draftSha256": None, "structuralFingerprint": None,
                        "localPrefilterStatus": "NOT_RUN", "triageStatus": "FAILED",
                        "triageReason": str(exc)[:500], "duplicateOf": None,
                        "crossProfileCloneOf": None,
                    }
                records.append(public_record)
                metrics.append({"profileId": profile, "attempt": attempt,
                                "elapsedSeconds": round(elapsed, 6),
                                "result": public_record["triageStatus"]})
                _atomic_replace(metrics_path, _json_bytes(metrics, pretty=True))
                if canonical_draft is not None and public_record.get("draftSha256"):
                    prior_drafts[profile].append((public_record["candidateId"], canonical_draft))
                    all_drafts.append((profile, public_record["candidateId"], canonical_draft))
                if sum(item["sizeBytes"] for item in _artifact_index(output_dir)) > MAX_ARTIFACT_BYTES:
                    raise WorkbenchError("run output exceeds the 100 MB artifact ceiling")
                checkpoint = _save_checkpoint(checkpoint_path, checkpoint, records, "IN_PROGRESS")
                progress = {"status": "IN_PROGRESS", "completed": len(records), "total": total,
                            "profileId": profile, "attempt": attempt,
                            "uniqueOwnerReviewCandidates": sum(r["triageStatus"] == "UNIQUE_OWNER_REVIEW_CANDIDATE" for r in records)}
                if progress_callback:
                    progress_callback(progress)
    except KeyboardInterrupt:
        checkpoint = _save_checkpoint(checkpoint_path, checkpoint, records, "CANCELLED")
        if progress_callback:
            progress_callback({"status": "CANCELLED", "completed": len(records), "total": total,
                               "profileId": None, "attempt": 0,
                               "uniqueOwnerReviewCandidates": _result_summary(checkpoint, status="CANCELLED")["uniqueOwnerReviewCandidates"]})
        return _write_summary_and_manifest(output_dir, checkpoint, "CANCELLED")

    checkpoint = _save_checkpoint(checkpoint_path, checkpoint, records, "COMPLETED")
    if progress_callback:
        progress_callback({"status": "COMPLETED", "completed": len(records), "total": total,
                           "profileId": None, "attempt": 0,
                           "uniqueOwnerReviewCandidates": _result_summary(checkpoint, status="COMPLETED")["uniqueOwnerReviewCandidates"]})
    return _write_summary_and_manifest(output_dir, checkpoint, "COMPLETED")


def _artifact_index(output_dir: Path) -> list[dict[str, Any]]:
    root = output_dir.resolve()
    result = []
    for path in output_dir.rglob("*"):
        if path.is_symlink():
            raise WorkbenchError("run output cannot contain symlinked artifacts")
        if path.is_file() and not path.name.endswith(".partial"):
            if not path.resolve().is_relative_to(root):
                raise WorkbenchError("run output artifact resolves outside the unique output folder")
            result.append({"sizeBytes": path.stat().st_size})
    return result


def _save_checkpoint(path: Path, checkpoint: dict[str, Any], records: list[dict[str, Any]], status: str) -> dict[str, Any]:
    updated = dict(checkpoint)
    updated.update({"records": records, "attemptsCompleted": len(records), "status": status})
    updated = _seal_checkpoint(updated)
    _atomic_replace(path, _json_bytes(updated, pretty=True))
    return updated


def _resolve_output(project_root: Path, relative: str) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts or not _SAFE_RUN_NAME.fullmatch(raw.name):
        raise WorkbenchError("output must be a project-relative unique folder without traversal")
    root = project_root.resolve()
    destination = (root / raw).resolve()
    if not destination.is_relative_to(root):
        raise WorkbenchError("output resolves outside the project root")
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--profiles", default=",".join(PROFILE_IDS))
    parser.add_argument("--attempts-per-profile", type=int, default=5)
    parser.add_argument("--seed-start", type=int, default=1000)
    parser.add_argument("--rows", type=int, default=8)
    parser.add_argument("--columns", type=int, default=8)
    parser.add_argument("--colors", type=int, default=3)
    parser.add_argument("--runs", type=int, default=2)
    parser.add_argument("--max-moves", type=int, default=8)
    parser.add_argument("--candidate-timeout-seconds", type=int, default=30)
    parser.add_argument("--near-duplicate-threshold", type=float, default=DEFAULT_NEAR_DUPLICATE_THRESHOLD)
    parser.add_argument("--output-relative", required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    try:
        config = validate_config({
            "profiles": [part for part in args.profiles.split(",") if part],
            "attemptsPerProfile": args.attempts_per_profile, "seedStart": args.seed_start,
            "rows": args.rows, "columns": args.columns, "colors": args.colors,
            "runs": args.runs, "maxMoves": args.max_moves,
            "candidateTimeoutSeconds": args.candidate_timeout_seconds,
            "nearDuplicateThreshold": args.near_duplicate_threshold,
        })
        output_dir = _resolve_output(args.project_root, args.output_relative)
        if args.resume:
            if not output_dir.is_dir():
                raise WorkbenchError("resume output folder does not exist")
        else:
            output_dir.mkdir(parents=True, exist_ok=True)
        summary = run_campaign_batch(
            config=config, output_dir=output_dir, resume=args.resume,
            progress_callback=lambda value: _atomic_replace(output_dir / "progress.json", _json_bytes(value, pretty=True)),
        )
        sys.stdout.write(json.dumps({"resultStatus": summary["resultStatus"], "outputRelative": output_dir.relative_to(args.project_root.resolve()).as_posix(),
                                     "generationAttempts": summary["generationAttempts"],
                                     "sourceBackedCandidateOutputs": summary["sourceBackedCandidateOutputs"],
                                     "generatedReferenceCandidates": summary["generatedReferenceCandidates"],
                                     "uniqueOwnerReviewCandidates": summary["uniqueOwnerReviewCandidates"],
                                     "engineQualifiedCampaignLevels": 0, "engineStatus": "BLOCKED_ENG_M24"}, separators=(",", ":")) + "\n")
        return 0
    except (WorkbenchError, OSError, ValueError) as exc:
        sys.stderr.write(f"workbench_error: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
