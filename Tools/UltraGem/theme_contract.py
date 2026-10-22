"""Neutral theme-preview slot contracts, independent of match gameplay.

LFX-M08-001. Symbolic placeholders only; no third-party artwork, Unity
textures, resources or game-specific rule authority is imported here.
"""
from __future__ import annotations

import re
from typing import Any

from asset_rights import audit_asset_bindings

PROFILES = ("Coral_Rescue","Garage_Legends","Dino_Islands",
            "The_Fractured_Realms","Wonder_Pop")
COMMON_SLOTS = {
    "board.background":"BACKGROUND",
    "piece.basic.1":"SPRITE",
    "piece.basic.2":"SPRITE",
    "piece.basic.3":"SPRITE",
    "ui.goal":"UI_ICON",
    "ui.booster":"UI_ICON",
    "vfx.match":"VFX",
}
GENERIC_PLACEHOLDER = "BUILTIN_EDITOR_GEOMETRY_ONLY"


def create_symbolic_theme_contract(profile_id: str, *,
                                    slot_assignments: dict[str, str] | None = None,
                                    rights_entries: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if profile_id not in PROFILES:
        raise ValueError("unknown game profile")
    overrides = dict(slot_assignments or {})
    if set(overrides) - set(COMMON_SLOTS):
        raise ValueError("unknown theme slot: no implicit game rules")
    for slot, reference in overrides.items():
        if not isinstance(reference,str) or re.fullmatch(r"ref:[A-Za-z0-9._/-]{5,128}",reference) is None:
            raise ValueError("theme binding must be an explicit symbolic reference")
        if ".." in reference.split("/"):
            raise ValueError("parent traversal forbidden in theme binding")
    rights = audit_asset_bindings(rights_entries or [])
    rights_by_slot = {
        (entry["profileId"], entry["slotId"]): entry
        for entry in rights["entries"]
    }
    slots = []
    for name, kind in sorted(COMMON_SLOTS.items()):
        binding = overrides.get(name)
        right = rights_by_slot.get((profile_id, name)) if binding else None
        if right is not None and right["sourceReference"] != binding:
            raise ValueError("theme binding does not match independent rights source reference")
        slots.append({
            "slotId": name,
            "kind": kind,
            "symbolicBinding": binding,
            "placeholderWhenMissing": GENERIC_PLACEHOLDER,
            "rightsMetadata": ({
                "rightsStatus": right["rightsStatus"],
                "scope": right["scope"],
                "permissionEvidenceReference": right["permissionEvidenceReference"],
                "localPreviewCandidate": right["localPreviewCandidate"],
                "requiresHumanRightsReview": right["requiresHumanRightsReview"],
                "productionDistributionAuthorized": False,
            } if right is not None else {
                "rightsStatus": "RIGHTS_UNKNOWN",
                "scope": None,
                "permissionEvidenceReference": None,
                "localPreviewCandidate": False,
                "requiresHumanRightsReview": True,
                "productionDistributionAuthorized": False,
            }),
        })
    return {
        "schemaVersion":1,
        "profileId":profile_id,
        "resultStatus":"EDITOR_THEME_PREVIEW_CONTRACT_ONLY",
        "engineStatus":"BLOCKED_ENG_M24",
        "releaseAuthorized":False,
        "missingArtFallback":GENERIC_PLACEHOLDER,
        "doesNotModifyGameplay":True,
        "rightsAuditStatus": rights["resultStatus"],
        "rightsDistributionAuthorized": rights["distributionAuthorized"],
        "slots": slots,
    }


def all_five_theme_contracts() -> list[dict[str, Any]]:
    return [create_symbolic_theme_contract(p) for p in PROFILES]
