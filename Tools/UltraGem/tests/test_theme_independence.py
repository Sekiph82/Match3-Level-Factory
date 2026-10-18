"""LFX-M08-009: Theme configuration cannot mutate the reference draft.

This is a source-side separation regression, not a certified Engine replay.
"""
from __future__ import annotations
import copy
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import leveldraft
from theme_contract import create_symbolic_theme_contract
from neutral_preview_recipes import geometric_preview_recipe

class ThemeIndependenceTests(unittest.TestCase):
    def test_theme_and_reduced_motion_never_change_canonical_draft(self):
        file=ROOT.parents[1]/"Assets/Match3Factory/Tests/Fixtures/ultragem_seed_712_draft.json"
        draft=leveldraft.loads_strict(file.read_text(encoding="utf-8"))
        before=copy.deepcopy(draft)
        golden=leveldraft.sha256(draft)
        for profile in ("Coral_Rescue","Garage_Legends","Dino_Islands",
                        "The_Fractured_Realms","Wonder_Pop"):
            for reduced in (True,False):
                themed=create_symbolic_theme_contract(profile,slot_assignments={
                    "ui.goal":"ref:Owner/ui-icon-0001"})
                recipe=geometric_preview_recipe(profile,reduced_motion=reduced)
                self.assertTrue(themed["doesNotModifyGameplay"])
                self.assertFalse(recipe["isGameplayRuleSource"])
                self.assertEqual(leveldraft.sha256(draft),golden)
                self.assertEqual(draft,before)
        self.assertEqual(golden,"fffe76265e590a787b3e1284a2960b378c88df3f0f5260f3d10faf639d5c794d")

if __name__=="__main__":unittest.main()
