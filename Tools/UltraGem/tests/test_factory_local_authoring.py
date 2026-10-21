from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import candidate_diversity
import factory_local_authoring as authoring
import leveldraft
from profile_compatibility import PROFILE_IDS, diagnose_profile_compatibility


class FactoryLocalAuthoringTests(unittest.TestCase):
    def test_five_profiles_produce_distinct_local_compatible_drafts(self):
        drafts = [authoring.create_draft(profile, 330000) for profile in PROFILE_IDS]
        self.assertEqual(len({d["gameProfileId"] for d in drafts}), 5)
        self.assertEqual(len({candidate_diversity.structural_fingerprint(d) for d in drafts}), 5)
        for draft in drafts:
            self.assertEqual(diagnose_profile_compatibility(draft)["localPolicyStatus"], "ACCEPTED_FOR_LOCAL_AUTHORING_ONLY")
            self.assertEqual(draft["sourceKind"], authoring.SOURCE_KIND)
            self.assertEqual(draft["goals"], [{"goalId": "goal.primary", "targetId": "sample.score", "targetCount": 500}])

    def test_seed_repeat_is_byte_deterministic_and_seed_only_is_structurally_different(self):
        first = authoring.create_draft(PROFILE_IDS[0], 17)
        repeat = authoring.create_draft(PROFILE_IDS[0], 17)
        other = authoring.create_draft(PROFILE_IDS[0], 18)
        self.assertEqual(leveldraft.dumps_canonical(first), leveldraft.dumps_canonical(repeat))
        self.assertNotEqual(leveldraft.sha256(first), leveldraft.sha256(other))
        self.assertNotEqual(candidate_diversity.structural_fingerprint(first), candidate_diversity.structural_fingerprint(other))

    def test_strict_roundtrip_palette_and_sample_adapter_constraints(self):
        draft = authoring.create_draft(PROFILE_IDS[2], 2026)
        parsed = leveldraft.loads_strict(leveldraft.dumps_canonical(draft))
        self.assertEqual(draft, parsed)
        self.assertTrue(all(c["active"] and not c["locked"] and c["specialId"] is None and c["obstacleId"] is None for c in draft["cells"]))
        self.assertLessEqual({c["contentId"] for c in draft["cells"]}, set(authoring.PALETTE))
        board = [[draft["cells"][r * draft["width"] + c]["contentId"] for c in range(draft["width"])]
                 for r in range(draft["height"])]
        self.assertFalse(any(board[r][c] == board[r][c+1] == board[r][c+2]
                             for r in range(draft["height"]) for c in range(draft["width"] - 2)))
        self.assertFalse(any(board[r][c] == board[r+1][c] == board[r+2][c]
                             for r in range(draft["height"] - 2) for c in range(draft["width"])))

    def test_invalid_profile_dimensions_palette_and_batch_bound_fail_closed(self):
        for args in (("unknown", 1), (PROFILE_IDS[0], -1)):
            with self.assertRaises(ValueError):
                authoring.create_draft(*args)
        for kwargs in ({"width": 5}, {"height": 13}, {"colors": 2}, {"colors": 7}):
            with self.assertRaises(ValueError):
                authoring.create_draft(PROFILE_IDS[0], 1, **kwargs)
        with self.assertRaises(ValueError):
            authoring.build_batch(list(PROFILE_IDS), attempts_per_profile=11, seed_start=1)

    def test_small_batch_has_separate_counts_and_engine_never_qualifies(self):
        result = authoring.build_batch(list(PROFILE_IDS), attempts_per_profile=3, seed_start=700)
        self.assertEqual(result["generationAttempts"], 15)
        self.assertEqual(result["localDraftCount"], 15)
        self.assertEqual(result["engineQualifiedCampaignLevels"], 0)
        self.assertEqual(result["engineStatus"], "BLOCKED_ENG_M24")
        self.assertTrue(all(v["attempts"] == 3 for v in result["profileResults"].values()))
        self.assertTrue(all(not r["ownerApproved"] for r in result["records"]))

    def test_write_batch_hash_manifest_and_no_overwrite(self):
        result = authoring.build_batch([PROFILE_IDS[0]], attempts_per_profile=2, seed_start=88)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "local-run"
            summary = authoring.write_batch(out, result)
            manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(len(manifest["entries"]), 2)
            for entry in manifest["entries"]:
                raw = (out / entry["path"]).read_bytes()
                self.assertLess(len(raw), 2_000_000)
                self.assertEqual(hashlib.sha256(raw).hexdigest(), entry["sha256"])
                parsed = leveldraft.loads_strict(raw.decode("utf-8"))
                self.assertEqual(leveldraft.sha256(parsed), entry["draftSha256"])
            self.assertEqual(summary["engineQualifiedCampaignLevels"], 0)
            with self.assertRaises(FileExistsError):
                authoring.write_batch(out, result)

    def test_goals_and_engine_independence(self):
        draft = authoring.create_draft(PROFILE_IDS[4], 31)
        self.assertTrue(all(not c["locked"] and c["specialId"] is None and c["obstacleId"] is None for c in draft["cells"]))
        self.assertIsNone(draft["engineSchemaVersion"])
        self.assertEqual(draft["validationStatus"], "PROTOTYPE_ONLY")
        self.assertEqual(diagnose_profile_compatibility(draft)["engineStatus"], "BLOCKED_ENG_M24")

    def test_maximum_board_and_batch_budgets_are_bounded(self):
        draft = authoring.create_draft(PROFILE_IDS[0], 99, width=12, height=12, colors=6)
        self.assertEqual(len(draft["cells"]), 144)
        self.assertLess(len(leveldraft.dumps_canonical(draft).encode("utf-8")), 100_000)
        batch = authoring.build_batch(list(PROFILE_IDS), attempts_per_profile=10, seed_start=1000)
        self.assertEqual(batch["generationAttempts"], authoring.MAX_BATCH)
        self.assertLessEqual(batch["generationAttempts"], 50)


if __name__ == "__main__":
    unittest.main()
