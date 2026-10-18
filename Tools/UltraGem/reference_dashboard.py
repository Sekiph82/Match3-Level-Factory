"""Deterministic reference-only batch score dashboards (LFX-M05-007).

A consumer-facing difficulty or win-rate claim requires MATCH3_ENGINE. This
analyzer only summarizes explicitly labelled donor/prototype observations and
never supplies a final difficulty tier. Pure functions, no filesystem writes.
"""
from __future__ import annotations

import csv
import io
import math
from collections import Counter
from typing import Any

MAX_ROWS = 4096
VALID_OUTCOMES = frozenset({"REFERENCE_COMPLETED", "REFERENCE_FAILED", "REFERENCE_UNKNOWN"})
COLUMNS = ("seed", "persona", "outcome", "movesUsed", "score")


def _validate(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(records, list) or len(records) > MAX_ROWS:
        raise ValueError("records must be a bounded list")
    result = []
    for index, row in enumerate(records):
        if not isinstance(row, dict) or set(row) != set(COLUMNS):
            raise ValueError(f"row {index} has missing or unsupported fields")
        seed, persona, outcome, moves, score = (row[field] for field in COLUMNS)
        if type(seed) is not int or not 0 <= seed < 2**63:
            raise ValueError(f"row {index}: invalid seed")
        if not isinstance(persona, str) or not 1 <= len(persona) <= 48 or not persona.replace("_", "").isalnum():
            raise ValueError(f"row {index}: invalid persona")
        if outcome not in VALID_OUTCOMES:
            raise ValueError(f"row {index}: invalid reference outcome")
        if type(moves) is not int or not 0 <= moves <= 10000:
            raise ValueError(f"row {index}: invalid moves")
        if type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 10**12:
            raise ValueError(f"row {index}: invalid score")
        result.append(dict(row))
    return result


def summarize_reference_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Returns exact observed distributions; UNKNOWN stays in the denominator."""
    rows = _validate(records)
    outcomes = Counter(row["outcome"] for row in rows)
    sorted_scores = sorted(row["score"] for row in rows)
    scores = {"0": 0, "1-999": 0, "1000-9999": 0, "10000+": 0}
    for value in sorted_scores:
        key = "0" if value == 0 else "1-999" if value < 1000 else "1000-9999" if value < 10000 else "10000+"
        scores[key] += 1
    by_persona = {}
    for persona in sorted({r["persona"] for r in rows}):
        subset = [r for r in rows if r["persona"] == persona]
        by_persona[persona] = {
            "samples": len(subset),
            "outcomes": {outcome: sum(r["outcome"] == outcome for r in subset)
                         for outcome in sorted(VALID_OUTCOMES)},
            "meanMovesObserved": round(sum(r["movesUsed"] for r in subset) / len(subset), 6),
        }
    return {
        "resultStatus": "REFERENCE_DASHBOARD_ONLY",
        "engineStatus": "BLOCKED_ENG_M24",
        "claimDifficultyOrWinProbability": False,
        "sampleCount": len(rows),
        "outcomes": {name: outcomes[name] for name in sorted(VALID_OUTCOMES)},
        "scoreHistogram": scores,
        "medianObservedScore": (sorted_scores[(len(rows)-1)//2] + sorted_scores[len(rows)//2]) / 2 if rows else None,
        "byPersona": by_persona,
        "explanation": "Descriptive donor observations only; these are not certified gameplay wins, success probabilities or difficulty.",
    }


def reference_csv(records: list[dict[str, Any]]) -> str:
    """Stable RFC4180 CSV; seed-sorted output prevents incidental row-order drift."""
    rows = _validate(records)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(sorted(rows, key=lambda r: (r["seed"], r["persona"], r["outcome"], r["movesUsed"], r["score"])))
    return stream.getvalue()
