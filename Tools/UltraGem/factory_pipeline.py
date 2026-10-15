"""Offline end-to-end UltraGem -> LevelDraft prototype runner."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from genlevels import rank_levels
from leveldraft import dumps_canonical, from_ultragem
from scoregames import evaluate_candidate

ULTRAGEM_REVISION = "0e64a5bc66a5fce4b899bf0734c9cc7417b4ed12"


def run_pipeline(*, rows: int, columns: int, colors: int, seed: int, candidate_count: int,
                 runs: int, max_moves: int, profile_id: str,
                 max_levels: int) -> dict:
    if not 1 <= candidate_count <= 16:
        raise ValueError("candidate_count must be between 1 and 16")
    if candidate_count * runs * max_moves * 4 > 4096:
        raise ValueError("candidate × runs × moves exceeds the 4096-step work budget")
    candidates = []
    for index in range(candidate_count):
        candidate_seed = (seed + index * 7919) % (2**31 - 1)
        candidate = evaluate_candidate(rows, columns, colors, candidate_seed, runs,
                                       max_moves)
        candidate["candidateIndex"] = index
        candidates.append(candidate)
    levels = rank_levels(candidates, seed=seed, max_levels=max_levels)
    drafts = []
    by_index = {candidate["candidateIndex"]: candidate for candidate in candidates}
    for recommendation in levels:
        candidate = by_index[recommendation["candidateIndex"]]
        draft = from_ultragem(candidate, profile_id=profile_id, move_budget=recommendation["moveBudget"])
        draft["goals"] = [{
            "goalId": "goal.primary",
            "targetId": f"ultragem.goal.{recommendation['goalId']}",
            "targetCount": recommendation["targetCount"],
        }]
        draft["sourceKind"] = "UltraGemCandidate+RankedGoal"
        drafts.append({
            "ordinal": recommendation["ordinal"],
            "rankingStatus": "RANKED_REFERENCE_HEURISTIC",
            "difficultyHypothesis": recommendation["difficultyHypothesis"],
            "draft": draft,
            "draftSha256": __import__("leveldraft").sha256(draft),
        })
    # A valid unranked board remains useful as an editable prototype. Keep the
    # draft explicitly unranked and retain the placeholder goal from the mapper;
    # never manufacture a difficulty result when the donor heuristic rejects it.
    if not drafts:
        for index, candidate in enumerate(candidates):
            draft = from_ultragem(candidate, profile_id=profile_id, move_budget=max_moves)
            draft["sourceKind"] = "UltraGemCandidateUnranked"
            drafts.append({
                "ordinal": index + 1,
                "rankingStatus": "NOT_RANKED_BY_PINNED_HEURISTIC",
                "difficultyHypothesis": None,
                "draft": draft,
                "draftSha256": __import__("leveldraft").sha256(draft),
            })
    return {
        "resultStatus": "REFERENCE_ONLY_UNVERIFIED",
        "engineStatus": "BLOCKED_ENG_M24",
        "engineReason": "No independently accepted final MATCH3_ENGINE SDK package is pinned.",
        "sourceRepository": "JohannesBuchner/ultragem",
        "sourceRevision": ULTRAGEM_REVISION,
        "seed": seed,
        "configuration": {
            "rows": rows, "columns": columns, "colors": colors,
            "candidateCount": candidate_count, "runsPerPolicy": runs,
            "maxMoves": max_moves, "workBudget": "candidate_count*runs*max_moves*4<=4096",
            "gameProfileId": profile_id,
        },
        "candidateCountCompleted": len(candidates),
        "rankedLevels": levels,
        "drafts": drafts,
        "unrankedDraftCount": sum(item["rankingStatus"] == "NOT_RANKED_BY_PINNED_HEURISTIC" for item in drafts),
        "rejectedCandidates": rank_levels.last_rejections,
        "referenceStatistics": candidates,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run the bounded, offline, reference-only UltraGem candidate pipeline.")
    parser.add_argument("--rows", type=int, default=8)
    parser.add_argument("--columns", type=int, default=8)
    parser.add_argument("--colors", type=int, default=3)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--candidates", type=int, default=1)
    parser.add_argument("--runs", type=int, default=2)
    parser.add_argument("--max-moves", type=int, default=20)
    parser.add_argument("--profile", choices=("Coral_Rescue", "Garage_Legends", "Dino_Islands", "The_Fractured_Realms", "Wonder_Pop"), default="Coral_Rescue")
    parser.add_argument("--max-levels", type=int, default=20)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--overwrite", action="store_true", help="replace an existing output file explicitly")
    args = parser.parse_args(argv)
    try:
        destination = _resolve_output(args.output) if args.output else None
        result = run_pipeline(
            rows=args.rows, columns=args.columns, colors=args.colors, seed=args.seed,
            candidate_count=args.candidates, runs=args.runs, max_moves=args.max_moves,
            profile_id=args.profile,
            max_levels=args.max_levels,
        )
        text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, default=_json_scalar) + "\n"
        if destination:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if args.overwrite:
                destination.write_text(text, encoding="utf-8", newline="\n")
            else:
                with destination.open("x", encoding="utf-8", newline="\n") as stream:
                    stream.write(text)
        else:
            sys.stdout.write(text)
        return 0
    except (ValueError, OSError) as error:
        sys.stderr.write(f"invalid_input: {error}\n")
        return 2


def _resolve_output(output: Path) -> Path:
    if output.is_absolute() or ".." in output.parts:
        raise ValueError("output must be a relative path without parent traversal")
    root = Path.cwd().resolve()
    destination = (root / output).resolve()
    if not destination.is_relative_to(root):
        raise ValueError("output resolves outside the current project")
    return destination


def _json_scalar(value):
    """Convert NumPy scalar metrics from the upstream analyzer to JSON values."""
    if hasattr(value, "item"):
        return value.item()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def serialize_result(result: dict) -> str:
    """Return the stable full-result representation used by repeatability checks."""
    return json.dumps(result, ensure_ascii=False, separators=(",", ":"), sort_keys=True, default=_json_scalar)


if __name__ == "__main__":
    raise SystemExit(main())
