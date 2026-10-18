"""Reference-only candidate triage, not game difficulty or a fun score.

LFX-M06-008. Ranks human inspection priority from explicit structural signals.
No legal-move simulation, win likelihood, player enjoyment estimate, or
production approval is inferred from UltraGem observations.
"""
from __future__ import annotations

import math
from typing import Any

import leveldraft
from reference_features import extract_reference_features

MAX_BATCH = 64
_ALLOWED_STATUS = {"RANKED_REFERENCE_HEURISTIC", "NOT_RANKED_BY_PINNED_HEURISTIC"}


def rank_reference_candidates(batch: dict[str, Any]) -> dict[str, Any]:
    """Pure, deterministic order. Lower triageRisk = earlier to review.

    Sorting rules: locally representable ahead of rejected, ranked donor
    ahead of unranked, lower observable complexity ahead of higher. These
    are REVIEW PRIORITIES only, not playable level ranking or difficulty.
    """
    if (not isinstance(batch, dict)
        or batch.get("resultStatus") != "REFERENCE_ONLY_UNVERIFIED"
        or batch.get("engineStatus") != "BLOCKED_ENG_M24"):
        raise ValueError("the result must be an explicit Engine-blocked UltraGem batch")
    drafts = batch.get("drafts")
    if not isinstance(drafts, list) or len(drafts) > MAX_BATCH:
        raise ValueError("candidate batch size must be <=64")
    ranked = []
    seen = set()
    for index, record in enumerate(drafts):
        if not isinstance(record, dict) or not isinstance(record.get("draft"), dict):
            raise ValueError("candidate record is invalid")
        draft = record["draft"]
        leveldraft.validate(draft)
        digest = leveldraft.sha256(draft)
        if record.get("draftSha256") != digest or digest in seen:
            raise ValueError("candidate digest mismatch or exact duplicate")
        seen.add(digest)
        status = record.get("rankingStatus")
        if status not in _ALLOWED_STATUS:
            raise ValueError("unrecognized donor ranking result")
        hypothesis = record.get("difficultyHypothesis")
        if hypothesis is not None and (type(hypothesis) not in (int, float)
                                       or not math.isfinite(hypothesis)
                                       or not 0 <= hypothesis <= 100):
            raise ValueError("donor hypothesis must be finite and nonnegative")
        if status != "RANKED_REFERENCE_HEURISTIC" and hypothesis is not None:
            raise ValueError("unranked drafts cannot have donor difficulty hypotheses")
        p = record.get("profileCompatibility")
        if not isinstance(p, dict) or p.get("engineStatus") != "BLOCKED_ENG_M24" or p.get("draftMutationPerformed") is not False:
            raise ValueError("missing profile authority quarantine")
        accepted = p.get("localPolicyStatus") == "ACCEPTED_BY_BUILDER_POLICY"
        if p.get("localPolicyStatus") not in ("ACCEPTED_BY_BUILDER_POLICY", "REJECTED_BY_BUILDER_POLICY"):
            raise ValueError("unknown local policy status")
        features = extract_reference_features(draft)
        active = max(1, features["activeCellCount"])
        # Counts identify items to inspect, they do NOT estimate difficulty.
        complexity = (features["lockedCellCount"] + sum(features["specialKinds"].values())
                      + sum(features["obstacleKinds"].values())) / active
        risk = round(min(1.0, complexity), 8)
        reasons = []
        if not accepted:
            reasons.append("REJECTED_BY_LOCAL_PROFILE_POLICY")
        if status != "RANKED_REFERENCE_HEURISTIC":
            reasons.append("NOT_RANKED_BY_PINNED_DONOR_HEURISTIC")
        if complexity > 0:
            reasons.append("HAS_LOCKED_SPECIAL_OR_OBSTACLE_CELLS")
        if not reasons:
            reasons.append("NO_STATIC_REVIEW_WARNINGS")
        ranked.append({
            "originalIndex": index,
            "draftSha256": digest,
            "profileId": draft["gameProfileId"],
            "donorRankingStatus": status,
            "donorDifficultyHypothesis": hypothesis,
            "localPolicyStatus": p["localPolicyStatus"],
            "staticTriageRisk": risk,
            "reviewReasons": reasons,
            "productionDifficulty": None,
            "productionSolvable": None,
            "approvalStatus": "OWNER_REVIEW_REQUIRED",
        })
    ranked.sort(key=lambda x: (
        x["localPolicyStatus"] != "ACCEPTED_BY_BUILDER_POLICY",
        x["donorRankingStatus"] != "RANKED_REFERENCE_HEURISTIC",
        x["staticTriageRisk"], x["draftSha256"],
    ))
    for i, record in enumerate(ranked):
        record["reviewOrder"] = i + 1
    return {
        "resultStatus": "REFERENCE_REVIEW_QUEUE_ONLY",
        "engineStatus": "BLOCKED_ENG_M24",
        "releaseAuthorized": False,
        "rankingIsGameplayDifficulty": False,
        "candidateCount": len(ranked),
        "orderedForHumanReview": ranked,
    }
