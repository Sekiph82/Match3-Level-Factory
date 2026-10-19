"""LFX-M13 five-game OFFLINE store, offer, economy and UI policy workbench.

A typed, read-only authoring review over the existing catalog/IAP/rights,
localization and conservative age-policy components. No pricing, purchases,
ad callbacks, reward claims, user identifiers, SDK or remote writer is present.
Not ENG-M20/M21/M24 authority. All consumer actions remain disabled.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from age_liveops_policy import FLAGS, validate_age_liveops_config
from asset_rights import audit_asset_bindings
from iap_binding_guard import audit_iap_entitlement_bindings
from localization_qa import build_localization_qa
from store_catalog import propose_store_catalog
from theme_contract import PROFILES, COMMON_SLOTS

TASK_IDS = tuple(f"LFX-M13-{i:03d}" for i in range(1, 12))
_SHA40 = re.compile(r"[0-9a-f]{40}\Z")
_ID = re.compile(r"[a-z][a-z0-9._-]{2,79}\Z")
_REF = re.compile(r"[A-Za-z][A-Za-z0-9._/-]{4,127}\Z")
_UI_STATES = {
    "BUY", "WATCH_AD", "CLAIM", "STORE_OFFLINE", "OWNED",
    "DISABLED", "PENDING",
}
_PLACEMENTS = {"REWARDED_AD", "STORE_OFFER", "EARNED_REWARD"}
_CB_KINDS = {"PURCHASE", "AD_CALLBACK", "CLAIM"}
_CB_OUTCOMES = {
    "UNVERIFIED", "FAILED_VERIFICATION", "CANCELLED", "NO_FILL",
    "DUPLICATE", "STALE_CATALOG", "INVALID_SIGNATURE", "PENDING",
}


def _digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(
        obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False).encode("utf-8")).hexdigest()


def _entry_game(row: dict[str, Any], profile_key: str = "profileId") -> str:
    profile = row[profile_key]
    if profile not in PROFILES:
        raise ValueError("unknown or foreign game profile")
    return profile


def _economy(row: dict[str, Any]) -> dict[str, Any]:
    fields = {
        "profileId", "scenarioId", "levelCompletions",
        "coinsEarnedPerCompletion", "dailyEarnedCoins", "boosterPurchases",
        "coinsPerBooster", "heartRegenSeconds",
    }
    if not isinstance(row, dict) or set(row) != fields:
        raise ValueError("economy case schema must be complete and pure")
    game = _entry_game(row)
    scenario = row["scenarioId"]
    if not isinstance(scenario, str) or _ID.fullmatch(scenario) is None:
        raise ValueError("invalid economy scenario")
    limits = {
        "levelCompletions": 10000, "coinsEarnedPerCompletion": 100000,
        "dailyEarnedCoins": 100000, "boosterPurchases": 10000,
        "coinsPerBooster": 100000, "heartRegenSeconds": 86400,
    }
    for key, limit in limits.items():
        n = row[key]
        if type(n) is not int or not 0 <= n <= limit:
            raise ValueError("economy input outside bounded nonnegative preview range")
    if row["heartRegenSeconds"] == 0:
        raise ValueError("heart regen must be a positive duration")
    gross = row["levelCompletions"] * row["coinsEarnedPerCompletion"] + row["dailyEarnedCoins"]
    sinks = row["boosterPurchases"] * row["coinsPerBooster"]
    return {
        "profileId": game, "scenarioId": scenario,
        "hypotheticalCoinsEarned": gross,
        "hypotheticalCoinsSpent": sinks,
        "hypotheticalNetCoins": gross - sinks,
        "potentialDeficitInHypotheticalScenario": sinks > gross,
        "heartRegenSecondsAssumedNotEngineVerified": row["heartRegenSeconds"],
        "liveUserBalanceRead": False,
        "actualCoinsOrLivesGrantedOrDebited": False,
    }


def _placement(row: dict[str, Any]) -> dict[str, Any]:
    fields = {
        "profileId", "placementId", "placementType", "frequencyCapPerDay",
        "requiresOptIn", "noFillFallback", "enabled",
    }
    if not isinstance(row, dict) or set(row) != fields:
        raise ValueError("placement must use strict known fields only")
    profile = _entry_game(row)
    if not isinstance(row["placementId"], str) or _ID.fullmatch(row["placementId"]) is None:
        raise ValueError("invalid placement identifier")
    if row["placementType"] not in _PLACEMENTS:
        raise ValueError("unknown offer/ad placement type")
    if type(row["frequencyCapPerDay"]) is not int or not 0 <= row["frequencyCapPerDay"] <= 20:
        raise ValueError("unbounded offer pressure rejected")
    if row["requiresOptIn"] is not True:
        raise ValueError("offer or rewarded content must be strictly opt-in")
    if row["noFillFallback"] not in ("DISABLED", "CONTINUE_WITHOUT_AD"):
        raise ValueError("missing safe no-fill or offline fallback")
    if row["enabled"] is not False:
        raise ValueError("real ad/offer/claim engagement remains disabled until age and Engine approvals")
    return {
        "profileId": profile, "placementId": row["placementId"],
        "placementType": row["placementType"],
        "frequencyCapPerDayProposal": row["frequencyCapPerDay"],
        "fallback": row["noFillFallback"],
        "requiresOptIn": True,
        "localPreviewOnly": True,
        "canShowRealStoreOrAds": False,
        "childPolicyOverridePossible": False,
    }


def _callback(row: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(row, dict) or set(row) != {
        "profileId", "callbackKind", "outcome", "eventReference"
    }:
        raise ValueError("callback must not contain receipt, identity, server override or grant")
    game = _entry_game(row)
    if row["callbackKind"] not in _CB_KINDS or row["outcome"] not in _CB_OUTCOMES:
        raise ValueError("authoritative success is not observable in this offline workbench")
    ref = row["eventReference"]
    if not isinstance(ref, str) or _REF.fullmatch(ref) is None:
        raise ValueError("bounded non-identifying callback audit reference required")
    return {
        "profileId": game, "callbackKind": row["callbackKind"],
        "outcome": row["outcome"], "eventReference": ref,
        "verifiedServerReceipt": False,
        "claimedIdempotency": False,
        "storeOrAdCallbackPerformed": False,
        "entitlementOrCoinsGranted": False,
    }


def preflight_m13_milestone(*, git_commit_sha: str,
                            store_items: list[dict[str, Any]],
                            iap_bindings: list[dict[str, Any]],
                            placements: list[dict[str, Any]],
                            economy_cases: list[dict[str, Any]],
                            assets: list[dict[str, Any]],
                            messages: dict[str, dict[str, dict[str, str]]],
                            ui_states: list[dict[str, Any]],
                            callbacks: list[dict[str, Any]],
                            previous_store_items: list[dict[str, Any]] | None = None,
                            owner_review_reference: str | None = None) -> dict[str, Any]:
    """Run one bounded M13 cross-title preview with NO remote or player actions."""
    if not isinstance(git_commit_sha, str) or _SHA40.fullmatch(git_commit_sha) is None:
        raise ValueError("invalid unverified 40-hex git revision")
    inputs = ((store_items, 128), (iap_bindings, 128), (placements, 128),
              (economy_cases, 128), (assets, 256), (ui_states, 256), (callbacks, 128))
    for value, bound in inputs:
        if not isinstance(value, list) or len(value) > bound:
            raise ValueError("unbounded or invalid M13 input array")
    if not isinstance(messages, dict) or set(messages) != set(PROFILES):
        raise ValueError("all five title localizations must be explicit")
    if owner_review_reference is not None and (
        not isinstance(owner_review_reference, str) or
        not 5 <= len(owner_review_reference.strip()) <= 256 or
        any(ord(c) < 32 for c in owner_review_reference)
    ):
        raise ValueError("invalid unsigned owner review reference")

    catalog = propose_store_catalog(store_items)
    # A title cannot silently re-use another game's client-side app namespace.
    namespaces = {}
    for product in catalog["products"]:
        key = (product["store"], product["appNamespace"])
        if key in namespaces and namespaces[key] != product["profileId"]:
            raise ValueError("multiple games cannot share a purported store app namespace")
        namespaces[key] = product["profileId"]
    bindings = audit_iap_entitlement_bindings(catalog, iap_bindings)
    if bindings["entitlementsIssued"] != 0 or bindings["publisherAuthorized"]:
        raise ValueError("existing IAP binding unexpectedly authorizes a grant")

    age = []
    for game in PROFILES:
        strict_flags = {key: False for key in FLAGS}
        diag = validate_age_liveops_config(profile_id=game, flags=strict_flags)
        if not diag["localPreviewAllowed"] or diag["realStoreAdsOrPersonalizationEligible"]:
            raise ValueError("age policy gate failed closed")
        age.append({"profileId": game, "audiencePolicy": diag["audiencePolicy"],
                    "adsOrPurchasesEligible": False,
                    "requiresIndependentAgeLegalReview": True})

    placement_receipts = []
    placement_keys = set()
    for row in placements:
        receipt = _placement(row)
        key = (receipt["profileId"], receipt["placementId"])
        if key in placement_keys:
            raise ValueError("duplicate placement slot")
        placement_keys.add(key)
        placement_receipts.append(receipt)
    placement_receipts.sort(key=lambda x: (x["profileId"], x["placementId"]))

    balances = []
    balance_keys = set()
    for row in economy_cases:
        b = _economy(row)
        key = (b["profileId"], b["scenarioId"])
        if key in balance_keys:
            raise ValueError("duplicate economy preview scenario")
        balance_keys.add(key)
        balances.append(b)
    balances.sort(key=lambda x: (x["profileId"], x["scenarioId"]))

    rights = audit_asset_bindings(assets)
    if rights["distributionAuthorized"]:
        raise ValueError("rights intake must never grant production redistribution")
    preview_art_slots = {(a["profileId"], a["slotId"])
                         for a in rights["entries"] if a["localPreviewCandidate"]}

    translations = []
    allowed_keys = {}
    for game in PROFILES:
        text = messages[game]
        if not isinstance(text, dict) or not 1 <= len(text) <= 128:
            raise ValueError("every game needs nonempty localized key catalogue")
        lang = build_localization_qa(game, text)
        if lang["productionApproved"]:
            raise ValueError("localization QA unexpectedly authorizes store build")
        allowed_keys[game] = set(text)
        translations.append({
            "profileId": game, "messageKeys": len(lang["entries"]),
            "missingTranslations": len(lang["missingTranslations"]),
            "ownerLinguisticReviewRequired": True,
            "runtimeApproved": False,
        })

    states = []
    state_keys = set()
    for row in ui_states:
        if not isinstance(row, dict) or set(row) != {
            "profileId", "stateId", "messageKey", "assetSlot", "enabled", "disabledReason"
        }:
            raise ValueError("unsupported UI state or button fields")
        game = _entry_game(row)
        if row["stateId"] not in _UI_STATES:
            raise ValueError("unknown player-visible UI state")
        if row["messageKey"] not in allowed_keys[game]:
            raise ValueError("unlocalized player-visible CTA")
        slot = row["assetSlot"]
        if slot is not None and (slot not in COMMON_SLOTS or (game, slot) not in preview_art_slots):
            raise ValueError("unreviewed or foreign theme preview slot")
        if row["enabled"] is not False:
            raise ValueError("fake functional CTA blocked until runtime backing exists")
        reason = row["disabledReason"]
        if not isinstance(reason, str) or not 5 <= len(reason) <= 100:
            raise ValueError("every disabled CTA must explain why it is unavailable")
        key = (game, row["stateId"])
        if key in state_keys:
            raise ValueError("duplicate UI state per game")
        state_keys.add(key)
        states.append({
            "profileId": game, "stateId": row["stateId"],
            "messageKey": row["messageKey"], "assetSlot": slot,
            "disabledReason": reason,
            "actualRuntimeActionEnabled": False,
        })
    states.sort(key=lambda x: (x["profileId"], x["stateId"]))

    blocked_callbacks = []
    callback_keys = set()
    for record in callbacks:
        c = _callback(record)
        key = (c["profileId"], c["callbackKind"], c["eventReference"])
        if key in callback_keys:
            raise ValueError("duplicate callback/claim reference cannot mint an entitlement")
        callback_keys.add(key)
        blocked_callbacks.append(c)
    blocked_callbacks.sort(key=lambda x: (x["profileId"], x["callbackKind"], x["eventReference"]))

    prior_diff = None
    if previous_store_items is not None:
        if not isinstance(previous_store_items, list):
            raise ValueError("previous local catalog must be a list")
        old = propose_store_catalog(previous_store_items)
        old_items = {(r["profileId"], r["store"], r["skuId"]): r for r in old["products"]}
        new_items = {(r["profileId"], r["store"], r["skuId"]): r for r in catalog["products"]}
        prior_diff = {
            "new": sorted("/".join(k) for k in new_items.keys() - old_items.keys()),
            "removed": sorted("/".join(k) for k in old_items.keys() - new_items.keys()),
            "changed": sorted("/".join(k) for k in old_items.keys() & new_items.keys()
                              if old_items[k] != new_items[k]),
            "oldUnsignedCatalogSha256": _digest(old),
            "productionChangeAuthorized": False,
        }

    matrix = {
        "LFX-M13-001": "LOCAL_SYMBOLIC_SKU_ONLY_NO_STORE_PRICING",
        "LFX-M13-002": "AGE_BLOCKED_AD_OFFER_PLACEMENT_PROPOSALS_ONLY",
        "LFX-M13-003": "INTEGER_HYPOTHETICAL_ECONOMY_NO_PLAYER_LEDGER",
        "LFX-M13-004": "IAP_METADATA_REVIEW_ONLY_NO_RECEIPT_OR_GRANT",
        "LFX-M13-005": "ORIGINAL_OR_RIGHTS_REVIEWED_ASSET_INTAKE_NOT_DISTRIBUTION",
        "LFX-M13-006": "FIVE_GAME_LOCALIZATION_QA_UNREVIEWED_TRANSLATIONS",
        "LFX-M13-007": "ALL_UNVERIFIED_AGE_AD_AND_PERSONALIZATION_GATES_DISABLED",
        "LFX-M13-008": "LOCAL_SHA_ONLY_NO_STAGING_OR_ENG_M20_M21_CONTRACT",
        "LFX-M13-009": "UNSIGNED_LOCAL_CATALOG_DIFF_ONLY" if prior_diff else "NO_BASELINE_CATALOG",
        "LFX-M13-010": "UNVERIFIED_CALLBACKS_NEVER_MINT_ENTITLEMENTS",
        "LFX-M13-011": "DISABLED_LOCALIZED_UI_ACTIONS_ONLY_NO_RUNTIME",
    }
    if set(matrix) != set(TASK_IDS):
        raise RuntimeError("M13 whole-milestone task identity drift")
    payload = {
        "catalog": catalog,
        "iapBindings": bindings,
        "placements": placement_receipts,
        "economyScenarios": balances,
        "previewAssetRights": rights,
        "localization": translations,
        "ageGuards": age,
        "playerVisibleUI": states,
        "untrustedCallbackPreviews": blocked_callbacks,
        "catalogDiff": prior_diff,
    }
    return {
        "schemaVersion": 1,
        "resultStatus": "M13_OFFLINE_WORKBENCH_REVIEW_ONLY",
        "engineStatus": "BLOCKED_ENG_M24",
        "engM20M21ApprovedRuntimeContractsAvailable": False,
        "sourceGitCommitShaUnverified": git_commit_sha,
        "ownerReviewReferenceUnverified": owner_review_reference,
        "unsignedLocalReviewSha256": _digest(payload),
        "diagnostics": payload,
        "realStoreProductPricingRead": False,
        "serverReceiptVerified": False,
        "consumerEntitlementsMinted": 0,
        "advertisementsDisplayed": False,
        "actualUserCoinsOrLivesModified": False,
        "userAudienceOrPIIProcessed": False,
        "remoteStagingPerformed": False,
        "productionAuthorized": False,
        "ownerLegalApprovalVerified": False,
        "officialMilestonePass": False,
        "taskEvidenceMatrix": matrix,
        "remainingAcceptanceGates": [
            "ENG_M20_M21_AND_ENG_M24_ACCEPTED_INTERFACES_MISSING",
            "INDEPENDENT_AGE_AD_COMMERCE_AND_ASSET_RIGHTS_APPROVAL",
            "ACTUAL_STORE_PRODUCTS_SIGNED_RECEIPTS_AND_PRICE_RUNTIME_UNVERIFIED",
            "REAL_SERVER_CLAIM_IDEMPOTENCY_AND_PLAYER_LEDGER_UNVERIFIED",
            "STAGING_AND_RUNTIME_UI_OFFLINE_NO_FILL_REPLAY_NOT_RUN",
            "EXPLICIT_OWNER_APPROVAL_AND_INDEPENDENT_QA_NOT_RUN",
        ],
    }
