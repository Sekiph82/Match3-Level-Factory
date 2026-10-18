"""Three original, synthetic onboarding LevelDraft v1 templates (LFX-M06-002).

Authoring examples only: no donor puzzle/asset copy, no certified initial move,
winning path, ENG-M24 SDK parity, or human beginner difficulty claim.
"""
from __future__ import annotations

from typing import Any
import leveldraft
from theme_contract import PROFILES

# Hand-authored neutral training progression, not ported from any third party.
_STEPS = ((4, 4, 3, 10, 3), (5, 4, 4, 14, 5), (5, 5, 4, 18, 8))


def make_tutorial_templates(profile_id: str, *, seed: int = 712) -> list[dict[str, Any]]:
    if profile_id not in PROFILES:
        raise ValueError("unknown profile")
    if type(seed) is not int or not 0 <= seed <= 2**63-4:
        raise ValueError("invalid seed or insufficient increment range")
    drafts=[]
    for index, (width, height, colors, moves, goal_count) in enumerate(_STEPS, start=1):
        cells=[]
        mask=[]
        for row in range(height):
            for column in range(width):
                # Step 3 introduces ONE non-playable hole as a spatial lesson.
                active = not (index==3 and row==2 and column==2)
                color = 1 + ((column+row*2+index)%colors)
                cells.append(dict(row=row,column=column,layer=0,active=active,locked=False,
                                  contentId=f"template.color.{color}" if active else None,
                                  obstacleId=None,obstacleDurability=0,lockDurability=0,specialId=None))
                mask.append(active)
        draft=dict(
            draftVersion=1,validationStatus="PROTOTYPE_ONLY",gameProfileId=profile_id,profileVersion=1,
            worldId="world.tutorial",chapterId="chapter.onboarding",levelId=f"tutorial.{index:02d}",
            releaseChannel="local",platform="windows-editor",locale="en",minEngineVersion=None,
            maxEngineVersion=None,seed=seed+index-1,width=width,height=height,layers=1,
            activeMask=mask,moveBudget=moves,timedMode=False,timeLimitSeconds=0,
            oneStarThreshold=1,twoStarThreshold=2,threeStarThreshold=3,
            difficultyLabel="difficulty.unrated",editorHintKey=f"tutorial.hint.{index:02d}",
            cells=cells,goals=[dict(goalId="goal.primary",targetId="sample.score",
                                   targetCount=goal_count)],engineSchemaVersion=None,
            sourceRepository="factory/original-templates",sourceRevision="lfx-r10",
            sourceKind="OriginalSyntheticTutorialTemplate",
        )
        leveldraft.validate(draft)
        drafts.append(leveldraft.canonicalize(draft))
    return drafts


def tutorial_source_receipt(profile_id: str, *, seed: int = 712) -> dict[str, Any]:
    drafts=make_tutorial_templates(profile_id,seed=seed)
    return {"resultStatus":"TUTORIAL_AUTHORING_ONLY", "engineStatus":"BLOCKED_ENG_M24",
            "profileId":profile_id,"templates":[{
                "levelId":d["levelId"],"draftSha256":leveldraft.sha256(d),
                "intendedLesson":["basic-color-match","larger-board","single-hole"][i],
                "certifiedEasyOrSolvable":False,
            } for i,d in enumerate(drafts)],
            "thirdPartyArtOrAssetsCopied":False,"releaseAuthorized":False}
