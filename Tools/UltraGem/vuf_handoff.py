"""Pure symbolic VUF/game UI contract handoff. No images or fake game states.

LFX-M08-012. All state names are placeholders awaiting original VUF art,
accessibility QA and canonical MATCH3_ENGINE action/state IDs.
"""
from __future__ import annotations

from typing import Any
from theme_contract import PROFILES

BASE_STATES=(
    "home.ready","level.start","level.gameplay","level.won","level.failed",
    "reward.claimable","reward.claimed","reward.disabled",
    "booster.owned","booster.unowned","booster.disabled",
    "offline.notice","content.update.available","content.update.failed",
    "purchase.pending","purchase.cancelled","purchase.unavailable",
    "ads.unavailable","ads.consent_required",
)
WONDER_EXCLUDED=("ads.unavailable","ads.consent_required")


def visual_state_contract(profile_id: str) -> dict[str, Any]:
    if profile_id not in PROFILES:
        raise ValueError("unknown game profile")
    states=[]
    for state in BASE_STATES:
        if profile_id=="Wonder_Pop" and state.startswith("ads."):
            states.append({"stateId":state,"requiresChildPolicyReview":True,
                           "previewEnabled":False,"semanticSource":"POLICY_BLOCKED"})
        else:
            states.append({"stateId":state,"requiresChildPolicyReview":False,
                           "previewEnabled":True,"semanticSource":"SYMBOLIC_ONLY"})
    return {
        "schemaVersion":1,"gameProfileId":profile_id,
        "resultStatus":"VUF_SYMBOLIC_HANDOFF_ONLY",
        "engineStatus":"BLOCKED_ENG_M24",
        "handoffTargets":["VUF-M01","VUF-M03","G01","G02"],
        "states":states,
        "ownerVisualAcceptanceRequired":True,
        "assetOrGameplaySourceIncluded":False,
        "productionApproved":False,
    }


def five_game_visual_inventory() -> list[dict[str, Any]]:
    return [visual_state_contract(profile) for profile in PROFILES]
