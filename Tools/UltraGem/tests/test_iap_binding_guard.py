from __future__ import annotations
import copy
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from store_catalog import propose_store_catalog
from iap_binding_guard import audit_iap_entitlement_bindings

class IapBindingGuardTests(unittest.TestCase):
    def catalog(self):
        return propose_store_catalog([{
            "profileId":"Coral_Rescue","store":"GOOGLE_PLAY",
            "appNamespace":"com.owner.samplegame",
            "skuId":"com.owner.samplegame.booster001",
            "productType":"CONSUMABLE","descriptionKey":"catalog.booster001",
            "entitlementId":"booster.slot1",
        }])
    def binding(self):
        return {"profileId":"Coral_Rescue","store":"GOOGLE_PLAY",
                "skuId":"com.owner.samplegame.booster001",
                "entitlementId":"booster.slot1"}
    def test_receipt_is_unverified_and_never_mints_entitlement(self):
        report=audit_iap_entitlement_bindings(self.catalog(),[self.binding()])
        self.assertFalse(report["storeVerificationPerformed"])
        self.assertEqual(report["entitlementsIssued"],0)
        self.assertFalse(report["publisherAuthorized"])
        self.assertFalse(report["runtimeStorePricesAvailable"])
        self.assertFalse(report["bindings"][0]["clientEntitlementMintAllowed"])
        self.assertEqual(report["engineStatus"],"BLOCKED_ENG_M24")
    def test_wrong_entitlement_unknown_sku_and_fake_grant_fail_closed(self):
        p=self.binding()
        p["entitlementId"]="premium.unlimited"
        with self.assertRaises(ValueError):audit_iap_entitlement_bindings(self.catalog(),[p])
        p=self.binding();p["skuId"]="com.fake.alternate"
        with self.assertRaises(ValueError):audit_iap_entitlement_bindings(self.catalog(),[p])
        with self.assertRaises(ValueError):audit_iap_entitlement_bindings(self.catalog(),[self.binding(),self.binding()])
        catalog=copy.deepcopy(self.catalog())
        catalog["products"][0]["clientCanMintEntitlement"]=True
        with self.assertRaises(ValueError):audit_iap_entitlement_bindings(catalog,[self.binding()])
        p=self.binding();p["verifiedPurchase"]=True
        with self.assertRaises(ValueError):audit_iap_entitlement_bindings(self.catalog(),[p])

if __name__=="__main__":unittest.main()
