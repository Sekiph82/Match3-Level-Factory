"""Bounded Python 3 adapter around UltraGem's original scenario and policy code.

Gameplay outcomes produced here are REFERENCE_ONLY. MATCH3_ENGINE is the only
authority for final playability and difficulty classification.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import numpy

from gemengine import (
    Activater,
    Board,
    BoardGravityPuller,
    Combiner,
    InitialFillerDisable,
    InitialFillerDoubleLock,
    InitialFillerDoubleLockSpecial,
    NastyTopFiller,
    PairCombiner,
    best_move_selector,
    random_move_selector,
    smart_move_selector,
    worst_move_selector,
)

POLICIES: tuple[tuple[str, Callable], ...] = (
    ("worst", worst_move_selector),
    ("random", random_move_selector),
    ("best", best_move_selector),
    ("smart", smart_move_selector),
)
STAT_NAMES = (
    "score", "ndestroyed", "nunlocked", "nstripe", "nbomb", "nzapper",
    "combo_22", "combo_42", "combo_44", "combo_51", "combo_52", "combo_54", "combo_55",
)


@dataclass(frozen=True)
class RunResult:
    policy: str
    run_seed: int
    moves_used: int
    shuffles: int
    outcome: str
    steps: list[list[int]]


def scoring_function(events: list[tuple[str, int]]) -> list[int]:
    nspecial = [0, 0, 0]
    combo_index = {22: 0, 42: 1, 44: 2, 51: 3, 52: 4, 54: 5, 55: 6}
    combos = [0, 0, 0, 0, 0, 0, 0]
    unlocked = destroyed = score = 0
    for event, value in events:
        if event == "activated":
            if value in (2, 3):
                nspecial[0] += 1
            elif value == 4:
                nspecial[1] += 1
            elif value == 5:
                nspecial[2] += 1
            score += 10 * value
        elif event == "unlocked":
            unlocked += value
        elif event == "destroyed":
            destroyed += value
            score += value
        elif event == "combined" and value in combo_index:
            combos[combo_index[value]] += 1
    return [score, destroyed, unlocked] + nspecial + combos


def create_scenario(nrows: int, ncols: int, ncolors: int, seed: int):
    """Keep UltraGem's original weighted blocker and special placement."""
    rng = numpy.random.RandomState(seed)
    board = Board(nrows=nrows, ncols=ncols)
    row_weights = 1.0 / (0.2 + numpy.arange(nrows))
    row_weights /= row_weights.sum()
    double_locked_rows = rng.choice(numpy.arange(nrows), p=row_weights)
    disabled_rows = rng.choice(numpy.arange(nrows), p=row_weights)
    col_weights = 1.0 / (0.2 + numpy.arange(ncols))
    col_weights /= col_weights.sum()
    double_locked_cols = rng.choice(numpy.arange(ncols), p=col_weights)
    disabled_cols = rng.choice(numpy.arange(ncols), p=col_weights)
    if rng.uniform() < 0.1:
        allowed_types = [2, 3, 4, 5] if rng.uniform() < 0.5 else [2, 3, 4]
        InitialFillerDoubleLockSpecial(
            board, ncolors=ncolors, types=allowed_types, nrows=int(double_locked_rows),
            ncols=int(double_locked_cols), rng=rng
        ).run()
    else:
        InitialFillerDoubleLock(
            board, nrows=int(double_locked_rows), ncols=int(double_locked_cols), rng=rng
        ).run()
    if rng.uniform() < 0.1:
        InitialFillerDisable(
            board, nrows=int(disabled_rows), ncols=int(disabled_cols), rng=rng
        ).run()
    return board, NastyTopFiller(board, ncolors=ncolors)


