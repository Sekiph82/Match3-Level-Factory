from __future__ import annotations
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from neutral_preview_recipes import all_preview_recipes, geometric_preview_recipe

class NeutralPreviewRecipesTests(unittest.TestCase):
    def test_all_five_have_original_distinguishable_shapes_and_reduced_motion(self):
        items=all_preview_recipes()
        self.assertEqual(len(items),5)
        self.assertEqual(len({p["profileId"] for p in items}),5)
        self.assertEqual(len({p["backgroundHex"] for p in items}),5)
        for item in items:
            self.assertEqual(len(item["pieceShapes"]),3)
            self.assertEqual(len({s["kind"] for s in item["pieceShapes"]}),3)
            self.assertFalse(item["releaseAuthorized"])
            self.assertFalse(item["isGameplayRuleSource"])
            self.assertEqual(item["engineStatus"],"BLOCKED_ENG_M24")
            self.assertEqual(item["frames"],1)
            self.assertTrue(item["reducedMotion"])
    def test_optional_animation_does_not_mutate_game_state(self):
        static=geometric_preview_recipe("Wonder_Pop")
        animated=geometric_preview_recipe("Wonder_Pop",reduced_motion=False)
        self.assertEqual(static["pieceShapes"],animated["pieceShapes"])
        self.assertEqual(animated["frames"],2)
        self.assertNotIn("moves",animated)
        self.assertNotIn("rngSeed",animated)
        with self.assertRaises(ValueError):
            geometric_preview_recipe("Wonder_Pop",reduced_motion="no")

if __name__=="__main__": unittest.main()
