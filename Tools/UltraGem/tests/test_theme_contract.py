from __future__ import annotations
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from theme_contract import (all_five_theme_contracts, create_symbolic_theme_contract,
                            COMMON_SLOTS, GENERIC_PLACEHOLDER)

class ThemeContractTests(unittest.TestCase):
    def test_every_profile_has_neutral_slots_not_game_authority(self):
        t=all_five_theme_contracts()
        self.assertEqual(len(t),5)
        self.assertEqual(len({x["profileId"] for x in t}),5)
        for x in t:
            self.assertEqual(len(x["slots"]),len(COMMON_SLOTS))
            self.assertFalse(x["releaseAuthorized"])
            self.assertTrue(x["doesNotModifyGameplay"])
            self.assertEqual(x["engineStatus"],"BLOCKED_ENG_M24")
            self.assertTrue(all(z["placeholderWhenMissing"]==GENERIC_PLACEHOLDER for z in x["slots"]))
    def test_symbolic_path_override_rejects_unknown_and_traversal(self):
        a=create_symbolic_theme_contract("Coral_Rescue",slot_assignments={"ui.goal":"ref:Owner/original-icon-v1"})
        self.assertTrue(any(x["symbolicBinding"]=="ref:Owner/original-icon-v1" for x in a["slots"]))
        for settings in ({"unknown":"ref:Owner/asset"},{"ui.goal":"../../secrets"},
                         {"ui.goal":"ref:x/../z"}):
            with self.assertRaises(ValueError):
                create_symbolic_theme_contract("Coral_Rescue",slot_assignments=settings)
        with self.assertRaises(ValueError):
            create_symbolic_theme_contract("WrongProfile")

if __name__=="__main__": unittest.main()
