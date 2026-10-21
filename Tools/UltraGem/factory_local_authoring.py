"""Bounded original Factory-local LevelDraft authoring for sample-preview use.

This generator does not consume or transform UltraGem boards. Outputs are
strictly local previews; they are not Engine-simulated or campaign-qualified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import os
import time
from pathlib import Path
from typing import Any

import candidate_diversity
import leveldraft
from profile_compatibility import PROFILE_IDS, diagnose_profile_compatibility

SOURCE_KIND = "FactoryOriginalLocalSampleBoard"
SOURCE_REVISION = "LFX-M11-R04-local-authoring-v2"
PALETTE = ("Blue", "Green", "Orange", "Purple", "White", "Yellow")
MAX_BATCH = 50
MAX_ATTEMPTS_PER_PROFILE = 10
RUN_SCHEMA_VERSION = 1


def _json_bytes(value: Any, *, pretty: bool = False) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                        indent=2 if pretty else None, separators=None if pretty else (",", ":")) + "\n").encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _atomic_create(path: Path, data: bytes) -> None:
    """Create a new file with a same-directory temporary and atomic rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    if path.exists() or partial.exists():
        raise FileExistsError(f"refusing to overwrite existing run artifact: {path.name}")
    try:
        with partial.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.rename(partial, path)
    except Exception:
        # A partial is intentionally retained after an interrupted write for
        # fail-closed inspection; never silently remove uncertain bytes.
        raise


def _atomic_replace(path: Path, data: bytes) -> None:
    partial = path.with_name(path.name + ".partial")
    # A previous interrupted/failed replacement is forensic evidence. Never
    # truncate it on a later retry; callers must inspect the partial explicitly.
    with partial.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    for attempt in range(5):
        try:
            os.replace(partial, path)
            return
        except PermissionError as exc:
            # Windows scanners/indexers can briefly hold a just-written file.
            # Retry only the documented transient access/sharing errors; never
            # fall back to a non-atomic write or delete an uncertain artifact.
            if os.name != "nt" or getattr(exc, "winerror", None) not in (5, 32) or attempt == 4:
                raise
            time.sleep(0.05 * (attempt + 1))


def _seal(checkpoint: dict[str, Any]) -> dict[str, Any]:
    body = dict(checkpoint)
    body.pop("checkpointSha256", None)
    body["checkpointSha256"] = _sha(_json_bytes(body))
    return body


def _event_hash(previous: str, sequence: int, event: str, data: dict[str, Any]) -> str:
    return _sha(_json_bytes({"previous": previous, "sequence": sequence,
                             "event": event, "data": data}))


def _validate_run_path(project_root: Path, run_dir: Path) -> tuple[Path, Path]:
    root = project_root.resolve(strict=True)
    raw_candidate = run_dir.absolute()
    if raw_candidate.is_symlink() or any(parent.is_symlink() for parent in raw_candidate.parents if parent != root.parent):
        raise ValueError("symlinked run paths are not accepted")
    candidate = raw_candidate.resolve(strict=True)
    if candidate == root or not candidate.is_relative_to(root):
        raise ValueError("run folder must be a child of the project root")
    return root, candidate