def _simulate_one(board: Board, topfill, selector: Callable, policy: str, run_seed: int,
                  max_moves: int, max_shuffles: int) -> RunResult:
    numpy.random.seed(run_seed)
    gravity = BoardGravityPuller(board)
    combiner = Combiner(board)
    pair = PairCombiner(board)
    activater = Activater(board)
    step_scores: list[list[int]] = []
    moves = shuffles = cascades = iterations = 0
    outcome = "MOVE_LIMIT"

    while moves < max_moves:
        iterations += 1
        if iterations > max_moves * 100 + max_shuffles * 4 + 100:
            outcome = "STEP_BUDGET_EXCEEDED"
            break

        changed = gravity.run()
        changed += topfill.run()
        if changed:
            continue

        changed = combiner.run()
        changed += activater.run()
        if changed:
            cascades += 1
            if cascades > (moves + 1) * 40:
                outcome = "CASCADE_BUDGET_EXCEEDED"
                break
            continue

        moves_list = list(pair.enumerate_valid_moves())
        if not moves_list:
            shuffles += 1
            if shuffles > max_shuffles:
                outcome = "NO_MOVES_AFTER_SHUFFLE_BUDGET"
                break
            pair.shuffle()
            continue

        step_scores.append(scoring_function(board.events))
        move = selector(board, moves_list)
        pair.run(*move)
        moves += 1
        combiner.set_last_interaction(*move)
        changed = combiner.run()
        changed += activater.run()
        if changed:
            cascades += 1
            if cascades > (moves + 1) * 40:
                outcome = "CASCADE_BUDGET_EXCEEDED"
                break

    final_score = scoring_function(board.events)
    while len(step_scores) < max_moves:
        step_scores.append(final_score.copy())
    return RunResult(policy, run_seed, moves, shuffles, outcome, step_scores[:max_moves])


def evaluate_candidate(rows: int, columns: int, colors: int, seed: int, runs: int,
                       max_moves: int) -> dict:
    if not (6 <= rows <= 12 and 6 <= columns <= 12):
        raise ValueError("board dimensions must each be between 6 and 12")
    if not 3 <= colors <= 6:
        raise ValueError("colors must be between 3 and 6")
    if not 0 <= seed <= 2**31 - 1:
        raise ValueError("seed must be between 0 and 2^31-1")
    if not 1 <= runs <= 8 or not 1 <= max_moves <= 40:
        raise ValueError("runs must be 1..8 and max_moves must be 1..40")
    board, _ = create_scenario(rows, columns, colors, seed)
    # Freeze candidate geometry before simulations so all policies see the same
    # candidate. A fresh filler is bound to each cloned board.
    initial = board.copy()
    policy_runs: dict[str, list[RunResult]] = {}
    for policy_index, (name, selector) in enumerate(POLICIES):
        results = []
        for run_index in range(runs):
            trial = initial.copy()
            filler = NastyTopFiller(trial, ncolors=colors)
            run_seed = (seed + 104729 * (run_index + 1) + 1009 * policy_index) % (2**31 - 1)
            results.append(_simulate_one(trial, filler, selector, name, run_seed,
                                         max_moves, max_shuffles=20))
        policy_runs[name] = results

    return {
        "seed": seed,
        "rows": rows,
        "columns": columns,
        "colors": colors,
        "initialBoard": _board_payload(initial),
        "referenceOnly": True,
        "engineValidation": "BLOCKED_ENG_M24",
        "statistics": {
            policy: {
                "completedRuns": len(results),
                "outcomes": [result.outcome for result in results],
                "runSeeds": [result.run_seed for result in results],
                "steps": [result.steps for result in results],
            }
            for policy, results in policy_runs.items()
        },
    }


def _board_payload(board: Board) -> dict:
    rows, columns = board.shape
    cells = []
    for row in range(rows):
        for column in range(columns):
            cells.append({
                "row": row,
                "column": column,
                "type": int(board.type[row, column]),
                "color": int(board.color[row, column]),
                "status": int(board.status[row, column]),
            })
    return {"rows": rows, "columns": columns, "cells": cells}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run bounded UltraGem reference-only simulations.")
    parser.add_argument("--rows", type=int, default=8)
    parser.add_argument("--columns", type=int, default=8)
    parser.add_argument("--colors", type=int, default=3)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--runs", type=int, default=2)
    parser.add_argument("--max-moves", type=int, default=20)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = evaluate_candidate(args.rows, args.columns, args.colors, args.seed, args.runs,
                                    args.max_moves)
        text = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        if args.output:
            if args.output.is_absolute() or ".." in args.output.parts:
                raise ValueError("output must be a relative path without parent traversal")
            destination = (Path.cwd() / args.output).resolve()
            if not destination.is_relative_to(Path.cwd().resolve()):
                raise ValueError("output resolves outside the current project")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(text, encoding="utf-8", newline="\n")
        else:
            sys.stdout.write(text)
        return 0
    except (ValueError, OSError) as error:
        sys.stderr.write(f"invalid_input: {error}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
