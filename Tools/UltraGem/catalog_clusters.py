"""Bounded, whole-catalog reference structural clustering and owner exception log.

Existing LFX-M06-011. Ignores theme labels when comparing structure but
preserves goal, holes, locks, blockers, specials and exact board geometry.
This module does not alter gameplay, reject/publish a level, or certify
any release; every override remains unverified until owner authority/audit.
"""
from __future__ import annotations

import math
import re
from typing import Any, Iterable

import leveldraft
from candidate_diversity import compare_drafts, MAX_CATALOG_ITEMS


def cluster_reference_catalog(items: Iterable[tuple[str, dict[str, Any]]],
                              *, threshold: float = 0.95) -> dict[str, Any]:
    if (type(threshold) not in (int, float) or not math.isfinite(threshold)
            or not 0 < threshold <= 1):
        raise ValueError("threshold must be a finite number in (0,1]")
    originals = list(items)
    if len(originals) > MAX_CATALOG_ITEMS:
        raise ValueError("reference catalog exceeds 64 drafts")
    observed = {}
    for candidate_id, draft in originals:
        if not isinstance(candidate_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", candidate_id):
            raise ValueError("invalid stable candidate identity")
        if candidate_id in observed:
            raise ValueError("duplicate candidate identity")
        leveldraft.validate(draft)
        observed[candidate_id] = draft
    ids = sorted(observed)
    parents = list(range(len(ids)))

    def root(index):
        while parents[index] != index:
            index = parents[index]
        return index

    similarities = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            comparison = compare_drafts(observed[ids[i]], observed[ids[j]])
            score = comparison["similarity"]
            if score >= threshold:
                # Transitive clusters collect even chain-linked candidates.
                a, b = root(i), root(j)
                parents[max(a, b)] = min(a, b)
                similarities.append({
                    "leftId": ids[i], "rightId": ids[j],
                    "similarity": score, "reason": comparison["reason"],
                    "crossProfile": not comparison["sameProfile"],
                })
    clusters = {}
    for index, candidate_id in enumerate(ids):
        clusters.setdefault(root(index), []).append({
            "candidateId": candidate_id,
            "draftSha256": leveldraft.sha256(observed[candidate_id]),
            "gameProfileId": observed[candidate_id]["gameProfileId"],
        })
    return {
        "resultStatus": "REFERENCE_CLUSTERS_ONLY",
        "engineStatus": "BLOCKED_ENG_M24",
        "threshold": threshold,
        "inputCount": len(ids),
        "clusters": [clusters[k] for k in sorted(clusters)],
        "similarPairs": similarities,
        "humanReviewRequired": True,
        "releaseAuthorized": False,
    }


def propose_duplicate_exception(cluster_report: dict[str, Any], *,
                                candidate_id: str, expected_sha256: str,
                                owner_reference: str, rationale: str) -> dict[str, Any]:
    if (not isinstance(cluster_report, dict)
            or cluster_report.get("resultStatus") != "REFERENCE_CLUSTERS_ONLY"
            or cluster_report.get("engineStatus") != "BLOCKED_ENG_M24"
            or cluster_report.get("releaseAuthorized") is not False):
        raise ValueError("trusted reference cluster report is required")
    if not isinstance(expected_sha256, str) or not re.fullmatch("[0-9a-f]{64}", expected_sha256):
        raise ValueError("exact candidate SHA256 required")
    if not isinstance(owner_reference, str) or not 5 <= len(owner_reference.strip()) <= 256:
        raise ValueError("traceable owner reference required")
    if not isinstance(rationale, str) or not 20 <= len(rationale.strip()) <= 1000:
        raise ValueError("exception requires meaningful rationale")
    matches = [c for cluster in cluster_report.get("clusters", []) for c in cluster
               if c.get("candidateId") == candidate_id]
    if len(matches) != 1 or matches[0].get("draftSha256") != expected_sha256:
        raise ValueError("stale, missing or ambiguous candidate identity")
    if not any(pair["leftId"] == candidate_id or pair["rightId"] == candidate_id
               for pair in cluster_report.get("similarPairs", [])):
        raise ValueError("no duplicate reason: exception not applicable")
    return {
        "resultStatus": "REFERENCE_DUPLICATE_OVERRIDE_REQUEST_ONLY",
        "engineStatus": "BLOCKED_ENG_M24",
        "candidateId": candidate_id,
        "candidateSha256": expected_sha256,
        "ownerReferenceUnverified": owner_reference.strip(),
        "rationale": rationale.strip(),
        "originalSimilarityFlagsPreserved": True,
        "reviewerAuthenticated": False,
        "releaseAuthorized": False,
    }
