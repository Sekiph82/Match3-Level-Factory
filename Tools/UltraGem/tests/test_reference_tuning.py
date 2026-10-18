from __future__ import annotations
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference_tuning import annotate_reference_tuning, verify_annotation


class ReferenceTuningTests(unittest.TestCase):
    def record(self):
        return annotate_reference_tuning(
            draft_sha256="f"*64,
            original_hypothesis="UNRATED", requested_label="HARD",
            rationale="Reference cohort looks too easy; please review against Engine later.",
            reviewer_reference="Drive/auditor-owner-001",
        )

    def test_annotates_without_mutating_source_or_certifying(self):
        record = self.record()
        self.assertEqual(record, self.record())
        self.assertTrue(verify_annotation(record, expected_draft_sha256="f"*64))
        self.assertFalse(verify_annotation(record, expected_draft_sha256="e"*64))
        self.assertFalse(record["releaseAuthorized"])
        self.assertEqual(record["resultStatus"], "REFERENCE_TUNING_ANNOTATION_ONLY")
        self.assertEqual(record["engineStatus"], "BLOCKED_ENG_M24")

    def test_hidden_mutation_forged_approval_and_short_reason_are_rejected(self):
        record = self.record()
        for key, value in (("requestedLabel", "CERTIFIED"), ("releaseAuthorized", True),
                           ("rationale", "x"), ("annotationSha256", "000"*21+"0")):
            edited = copy.deepcopy(record)
            edited[key] = value
            self.assertFalse(verify_annotation(edited, expected_draft_sha256="f"*64))
        with self.assertRaises(ValueError):
            annotate_reference_tuning(draft_sha256="broken", original_hypothesis="UNRATED",
                                      requested_label="HARD", rationale="A sufficiently detailed explanation.",
                                      reviewer_reference="Drive/auditor-001")


if __name__ == "__main__":
    unittest.main()