def start_run(project_root: Path, run_relative: str, profiles: list[str], *,
              attempts_per_profile: int, seed_start: int, width: int = 8,
              height: int = 8, colors: int = 4,
              near_duplicate_threshold: float = .95) -> dict[str, Any]:
    """Initialize an immutable, project-local checkpointed authoring run."""
    relative = Path(run_relative)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError("run path must be a safe project-relative path")
    root = project_root.resolve(strict=True)
    run_dir = root / relative
    config = {"profiles": profiles, "attemptsPerProfile": attempts_per_profile,
              "seedStart": seed_start, "width": width, "height": height,
              "colors": colors, "nearDuplicateThreshold": near_duplicate_threshold}
    # Validate all requested work before making any output directory.
    build_batch(profiles, attempts_per_profile=attempts_per_profile,
                seed_start=seed_start, width=width, height=height, colors=colors,
                near_duplicate_threshold=near_duplicate_threshold)
    if type(seed_start) is not int or seed_start < 0 or seed_start > 2**63 - 1 - 400_000:
        raise ValueError("seed_start is outside the safe deterministic range")
    prospective_parent = run_dir.parent
    if prospective_parent.exists():
        resolved_parent = prospective_parent.resolve(strict=True)
        if not resolved_parent.is_relative_to(root) or any(p.is_symlink() for p in prospective_parent.parents if p != root.parent):
            raise ValueError("run parent resolves outside the project or through a symlink")
    run_dir.parent.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(exist_ok=False)
    try:
        # Re-resolve after creation to reject a raced-in symlink or path swap.
        root, run_dir = _validate_run_path(root, run_dir)
        checkpoint = _seal({"runSchemaVersion": RUN_SCHEMA_VERSION,
                            "sourceRevision": SOURCE_REVISION,
                            "authoringAlgorithm": SOURCE_REVISION,
                            "configuration": config,
                            "configurationSha256": _sha(_json_bytes(config)),
                            "status": "READY", "records": [], "events": [],
                            "eventHead": "0" * 64, "createdUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        _atomic_create(run_dir / "checkpoint.json", _json_bytes(checkpoint, pretty=True))
        _atomic_create(run_dir / "run-config.json", _json_bytes({"configuration": config,
                      "configurationSha256": checkpoint["configurationSha256"],
                      "sourceRevision": SOURCE_REVISION}, pretty=True))
        return checkpoint
    except Exception:
        # Preserve a partially initialized directory for forensic recovery.
        raise


def request_cancel(run_dir: Path) -> None:
    """Durably request cancellation of an active or not-yet-started run."""
    marker = run_dir / "cancel.request"
    _atomic_create(marker, b"cancel\n")


def _read_run_checkpoint(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "checkpoint.json"
    if not path.is_file() or path.is_symlink():
        raise ValueError("checkpoint is missing or unsafe")
    try:
        checkpoint = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"checkpoint JSON is invalid: {exc}") from exc
    if checkpoint.get("checkpointSha256") != _seal(checkpoint).get("checkpointSha256"):
        raise ValueError("checkpoint SHA-256 validation failed")
    if checkpoint.get("runSchemaVersion") != RUN_SCHEMA_VERSION:
        raise ValueError("unsupported run checkpoint version")
    if checkpoint.get("sourceRevision") != SOURCE_REVISION or checkpoint.get("authoringAlgorithm") != SOURCE_REVISION:
        raise ValueError("stale source or authoring algorithm revision")
    config = checkpoint.get("configuration")
    if not isinstance(config, dict) or checkpoint.get("configurationSha256") != _sha(_json_bytes(config)):
        raise ValueError("configuration hash validation failed")
    try:
        build_batch(config["profiles"], attempts_per_profile=config["attemptsPerProfile"],
                    seed_start=config["seedStart"], width=config["width"],
                    height=config["height"], colors=config["colors"],
                    near_duplicate_threshold=config["nearDuplicateThreshold"])
    except (KeyError, TypeError, ValueError, RuntimeError) as exc:
        raise ValueError(f"checkpoint configuration is invalid: {exc}") from exc
    config_path = run_dir / "run-config.json"
    if config_path.is_symlink() or not config_path.is_file():
        raise ValueError("run configuration is missing or unsafe")
    try:
        persisted_config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("run configuration JSON is invalid") from exc
    if (persisted_config.get("configuration") != config or
            persisted_config.get("configurationSha256") != checkpoint["configurationSha256"] or
            persisted_config.get("sourceRevision") != SOURCE_REVISION):
        raise ValueError("persisted run configuration does not match checkpoint source/configuration")
    events = checkpoint.get("events")
    if not isinstance(events, list) or len(events) != len(checkpoint.get("records", [])):
        raise ValueError("event sequence does not match saved candidate records")
    previous = "0" * 64
    for index, event in enumerate(events):
        if not isinstance(event, dict) or event.get("event") not in {"CANDIDATE_COMMITTED", "CANDIDATE_RECOVERED"}:
            raise ValueError("event sequence contains an unknown event")
        if event.get("sequence") != index + 1 or event.get("previousEventSha256") != previous:
            raise ValueError("event sequence or chain is invalid")
        expected = _event_hash(previous, event["sequence"], event["event"], event["data"])
        if event.get("eventSha256") != expected:
            raise ValueError("event chain SHA-256 validation failed")
        record = checkpoint["records"][index]
        event_data = event.get("data")
        if (not isinstance(event_data, dict) or event_data.get("path") != record.get("path") or
                event_data.get("rawSha256") != record.get("rawSha256") or
                event_data.get("draftSha256") != record.get("draftSha256")):
            raise ValueError("event does not authenticate the corresponding saved record")
        previous = expected
    if checkpoint.get("eventHead") != previous:
        raise ValueError("event chain head does not match")
    return checkpoint


def _load_saved_drafts(run_dir: Path, checkpoint: dict[str, Any], *, allow_orphan: bool = False) -> list[dict[str, Any]]:
    records = checkpoint.get("records")
    if not isinstance(records, list) or len(records) > MAX_BATCH:
        raise ValueError("checkpoint record count is invalid")
    loaded = []
    known_paths = {"checkpoint.json", "run-config.json", "manifest.json", "summary.json", "progress.json", "cancel.request"}
    for record in records:
        rel = Path(record.get("path", ""))
        if rel.is_absolute() or ".." in rel.parts or rel.suffix != ".json":
            raise ValueError("checkpoint contains unsafe artifact path")
        path = run_dir / rel
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(run_dir.resolve()):
            raise ValueError("checkpoint artifact is missing or outside the run folder")
        raw = path.read_bytes()
        if _sha(raw) != record.get("rawSha256"):
            raise ValueError("saved candidate raw file hash differs from checkpoint")
        draft = leveldraft.loads_strict(raw.decode("utf-8"))
        leveldraft.validate(draft)
        if leveldraft.sha256(draft) != record.get("draftSha256") or draft.get("gameProfileId") != record.get("profileId") or draft.get("seed") != record.get("seed"):
            raise ValueError("saved draft canonical SHA, profile or seed does not match checkpoint")
        known_paths.add(rel.as_posix())
        loaded.append({"record": record, "draft": draft})
    config = checkpoint["configuration"]
    for index, saved in enumerate(loaded):
        expected = _candidate_for_index(config, index, loaded[:index])
        if (saved["record"].get("path") != expected["record"]["path"] or
                saved["record"].get("candidateId") != expected["record"]["candidateId"] or
                saved["record"].get("status") != expected["record"]["status"] or
                saved["record"].get("draftSha256") != expected["record"]["draftSha256"] or
                leveldraft.dumps_canonical(saved["draft"]) != leveldraft.dumps_canonical(expected["draft"])):
            raise ValueError("saved candidate differs from deterministic source/configuration recomputation")
    for path in run_dir.rglob("*"):
        if path.is_symlink():
            raise ValueError("symlink found inside local run")
        if path.is_file():
            rel = path.relative_to(run_dir).as_posix()
            if rel.endswith(".partial"):
                raise ValueError("partial artifact detected; recovery fails closed")
            if rel not in known_paths and not (allow_orphan and rel.startswith("drafts/") and rel.endswith(".json")):
                raise ValueError(f"unexpected file in run folder: {rel}")
    return loaded


def _candidate_for_index(config: dict[str, Any], index: int,
                         prior: list[dict[str, Any]]) -> dict[str, Any]:
    per_profile = config["attemptsPerProfile"]
    profile_index, attempt_zero = divmod(index, per_profile)
    profile = config["profiles"][profile_index]
    seed = config["seedStart"] + profile_index * 100_000 + attempt_zero
    draft = create_draft(profile, seed, width=config["width"], height=config["height"], colors=config["colors"])
    fingerprint = candidate_diversity.structural_fingerprint(draft)
    same_profile = [item for item in prior if item["record"]["profileId"] == profile]
    nearest = max(((item["record"]["candidateId"], candidate_diversity.compare_drafts(draft, item["draft"]))
                   for item in same_profile), key=lambda item: item[1]["similarity"], default=None)
    clone = next((item["record"]["candidateId"] for item in prior
                  if candidate_diversity.structural_fingerprint(item["draft"]) == fingerprint), None)
    status = "LOCAL_SAMPLE_COMPATIBLE_PREVIEW_ONLY"
    if nearest and nearest[1]["similarity"] >= config["nearDuplicateThreshold"]:
        status = "REJECTED_NEAR_DUPLICATE"
    elif clone:
        status = "REJECTED_CROSS_PROFILE_CLONE"
    draft_sha = leveldraft.sha256(draft)
    candidate_id = f"{profile}/local-{attempt_zero + 1:02d}/seed-{seed}-{draft_sha[:12]}"
    filename = f"attempt-{attempt_zero + 1:02d}.json"
    rel = (Path("drafts") / profile / filename).as_posix()
    record = {"candidateId": candidate_id, "profileId": profile, "attempt": attempt_zero + 1,
              "seed": seed, "path": rel, "sourceKind": SOURCE_KIND,
              "sourceRevision": SOURCE_REVISION, "draftSha256": draft_sha,
              "status": status, "engineStatus": "BLOCKED_ENG_M24",
              "engineQualified": False, "ownerReviewed": False, "ownerApproved": False,
              "nearDuplicateOf": nearest[0] if nearest and nearest[1]["similarity"] >= config["nearDuplicateThreshold"] else None,
              "crossProfileCloneOf": clone}
    return {"record": record, "draft": draft}


def _save_checkpoint(run_dir: Path, checkpoint: dict[str, Any]) -> dict[str, Any]:
    sealed = _seal(checkpoint)
    _atomic_replace(run_dir / "checkpoint.json", _json_bytes(sealed, pretty=True))
    entries = [{"path": r["path"], "profileId": r["profileId"], "seed": r["seed"],
                "draftSha256": r["draftSha256"], "rawSha256": r["rawSha256"]}
               for r in sealed["records"]]
    _atomic_replace(run_dir / "manifest.json", _json_bytes({"sourceKind": SOURCE_KIND,
                  "sourceRevision": SOURCE_REVISION, "configurationSha256": sealed["configurationSha256"],
                  "entries": entries}, pretty=True))
    profile_results = {profile: {"attempts": sum(r["profileId"] == profile for r in sealed["records"]),
                                 "uniqueLocal": sum(r["profileId"] == profile and r["status"] == "LOCAL_SAMPLE_COMPATIBLE_PREVIEW_ONLY"
                                                    for r in sealed["records"])}
                       for profile in sealed["configuration"]["profiles"]}
    summary = {"resultStatus": sealed["status"], "sourceKind": SOURCE_KIND,
               "sourceRevision": SOURCE_REVISION,
               "generationAttempts": len(sealed["records"]), "localDraftCount": len(sealed["records"]),
               "locallyCompatibleUniqueCount": sum(r["status"] == "LOCAL_SAMPLE_COMPATIBLE_PREVIEW_ONLY" for r in sealed["records"]),
               "engineQualifiedCampaignLevels": 0, "engineStatus": "BLOCKED_ENG_M24",
               "ownerReviewed": 0, "ownerApproved": 0, "profileResults": profile_results,
               "records": [{"candidateId": r["candidateId"], "profileId": r["profileId"],
                            "attempt": r["attempt"], "seed": r["seed"], "draftSha256": r["draftSha256"],
                            "status": r["status"], "recordPath": r["path"], "recordSha256": r["rawSha256"]}
                           for r in sealed["records"]]}
    _atomic_replace(run_dir / "summary.json", _json_bytes(summary, pretty=True))
    return sealed


def _expected_manifest(checkpoint: dict[str, Any]) -> dict[str, Any]:
    return {"sourceKind": SOURCE_KIND, "sourceRevision": SOURCE_REVISION,
            "configurationSha256": checkpoint["configurationSha256"],
            "entries": [{"path": r["path"], "profileId": r["profileId"], "seed": r["seed"],
                         "draftSha256": r["draftSha256"], "rawSha256": r["rawSha256"]}
                        for r in checkpoint["records"]]}


def _recover_checkpoint_manifest_gap(run_dir: Path, checkpoint: dict[str, Any],
                                     actual_manifest: Any) -> bool:
    """Repair exactly one checkpoint-ahead manifest after a process crash.

    The saved candidate was already recomputed and byte/hash-validated by
    _load_saved_drafts. Recovery is allowed only when the persisted manifest
    exactly equals the checkpoint's records with its last record removed and
    the final hash-chained event is a normal commit or orphan recovery.
    """
    records = checkpoint.get("records")
    events = checkpoint.get("events")
    if not isinstance(records, list) or not isinstance(events, list) or len(records) == 0 or len(events) != len(records):
        return False
    last_event = events[-1]
    if not isinstance(last_event, dict) or last_event.get("event") not in {"CANDIDATE_COMMITTED", "CANDIDATE_RECOVERED"}:
        return False
    previous = dict(checkpoint)
    previous["records"] = records[:-1]
    previous["events"] = events[:-1]
    expected_previous_head = events[-2]["eventSha256"] if len(events) > 1 else "0" * 64
    if checkpoint.get("eventHead") != last_event.get("eventSha256") or last_event.get("previousEventSha256") != expected_previous_head:
        return False
    previous["eventHead"] = expected_previous_head
    if actual_manifest != _expected_manifest(previous):
        return False
    _atomic_replace(run_dir / "manifest.json", _json_bytes(_expected_manifest(checkpoint), pretty=True))
    return True


def run_session(project_root: Path, run_relative: str, *, resume: bool = False,
                progress_callback=None, max_new_candidates: int | None = None,
                crash_after_artifact: bool = False) -> dict[str, Any]:
    """Run or resume a deterministic batch; output files are create-only."""
    relative = Path(run_relative)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError("run path must be a safe project-relative path")
    root = project_root.resolve(strict=True)
    run_dir = root / relative
    root, run_dir = _validate_run_path(root, run_dir)
    checkpoint = _read_run_checkpoint(run_dir)
    if not resume and checkpoint["status"] not in ("READY", "CANCELLED"):
        raise ValueError("run already started; use resume=True")
    saved = _load_saved_drafts(run_dir, checkpoint, allow_orphan=True)
    config = checkpoint["configuration"]
    total = len(config["profiles"]) * config["attemptsPerProfile"]
    if len(saved) > total:
        raise ValueError("checkpoint exceeds configured batch size")
    manifest_path = run_dir / "manifest.json"
    if manifest_path.exists():
        expected_manifest = _expected_manifest(checkpoint)
        try:
            actual_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("manifest JSON is invalid") from exc
        if actual_manifest != expected_manifest and not _recover_checkpoint_manifest_gap(run_dir, checkpoint, actual_manifest):
            raise ValueError("manifest does not match checkpoint records")
    elif checkpoint["status"] != "READY" or checkpoint["records"]:
        raise ValueError("run manifest is missing")
    marker = run_dir / "cancel.request"
    if resume and marker.exists():
        marker.unlink()
    # One exact orphan may be adopted after the known artifact-before-checkpoint crash boundary.
    expected_next = _candidate_for_index(config, len(saved), saved) if len(saved) < total else None
    known = {r["record"]["path"] for r in saved}
    orphan_files = [p for p in run_dir.rglob("*.json") if p.is_file() and
                    p.name not in {"checkpoint.json", "run-config.json", "manifest.json", "summary.json", "progress.json"} and
                    p.relative_to(run_dir).as_posix() not in known]
    if orphan_files:
        if len(orphan_files) != 1 or expected_next is None or orphan_files[0].relative_to(run_dir).as_posix() != expected_next["record"]["path"]:
            raise ValueError("unexpected or multiple orphan files; recovery fails closed")
        raw = orphan_files[0].read_bytes()
        expected_raw = _json_bytes(expected_next["draft"], pretty=True)
        if raw != expected_raw:
            raise ValueError("orphan bytes do not match deterministic recomputation")
        if _sha(leveldraft.dumps_canonical(expected_next["draft"]).encode("utf-8")) != expected_next["record"]["draftSha256"]:
            raise ValueError("orphan recomputation provenance does not match")
        expected_next["record"]["rawSha256"] = _sha(raw)
        saved.append(expected_next)
        checkpoint["records"].append(expected_next["record"])
        sequence = len(checkpoint["events"]) + 1
        data = {"path": expected_next["record"]["path"], "rawSha256": expected_next["record"]["rawSha256"],
                "draftSha256": expected_next["record"]["draftSha256"], "recoveredOrphan": True}
        event = {"sequence": sequence, "previousEventSha256": checkpoint["eventHead"],
                 "event": "CANDIDATE_RECOVERED", "data": data}
        event["eventSha256"] = _event_hash(event["previousEventSha256"], sequence, event["event"], data)
        checkpoint["events"].append(event); checkpoint["eventHead"] = event["eventSha256"]
        checkpoint["status"] = "RUNNING"
        checkpoint = _save_checkpoint(run_dir, checkpoint)
    if resume and checkpoint["status"] == "COMPLETED":
        return checkpoint
    if marker.exists():
        checkpoint["status"] = "CANCELLED"
        checkpoint = _save_checkpoint(run_dir, checkpoint)
        _atomic_replace(run_dir / "progress.json", _json_bytes({"status": "CANCELLED", "completed": len(saved), "total": total}, pretty=True))
        return checkpoint
    checkpoint["status"] = "RUNNING"
    checkpoint = _save_checkpoint(run_dir, checkpoint)
    _atomic_replace(run_dir / "progress.json", _json_bytes({"status": checkpoint["status"],
                    "completed": len(saved), "total": total}, pretty=True))
    started = time.monotonic()
    made = 0
    while len(saved) < total:
        if marker.exists():
            checkpoint["status"] = "CANCELLED"
            checkpoint["elapsedSeconds"] = round(time.monotonic() - started, 6)
            checkpoint = _save_checkpoint(run_dir, checkpoint)
            _atomic_replace(run_dir / "progress.json", _json_bytes({"status": "CANCELLED", "completed": len(saved), "total": total}, pretty=True))
            break
        item = _candidate_for_index(config, len(saved), saved)
        raw = _json_bytes(item["draft"], pretty=True)
        path = run_dir / item["record"]["path"]
        _atomic_create(path, raw)
        if crash_after_artifact:
            raise RuntimeError("injected crash after candidate artifact write")
        item["record"]["rawSha256"] = _sha(raw)
        saved.append(item)
        checkpoint["records"].append(item["record"])
        sequence = len(checkpoint["events"]) + 1
        data = {"path": item["record"]["path"], "rawSha256": item["record"]["rawSha256"],
                "draftSha256": item["record"]["draftSha256"], "recoveredOrphan": False}
        event = {"sequence": sequence, "previousEventSha256": checkpoint["eventHead"],
                 "event": "CANDIDATE_COMMITTED", "data": data}
        event["eventSha256"] = _event_hash(event["previousEventSha256"], sequence, event["event"], data)
        checkpoint["events"].append(event); checkpoint["eventHead"] = event["eventSha256"]
        checkpoint["status"] = "RUNNING"
        checkpoint = _save_checkpoint(run_dir, checkpoint)
        made += 1
        if progress_callback:
            progress_callback({"status": checkpoint["status"], "completed": len(saved), "total": total,
                               "profileId": item["record"]["profileId"], "attempt": item["record"]["attempt"]})
        _atomic_replace(run_dir / "progress.json", _json_bytes({"status": checkpoint["status"],
                        "completed": len(saved), "total": total,
                        "profileId": item["record"]["profileId"], "attempt": item["record"]["attempt"]}, pretty=True))
        if max_new_candidates is not None and made >= max_new_candidates:
            break
    if len(saved) == total:
        checkpoint["status"] = "COMPLETED"
        checkpoint["elapsedSeconds"] = round(time.monotonic() - started, 6)
        checkpoint = _save_checkpoint(run_dir, checkpoint)
        _atomic_replace(run_dir / "progress.json", _json_bytes({"status": "COMPLETED", "completed": total, "total": total}, pretty=True))
    return checkpoint


def _cell(row: int, column: int, gem: str) -> dict[str, Any]:
    return {"row": row, "column": column, "layer": 0, "active": True,
            "locked": False, "contentId": gem, "obstacleId": None,
            "obstacleDurability": 0, "lockDurability": 0, "specialId": None}


def create_draft(profile_id: str, seed: int, *, width: int = 8, height: int = 8,
                 colors: int = 4) -> dict[str, Any]:
    """Create a deterministic full-active board using only Studio sample gems."""
    if profile_id not in PROFILE_IDS:
        raise ValueError("unknown profile")
    if type(seed) is not int or not 0 <= seed <= 2**63 - 1:
        raise ValueError("seed must be an integer in [0, 2^63-1]")
    if type(width) is not int or not 6 <= width <= 12 or type(height) is not int or not 6 <= height <= 12:
        raise ValueError("local sample dimensions must be within [6, 12]")
    if type(colors) is not int or not 3 <= colors <= min(6, len(PALETTE)):
        raise ValueError("color count must be within [3, 6]")

    # Profile is part of the seed stream so same-seed title boards do not
    # silently become cross-title clones. This is authoring diversity only.
    profile_offset = PROFILE_IDS.index(profile_id) * 1_000_003
    rng = random.Random(seed ^ profile_offset)
    palette = PALETTE[:colors]
    grid: list[list[str]] = []
    for row in range(height):
        current: list[str] = []
        for column in range(width):
            choices = [gem for gem in palette
                       if not (column >= 2 and current[column - 1] == current[column - 2] == gem)
                       and not (row >= 2 and grid[row - 1][column] == grid[row - 2][column] == gem)]
            if not choices:
                raise RuntimeError("palette cannot satisfy the no-initial-triple constraint")
            current.append(rng.choice(choices))
        grid.append(current)

    draft = {
        "draftVersion": 1, "validationStatus": "PROTOTYPE_ONLY",
        "gameProfileId": profile_id, "profileVersion": 1,
        "worldId": "world.r03.local", "chapterId": "chapter.r03.local",
        "levelId": f"local.seed-{seed}", "releaseChannel": "local",
        "platform": "windows-editor", "locale": "en",
        "seed": seed, "width": width, "height": height,
        "minEngineVersion": None, "maxEngineVersion": None,
        "layers": 1, "activeMask": [True] * (width * height),
        "moveBudget": 20,
        "cells": [_cell(r, c, grid[r][c]) for r in range(height) for c in range(width)],
        "goals": [{"goalId": "goal.primary", "targetId": "sample.score", "targetCount": 500}],
        "engineSchemaVersion": None, "timedMode": False,
        "timeLimitSeconds": 0, "oneStarThreshold": 100,
        "twoStarThreshold": 250, "threeStarThreshold": 500,
        "difficultyLabel": "difficulty.unrated", "editorHintKey": None,
        "sourceRepository": "Match3-Level-Factory",
        "sourceRevision": SOURCE_REVISION, "sourceKind": SOURCE_KIND,
    }
    leveldraft.validate(draft)
    if diagnose_profile_compatibility(draft)["localPolicyStatus"] != "ACCEPTED_FOR_LOCAL_AUTHORING_ONLY":
        raise ValueError("generated board is outside the confirmed sample-profile contract")
    return leveldraft.canonicalize(draft)


def build_batch(profiles: list[str], *, attempts_per_profile: int, seed_start: int,
                width: int = 8, height: int = 8, colors: int = 4,
                near_duplicate_threshold: float = .95) -> dict[str, Any]:
    if not profiles or len(set(profiles)) != len(profiles) or any(p not in PROFILE_IDS for p in profiles):
        raise ValueError("profiles must be a nonempty unique subset of the five known profiles")
    if type(attempts_per_profile) is not int or not 1 <= attempts_per_profile <= 10:
        raise ValueError("attempts_per_profile must be within [1, 10]")
    if len(profiles) * attempts_per_profile > MAX_BATCH:
        raise ValueError("batch exceeds the 50-draft safety cap")
    accepted: dict[str, list[tuple[str, dict[str, Any]]]] = {p: [] for p in profiles}
    all_accepted: list[tuple[str, dict[str, Any]]] = []
    records = []
    for pi, profile in enumerate(profiles):
        for attempt in range(attempts_per_profile):
            seed = seed_start + pi * 100_000 + attempt
            draft = create_draft(profile, seed, width=width, height=height, colors=colors)
            canonical = leveldraft.dumps_canonical(draft)
            sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            prior = accepted[profile]
            comparisons = [(candidate_id, candidate_diversity.compare_drafts(draft, old))
                           for candidate_id, old in prior]
            nearest = max(comparisons, key=lambda item: item[1]["similarity"], default=None)
            cross_clone = next((cid for cid, old in all_accepted
                                if candidate_diversity.structural_fingerprint(old) ==
                                candidate_diversity.structural_fingerprint(draft)), None)
            status = "LOCAL_SAMPLE_COMPATIBLE_PREVIEW_ONLY"
            if nearest and nearest[1]["similarity"] >= near_duplicate_threshold:
                status = "REJECTED_NEAR_DUPLICATE"
            elif cross_clone:
                status = "REJECTED_CROSS_PROFILE_CLONE"
            cid = f"{profile}/local-{attempt + 1:02d}/seed-{seed}-{sha[:12]}"
            record = {"candidateId": cid, "profileId": profile, "attempt": attempt + 1,
                      "seed": seed, "sourceKind": SOURCE_KIND, "sourceRevision": SOURCE_REVISION,
                      "sourceGenerated": True, "generationEvent": "FACTORY_ORIGINAL_LOCAL_AUTHORING",
                      "draftSha256": sha, "status": status,
                      "nearestCandidate": nearest[0] if nearest else None,
                      "crossProfileCloneOf": cross_clone, "engineStatus": "BLOCKED_ENG_M24",
                      "engineQualified": False, "ownerReviewed": False, "ownerApproved": False,
                      "draft": draft}
            records.append(record)
            if status == "LOCAL_SAMPLE_COMPATIBLE_PREVIEW_ONLY":
                accepted[profile].append((cid, draft))
                all_accepted.append((cid, draft))
    return {"resultStatus": "COMPLETED", "sourceKind": SOURCE_KIND,
            "sourceRevision": SOURCE_REVISION, "engineStatus": "BLOCKED_ENG_M24",
            "engineQualifiedCampaignLevels": 0, "ownerReviewed": 0, "ownerApproved": 0,
            "generationAttempts": len(records), "localDraftCount": len(records),
            "locallyCompatibleUniqueCount": sum(len(v) for v in accepted.values()),
            "rejectedNearOrCrossProfileCount": sum(r["status"].startswith("REJECTED") for r in records),
            "profileResults": {p: {"attempts": sum(r["profileId"] == p for r in records),
                                   "uniqueLocal": len(accepted[p])} for p in profiles},
            "records": records}


def write_batch(output_dir: Path, batch: dict[str, Any]) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError("local-authoring output directory must be empty")
    output_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    local_records = []
    for record in batch["records"]:
        draft_text = leveldraft.dumps_canonical(record["draft"], pretty=True)
        draft_path = output_dir / "drafts" / record["profileId"] / (record["candidateId"].split("/")[1] + ".json")
        draft_path.parent.mkdir(parents=True, exist_ok=True)
        with draft_path.open("xb") as stream:
            stream.write(draft_text.encode("utf-8"))
        record_path = Path("drafts") / record["profileId"] / draft_path.name
        entries.append({"path": record_path.as_posix(), "sizeBytes": draft_path.stat().st_size,
                        "sha256": hashlib.sha256(draft_path.read_bytes()).hexdigest(),
                        "draftSha256": record["draftSha256"], "status": record["status"],
                        "profileId": record["profileId"], "seed": record["seed"]})
        local_records.append({k: v for k, v in record.items() if k != "draft"} | {
            "recordPath": record_path.as_posix(),
            "recordSha256": hashlib.sha256(draft_path.read_bytes()).hexdigest(),
        })
    summary = {k: v for k, v in batch.items() if k != "records"}
    summary["records"] = local_records
    with (output_dir / "summary.json").open("xb") as stream:
        stream.write((json.dumps(summary, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    manifest = {"manifestVersion": 1, "sourceKind": SOURCE_KIND, "entries": entries}
    with (output_dir / "manifest.json").open("xb") as stream:
        stream.write((json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--profiles", default=",".join(PROFILE_IDS))
    parser.add_argument("--attempts-per-profile", type=int, default=5)
    parser.add_argument("--seed-start", type=int, default=330000)
    parser.add_argument("--width", type=int, default=8)
    parser.add_argument("--height", type=int, default=8)
    parser.add_argument("--colors", type=int, default=4)
    parser.add_argument("--output-relative", required=True)
    parser.add_argument("--session-start", action="store_true", help="initialize and run a crash-safe local session")
    parser.add_argument("--session-resume", action="store_true", help="resume the authenticated local session")
    parser.add_argument("--cancel-local-run", action="store_true", help="write a durable cancel request for this run")
    args = parser.parse_args(argv)
    root = args.project_root.resolve()
    relative = Path(args.output_relative)
    if relative.is_absolute() or ".." in relative.parts:
        parser.error("output must be a safe project-relative path")
    output = (root / relative).resolve()
    if not output.is_relative_to(root):
        parser.error("output resolves outside project root")
    try:
        if args.cancel_local_run:
            request_cancel(output)
            sys.stdout.write(json.dumps({"resultStatus": "CANCEL_REQUESTED", "run": args.output_relative}) + "\n")
            return 0
        if args.session_start:
            start_run(root, args.output_relative,
                      [p for p in args.profiles.split(",") if p],
                      attempts_per_profile=args.attempts_per_profile, seed_start=args.seed_start,
                      width=args.width, height=args.height, colors=args.colors)
        if args.session_start or args.session_resume:
            checkpoint = run_session(root, args.output_relative, resume=args.session_resume)
            sys.stdout.write(json.dumps({"resultStatus": checkpoint["status"],
                             "completed": len(checkpoint["records"]),
                             "engineStatus": "BLOCKED_ENG_M24"}) + "\n")
            return 0
        batch = build_batch([p for p in args.profiles.split(",") if p],
                            attempts_per_profile=args.attempts_per_profile,
                            seed_start=args.seed_start, width=args.width,
                            height=args.height, colors=args.colors)
        summary = write_batch(output, batch)
    except (OSError, ValueError, RuntimeError) as exc:
        sys.stderr.write(f"local_authoring_error: {type(exc).__name__}: {exc}\n")
        return 2
    sys.stdout.write(json.dumps({k: summary[k] for k in (
        "resultStatus", "generationAttempts", "localDraftCount",
        "locallyCompatibleUniqueCount", "engineQualifiedCampaignLevels", "engineStatus")}) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
