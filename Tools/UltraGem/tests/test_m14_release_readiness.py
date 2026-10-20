"""M14 all-twelve-task source-only cross-milestone safety checks."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import leveldraft
from age_liveops_policy import FLAGS
from m09_milestone_preflight import preflight_m09_milestone
from m10_milestone_preflight import preflight_m10_milestone
from m11_milestone_qualification import qualify_m11_milestone
from m12_milestone_preflight import preflight_m12_milestone
from m13_milestone_workbench import preflight_m13_milestone
from m14_release_readiness import assess_m14_release_readiness
from preview_pack import build_preview_pack
from theme_contract import PROFILES


class M14ReleaseReadinessTests(unittest.TestCase):
    GIT = "a" * 40

    @classmethod
    def setUpClass(cls):
        file = ROOT.parents[1] / "Assets/Match3Factory/Tests/Fixtures/ultragem_seed_712_draft.json"
        cls.draft = leveldraft.loads_strict(file.read_text(encoding="utf-8"))

    @staticmethod
    def features():
        names = ("timedMode", "endlessMode", "leaderboards", "competitions",
                 "socialInvites", "behavioralTargeting", "realAds", "realIap")
        return {p: {name: False for name in names} for p in PROFILES}

    def previous_milestones(self):
        source = copy.deepcopy(self.draft)
        pack = build_preview_pack([source])
        m09 = preflight_m09_milestone(
            proposed=pack, git_commit_sha=self.GIT, locales=["en", "tr"])
        m10 = preflight_m10_milestone(
            game_id="Coral_Rescue", channel="staging", platform="android",
            git_commit_sha=self.GIT, manifest_sha256="b" * 64,
            artifacts=[{
                "gameProfileId": "Coral_Rescue",
                "relativePath": "levels/preview.json", "kind": "level",
                "body": b'{"referenceOnly":true}', "rightsStatus": "REFERENCE_ONLY",
            }])
        m11 = qualify_m11_milestone(
            drafts=[source], source_git_sha=self.GIT)
        policies = {}
        for game in PROFILES:
            policies[game] = {
                "flags": {flag: False for flag in FLAGS},
                "caps": {
                    "adsPerSession": 0, "earnedPacksPerDay": 2,
                    "collectionItems": 20, "eventDurationHours": 72,
                    "streakPressureEnabled": False,
                    "forcedOfferPopups": 0, "premiumRewardCount": 0,
                    "personalizedEngagement": False,
                },
            }
        events = [{
            "profileId": game, "eventId": "weekly.sample",
            "cadence": "WEEKLY", "timezoneId": "Europe/Istanbul",
            "startLocal": "2026-10-19T09:00:00",
            "endLocal": "2026-10-20T09:00:00",
            "startFold": None, "endFold": None,
            "contentKind": "LEVEL", "contentId": "level.001",
            "claimPreviouslyRecordedByCaller": False,
        } for game in PROFILES]
        m12 = preflight_m12_milestone(
            events=events, policies=policies,
            available_content={p: ["level.001"] for p in PROFILES},
            observed_server_utc="2026-10-19T10:00:00Z",
            git_commit_sha=self.GIT, manifest_sha256="b" * 64)
        m13 = preflight_m13_milestone(
            git_commit_sha=self.GIT, store_items=[], iap_bindings=[],
            placements=[], economy_cases=[], assets=[],
            messages={p: {"ui.status": {"en": "Not available"}} for p in PROFILES},
            ui_states=[], callbacks=[])
        return {"m09": m09, "m10": m10, "m11": m11, "m12": m12, "m13": m13}

    def test_entire_m14_twelve_task_gate_never_grants_commercial_release(self):
        receipts = self.previous_milestones()
        original = copy.deepcopy(receipts)
        original["m10"]["inspectedLocalArtifacts"] = [
            dict(item) for item in original["m10"]["inspectedLocalArtifacts"]]
        report = assess_m14_release_readiness(
            **receipts, source_git_sha=self.GIT, optional_features=self.features())
        self.assertEqual(receipts, original)
        self.assertEqual(len(report["taskEvidenceMatrix"]), 12)
        self.assertEqual(set(report["taskEvidenceMatrix"]),
                         {f"LFX-M14-{i:03d}" for i in range(1, 13)})
        self.assertEqual(report["resultStatus"],
                         "M14_OFFLINE_RELEASE_READINESS_GAP_REPORT_ONLY")
        self.assertEqual(len(report["upstreamPreviewContracts"]), 5)
        self.assertEqual(len(report["explicitlyDisabledFutureFeatures"]), 5)
        self.assertEqual(len(report["prototypeInputsByGameNotCampaign"]), 5)
        self.assertEqual(report["realCampaignLevelsEngineQualified"], 0)
        for key in ("runtimeWinOrSolverParityVerified", "productionBuildContentsInspected",
                    "productionSecretsAuditPerformed", "realOTAOrOfflineReplayPerformed",
                    "consumerAgeStorePoliciesIndependentlyApproved",
                    "signedReleaseManifestProduced", "immutableV1SourceTagCreated",
                    "productionAuthorized", "officialMilestonePass", "ownerAccepted"):
            self.assertIs(report[key], False, key)
        self.assertEqual(report, assess_m14_release_readiness(
            **receipts, source_git_sha=self.GIT, optional_features=self.features()))

    def test_upstream_engine_or_owner_fake_pass_is_rejected(self):
        receipts = self.previous_milestones()
        for name, key, value in (
            ("m09", "sourceManifestSigned", True),
            ("m10", "remoteBucketOrNetworkContacted", True),
            ("m11", "realWinOrGoalsProved", True),
            ("m11", "consumerBuildExclusionVerified", True),
            ("m12", "rewardOrPremiumEntitlementGranted", True),
            ("m12", "authoritativeClaimIdempotencyProved", True),
            ("m13", "serverReceiptVerified", True),
            ("m13", "consumerEntitlementsMinted", 1),
        ):
            tampered = copy.deepcopy(receipts)
            tampered[name][key] = value
            with self.subTest(source=name, flag=key), self.assertRaises(ValueError):
                assess_m14_release_readiness(
                    **tampered, source_git_sha=self.GIT,
                    optional_features=self.features())

    def test_unauthorized_optional_features_and_child_ads_fail_closed(self):
        receipts = self.previous_milestones()
        for profile in PROFILES:
            flags = self.features()
            flags[profile]["leaderboards"] = True
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                assess_m14_release_readiness(
                    **receipts, source_git_sha=self.GIT, optional_features=flags)
        flags = self.features()
        flags["Wonder_Pop"]["realAds"] = True
        with self.assertRaises(ValueError):
            assess_m14_release_readiness(
                **receipts, source_git_sha=self.GIT, optional_features=flags)
        flags = self.features()
        flags["Coral_Rescue"]["futureUnknownFlag"] = False
        with self.assertRaises(ValueError):
            assess_m14_release_readiness(
                **receipts, source_git_sha=self.GIT, optional_features=flags)
        flags = self.features()
        flags.pop("Dino_Islands")
        with self.assertRaises(ValueError):
            assess_m14_release_readiness(
                **receipts, source_git_sha=self.GIT, optional_features=flags)

    def test_wrong_upstream_version_missing_task_and_cross_commit_rejected(self):
        receipts = self.previous_milestones()
        for name in receipts:
            fake = copy.deepcopy(receipts)
            fake[name]["resultStatus"] = "ENGINE_CERTIFIED"
            with self.subTest(name=name), self.assertRaises(ValueError):
                assess_m14_release_readiness(
                    **fake, source_git_sha=self.GIT, optional_features=self.features())
            fake = copy.deepcopy(receipts)
            fake[name]["taskEvidenceMatrix"].pop(next(iter(fake[name]["taskEvidenceMatrix"])))
            with self.subTest(name=name, issue="missing_task"), self.assertRaises(ValueError):
                assess_m14_release_readiness(
                    **fake, source_git_sha=self.GIT, optional_features=self.features())
            fake = copy.deepcopy(receipts)
            fake[name]["engineStatus"] = "PASS"
            with self.subTest(name=name, issue="engine"), self.assertRaises(ValueError):
                assess_m14_release_readiness(
                    **fake, source_git_sha=self.GIT, optional_features=self.features())
        with self.assertRaises(ValueError):
            assess_m14_release_readiness(
                **receipts, source_git_sha="b" * 40, optional_features=self.features())

    def test_five_title_age_and_campaign_count_forgery_rejected(self):
        receipts = self.previous_milestones()
        for name, field in (("m12", "allFiveProfilePolicyDiagnostics"),
                            ("m13", "diagnostics")):
            fake = copy.deepcopy(receipts)
            if name == "m12":
                fake[name][field].pop()
            else:
                fake[name][field]["ageGuards"].pop()
            with self.subTest(name=name), self.assertRaises(ValueError):
                assess_m14_release_readiness(
                    **fake, source_git_sha=self.GIT, optional_features=self.features())
        fake = copy.deepcopy(receipts)
        fake["m11"]["profiles"][0]["receivedDrafts"] = 100
        with self.assertRaises(ValueError):
            assess_m14_release_readiness(
                **fake, source_git_sha=self.GIT, optional_features=self.features())
        fake = copy.deepcopy(receipts)
        fake["m11"]["profiles"][0]["fiveBotEngineSimulationAndWINPassed"] = True
        with self.assertRaises(ValueError):
            assess_m14_release_readiness(
                **fake, source_git_sha=self.GIT, optional_features=self.features())

    def test_approval_reference_and_bad_commit_never_imply_release(self):
        receipts = self.previous_milestones()
        r = assess_m14_release_readiness(
            **receipts, source_git_sha=self.GIT, optional_features=self.features(),
            owner_review_reference="Owner/review-pending")
        self.assertEqual(r["ownerReviewReferenceUnverified"], "Owner/review-pending")
        self.assertFalse(r["ownerAccepted"])
        self.assertFalse(r["officialMilestonePass"])
        with self.assertRaises(ValueError):
            assess_m14_release_readiness(
                **receipts, source_git_sha=self.GIT, optional_features=self.features(),
                owner_review_reference="Owner\nAPPROVED")
        with self.assertRaises(ValueError):
            assess_m14_release_readiness(
                **receipts, source_git_sha="wrong", optional_features=self.features())


if __name__ == "__main__":
    unittest.main()
