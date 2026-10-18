"""LFX-M06-008 source-based deterministic human triage tests."""
from __future__ import annotations
import copy
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import leveldraft
from candidate_ranking import rank_reference_candidates


class CandidateRankingTests(unittest.TestCase):
    def fixture(self):
        p=ROOT.parents[1]/"Assets/Match3Factory/Tests/Fixtures/ultragem_seed_712_draft.json"
        return leveldraft.loads_strict(p.read_text(encoding="utf-8"))

    def entry(self, draft, *, status="RANKED_REFERENCE_HEURISTIC", policy="REJECTED_BY_BUILDER_POLICY"):
        return {
            "draft": draft, "draftSha256": leveldraft.sha256(draft),
            "rankingStatus": status, "difficultyHypothesis": 0.3 if status.startswith("RANKED") else None,
            "profileCompatibility": {"engineStatus": "BLOCKED_ENG_M24",
                                     "localPolicyStatus": policy,
                                     "draftMutationPerformed": False},
        }

    def test_real_seed712_is_quarantined_with_explainable_review_order(self):
        source=self.fixture()
        alternate=copy.deepcopy(source)
        alternate["levelId"]="candidate.second"
        alternate["seed"]=713
        data={"resultStatus":"REFERENCE_ONLY_UNVERIFIED","engineStatus":"BLOCKED_ENG_M24",
              "drafts":[self.entry(source), self.entry(alternate, status="NOT_RANKED_BY_PINNED_HEURISTIC")]}
        saved=copy.deepcopy(data)
        report=rank_reference_candidates(data)
        self.assertEqual(data,saved)
        self.assertEqual(report["candidateCount"],2)
        self.assertEqual(report["orderedForHumanReview"][0]["originalIndex"],0)
        self.assertIn("REJECTED_BY_LOCAL_PROFILE_POLICY",report["orderedForHumanReview"][0]["reviewReasons"])
        self.assertIsNone(report["orderedForHumanReview"][0]["productionDifficulty"])
        self.assertIsNone(report["orderedForHumanReview"][0]["productionSolvable"])
        self.assertFalse(report["rankingIsGameplayDifficulty"])
        self.assertFalse(report["releaseAuthorized"])
        self.assertEqual(report,rank_reference_candidates(data))

    def test_wrong_hash_duplicate_and_fabricated_engine_status_fail_closed(self):
        source=self.fixture()
        r=self.entry(source)
        base={"resultStatus":"REFERENCE_ONLY_UNVERIFIED","engineStatus":"BLOCKED_ENG_M24","drafts":[r]}
        for mutation in ("bad_sha","fake_engine","duplicate","fake_policy","nan"):
            p=copy.deepcopy(base)
            if mutation=="bad_sha": p["drafts"][0]["draftSha256"]="0"*64
            if mutation=="fake_engine": p["engineStatus"]="ENGINE_CERTIFIED"
            if mutation=="duplicate": p["drafts"].append(copy.deepcopy(p["drafts"][0]))
            if mutation=="fake_policy": p["drafts"][0]["profileCompatibility"]["localPolicyStatus"]="PASSED"
            if mutation=="nan": p["drafts"][0]["difficultyHypothesis"]=float("nan")
            with self.subTest(case=mutation),self.assertRaises(ValueError):
                rank_reference_candidates(p)


if __name__=="__main__":
    unittest.main()
