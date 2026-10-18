"""Transparent donor-candidate explanation sheets (LFX-M06-012 partial).

The imported UltraGem engine exposes FOUR historical policies, not the FIVE
Engine-specified player personas. Missing fifth persona must be explicit and
never interpreted as simulated or accepted production difficulty.
"""
from __future__ import annotations

from typing import Any

import leveldraft

DONOR_POLICIES=("worst","random","best","smart")
REQUIRED_PRODUCTION_PERSONAS=("Beginner","Casual","Strategic","Expert","Random")
MAX_RECOMMENDATIONS=128


def explain_reference_batch(result: dict[str, Any]) -> dict[str, Any]:
    if (not isinstance(result,dict) or result.get("resultStatus")!="REFERENCE_ONLY_UNVERIFIED"
        or result.get("engineStatus")!="BLOCKED_ENG_M24"):
        raise ValueError("not a legal reference-only pipeline result")
    config=result.get("configuration")
    candidates=result.get("drafts")
    if not isinstance(config,dict) or not isinstance(candidates,list) or len(candidates)>MAX_RECOMMENDATIONS:
        raise ValueError("invalid or oversized candidate batch")
    seed=config.get("seed",result.get("seed"))
    explanations=[]
    for index,item in enumerate(candidates):
        if not isinstance(item,dict) or not isinstance(item.get("draft"),dict):
            raise ValueError("invalid candidate entry")
        draft=item["draft"]
        leveldraft.validate(draft)
        if item.get("draftSha256")!=leveldraft.sha256(draft):
            raise ValueError("candidate integrity mismatch")
        compatibility=item.get("profileCompatibility")
        if (not isinstance(compatibility,dict)
            or compatibility.get("engineStatus")!="BLOCKED_ENG_M24"
            or compatibility.get("draftMutationPerformed") is not False):
            raise ValueError("missing fail-closed profile compatibility receipt")
        heuristic=item.get("difficultyHypothesis")
        if heuristic is not None and (type(heuristic) not in (int,float) or not 0<=heuristic<=100):
            raise ValueError("unbounded donor heuristic")
        explanations.append({
            "ordinal":item.get("ordinal",index+1),
            "sourceDraftSha256":item["draftSha256"],
            "sourceSeed":draft["seed"],
            "profileId":draft["gameProfileId"],
            "goalTargets":[{"id":g["targetId"],"count":g["targetCount"]} for g in draft["goals"]],
            "donorRanking":item.get("rankingStatus","UNVERIFIED"),
            "donorDifficultyHypothesis":heuristic,
            "localCapabilityDecision":compatibility.get("localPolicyStatus","NOT_CHECKED"),
            "donorPoliciesAvailable":list(DONOR_POLICIES),
            "productionPersonasNotEvaluated":list(REQUIRED_PRODUCTION_PERSONAS),
            "reason":"UltraGem donor scoring is reference-only; requires ENG-M24 authoritative replay and five-persona evaluation.",
            "productionCandidateApproved":False,
        })
    return {
        "resultStatus":"REFERENCE_BATCH_EXPLANATION_ONLY",
        "engineStatus":"BLOCKED_ENG_M24",
        "generatorSeed":result.get("seed"),
        "parameterBounds":dict(config),
        "candidateCount":len(explanations),
        "rankingExplanations":explanations,
        "referenceRejectReasons":result.get("rejectedCandidates",[]),
        "fivePersonaMetricsAvailable":False,
        "ownerReviewRequired":True,
        "releaseAuthorized":False,
    }
