"""Asset-rights intake scanner for five-game preview slots (LFX-M08-008).

This is an evidence filter, NOT a legal opinion or auto-licensing service.
No art/fonts/audio are downloaded, imported, redistributed or generated.
The Unity Game Simulation sample's editor-only scope never authorizes
commercial third-party media distribution.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

RIGHTS = frozenset({"OWNER_ORIGINAL", "LICENSE_REVIEWED", "REFERENCE_ONLY",
                     "UNLICENSED", "RIGHTS_UNKNOWN"})
KIND = frozenset({"SPRITE", "FONT", "SOUND", "VFX", "BACKGROUND", "UI_ICON"})
PROFILES = frozenset({"Coral_Rescue", "Garage_Legends", "Dino_Islands",
                      "The_Fractured_Realms", "Wonder_Pop"})


def audit_asset_bindings(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Every unreviewed entry stays symbolic; no asset export is granted."""
    if not isinstance(entries, list) or len(entries) > 512:
        raise ValueError("asset catalog must be a bounded array")
    seen = set()
    scanned = []
    for item in entries:
        if not isinstance(item, dict) or set(item) != {
                "profileId", "slotId", "kind", "rightsStatus", "sourceReference",
                "contentSha256", "permissionEvidenceReference", "scope"}:
            raise ValueError("asset entry has missing or unsupported fields")
        profile, slot, kind, rights, source, digest, proof, scope = (
            item[key] for key in ("profileId", "slotId", "kind", "rightsStatus",
                                 "sourceReference", "contentSha256", "permissionEvidenceReference", "scope"))
        if profile not in PROFILES or kind not in KIND or rights not in RIGHTS:
            raise ValueError("unknown profile, asset type or rights status")
        if not isinstance(slot, str) or re.fullmatch("[a-z][a-z0-9_.-]{2,79}", slot) is None:
            raise ValueError("invalid symbolic asset slot")
        if not isinstance(source, str) or len(source) > 512 or not source:
            raise ValueError("source reference must be explicit")
        if not isinstance(digest, str) or re.fullmatch("[0-9a-f]{64}", digest) is None:
            raise ValueError("asset content digest must be SHA256")
        if proof is not None and (not isinstance(proof, str) or len(proof) > 512 or len(proof) < 5):
            raise ValueError("invalid permission evidence reference")
        if scope not in {"LOCAL_EDITOR_PREVIEW_ONLY", "UNITY_PROJECT_ONLY", "PRODUCTION_REDISTRIBUTION"}:
            raise ValueError("unknown usage scope")
        key = (profile, slot)
        if key in seen:
            raise ValueError("duplicate profile/slot asset binding")
        seen.add(key)
        # Explicit evidence and production scope still do NOT automatically
        # grant commercial redistribution; human rights review is a separate gate.
        approved_for_local_preview = rights in {"OWNER_ORIGINAL", "LICENSE_REVIEWED"} and bool(proof)
        scanned.append({
            "profileId": profile,
            "slotId": slot,
            "kind": kind,
            "rightsStatus": rights,
            "sourceReference": source,
            "contentSha256": digest,
            "scope": scope,
            "permissionEvidenceReference": proof,
            "localPreviewCandidate": approved_for_local_preview,
            "requiresHumanRightsReview": True,
            "productionDistributionAuthorized": False,
        })
    return {
        "resultStatus": "RIGHTS_INTAKE_ONLY",
        "engineStatus": "BLOCKED_ENG_M24",
        "distributionAuthorized": False,
        "entries": sorted(scanned, key=lambda x: (x["profileId"], x["slotId"])),
        "blocked": sum(not x["localPreviewCandidate"] for x in scanned),
    }
