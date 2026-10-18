"""Fail-closed review state machine cannot publish a generated level."""
from __future__ import annotations
import copy
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from candidate_review import new_review_ticket, decide_reference_ticket, verify_review_ticket


class CandidateReviewTests(unittest.TestCase):
    def ticket(self):
        return new_review_ticket(candidate_sha256="a"*64, source_sha256="b"*64, generator_seed=712)

    def test_review_acceptance_is_not_game_publish_authorization(self):
        t = self.ticket()
        self.assertEqual(t["status"], "REVIEW_REQUIRED")
        self.assertTrue(verify_review_ticket(t))
        after = decide_reference_ticket(t, approved=True, reviewer_reference="Owner/Drive-REF01",
                 rationale="Visually acceptable reference fixture, but no official Engine parity.",
                 expected_candidate_sha256="a"*64)
        self.assertEqual(after["status"], "APPROVED_FOR_REFERENCE_TESTS")
        self.assertFalse(after["releaseAuthorized"])
        self.assertEqual(after["engineStatus"], "BLOCKED_ENG_M24")
        self.assertEqual(t["status"], "REVIEW_REQUIRED")
        self.assertNotEqual(t["recordSha256"], after["recordSha256"])
        with self.assertRaises(ValueError):
            decide_reference_ticket(after, approved=True, reviewer_reference="Owner/Drive-REF01",
                 rationale="A second decision must be rejected to preserve the audit history.",
                 expected_candidate_sha256="a"*64)

    def test_rejection_and_tampering_cannot_become_publish(self):
        t = self.ticket()
        r = decide_reference_ticket(t, approved=False, reviewer_reference="Owner/Drive-REF01",
                 rationale="Different gameplay style requested. Candidate is not accepted.",
                 expected_candidate_sha256="a"*64)
        self.assertEqual(r["status"], "REJECTED")
        for key,value in (("releaseAuthorized", True), ("engineStatus", "ENGINE_CERTIFIED"),
                          ("status", "PUBLISHED"), ("candidateSha256", "c"*64)):
            q=copy.deepcopy(r); q[key]=value
            self.assertFalse(verify_review_ticket(q))

    def test_stale_candidate_or_fake_reviewer_fails_closed(self):
        t = self.ticket()
        with self.assertRaises(ValueError):
            decide_reference_ticket(t, approved=True, reviewer_reference="Owner/Drive-REF01",
                 rationale="Suitable only for reference use, not a production result.",
                 expected_candidate_sha256="f"*64)
        with self.assertRaises(ValueError):
            decide_reference_ticket(t, approved=True, reviewer_reference="",
                 rationale="Suitable only for reference use, not a production result.",
                 expected_candidate_sha256="a"*64)


if __name__ == "__main__":
    unittest.main()
