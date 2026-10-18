from __future__ import annotations
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from experiment_config import propose_experiment
from theme_contract import PROFILES

class ExperimentConfigTests(unittest.TestCase):
    def data(self):
        return [dict(variantId="A",weightPercent=45,configReference="Drive/config-A"),
                dict(variantId="B",weightPercent=45,configReference="Drive/config-B")]
    def sample(self,game="Coral_Rescue"):
        return propose_experiment(game_id=game,experiment_id="offer_preview",
            variants=self.data(),holdout_percent=10,
            audience_mode="NON_PERSONALIZED_OPT_IN_ONLY",rollback_reference="Drive/rollback-plan")
    def test_five_profiles_have_optin_and_holdout_with_no_user_allocation(self):
        for game in PROFILES:
            with self.subTest(game=game):
                p=self.sample(game)
                self.assertEqual(p["holdoutPercent"],10)
                self.assertFalse(p["personalDataProcessed"])
                self.assertFalse(p["stableAllocatorImplemented"])
                self.assertFalse(p["remoteDeploymentAuthorized"])
                self.assertEqual(p["engineStatus"],"BLOCKED_ENG_M24")
                self.assertTrue(p["requiresConsentBeforeEligibility"])
                self.assertEqual(p,self.sample(game))
    def test_bad_weights_behavioral_targeting_or_missing_rollback_rejected(self):
        with self.assertRaises(ValueError):
            propose_experiment(game_id="Wonder_Pop",experiment_id="test_exp",
                variants=self.data(),holdout_percent=10,audience_mode="BEHAVIORAL_TARGETING",
                rollback_reference="Drive/rollback-plan")
        wrong=self.data()
        wrong[0]["weightPercent"]=40
        with self.assertRaises(ValueError):
            propose_experiment(game_id="Coral_Rescue",experiment_id="test_exp",
                variants=wrong,holdout_percent=10,audience_mode="NON_PERSONALIZED_OPT_IN_ONLY",
                rollback_reference="Drive/rollback-plan")
        with self.assertRaises(ValueError):
            propose_experiment(game_id="Coral_Rescue",experiment_id="test_exp",
                variants=self.data(),holdout_percent=10,audience_mode="NON_PERSONALIZED_OPT_IN_ONLY",
                rollback_reference="")
        wrong=self.data();wrong[1]["userCookieKey"]="tracking"
        with self.assertRaises(ValueError):
            propose_experiment(game_id="Coral_Rescue",experiment_id="test_exp",
                variants=wrong,holdout_percent=10,audience_mode="NON_PERSONALIZED_OPT_IN_ONLY",
                rollback_reference="Drive/rollback-plan")

if __name__=="__main__":
    unittest.main()
