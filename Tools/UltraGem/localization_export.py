"""Deterministic five-game text/asset preview export, not store-approved content.

Existing LFX-M13-006. Produces content-addressed bytes in-memory, never writes
language resources to a player package without owner review and Engine gates.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from localization_qa import build_localization_qa, LOCALES
from theme_contract import PROFILES, COMMON_SLOTS


def export_localized_preview(profile_id: str, messages: dict[str, dict[str, str]],
                             asset_references: dict[str, str],
                             *, locales: tuple[str, ...] = LOCALES) -> dict[str, Any]:
    if profile_id not in PROFILES:
        raise ValueError('invalid game profile')
    if not isinstance(asset_references, dict) or set(asset_references)-set(COMMON_SLOTS):
        raise ValueError('unknown or invalid preview asset slot')
    for slot, asset in asset_references.items():
        if (not isinstance(asset,str) or len(asset)>144 or
            re.fullmatch(r'ref:[A-Za-z0-9._/-]{5,128}',asset) is None or
            '..' in asset.split('/')):
            raise ValueError('preview requires bounded symbolic asset references only')
    report=build_localization_qa(profile_id,messages,requested_locales=locales)
    resources={}
    bundles=[]
    for locale in sorted(locales):
        strings={}
        unresolved=[]
        for item in report['entries']:
            matched=next(v for v in item['variants'] if v['locale']==locale)
            strings[item['key']]=matched['text']
            if matched['usedEnglishFallback']:
                unresolved.append(item['key'])
        pack={
            'schemaVersion':1,
            'resultStatus':'LOCALIZED_EDITOR_PREVIEW_ONLY',
            'engineStatus':'BLOCKED_ENG_M24',
            'profileId':profile_id,
            'locale':locale,
            'strings':strings,
            'symbolicAssetSlots':dict(sorted(asset_references.items())),
            'englishFallbackKeys':unresolved,
            'linguisticReviewRequired':True,
            'artworkRightsIndependentlyVerified':False,
            'productionApproved':False,
        }
        payload=(json.dumps(pack,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode('utf-8')
        name=f'localization/{profile_id}/{locale}.json'
        resources[name]=payload
        bundles.append({'path':name,'sha256':hashlib.sha256(payload).hexdigest(),
                        'sizeBytes':len(payload),'locale':locale,
                        'fallbackCount':len(unresolved)})
    return {
        'resultStatus':'LOCALIZED_PREVIEW_EXPORT_ONLY',
        'engineStatus':'BLOCKED_ENG_M24',
        'gameProfileId':profile_id,
        'bytesByPath':resources,
        'manifest':bundles,
        'languageReviewRequired':True,
        'externalAssetRightsVerified':False,
        'productionExportAuthorized':False,
    }
