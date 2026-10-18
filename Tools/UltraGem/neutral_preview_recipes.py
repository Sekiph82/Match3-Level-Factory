"""Original neutral geometric preview recipes for five game IDs.

No game artwork/sounds/fonts imported, no renderer or authoritative rules.
Each recipe is declarative editor-only metadata for later Unity visualization.
"""
from __future__ import annotations

from typing import Any
from theme_contract import create_symbolic_theme_contract

PALETTES = {
    "Coral_Rescue": ("#103F62","#1B819A","#A8DFE8"),
    "Garage_Legends": ("#202D3C","#E58D37","#F1DCC4"),
    "Dino_Islands": ("#244E42","#84AB63","#F7D38B"),
    "The_Fractured_Realms": ("#2C2350","#8866B9","#D7C6EF"),
    "Wonder_Pop": ("#355777","#E9AAAD","#F7E9CB"),
}
SHAPES = {
    "Coral_Rescue": ("circle","diamond","hexagon"),
    "Garage_Legends": ("octagon","square","triangle"),
    "Dino_Islands": ("oval","hexagon","diamond"),
    "The_Fractured_Realms": ("diamond","triangle","star"),
    "Wonder_Pop": ("circle","rounded_square","star"),
}
# These shapes have no similarity claim to any donor game art.

def geometric_preview_recipe(profile_id: str, *, reduced_motion: bool = True) -> dict[str, Any]:
    contract=create_symbolic_theme_contract(profile_id)
    if type(reduced_motion) is not bool:
        raise ValueError("reduced_motion must be boolean")
    colors=PALETTES[profile_id]
    shapes=SHAPES[profile_id]
    return {
        "schemaVersion":1,
        "profileId":profile_id,
        "resultStatus":"GEOMETRIC_EDITOR_PREVIEW_ONLY",
        "engineStatus":"BLOCKED_ENG_M24",
        "assetRightsStatus":"SYNTHETIC_GEOMETRY_NO_EXTERNAL_ASSET",
        "releaseAuthorized":False,
        "previewSlotCount":len(contract["slots"]),
        "backgroundHex":colors[0],
        "accentHex":colors[1],
        "contrastHex":colors[2],
        "pieceShapes":[{"kind":shape,"colorHex":colors[(i+1)%3],"shapeNumber":i+1}
                       for i,shape in enumerate(shapes)],
        "reducedMotion":reduced_motion,
        "frames":1 if reduced_motion else 2,
        "isGameplayRuleSource":False,
    }


def all_preview_recipes() -> list[dict[str, Any]]:
    return [geometric_preview_recipe(profile) for profile in PALETTES]
