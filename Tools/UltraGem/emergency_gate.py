"""Reference-only emergency content switch plan (LFX-M12-006).

Authoring a disable/reenable request must not edit client save data, grant
rewards, or update remote-config until a signed Engine-compatible manifest and
owner approved server action are verified.
"""
from __future__ import annotations

import re
from typing import Any

from theme_contract import PROFILES

SUPPORTED_KINDS={"LEVEL","EVENT","OFFER","COLLECTION"}


def propose_emergency_gate(*, game_id: str, content_kind: str, content_id: str,
                           requested_enabled: bool, reason: str,
                           current_manifest_sha256: str,
                           owner_review_reference: str) -> dict[str,Any]:
    if game_id not in PROFILES or content_kind not in SUPPORTED_KINDS:
        raise ValueError("unknown game or content kind")
    if not isinstance(content_id,str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,127}",content_id) is None:
        raise ValueError("invalid content identity")
    if type(requested_enabled) is not bool:
        raise ValueError("requested_enabled must be boolean")
    if not isinstance(reason,str) or not 20<=len(reason.strip())<=500:
        raise ValueError("evidence-based reason required")
    if not isinstance(current_manifest_sha256,str) or re.fullmatch(r"[0-9a-f]{64}",current_manifest_sha256) is None:
        raise ValueError("current manifest digest required")
    if not isinstance(owner_review_reference,str) or not 5<=len(owner_review_reference.strip())<=256:
        raise ValueError("owner trace reference required")
    return {
        "schemaVersion":1,
        "resultStatus":"EMERGENCY_CONTENT_GATE_PROPOSAL_ONLY",
        "engineStatus":"BLOCKED_ENG_M24",
        "gameId":game_id,"contentKind":content_kind,"contentId":content_id,
        "requestedEnabled":requested_enabled,
        "reason":reason.strip(),
        "sourceManifestSha256":current_manifest_sha256,
        "ownerReviewReferenceUnverified":owner_review_reference.strip(),
        "reEnableRequiresSignedRollbackOrRelease":requested_enabled,
        "compatibilityMatrixVerified":False,
        "playerSaveOrClaimsModified":False,
        "remoteConfigChanged":False,
        "productionAuthorized":False,
    }
