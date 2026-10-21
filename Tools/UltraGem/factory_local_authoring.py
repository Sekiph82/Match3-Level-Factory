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
from pathlib import Path
from typing import Any

import candidate_diversity
import leveldraft
from profile_compatibility import PROFILE_IDS, diagnose_profile_compatibility

SOURCE_KIND = "FactoryOriginalLocalSampleBoard"
SOURCE_REVISION = "LFX-M11-R03-local-authoring-v1"
PALETTE = ("Blue", "Green", "Orange", "Purple", "White", "Yellow")
MAX_BATCH = 50


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
    args = parser.parse_args(argv)
    root = args.project_root.resolve()
    relative = Path(args.output_relative)
    if relative.is_absolute() or ".." in relative.parts:
        parser.error("output must be a safe project-relative path")
    output = (root / relative).resolve()
    if not output.is_relative_to(root):
        parser.error("output resolves outside project root")
    try:
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
