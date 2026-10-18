from __future__ import annotations
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from store_catalog import propose_store_catalog
from theme_contract import PROFILES

class StoreCatalogTests(unittest.TestCase):
    def entry(self,profile="Coral_Rescue",store="APPLE_APP_STORE"):
        return {
          "profileId":profile,"store":store,
          "appNamespace":"com.owner.samplegame",
          "skuId":"com.owner.samplegame.booster001",
          "productType":"CONSUMABLE",
          "descriptionKey":"catalog.booster001",
          "entitlementId":"booster.slot1",
        }
    def test_five_title_catalog_is_metadata_only_not_price_or_grant(self):
        rows=[]
        for index,profile in enumerate(PROFILES):
            p=self.entry(profile)
            p["appNamespace"]=f"com.owner.game{index+1}"
            p["skuId"]=p["appNamespace"]+".booster001"
            rows.append(p)
        output=propose_store_catalog(rows)
        self.assertEqual(len(output["products"]),5)
        self.assertFalse(output["containsStaticPriceOrCurrency"])
        self.assertFalse(output["entitlementOrPurchaseAuthorized"])
        self.assertEqual(output["liveStorePricingSource"],"STORE_RUNTIME_ONLY")
        for item in output["products"]:
            self.assertFalse(item["storeSkuExistenceVerified"])
            self.assertFalse(item["clientCanMintEntitlement"])
            self.assertTrue(item["serverReceiptVerificationRequired"])
        child=next(x for x in output["products"] if x["profileId"]=="Wonder_Pop")
        self.assertTrue(child["childPolicyRequiresIndependentReview"])
        self.assertEqual(output,propose_store_catalog(rows))
    def test_fake_price_and_foreign_namespace_cannot_be_serialized(self):
        p=self.entry();p["price"]=2.99
        with self.assertRaises(ValueError):propose_store_catalog([p])
        p=self.entry();p["skuId"]="com.other.fake.booster"
        with self.assertRaises(ValueError):propose_store_catalog([p])
        p=self.entry()
        with self.assertRaises(ValueError):propose_store_catalog([p,p])
        p=self.entry();p["productType"]="FREE_PREMIUM_MINT"
        with self.assertRaises(ValueError):propose_store_catalog([p])

if __name__=="__main__":unittest.main()
