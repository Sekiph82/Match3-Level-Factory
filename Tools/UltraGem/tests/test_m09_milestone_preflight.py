"""Whole M09 offline release milestone preflight regression tests."""
from __future__ import annotations
import copy
import hashlib
import io
import json
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import leveldraft
from m09_milestone_preflight import preflight_m09_milestone, TASK_IDS
from preview_pack import build_preview_pack
from theme_contract import PROFILES

class M09MilestonePreflightTests(unittest.TestCase):
    def sample(self, count=5):
        path = ROOT.parents[1] / "Assets/Match3Factory/Tests/Fixtures/ultragem_seed_712_draft.json"
        base = leveldraft.loads_strict(path.read_text(encoding="utf-8"))
        drafts = []
        for i, profile in enumerate(PROFILES[:count]):
            draft = copy.deepcopy(base)
            draft["gameProfileId"] = profile
            draft["levelId"] = "preview.m09." + str(i)
            drafts.append(draft)
        return build_preview_pack(drafts)

    def test_milestone_all_ten_items_five_titles_three_platforms(self):
        batch = self.sample()
        original = copy.deepcopy(batch)
        result = preflight_m09_milestone(proposed=batch, git_commit_sha="a" * 40,
                                        locales=["en", "tr"])
        self.assertEqual(original, batch)
        self.assertEqual(set(result["taskEvidenceMatrix"]), set(TASK_IDS))
        self.assertEqual(len(result["platformPlans"]), 15)
        self.assertEqual(len(result["relativeR2PathProposalsNotUploadKeys"]), 15)
        self.assertFalse(result["publishAuthorized"])
        self.assertFalse(result["officialMilestonePass"])
        self.assertFalse(result["engineCapabilityBoundsVerified"])
        self.assertEqual(result["engineStatus"], "BLOCKED_ENG_M24")
        self.assertEqual(result, preflight_m09_milestone(
            proposed=batch, git_commit_sha="a" * 40, locales=["en", "tr"]))

    def test_cross_release_diff_and_rollback_stay_offline(self):
        old = self.sample(1)
        proposed = self.sample(2)
        result = preflight_m09_milestone(proposed=proposed, previous=old,
            git_commit_sha="b" * 40, locales=["en"],
            previous_release_reference="Review/not-yet-accepted")
        self.assertEqual(len(result["previewDiff"]["created"]), 1)
        self.assertFalse(result["rollbackProposal"]["atomicPointerSwitchAuthorized"])
        self.assertFalse(result["rollbackProposal"]["previousAcceptanceIndependentlyVerified"])
        self.assertFalse(result["distributedLockVerified"])
        self.assertFalse(result["atomicChannelPointerSwitched"])

    def test_version_publication_and_engine_forgery_rejected(self):
        for field, value in (("channel", "production"), ("signed", True),
                             ("publishAuthorized", True),
                             ("engineStatus", "ACCEPTED"), ("schemaVersion", 2)):
            fake = self.sample(1)
            fake[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                preflight_m09_milestone(proposed=fake, git_commit_sha="d" * 40,
                                       locales=["en"])
        fake = self.sample(1)
        fake["ownerAccepted"] = True
        with self.assertRaises(ValueError):
            preflight_m09_milestone(proposed=fake, git_commit_sha="d" * 40,
                                   locales=["en"])

    def test_invalid_seed_context_or_locale_rejected(self):
        batch = self.sample(1)
        for sha in ("short", "G" * 40):
            with self.assertRaises(ValueError):
                preflight_m09_milestone(proposed=batch, git_commit_sha=sha,
                                       locales=["en"])
        for locales in ([], ["tr", "tr"], ["../en"]):
            with self.assertRaises(ValueError):
                preflight_m09_milestone(proposed=batch, git_commit_sha="a" * 40,
                                       locales=locales)

if __name__ == "__main__":
    unittest.main()
