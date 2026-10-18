"""LFX-M07-003: bounded repeat-seed UltraGem *reference* observation matrix.

Runs the pinned donor pipeline as a child. Neither donor 'wins' nor ranked
levels are real Match3 Engine wins, difficulty, solvability or release approval.
The caller gets FAIL/UNKNOWN for errors/timeouts; no fabricated success.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import leveldraft
from factory_pipeline import ULTRAGEM_REVISION

MAX_SEEDS = 8
MAX_JSON_BYTES = 2_000_000


def _strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON property")
        result[key] = value
    return result


def _read_result(text: str, seed: int, profile_id: str) -> dict[str, Any]:
    if len(text.encode("utf-8")) > MAX_JSON_BYTES:
        raise ValueError("donor output exceeds size limit")
    try:
        result = json.loads(text, object_pairs_hook=_strict_pairs)
    except (ValueError, TypeError) as exc:
        raise ValueError("donor result is not JSON") from exc
    if (not isinstance(result, dict)
        or result.get("resultStatus") != "REFERENCE_ONLY_UNVERIFIED"
        or result.get("engineStatus") != "BLOCKED_ENG_M24"
        or result.get("sourceRevision") != ULTRAGEM_REVISION
        or type(result.get("seed")) is not int or result.get("seed") != seed):
        raise ValueError("donor revision/status/seed mismatch")
    config = result.get("configuration")
    if not isinstance(config, dict) or config.get("gameProfileId") != profile_id:
        raise ValueError("donor profile mismatch")
    drafts = result.get("drafts")
    if not isinstance(drafts, list) or not 1 <= len(drafts) <= 16:
        raise ValueError("invalid donor draft count")
    seen = set()
    ranked = 0
    rejected = 0
    for record in drafts:
        if not isinstance(record, dict) or not isinstance(record.get("draft"), dict):
            raise ValueError("invalid record")
        draft = record["draft"]
        leveldraft.validate(draft)
        digest = leveldraft.sha256(draft)
        if digest != record.get("draftSha256") or digest in seen:
            raise ValueError("draft hash mismatch/duplicate")
        if draft["gameProfileId"] != profile_id:
            raise ValueError("foreign draft profile")
        seen.add(digest)
        if record.get("rankingStatus") == "RANKED_REFERENCE_HEURISTIC":
            ranked += 1
        elif record.get("rankingStatus") != "NOT_RANKED_BY_PINNED_HEURISTIC":
            raise ValueError("invalid donor ranking")
        compatibility = record.get("profileCompatibility")
        if not isinstance(compatibility, dict) or compatibility.get("engineStatus") != "BLOCKED_ENG_M24":
            raise ValueError("fake Engine compatibility")
        if compatibility.get("localPolicyStatus") != "ACCEPTED_FOR_LOCAL_AUTHORING_ONLY":
            rejected += 1
    return {
        "status": "REFERENCE_OBSERVED",
        "seed": seed,
        "rankedDrafts": ranked,
        "unrankedDrafts": len(drafts) - ranked,
        "localPolicyRejectedDrafts": rejected,
        "referenceArtifactSha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "draftSha256": sorted(seen),
    }


def sample_reference_seeds(*, seeds: list[int], profile_id: str = "Coral_Rescue",
                           timeout_seconds: int = 12, rows: int = 6, columns: int = 6,
                           colors: int = 3, runs: int = 1, max_moves: int = 2) -> dict[str, Any]:
    """Process-isolated observations; no writes, cloud, credentials or CI.

    The maximum wall-clock budget is MAX_SEEDS * 12s. Each child is killed
    on timeout, explicitly UNKNOWN; failure does not erase other samples.
    """
    if (not isinstance(seeds, list) or not 1 <= len(seeds) <= MAX_SEEDS
        or any(type(x) is not int or not 0 <= x < 2**31 for x in seeds)
        or len(set(seeds)) != len(seeds)):
        raise ValueError("seeds must be 1..8 unique bounded integers")
    if profile_id not in leveldraft.PROFILE_IDS:
        raise ValueError("unknown profile")
    if type(timeout_seconds) is not int or not 2 <= timeout_seconds <= 12:
        raise ValueError("per-seed timeout 2..12 seconds")
    if any(type(x) is not int for x in (rows, columns, colors, runs, max_moves)):
        raise ValueError("integer donor parameters required")
    if (not 3 <= rows <= 12 or not 3 <= columns <= 12 or not 3 <= colors <= 7
        or not 1 <= runs <= 4 or not 1 <= max_moves <= 20
        or runs * max_moves * 4 > 160):
        raise ValueError("donor work budget invalid")
    runner = Path(__file__).resolve().parent / "factory_pipeline.py"
    if not runner.is_file() or runner.is_symlink():
        raise ValueError("pinned runner unavailable")
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["OPENBLAS_NUM_THREADS"] = "1"
    env["OMP_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"
    observed = []
    for seed in sorted(seeds):
        cmd = [sys.executable, "-B", str(runner), "--seed", str(seed),
               "--rows", str(rows), "--columns", str(columns), "--colors", str(colors),
               "--candidates", "1", "--runs", str(runs), "--max-moves", str(max_moves),
               "--profile", profile_id, "--max-levels", "1"]
        try:
            proc = subprocess.run(cmd, cwd=runner.parent, env=env, capture_output=True,
                                  text=True, errors="replace", timeout=timeout_seconds, check=False)
            if proc.returncode != 0:
                row = {"seed": seed, "status": "REFERENCE_FAIL_PROCESS_EXIT", "exitCode": proc.returncode}
            else:
                try:
                    row = _read_result(proc.stdout, seed, profile_id)
                except (ValueError, leveldraft.DraftError):
                    row = {"seed": seed, "status": "REFERENCE_FAIL_INTEGRITY"}
        except subprocess.TimeoutExpired:
            row = {"seed": seed, "status": "UNKNOWN_TIMEOUT_KILLED"}
        except OSError:
            row = {"seed": seed, "status": "UNKNOWN_HOST_EXECUTION"}
        observed.append(row)
    counts = {s: sum(x["status"] == s for x in observed) for s in (
        "REFERENCE_OBSERVED", "REFERENCE_FAIL_PROCESS_EXIT",
        "REFERENCE_FAIL_INTEGRITY", "UNKNOWN_TIMEOUT_KILLED", "UNKNOWN_HOST_EXECUTION")}
    return {
        "resultStatus": "REFERENCE_STOCHASTIC_OBSERVATIONS_ONLY",
        "engineStatus": "BLOCKED_ENG_M24",
        "sourceRevision": ULTRAGEM_REVISION,
        "profileId": profile_id,
        "seeds": sorted(seeds), "runsPerSeed": runs, "maxMoves": max_moves,
        "observations": observed, "outcomeDistribution": counts,
        "allReferenceProcessesObserved": counts["REFERENCE_OBSERVED"] == len(seeds),
        "certifiedGameplaySuccessProbability": None,
        "certifiedDifficulty": None,
        "releaseAuthorized": False,
    }
