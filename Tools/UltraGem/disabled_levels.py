"""Non-shipping disabled-level recovery proposal (LFX-M09-009).

A bad/corrupt level may be *proposed* for quarantine without modifying the
LevelDraft, awarding a win, or deleting remote content. Only a future signed
Engine-compatible manifest, owner approval and safe frontier can enforce it.
"""
from __future__ import annotations

import re
from typing import Any

from theme_contract import PROFILES

REASONS={"BAD_HASH","CRASH_ON_OPEN","ENGINE_INCOMPATIBLE","CONTENT_RIGHTS_HOLD",
         "OWNER_DISABLED","PLAYER_PROGRESS_RISK"}


def propose_disabled_levels(*, game_id: str, manifest_sha256: str,
                            affected: list[dict[str,Any]],
                            owner_review_reference: str) -> dict[str,Any]:
    if game_id not in PROFILES:
        raise ValueError("unknown game ID")
    if not isinstance(manifest_sha256,str) or re.fullmatch("[0-9a-f]{64}",manifest_sha256) is None:
        raise ValueError("pinned manifest SHA256 required")
    if not isinstance(owner_review_reference,str) or not 5<=len(owner_review_reference.strip())<=256:
        raise ValueError("traceable owner review reference required")
    if not isinstance(affected,list) or not 1<=len(affected)<=128:
        raise ValueError("1..128 level disable proposals required")
    keys=set()
    normalized=[]
    for item in affected:
        if not isinstance(item,dict) or set(item)!={"worldId","chapterId","levelId","reason"}:
            raise ValueError("invalid disable-list entry")
        ids=(item["worldId"],item["chapterId"],item["levelId"])
        if any(not isinstance(x,str) or re.fullmatch("[A-Za-z0-9][A-Za-z0-9._-]{0,127}",x) is None for x in ids):
            raise ValueError("invalid level identity")
        if ids in keys:
            raise ValueError("duplicate level disable request")
        keys.add(ids)
        if item["reason"] not in REASONS:
            raise ValueError("unrecognized disable reason")
        normalized.append(dict(item))
    return {
        "schemaVersion":1,
        "resultStatus":"DISABLED_LEVEL_PROPOSAL_ONLY",
        "engineStatus":"BLOCKED_ENG_M24",
        "gameId":game_id,
        "pinnedManifestSha256":manifest_sha256,
        "ownerReviewReferenceUnverified":owner_review_reference.strip(),
        "disabledLevels":sorted(normalized,key=lambda x:(x["worldId"],x["chapterId"],x["levelId"])),
        "safeProgressFrontierVerified":False,
        "levelRewardsModified":False,
        "fakeWinOrStarGranted":False,
        "remoteObjectsDeleted":False,
        "reenableAuthorized":False,
        "signedPatchGenerated":False,
        "publishAuthorized":False,
    }
