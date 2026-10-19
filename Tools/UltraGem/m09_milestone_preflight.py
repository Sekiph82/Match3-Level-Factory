"""LFX-M09 offline milestone-wide release preflight, NEVER a publisher.

Orchestrates existing preview pack, diff, rights/ZIP screening, platform planning,
and rollback intent. SHA receipts here are unsigned content fingerprints only.
No Engine SDK, live remote pointer, signing key, approval or cloud write is inferred.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from content_exclusion import validate_preview_file_inventory
from preview_archive_scan import scan_preview_archive
from preview_diff import _index, diff_preview_manifests
from release_plan import plan_platform_preview, plan_r2_topology, plan_rollback_only
from theme_contract import PROFILES

HEX40 = re.compile(r"[0-9a-f]{40}\Z")
ROOT_KEYS = {
    "schemaVersion", "resultStatus", "engineStatus", "channel", "levelCount",
    "groups", "containsGameRuntimeOrArt", "signed", "publishAuthorized",
}
TASK_IDS = tuple(f"LFX-M09-{i:03d}" for i in range(1, 11))
BLOCKERS = (
    "ENG_M24_ACCEPTED_SDK", "CANONICAL_SIGNED_LEVELPACK", "SIGNED_RELEASE_MANIFEST",
    "OWNER_AND_RIGHTS_APPROVAL", "DISTRIBUTED_LOCK_AND_POINTER_ATOMICITY",
    "ACTUAL_PLAYER_AND_PLATFORM_VALIDATION",
)


def _strict_preview(value: dict[str, Any]) -> tuple[str, str, list[str]]:
    """Reject forged publish metadata even if the older index accepts it."""
    if not isinstance(value, dict) or set(value) != ROOT_KEYS:
        raise ValueError("unknown or missing preview manifest fields")
    if (type(value["schemaVersion"]) is not int or value["schemaVersion"] != 1
            or value["resultStatus"] != "LOCAL_PREVIEW_MANIFEST_ONLY"
            or value["engineStatus"] != "BLOCKED_ENG_M24"
            or value["signed"] is not False
            or value["publishAuthorized"] is not False
            or value["containsGameRuntimeOrArt"] is not False):
        raise ValueError("not an unsigned, Engine-blocked local preview")
    channel, indexed = _index(value)
    if not indexed:
        raise ValueError("empty preview pack")
    profiles = set()
    for group in value["groups"]:
        profile = group["gameProfileId"]
        if profile not in PROFILES:
            raise ValueError("unknown game profile")
        profiles.add(profile)
        for level in group["levels"]:
            if type(level["draftJsonUtf8Bytes"]) is not int or not 1 <= level["draftJsonUtf8Bytes"] <= 8_000_000:
                raise ValueError("invalid canonical draft byte length")
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(encoded) > 2_000_000:
        raise ValueError("preview manifest exceeds bounded size")
    return channel, hashlib.sha256(encoded).hexdigest(), sorted(profiles)


def preflight_m09_milestone(*, proposed: dict[str, Any], git_commit_sha: str,
                            locales: list[str], previous: dict[str, Any] | None = None,
                            inventory: list[dict[str, Any]] | None = None,
                            archive_bytes: bytes | None = None,
                            previous_release_reference: str | None = None,
                            owner_review_reference: str | None = None) -> dict[str, Any]:
    """Read-only all-M09 offline audit; never signs, stages, switches or publishes.

    previous is a local preview baseline, NEVER an independently accepted
    production release. previous_release_reference is an unverified note.
    """
    if not isinstance(git_commit_sha, str) or HEX40.fullmatch(git_commit_sha) is None:
        raise ValueError("exact lowercase Git commit SHA required")
    channel, digest, profiles = _strict_preview(proposed)
    if not isinstance(locales, list) or not 1 <= len(locales) <= 16:
        raise ValueError("bounded locale list required")
    if (archive_bytes is None) != (inventory is None):
        raise ValueError("archive bytes and inventory must be supplied together")
    if previous_release_reference is not None and previous is None:
        raise ValueError("rollback reference without previous preview is invalid")
    if owner_review_reference is not None and (
        not isinstance(owner_review_reference, str)
        or not 5 <= len(owner_review_reference.strip()) <= 256
        or any(ord(c) < 32 for c in owner_review_reference)
    ):
        raise ValueError("invalid unverified owner review reference")

    platform_plans = [plan_platform_preview(profile_id=profile, channel=channel,
                       platform=platform, locales=locales)
                      for profile in profiles for platform in ("android", "ios", "windows")]
    # A deterministic proposed namespace is NOT a remotely allocated object.
    proposed_paths = [plan_r2_topology(profile_id=profile, channel=channel,
                      platform=platform, content_kind="levels", content_sha256=digest)
                      for profile in profiles for platform in ("android", "ios", "windows")]

    diff = None
    rollback = None
    previous_digest = None
    if previous is not None:
        old_channel, previous_digest, _ = _strict_preview(previous)
        if old_channel != channel:
            raise ValueError("cross-channel release diff forbidden")
        diff = diff_preview_manifests(previous, proposed)
        if previous_digest != digest and previous_release_reference is not None:
            rollback = plan_rollback_only(previous_manifest_sha256=previous_digest,
                next_manifest_sha256=digest,
                previous_release_reference=previous_release_reference)

    archive = None
    if inventory is not None:
        rights = validate_preview_file_inventory(inventory)
        if rights["denied"] or not rights["acceptedForFurtherInspection"]:
            raise ValueError("rights and path preflight refused the preview archive")
        archive = scan_preview_archive(archive_bytes, inventory)
        if archive["productionReleaseAuthorized"] is not False:
            raise ValueError("prototype archive cannot authorize production")

    matrix = {
        "LFX-M09-001": "LOCAL_GROUPED_LEVELDRAFT_SHA_ONLY",
        "LFX-M09-002": "UNSIGNED_LOCAL_VERSION_AND_HASH_ENVELOPE",
        "LFX-M09-003": "LOCAL_DIFF_VERIFIED" if diff else "NO_PRIOR_PREVIEW",
        "LFX-M09-004": "STAGE_AND_POINTER_PLAN_ONLY",
        "LFX-M09-005": "UNVERIFIED_ROLLBACK_PLAN" if rollback else "NO_VERIFIED_ACCEPTED_PREVIOUS_RELEASE",
        "LFX-M09-006": "LOCAL_PLATFORM_REQUIREMENTS_ONLY",
        "LFX-M09-007": "PROCESS_LOCAL_CAS_ONLY_NOT_DISTRIBUTED",
        "LFX-M09-008": "UNSIGNED_COMMIT_PROVENANCE_ONLY",
        "LFX-M09-009": "NO_SIGNED_HOTFIX_OR_SAFE_FRONTIER_PROOF",
        "LFX-M09-010": "PREVIEW_ZIP_BYTES_VERIFIED_NOT_RELEASE" if archive else "NO_ARCHIVE_BYTES_SUPPLIED",
    }
    if set(matrix) != set(TASK_IDS):
        raise RuntimeError("M09 milestone task contract drift")
    return {
        "schemaVersion": 1,
        "resultStatus": "M09_OFFLINE_MILESTONE_PREFLIGHT_ONLY",
        "engineStatus": "BLOCKED_ENG_M24",
        "channel": channel,
        "sourceGitCommitShaUnverified": git_commit_sha,
        "sourcePreviewManifestSha256": digest,
        "previousPreviewManifestSha256": previous_digest,
        "sourceManifestSigned": False,
        "schemaVersionMinPreviewOnly": 1,
        "schemaVersionMaxPreviewOnly": 1,
        "engineCapabilityBoundsVerified": False,
        "levelCount": proposed["levelCount"],
        "profiles": profiles,
        "platformPlans": platform_plans,
        "relativeR2PathProposalsNotUploadKeys": proposed_paths,
        "previewDiff": diff,
        "rollbackProposal": rollback,
        "archiveByteScan": archive,
        "ownerReviewReferenceUnverified": owner_review_reference.strip() if owner_review_reference else None,
        "ownerApprovalVerified": False,
        "stagedRemotePayloadVerified": False,
        "atomicChannelPointerSwitched": False,
        "distributedLockVerified": False,
        "signedReleaseRecordProduced": False,
        "safeDisabledLevelFrontierVerified": False,
        "publishAuthorized": False,
        "officialMilestonePass": False,
        "taskEvidenceMatrix": matrix,
        "remainingAcceptanceGates": list(BLOCKERS),
    }
