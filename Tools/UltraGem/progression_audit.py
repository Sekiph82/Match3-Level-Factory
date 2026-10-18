"""Transparent static tutorial/chapter feature introduction audit (LFX-M05-013).

Warns about repeated goals, unintroduced specials/obstacles and data ordering;
never infers skill, solver difficulty or production playability from counts.
"""
from __future__ import annotations

from collections import Counter
from typing import Any
import leveldraft

MAX_DRAFTS=128


def audit_progression(drafts: list[dict[str,Any]], *, tutorial_count: int = 3,
                      repeated_goal_warning_at: int = 3) -> dict[str,Any]:
    if not isinstance(drafts,list) or not 1 <= len(drafts) <= MAX_DRAFTS:
        raise ValueError("1..128 drafts required")
    if type(tutorial_count) is not int or not 0 <= tutorial_count <= 20:
        raise ValueError("invalid tutorial_count")
    if type(repeated_goal_warning_at) is not int or not 2 <= repeated_goal_warning_at <= 20:
        raise ValueError("invalid repeat threshold")
    seen_ids=set()
    warnings=[]
    introduced=set()
    prior_world=None
    goal_repetition=0
    prior_goals=None
    world_first_seen=set()
    for position,draft in enumerate(drafts,1):
        leveldraft.validate(draft)
        identity=(draft['gameProfileId'],draft['worldId'],draft['chapterId'],draft['levelId'])
        if identity in seen_ids:raise ValueError("duplicate level identity")
        seen_ids.add(identity)
        world=(draft['gameProfileId'],draft['worldId'])
        if prior_world != world:
            if world in world_first_seen:
                warnings.append({"ordinal":position,"code":"WORLD_SEQUENCE_INTERLEAVED"})
            world_first_seen.add(world)
            introduced=set()
            prior_goals=None
            goal_repetition=0
            prior_world=world
        mechanics=set()
        for cell in draft['cells']:
            if cell['active']:
                if cell['locked']:mechanics.add('locked_cell')
                if cell['specialId']:mechanics.add('special:'+cell['specialId'])
                if cell['obstacleId']:mechanics.add('obstacle:'+cell['obstacleId'])
        if position<=tutorial_count and mechanics:
            warnings.append({"ordinal":position,"code":"TUTORIAL_ADVANCED_MECHANICS_PRESENT",
                             "details":sorted(mechanics)})
        # Only static facts. A mechanic introduced here still needs Engine validation.
        new=mechanics-introduced
        if len(new)>1:
            warnings.append({"ordinal":position,"code":"MULTIPLE_NEW_MECHANICS_IN_ONE_LEVEL",
                             "details":sorted(new)})
        introduced|=mechanics
        goals=tuple(sorted((g['targetId'],g['targetCount']) for g in draft['goals']))
        goal_repetition=goal_repetition+1 if goals==prior_goals else 1
        prior_goals=goals
        if goal_repetition>=repeated_goal_warning_at:
            warnings.append({"ordinal":position,"code":"REPEATED_EXACT_GOALS",
                             "consecutiveCount":goal_repetition})
    return {"resultStatus":"REFERENCE_PROGRESSION_AUDIT_ONLY", "engineStatus":"BLOCKED_ENG_M24",
            "candidateCount":len(drafts),"warnings":warnings,"reviewRequired":True,
            "playabilityCertified":False,"releaseAuthorized":False}
