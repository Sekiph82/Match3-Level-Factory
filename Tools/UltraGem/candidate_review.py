"""Candidate review state machine with a hard commercial publication gate.

LFX-M06-009. Human review is required even for reference prototypes.
A reviewer reference is provenance metadata, NOT cryptographic proof of
identity, and never grants MATCH3_ENGINE certification or remote upload.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

STATES = ("GENERATED", "REVIEW_REQUIRED", "APPROVED_FOR_REFERENCE_TESTS", "REJECTED")
SHA_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


def new_review_ticket(*, candidate_sha256: str, source_sha256: str, generator_seed: int) -> dict[str, Any]:
    if any(not isinstance(v, str) or SHA_PATTERN.fullmatch(v) is None for v in (candidate_sha256, source_sha256)):
        raise ValueError("source and candidate SHA256 must be lowercase SHA256")
    if type(generator_seed) is not int or not 0 <= generator_seed < 2**63:
        raise ValueError("invalid generator seed")
    record = {
        "schemaVersion": 1,
        "status": "REVIEW_REQUIRED",
        "resultStatus": "REFERENCE_REVIEW_ONLY",
        "engineStatus": "BLOCKED_ENG_M24",
        "candidateSha256": candidate_sha256,
        "sourceSha256": source_sha256,
        "generatorSeed": generator_seed,
        "reviewerReference": None,
        "reviewRationale": None,
        "releaseAuthorized": False,
    }
    record["recordSha256"] = _digest(record)
    return record


def decide_reference_ticket(ticket: dict[str, Any], *, approved: bool,
                            reviewer_reference: str, rationale: str,
                            expected_candidate_sha256: str) -> dict[str, Any]:
    if not verify_review_ticket(ticket) or ticket["status"] != "REVIEW_REQUIRED":
        raise ValueError("only intact unreviewed tickets can be decided")
    if ticket["candidateSha256"] != expected_candidate_sha256:
        raise ValueError("candidate changed since ticket was created")
    if type(approved) is not bool:
        raise ValueError("approved must be boolean")
    if not isinstance(reviewer_reference, str) or not 5 <= len(reviewer_reference.strip()) <= 256:
        raise ValueError("reviewer reference is required")
    if not isinstance(rationale, str) or not 20 <= len(rationale.strip()) <= 1000:
        raise ValueError("detailed rationale required")
    result = dict(ticket)
    result["status"] = "APPROVED_FOR_REFERENCE_TESTS" if approved else "REJECTED"
    result["reviewerReference"] = reviewer_reference.strip()
    result["reviewRationale"] = rationale.strip()
    result["recordSha256"] = _digest(result)
    return result


def verify_review_ticket(ticket: dict[str, Any]) -> bool:
    if not isinstance(ticket, dict) or set(ticket) != {
        "schemaVersion", "status", "resultStatus", "engineStatus", "candidateSha256",
        "sourceSha256", "generatorSeed", "reviewerReference", "reviewRationale",
        "releaseAuthorized", "recordSha256",
    }:
        return False
    if (ticket["schemaVersion"] != 1 or ticket["resultStatus"] != "REFERENCE_REVIEW_ONLY"
        or ticket["engineStatus"] != "BLOCKED_ENG_M24" or ticket["releaseAuthorized"] is not False
        or ticket["status"] not in STATES[1:]):
        return False
    if type(ticket["generatorSeed"]) is not int or not 0 <= ticket["generatorSeed"] < 2**63:
        return False
    if any(not isinstance(ticket[k], str) or SHA_PATTERN.fullmatch(ticket[k]) is None
           for k in ("candidateSha256", "sourceSha256", "recordSha256")):
        return False
    if ticket["status"] == "REVIEW_REQUIRED":
        if ticket["reviewerReference"] is not None or ticket["reviewRationale"] is not None:
            return False
    elif (not isinstance(ticket["reviewerReference"], str) or not 5 <= len(ticket["reviewerReference"]) <= 256
          or not isinstance(ticket["reviewRationale"], str) or not 20 <= len(ticket["reviewRationale"]) <= 1000):
        return False
    return ticket["recordSha256"] == _digest(ticket)


def _digest(record: dict[str, Any]) -> str:
    body = {k: v for k, v in record.items() if k != "recordSha256"}
    payload = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
