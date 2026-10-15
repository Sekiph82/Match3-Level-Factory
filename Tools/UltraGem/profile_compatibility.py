"""Fail-closed builder diagnostics for reference drafts; never certifies Engine playability."""

from collections import Counter

PROFILE_IDS = (
    "Coral_Rescue", "Garage_Legends", "Dino_Islands",
    "The_Fractured_Realms", "Wonder_Pop",
)
SUPPORTED_GOALS = {"sample.score", "sample.glass"}
SUPPORTED_OBSTACLES = {"sample.glass"}


def diagnose_profile_compatibility(draft: dict) -> dict:
    """Report local-profile policy findings while preserving all source fields."""
    profile_id = draft.get("gameProfileId")
    if profile_id not in PROFILE_IDS:
        return {
            "profileId": profile_id,
            "localPolicyStatus": "REJECTED_UNKNOWN_PROFILE",
            "engineStatus": "BLOCKED_ENG_M24",
            "draftMutationPerformed": False,
            "findings": [{"code": "UNKNOWN_PROFILE", "path": "gameProfileId", "sourceValue": profile_id}],
            "mappingHints": [],
        }

    findings = []
    cells = draft.get("cells", [])
    locked = [cell for cell in cells if cell.get("active") and (cell.get("locked") or cell.get("lockDurability", 0) > 0)]
    if locked:
        findings.append({"code": "PROFILE_CAPABILITY_DISABLED", "capabilityId": "cell.lock", "path": "cells", "count": len(locked), "sourceValues": sorted({str(cell.get("lockDurability", 0)) for cell in locked})})
    specials = Counter(cell.get("specialId") for cell in cells if cell.get("active") and cell.get("specialId"))
    for special_id, count in sorted(specials.items()):
        findings.append({"code": "PROFILE_CAPABILITY_DISABLED", "capabilityId": "special.unmapped", "path": "cells.specialId", "sourceValue": special_id, "count": count})
    obstacles = Counter(cell.get("obstacleId") for cell in cells if cell.get("active") and cell.get("obstacleId") not in (None, *SUPPORTED_OBSTACLES))
    for obstacle_id, count in sorted(obstacles.items()):
        findings.append({"code": "PROFILE_CAPABILITY_DISABLED", "capabilityId": "obstacle.unmapped", "path": "cells.obstacleId", "sourceValue": obstacle_id, "count": count})
    goals = [goal for goal in draft.get("goals", []) if goal.get("targetId") not in SUPPORTED_GOALS]
    for goal in sorted(goals, key=lambda value: (value.get("goalId", ""), value.get("targetId", ""))):
        findings.append({"code": "PROFILE_CAPABILITY_DISABLED", "capabilityId": "goal.unmapped", "path": "goals.targetId", "sourceValue": goal.get("targetId"), "goalId": goal.get("goalId")})

    return {
        "profileId": profile_id,
        "localPolicyStatus": "REJECTED_BY_BUILDER_POLICY" if findings else "ACCEPTED_FOR_LOCAL_AUTHORING_ONLY",
        "engineStatus": "BLOCKED_ENG_M24",
        "draftMutationPerformed": False,
        "findings": findings,
        "mappingHints": [
            {"sourcePattern": "ultragem.color.*", "capabilityId": "piece.color.basic", "mappingStatus": "IDENTIFIER_HINT_ONLY_ENGINE_SEMANTICS_UNVERIFIED"},
            {"sourceValue": "ultragem.spawn_random", "capabilityId": "piece.color.basic", "mappingStatus": "REQUIRES_ENGINE_SPAWN_CONTRACT"},
            {"sourcePattern": "ultragem.*special", "capabilityId": None, "mappingStatus": "BLOCKED_ENG_M24"},
            {"sourcePattern": "ultragem.*lock", "capabilityId": None, "mappingStatus": "BLOCKED_ENG_M24"},
            {"sourcePattern": "ultragem.goal.score", "capabilityId": "goal.score", "mappingStatus": "GOAL_SEMANTICS_UNVERIFIED"},
        ],
    }
