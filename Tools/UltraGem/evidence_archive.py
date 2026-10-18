"""Fail-closed evidence/archive routing policy, independent of ENG-M24.

LFX-M07-011 source preparation. Decide where evidence *may* live.
No uploader, file deletion, file discovery, secrets or remote network calls.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import PurePosixPath
from typing import Any

MAX_FILES = 256
MAX_FILE_BYTES = 25_000_000
ALLOWED_KINDS = frozenset({"SOURCE_FIXTURE", "TEST_SOURCE", "RAW_NUNIT", "RAW_SIMULATION",
                           "REPLAY_TRACE", "PROFILE_TRACE", "SCREENSHOT", "PROFILE_METRICS"})
GITHUB_KINDS = frozenset({"SOURCE_FIXTURE", "TEST_SOURCE"})
NEVER_BUNDLE_DIRS = frozenset({"logs", "tests", "tools", "coordination", "evidence",
                               "audits", "editor", "thirdparty", ".git", ".github"})
DRIVE_FOLDER = "05_EVIDENCE"


def _safe_path(name: str) -> str:
    if not isinstance(name, str) or not name or len(name) > 240 or "\\" in name or "\x00" in name or ":" in name:
        raise ValueError("path must be a bounded relative POSIX path")
    p = PurePosixPath(name)
    if p.is_absolute() or "." in name.split("/") or ".." in name.split("/") or "//" in name:
        raise ValueError("absolute or traversing paths are forbidden")
    return p.as_posix()


def build_evidence_routing(entries: list[dict[str, Any]], *, source_commit_sha: str,
                           engine_status: str = "BLOCKED_ENG_M24") -> dict[str, Any]:
    if not isinstance(source_commit_sha, str) or re.fullmatch("[0-9a-f]{40}", source_commit_sha) is None:
        raise ValueError("source git SHA must be exact lowercase 40 hex")
    if engine_status != "BLOCKED_ENG_M24":
        raise ValueError("no final Engine evidence authority is available")
    if not isinstance(entries, list) or len(entries) > MAX_FILES:
        raise ValueError("evidence input must be a bounded list")
    seen = set()
    rows = []
    for item in entries:
        if not isinstance(item, dict) or set(item) != {"path", "kind", "bytes"}:
            raise ValueError("evidence records must contain path, kind and bytes only")
        name = _safe_path(item["path"])
        if name in seen:
            raise ValueError("duplicate evidence path")
        seen.add(name)
        kind = item["kind"]
        data = item["bytes"]
        if kind not in ALLOWED_KINDS or type(data) is not bytes or len(data) > MAX_FILE_BYTES:
            raise ValueError("unsupported evidence type or oversized bytes")
        if kind in GITHUB_KINDS and len(data) > 100_000:
            raise ValueError("source fixtures must be tiny, not raw evidence dumps")
        # Every raw result stays Drive-only. Even source fixture files cannot
        # be placed in runtime asset-bundle folders.
        destination = "GITHUB_TRACKED_SOURCE" if kind in GITHUB_KINDS else "DRIVE_05_EVIDENCE"
        rows.append({
            "path": name, "kind": kind, "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "storageRoute": destination,
            "excludeFromPlayerAndAddressables": True,
        })
    return {
        "resultStatus": "SOURCE_ARCHIVE_ROUTING_ONLY",
        "engineStatus": engine_status,
        "sourceCommit": source_commit_sha,
        "archiveFolder": DRIVE_FOLDER,
        "releaseAuthorized": False,
        "files": sorted(rows, key=lambda item: item["path"]),
        "excludedPlayerFolders": sorted(NEVER_BUNDLE_DIRS),
    }


def verify_local_manifest(manifest: dict[str, Any], files: dict[str, bytes]) -> bool:
    """Verify user-supplied byte mapping without filesystem reads or writes."""
    if not isinstance(manifest, dict) or manifest.get("releaseAuthorized") is not False:
        return False
    entries = manifest.get("files")
    if not isinstance(entries, list) or not isinstance(files, dict):
        return False
    try:
        rebuilt = build_evidence_routing(
            [{"path": name, "kind": row["kind"], "bytes": files[name]}
             for row in entries for name in [row["path"]]],
            source_commit_sha=manifest["sourceCommit"],
            engine_status=manifest["engineStatus"])
        return rebuilt == manifest and len(files) == len(entries)
    except (ValueError, KeyError, TypeError):
        return False
