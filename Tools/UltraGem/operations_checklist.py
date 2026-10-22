"""Offline M10 operations checklist; never performs provider or production actions."""
from __future__ import annotations

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

_ALLOWED_REFERENCE = re.compile(r"^(?:ticket|drive|audit|build|provider|owner)/[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
_SECRET_ASSIGNMENT = re.compile(r"(?i)(?:token|password|secret|bearer|api[_-]?key)\s*[:=]")
_SECRET_WORD = re.compile(r"(?i)(?:^|[._/-])(?:secret|password|bearer|token)(?:$|[._/-])")


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
        if (not isinstance(value, str) or len(value) > 128
                or _ALLOWED_REFERENCE.fullmatch(value) is None
                or ".." in value
                or _SECRET_ASSIGNMENT.search(value)
                or _SECRET_WORD.search(value)):
            raise ValueError(f"invalid opaque evidence reference for {key}")
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
