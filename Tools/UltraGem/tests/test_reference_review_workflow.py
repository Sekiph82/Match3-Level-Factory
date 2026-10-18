"""Real seed-712 integrated reference-only review and fail-closed tests."""
from __future__ import annotations
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import leveldraft
from profile_compatibility import diagnose_profile_compatibility
from reference_review_workflow import build_reference_review_dossier
from candidate_ranking import rank_reference_candidates
from candidate_review import verify_review_ticket


def fixture():
    path = ROOT.parents[1] / "Assets/Match3Factory/Tests/Fixtures/ultragem_seed_712_draft.json"
    return leveldraft.loads_strict(path.read_text(encoding="utf-8"))


def entry(draft, *, ranked=True):
    return {
        "draft": draft, "draftSha256": leveldraft.sha256(draft),
        "rankingStatus": "RANKED_REFERENCE_HEURISTIC" if ranked else "NOT_RANKED_BY_PINNED_HEURISTIC",
        "difficultyHypothesis": .3 if ranked else None,
        "profileCompatibility": diagnose_profile_compatibility(draft),
    }


def batch(*entries):
    return {
        "resultStatus": "REFERENCE_ONLY_UNVERIFIED",
        "engineStatus": "BLOCKED_ENG_M24",
        "sourceRevision": "0e64a5bc66a5fce4b899bf0734c9cc7417b4ed12",
        "configuration": {"gameProfileId": "Coral_Rescue", "seed": 712},
        "drafts": list(entries), "rejectedCandidates": [], "seed": 712,
    }


class ReferenceReviewWorkflowTests(unittest.TestCase):
    def test_real_seed712_dossier_integrity_and_determinism(self):
        src=batch(entry(fixture()))
        snapshot=copy.deepcopy(src)
        result=build_reference_review_dossier(src)
        self.assertEqual(src, snapshot)
        self.assertEqual(result, build_reference_review_dossier(src))
        self.assertEqual(result["candidateCount"], 1)
        self.assertFalse(result["releaseAuthorized"])
        self.assertEqual(result["engineStatus"], "BLOCKED_ENG_M24")
        self.assertFalse(result["productionDifficultyValidated"])
        self.assertEqual(result["engineBotPersonasEvaluated"], [])
        one=result["ownerReviewQueue"][0]
        self.assertEqual(one["profileStatus"], "REJECTED_BY_BUILDER_POLICY")
        self.assertFalse(one["productionReady"])
        self.assertTrue(verify_review_ticket(one["reviewTicket"]))
        self.assertEqual(one["draftSha256"], "fffe76265e590a787b3e1284a2960b378c88df3f0f5260f3d10faf639d5c794d")

    def test_real_local_acceptance_status_is_recognized(self):
        original=fixture()
        accepted=copy.deepcopy(original)
        for cell in accepted["cells"]:
            if cell["active"]:
                cell["locked"]=False
                cell["lockDurability"]=0
                cell["specialId"]=None
                cell["contentId"]="ultragem.color.1"
        accepted["goals"]=[{"goalId":"goal.primary","targetId":"sample.score","targetCount":321}]
        leveldraft.validate(accepted)
        allowed=entry(accepted)
        self.assertEqual(allowed["profileCompatibility"]["localPolicyStatus"], "ACCEPTED_FOR_LOCAL_AUTHORING_ONLY")
        candidates=batch(entry(original),allowed)
        ordered=rank_reference_candidates(candidates)["orderedForHumanReview"]
        self.assertEqual(ordered[0]["draftSha256"], allowed["draftSha256"])
        self.assertEqual(build_reference_review_dossier(candidates)["ownerReviewQueue"][0]["profileStatus"], "ACCEPTED_FOR_LOCAL_AUTHORING_ONLY")

    def test_forged_local_capabilities_fail(self):
        bad=entry(fixture())
        bad["profileCompatibility"]["localPolicyStatus"]="ACCEPTED_FOR_LOCAL_AUTHORING_ONLY"
        with self.assertRaisesRegex(ValueError, "forged"):
            build_reference_review_dossier(batch(bad))

    def test_duplicate_canonical_sha_does_not_pass(self):
        same=entry(fixture())
        with self.assertRaisesRegex(ValueError, "duplicate"):
            build_reference_review_dossier(batch(same,same))

    def test_structure_dedupe_does_not_approve(self):
        original=fixture()
        similar=copy.deepcopy(original)
        similar["seed"]+=2
        similar["levelId"]="relabel2"
        result=build_reference_review_dossier(batch(entry(original),entry(similar)),threshold=1.0)
        self.assertEqual(len(result["deduplication"]["accepted"]),1)
        self.assertEqual(len(result["deduplication"]["rejected"]),1)
        self.assertEqual(len(result["ownerReviewQueue"]),2)
        self.assertTrue(all(x["reviewTicket"]["status"]=="REVIEW_REQUIRED" for x in result["ownerReviewQueue"]))

    def test_invalid_threshold_and_foreign_profile_fail(self):
        with self.assertRaises(ValueError):
            build_reference_review_dossier(batch(entry(fixture())),threshold=float("nan"))
        foreign=copy.deepcopy(fixture())
        foreign["gameProfileId"]="Dino_Islands"
        with self.assertRaisesRegex(ValueError, "foreign"):
            build_reference_review_dossier(batch(entry(foreign)))

    def test_corrupted_digest_and_false_engine_pass_rejected(self):
        candidate=entry(fixture())
        candidate["draftSha256"]="0"*64
        with self.assertRaises(ValueError):
            build_reference_review_dossier(batch(candidate))
        src=batch(entry(fixture()))
        src["engineStatus"]="PASS"
        with self.assertRaises(ValueError):
            build_reference_review_dossier(src)


if __name__=="__main__":
    unittest.main()
