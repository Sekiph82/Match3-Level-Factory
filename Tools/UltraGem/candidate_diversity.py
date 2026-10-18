"""Reference-only LevelDraft diversity analysis, independent of MATCH3_ENGINE.

LFX-M06-007/011 source preparation. This module never claims legal moves,
solvability, certified difficulty or publish eligibility.
UltraGem's pinned `genlevels.py` already weights journey variety; these
structure checks add a separate, fail-closed duplicate screen, not a resolver.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Iterable

import leveldraft

MAX_CATALOG_ITEMS = 512
DEFAULT_NEAR_DUPLICATE_THRESHOLD = 0.95
_RESULT_STATUS = "REFERENCE_STRUCTURAL_ONLY"
_ENGINE_STATUS = "BLOCKED_ENG_M24"


def _canonical_shape(draft: dict[str, Any]) -> tuple[tuple[int, int, int], tuple, tuple]:
    """Ignore named game/theme and color labels, but NEVER mechanics or goals."""
    leveldraft.validate(draft)
    dims = (draft["width"], draft["height"], draft["layers"])
    palette: dict[str, int] = {}
    tokens = []
    for cell in sorted(draft["cells"], key=lambda c: (c["layer"], c["row"], c["column"])):
        if not cell["active"]:
            tokens.append(("HOLE",))
            continue
        content = cell["contentId"]
        # Only donor-documented interchangeable *colors* can be renamed.
        # Do not guess that an unknown game piece ID is an ordinary color.
        if isinstance(content, str) and content.startswith("ultragem.color."):
            if content not in palette:
                palette[content] = len(palette)
            content_token = ("COLOR", palette[content])
        else:
            content_token = ("EXACT", content)
        tokens.append((
            content_token, cell["locked"], cell["lockDurability"],
            cell["obstacleId"], cell["obstacleDurability"], cell["specialId"],
        ))
    # Goal IDs are arbitrary instance identifiers. Goals' meaning/count is not.
    goals = tuple(sorted((g["targetId"], g["targetCount"]) for g in draft["goals"]))
    return dims, tuple(tokens), goals


def structural_fingerprint(draft: dict[str, Any]) -> str:
    """Stable, theme-independent prototype signature, NOT an Engine pack hash."""
    dimensions, cells, goals = _canonical_shape(draft)
    payload = json.dumps([dimensions, cells, goals], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compare_drafts(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Pure structural comparison, with exact mismatch reasons and no mutation."""
    left_dims, left_cells, left_goals = _canonical_shape(left)
    right_dims, right_cells, right_goals = _canonical_shape(right)
    if left_dims != right_dims:
        similarity = 0.0
        reason = "GEOMETRY_MISMATCH"
        changed_cells = None
    else:
        changed_cells = sum(a != b for a, b in zip(left_cells, right_cells))
        # Different goals must never be treated as exact duplicates.
        cell_fraction = 1 - changed_cells / len(left_cells)
        similarity = 0.85 * cell_fraction + 0.15 * float(left_goals == right_goals)
        reason = "EXACT_STRUCTURAL_DUPLICATE" if changed_cells == 0 and left_goals == right_goals else (
            "GOAL_DIFFERENCE" if changed_cells == 0 else "STRUCTURAL_DIFFERENCE"
        )
    return {
        "resultStatus": _RESULT_STATUS,
        "engineStatus": _ENGINE_STATUS,
        "sameProfile": left["gameProfileId"] == right["gameProfileId"],
        "similarity": round(similarity, 8),
        "changedCellCount": changed_cells,
        "goalSemanticsEqual": left_goals == right_goals,
        "reason": reason,
        "leftDraftSha256": leveldraft.sha256(left),
        "rightDraftSha256": leveldraft.sha256(right),
    }


def screen_catalog(items: Iterable[tuple[str, dict[str, Any]]],
                   *, threshold: float = DEFAULT_NEAR_DUPLICATE_THRESHOLD) -> dict[str, Any]:
    """Report ordered reference-only candidate triage with explicit owner review.

    No draft or input sequence is mutated. A candidate is compared with all
    previously accepted candidates. Deterministic bounded O(n²) comparisons;
    no hidden approval, deletion, or release side effect.
    """
    if isinstance(threshold, bool) or not isinstance(threshold, (float, int)) or not math.isfinite(threshold) or not 0 < threshold <= 1:
        raise ValueError("threshold must be finite and within (0, 1]")
    items = list(items)
    if len(items) > MAX_CATALOG_ITEMS:
        raise ValueError("catalog exceeds reference comparison budget")
    accepted: list[tuple[str, dict[str, Any]]] = []
    rejected: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for candidate_id, draft in items:
        if not isinstance(candidate_id, str) or not candidate_id or candidate_id in seen_ids:
            raise ValueError("candidate IDs must be nonempty unique strings")
        seen_ids.add(candidate_id)
        # Validate EVERY candidate, even those rejected as duplicates.
        leveldraft.validate(draft)
        nearest = None
        for accepted_id, prior in accepted:
            report = compare_drafts(draft, prior)
            if nearest is None or report["similarity"] > nearest["similarity"]:
                nearest = {"candidateId": accepted_id, **report}
        if nearest and nearest["similarity"] >= threshold:
            rejected.append({
                "candidateId": candidate_id,
                "duplicateOf": nearest["candidateId"],
                "similarity": nearest["similarity"],
                "reason": "REFERENCE_NEAR_DUPLICATE",
                "draftSha256": leveldraft.sha256(draft),
            })
        else:
            accepted.append((candidate_id, draft))
    return {
        "resultStatus": _RESULT_STATUS,
        "engineStatus": _ENGINE_STATUS,
        "releaseAuthorized": False,
        "threshold": threshold,
        "accepted": [{"candidateId": key, "draftSha256": leveldraft.sha256(value),
                      "structuralFingerprint": structural_fingerprint(value)} for key, value in accepted],
        "rejected": rejected,
        "ownerReviewRequired": True,
    }
