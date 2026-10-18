"""Deterministic in-memory prototype pack manifest (LFX-M09-001 partial).

NOT a shipping/signed LevelPack. Never serializes licensed sample game code,
artwork, scene metadata or Engine-certified content. ENG-M24 gates release.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

import leveldraft

MAX_LEVELS = 128
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


def build_preview_pack(drafts: list[dict[str, Any]], *,
                       channel: str = "local") -> dict[str, Any]:
    """Construct collision-free, content-addressed *preview* JSON records."""
    if not isinstance(drafts, list) or not 1 <= len(drafts) <= MAX_LEVELS:
        raise ValueError("drafts must contain 1..128 levels")
    if channel not in {"local", "development", "staging"}:
        raise ValueError("production channels forbidden without Engine gate")
    grouped = {}
    keys = set()
    for draft in drafts:
        leveldraft.validate(draft)
        if draft["releaseChannel"] != channel:
            raise ValueError("mixed release channels are not allowed")
        ids = (draft["gameProfileId"], draft["worldId"], draft["chapterId"], draft["levelId"])
        if any(not isinstance(v, str) or _ID.fullmatch(v) is None for v in ids):
            raise ValueError("unusable profile/world/chapter/level identifier")
        if ids in keys:
            raise ValueError("duplicate level identity within preview pack")
        keys.add(ids)
        body = leveldraft.dumps_canonical(draft)
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        if digest != leveldraft.sha256(draft):
            raise ValueError("canonical LevelDraft hash mismatch")
        group_key = ids[:3]
        grouped.setdefault(group_key, []).append({
            "levelId": ids[3],
            "draftSha256": digest,
            "draftJsonUtf8Bytes": len(body.encode("utf-8")),
            "resultStatus": "PROTOTYPE_ONLY",
            "engineStatus": "BLOCKED_ENG_M24",
        })
    groups = []
    for (profile, world, chapter), levels in sorted(grouped.items()):
        groups.append({
            "gameProfileId": profile,
            "worldId": world,
            "chapterId": chapter,
            "levels": sorted(levels, key=lambda item: item["levelId"]),
        })
    return {
        "schemaVersion": 1,
        "resultStatus": "LOCAL_PREVIEW_MANIFEST_ONLY",
        "engineStatus": "BLOCKED_ENG_M24",
        "channel": channel,
        "levelCount": len(drafts),
        "groups": groups,
        "containsGameRuntimeOrArt": False,
        "signed": False,
        "publishAuthorized": False,
    }
