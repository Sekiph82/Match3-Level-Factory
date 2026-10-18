"""Deterministic, non-destructive reference-only color-swap mutations.

LFX-M06-003 source preparation. Pinned UltraGem scoregames/genlevels provide
candidate generation/ranking, not an owner-approved variant mutation API.
This isolated module NEVER simulates, validates wins, or publishes game levels.
"""
from __future__ import annotations

import copy
import random
from typing import Any

import leveldraft

MAX_VARIANTS = 8
MAX_ATTEMPTS_PER_VARIANT = 32


def propose_color_mutations(draft: dict[str, Any], *,
                            expected_source_sha256: str,
                            approval_reference: str,
                            seed: int,
                            count: int = 3) -> dict[str, Any]:
    """Create candidate color-position swaps without modifying source/metadata.

    An approval reference is trace metadata ONLY. It is not proof of the
    authority behind the decision and never authorizes a release.
    """
    leveldraft.validate(draft)
    source_hash = leveldraft.sha256(draft)
    if not isinstance(expected_source_sha256, str) or expected_source_sha256 != source_hash:
        raise ValueError("source SHA256 mismatch: no mutations allowed")
    if not isinstance(approval_reference, str) or not approval_reference.strip() or len(approval_reference) > 256:
        raise ValueError("an explicit approval record reference is required")
    if isinstance(seed, bool) or type(seed) is not int or not 0 <= seed <= 2**63 - 1:
        raise ValueError("seed must be a bounded non-negative integer")
    if isinstance(count, bool) or type(count) is not int or not 1 <= count <= MAX_VARIANTS:
        raise ValueError("count must be between 1 and 8")

    mutable = [index for index, cell in enumerate(draft["cells"])
               if cell["active"] and not cell["locked"] and cell["lockDurability"] == 0
               and cell["obstacleId"] is None and cell["specialId"] is None
               and isinstance(cell["contentId"], str)
               and cell["contentId"].startswith("ultragem.color.")]
    pairs = [(a, b) for i, a in enumerate(mutable) for b in mutable[i + 1:]
             if draft["cells"][a]["contentId"] != draft["cells"][b]["contentId"]]
    if not pairs:
        return _result(source_hash, approval_reference, seed, [], [{
            "code": "NO_MUTABLE_COLOR_PAIR",
            "details": "Existing special, obstacle and locked cells cannot be silently altered.",
        }])

    rng = random.Random(seed)
    generated = []
    rejected = []
    seen = {source_hash}
    attempts_budget = MAX_ATTEMPTS_PER_VARIANT * count
    # Bounded, seeded exploration, preserving original draft's references.
    for _ in range(attempts_budget):
        if len(generated) >= count:
            break
        a, b = pairs[rng.randrange(len(pairs))]
        candidate = copy.deepcopy(draft)
        candidate["cells"][a]["contentId"], candidate["cells"][b]["contentId"] = (
            candidate["cells"][b]["contentId"], candidate["cells"][a]["contentId"])
        # Keep identity trace distinct, but never upgrade status or channel.
        candidate["levelId"] = f"mutation.{seed}.{len(generated) + 1}"
        candidate["sourceKind"] = "UltraGemReferenceColorSwap"
        leveldraft.validate(candidate)
        digest = leveldraft.sha256(candidate)
        if digest in seen:
            continue
        seen.add(digest)
        generated.append({
            "ordinal": len(generated) + 1,
            "draft": candidate,
            "draftSha256": digest,
            "swappedCellCoordinates": [
                [draft["cells"][k]["layer"], draft["cells"][k]["row"], draft["cells"][k]["column"]]
                for k in (a, b)
            ],
            "validationStatus": "PROTOTYPE_ONLY",
            "engineStatus": "BLOCKED_ENG_M24",
        })
    if len(generated) < count:
        rejected.append({"code": "DIVERSITY_EXHAUSTED",
                         "requested": count, "produced": len(generated)})
    return _result(source_hash, approval_reference, seed, generated, rejected)


def _result(source_hash, approval_reference, seed, generated, rejected):
    return {
        "resultStatus": "REFERENCE_MUTATION_ONLY",
        "engineStatus": "BLOCKED_ENG_M24",
        "sourceDraftSha256": source_hash,
        "sourceApprovalReferenceUnverified": approval_reference,
        "ownerReviewRequired": True,
        "releaseAuthorized": False,
        "seed": seed,
        "generated": generated,
        "rejections": rejected,
    }
