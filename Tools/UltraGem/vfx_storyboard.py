"""LFX-M08-011: Original, geometric-only VFX rehearsal frames.

This is a read-only *timing and accessibility storyboard*, not a cascade,
move, goal, physics, or match simulation. No RNG, Engine calls, licensed
assets, game-state writes, production exports or imported donor artwork.
Actual gameplay event-to-FX mapping / replay comparison awaits ENG-M24.

Source-first disposition: Unity Game Simulation Match3Visual.cs at pinned
7a77506428e699f5bce8ab5e2c1bc3d1f3a966a7 uses CodeMonkey.Utils and
legacy Match3 events: REJECTED_REASON (not a neutral Unity 6.6 standalone
editor timing source). UltraGem gemengine.py has no matching VFX source.
Original geometric preview only; reuse existing preview palettes.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from neutral_preview_recipes import geometric_preview_recipe

EFFECTS = ("combo", "line", "fish", "egg", "conveyor", "portal")
TOTAL_MS = 900
FRAME_COUNT = 12
REFERENCE_STATUS = "SYMBOLIC_FX_PREVIEW_ONLY"
ENGINE_STATUS = "BLOCKED_ENG_M24"


def _element(kind: str, x: int, y: int, size: int, opacity: int,
             color_hex: str) -> dict[str, Any]:
    if kind not in {"circle", "diamond", "line", "oval", "square"}:
        raise ValueError("unsupported geometric primitive")
    if not all(type(v) is int and 0 <= v <= 1000 for v in (x, y, size, opacity)):
        raise ValueError("unbounded geometry")
    return {"kind": kind, "x": x, "y": y, "size": size,
            "opacityPermille": opacity, "colorHex": color_hex}


def _frame(effect: str, tick: int, reduced: bool, color: str, accent: str) -> list[dict[str, Any]]:
    """Produce neutral schematic paths, not game mechanics or player events."""
    # Only full effects animate. Reduced effects hold a single high-contrast frame.
    t = 0.5 if reduced else tick / (FRAME_COUNT - 1)
    fade = 900 if reduced else max(250, round(1000 - 650 * t))
    if effect == "combo":
        return [_element("circle", 500, 500, round(80 + 230 * t), fade, color),
                _element("diamond", 500, 500, 70, 950, accent)]
    if effect == "line":
        return [_element("line", round(140 + 720 * t), 500, 100, fade, color),
                _element("square", 500, 500, 60, 900, accent)]
    if effect == "fish":
        return [_element("oval", round(160 + 680 * t), round(500 - 100 * math.sin(t * math.pi)),
                         75, 950, color),
                _element("diamond", 850, 500, 65, 900, accent)]
    if effect == "egg":
        return [_element("oval", 500, 500, round(140 - 35 * t), 950, color),
                _element("line", 500, round(470 + 110 * t), 80, fade, accent)]
    if effect == "conveyor":
        return [_element("square", round(180 + 160 * ((t + step / 4) % 1.0)),
                         500 + step * 45, 45, 950, color if step % 2 == 0 else accent)
                for step in range(4)]
    if effect == "portal":
        return [_element("circle", 250, 500, round(95 + 20 * t), 920, color),
                _element("circle", 750, 500, round(95 + 20 * (1 - t)), 920, color),
                _element("diamond", round(250 + 500 * t),
                         round(500 - 100 * math.sin(t * math.pi)), 44, fade, accent)]
    raise ValueError("unsupported effect")


def create_vfx_storyboard(profile_id: str, effect: str, *, reduced_motion: bool = True) -> dict[str, Any]:
    if effect not in EFFECTS or not isinstance(effect, str):
        raise ValueError("effect must be one of the six symbolic effect IDs")
    if type(reduced_motion) is not bool:
        raise ValueError("reduced_motion must be a boolean")
    recipe = geometric_preview_recipe(profile_id, reduced_motion=reduced_motion)
    # No unbounded scene/asset references, source paths, or gameplay structures.
    frames = []
    count = 1 if reduced_motion else FRAME_COUNT
    for tick in range(count):
        elements = _frame(effect, tick, reduced_motion,
                          recipe["contrastHex"], recipe["accentHex"])
        frames.append({"frame": tick, "atMs": 0 if reduced_motion
                       else round(TOTAL_MS * tick / (FRAME_COUNT - 1)),
                       "elements": elements})
    result = {
        "schemaVersion": 1,
        "profileId": profile_id,
        "effectId": effect,
        "resultStatus": REFERENCE_STATUS,
        "engineStatus": ENGINE_STATUS,
        "engineReplayComparison": "NOT_RUN",
        "assetRightsStatus": "SYNTHETIC_GEOMETRY_NO_EXTERNAL_ASSET",
        "releaseAuthorized": False,
        "isGameplayRuleSource": False,
        "reducedMotion": reduced_motion,
        "frameDurationMs": 0 if reduced_motion else TOTAL_MS,
        "frameCount": count,
        "frames": frames,
    }
    digest = hashlib.sha256(json.dumps(result, sort_keys=True, separators=(",", ":"),
                                       ensure_ascii=False).encode("utf-8")).hexdigest()
    return {**result, "storyboardSha256": digest}
