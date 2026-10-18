"""Evidence-bound manual reference tuning annotations (LFX-M05-008).

Never mutates LevelDraft or donor results; it annotates provisional difficulty
labels only. Actual game difficulty, release and Engine status remain unchanged.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

_LEVELS = frozenset({"UNRATED", "VERY_EASY", "EASY", "NORMAL", "HARD", "EXPERT"})


def annotate_reference_tuning(*, draft_sha256: str, original_hypothesis: str,
                              requested_label: str, rationale: str,
                              reviewer_reference: str, previous_annotation_sha256: str | None = None) -> dict[str, Any]:
    """Construct a deterministic immutable-in-spirit audit record, not an edit."""
    if not isinstance(draft_sha256, str) or re.fullmatch("[0-9a-f]{64}", draft_sha256) is None:
        raise ValueError("draft_sha256 must be 64 lowercase hex characters")
    if original_hypothesis not in _LEVELS or requested_label not in _LEVELS:
        raise ValueError("only explicitly supported provisional labels may be annotated")
    if not isinstance(rationale, str) or not 20 <= len(rationale.strip()) <= 1000:
        raise ValueError("an explanatory rationale of 20..1000 characters is required")
    if not isinstance(reviewer_reference, str) or not 5 <= len(reviewer_reference.strip()) <= 256:
        raise ValueError("a reviewer trace reference is required")
    if previous_annotation_sha256 is not None and (not isinstance(previous_annotation_sha256, str) or
                                                   re.fullmatch("[0-9a-f]{64}", previous_annotation_sha256) is None):
        raise ValueError("invalid previous annotation digest")
    record = {
        "schemaVersion": 1,
        "resultStatus": "REFERENCE_TUNING_ANNOTATION_ONLY",
        "engineStatus": "BLOCKED_ENG_M24",
        "releaseAuthorized": False,
        "draftSha256": draft_sha256,
        "originalHypothesis": original_hypothesis,
        "requestedLabel": requested_label,
        "rationale": rationale.strip(),
        "reviewerReferenceUnverified": reviewer_reference.strip(),
        "previousAnnotationSha256": previous_annotation_sha256,
    }
    payload = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    record["annotationSha256"] = hashlib.sha256(payload).hexdigest()
    return record


def verify_annotation(record: dict[str, Any], *, expected_draft_sha256: str) -> bool:
    if not isinstance(record, dict) or "annotationSha256" not in record:
        return False
    body = dict(record)
    digest = body.pop("annotationSha256")
    if type(digest) is not str or re.fullmatch("[0-9a-f]{64}", digest) is None:
        return False
    try:
        recovered = annotate_reference_tuning(
            draft_sha256=body["draftSha256"],
            original_hypothesis=body["originalHypothesis"],
            requested_label=body["requestedLabel"],
            rationale=body["rationale"],
            reviewer_reference=body["reviewerReferenceUnverified"],
            previous_annotation_sha256=body["previousAnnotationSha256"],
        )
    except (ValueError, KeyError, TypeError):
        return False
    return (recovered == record and body["draftSha256"] == expected_draft_sha256
            and body.get("engineStatus") == "BLOCKED_ENG_M24"
            and body.get("releaseAuthorized") is False)
