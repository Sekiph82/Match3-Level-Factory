"""Non-personalized experiment *configuration proposal* (LFX-M12-004).

No user identifiers, cookies, behavioral targeting, cohort assignment,
premium grants, player bucketing or remote publication. The actual experiment
allocator belongs to the future independently audited Engine/liveops backend.
"""
from __future__ import annotations

import re
from typing import Any

from theme_contract import PROFILES

MAX_VARIANTS=8


def propose_experiment(*, game_id: str, experiment_id: str,
                       variants: list[dict[str,Any]], holdout_percent: int,
                       audience_mode: str, rollback_reference: str) -> dict[str,Any]:
    if game_id not in PROFILES:
        raise ValueError("unknown game ID")
    if not isinstance(experiment_id,str) or re.fullmatch("[A-Za-z][A-Za-z0-9._-]{2,79}",experiment_id) is None:
        raise ValueError("invalid experiment ID")
    if not isinstance(variants,list) or not 2<=len(variants)<=MAX_VARIANTS:
        raise ValueError("experiments require 2..8 variants")
    if type(holdout_percent) is not int or not 1<=holdout_percent<=50:
        raise ValueError("holdout must be 1..50 percent")
    if audience_mode not in {"NON_PERSONALIZED_OPT_IN_ONLY","BEHAVIORAL_TARGETING"}:
        raise ValueError("unknown audience mode")
    if audience_mode!="NON_PERSONALIZED_OPT_IN_ONLY":
        raise ValueError("behavioral targeting is disabled in all unverified-age profiles")
    if not isinstance(rollback_reference,str) or not 5<=len(rollback_reference.strip())<=256:
        raise ValueError("traceable rollback reference required")
    seen=set()
    weighted=0
    records=[]
    for item in variants:
        if not isinstance(item,dict) or set(item)!={"variantId","weightPercent","configReference"}:
            raise ValueError("unknown/missing variant keys")
        variant=item["variantId"]
        weight=item["weightPercent"]
        source=item["configReference"]
        if not isinstance(variant,str) or re.fullmatch("[A-Za-z][A-Za-z0-9._-]{1,39}",variant) is None or variant in seen:
            raise ValueError("invalid or duplicate variant ID")
        seen.add(variant)
        if type(weight) is not int or not 1<=weight<=99:
            raise ValueError("invalid weight")
        weighted+=weight
        if not isinstance(source,str) or not 5<=len(source)<=256:
            raise ValueError("variant source reference required")
        records.append(dict(item))
    if weighted+holdout_percent!=100:
        raise ValueError("weights plus holdout must total 100%")
    return {
        "schemaVersion":1,
        "resultStatus":"EXPERIMENT_CONFIG_PROPOSAL_ONLY",
        "engineStatus":"BLOCKED_ENG_M24",
        "gameProfileId":game_id,
        "experimentId":experiment_id,
        "audienceMode":audience_mode,
        "privacyPolicy":"NO_CLIENT_OR_USER_IDENTIFIERS",
        "variants":sorted(records,key=lambda x:x["variantId"]),
        "holdoutPercent":holdout_percent,
        "rollbackReferenceUnverified":rollback_reference.strip(),
        "stableAllocatorImplemented":False,
        "requiresConsentBeforeEligibility":True,
        "personalDataProcessed":False,
        "rewardOrClaimChanged":False,
        "remoteDeploymentAuthorized":False,
    }
