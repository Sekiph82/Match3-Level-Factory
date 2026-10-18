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



def _initial_board_observation(candidate: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Capture the real donor's SETUP board; never reconstruct later board states."""
    board = candidate.get("initialBoard")
    if not isinstance(board, dict) or set(board) != {"rows", "columns", "cells"}:
        raise ValueError("pinned donor initialBoard must have exact dimensions and cells")
    rows = _nonnegative(board["rows"], "initialBoard.rows", 12)
    columns = _nonnegative(board["columns"], "initialBoard.columns", 12)
    if not (6 <= rows <= 12 and 6 <= columns <= 12):
        raise ValueError("initial donor dimensions are outside the pinned generator")
    raw_cells = board["cells"]
    if not isinstance(raw_cells, list) or len(raw_cells) != rows * columns:
        raise ValueError("initial donor cells do not cover the full board")
    cells = []
    seen = set()
    numeric = []
    for cell in raw_cells:
        if not isinstance(cell, dict) or set(cell) != {"row", "column", "type", "color", "status"}:
            raise ValueError("invalid donor board cell fields")
        row = _nonnegative(cell["row"], "initialCell.row", rows - 1)
        column = _nonnegative(cell["column"], "initialCell.column", columns - 1)
        kind = cell["type"]
        if type(kind) is not int or not -1 <= kind <= 5:
            raise ValueError("unknown original donor gem type")
        color = _nonnegative(cell["color"], "initialCell.color", 6)
        status = _nonnegative(cell["status"], "initialCell.status", 2)
        if (row, column) in seen:
            raise ValueError("duplicate initial donor board cell")
        seen.add((row, column))
        cells.append({"row": row, "column": column, "type": kind,
                      "color": color, "status": status})
    cells.sort(key=lambda c: (c["row"], c["column"]))
    for cell in cells:
        if cell["type"] == -1 and (cell["color"] != 0 or cell["status"] != 0):
            raise ValueError("disabled donor cell cannot hold a color or a lock")
        numeric.append([cell["row"], cell["column"], cell["type"],
                        cell["color"], cell["status"]])
    digest = hashlib.sha256(json.dumps(numeric, separators=(",", ":")).encode("utf-8")).hexdigest()
    return {"rows": rows, "columns": columns, "cells": cells}, digest


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
    initial_board, board_sha = _initial_board_observation(matches[0])
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
        "initialBoard": initial_board,
        "initialBoardSha256": board_sha,
        "initialBoardIsSeededDonorSetup": True,
        "boardAtCheckpointAvailable": False,
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

    No implicit file writes; an explicit --output creates NEW project-contained JSON only.\n    No play/Engine invocation, overwrite or automatic publication.
    """
    import argparse
    import sys
    from pathlib import Path

    parser = argparse.ArgumentParser(description="UltraGem reference checkpoints (NOT Engine gameplay)")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--candidate", type=int, default=0)
    parser.add_argument("--policy", choices=POLICIES, default="smart")
    parser.add_argument("--run", type=int, default=0)
    parser.add_argument("--output", type=Path, help="optional NEW project-relative .json; no overwrite")
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
        content = json.dumps(output, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
        if args.output is None:
            sys.stdout.write(content)
        else:
            requested = args.output
            if requested.is_absolute() or ".." in requested.parts or requested.suffix.lower() != ".json":
                raise ValueError("output must be a relative .json path without parent traversal")
            base = Path.cwd().resolve()
            destination = (base / requested).resolve()
            if not destination.is_relative_to(base) or not destination.parent.is_dir():
                raise ValueError("output must stay inside an existing current-project directory")
            with destination.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(content)
        return 0
    except (ValueError, OSError, UnicodeError, json.JSONDecodeError) as error:
        sys.stderr.write(f"invalid_checkpoint_input: {error}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
