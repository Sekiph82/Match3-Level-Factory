"""Fail-closed preview release-file inventory and attribution exclusion.

LFX-M09-010. Static path/type/rights screen only, not a pack archive parser,
binary scanner or game-release signoff. No production content is emitted.
"""
from __future__ import annotations

import re
from typing import Any

MAX_ENTRIES=256
MAX_PREVIEW_BYTES=200_000_000
ALLOWED_ROOTS={"levels","localization","media"}
ALLOWED_JSON_SUFFIXES=(".json",)
ALLOWED_MEDIA_SUFFIXES=(".png",".webp",".svg")
FORBIDDEN_SEGMENTS={
    ".git",".github","assets","tests","tools","editor","unity","temp",
    "coordination","logs","evidence","audits","build","cache","thirdparty",
    "plugins","private","credentials","secrets","source",
}
FORBIDDEN_TOKENS=("apikey","api_key","token","secret","password","credential",
                  "privatekey","private_key","r2writer","cert","firebase")


def validate_preview_file_inventory(entries: list[dict[str,Any]]) -> dict[str,Any]:
    if not isinstance(entries,list) or len(entries)>MAX_ENTRIES:
        raise ValueError("file inventory must be bounded")
    seen=set()
    accepted=[]
    denied=[]
    for index,record in enumerate(entries):
        if not isinstance(record,dict) or set(record)!={"path","sha256","sizeBytes","kind","rightsStatus"}:
            raise ValueError("invalid file manifest schema")
        path=record["path"]
        digest=record["sha256"]
        size=record["sizeBytes"]
        kind=record["kind"]
        rights=record["rightsStatus"]
        if not isinstance(path,str) or not 3<=len(path)<=240 or not path.isascii() or (
            re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*",path) is None or
            ".." in path.split("/") or "." in path.split("/") or "//" in path or path.startswith("/")):
            raise ValueError("invalid relative inventory path")
        normalized=path.lower()
        if normalized in seen:
            raise ValueError("duplicate or case-colliding path")
        seen.add(normalized)
        if not isinstance(digest,str) or re.fullmatch(r"[0-9a-f]{64}",digest) is None:
            raise ValueError("file digest must be SHA256")
        if type(size) is not int or not 0<size<=MAX_PREVIEW_BYTES:
            raise ValueError("file size invalid")
        if kind not in {"LEVEL_JSON","LOCALIZATION_JSON","MEDIA"} or rights not in {
            "OWNER_ORIGINAL","LICENSE_REVIEWED","REFERENCE_ONLY","RIGHTS_UNKNOWN","UNLICENSED"}:
            raise ValueError("unknown file kind or rights status")
        segs=normalized.split("/")
        reasons=[]
        if segs[0] not in ALLOWED_ROOTS or any(s in FORBIDDEN_SEGMENTS for s in segs):
            reasons.append("NON_PLAYER_OR_FORBIDDEN_SOURCE_PATH")
        if any(t in normalized for t in FORBIDDEN_TOKENS) or normalized.endswith((".cs",".py",".dll",".asmdef",".unity",".prefab",".meta",".env",".p12",".key")):
            reasons.append("EXECUTABLE_SECRET_OR_PROJECT_FILE")
        if kind=="LEVEL_JSON" and (segs[0]!="levels" or not normalized.endswith(ALLOWED_JSON_SUFFIXES)):
            reasons.append("INVALID_LEVEL_ASSET_ROUTE")
        if kind=="LOCALIZATION_JSON" and (segs[0]!="localization" or not normalized.endswith(ALLOWED_JSON_SUFFIXES)):
            reasons.append("INVALID_LOCALIZATION_ROUTE")
        if kind=="MEDIA" and (segs[0]!="media" or not normalized.endswith(ALLOWED_MEDIA_SUFFIXES)):
            reasons.append("INVALID_MEDIA_ROUTE")
        if kind=="MEDIA" and rights not in {"OWNER_ORIGINAL","LICENSE_REVIEWED"}:
            reasons.append("NO_DISTRIBUTION_RIGHTS_EVIDENCE")
        item={"path":path,"sha256":digest,"sizeBytes":size,"kind":kind,
              "rightsStatus":rights,"sourceInventoryScreen":"REVIEW_CANDIDATE" if not reasons else "REJECTED",
              "reasons":reasons}
        (denied if reasons else accepted).append(item)
    return {
        "resultStatus":"PREVIEW_RELEASE_INVENTORY_SCREEN_ONLY",
        "engineStatus":"BLOCKED_ENG_M24",
        "runtimePackInspected":False,
        "productionReleaseAuthorized":False,
        "acceptedForFurtherInspection":sorted(accepted,key=lambda x:x["path"]),
        "denied":sorted(denied,key=lambda x:x["path"]),
        "remainingGates":["ACTUAL_ARCHIVE_BYTE_SCAN","LICENSE_REVIEW","ENG_M24","SIGNED_PACK","OWNER_APPROVAL"],
    }
