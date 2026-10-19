"""Offline, fail-closed release planning only, NEVER remote publishing.

LFX-M09-005/006 and LFX-M10-001 local source preparation. Authoritative
Engine/release contracts, store credentials and Cloudflare R2 writes are absent.
"""
from __future__ import annotations

import re
from typing import Any

from theme_contract import PROFILES

PLATFORMS=("android","ios","windows")
# ``local`` is an offline-only preview namespace used by preview_pack. Its
# presence here enables metadata planning only; all returned plans continue to
# deny uploads and production release authorization.
CHANNELS=("local","development","staging","production")
REQUIRED_LANGUAGES=("en", "tr")


def plan_platform_preview(*, profile_id: str, channel: str, platform: str,
                          locales: list[str]) -> dict[str, Any]:
    if profile_id not in PROFILES or channel not in CHANNELS or platform not in PLATFORMS:
        raise ValueError("unsupported profile/channel/platform")
    if not isinstance(locales,list) or not 1<=len(locales)<=16 or len(locales)!=len(set(locales)):
        raise ValueError("locale list must be unique and bounded")
    if any(not isinstance(lang,str) or re.fullmatch(r"[a-z]{2}(?:-[A-Z]{2})?",lang) is None for lang in locales):
        raise ValueError("unsupported locale")
    return {
        "resultStatus":"LOCAL_PLATFORM_REQUIREMENTS_ONLY",
        "engineStatus":"BLOCKED_ENG_M24",
        "profileId":profile_id,
        "channel":channel,"platform":platform,
        "locales":sorted(locales),
        "expectedLocalizationSlots":["ui.title","ui.goal","ui.won","ui.failed"],
        "assetBundleTargets":{
            "android":"Android ARM64 sprite and audio are outside this preview",
            "ios":"iOS sprite and audio are outside this preview",
            "windows":"Windows Editor preview only; no runtime scene packaging",
        }[platform],
        "missingStorefrontAssetProof":True,
        "productionValid":False,
        "publishAuthorized":False,
    }


def plan_rollback_only(*, previous_manifest_sha256: str, next_manifest_sha256: str,
                       previous_release_reference: str) -> dict[str, Any]:
    for sha in (previous_manifest_sha256,next_manifest_sha256):
        if not isinstance(sha,str) or re.fullmatch(r"[0-9a-f]{64}",sha) is None:
            raise ValueError("manifest SHA256 must be lowercase hex")
    if previous_manifest_sha256==next_manifest_sha256:
        raise ValueError("unchanged manifests are not a release rollback")
    if not isinstance(previous_release_reference,str) or not 5<=len(previous_release_reference.strip())<=256:
        raise ValueError("previous accepted release reference required")
    return {
        "resultStatus":"ROLLBACK_METADATA_PLAN_ONLY",
        "engineStatus":"BLOCKED_ENG_M24",
        "previousManifestSha256":previous_manifest_sha256,
        "proposedManifestSha256":next_manifest_sha256,
        "previousReleaseReferenceUnverified":previous_release_reference.strip(),
        "previousAcceptanceIndependentlyVerified":False,
        "stageRequired":True,
        "atomicPointerSwitchAuthorized":False,
        "uploadAuthorized":False,
    }


def plan_r2_topology(*, profile_id: str, channel: str, platform: str,
                     content_kind: str, content_sha256: str) -> dict[str, Any]:
    if profile_id not in PROFILES or channel not in CHANNELS or platform not in PLATFORMS:
        raise ValueError("invalid R2 namespace")
    if content_kind not in {"levels","media"}:
        raise ValueError("content kind must be levels or media")
    if not isinstance(content_sha256,str) or re.fullmatch(r"[0-9a-f]{64}",content_sha256) is None:
        raise ValueError("invalid content-addressed object")
    # This is a string, not an R2 object key authorized for upload.
    proposed=f"{profile_id}/{channel}/{platform}/{content_kind}/{content_sha256}"
    return {
        "resultStatus":"R2_PATH_PROPOSAL_ONLY",
        "engineStatus":"BLOCKED_ENG_M24",
        "proposedRelativeObjectKey":proposed,
        "bucketOrEndpoint":None,
        "originSigned":False,
        "r2CredentialsRequested":False,
        "remoteWriteAuthorized":False,
        "productionPointerAuthorized":False,
    }
