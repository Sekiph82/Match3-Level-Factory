from __future__ import annotations
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from vuf_handoff import five_game_visual_inventory,visual_state_contract,BASE_STATES

class VufHandoffTests(unittest.TestCase):
    def test_all_five_include_claim_rewards_boosters_purchases_offline_disabled(self):
        profiles=five_game_visual_inventory()
        self.assertEqual(len(profiles),5)
        self.assertEqual(len({p["gameProfileId"] for p in profiles}),5)
        for p in profiles:
            self.assertEqual(len(p["states"]),len(BASE_STATES))
            self.assertEqual({s["stateId"] for s in p["states"]},set(BASE_STATES))
            self.assertTrue(p["ownerVisualAcceptanceRequired"])
            self.assertFalse(p["assetOrGameplaySourceIncluded"])
            self.assertFalse(p["productionApproved"])
            self.assertEqual(p["engineStatus"],"BLOCKED_ENG_M24")
    def test_child_title_ads_require_special_review(self):
        x=visual_state_contract("Wonder_Pop")
        ads=[s for s in x["states"] if s["stateId"].startswith("ads.")]
        self.assertEqual(len(ads),2)
        self.assertTrue(all(s["requiresChildPolicyReview"] and not s["previewEnabled"] for s in ads))
        with self.assertRaises(ValueError):
            visual_state_contract("UnknownTitle")

if __name__=="__main__":unittest.main()
