import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import leveldraft
from tutorial_templates import make_tutorial_templates,tutorial_source_receipt
from theme_contract import PROFILES

class TutorialTemplatesTests(unittest.TestCase):
    def test_all_five_three_levels_stable_original_noncertified(self):
        for game in PROFILES:
            drafts=make_tutorial_templates(game)
            self.assertEqual(len(drafts),3)
            self.assertEqual([(d['width'],d['height']) for d in drafts],[(4,4),(5,4),(5,5)])
            self.assertEqual([sum(not b for b in d['activeMask']) for d in drafts],[0,0,1])
            self.assertEqual([d['goals'][0]['targetCount'] for d in drafts],[3,5,8])
            self.assertTrue(all(d['validationStatus']=='PROTOTYPE_ONLY' for d in drafts))
            self.assertTrue(all(not any(c['specialId'] or c['locked'] for c in d['cells']) for d in drafts))
            for d in drafts:self.assertEqual(leveldraft.loads_strict(leveldraft.dumps_canonical(d)),d)
            self.assertEqual(drafts,make_tutorial_templates(game))
            receipt=tutorial_source_receipt(game)
            self.assertFalse(receipt['releaseAuthorized'])
            self.assertTrue(all(not x['certifiedEasyOrSolvable'] for x in receipt['templates']))
    def test_bad_profile_seed_rejected(self):
        for seed in (-1,True,2**63-2):
            with self.assertRaises(ValueError):make_tutorial_templates('Coral_Rescue',seed=seed)
        with self.assertRaises(ValueError):make_tutorial_templates('bad_game')

if __name__=='__main__':unittest.main()
