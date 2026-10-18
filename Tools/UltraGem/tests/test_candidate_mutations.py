"""Deterministic reference mutation tests; no gameplay or Engine claims."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import leveldraft
from candidate_mutations import propose_color_mutations


class CandidateMutationTests(unittest.TestCase):
    def source(self):
        p = ROOT.parents[1] / "Assets/Match3Factory/Tests/Fixtures/ultragem_seed_712_draft.json"
        draft = leveldraft.loads_strict(p.read_text(encoding="utf-8"))
        # The real donor result's fixed center is special+locked, and its
        # border is random spawners. Build an editable neutral color-pair
        # subset without changing the test's original fixture.
        draft["cells"][0]["contentId"] = "ultragem.color.1"
        draft["cells"][1]["contentId"] = "ultragem.color.2"
        draft["cells"][6]["contentId"] = "ultragem.color.3"
        leveldraft.validate(draft)
        return draft

    def test_three_controlled_variants_deterministic_preserving_locked_and_special(self):
        draft = self.source()
        before = copy.deepcopy(draft)
        sha = leveldraft.sha256(draft)
        options = dict(expected_source_sha256=sha, approval_reference="owner-reviewed-fixture-A", seed=712, count=3)
        one = propose_color_mutations(draft, **options)
        two = propose_color_mutations(draft, **options)
        self.assertEqual(one, two)
        self.assertEqual(draft, before)
        self.assertFalse(one["releaseAuthorized"])
        self.assertEqual(one["resultStatus"], "REFERENCE_MUTATION_ONLY")
        self.assertEqual(one["engineStatus"], "BLOCKED_ENG_M24")
        self.assertGreaterEqual(len(one["generated"]), 1)
        fingerprints = set()
        for item in one["generated"]:
            self.assertNotIn(item["draftSha256"], fingerprints)
            fingerprints.add(item["draftSha256"])
            candidate = item["draft"]
            self.assertEqual(item["draftSha256"], leveldraft.sha256(candidate))
            self.assertEqual(candidate["goals"], draft["goals"])
            self.assertEqual(candidate["activeMask"], draft["activeMask"])
            self.assertEqual(candidate["cells"][2], draft["cells"][2])
            self.assertEqual(candidate["validationStatus"], "PROTOTYPE_ONLY")
            self.assertEqual(candidate["releaseChannel"], "local")

    def test_mismatched_source_missing_receipt_or_unbounded_request_rejected(self):
        draft = self.source()
        sha = leveldraft.sha256(draft)
        base = dict(expected_source_sha256=sha, approval_reference="owner-ref", seed=5)
        for overrides in ({"expected_source_sha256": "0" * 64},
                          {"approval_reference": ""}, {"seed": -1},
                          {"count": 0}, {"count": 9}):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                propose_color_mutations(draft, **{**base, **overrides})

    def test_without_safe_mutable_color_pairs_reports_no_candidate(self):
        draft = self.source()
        for cell in draft["cells"]:
            if not cell["locked"] and not cell["specialId"] and isinstance(cell["contentId"], str) and cell["contentId"].startswith("ultragem.color."):
                cell["contentId"] = "ultragem.spawn_random"
        leveldraft.validate(draft)
        result = propose_color_mutations(draft, expected_source_sha256=leveldraft.sha256(draft),
                                         approval_reference="owner-ref", seed=712)
        self.assertEqual(result["generated"], [])
        self.assertEqual(result["rejections"][0]["code"], "NO_MUTABLE_COLOR_PAIR")


if __name__ == "__main__":
    unittest.main()
