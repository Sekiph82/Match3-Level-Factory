"""Catalog-wide similarity, adversarial input and owner override gates."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import leveldraft
from catalog_clusters import cluster_reference_catalog, propose_duplicate_exception


def sample():
    p=ROOT.parents[1] / "Assets/Match3Factory/Tests/Fixtures/ultragem_seed_712_draft.json"
    return leveldraft.loads_strict(p.read_text(encoding="utf-8"))


class CatalogClustersTests(unittest.TestCase):
    def test_same_structure_across_titles_is_flagged_not_removed(self):
        a=sample()
        b=copy.deepcopy(a)
        b["gameProfileId"]="Garage_Legends"
        b["seed"]+=1
        b["levelId"]="copy.two"
        report=cluster_reference_catalog([("a",a),("b",b)],threshold=1.0)
        self.assertEqual(len(report["clusters"]),1)
        self.assertEqual(len(report["clusters"][0]),2)
        self.assertTrue(report["similarPairs"][0]["crossProfile"])
        self.assertFalse(report["releaseAuthorized"])
        self.assertEqual(report["engineStatus"],"BLOCKED_ENG_M24")
        self.assertEqual(report,cluster_reference_catalog([("b",b),("a",a)],threshold=1.0))

    def test_goal_difference_does_not_make_exact_cluster(self):
        a=sample()
        b=copy.deepcopy(a)
        b["goals"][0]["targetCount"]+=1
        report=cluster_reference_catalog([("a",a),("b",b)],threshold=.95)
        self.assertEqual(len(report["clusters"]),2)
        self.assertEqual(report["similarPairs"],[])

    def test_override_is_unauthenticated_and_never_waives_duplicate(self):
        a=sample()
        b=copy.deepcopy(a)
        b["seed"]+=2
        b["levelId"]="other.id"
        report=cluster_reference_catalog([("first",a),("second",b)])
        receipt=propose_duplicate_exception(report,
            candidate_id="second",expected_sha256=leveldraft.sha256(b),
            owner_reference="Drive/owner-note-001",
            rationale="Only a reference exception requested, never production approval.")
        self.assertFalse(receipt["reviewerAuthenticated"])
        self.assertFalse(receipt["releaseAuthorized"])
        self.assertTrue(receipt["originalSimilarityFlagsPreserved"])
        self.assertEqual(len(report["similarPairs"]),1)
        with self.assertRaises(ValueError):
            propose_duplicate_exception(report,
                candidate_id="second",expected_sha256="f"*64,
                owner_reference="Drive/owner-note-001",
                rationale="Wrong source digest must not bypass similarity controls.")

    def test_incorrect_budget_ids_or_threshold_rejected(self):
        a=sample()
        for invalid in (0,1.1,float("nan"),True):
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):
                cluster_reference_catalog([("a",a)],threshold=invalid)
        with self.assertRaises(ValueError):
            cluster_reference_catalog([("a",a),("a",a)])
        with self.assertRaises(ValueError):
            cluster_reference_catalog([("a",a)]*65)
        with self.assertRaises(ValueError):
            cluster_reference_catalog([("../evil",a)])

    def test_fixture_source_not_mutated_by_clustering(self):
        a=sample()
        before=copy.deepcopy(a)
        _=cluster_reference_catalog([("a",a)])
        self.assertEqual(a,before)


if __name__=="__main__":
    unittest.main()
