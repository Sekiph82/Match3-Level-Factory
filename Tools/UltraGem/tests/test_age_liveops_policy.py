from __future__ import annotations
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from age_liveops_policy import FLAGS,validate_age_liveops_config
from theme_contract import PROFILES

class AgeLiveOpsPolicyTests(unittest.TestCase):
    def flags(self):return {name:False for name in FLAGS}
    def test_all_five_default_to_strict_optout(self):
        for profile in PROFILES:
            with self.subTest(profile=profile):
                out=validate_age_liveops_config(profile_id=profile,flags=self.flags())
                self.assertEqual(out["rejectedFlags"],[])
                self.assertTrue(out["localPreviewAllowed"])
                self.assertFalse(out["releaseAuthorized"])
                self.assertFalse(out["realStoreAdsOrPersonalizationEligible"])
                self.assertTrue(out["requiresHumanAgeLegalReview"])
        self.assertEqual(validate_age_liveops_config(profile_id="Wonder_Pop",flags=self.flags())
                         ["audiencePolicy"],"CHILD_DIRECTED_5_12")
    def test_child_and_ambiguous_titles_cannot_bypass_with_review_reference(self):
        for profile in PROFILES:
            for sensitive in FLAGS:
                blocked=self.flags();blocked[sensitive]=True
                out=validate_age_liveops_config(profile_id=profile,flags=blocked,
                         audience_review_reference="Owner/unverified-review-R01")
                self.assertIn(sensitive,out["rejectedFlags"])
                self.assertFalse(out["localPreviewAllowed"])
                self.assertFalse(out["releaseAuthorized"])
    def test_unknown_fields_and_string_boolean_rejected(self):
        values=self.flags()
        values["enableSecretAds"]=True
        with self.assertRaises(ValueError):
            validate_age_liveops_config(profile_id="Wonder_Pop",flags=values)
        values=self.flags()
        values["personalizedAds"]="false"
        with self.assertRaises(ValueError):
            validate_age_liveops_config(profile_id="Coral_Rescue",flags=values)

if __name__=="__main__":unittest.main()
