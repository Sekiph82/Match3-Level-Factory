"""Safety preflight for preview publication. It NEVER publishes.

LFX-M10-008. Factory authoring must not silently turn preview data into
production remote content. The final owner, signer and Engine gates are not
available, therefore every such preflight returns BLOCKED.
"""
from __future__ import annotations

import re
from typing import Any

CHANNELS={"development","staging","production"}


def assess_remote_publish_preflight(*, channel: str, game_id: str,
                                    manifest_sha256: str,
                                    owner_approval_reference: str | None = None,
                                    preview_confirmed: bool = False) -> dict[str,Any]:
    if channel not in CHANNELS:
        raise ValueError("invalid publishing channel")
    from theme_contract import PROFILES
    if game_id not in PROFILES:
        raise ValueError("unknown game ID")
    if not isinstance(manifest_sha256,str) or re.fullmatch("[0-9a-f]{64}",manifest_sha256) is None:
        raise ValueError("invalid level manifest SHA")
    if type(preview_confirmed) is not bool:
        raise ValueError("preview_confirmed must be boolean")
    if owner_approval_reference is not None and (
        not isinstance(owner_approval_reference,str) or not 5<=len(owner_approval_reference.strip())<=256):
        raise ValueError("owner approval reference invalid")
    reasons=[
        "ENG_M24_FINAL_PACKAGE_NOT_INDEPENDENTLY_ACCEPTED",
        "SIGNED_COMPATIBLE_RELEASE_MANIFEST_MISSING",
        "REMOTE_WRITER_AUTHORITY_NOT_AVAILABLE",
    ]
    if channel=="production" and not owner_approval_reference:
        reasons.append("EXPLICIT_PRODUCTION_OWNER_APPROVAL_MISSING")
    if not preview_confirmed:
        reasons.append("OWNER_PREVIEW_NOT_CONFIRMED")
    return {
        "resultStatus":"PUBLISH_PREFLIGHT_BLOCKED",
        "engineStatus":"BLOCKED_ENG_M24",
        "channel":channel,
        "gameId":game_id,
        "manifestSha256":manifest_sha256,
        "ownerApprovalReferenceUnverified":owner_approval_reference,
        "previewConfirmedByCallerUnverified":preview_confirmed,
        "blockReasons":reasons,
        "writerCredentialsAvailable":False,
        "networkOrStorageAccessPerformed":False,
        "publishAuthorized":False,
    }
