"""LFX-M10 offline R2/client-delivery milestone-wide safety gate.

Pure Python, local-only. This prepares inspectable *plans* for all ten M10
tasks; it is not a Cloudflare client, signer, CDN, launcher or live publisher.
The authoritative ENG-M24 package, rights, owner and device gates remain open.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

from disabled_levels import propose_disabled_levels
from publish_preflight import assess_remote_publish_preflight
from release_plan import plan_r2_topology
from theme_contract import PROFILES

_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_PATH = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,239}\Z")
_CHANNELS = {"development", "staging", "production"}
_PLATFORMS = {"android", "ios", "windows"}
_KINDS = {
    "level": ("levels/", ".json", "levels"),
    "localization": ("localization/", ".json", "levels"),
    "media_png": ("media/", ".png", "media"),
    "media_webp": ("media/", ".webp", "media"),
    "media_svg": ("media/", ".svg", "media"),
}
_FORBIDDEN = ("code", "script", "assembly", "dll", "exe", "wasm",
              "prefab", "scene", "runtime", "plugin", "credential",
              "secret", "token", "behavior", "feature", "ads", "iap")
_TASKS = tuple(f"LFX-M10-{i:03d}" for i in range(1, 11))
_GATES = (
    "ENG_M24_CANONICAL_SIGNED_PACK_MISSING",
    "SIGNED_MANIFEST_AND_TRUSTED_CLIENT_VERIFIER_MISSING",
    "INDEPENDENT_OWNER_AND_RIGHTS_APPROVAL_MISSING",
    "R2_WRITER_AUTH_AND_OBJECT_READ_SMOKE_NOT_PERFORMED",
    "ACTUAL_CLIENT_OFFLINE_FALLBACK_AND_CANARY_NOT_RUN",
    "ATOMIC_REMOTE_POINTER_AND_ROLLBACK_NOT_PROVEN",
    "EMERGENCY_IN_GAME_SAFE_FRONTIER_NOT_PROVEN",
)


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
        raise ValueError(label + " must be a lowercase SHA256")
    return value


def _validate_artifact(item: dict[str, Any], game_id: str) -> dict[str, Any]:
    if not isinstance(item, dict) or set(item) != {
        "gameProfileId", "relativePath", "kind", "body", "rightsStatus"
    }:
        raise ValueError("local artifact has unknown/missing schema fields")
    if item["gameProfileId"] != game_id:
        raise ValueError("cross-title artifact cannot be imported")
    kind = item["kind"]
    if kind not in _KINDS:
        raise ValueError("new code, metadata behavior or unreviewed asset kind forbidden")
    prefix, suffix, topology_kind = _KINDS[kind]
    path = item["relativePath"]
    if not isinstance(path, str) or _PATH.fullmatch(path) is None:
        raise ValueError("invalid relative content path")
    if (not path.startswith(prefix) or not path.endswith(suffix)
            or len(path.split("/")) < 2
            or any(x in ("", ".", "..") for x in path.split("/"))
            or any(bad in path.lower().split("/") for bad in _FORBIDDEN)):
        raise ValueError("unrecognized content path or prohibited code/credential route")
    if kind.startswith("media_") and item["rightsStatus"] not in (
            "OWNER_ORIGINAL", "LICENSE_REVIEWED"):
        raise ValueError("distribution rights evidence not established")
    if not kind.startswith("media_") and item["rightsStatus"] not in (
            "OWNER_ORIGINAL", "LICENSE_REVIEWED", "REFERENCE_ONLY"):
        raise ValueError("unknown file rights declaration")
    body = item["body"]
    if not isinstance(body, bytes) or not 1 <= len(body) <= 8_000_000:
        raise ValueError("bounded actual content bytes required")
    # Read, hash and retain only checksums and counts; never put bytes into
    # a response, Git history, a secret-bearing build, or any R2 write.
    import io
    import zipfile
    from preview_archive_scan import scan_preview_archive
    from content_exclusion import validate_preview_file_inventory

    inventory_kind = ("MEDIA" if kind.startswith("media_") else
                      "LOCALIZATION_JSON" if kind == "localization" else "LEVEL_JSON")
    digest = hashlib.sha256(body).hexdigest()
    record = {
        "path": path, "sha256": digest, "sizeBytes": len(body),
        "kind": inventory_kind, "rightsStatus": item["rightsStatus"],
    }
    if validate_preview_file_inventory([record])["denied"]:
        raise ValueError("content route or rights failed local exclusion preflight")
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as zf:
        zf.writestr(path, body)
    # Strict JSON/SVG structure + forbidden credential-like byte screening,
    # not just a claimed hash; inspect *real* staged prototype bytes.
    scanned = scan_preview_archive(stream.getvalue(), [record])
    if scanned["fileCount"] != 1 or scanned["productionReleaseAuthorized"] is not False:
        raise ValueError("actual prototype archive byte screen failed")
    return {
        "relativePath": path,
        "kind": kind,
        "contentSha256": digest,
        "bytesVerified": len(body),
        "topologyKind": topology_kind,
        "legalRightsIndependentlyVerified": False,
        "engineSchemaVerified": False,
        "distributionAuthorized": False,
    }


def preflight_m10_milestone(*, game_id: str, channel: str, platform: str,
                            git_commit_sha: str, manifest_sha256: str,
                            artifacts: list[dict[str, Any]],
                            owner_review_reference: str | None = None,
                            incident_affected: list[dict[str, Any]] | None = None
                            ) -> dict[str, Any]:
    """One bounded, deterministic whole-M10 rehearsal, absolutely no network.

    Real publisher auth, signed CDN pointers, client game replay and official
    Engine-provided proof cannot be substituted by these offline checks.
    """
    if game_id not in PROFILES or channel not in _CHANNELS or platform not in _PLATFORMS:
        raise ValueError("unsupported title, channel or target platform")
    if not isinstance(git_commit_sha, str) or _HEX40.fullmatch(git_commit_sha) is None:
        raise ValueError("invalid claimed source commit")
    _sha(manifest_sha256, "manifestSha256")
    if not isinstance(artifacts, list) or not 1 <= len(artifacts) <= 32:
        raise ValueError("bounded actual artifact list required")
    if owner_review_reference is not None and (
        not isinstance(owner_review_reference, str)
        or not 5 <= len(owner_review_reference.strip()) <= 256
        or any(ord(ch) < 32 for ch in owner_review_reference)
    ):
        raise ValueError("invalid unverified owner note")
    if incident_affected is not None and owner_review_reference is None:
        raise ValueError("incident rehearsal requires owner review reference")

    inspected = [_validate_artifact(record, game_id) for record in artifacts]
    if sum(entry["bytesVerified"] for entry in inspected) > 32_000_000:
        raise ValueError("total local bytes exceed bounded rehearsal")
    if len(set(entry["relativePath"].lower() for entry in inspected)) != len(inspected):
        raise ValueError("duplicate or case-colliding filenames")
    inspected.sort(key=lambda item: item["relativePath"])
    routes = [plan_r2_topology(profile_id=game_id, channel=channel,
        platform=platform, content_kind=item["topologyKind"],
        content_sha256=item["contentSha256"]) for item in inspected]
    if any(route["remoteWriteAuthorized"] or route["bucketOrEndpoint"] is not None
           for route in routes):
        raise ValueError("the source topology planner must remain offline")
    blocked_publish = assess_remote_publish_preflight(
        channel=channel, game_id=game_id, manifest_sha256=manifest_sha256,
        owner_approval_reference=owner_review_reference, preview_confirmed=False)
    if blocked_publish["publishAuthorized"] or blocked_publish["networkOrStorageAccessPerformed"]:
        raise ValueError("the publish preflight must remain blocked")

    incident = None
    if incident_affected is not None:
        incident = propose_disabled_levels(
            game_id=game_id, manifest_sha256=manifest_sha256,
            affected=incident_affected,
            owner_review_reference=owner_review_reference)
        if incident["publishAuthorized"] or incident["safeProgressFrontierVerified"]:
            raise ValueError("a simulated incident is not a tested production rollback")
    matrix = {
        "LFX-M10-001": "OFFLINE_CONTENT_ADDRESSED_ROUTE_PROPOSALS",
        "LFX-M10-002": "PUBLIC_READ_AND_SIGNED_CLIENT_VERIFICATION_NOT_RUN",
        "LFX-M10-003": "WRITER_CREDENTIALS_NOT_REQUESTED_OR_EMBEDDED",
        "LFX-M10-004": "LOCAL_ACTUAL_BYTES_VERIFIED_R2_UPLOAD_NOT_RUN",
        "LFX-M10-005": "CANARY_AND_ATOMIC_REMOTE_ROLLBACK_NOT_RUN",
        "LFX-M10-006": "REAL_CLIENT_DOWNLOAD_AND_OFFLINE_FALLBACK_NOT_RUN",
        "LFX-M10-007": "OWNER_AND_ROTATION_OPERATIONS_REQUIRE_REAL_APPROVAL",
        "LFX-M10-008": "PRODUCTION_WRITES_FAIL_CLOSED",
        "LFX-M10-009": ("OFFLINE_DISABLE_PROPOSAL_ONLY" if incident else
                        "EMERGENCY_LEVEL_DRILL_NOT_RUN"),
        "LFX-M10-010": "KNOWN_CONTENT_PATHS_ONLY_NO_CODE_OR_FOREIGN_TITLE",
    }
    if set(matrix) != set(_TASKS):
        raise RuntimeError("milestone task identity drift")
    return {
        "schemaVersion": 1,
        "resultStatus": "M10_OFFLINE_MILESTONE_PREFLIGHT_ONLY",
        "engineStatus": "BLOCKED_ENG_M24",
        "gameProfileId": game_id,
        "channel": channel, "platform": platform,
        "claimedCommitShaUnverified": git_commit_sha,
        "claimedManifestSha256Unverified": manifest_sha256,
        "inspectedLocalArtifacts": inspected,
        "proposedR2PathsNotUploaded": routes,
        "publishPreflight": blocked_publish,
        "disabledLevelIncidentProposal": incident,
        "clientDownloadObserved": False,
        "offlinePlayerFallbackProved": False,
        "canaryAudienceReleased": False,
        "signedManifestVerified": False,
        "writerCredentialsEverLoaded": False,
        "remoteBucketOrNetworkContacted": False,
        "productionPointerModified": False,
        "ownerAccepted": False,
        "publishAuthorized": False,
        "officialMilestonePass": False,
        "taskEvidenceMatrix": matrix,
        "remainingAcceptanceGates": list(_GATES),
    }
