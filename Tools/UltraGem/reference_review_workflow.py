"""Integrated, deterministic, reference-only owner review dossier.

Existing tasks: LFX-M06-007/008/009/011/012. This NEVER certifies
playability, gameplay difficulty, Engine parity, or publication.
"""
from __future__ import annotations

from typing import Any

import leveldraft
from profile_compatibility import diagnose_profile_compatibility
from reference_analysis import analyze_ranked_output
from candidate_diversity import screen_catalog
from candidate_ranking import rank_reference_candidates
from reference_batch_explanation import explain_reference_batch
from candidate_review import new_review_ticket

MAX_BATCH = 64


def build_reference_review_dossier(batch: dict[str, Any], *, threshold: float = 0.95) -> dict[str, Any]:
    """Validate all inputs before issuing review tickets; never mutate drafts.

    Canonical profile receipts are independently re-created from the draft
    itself, preventing an untrusted batch from claiming supported mechanics.
    """
    if (not isinstance(batch, dict)
            or batch.get("resultStatus") != "REFERENCE_ONLY_UNVERIFIED"
            or batch.get("engineStatus") != "BLOCKED_ENG_M24"):
        raise ValueError("only quarantined UltraGem reference batches are supported")
    entries = batch.get("drafts")
    if not isinstance(entries, list) or len(entries) > MAX_BATCH:
        raise ValueError("reference review batches limited to 64 candidates")
    config = batch.get("configuration")
    if not isinstance(config, dict):
        raise ValueError("configuration is required")
    declared_profile = config.get("gameProfileId")
    if declared_profile is not None and not isinstance(declared_profile, str):
        raise ValueError("invalid declared profile")
    for item in entries:
        if not isinstance(item, dict) or not isinstance(item.get("draft"), dict):
            raise ValueError("missing reference draft")
        draft = item["draft"]
        leveldraft.validate(draft)
        if item.get("draftSha256") != leveldraft.sha256(draft):
            raise ValueError("stored digest diverges from actual draft")
        if declared_profile is not None and draft["gameProfileId"] != declared_profile:
            raise ValueError("batch contains foreign game profile")
        if item.get("profileCompatibility") != diagnose_profile_compatibility(draft):
            raise ValueError("unverified or forged local capability receipt")
    static = analyze_ranked_output(batch, threshold=threshold)
    ranked = rank_reference_candidates(batch)
    explained = explain_reference_batch(batch)
    ids = [f"draft.{index:04d}" for index in range(len(entries))]
    catalog = screen_catalog(
        zip(ids, (entry["draft"] for entry in entries)), threshold=threshold
    )
    digest_to_index = {entry["draftSha256"]: i for i, entry in enumerate(entries)}
    ordered = []
    for record in ranked["orderedForHumanReview"]:
        index = digest_to_index[record["draftSha256"]]
        draft = entries[index]["draft"]
        ticket = new_review_ticket(
            candidate_sha256=record["draftSha256"],
            source_sha256=record["draftSha256"],
            generator_seed=draft["seed"],
        )
        ordered.append({
            "candidateId": ids[index],
            "draftSha256": record["draftSha256"],
            "reviewRank": record["reviewOrder"],
            "riskReasons": record["reviewReasons"],
            "profileStatus": record["localPolicyStatus"],
            "reviewTicket": ticket,
            "productionReady": False,
        })
    return {
        "resultStatus": "INTEGRATED_REFERENCE_REVIEW_ONLY",
        "engineStatus": "BLOCKED_ENG_M24",
        "releaseAuthorized": False,
        "signatureOrSignerPresent": False,
        "sourceRevision": batch.get("sourceRevision"),
        "candidateCount": len(entries),
        "deduplication": catalog,
        "statistics": static,
        "donorExplanations": explained,
        "ownerReviewQueue": ordered,
        "engineBotPersonasEvaluated": [],
        "productionDifficultyValidated": False,
    }
