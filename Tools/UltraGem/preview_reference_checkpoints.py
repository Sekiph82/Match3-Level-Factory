"""LFX-M08-007 partial: UltraGem *checkpoint* preview, NOT gameplay simulation.

Reuse the adapted scoregames.STAT_NAMES checkpoint schema. UltraGem captures
cumulative event values BEFORE each policy move, not board frames or exact
cascade order. Do not reconstruct unobserved events or claim goal/WIN/replay.
Source-first INTERNAL_REUSE of factory_pipeline + scoregames from
JohannesBuchner/ultragem @0e64a5bc66a5fce4b899bf0734c9cc7417b4ed12.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from scoregames import STAT_NAMES

PINNED = "0e64a5bc66a5fce4b899bf0734c9cc7417b4ed12"
POLICIES = ("worst", "random", "best", "smart")
OUTCOMES = {"MOVE_LIMIT", "STEP_BUDGET_EXCEEDED", "CASCADE_BUDGET_EXCEEDED",
            "NO_MOVES_AFTER_SHUFFLE_BUDGET"}


def _nonnegative(value: Any, name: str, limit: int = 10**12) -> int:
    if type(value) is not int or not 0 <= value <= limit:
        raise ValueError(f"{name} must be a bounded integer")
    return value


def preview_reference_checkpoints(batch: dict[str, Any], *, candidate_index: int,
                                  policy: str, run_index: int) -> dict[str, Any]:
    if not isinstance(batch, dict) or batch.get("resultStatus") != "REFERENCE_ONLY_UNVERIFIED":
        raise ValueError("input must be a reference-only batch, not Engine or release data")
    if (batch.get("engineStatus") != "BLOCKED_ENG_M24"
            or batch.get("sourceRepository") != "JohannesBuchner/ultragem"
            or batch.get("sourceRevision") != PINNED):
        raise ValueError("missing pinned donor and blocked Engine provenance")
    config = batch.get("configuration")
    if not isinstance(config, dict):
        raise ValueError("missing factory generation configuration")
    max_moves = _nonnegative(config.get("maxMoves"), "maxMoves", 40)
    if not 1 <= max_moves <= 40:
        raise ValueError("maxMoves outside existing factory budget")
    _nonnegative(candidate_index, "candidate_index", 15)
    _nonnegative(run_index, "run_index", 7)
    if not isinstance(policy, str) or policy not in POLICIES:
        raise ValueError("unknown donor policy; fifth Engine persona is unavailable")
    records = batch.get("referenceStatistics")
    if not isinstance(records, list) or not 1 <= len(records) <= 16:
        raise ValueError("referenceStatistics must be a bounded nonempty batch")
    matches = [record for record in records if isinstance(record, dict)
               and record.get("candidateIndex") == candidate_index]
    if len(matches) != 1:
        raise ValueError("missing or duplicate candidate checkpoint provenance")
    data = matches[0].get("statistics")
    if not isinstance(data, dict) or set(data) != set(POLICIES):
        raise ValueError("four original donor policies required")
    row = data[policy]
    if not isinstance(row, dict):
        raise ValueError("invalid donor policy record")
    count = _nonnegative(row.get("completedRuns"), "completedRuns", 8)
    if not 1 <= count <= 8:
        raise ValueError("invalid run count")
    if not all(isinstance(row.get(k), list) and len(row[k]) == count
               for k in ("outcomes", "runSeeds", "steps")):
        raise ValueError("donor run fields disagree with completedRuns")
    if run_index >= count:
        raise ValueError("unknown run")
    if any(o not in OUTCOMES for o in row["outcomes"]):
        raise ValueError("unknown donor outcome, cannot promote to WIN")
    run_seed = _nonnegative(row["runSeeds"][run_index], "runSeed", 2**31 - 1)
    sample = row["steps"][run_index]
    if not isinstance(sample, list) or len(sample) != max_moves:
        raise ValueError("exact bounded before-move checkpoints required")
    if len(STAT_NAMES) != 13 or len(set(STAT_NAMES)) != 13:
        raise ValueError("donor checkpoint schema drift")
    checkpoints = []
    previous = [0] * len(STAT_NAMES)
    for index, values in enumerate(sample):
        if not isinstance(values, list) or len(values) != len(STAT_NAMES):
            raise ValueError("checkpoint length invalid")
        validated = [_nonnegative(v, "metric") for v in values]
        if any(now < before for now, before in zip(validated, previous)):
            raise ValueError("donor cumulative checkpoint moved backwards")
        delta = {name: now - before for name, now, before
                 in zip(STAT_NAMES, validated, previous) if now != before}
        checkpoints.append({"beforeMove": index + 1, "deltaSincePriorCheckpoint": delta,
                            "cumulative": dict(zip(STAT_NAMES, validated))})
        previous = validated
    digest = hashlib.sha256(json.dumps(sample, sort_keys=True, separators=(",", ":"))
                            .encode("utf-8")).hexdigest()
    return {
        "resultStatus": "REFERENCE_CHECKPOINT_PREVIEW_ONLY",
        "engineStatus": "BLOCKED_ENG_M24",
        "sourceRevision": PINNED,
        "candidateIndex": candidate_index,
        "policy": policy,
        "runIndex": run_index,
        "runSeed": run_seed,
        "donorOutcome": row["outcomes"][run_index],
        "checkpointSha256": digest,
        "checkpointsAreBeforeMove": True,
        "exactCascadeOrderOrBoardFramesAvailable": False,
        "goalsOrWinProved": False,
        "lastMoveMayBeUnobserved": True,
        "releaseAuthorized": False,
        "checkpoints": checkpoints,
    }



def _unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError(f"duplicate JSON key: {name}")
        result[name] = value
    return result


def main(argv: list[str] | None = None) -> int:
    """Read one prior donor pipeline JSON and print a read-only preview.

    No file writes, no play/Engine invocation and no automatic publication.
    """
    import argparse
    import sys
    from pathlib import Path

    parser = argparse.ArgumentParser(description="UltraGem reference checkpoints (NOT Engine gameplay)")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--candidate", type=int, default=0)
    parser.add_argument("--policy", choices=POLICIES, default="smart")
    parser.add_argument("--run", type=int, default=0)
    args = parser.parse_args(argv)
    try:
        source = args.input
        if not source.is_file() or source.is_symlink():
            raise ValueError("input must be an existing non-symlink file")
        if not 0 < source.stat().st_size <= 2_000_000:
            raise ValueError("input must be nonempty and at most 2MB")
        batch = json.loads(source.read_text(encoding="utf-8-sig"),
                           object_pairs_hook=_unique_keys,
                           parse_constant=lambda value: (_ for _ in ()).throw(
                               ValueError(f"invalid numeric constant: {value}")))
        output = preview_reference_checkpoints(
            batch, candidate_index=args.candidate, policy=args.policy, run_index=args.run
        )
        sys.stdout.write(json.dumps(output, sort_keys=True, ensure_ascii=False, indent=2) + "\n")
        return 0
    except (ValueError, OSError, UnicodeError, json.JSONDecodeError) as error:
        sys.stderr.write(f"invalid_checkpoint_input: {error}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
