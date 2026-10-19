"""LFX-M12 single-milestone offline LiveOps authoring / preview review.

Combines existing calendar, conservative age/cap policies, experiment metadata
and emergency event stops. No ENG-M20/24 interface, idempotent claim server,
client state, cloud provider, key, signed config or grant operation exists here.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from age_liveops_policy import validate_age_liveops_config, FLAGS
from audience_caps import evaluate_content_caps
from event_calendar import propose_calendar_event, preview_event_window
from experiment_config import propose_experiment
from theme_contract import PROFILES

TASK_IDS = tuple(f"LFX-M12-{i:03d}" for i in range(1, 14))
_EVENT_FIELDS = {
    "profileId", "eventId", "cadence", "timezoneId", "startLocal", "endLocal",
    "startFold", "endFold", "contentKind", "contentId",
    "claimPreviouslyRecordedByCaller",
}
_EXP_FIELDS = {
    "gameProfileId", "experimentId", "variants", "holdoutPercent",
    "audienceMode", "rollbackReference",
}
_POLICY_FIELDS = {"flags", "caps"}
_CONTENT_KINDS = {"LEVEL", "WORLD", "GOAL", "COLLECTION"}
_ID = re.compile(r"[A-Za-z][A-Za-z0-9._-]{2,79}\Z")
_CONTENT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{2,127}\Z")
_SHA40 = re.compile(r"[0-9a-f]{40}\Z")
_SHA64 = re.compile(r"[0-9a-f]{64}\Z")
_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")


def _strict_server_sample(sample: str) -> str:
    if not isinstance(sample, str) or _UTC.fullmatch(sample) is None:
        raise ValueError("explicit exact YYYY-MM-DDTHH:MM:SSZ sample required")
    from datetime import datetime, timezone
    try:
        if datetime.fromisoformat(sample.replace("Z", "+00:00")).tzinfo != timezone.utc:
            raise ValueError("UTC sample is not UTC")
    except ValueError as exc:
        raise ValueError("invalid server-time sample") from exc
    return sample


def _metadata_digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        allow_nan=False).encode("utf-8")).hexdigest()


def preflight_m12_milestone(*, events: list[dict[str, Any]],
                            policies: dict[str, dict[str, Any]],
                            available_content: dict[str, list[str]],
                            observed_server_utc: str,
                            manifest_sha256: str, git_commit_sha: str,
                            disabled_event_ids: list[str] | None = None,
                            experiments: list[dict[str, Any]] | None = None,
                            owner_review_reference: str | None = None
                            ) -> dict[str, Any]:
    """Dry-run all 13 M12 acceptance areas for the five declared titles.

    A caller-supplied server UTC string and previous-claim boolean are NOT
    trusted backend attestation. No recurring occurrence expansion or grant.
    """
    if not isinstance(git_commit_sha, str) or _SHA40.fullmatch(git_commit_sha) is None:
        raise ValueError("40-lowercase-hex source SHA required")
    if not isinstance(manifest_sha256, str) or _SHA64.fullmatch(manifest_sha256) is None:
        raise ValueError("64-lowercase-hex unverified manifest SHA required")
    observed_server_utc = _strict_server_sample(observed_server_utc)
    if (not isinstance(events, list) or not 1 <= len(events) <= 65 or
            not isinstance(policies, dict) or set(policies) != set(PROFILES) or
            not isinstance(available_content, dict) or set(available_content) != set(PROFILES)):
        raise ValueError("bounded events and all-five-profile policy/content maps required")
    if owner_review_reference is not None and (
        not isinstance(owner_review_reference, str) or
        not 5 <= len(owner_review_reference.strip()) <= 256 or
        any(ord(c) < 32 for c in owner_review_reference)
    ):
        raise ValueError("invalid unverified owner review reference")
    stops = [] if disabled_event_ids is None else disabled_event_ids
    experiment_items = [] if experiments is None else experiments
    if (not isinstance(stops, list) or len(stops) > 65 or
            not isinstance(experiment_items, list) or len(experiment_items) > 20):
        raise ValueError("bounded event stops and experiment proposals required")
    if any(not isinstance(v, str) or len(v) > 170 for v in stops):
        raise ValueError("malformed disabled event identifiers")
    if len(stops) != len(set(stops)):
        raise ValueError("duplicate disabled event identifiers")

    policy_receipts = []
    content_sets = {}
    for profile in PROFILES:
        item = policies[profile]
        if not isinstance(item, dict) or set(item) != _POLICY_FIELDS:
            raise ValueError("unknown or incomplete per-title policy schema")
        flags = item["flags"]
        caps = item["caps"]
        # Existing independent policy gates handle strict field/type validation.
        if not isinstance(flags, dict) or set(flags) != set(FLAGS):
            raise ValueError("unknown/missing age policy flags")
        age = validate_age_liveops_config(profile_id=profile, flags=flags)
        content_cap = evaluate_content_caps(profile, caps)
        if not age["localPreviewAllowed"] or not content_cap["canPreviewLocally"]:
            raise ValueError("age/privacy/child content policy violation")
        content = available_content[profile]
        if (not isinstance(content, list) or len(content) > 256 or
                any(not isinstance(v, str) or _CONTENT_ID.fullmatch(v) is None for v in content) or
                len(content) != len(set(content))):
            raise ValueError("duplicate or unknown available content IDs")
        content_sets[profile] = set(content)
        policy_receipts.append({
            "profileId": profile,
            "audiencePolicy": age["audiencePolicy"],
            "agePolicyLocalPreviewAllowed": age["localPreviewAllowed"],
            "capPolicyLocalPreviewAllowed": content_cap["canPreviewLocally"],
            "ageLegallyVerified": False,
            "adsOrBehavioralTargetingEnabled": False,
            "productionPolicyApproved": False,
        })

    previews = []
    known_ids = set()
    for item in events:
        if not isinstance(item, dict) or set(item) != _EVENT_FIELDS:
            raise ValueError("unknown or missing event authoring fields")
        profile, eid = item["profileId"], item["eventId"]
        if profile not in PROFILES or not isinstance(eid, str) or _ID.fullmatch(eid) is None:
            raise ValueError("invalid per-title event")
        key = profile + "/" + eid
        if key in known_ids:
            raise ValueError("repeated season/event activation identity in proposed batch")
        known_ids.add(key)
        if item["contentKind"] not in _CONTENT_KINDS:
            raise ValueError("unsupported event content capability kind")
        cid = item["contentId"]
        if not isinstance(cid, str) or _CONTENT_ID.fullmatch(cid) is None:
            raise ValueError("invalid event content identity")
        if type(item["claimPreviouslyRecordedByCaller"]) is not bool:
            raise ValueError("caller claim preview must be exact boolean")
        schedule = propose_calendar_event(
            profile_id=profile, event_id=eid, cadence=item["cadence"],
            timezone_id=item["timezoneId"], start_local=item["startLocal"],
            end_local=item["endLocal"], start_fold=item["startFold"],
            end_fold=item["endFold"])
        phase = preview_event_window(schedule, observed_server_utc=observed_server_utc)
        if key in stops:
            display = "STOPPED_BY_LOCAL_PREVIEW_REQUEST_NO_GRANT"
        elif cid not in content_sets[profile]:
            display = "MISSING_REFERENCED_CONTENT_DISPLAY_DISABLED"
        elif phase == "ACTIVE_DISPLAY_PREVIEW_NO_GRANT" and item["claimPreviouslyRecordedByCaller"]:
            display = "ACTIVE_PREVIOUSLY_RECORDED_BY_CALLER_DISPLAY_ONLY"
        else:
            display = phase
        previews.append({
            "profileId": profile, "eventId": eid,
            "contentKind": item["contentKind"], "contentId": cid,
            "startUtc": schedule["startUtc"], "endUtc": schedule["endUtc"],
            "cadenceLabelOnlyNoRecurrenceService": schedule["cadence"],
            "observedServerUtcProvidedByCallerUnverified": observed_server_utc,
            "displayStatus": display,
            "previousClaimBooleanProvidedByCallerUnverified":
                item["claimPreviouslyRecordedByCaller"],
            "actualClaimHistoryChecked": False,
            "rewardOrEntitlementGranted": False,
            "idempotentBackendProof": False,
        })
    if set(stops) - known_ids:
        raise ValueError("stopped event not found; typo fail-closed")

    experiment_receipts = []
    exp_ids = set()
    for item in experiment_items:
        if not isinstance(item, dict) or set(item) != _EXP_FIELDS:
            raise ValueError("experiment has unknown/missing fields")
        profile, eid = item["gameProfileId"], item["experimentId"]
        if profile not in PROFILES or not isinstance(eid, str) or _ID.fullmatch(eid) is None:
            raise ValueError("unknown experiment identity")
        key = profile + "/" + eid
        if key in exp_ids:
            raise ValueError("duplicate experiment across one title")
        exp_ids.add(key)
        proposal = propose_experiment(
            game_id=profile, experiment_id=eid,
            variants=item["variants"], holdout_percent=item["holdoutPercent"],
            audience_mode=item["audienceMode"],
            rollback_reference=item["rollbackReference"])
        if proposal["remoteDeploymentAuthorized"] or proposal["rewardOrClaimChanged"]:
            raise ValueError("experiment proposal must never deploy or grant")
        experiment_receipts.append({
            "gameProfileId": profile, "experimentId": eid,
            "holdoutPercent": proposal["holdoutPercent"],
            "audienceMode": proposal["audienceMode"],
            "stableAllocatorImplemented": False,
            "requiresConsentBeforeEligibility": True,
            "publishAuthorized": False,
        })

    previews.sort(key=lambda row: (row["profileId"], row["eventId"]))
    experiment_receipts.sort(key=lambda row: (row["gameProfileId"], row["experimentId"]))
    unsigned_payload = {
        "events": previews,
        "experiments": experiment_receipts,
        "policyDiagnostics": policy_receipts,
        "disabledEventIds": sorted(stops),
    }
    preview_digest = _metadata_digest(unsigned_payload)
    matrix = {
        "LFX-M12-001": "LOCAL_SCHEMA_PREVIEW_ONLY_ENG_M20_NOT_PINNED",
        "LFX-M12-002": "DST_AWARE_SINGLE_WINDOWS_RECURRENCE_BACKEND_NOT_RUN",
        "LFX-M12-003": "NO_PREMIUM_REWARD_GRANTS_OR_PRODUCTION_PROMOTION",
        "LFX-M12-004": "NON_PERSONALIZED_EXPERIMENT_PROPOSALS_ONLY",
        "LFX-M12-005": "ALL_FIVE_AGE_AND_AD_POLICIES_FAIL_CLOSED",
        "LFX-M12-006": "STOPPED_EVENT_LOCAL_PREVIEW_ONLY_NO_REMOTE_SWITCH",
        "LFX-M12-007": "FIVE_TITLE_EVENT_DISPLAY_SIMULATOR_NO_CLAIM",
        "LFX-M12-008": "UNSIGNED_PREVIEW_DIGEST_NO_CLOUD_EXPORT",
        "LFX-M12-009": "OWNER_REVIEW_REFERENCE_UNVERIFIED_NO_APPROVAL",
        "LFX-M12-010": "MISSING_CONTENT_STALE_SERVER_DUPLICATE_PREVIEW_BLOCKED",
        "LFX-M12-011": "INDEPENDENT_POLICY_AND_IDEMPOTENT_BACKEND_AUDIT_NOT_RUN",
        "LFX-M12-012": "JOURNEY_STAR_CHEST_COMEBACK_METADATA_NOT_ENGINE_BOUND",
        "LFX-M12-013": "WONDER_POP_CHILD_CONTENT_CAPS_ACTIVE_FOR_PREVIEW",
    }
    if set(matrix) != set(TASK_IDS):
        raise RuntimeError("whole milestone task matrix drift")
    return {
        "schemaVersion": 1,
        "resultStatus": "M12_OFFLINE_EVENT_POLICY_PREVIEW_ONLY",
        "engineStatus": "BLOCKED_ENG_M24",
        "engM20OfficialEventAndClaimContractVerified": False,
        "claimedGitCommitShaUnverified": git_commit_sha,
        "claimedSourceManifestSha256Unverified": manifest_sha256,
        "ownerReviewReferenceUnverified":
            owner_review_reference.strip() if owner_review_reference else None,
        "eventCount": len(previews),
        "eventPreviews": previews,
        "experimentPreviews": experiment_receipts,
        "allFiveProfilePolicyDiagnostics": policy_receipts,
        "unsignedLocalPreviewSha256": preview_digest,
        "providerSpecificExportSigned": False,
        "actualServerTimeAttested": False,
        "existingClaimsVerifiedByServer": False,
        "recurringOccurrencesExpanded": False,
        "authoritativeClaimIdempotencyProved": False,
        "rewardOrPremiumEntitlementGranted": False,
        "userIdentifiersProcessed": False,
        "kidBehavioralAdsEnabled": False,
        "remoteConfigPublished": False,
        "signedConfigCreated": False,
        "ownerApprovalVerified": False,
        "productionAuthorized": False,
        "officialMilestonePass": False,
        "taskEvidenceMatrix": matrix,
        "remainingAcceptanceGates": [
            "ENG_M20_AND_ENG_M24_ACCEPTED_INTERFACES_MISSING",
            "BACKEND_SERVER_TIME_AND_CLAIM_IDEMPOTENCY_NOT_PROVEN",
            "RECURRENCE_AND_PER_PROFILE_POLICY_LEGAL_APPROVAL_OPEN",
            "APPROVED_BACKEND_SIGNER_AND_PROVIDER_SCHEMA_NOT_PINNED",
            "REAL_CLIENT_OFFLINE_ONLINE_BOUNDARY_AND_INDEPENDENT_AUDIT_NOT_RUN",
        ],
    }
