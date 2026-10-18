"""Fail-closed five-title age/liveops authoring guard, NOT an ad SDK.

LFX-M12-005. Wonder_Pop is treated as child-directed 5-12. Other titles'
age classification is unresolved, so behavioral targeting/personalization
must also remain disabled pending independent age and privacy review.
"""
from __future__ import annotations

from theme_contract import PROFILES

FLAGS=("personalizedAds","behavioralAnalytics","personalizedExperiments",
       "adPlacementsEnabled","paidOffersEnabled","lootOffersEnabled",
       "thirdPartyTrackingEnabled")
BLOCKED_CHILD=set(FLAGS)
SENSITIVE=set(FLAGS)


def validate_age_liveops_config(*, profile_id: str, flags: dict[str,bool],
                                audience_review_reference: str | None = None) -> dict:
    if profile_id not in PROFILES:
        raise ValueError("unknown game profile")
    if not isinstance(flags,dict) or set(flags)!=set(FLAGS) or any(type(v) is not bool for v in flags.values()):
        raise ValueError("liveops flags must be complete strict booleans")
    if audience_review_reference is not None and (
        not isinstance(audience_review_reference,str) or
        not 5<=len(audience_review_reference.strip())<=256):
        raise ValueError("audience review reference must be bounded")
    child=profile_id=="Wonder_Pop"
    prohibited=BLOCKED_CHILD if child else SENSITIVE
    rejected=sorted(k for k in prohibited if flags[k])
    return {
        "resultStatus":"AGE_POLICY_AUTHORING_DIAGNOSTIC_ONLY",
        "engineStatus":"BLOCKED_ENG_M24",
        "gameProfileId":profile_id,
        "audiencePolicy":"CHILD_DIRECTED_5_12" if child else "AGE_CLASSIFICATION_UNVERIFIED",
        "audienceReviewReferenceUnverified":audience_review_reference.strip() if audience_review_reference else None,
        "rejectedFlags":rejected,
        "localPreviewAllowed":not rejected,
        "realStoreAdsOrPersonalizationEligible":False,
        "requiresHumanAgeLegalReview":True,
        "releaseAuthorized":False,
    }
