"""M14 v1.0 cross-title release-readiness review, strictly OFFLINE and fail-closed.

Consumes the previous M09..M13 local source/preview receipts. No offline
receipt, unit-test count or source SHA constitutes independently accepted
MATCH3_ENGINE gameplay, client build exclusion, store/age/legal approval,
signed content, live R2 delivery, or commercial v1.0 release authorization.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from theme_contract import PROFILES

_TASK_IDS = tuple(f"LFX-M14-{n:03d}" for n in range(1, 13))
_SHA40 = re.compile(r"[0-9a-f]{40}\Z")
_STAGES = {
    "M09": {
        "status": "M09_OFFLINE_MILESTONE_PREFLIGHT_ONLY",
        "gitKey": "sourceGitCommitShaUnverified",
        "taskCount": 10,
        "no": ("publishAuthorized", "officialMilestonePass", "sourceManifestSigned",
               "ownerApprovalVerified", "signedReleaseRecordProduced",
               "atomicChannelPointerSwitched", "distributedLockVerified"),
    },
    "M10": {
        "status": "M10_OFFLINE_MILESTONE_PREFLIGHT_ONLY",
        "gitKey": "claimedCommitShaUnverified",
        "taskCount": 10,
        "no": ("publishAuthorized", "officialMilestonePass", "ownerAccepted",
               "clientDownloadObserved", "offlinePlayerFallbackProved",
               "remoteBucketOrNetworkContacted", "writerCredentialsEverLoaded",
               "productionPointerModified", "signedManifestVerified"),
    },
    "M11": {
        "status": "M11_OFFLINE_SOURCE_QUALIFICATION_ONLY",
        "gitKey": "sourceGitCommitShaUnverified",
        "taskCount": 10,
        "no": ("publishAuthorized", "officialMilestonePass", "realWinOrGoalsProved",
               "match3EngineSimulationExecuted", "fiveIndependentBotsExecuted",
               "authoritativeReplayObserved", "legalApprovalVerified",
               "consumerBuildExclusionVerified", "ownerAccepted",
               "releaseTagOrPackageCreated"),
    },
    "M12": {
        "status": "M12_OFFLINE_EVENT_POLICY_PREVIEW_ONLY",
        "gitKey": "claimedGitCommitShaUnverified",
        "taskCount": 13,
        "no": ("officialMilestonePass", "rewardOrPremiumEntitlementGranted",
               "authoritativeClaimIdempotencyProved", "existingClaimsVerifiedByServer",
               "kidBehavioralAdsEnabled", "remoteConfigPublished",
               "signedConfigCreated", "ownerApprovalVerified", "userIdentifiersProcessed"),
    },
    "M13": {
        "status": "M13_OFFLINE_WORKBENCH_REVIEW_ONLY",
        "gitKey": "sourceGitCommitShaUnverified",
        "taskCount": 11,
        "no": ("officialMilestonePass", "productionAuthorized", "remoteStagingPerformed",
               "serverReceiptVerified", "realStoreProductPricingRead",
               "userAudienceOrPIIProcessed", "ownerLegalApprovalVerified",
               "actualUserCoinsOrLivesModified", "advertisementsDisplayed"),
    },
}
_OPTIONAL = ("timedMode", "endlessMode", "leaderboards", "competitions",
             "socialInvites", "behavioralTargeting", "realAds", "realIap")


def _review_stage(name: str, record: dict[str, Any], source_git_sha: str) -> dict[str, Any]:
    spec = _STAGES[name]
    if not isinstance(record, dict):
        raise ValueError(name + " receipt missing")
    if (record.get("resultStatus") != spec["status"]
        or record.get("engineStatus") != "BLOCKED_ENG_M24"
        or record.get(spec["gitKey"]) != source_git_sha):
        raise ValueError(name + " not matching the pinned, Engine-blocked offline receipt")
    expected_ids = {f"LFX-{name}-{n:03d}" for n in range(1, spec["taskCount"] + 1)}
    if not isinstance(record.get("taskEvidenceMatrix"), dict) or set(record["taskEvidenceMatrix"]) != expected_ids:
        raise ValueError(name + " milestone task coverage is incomplete or invented")
    if any(record.get(field) is not False for field in spec["no"]):
        raise ValueError(name + " attempted to promote unverified runtime/owner authority")
    if name == "M13" and record.get("consumerEntitlementsMinted") != 0:
        raise ValueError("offline M13 cannot mint any entitlements")
    if name == "M11":
        profiles = record.get("profiles")
        if (not isinstance(profiles, list) or len(profiles) != len(PROFILES)
            or any(not isinstance(p, dict)
                   or not isinstance(p.get("gameProfileId"), str) for p in profiles)
            or set(p["gameProfileId"] for p in profiles) != set(PROFILES)):
            raise ValueError("M11 must report all five game profiles")
        for p in profiles:
            if (type(p.get("receivedDrafts")) is not int or
                    not 0 <= p["receivedDrafts"] <= 100 or
                    p.get("fiveBotEngineSimulationAndWINPassed") is not False or
                    p.get("productionReleaseAuthorized") is not False):
                raise ValueError("M11 profile falsely certified a campaign or Engine WIN")
        if record.get("sourceLevelDraftCount") != sum(x["receivedDrafts"] for x in profiles):
            raise ValueError("M11 per-title input totals mismatch")
        count_complete = all(x["receivedDrafts"] == 100 for x in profiles)
        if record.get("allFiveHundredInputDraftsSupplied") is not count_complete:
            raise ValueError("M11 forged completeness relative to supplied prototype count")
        distinct_complete = all(
            x.get("hundredDistinctGameplayStructuresSupplied") is True
            for x in profiles)
        if record.get("allFiveHundredDistinctGameContentStructuresSupplied") is not distinct_complete:
            raise ValueError("M11 claimed source diversity does not match five title counts")
    if name == "M12":
        policies = record.get("allFiveProfilePolicyDiagnostics")
        if (not isinstance(policies, list) or len(policies) != len(PROFILES)
                or any(not isinstance(p, dict)
                       or not isinstance(p.get("profileId"), str) for p in policies)
                or set(p["profileId"] for p in policies) != set(PROFILES)):
            raise ValueError("M12 did not cover five strict policy profiles")
        if any(p.get("adsOrBehavioralTargetingEnabled") is not False
               or p.get("productionPolicyApproved") is not False for p in policies):
            raise ValueError("M12 must deny child/ad production policy promotion")
    if name == "M13":
        diag = record.get("diagnostics")
        age = diag.get("ageGuards") if isinstance(diag, dict) else None
        if (not isinstance(age, list) or len(age) != len(PROFILES)
                or any(not isinstance(p, dict)
                       or not isinstance(p.get("profileId"), str) for p in age)
                or set(p["profileId"] for p in age) != set(PROFILES)):
            raise ValueError("M13 age-policy profiles incomplete")
        if any(p.get("adsOrPurchasesEligible") is not False for p in age):
            raise ValueError("M13 enabled real advertisements or IAP for unverified ages")
    return {
        "stage": name,
        "sourceStatus": record["resultStatus"],
        "allTaskIdsRepresented": True,
        "reportedTaskCount": len(expected_ids),
        "sourceCommitClaimUnverified": source_git_sha,
        "canonicalEngineSdkVerified": False,
        "ownerOrIndependentAcceptanceVerified": False,
    }


def assess_m14_release_readiness(*, m09: dict[str, Any], m10: dict[str, Any],
                                 m11: dict[str, Any], m12: dict[str, Any],
                                 m13: dict[str, Any], source_git_sha: str,
                                 optional_features: dict[str, dict[str, bool]],
                                 owner_review_reference: str | None = None
                                 ) -> dict[str, Any]:
    """Inspect five prior *offline* receipts without publishing or grants.

    source_git_sha is a caller claim, not a GitHub attestation or SDK pin.
    Unlike Engine/release acceptance, this function is deterministic and has no
    filesystem, network, user-data, build or credential side effects.
    """
    if not isinstance(source_git_sha, str) or _SHA40.fullmatch(source_git_sha) is None:
        raise ValueError("exact lowercase SHA-1 Git commit string required")
    if owner_review_reference is not None and (
        not isinstance(owner_review_reference, str)
        or not 5 <= len(owner_review_reference.strip()) <= 256
        or any(ord(c) < 32 for c in owner_review_reference)
    ):
        raise ValueError("invalid owner note; this never means actual approval")
    if not isinstance(optional_features, dict) or set(optional_features) != set(PROFILES):
        raise ValueError("all five titles require explicit future-feature gates")
    reviewed = []
    for profile in PROFILES:
        options = optional_features[profile]
        if not isinstance(options, dict) or set(options) != set(_OPTIONAL):
            raise ValueError("unknown or missing future feature flags")
        if any(type(v) is not bool or v for v in options.values()):
            raise ValueError("future/ads/social/IAP capabilities must remain disabled")
        reviewed.append({
            "profileId": profile, "optionalFeatureNames": list(_OPTIONAL),
            "allDisabledUntilEngineAndAgeOwnerReview": True,
            "runtimeFeatureFlagsModified": False,
            "childSocialOrAdsEnabled": False,
        })

    source = {"M09": m09, "M10": m10, "M11": m11, "M12": m12, "M13": m13}
    upstream = [_review_stage(name, source[name], source_git_sha) for name in _STAGES]
    # Across all M11 profiles, an actual Engine-verified campaign level count
    # remains ZERO. All M11 counts here are local prototype input drafts.
    prototypes = {p["gameProfileId"]: p["receivedDrafts"] for p in m11["profiles"]}
    if m10.get("gameProfileId") not in PROFILES:
        raise ValueError("M10 offline read proposal does not identify a known title")
    if (not isinstance(m09.get("profiles"), list)
            or not m09["profiles"] or len(m09["profiles"]) > len(PROFILES)
            or any(not isinstance(p, str) or p not in PROFILES for p in m09["profiles"])
            or len(m09["profiles"]) != len(set(m09["profiles"]))):
        raise ValueError("M09 pack proposal refers to unknown/duplicate title")

    proof = {
        "upstreamStages": upstream,
        "futureFeatureGates": reviewed,
        "prototypeDraftInputsByProfileNotCampaign": [
            {"profileId": p, "inputPrototypeDrafts": prototypes[p],
             "engineQualifiedCampaignLevelsVerified": 0}
            for p in PROFILES
        ],
    }
    encoded = json.dumps(proof, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    matrix = {
        "LFX-M14-001": "ENG_M24_FINAL_PIN_AND_INDEPENDENT_ACCEPTANCE_BLOCKED",
        "LFX-M14-002": "FIVE_TITLE_PREVIEW_CONTRACTS_ONLY_NO_SIGNED_LIVE_CONFIG",
        "LFX-M14-003": "REAL_OFFLINE_OTA_CLIENT_REPLAY_AND_ROLLBACK_NOT_RUN",
        "LFX-M14-004": "FAIL_CLOSED_LOCAL_STORE_AD_AGE_POLICY_PREVIEW_ONLY",
        "LFX-M14-005": "PREVIEW_ARCHIVE_EXCLUSION_NOT_REAL_APK_AAB_IPA_AUDIT",
        "LFX-M14-006": "NO_CREDS_USED_OFFLINE_REAL_PRODUCTION_TOKEN_AUDIT_NOT_RUN",
        "LFX-M14-007": "WINDOWS_AND_UNITY_FRESH_REPRODUCIBLE_BUILD_NOT_RUN",
        "LFX-M14-008": "INDEPENDENT_CROSS_TITLE_AUDIT_AND_OWNER_SIGNOFF_NOT_RUN",
        "LFX-M14-009": "V1_TAG_AND_RELEASE_ARTIFACT_FORBIDDEN_PENDING_ACCEPTANCE",
        "LFX-M14-010": "FIVE_BOT_ENGINE_PARITY_AND_TIMEOUT_PROOF_NOT_RUN",
        "LFX-M14-011": "FIVE_GAME_ART_UI_MOBILE_OWNER_RELEASE_QA_NOT_RUN",
        "LFX-M14-012": "FIVE_TITLE_OPTIONAL_FEATURES_EXPLICITLY_DISABLED",
    }
    if set(matrix) != set(_TASK_IDS):
        raise RuntimeError("final milestone task matrix incomplete")
    return {
        "schemaVersion": 1,
        "resultStatus": "M14_OFFLINE_RELEASE_READINESS_GAP_REPORT_ONLY",
        "engineStatus": "BLOCKED_ENG_M24",
        "engM20AndM21Accepted": False,
        "sourceGitCommitShaUnverified": source_git_sha,
        "ownerReviewReferenceUnverified": owner_review_reference.strip() if owner_review_reference else None,
        "upstreamPreviewContracts": upstream,
        "explicitlyDisabledFutureFeatures": reviewed,
        "prototypeInputsByGameNotCampaign": proof["prototypeDraftInputsByProfileNotCampaign"],
        "sourceOnlyReviewSha256": hashlib.sha256(encoded).hexdigest(),
        "runtimeWinOrSolverParityVerified": False,
        "productionBuildContentsInspected": False,
        "productionSecretsAuditPerformed": False,
        "realOTAOrOfflineReplayPerformed": False,
        "consumerAgeStorePoliciesIndependentlyApproved": False,
        "realCampaignLevelsEngineQualified": 0,
        "signedReleaseManifestProduced": False,
        "immutableV1SourceTagCreated": False,
        "ownerAccepted": False,
        "productionAuthorized": False,
        "officialMilestonePass": False,
        "taskEvidenceMatrix": matrix,
        "remainingAcceptanceGates": [
            "ENG_M24_AND_ENG_M20_M21_ACCEPTED_RUNTIME_CONTRACTS",
            "FIVE_TITLE_100_CAMPAIGN_LEVELS_PER_TITLE_WITH_ENGINE_REPLAY",
            "REAL_FIVE_BOT_SOLVER_AND_CROSS_MECHANIC_PARITY",
            "CLEAN_WINDOWS_UNITY_PLAYER_BUILDS_AND_EXCLUSION_AUDIT",
            "APP_STORE_GOOGLE_PLAY_CHILD_POLICY_AND_RIGHTS_LEGAL_APPROVAL",
            "SIGNED_OTA_ROLLBACK_REAL_CLIENT_AND_CDN_READ_WRITE_DRILLS",
            "OWNER_INDEPENDENT_AUDIT_ACCEPTANCE_AND_RELEASE_TAG",
        ],
    }
