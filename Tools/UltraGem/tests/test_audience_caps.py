import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from audience_caps import evaluate_content_caps
from theme_contract import PROFILES

class AudienceCapsTests(unittest.TestCase):
    def defaults(self):
        return dict(adsPerSession=0,earnedPacksPerDay=2,collectionItems=30,eventDurationHours=72,
                    streakPressureEnabled=False,forcedOfferPopups=0,premiumRewardCount=0,
                    personalizedEngagement=False)
    def test_five_profile_safe_neutral_preview_never_certifies_remote(self):
        for profile in PROFILES:
            r=evaluate_content_caps(profile,self.defaults())
            self.assertTrue(r['canPreviewLocally'])
            self.assertFalse(r['actualLegalAgeStatusVerified'])
            self.assertFalse(r['rewardGrantOrPublishAuthorized'])
            self.assertEqual(r['violations'],[])
    def test_wonder_child_and_ambiguous_age_profiles_block_pressure(self):
        for change, expected in [({'adsPerSession':1},'ADS_NOT_AGE_CLEARED'),
                                 ({'streakPressureEnabled':True},'CHILD_STREAK_PRESSURE_NOT_ALLOWED'),
                                 ({'premiumRewardCount':1},'CHILD_PREMIUM_REWARD_META_NOT_ALLOWED'),
                                 ({'eventDurationHours':24},'CHILD_SHORT_DEADLINE_PRESSURE'),
                                 ({'earnedPacksPerDay':4},'CHILD_EARNED_PACK_DAILY_CAP'),
                                 ({'collectionItems':101},'CHILD_COLLECTION_SCOPE_CAP')]:
            r=evaluate_content_caps('Wonder_Pop',{**self.defaults(),**change})
            self.assertIn(expected,r['violations'])
            self.assertFalse(r['canPreviewLocally'])
        r=evaluate_content_caps('Garage_Legends',{**self.defaults(),'adsPerSession':1})
        self.assertFalse(r['canPreviewLocally'])
    def test_extra_key_or_bool_count_fail_closed(self):
        with self.assertRaises(ValueError):evaluate_content_caps('Wonder_Pop',{**self.defaults(),'adminKey':'secret'})
        with self.assertRaises(ValueError):evaluate_content_caps('Wonder_Pop',{**self.defaults(),'adsPerSession':True})

if __name__=='__main__':unittest.main()
