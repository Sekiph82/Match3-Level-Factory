"""LFX-M11 all-ten-task offline source qualification tests, not Engine tests."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import leveldraft
from m11_milestone_qualification import qualify_m11_milestone
from theme_contract import PROFILES


class M11MilestoneQualificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT.parents[1] / "Assets/Match3Factory/Tests/Fixtures/ultragem_seed_712_draft.json"
        cls.base = leveldraft.loads_strict(path.read_text(encoding="utf-8"))

    def draft(self, game, ordinal):
        record = copy.deepcopy(self.base)
        record["gameProfileId"] = game
        record["levelId"] = "reference.m11." + str(ordinal)
        record["seed"] = 712 + ordinal
        return record

    def qualify(self, drafts, **kwargs):
        return qualify_m11_milestone(
            drafts=drafts, source_git_sha="a" * 40, **kwargs)

    def test_one_milestone_receipt_covers_all_ten_m11_tasks_five_title_schema(self):
        inputs = [self.draft(profile, i) for i, profile in enumerate(PROFILES)]
        original = copy.deepcopy(inputs)
        report = self.qualify(inputs)
        self.assertEqual(inputs, original)
        self.assertEqual(set(report["taskEvidenceMatrix"]),
                         {f"LFX-M11-{i:03d}" for i in range(1, 11)})
        self.assertEqual(report["canonicalJsonRoundtripCount"], 5)
        self.assertEqual(len(report["profiles"]), 5)
        self.assertEqual(report["sourceLevelDraftCount"], 5)
        self.assertTrue(all(x["receivedDrafts"] == 1 for x in report["profiles"]))
        self.assertTrue(all(x["referencePackManifestSha256"] for x in report["profiles"]))
        self.assertFalse(report["allFiveHundredInputDraftsSupplied"])
        self.assertFalse(report["allFiveHundredDistinctGameContentStructuresSupplied"])
        self.assertFalse(report["match3EngineSimulationExecuted"])
        self.assertFalse(report["fiveIndependentBotsExecuted"])
        self.assertFalse(report["realWinOrGoalsProved"])
        self.assertFalse(report["releaseTagOrPackageCreated"])
        self.assertFalse(report["publishAuthorized"])
        self.assertFalse(report["officialMilestonePass"])
        self.assertEqual(report, self.qualify(list(reversed(inputs))))

    def test_bulk_five_times_one_hundred_does_not_manufacture_engine_proof(self):
        # 500 valid prototype drafts, but reusing one underlying board per
        # game with 100 different IDs/seeds. Counts must not certify variety.
        inputs = [self.draft(game, i)
                  for game in PROFILES for i in range(100)]
        out = self.qualify(inputs)
        self.assertEqual(out["sourceLevelDraftCount"], 500)
        self.assertEqual(out["canonicalJsonRoundtripCount"], 500)
        self.assertTrue(out["allFiveHundredInputDraftsSupplied"])
        self.assertFalse(out["allFiveHundredDistinctGameContentStructuresSupplied"])
        self.assertTrue(all(p["distinctCanonicalDraftHashes"] == 100
                            for p in out["profiles"]))
        self.assertTrue(all(p["distinctGameContentFingerprintsNotDifficulty"] == 1
                            for p in out["profiles"]))
        self.assertTrue(all(not p["hundredDistinctGameplayStructuresSupplied"]
                            for p in out["profiles"]))
        self.assertFalse(out["authoritativeReplayObserved"])
        self.assertFalse(out["realWinOrGoalsProved"])

    def test_duplicate_level_identity_and_overcapacity_rejected(self):
        item = self.draft("Coral_Rescue", 0)
        with self.assertRaises(ValueError):
            self.qualify([item, copy.deepcopy(item)])
        with self.assertRaises(ValueError):
            self.qualify([])
        with self.assertRaises(ValueError):
            self.qualify([copy.deepcopy(item)] * 501)
        with self.assertRaises(ValueError):
            self.qualify([self.draft("Coral_Rescue", i) for i in range(101)])

    def test_fake_engine_release_and_schema_claims_do_not_roundtrip(self):
        for field, value in (
                ("releaseChannel", "production"),
                ("engineSchemaVersion", "1.0"),
                ("validationStatus", "ENGINE_CERTIFIED"),
                ("minEngineVersion", "2027.0"),
                ("gameProfileId", "unknown_profile")):
            bad = self.draft("Coral_Rescue", 0)
            bad[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.qualify([bad])
        bad = self.draft("Coral_Rescue", 0)
        bad["runtimeWon"] = True
        with self.assertRaises(ValueError):
            self.qualify([bad])

    def test_unknown_or_mutated_nested_leveldraft_cannot_create_hash_evidence(self):
        invalid = self.draft("Wonder_Pop", 0)
        invalid["cells"][0]["illegalCodeField"] = "inject"
        with self.assertRaises(ValueError):
            self.qualify([invalid])
        bad = self.draft("Wonder_Pop", 1)
        bad["cells"][0]["contentId"] = None
        bad["cells"][0]["obstacleId"] = None
        with self.assertRaises(ValueError):
            self.qualify([bad])

    def test_malformed_commit_locales_and_review_claim_rejected(self):
        item = [self.draft("Coral_Rescue", 1)]
        for sha in ("bad", "G" * 40, "A" * 40):
            with self.assertRaises(ValueError):
                qualify_m11_milestone(drafts=item, source_git_sha=sha)
        for languages in ([], ["tr", "tr"], ["../tr"], ["english"]):
            with self.subTest(languages=languages), self.assertRaises(ValueError):
                self.qualify(item, locale_requirements=languages)
        with self.assertRaises(ValueError):
            self.qualify(item, owner_review_reference="Review\nOWNER_APPROVED")

    def test_unverified_owner_review_never_promotes_release(self):
        outcome = self.qualify(
            [self.draft("Garage_Legends", 2)],
            owner_review_reference="owner-review/pending")
        self.assertEqual(outcome["ownerReviewReferenceUnverified"],
                         "owner-review/pending")
        self.assertFalse(outcome["ownerAccepted"])
        self.assertFalse(outcome["legalApprovalVerified"])
        self.assertFalse(outcome["consumerBuildExclusionVerified"])
        self.assertFalse(outcome["officialMilestonePass"])


if __name__ == "__main__":
    unittest.main()
