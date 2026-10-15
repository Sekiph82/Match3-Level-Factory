"""Python 3 callable form of UltraGem's score-conditioned goal and journey ranking."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy
from scipy.stats.mstats import mquantiles

from scoregames import STAT_NAMES

SCORES_PREFERENCES = (
    ("nunlocked", "combo_22", "combo_42", "combo_44", "combo_52", "combo_54", "combo_55"),
    ("nstripe", "nbomb", "nzapper"),
    ("score",),
)
SCORE_GROUP = {name: group for group, names in enumerate(SCORES_PREFERENCES) for name in names}


def rank_levels(candidates: list[dict], *, seed: int, max_levels: int = 100) -> list[dict]:
    """Preserve the donor's best/random/smart quantile thresholds and journey weighting."""
    if not 0 <= seed <= 2**31 - 1:
        raise ValueError("seed must be between 0 and 2^31-1")
    if not 1 <= max_levels <= 1000:
        raise ValueError("max_levels must be between 1 and 1000")
    rng = numpy.random.RandomState(seed)
    score_index = {name: index for index, name in enumerate(STAT_NAMES)}
    eligible = []
    rejected = []

    for candidate in candidates:
        stats = candidate.get("statistics", {})
        if not all(name in stats and stats[name].get("steps") for name in ("best", "random", "smart")):
            rejected.append({"seed": candidate.get("seed"), "reason": "required policy samples are missing"})
            continue
        if any(len(stats[name]["steps"]) < 2 for name in ("best", "random", "smart")):
            rejected.append({"seed": candidate.get("seed"), "reason": "at least two runs per policy are required for a difficulty estimate"})
            continue
        try:
            best = numpy.asarray(stats["best"]["steps"], dtype=numpy.int64)
            random = numpy.asarray(stats["random"]["steps"], dtype=numpy.int64)
            smart = numpy.asarray(stats["smart"]["steps"], dtype=numpy.int64)
            if best.ndim != 3 or random.ndim != 3 or smart.ndim != 3 or best.shape[1:] != random.shape[1:] or best.shape[1:] != smart.shape[1:]:
                raise ValueError("policy step arrays have inconsistent shapes")
            def policy_quantiles(samples):
                # Match UltraGem's original (runs, steps * statistics) layout;
                # SciPy mquantiles accepts at most two dimensions.
                run_count, step_count, statistic_count = samples.shape
                if run_count == 1:
                    # mquantiles' default outer plotting positions have a
                    # missing-value fill for a single sample; represent the
                    # observed value as both estimates without a NaN cast.
                    return numpy.repeat(samples, 2, axis=0)
                quantiles = mquantiles(
                    samples.reshape(run_count, step_count * statistic_count),
                    prob=[0.5, 0.95], axis=0,
                )
                # SciPy returns a masked array; fill masked quantiles with zero
                # before integer conversion to avoid NumPy's NaN fill cast.
                quantiles = numpy.asarray(numpy.ma.filled(quantiles, 0), dtype=numpy.int64)
                return quantiles.reshape(2, step_count, statistic_count)

            best_q = policy_quantiles(best)
            random_q = policy_quantiles(random)
            smart_q = policy_quantiles(smart)
            randomness = best_q[1] - best_q[0]
            intelligence = smart_q[0] - best_q[0]
            goal_values = smart_q[0]
            steps = numpy.arange(1, len(goal_values) + 1)
            candidate_rows = candidate["initialBoard"]["rows"]
            candidate_cols = candidate["initialBoard"]["columns"]
            candidate_colors = int(candidate.get("colors", max(
                (cell["color"] for cell in candidate["initialBoard"]["cells"]), default=0
            )))
            chosen = None
            for group_names in SCORES_PREFERENCES:
                goal_indices = [score_index[name] for name in group_names]
                rng.shuffle(goal_indices)
                for goal_index in goal_indices:
                    goal = goal_values[:, goal_index]
                    mask = (goal > 0) & (steps >= 10) & (intelligence[:, goal_index] > randomness[:, goal_index] * 0.75)
                    mask_second = mask & (goal > 1)
                    if int(mask.sum()) <= 1:
                        continue
                    selected = numpy.where(mask_second)[0][1] if int(mask_second.sum()) > 1 else numpy.where(mask)[0][1]
                    target = int(goal[selected])
                    reference_uncertainty = float(random_q[1, selected, goal_index])
                    smart_value = max(float(smart_q[0, selected, goal_index]), 1.0)
                    difficulty = round((reference_uncertainty / smart_value) * 20) / 20
                    chosen = {
                        "candidateSeed": candidate["seed"],
                        "candidateIndex": candidate.get("candidateIndex", 0),
                        "rows": candidate_rows,
                        "columns": candidate_cols,
                        "colors": candidate_colors,
                        "moveBudget": int(selected + 1),
                        "goalId": STAT_NAMES[goal_index],
                        "goalIndex": goal_index,
                        "targetCount": target,
                        "difficultyHypothesis": difficulty,
                        "randomnessToGoalRatio": reference_uncertainty / smart_value,
                        "intelligenceToRandomness": float(intelligence[selected, goal_index]) / max(float(randomness[selected, goal_index]), 1.0),
                    }
                    break
                if chosen:
                    break
            if chosen:
                eligible.append(chosen)
            else:
                rejected.append({"seed": candidate.get("seed"), "reason": "no score-conditioned goal met the pinned heuristic"})
        except (KeyError, TypeError, ValueError, IndexError) as error:
            rejected.append({"seed": candidate.get("seed"), "reason": f"invalid statistics: {error}"})

    result = []
    previous_goal = 0
    previous_group = -1
    previous_colors = 0
    while eligible and len(result) < max_levels:
        weights = numpy.asarray([
            1.0 / (0.05 + item["difficultyHypothesis"]
                   + (item["goalIndex"] == previous_goal) * 1
                   + (SCORE_GROUP.get(item["goalId"], -1) == previous_group) * 10
                   + (item["colors"] == previous_colors) * 2)
            for item in eligible
        ], dtype=numpy.float64)
        total = float(weights.sum())
        if not numpy.isfinite(total) or total <= 0:
            raise ValueError("journey weights are invalid")
        weights /= total
        index = int(rng.choice(numpy.arange(len(eligible)), p=weights))
        item = eligible.pop(index)
        item["ordinal"] = len(result) + 1
        result.append(item)
        previous_goal = item["goalIndex"]
        previous_group = SCORE_GROUP.get(item["goalId"], -1)
        previous_colors = item["colors"]

    rank_levels.last_rejections = rejected
    return result


rank_levels.last_rejections = []


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Rank UltraGem policy statistics into a reference-only journey.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--max-levels", type=int, default=100)
    args = parser.parse_args(argv)
    data = json.loads(args.input.read_text(encoding="utf-8"))
    levels = rank_levels(data["candidates"], seed=args.seed, max_levels=args.max_levels)
    print(json.dumps({"levels": levels, "rejected": rank_levels.last_rejections}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
