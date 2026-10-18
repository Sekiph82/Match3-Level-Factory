"""Local optional Time Attack/Endless authoring proposals (LFX-M06-013).

The current LevelDraft v1 has a timedMode flag but NO Endless gameplay
contract. Endless must stay a metadata-only proposal. Neither mode may
enter a game or change progression/economy before ENG-M24 acceptance.
"""
from __future__ import annotations

import copy
from typing import Any

import leveldraft

_MODES = {"TIME_ATTACK", "ENDLESS"}


def propose_optional_mode(source: dict[str, Any], *, expected_sha256: str, mode: str,
                          owner_request_reference: str, age_review_reference: str | None = None,
                          time_limit_seconds: int | None = None) -> dict[str, Any]:
    leveldraft.validate(source)
    digest = leveldraft.sha256(source)
    if digest != expected_sha256:
        raise ValueError("source draft SHA mismatch")
    if mode not in _MODES:
        raise ValueError("unsupported optional mode")
    if not isinstance(owner_request_reference,str) or not 5<=len(owner_request_reference.strip())<=256:
        raise ValueError("owner request reference is required")
    if source["gameProfileId"]=="Wonder_Pop" and (
        not isinstance(age_review_reference,str) or not 5<=len(age_review_reference.strip())<=256):
        raise ValueError("Wonder_Pop pressure modes require explicit owner age review")
    if age_review_reference is not None and (
        not isinstance(age_review_reference,str) or not 5<=len(age_review_reference.strip())<=256):
        raise ValueError("age review reference invalid")
    if mode=="TIME_ATTACK":
        if type(time_limit_seconds) is not int or not 10<=time_limit_seconds<=3600:
            raise ValueError("Time Attack requires 10..3600 seconds")
        if source["timedMode"]:
            raise ValueError("source is already timed")
        candidate=copy.deepcopy(source)
        candidate["timedMode"]=True
        candidate["timeLimitSeconds"]=time_limit_seconds
        candidate["sourceKind"]="OptionalTimeAttackReference"
        leveldraft.validate(candidate)
        proposal_sha=leveldraft.sha256(candidate)
        # Important: Time Attack has a representable authoring schema, NOT a
        # certified game mode or runtime replay.
        authoring_draft=candidate
    else:
        if time_limit_seconds is not None:
            raise ValueError("Endless has no time limit in v1")
        proposal_sha=None
        authoring_draft=None
    return {
        "resultStatus":"OPTIONAL_MODE_AUTHORING_PROPOSAL_ONLY",
        "engineStatus":"BLOCKED_ENG_M24",
        "mode":mode,
        "sourceDraftSha256":digest,
        "proposalDraftSha256":proposal_sha,
        "authoringDraft":authoring_draft,
        "levelDraftV1CanRepresentMode": mode=="TIME_ATTACK",
        "requiresEngineRuntimeContract":True,
        "ownerRequestReferenceUnverified":owner_request_reference.strip(),
        "ageReviewReferenceUnverified":age_review_reference.strip() if age_review_reference else None,
        "progressionRewardsModified":False,
        "economyModified":False,
        "productionAuthorized":False,
    }
