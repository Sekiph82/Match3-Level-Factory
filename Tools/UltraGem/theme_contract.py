"""Neutral theme-preview slot contracts, independent of match gameplay.

LFX-M08-001. Symbolic placeholders only; no third-party artwork, Unity
textures, resources or game-specific rule authority is imported here.
"""
from __future__ import annotations

import re
from typing import Any

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
                                    slot_assignments: dict[str, str] | None = None) -> dict[str, Any]:
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
    return {
        "schemaVersion":1,
        "profileId":profile_id,
        "resultStatus":"EDITOR_THEME_PREVIEW_CONTRACT_ONLY",
        "engineStatus":"BLOCKED_ENG_M24",
        "releaseAuthorized":False,
        "missingArtFallback":GENERIC_PLACEHOLDER,
        "doesNotModifyGameplay":True,
        "slots":[{"slotId":name,"kind":kind,
                  "symbolicBinding":overrides.get(name),
                  "placeholderWhenMissing":GENERIC_PLACEHOLDER}
                 for name,kind in sorted(COMMON_SLOTS.items())],
    }


def all_five_theme_contracts() -> list[dict[str, Any]]:
    return [create_symbolic_theme_contract(p) for p in PROFILES]
