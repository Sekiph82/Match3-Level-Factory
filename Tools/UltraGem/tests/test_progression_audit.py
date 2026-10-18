import copy
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tutorial_templates import make_tutorial_templates
from progression_audit import audit_progression

class ProgressionAuditTests(unittest.TestCase):
    def test_three_synthetic_lessons_do_not_claim_winnability(self):
        levels=make_tutorial_templates('Coral_Rescue')
        r=audit_progression(levels)
        self.assertEqual(r['candidateCount'],3)
        self.assertEqual(r['warnings'],[])
        self.assertFalse(r['playabilityCertified'])
        self.assertFalse(r['releaseAuthorized'])
    def test_premature_special_and_repetition_warn_not_certify(self):
        levels=make_tutorial_templates('Coral_Rescue')
        levels[0]['cells'][0]['specialId']='template.bomb'
        for d in levels[1:]:d['goals'][0]['targetCount']=levels[0]['goals'][0]['targetCount']
        codes=[x['code'] for x in audit_progression(levels)['warnings']]
        self.assertIn('TUTORIAL_ADVANCED_MECHANICS_PRESENT',codes)
        self.assertIn('REPEATED_EXACT_GOALS',codes)
    def test_duplicate_identity_fails_closed(self):
        levels=make_tutorial_templates('Garage_Legends')
        with self.assertRaises(ValueError):audit_progression([levels[0],copy.deepcopy(levels[0])])
        with self.assertRaises(ValueError):audit_progression(levels,repeated_goal_warning_at=1)

if __name__=='__main__':unittest.main()
