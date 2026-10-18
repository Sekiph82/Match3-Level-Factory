"""Age-conservative declarative content caps, no backend entitlements.

LFX-M12-013. Wonder Pop child profile disables ads, streak pressure, direct
paid offers and exploitative short-lived reward prompts. Other titles are
unverified age: no forced ads or behavioral targeting until legal review.
"""
from __future__ import annotations

from typing import Any
from theme_contract import PROFILES

_KEYS={'adsPerSession','earnedPacksPerDay','collectionItems','eventDurationHours',
       'streakPressureEnabled','forcedOfferPopups','premiumRewardCount',
       'personalizedEngagement'}


def evaluate_content_caps(profile_id: str, settings: dict[str,Any]) -> dict[str,Any]:
    if profile_id not in PROFILES:
        raise ValueError('unknown title')
    if not isinstance(settings,dict) or set(settings)!=_KEYS:
        raise ValueError('unknown or missing content configuration fields')
    numeric=('adsPerSession','earnedPacksPerDay','collectionItems','eventDurationHours',
             'forcedOfferPopups','premiumRewardCount')
    if any(type(settings[k]) is not int or not 0<=settings[k]<=10000 for k in numeric):
        raise ValueError('content limits must be bounded exact integers')
    if any(type(settings[k]) is not bool for k in ('streakPressureEnabled','personalizedEngagement')):
        raise ValueError('content flags must be boolean')
    child=profile_id=='Wonder_Pop'
    violations=[]
    if settings['adsPerSession']>0:
        violations.append('ADS_NOT_AGE_CLEARED')
    if settings['personalizedEngagement']:
        violations.append('BEHAVIORAL_PERSONALIZATION_NOT_CLEARED')
    if settings['forcedOfferPopups']>0:
        violations.append('FORCED_OFFERS_NOT_ALLOWED')
    if child:
        if settings['streakPressureEnabled']:
            violations.append('CHILD_STREAK_PRESSURE_NOT_ALLOWED')
        if settings['premiumRewardCount']>0:
            violations.append('CHILD_PREMIUM_REWARD_META_NOT_ALLOWED')
        if settings['earnedPacksPerDay']>3:
            violations.append('CHILD_EARNED_PACK_DAILY_CAP')
        if settings['collectionItems']>100:
            violations.append('CHILD_COLLECTION_SCOPE_CAP')
        if 0<settings['eventDurationHours']<48:
            violations.append('CHILD_SHORT_DEADLINE_PRESSURE')
    return {
        'resultStatus':'CHILD_SAFE_CONTENT_CAP_PREVIEW_ONLY',
        'engineStatus':'BLOCKED_ENG_M24',
        'gameProfileId':profile_id,'childDirected':child,
        'violations':violations,'canPreviewLocally':not violations,
        'actualLegalAgeStatusVerified':False,
        'rewardGrantOrPublishAuthorized':False,
    }
