"""Reference-only tier policy and anti-size-bias diagnostic configuration.

LFX-M05-005 and -006 source preparation. Actual five-persona difficulty is
calibrated only by the future authoritative MATCH3_ENGINE replay cohort.
"""
from __future__ import annotations

import math
from typing import Any

BANDS=("VERY_EASY","EASY","NORMAL","HARD","EXPERT")
INELIGIBLE_FEATURES=frozenset({"boardArea","boardWidth","boardHeight","obstacleCount","lockCount"})


def make_reference_tier_policy(*, boundaries: list[float],
                               min_samples_per_persona: int,
                               reviewer_reference: str) -> dict[str, Any]:
    if not isinstance(boundaries,list) or len(boundaries)!=4 or any(
            isinstance(x,bool) or type(x) not in (float,int) or not math.isfinite(x) or not 0<x<1 for x in boundaries):
        raise ValueError("tier boundaries must contain four finite 0..1 fractions")
    if boundaries!=sorted(set(boundaries)):
        raise ValueError("tier boundaries must be strictly increasing")
    if type(min_samples_per_persona) is not int or not 2<=min_samples_per_persona<=10000:
        raise ValueError("minimum samples must be bounded")
    if not isinstance(reviewer_reference,str) or not 5<=len(reviewer_reference.strip())<=256:
        raise ValueError("traceable reviewer reference required")
    return {
        "schemaVersion":1,
        "resultStatus":"REFERENCE_THRESHOLD_POLICY_ONLY",
        "engineStatus":"BLOCKED_ENG_M24",
        "bands":list(BANDS),
        "uncalibratedBoundaries":list(boundaries),
        "minSamplesPerPersona":min_samples_per_persona,
        "reviewerReferenceUnverified":reviewer_reference.strip(),
        "tierAssigned":None,
        "ownerCalibrationRequired":True,
        "releaseAuthorized":False,
    }


def diagnose_metric_bias(*, provided_features: list[str],
                         observed_personas: list[str],
                         claimed_result: str | None = None) -> dict[str, Any]:
    if not isinstance(provided_features,list) or not all(isinstance(x,str) for x in provided_features):
        raise ValueError("feature names must be strings")
    if not isinstance(observed_personas,list) or not all(isinstance(x,str) for x in observed_personas):
        raise ValueError("persona IDs must be strings")
    kinds=set(provided_features)
    reason=[]
    if not kinds or kinds.issubset(INELIGIBLE_FEATURES):
        reason.append("ONLY_GEOMETRY_OR_BLOCKER_COUNT")
    expected={"Beginner","Casual","Strategic","Expert","Random"}
    if not expected.issubset(set(observed_personas)):
        reason.append("FIVE_ENGINE_PERSONA_RUNS_MISSING")
    if claimed_result not in (None,"REFERENCE_ONLY"):
        reason.append("UNSUPPORTED_CERTIFIED_DIFFICULTY_CLAIM")
    return {
        "resultStatus":"REFERENCE_BIAS_DIAGNOSTIC_ONLY",
        "engineStatus":"BLOCKED_ENG_M24",
        "warnings":reason,
        "canAssignCertifiedTier":False,
        "releaseAuthorized":False,
    }
