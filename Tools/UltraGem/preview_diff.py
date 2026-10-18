"""Content-addressed diff for local prototype manifests (LFX-M09-003).

No writes, remote object names, uploads, pointer mutation or official release.
Only preview_pack.build_preview_pack() manifests are accepted.
"""
from __future__ import annotations

from typing import Any

def _index(preview: dict[str, Any]) -> tuple[str, dict[tuple[str,str,str,str], str]]:
    if not isinstance(preview,dict) or preview.get("resultStatus")!="LOCAL_PREVIEW_MANIFEST_ONLY" or preview.get("engineStatus")!="BLOCKED_ENG_M24" or preview.get("publishAuthorized") is not False:
        raise ValueError("only local Engine-blocked preview manifests are supported")
    channel = preview.get("channel")
    if channel not in ("local","development","staging"):
        raise ValueError("production channel prohibited")
    groups=preview.get("groups")
    if not isinstance(groups,list) or len(groups)>128:
        raise ValueError("invalid preview groups")
    result={}
    for group in groups:
        if not isinstance(group,dict) or set(group)!= {"gameProfileId","worldId","chapterId","levels"}:
            raise ValueError("invalid preview group")
        levels=group["levels"]
        if not isinstance(levels,list) or len(levels)>128:
            raise ValueError("invalid levels")
        for level in levels:
            if not isinstance(level,dict) or set(level)!={"levelId","draftSha256","draftJsonUtf8Bytes","resultStatus","engineStatus"}:
                raise ValueError("invalid level manifest")
            if level["resultStatus"]!="PROTOTYPE_ONLY" or level["engineStatus"]!="BLOCKED_ENG_M24":
                raise ValueError("unexpected level status")
            digest=level["draftSha256"]
            if not isinstance(digest,str) or len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError("invalid digest")
            key=(group["gameProfileId"],group["worldId"],group["chapterId"],level["levelId"])
            if key in result or len(result)>=128:
                raise ValueError("duplicate or too many level identities")
            result[key]=digest
    if preview.get("levelCount")!=len(result):
        raise ValueError("declared level count mismatch")
    return channel,result


def diff_preview_manifests(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    old_channel, before=_index(old)
    new_channel,after=_index(new)
    if old_channel!=new_channel:
        raise ValueError("cross-channel diffs require separate review")
    created=[];updated=[];deleted=[];unchanged=[]
    for key in sorted(set(before)|set(after)):
        key_string="/".join(key)
        if key not in before:
            created.append({"levelPath":key_string,"newSha256":after[key]})
        elif key not in after:
            deleted.append({"levelPath":key_string,"previousSha256":before[key]})
        elif before[key]!=after[key]:
            updated.append({"levelPath":key_string,"previousSha256":before[key],"newSha256":after[key]})
        else:
            unchanged.append({"levelPath":key_string,"draftSha256":after[key]})
    return {
        "resultStatus":"LOCAL_PREVIEW_DIFF_ONLY",
        "engineStatus":"BLOCKED_ENG_M24",
        "channel":old_channel,
        "created":created,"updated":updated,"deleted":deleted,"unchanged":unchanged,
        "publishAuthorized":False,
        "deleteRemoteObjectsAuthorized":False,
        "immutableRuntimeObjectNamesGenerated":False,
    }
