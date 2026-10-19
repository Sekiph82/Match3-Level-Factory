"""LFX-M11 whole-milestone *offline* v0.9 source qualification dossier.

Checks actual canonical LevelDraft JSON and local M09 preview pack boundaries.
Never claims Engine gameplay, four/five-bot simulation, remote patch, WIN,
art redistribution, clean-install, release or independent owner approval.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

import leveldraft
from preview_pack import build_preview_pack
from m09_milestone_preflight import preflight_m09_milestone
from theme_contract import PROFILES

_PROFILE_ORDER = tuple(PROFILES)
_TASKS = tuple(f"LFX-M11-{n:03d}" for n in range(1, 11))
_SHA40 = re.compile(r"[0-9a-f]{40}\Z")
_ENGINE_GATES = (
    "ENG_M24_FINAL_ACCEPTED_ENGINE_SDK_NOT_PROVIDED",
    "EDITOR_TO_REAL_SIMULATOR_PACK_RUNTIME_WIN_PARITY_NOT_RUN",
    "ENGINE_REPLAY_AND_FIVE_INDEPENDENT_BOT_PROOF_NOT_RUN",
    "REMOTE_PATCH_BAD_UPDATE_OFFLINE_CLIENT_FALLBACK_NOT_RUN",
    "FRESH_WINDOWS_INSTALL_NOT_REPRODUCED",
    "SOURCE_LICENSE_AND_MEDIA_RIGHTS_INDEPENDENT_REVIEW_REQUIRED",
    "CONSUMER_PLAYER_BUILD_EXCLUSION_NOT_INDEPENDENTLY_AUDITED",
    "OWNER_APPROVAL_AND_FACTORY_V09_RELEASE_TAG_NOT_AUTHORIZED",
)


def _fingerprint_gameplay_shape(draft: dict[str, Any]) -> str:
    """Unsigned draft-content diversity clue, NOT a gameplay/difficulty score.

    Exclude profile and human IDs (and seed) so repeated renamed copies are
    not mistaken for 100 distinct gameplay structures.
    """
    payload = {
        "dimensions": [draft["width"], draft["height"], draft["layers"]],
        "activeMask": draft["activeMask"],
        "cells": draft["cells"],
        "goals": draft["goals"],
        "moveBudget": draft["moveBudget"],
        "timedMode": draft["timedMode"],
        "timeLimitSeconds": draft["timeLimitSeconds"],
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                     separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def qualify_m11_milestone(*, drafts: list[dict[str, Any]],
                          source_git_sha: str,
                          locale_requirements: list[str] | None = None,
                          owner_review_reference: str | None = None
                          ) -> dict[str, Any]:
    """Validate <=500 input draft records and compute a truthful 10-task gate.

    This function does NOT generate any candidate or run a solver, bot,
    Unity Editor, Engine runtime, CDN, clean install, signed release or build.
    """
    if not isinstance(source_git_sha, str) or _SHA40.fullmatch(source_git_sha) is None:
        raise ValueError("source_git_sha must be exactly 40 lowercase hex digits")
    if not isinstance(drafts, list) or not 1 <= len(drafts) <= 500:
        raise ValueError("supply 1..500 real local LevelDraft dicts")
    locales = ["en", "tr"] if locale_requirements is None else locale_requirements
    if not isinstance(locales, list) or not 1 <= len(locales) <= 16:
        raise ValueError("bounded locale requirements required")
    if owner_review_reference is not None and (
            not isinstance(owner_review_reference, str) or
            not 5 <= len(owner_review_reference.strip()) <= 256 or
            any(ord(ch) < 32 for ch in owner_review_reference)):
        raise ValueError("invalid owner-review note; no approval may be inferred")

    by_profile = {profile: [] for profile in _PROFILE_ORDER}
    hashes = {profile: set() for profile in _PROFILE_ORDER}
    shapes = {profile: set() for profile in _PROFILE_ORDER}
    seed_sets = {profile: set() for profile in _PROFILE_ORDER}
    seen_ids = set()
    roundtrip_count = 0
    for draft in drafts:
        # The original strict neutral schema is the only allowed validator.
        # Invalid final Engine claims and unknown C# gameplay fields fail here.
        leveldraft.validate(draft)
        if draft["releaseChannel"] != "local":
            raise ValueError("M11 source dossier accepts local prototype channel only")
        canonical = leveldraft.dumps_canonical(draft)
        parsed = leveldraft.loads_strict(canonical)
        if leveldraft.dumps_canonical(parsed) != canonical:
            raise ValueError("canonical JSON import/export mismatch")
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        if digest != leveldraft.sha256(draft):
            raise ValueError("canonical JSON digest mismatch")
        profile = draft["gameProfileId"]
        key = (profile, draft["worldId"], draft["chapterId"], draft["levelId"])
        if key in seen_ids:
            raise ValueError("duplicate cross-title world/chapter/level identity")
        seen_ids.add(key)
        if len(by_profile[profile]) == 100:
            raise ValueError("more than 100 levels per title is outside M11 gate")
        by_profile[profile].append(draft)
        hashes[profile].add(digest)
        shapes[profile].add(_fingerprint_gameplay_shape(parsed))
        seed_sets[profile].add(draft["seed"])
        roundtrip_count += 1

    groups = []
    total_unique_structures = 0
    for profile in _PROFILE_ORDER:
        records = by_profile[profile]
        if records:
            # Existing M09 preview contract is bounded to 128 levels.
            pack = build_preview_pack(records, channel="local")
            gate = preflight_m09_milestone(
                proposed=pack, git_commit_sha=source_git_sha,
                locales=locales)
            if gate["publishAuthorized"] is not False or gate["officialMilestonePass"] is not False:
                raise ValueError("M09 preview contract unexpectedly allowed release")
            preview_sha = gate["sourcePreviewManifestSha256"]
        else:
            preview_sha = None
        distinct = len(shapes[profile])
        total_unique_structures += distinct
        groups.append({
            "gameProfileId": profile,
            "receivedDrafts": len(records),
            "expectedForM11": 100,
            "missingInputs": 100 - len(records),
            "distinctCanonicalDraftHashes": len(hashes[profile]),
            "distinctGameContentFingerprintsNotDifficulty": distinct,
            "distinctSourceSeeds": len(seed_sets[profile]),
            "hundredPrototypeDraftInputsSupplied": len(records) == 100,
            "hundredDistinctGameplayStructuresSupplied": len(records) == distinct == 100,
            "referencePackManifestSha256": preview_sha,
            "referencePackIsSigned": False,
            "fiveBotEngineSimulationAndWINPassed": False,
            "productionReleaseAuthorized": False,
        })
    provided_full = all(g["hundredPrototypeDraftInputsSupplied"] for g in groups)
    distinct_full = all(g["hundredDistinctGameplayStructuresSupplied"] for g in groups)
    matrix = {
        "LFX-M11-001": "FRESH_WINDOWS_INSTALL_NOT_RUN",
        "LFX-M11-002": "EDITOR_ENGINE_RUNTIME_WIN_SMOKE_BLOCKED_ENG_M24",
        "LFX-M11-003": "LOCAL_CANONICAL_DRAFT_ROUNDTRIP_CHECKED_ONLY",
        "LFX-M11-004": "REMOTE_PATCH_AND_REAL_OFFLINE_FALLBACK_NOT_RUN",
        "LFX-M11-005": ("FIVE_TITLE_INPUT_COUNTS_ONLY_BOT_PROOF_NOT_RUN"
                        if provided_full else "FIVE_TITLE_100_LEVEL_INPUTS_INCOMPLETE"),
        "LFX-M11-006": "LICENSE_AND_IMPORTED_MEDIA_LEGAL_REVIEW_NOT_RUN",
        "LFX-M11-007": "INDEPENDENT_AUDIT_PLAYER_BUILD_AND_OWNER_SIGNOFF_NOT_RUN",
        "LFX-M11-008": "FACTORY_V09_CANDIDATE_NOT_TAGGED_OR_RELEASED",
        "LFX-M11-009": ("FIVE_TITLE_100_STRUCTURE_INPUTS_NOT_ENGINE_SIMULATED"
                        if distinct_full else "100_DISTINCT_STRUCTURE_SETS_MISSING"),
        "LFX-M11-010": "DONOR_PROVENANCE_NOT_INDEPENDENTLY_CLEARED_OR_ENGINE_MATCHED",
    }
    if set(matrix) != set(_TASKS):
        raise RuntimeError("M11 task identity drift")

    return {
        "schemaVersion": 1,
        "resultStatus": "M11_OFFLINE_SOURCE_QUALIFICATION_ONLY",
        "engineStatus": "BLOCKED_ENG_M24",
        "sourceGitCommitShaUnverified": source_git_sha,
        "ownerReviewReferenceUnverified": (
            owner_review_reference.strip() if owner_review_reference else None),
        "sourceLevelDraftCount": len(drafts),
        "canonicalJsonRoundtripCount": roundtrip_count,
        "profiles": groups,
        "sourceDraftHashesUniqueByIdentity": len(seen_ids) == len(drafts),
        "totalDistinctContentFingerprintsNotDifficulty": total_unique_structures,
        "allFiveHundredInputDraftsSupplied": provided_full,
        "allFiveHundredDistinctGameContentStructuresSupplied": distinct_full,
        "generatorExecutionPerformed": False,
        "fiveIndependentBotsExecuted": False,
        "match3EngineSimulationExecuted": False,
        "authoritativeReplayObserved": False,
        "realWinOrGoalsProved": False,
        "localFactoryCleanInstallVerified": False,
        "remotePatchFallbackVerified": False,
        "legalApprovalVerified": False,
        "consumerBuildExclusionVerified": False,
        "ownerAccepted": False,
        "releaseTagOrPackageCreated": False,
        "publishAuthorized": False,
        "officialMilestonePass": False,
        "taskEvidenceMatrix": matrix,
        "remainingAcceptanceGates": list(_ENGINE_GATES),
    }
