"""Offline M10 operations checklist; never performs provider or production actions."""
from __future__ import annotations

import json
import re
from typing import Any

from theme_contract import PROFILES


CHECKS = (
    ("incident_record", "Incident record identifies the affected profile and scope."),
    ("known_good_manifest", "Known-good manifest/version and its immutable digest are identified."),
    ("rollback_plan", "Rollback target and bounded rollback plan are documented."),
    ("owner_approval", "Owner approval is recorded for this exact incident and rollback scope."),
    ("expired_key_identifier", "Expired credential is identified by a non-secret provider reference only."),
    ("rotation_request", "Owner/provider rotation request and change window are documented."),
    ("new_key_validation", "Provider-side new-key validation receipt is available without exposing key bytes."),
    ("old_key_revocation", "Provider-side old-key revocation receipt is available without exposing key bytes."),
    ("client_rollback_validation", "Real Engine client rollback and cache-fallback evidence is available."),
    ("incident_review", "Post-incident review and independent evidence review are recorded."),
)

_REFERENCE_ID_PATTERNS = {
    "ticket": re.compile(r"(?:LFX-M10-007-[0-9]{2}|INC-[A-Z0-9]{2,12}-[0-9]{4,12})", re.I),
    "drive": re.compile(r"[A-Za-z0-9_-]{25,64}"),
    "audit": re.compile(r"(?:AUD-LFX-M10-007-[0-9]{2}|AUD-[0-9]{4}-[0-9]{2})", re.I),
    "build": re.compile(r"(?:BUILD|GH)-[0-9]{6,20}", re.I),
    "provider": re.compile(r"(?:CASE|INC|CHG|ROT|VALID|REVOKE)-[A-Z0-9]{2,16}-[0-9]{3,15}", re.I),
    "owner": re.compile(r"APPROVAL-INC-[0-9]{3,12}", re.I),
}
_SECRET_ASSIGNMENT = re.compile(r"(?i)(?:token|password|secret|bearer|api[_-]?key)\s*[:=]")
_SECRET_WORD = re.compile(r"(?i)(?:^|[._/-])(?:secret|password|bearer|token)(?:$|[._/-])")
_TOKEN_SHAPED_VALUE = re.compile(
    r"(?i)(?:gh[pousr]_[a-z0-9_]{20,}|github_pat_[a-z0-9_]{20,}|"
    r"(?:sk|rk)_(?:live|test)_[a-z0-9]{12,}|"
    r"xox[baprs]-[a-z0-9-]{20,}|AIza[a-z0-9_-]{30,}|"
    r"azdpat_[a-z0-9]{20,}|glpat-[a-z0-9_-]{20,}|"
    r"npm_[a-z0-9]{20,}|hf_[a-z0-9]{20,}|pypi-[a-z0-9_-]{20,})"
)
_MAX_REFERENCE_JSON_CHARS = 4_096


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Build a JSON object while rejecting keys a normal dict would erase."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_nonfinite_json(value: str) -> None:
    raise ValueError(f"non-finite JSON value is not allowed: {value}")


def build_operations_checklist_from_json(*, profile_id: str, incident_id: str,
                                         evidence_references_json: str) -> dict[str, Any]:
    """Parse untrusted reference JSON without losing duplicate-key evidence.

    The regular Python-dict API cannot detect duplicate keys already collapsed
    by a caller's JSON parser. This bounded entry point checks duplicates before
    passing the exact object through the same offline validation path.
    """
    if (not isinstance(evidence_references_json, str)
            or len(evidence_references_json) > _MAX_REFERENCE_JSON_CHARS):
        raise ValueError("evidence reference JSON must be a string of at most 4096 characters")
    try:
        references = json.loads(
            evidence_references_json,
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=_reject_nonfinite_json,
        )
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError("invalid evidence reference JSON") from exc
    if not isinstance(references, dict):
        raise ValueError("evidence reference JSON must contain one object")
    return build_operations_checklist(
        profile_id=profile_id,
        incident_id=incident_id,
        evidence_references=references,
    )


def build_operations_checklist(*, profile_id: str, incident_id: str,
                               evidence_references: dict[str, str] | None = None) -> dict[str, Any]:
    """Build a deterministic, non-authoritative checklist from opaque references.

    A reference is merely a locator claim: it is never fetched or verified here.
    Even a complete reference set cannot authorize rollback, key rotation,
    publication, or any production action.
    """
    if not isinstance(profile_id, str) or profile_id not in PROFILES:
        raise ValueError("unknown game profile")
    if not isinstance(incident_id, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", incident_id) is None:
        raise ValueError("invalid incident identity")
    if evidence_references is None:
        evidence_references = {}
    if not isinstance(evidence_references, dict):
        raise ValueError("evidence references must be an object")
    expected = {key for key, _ in CHECKS}
    if any(not isinstance(key, str) or key not in expected for key in evidence_references):
        raise ValueError("unknown checklist evidence reference")

    normalized: dict[str, str] = {}
    for key, value in evidence_references.items():
        namespace, separator, identifier = value.partition("/") if isinstance(value, str) else ("", "", "")
        identifier_pattern = _REFERENCE_ID_PATTERNS.get(namespace)
        if (not isinstance(value, str) or len(value) > 128 or not separator
                or identifier_pattern is None or identifier_pattern.fullmatch(identifier) is None
                or ".." in value
                or _SECRET_ASSIGNMENT.search(value)
                or _SECRET_WORD.search(value)):
            raise ValueError(f"invalid opaque evidence reference for {key}")
        if _TOKEN_SHAPED_VALUE.search(value):
            raise ValueError(f"token-shaped evidence reference is not allowed for {key}")
        normalized[key] = value

    checklist = [{
        "checkId": key,
        "requirement": description,
        "evidenceReferenceUnverified": normalized.get(key),
        "status": "REFERENCE_UNVERIFIED" if key in normalized else "MISSING",
        "executionPerformed": False,
    } for key, description in CHECKS]
    missing = [item["checkId"] for item in checklist if item["status"] == "MISSING"]
    return {
        "schemaVersion": 1,
        "resultStatus": "OFFLINE_OPERATIONS_CHECKLIST_ONLY",
        "checklistStatus": "CANDIDATE_REFERENCES_COMPLETE_UNVERIFIED" if not missing else "INCOMPLETE_REFERENCES",
        "gameProfileId": profile_id,
        "incidentId": incident_id,
        "checks": checklist,
        "missingEvidenceCheckIds": missing,
        "ownerApprovalReferenceRecorded": "owner_approval" in normalized,
        "ownerApprovalVerified": False,
        "evidenceReferencesVerified": False,
        "engineStatus": "BLOCKED_ENG_M24",
        "productionEnabled": False,
        "productionAuthorization": False,
        "publishAuthorized": False,
        "writerCredentialsLoaded": False,
        "networkOrProviderAccessPerformed": False,
        "rollbackExecuted": False,
        "keyRotationExecuted": False,
        "keyRevocationExecuted": False,
        "clientRollbackValidated": False,
        "officialTaskPass": False,
    }
