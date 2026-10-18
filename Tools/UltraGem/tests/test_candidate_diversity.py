"""No Engine/production assertion: structural prototype triage only."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import candidate_diversity
import leveldraft


def fixture():
    file = ROOT.parents[1] / "Assets/Match3Factory/Tests/Fixtures/ultragem_seed_712_draft.json"
    return leveldraft.loads_strict(file.read_text(encoding="utf-8"))


class CandidateDiversityTests(unittest.TestCase):
    def test_same_source_and_renamed_colors_have_identical_structure(self):
        source = fixture()
        colors = copy.deepcopy(source)
        mapping = {"ultragem.color.1": "ultragem.color.3",
                   "ultragem.color.2": "ultragem.color.1",
                   "ultragem.color.3": "ultragem.color.2"}
        for cell in colors["cells"]:
            if cell["contentId"] in mapping:
                cell["contentId"] = mapping[cell["contentId"]]
        colors["gameProfileId"] = "Garage_Legends"
        colors["seed"] = 713
        colors["levelId"] = "different.level"
        a = candidate_diversity.structural_fingerprint(source)
        self.assertEqual(a, candidate_diversity.structural_fingerprint(colors))
        report = candidate_diversity.compare_drafts(source, colors)
        self.assertEqual(report["similarity"], 1.0)
        self.assertFalse(report["sameProfile"])
        self.assertEqual(report["reason"], "EXACT_STRUCTURAL_DUPLICATE")
        self.assertNotEqual(leveldraft.sha256(source), leveldraft.sha256(colors))

    def test_goals_obstacles_locks_and_holes_cannot_hide_in_color_rename(self):
        original = fixture()
        variants = []
        different_goal = copy.deepcopy(original)
        different_goal["goals"][0]["targetCount"] += 1
        variants.append(different_goal)
        different_lock = copy.deepcopy(original)
        different_lock["cells"][2]["lockDurability"] -= 1
        variants.append(different_lock)
        different_obstacle = copy.deepcopy(original)
        different_obstacle["cells"][2]["obstacleId"] = "sample.glass"
        different_obstacle["cells"][2]["obstacleDurability"] = 1
        variants.append(different_obstacle)
        hole = copy.deepcopy(original)
        cell = hole["cells"][0]
        cell["active"], cell["contentId"] = False, None
        hole["activeMask"][0] = False
        variants.append(hole)
        for changed in variants:
            with self.subTest(change=variants.index(changed)):
                self.assertNotEqual(candidate_diversity.structural_fingerprint(original),
                                    candidate_diversity.structural_fingerprint(changed))
                self.assertLess(candidate_diversity.compare_drafts(original, changed)["similarity"], 1.0)

    def test_different_geometry_is_not_near_duplicate(self):
        a = fixture()
        b = copy.deepcopy(a)
        b["cells"] = [cell for cell in b["cells"] if cell["row"] < 7]
        b["activeMask"] = b["activeMask"][:56]
        b["height"] = 7
        self.assertEqual(candidate_diversity.compare_drafts(a, b)["reason"], "GEOMETRY_MISMATCH")
        self.assertEqual(candidate_diversity.compare_drafts(a, b)["similarity"], 0.0)

    def test_catalog_is_bounded_deterministic_and_never_publishes(self):
        a = fixture()
        b = copy.deepcopy(a); b["seed"] += 1; b["levelId"] = "different.id"
        c = copy.deepcopy(a); c["goals"][0]["targetCount"] += 1
        first = candidate_diversity.screen_catalog([("A", a), ("B", b), ("C", c)], threshold=0.95)
        again = candidate_diversity.screen_catalog([("A", a), ("B", b), ("C", c)], threshold=0.95)
        self.assertEqual(first, again)
        self.assertEqual([x["candidateId"] for x in first["accepted"]], ["A", "C"])
        self.assertEqual(first["rejected"][0]["duplicateOf"], "A")
        self.assertFalse(first["releaseAuthorized"])
        self.assertEqual(first["engineStatus"], "BLOCKED_ENG_M24")
        self.assertEqual(a["seed"], 712)
        for bad in (0, -1, 1.01, float("nan"), float("inf"), True):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    candidate_diversity.screen_catalog([], threshold=bad)
        with self.assertRaises(ValueError):
            candidate_diversity.screen_catalog([("A", a), ("A", a)])
        with self.assertRaises(ValueError):
            candidate_diversity.screen_catalog([("N"+str(i), a) for i in range(513)])

    def test_invalid_draft_fails_closed(self):
        a = fixture()
        a["engineSchemaVersion"] = "fabricated"
        with self.assertRaises(leveldraft.DraftError):
            candidate_diversity.structural_fingerprint(a)
        with self.assertRaises(leveldraft.DraftError):
            candidate_diversity.screen_catalog([("invalid", a)])


if __name__ == "__main__":
    unittest.main()
