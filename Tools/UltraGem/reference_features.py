"""Fail-closed, Engine-independent feature extraction for candidate authoring.

LFX-M05-001 local preparation. Board area or blocker counts are NOT a
difficulty grade. UltraGem's original goal/difficulty heuristic remains in the
pinned donor adapter; only the accepted MATCH3_ENGINE may certify gameplay.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

import leveldraft


def extract_reference_features(draft: dict[str, Any]) -> dict[str, Any]:
    """Compute interpretable static quantities without simulating any move."""
    leveldraft.validate(draft)
    cells = draft["cells"]
    active = [cell for cell in cells if cell["active"]]
    holes = len(cells) - len(active)
    colors = Counter(
        cell["contentId"] for cell in active
        if isinstance(cell["contentId"], str)
        and cell["contentId"].startswith("ultragem.color.")
    )
    obstacles = Counter(cell["obstacleId"] for cell in active if cell["obstacleId"])
    specials = Counter(cell["specialId"] for cell in active if cell["specialId"])
    goals = [{"targetId": goal["targetId"], "targetCount": goal["targetCount"]}
             for goal in sorted(draft["goals"], key=lambda g: (g["targetId"], g["goalId"]))]
    budget = draft["moveBudget"]
    return {
        "resultStatus": "REFERENCE_STATIC_FEATURES_ONLY",
        "engineStatus": "BLOCKED_ENG_M24",
        "notDifficultyOrSolvability": True,
        "draftSha256": leveldraft.sha256(draft),
        "dimensions": {"rows": draft["height"], "columns": draft["width"], "layers": draft["layers"]},
        "cellCount": len(cells),
        "activeCellCount": len(active),
        "holeCount": holes,
        "lockedCellCount": sum(bool(c["locked"]) for c in active),
        "lockDurabilityTotal": sum(c["lockDurability"] for c in active),
        "obstacleDurabilityTotal": sum(c["obstacleDurability"] for c in active),
        "obstacleKinds": dict(sorted(obstacles.items())),
        "specialKinds": dict(sorted(specials.items())),
        "observedDonorColorKinds": len(colors),
        "observedDonorColorCounts": dict(sorted(colors.items())),
        "moveBudget": budget,
        "timedMode": draft["timedMode"],
        "timeLimitSeconds": draft["timeLimitSeconds"],
        "goals": goals,
        "goalPressureReferenceOnly": [
            {"targetId": goal["targetId"],
             "targetCountPerBudgetMove": round(goal["targetCount"] / budget, 6)}
            for goal in goals
        ],
    }
