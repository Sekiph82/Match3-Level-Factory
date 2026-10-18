"""Static feature extraction: deliberately no solver or difficulty assertions."""
from __future__ import annotations
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import leveldraft
from reference_features import extract_reference_features


class ReferenceFeaturesTests(unittest.TestCase):
    def get_draft(self):
        fixture = ROOT.parents[1] / "Assets/Match3Factory/Tests/Fixtures/ultragem_seed_712_draft.json"
        return leveldraft.loads_strict(fixture.read_text(encoding="utf-8"))

    def test_real_seed712_fixture_is_factual_and_reference_only(self):
        draft = self.get_draft()
        preview = extract_reference_features(draft)
        self.assertEqual(preview["cellCount"], 64)
        self.assertEqual(preview["activeCellCount"], 64)
        self.assertEqual(preview["lockedCellCount"], 32)
        self.assertEqual(sum(preview["specialKinds"].values()), 32)
        self.assertEqual(preview["lockDurabilityTotal"], 64)
        self.assertEqual(preview["observedDonorColorKinds"], 3)
        self.assertEqual(preview["moveBudget"], 18)
        self.assertEqual(preview["goals"][0]["targetId"], "ultragem.goal.score")
        self.assertEqual(preview["goals"][0]["targetCount"], 10908)
        self.assertEqual(preview["goalPressureReferenceOnly"][0]["targetCountPerBudgetMove"], 606)
        self.assertTrue(preview["notDifficultyOrSolvability"])
        self.assertEqual(preview["engineStatus"], "BLOCKED_ENG_M24")
        self.assertNotIn("difficulty", preview)
        self.assertEqual(preview["draftSha256"], leveldraft.sha256(draft))

    def test_holes_obstacle_health_and_budgets_not_confused_with_difficulty(self):
        draft = self.get_draft()
        with_hole = copy.deepcopy(draft)
        c = with_hole["cells"][0]
        c["active"], c["contentId"] = False, None
        with_hole["activeMask"][0] = False
        a = extract_reference_features(draft)
        b = extract_reference_features(with_hole)
        self.assertEqual(b["activeCellCount"], a["activeCellCount"] - 1)
        self.assertEqual(b["holeCount"], a["holeCount"] + 1)
        with_move = copy.deepcopy(draft)
        with_move["moveBudget"] = 36
        x = extract_reference_features(with_move)
        self.assertEqual(x["goalPressureReferenceOnly"][0]["targetCountPerBudgetMove"], 303)
        self.assertTrue(x["notDifficultyOrSolvability"])

    def test_invalid_or_fake_engine_certified_draft_fails_closed(self):
        draft = self.get_draft()
        draft["validationStatus"] = "ENGINE_CERTIFIED"
        with self.assertRaises(leveldraft.DraftError):
            extract_reference_features(draft)


if __name__ == "__main__":
    unittest.main()
