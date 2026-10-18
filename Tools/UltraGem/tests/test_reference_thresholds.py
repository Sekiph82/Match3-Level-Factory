from __future__ import annotations
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from reference_thresholds import make_reference_tier_policy,diagnose_metric_bias

class ReferenceThresholdTests(unittest.TestCase):
    def test_explicit_config_is_not_a_production_grade(self):
        p=make_reference_tier_policy(boundaries=[.1,.3,.7,.9],
            min_samples_per_persona=100,reviewer_reference="Owner/threshold-policy-R01")
        self.assertEqual(len(p["bands"]),5)
        self.assertIsNone(p["tierAssigned"])
        self.assertTrue(p["ownerCalibrationRequired"])
        self.assertFalse(p["releaseAuthorized"])
        self.assertEqual(p["engineStatus"],"BLOCKED_ENG_M24")
        for q in ([0,.3,.7,.9],[.3,.1,.7,.9],[.3,.3,.7,.9],[.1,.3,float("nan"),.9]):
            with self.assertRaises(ValueError):
                make_reference_tier_policy(boundaries=q,min_samples_per_persona=100,
                                           reviewer_reference="Owner/policy")
    def test_area_and_blocker_count_alone_never_certify_difficulty(self):
        r=diagnose_metric_bias(provided_features=["boardArea","obstacleCount"],
                              observed_personas=["smart","random"],claimed_result="CERTIFIED")
        self.assertIn("ONLY_GEOMETRY_OR_BLOCKER_COUNT",r["warnings"])
        self.assertIn("FIVE_ENGINE_PERSONA_RUNS_MISSING",r["warnings"])
        self.assertIn("UNSUPPORTED_CERTIFIED_DIFFICULTY_CLAIM",r["warnings"])
        self.assertFalse(r["canAssignCertifiedTier"])
        self.assertEqual(r["engineStatus"],"BLOCKED_ENG_M24")
        r=diagnose_metric_bias(provided_features=["goalPressure"],
                    observed_personas=["Beginner","Casual","Strategic","Expert","Random"])
        self.assertFalse(r["canAssignCertifiedTier"])
        self.assertFalse(r["releaseAuthorized"])

if __name__=="__main__":unittest.main()
