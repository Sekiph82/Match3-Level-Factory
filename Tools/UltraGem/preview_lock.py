"""In-process optimistic compare-and-swap for LOCAL preview manifests.

LFX-M09-007 source proof: simultaneous local editor threads cannot silently
replace a previously chosen preview. This is NOT a distributed R2 publisher
lock, authorization system, or replacement for final signed Engine manifests.
"""
from __future__ import annotations

import copy
import hashlib
import json
import threading
from typing import Any

from preview_diff import _index


class StalePreviewRevision(ValueError):
    pass


def _check_and_hash(manifest: dict[str, Any]) -> str:
    channel, indexed = _index(manifest)
    if channel not in ("local", "development", "staging"):
        raise ValueError("production channel cannot use preview revision protocol")
    encoded=json.dumps(manifest,ensure_ascii=False,sort_keys=True,separators=(",",":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class LocalPreviewRevisionStore:
    """Memory-only deterministic transaction receipts, no filesystem writes."""
    def __init__(self, manifest: dict[str, Any]):
        digest=_check_and_hash(manifest)
        self._lock=threading.Lock()
        self._current=copy.deepcopy(manifest)
        self._digest=digest
        self._revision=0

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "revision":self._revision,
                "manifestSha256":self._digest,
                "manifest":copy.deepcopy(self._current),
                "engineStatus":"BLOCKED_ENG_M24",
                "remotePublishAuthorized":False,
            }

    def compare_and_swap(self, *, expected_revision: int, expected_sha256: str,
                         proposed_manifest: dict[str, Any]) -> dict[str, Any]:
        digest=_check_and_hash(proposed_manifest)
        with self._lock:
            if type(expected_revision) is not int or expected_revision != self._revision or expected_sha256 != self._digest:
                raise StalePreviewRevision("local preview changed; fetch fresh snapshot and re-review")
            if proposed_manifest["channel"]!=self._current["channel"]:
                raise ValueError("cross-channel mutation forbidden")
            if digest==self._digest:
                raise ValueError("unchanged manifest does not create a new revision")
            before=self._digest
            self._current=copy.deepcopy(proposed_manifest)
            self._digest=digest
            self._revision+=1
            return {
                "resultStatus":"LOCAL_PREVIEW_CAS_ONLY",
                "engineStatus":"BLOCKED_ENG_M24",
                "previousSha256":before,
                "currentSha256":digest,
                "revision":self._revision,
                "distributedLockAcquired":False,
                "remotePublishAuthorized":False,
            }
