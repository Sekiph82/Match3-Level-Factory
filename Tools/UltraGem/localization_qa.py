"""Five-title safe localizable message preview and fallback QA (LFX-M13-006).

Never silently claims translation approval; missing translations explicitly
fall back to English with a review marker. No store price or remote config.
"""
from __future__ import annotations

import re
from typing import Any
from theme_contract import PROFILES

LOCALES=('en','tr','sw','fr','de')
_KEY=re.compile(r'[a-z][a-z0-9]*(?:\.[a-z0-9_]+){1,5}\Z')
_PLACEHOLDERS={'level','world','count'}
_TOKEN=re.compile(r'\{([^{}]+)\}')


def build_localization_qa(profile_id: str, messages: dict[str,dict[str,str]],
                          *, requested_locales: tuple[str,...] = LOCALES) -> dict[str,Any]:
    if profile_id not in PROFILES:
        raise ValueError('unknown game profile')
    if not isinstance(messages,dict) or not 1<=len(messages)<=128:
        raise ValueError('1..128 messages required')
    if (not isinstance(requested_locales,tuple) or len(requested_locales)!=len(set(requested_locales)) or
        any(locale not in LOCALES for locale in requested_locales) or 'en' not in requested_locales):
        raise ValueError('review locales must be unique and include English')
    output=[]
    missing=[]
    for key,translations in sorted(messages.items()):
        if not isinstance(key,str) or _KEY.fullmatch(key) is None:
            raise ValueError('invalid localization key')
        if not isinstance(translations,dict) or 'en' not in translations or set(translations)-set(LOCALES):
            raise ValueError('valid English baseline is mandatory')
        expected=None
        for locale,text in translations.items():
            if not isinstance(text,str) or not text.strip() or len(text)>512 or any(
                bad in text.lower() for bad in ('<script','javascript:','http://','https://','${','<iframe')):
                raise ValueError('unsafe or empty translation')
            if text.lstrip().startswith(('=','+','-','@')):
                raise ValueError('CSV/formula injection prefix prohibited')
            if text.count('{')!=text.count('}'):
                raise ValueError('unpaired placeholders')
            fields=set(_TOKEN.findall(text))
            if not fields<=_PLACEHOLDERS:
                raise ValueError('unknown substitutions, prices, receipts and entitlements prohibited')
            if expected is None:expected=fields
            elif expected!=fields:raise ValueError('translated placeholders do not match English')
        entry={'key':key,'variants':[]}
        for locale in sorted(requested_locales):
            fallback=locale not in translations
            if fallback:missing.append({'key':key,'locale':locale})
            entry['variants'].append({'locale':locale,'text':translations.get(locale,translations['en']),
                                      'usedEnglishFallback':fallback,'ownerLinguisticReviewRequired':True})
        output.append(entry)
    return {'resultStatus':'LOCALIZATION_QA_PREVIEW_ONLY','engineStatus':'BLOCKED_ENG_M24',
            'gameProfileId':profile_id,'entries':output,'missingTranslations':missing,
            'reviewRequired':True,'storePriceInjected':False,'productionApproved':False}
