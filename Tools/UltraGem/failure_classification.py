"""Explicit FAIL / UNKNOWN taxonomy for pre-Engine chaos evidence.

LFX-M07-010 source preparation. This parser cannot declare PASS: only the
future signed Engine host can prove simulation/replay success.
"""
from __future__ import annotations
from typing import Any

FAIL_EVENTS=frozenset({"MALFORMED_PACK","INVALID_GAME_ID","SOURCE_HASH_MISMATCH",
                        "REPLAY_HASH_DIVERGENCE","ILLEGAL_MOVE","WRONG_SCHEMA"})
UNKNOWN_EVENTS=frozenset({"SIMULATION_ABORTED","PROCESS_KILLED","TIMEOUT","OOM_BUDGET",
                           "STALE_CACHE_UNVERIFIED","NULL_RESULT","COLLISION_LOOP",
                           "ENGINE_NOT_PINNED"})


def classify_reference_failure(*, event_id: str, observed: bool,
                               evidence_reference: str | None = None) -> dict[str, Any]:
    if not isinstance(event_id,str) or event_id not in FAIL_EVENTS|UNKNOWN_EVENTS:
        raise ValueError("unknown evidence event cannot be assigned PASS")
    if type(observed) is not bool:
        raise ValueError("observed must be boolean")
    if evidence_reference is not None and (not isinstance(evidence_reference,str) or
                                          not 5<=len(evidence_reference)<=256):
        raise ValueError("evidence reference must be bounded")
    status="FAIL" if observed and event_id in FAIL_EVENTS else "UNKNOWN"
    return {
        "resultStatus":status,
        "engineStatus":"BLOCKED_ENG_M24",
        "eventId":event_id,
        "eventObserved":observed,
        "evidenceReferenceUnverified":evidence_reference,
        "acceptedGameplay":False,
        "releaseAuthorized":False,
        "reason":("Explicit negative case" if status=="FAIL" else
                  "Insufficient authoritative evidence; never infer successful replay."),
    }
