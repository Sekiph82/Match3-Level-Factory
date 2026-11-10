"""LFX-M14-003: Offline staging manifest validation — OTA replay prototype.

PROTOTYPE_ONLY. Validates structural integrity of staging-only level-pack
manifests for five game profiles. No network, R2, CDN, Engine resolution, or
production distribution is performed. ENG-M24 acceptance is required before
any official milestone PASS or release authorization.

Claims preserved across update: each loaded manifest keeps an immutable list
of previously observed claim IDs from the caller. No server idempotency or
grant execution is performed here.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from theme_contract import PROFILES

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_PROFILE_SET = frozenset(PROFILES)

# Minimum schema version the Factory understands (PROTOTYPE_ONLY).
_FACTORY_SCHEMA_MIN = 1
# Maximum schema version the Factory understands (PROTOTYPE_ONLY).
_FACTORY_SCHEMA_MAX = 1

# Engine schema version expected; replaced when ENG-M24 is accepted.
_ENGINE_SCHEMA_VERSION = "BLOCKED_ENG_M24"


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_manifest(manifest: Any) -> dict[str, Any]:
    """Validate a staging manifest and return a receipt.

    Parameters
    ----------
    manifest:
        A dict (or JSON-parsed object) with the staging manifest fields.

    Returns
    -------
    dict with status, profileId, version and any corruption findings.
    Raises ValueError for missing/invalid fields.
    """
    _require(isinstance(manifest, dict), "manifest must be a dict")

    profile_id = manifest.get("profileId")
    _require(isinstance(profile_id, str) and profile_id in _PROFILE_SET,
             f"profileId must be one of {sorted(_PROFILE_SET)!r}")

    version = manifest.get("version")
    _require(isinstance(version, int) and version >= 1,
             "version must be a positive integer")

    level_pack_sha = manifest.get("levelPackSha256")
    _require(isinstance(level_pack_sha, str) and bool(_SHA256.match(level_pack_sha)),
             "levelPackSha256 must be a 64-hex-char string")

    schema_ver = manifest.get("schemaVersion")
    _require(isinstance(schema_ver, int) and
             _FACTORY_SCHEMA_MIN <= schema_ver <= _FACTORY_SCHEMA_MAX,
             f"schemaVersion must be int in [{_FACTORY_SCHEMA_MIN},{_FACTORY_SCHEMA_MAX}]")

    engine_min = manifest.get("engineSchemaVersionMin")
    _require(isinstance(engine_min, int) and engine_min >= 1,
             "engineSchemaVersionMin must be a positive integer")

    # Integrity check: if integrityDigest is present, verify it covers the
    # canonical key set (profileId, version, levelPackSha256, schemaVersion).
    integrity_status = "NOT_PROVIDED"
    if "integrityDigest" in manifest:
        canonical = json.dumps(
            {k: manifest[k] for k in
             ("profileId", "version", "levelPackSha256", "schemaVersion")},
            sort_keys=True, separators=(",", ":"))
        expected = _sha256_bytes(canonical.encode())
        if manifest["integrityDigest"] == expected:
            integrity_status = "VALID"
        else:
            integrity_status = "CORRUPTED"

    claims: list[str] = []
    if "claimIds" in manifest:
        raw_claims = manifest["claimIds"]
        _require(isinstance(raw_claims, list),
                 "claimIds must be a list")
        for cid in raw_claims:
            _require(isinstance(cid, str) and cid,
                     "each claimId must be a non-empty string")
        claims = list(raw_claims)

    return {
        "status": "VALID" if integrity_status != "CORRUPTED" else "CORRUPTED",
        "profileId": profile_id,
        "version": version,
        "integrityStatus": integrity_status,
        "claimsPreserved": claims,
        "engineSchemaVersionMin": engine_min,
        "engineStatus": _ENGINE_SCHEMA_VERSION,
        "prototype": True,
        "productionAuthorized": False,
    }


def apply_update(old_manifest: dict[str, Any],
                 new_manifest: dict[str, Any]) -> dict[str, Any]:
    """Simulate applying an OTA manifest update.

    Rules:
    - New version must be strictly greater than old version.
    - profileId must match.
    - Previous manifest SHA is recorded for rollback.
    - Claims from the old manifest are merged (preserved) into the new receipt.

    Returns a receipt dict or raises ValueError.
    """
    old_receipt = validate_manifest(old_manifest)
    new_receipt = validate_manifest(new_manifest)

    _require(old_receipt["profileId"] == new_receipt["profileId"],
             "profileId mismatch between old and new manifest")
    _require(new_manifest["version"] > old_manifest["version"],
             "new manifest version must be strictly greater than old version")
    _require(old_receipt["status"] != "CORRUPTED",
             "cannot update from a CORRUPTED manifest")
    _require(new_receipt["status"] != "CORRUPTED",
             "cannot apply a CORRUPTED new manifest")

    # Record rollback pointer (SHA256 of canonical old manifest JSON).
    old_canonical = json.dumps(old_manifest, sort_keys=True,
                               separators=(",", ":"))
    rollback_sha = _sha256_bytes(old_canonical.encode())

    # Merge claims: union of old + new claim IDs.
    all_claims = sorted(set(old_receipt["claimsPreserved"]) |
                        set(new_receipt["claimsPreserved"]))

    return {
        "status": "UPDATE_APPLIED",
        "profileId": new_receipt["profileId"],
        "oldVersion": old_manifest["version"],
        "newVersion": new_manifest["version"],
        "rollbackManifestSha256": rollback_sha,
        "claimsPreserved": all_claims,
        "engineSchemaVersionMin": new_manifest["engineSchemaVersionMin"],
        "engineStatus": _ENGINE_SCHEMA_VERSION,
        "prototype": True,
        "productionAuthorized": False,
    }


def check_rollback(current_manifest: dict[str, Any],
                   previous_manifest: dict[str, Any]) -> dict[str, Any]:
    """Verify that previous_manifest is a valid rollback target.

    Returns a receipt confirming rollback eligibility or raises ValueError.
    The previous manifest must have a lower version and matching profileId.
    """
    cur_receipt = validate_manifest(current_manifest)
    prev_receipt = validate_manifest(previous_manifest)

    _require(cur_receipt["profileId"] == prev_receipt["profileId"],
             "profileId mismatch in rollback check")
    _require(previous_manifest["version"] < current_manifest["version"],
             "rollback target must have a lower version than current")
    _require(prev_receipt["status"] != "CORRUPTED",
             "rollback target manifest is CORRUPTED — rollback unsafe")

    # Claims from current manifest must still be preserved after rollback.
    merged_claims = sorted(set(cur_receipt["claimsPreserved"]) |
                           set(prev_receipt["claimsPreserved"]))

    return {
        "status": "ROLLBACK_ELIGIBLE",
        "profileId": cur_receipt["profileId"],
        "currentVersion": current_manifest["version"],
        "rollbackVersion": previous_manifest["version"],
        "claimsPreserved": merged_claims,
        "engineSchemaVersionMin": previous_manifest["engineSchemaVersionMin"],
        "engineStatus": _ENGINE_SCHEMA_VERSION,
        "prototype": True,
        "productionAuthorized": False,
    }


def check_engine_compatibility(manifest: dict[str, Any],
                               installed_version: int) -> dict[str, Any]:
    """Check whether a manifest's engineSchemaVersionMin is satisfied.

    Parameters
    ----------
    manifest:
        Staging manifest dict.
    installed_version:
        The engine schema version currently installed (simulated; real
        value requires ENG-M24).

    Returns a receipt with compatibilityStatus COMPATIBLE or INCOMPATIBLE.
    Raises ValueError for invalid inputs.
    """
    receipt = validate_manifest(manifest)
    _require(isinstance(installed_version, int) and installed_version >= 1,
             "installed_version must be a positive integer")

    compatible = installed_version >= receipt["engineSchemaVersionMin"]
    return {
        "status": "ENGINE_COMPAT_CHECK",
        "profileId": receipt["profileId"],
        "manifestVersion": manifest["version"],
        "requiredEngineSchemaVersionMin": receipt["engineSchemaVersionMin"],
        "installedEngineSchemaVersion": installed_version,
        "compatibilityStatus": "COMPATIBLE" if compatible else "INCOMPATIBLE",
        "engineStatus": _ENGINE_SCHEMA_VERSION,
        "prototype": True,
        "productionAuthorized": False,
    }


def replay_staging_sequence(sequence: list[dict[str, Any]]) -> dict[str, Any]:
    """Replay a sequence of manifest updates for a single profile.

    Validates each step in order: load, then apply each subsequent update.
    Returns a summary receipt. Raises ValueError on the first invalid step.

    Parameters
    ----------
    sequence:
        Ordered list of manifest dicts (oldest first). Must have at least 2.
    """
    _require(isinstance(sequence, list) and len(sequence) >= 2,
             "sequence must be a list of at least 2 manifests")

    receipts: list[dict[str, Any]] = []
    current = sequence[0]
    receipts.append(validate_manifest(current))

    for nxt in sequence[1:]:
        step = apply_update(current, nxt)
        receipts.append(step)
        current = nxt

    # Final validation of the last manifest.
    final = validate_manifest(current)
    all_claims = sorted({c for r in receipts for c in r.get("claimsPreserved", [])})

    return {
        "status": "SEQUENCE_REPLAYED",
        "profileId": final["profileId"],
        "steps": len(sequence),
        "finalVersion": current["version"],
        "claimsPreserved": all_claims,
        "engineStatus": _ENGINE_SCHEMA_VERSION,
        "prototype": True,
        "productionAuthorized": False,
        "officialMilestonePass": False,
    }
