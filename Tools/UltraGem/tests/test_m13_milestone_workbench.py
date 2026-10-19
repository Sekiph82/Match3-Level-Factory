"""M13 one-milestone conservative offline catalog and UI safety tests."""
from __future__ import annotations
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from m13_milestone_workbench import preflight_m13_milestone, TASK_IDS
from theme_contract import PROFILES


class M13WorkbenchTests(unittest.TestCase):
    @staticmethod
    def product(profile="Coral_Rescue"):
        name = profile.lower()
        namespace = "com.owner." + name
        return {
            "profileId": profile, "store": "GOOGLE_PLAY",
            "appNamespace": namespace,
            "skuId": namespace + ".booster001",
            "productType": "CONSUMABLE",
            "descriptionKey": "catalog.booster001",
            "entitlementId": "booster.slot1",
        }

    @staticmethod
    def balance(profile):
        return {
            "profileId": profile, "scenarioId": "sample.balance",
            "levelCompletions": 3, "coinsEarnedPerCompletion": 100,
            "dailyEarnedCoins": 25, "boosterPurchases": 2,
            "coinsPerBooster": 40, "heartRegenSeconds": 900,
        }

    @staticmethod
    def placement(profile, placement_type="REWARDED_AD"):
        return {
            "profileId": profile,
            "placementId": "booster.optin",
            "placementType": placement_type,
            "frequencyCapPerDay": 2, "requiresOptIn": True,
            "noFillFallback": "CONTINUE_WITHOUT_AD",
            "enabled": False,
        }

    @staticmethod
    def state(profile, state="BUY"):
        return {
            "profileId": profile, "stateId": state,
            "messageKey": "ui.cta", "assetSlot": None,
            "enabled": False, "disabledReason": "Offline review only",
        }

    def args(self):
        return {
            "git_commit_sha": "a" * 40,
            "store_items": [],
            "iap_bindings": [],
            "placements": [self.placement(p) for p in PROFILES],
            "economy_cases": [self.balance(p) for p in PROFILES],
            "assets": [],
            "messages": {p: {"ui.cta": {"en": "Unavailable",
                                      "tr": "Kullanilamiyor"}} for p in PROFILES},
            "ui_states": [self.state(p) for p in PROFILES],
            "callbacks": [],
        }

    def run_preview(self, **changes):
        sample = self.args()
        sample.update(changes)
        return preflight_m13_milestone(**sample)

    def test_all_eleven_m13_tasks_five_game_offline_never_authorizes(self):
        args = self.args()
        saved = copy.deepcopy(args)
        result = preflight_m13_milestone(**args)
        self.assertEqual(args, saved)
        self.assertEqual(set(result["taskEvidenceMatrix"]), set(TASK_IDS))
        self.assertEqual(len(result["diagnostics"]["localization"]), 5)
        self.assertEqual(len(result["diagnostics"]["ageGuards"]), 5)
        self.assertEqual(len(result["diagnostics"]["placements"]), 5)
        self.assertEqual(len(result["diagnostics"]["playerVisibleUI"]), 5)
        self.assertEqual(len(result["diagnostics"]["economyScenarios"]), 5)
        self.assertFalse(result["officialMilestonePass"])
        self.assertFalse(result["productionAuthorized"])
        self.assertFalse(result["remoteStagingPerformed"])
        self.assertFalse(result["realStoreProductPricingRead"])
        self.assertEqual(result["consumerEntitlementsMinted"], 0)
        self.assertFalse(result["userAudienceOrPIIProcessed"])
        self.assertEqual(result["engineStatus"], "BLOCKED_ENG_M24")
        self.assertEqual(result, self.run_preview(
            placements=list(reversed(args["placements"])),
            economy_cases=list(reversed(args["economy_cases"])),
            ui_states=list(reversed(args["ui_states"]))))

    def test_five_title_catalog_bindings_and_no_static_price(self):
        products = [self.product(p) for p in PROFILES]
        bindings = [
            {k: x[k] for k in ("profileId", "store", "skuId", "entitlementId")}
            for x in products
        ]
        result = self.run_preview(store_items=products, iap_bindings=bindings)
        catalog = result["diagnostics"]["catalog"]
        self.assertEqual(len(catalog["products"]), 5)
        self.assertFalse(catalog["entitlementOrPurchaseAuthorized"])
        self.assertEqual(result["diagnostics"]["iapBindings"]["entitlementsIssued"], 0)
        self.assertTrue(all(not x["clientCanMintEntitlement"]
                            for x in catalog["products"]))
        tampered = copy.deepcopy(products)
        tampered[0]["priceUsd"] = 2.99
        with self.assertRaises(ValueError):
            self.run_preview(store_items=tampered)
        binding = copy.deepcopy(bindings)
        binding[0]["entitlementId"] = "premium.unlimited"
        with self.assertRaises(ValueError):
            self.run_preview(store_items=products, iap_bindings=binding)
        duplicate_namespace = copy.deepcopy(products)
        duplicate_namespace[1]["appNamespace"] = products[0]["appNamespace"]
        duplicate_namespace[1]["skuId"] = products[0]["skuId"]
        with self.assertRaises(ValueError):
            self.run_preview(store_items=duplicate_namespace)

    def test_opt_in_offer_caps_and_all_unverified_age_flags_fail_closed(self):
        for profile in PROFILES:
            row = self.placement(profile)
            row["enabled"] = True
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                self.run_preview(placements=[row])
        for field, value in (("requiresOptIn", False), ("frequencyCapPerDay", 99),
                             ("noFillFallback", "NO_SAFE_FALLBACK"),
                             ("placementType", "FORCED_AD")):
            row = self.placement("Wonder_Pop")
            row[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.run_preview(placements=[row])

    def test_hypothetical_economy_detects_overspend_never_mints(self):
        row = self.balance("Garage_Legends")
        r = self.run_preview(economy_cases=[row])
        outcome = r["diagnostics"]["economyScenarios"][0]
        self.assertEqual(outcome["hypotheticalCoinsEarned"], 325)
        self.assertEqual(outcome["hypotheticalCoinsSpent"], 80)
        self.assertEqual(outcome["hypotheticalNetCoins"], 245)
        self.assertFalse(outcome["actualCoinsOrLivesGrantedOrDebited"])
        row["boosterPurchases"] = 50
        deficit = self.run_preview(economy_cases=[row])
        self.assertTrue(deficit["diagnostics"]["economyScenarios"][0]
                        ["potentialDeficitInHypotheticalScenario"])
        self.assertFalse(deficit["actualUserCoinsOrLivesModified"])
        row["coinsPerBooster"] = -1
        with self.assertRaises(ValueError):
            self.run_preview(economy_cases=[row])

    def test_localization_disabled_CTA_and_asset_evidence(self):
        ui = self.state("Wonder_Pop", state="WATCH_AD")
        with self.assertRaises(ValueError):
            self.run_preview(ui_states=[dict(ui, enabled=True)])
        with self.assertRaises(ValueError):
            self.run_preview(ui_states=[dict(ui, messageKey="missing.key")])
        with self.assertRaises(ValueError):
            self.run_preview(ui_states=[dict(ui, assetSlot="ui.booster")])
        asset = {
            "profileId": "Wonder_Pop", "slotId": "ui.booster",
            "kind": "UI_ICON", "rightsStatus": "OWNER_ORIGINAL",
            "sourceReference": "Owner/original-ui-icon",
            "contentSha256": "b" * 64,
            "permissionEvidenceReference": "Owner/license-evidence",
            "scope": "LOCAL_EDITOR_PREVIEW_ONLY",
        }
        output = self.run_preview(
            assets=[asset], ui_states=[dict(ui, assetSlot="ui.booster")])
        self.assertEqual(output["diagnostics"]["previewAssetRights"]["blocked"], 0)
        asset["rightsStatus"] = "REFERENCE_ONLY"
        with self.assertRaises(ValueError):
            self.run_preview(assets=[asset], ui_states=[dict(ui, assetSlot="ui.booster")])
        messages = self.args()["messages"]
        messages["Coral_Rescue"]["ui.cta"]["tr"] = "=UNSAFE()"
        with self.assertRaises(ValueError):
            self.run_preview(messages=messages)

    def test_failed_callback_cancelled_ad_duplicate_claim_never_grants(self):
        callback = {
            "profileId": "Coral_Rescue", "callbackKind": "CLAIM",
            "outcome": "DUPLICATE", "eventReference": "daily.reward.01",
        }
        result = self.run_preview(callbacks=[callback])
        c = result["diagnostics"]["untrustedCallbackPreviews"][0]
        self.assertFalse(c["entitlementOrCoinsGranted"])
        self.assertFalse(c["verifiedServerReceipt"])
        self.assertEqual(result["consumerEntitlementsMinted"], 0)
        with self.assertRaises(ValueError):
            self.run_preview(callbacks=[callback, copy.deepcopy(callback)])
        for outcome in ("SUCCESS", "SERVER_VERIFIED", "UNSIGNED_GRANT"):
            with self.assertRaises(ValueError):
                self.run_preview(callbacks=[dict(callback, outcome=outcome)])
        with self.assertRaises(ValueError):
            self.run_preview(callbacks=[dict(callback, userEmail="private@example.com")])

    def test_local_catalog_diff_and_fake_owner_approval_cannot_publish(self):
        old = [self.product("Coral_Rescue")]
        new = [self.product("Coral_Rescue"), self.product("Dino_Islands")]
        result = self.run_preview(
            store_items=new, previous_store_items=old,
            owner_review_reference="Owner/review-pending")
        diff = result["diagnostics"]["catalogDiff"]
        self.assertEqual(len(diff["new"]), 1)
        self.assertEqual(diff["changed"], [])
        self.assertFalse(diff["productionChangeAuthorized"])
        self.assertFalse(result["ownerLegalApprovalVerified"])
        self.assertFalse(result["productionAuthorized"])
        with self.assertRaises(ValueError):
            self.run_preview(owner_review_reference="Owner\nAPPROVED")


if __name__ == "__main__":
    unittest.main()
