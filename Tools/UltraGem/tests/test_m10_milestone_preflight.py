"""One bounded all-M10 offline rehearsal: never certifies Engine or R2 access."""
from __future__ import annotations
import copy
import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from m10_milestone_preflight import preflight_m10_milestone
from theme_contract import PROFILES


class M10MilestonePreflightTests(unittest.TestCase):
    @staticmethod
    def item(game="Coral_Rescue", path="levels/ch1/l1.json",
             kind="level", body=b'{"version":1,"prototype":true}',
             rights="REFERENCE_ONLY"):
        return {
            "gameProfileId": game, "relativePath": path,
            "kind": kind, "body": body, "rightsStatus": rights
        }

    def run_one(self, **overrides):
        args = {
            "game_id": "Coral_Rescue", "channel": "staging",
            "platform": "android", "git_commit_sha": "c" * 40,
            "manifest_sha256": "d" * 64,
            "artifacts": [self.item()],
        }
        args.update(overrides)
        return preflight_m10_milestone(**args)

    def test_one_rehearsal_exposes_all_ten_tasks_without_any_real_writer(self):
        r = self.run_one()
        self.assertEqual(set(r["taskEvidenceMatrix"]),
                         {f"LFX-M10-{i:03d}" for i in range(1, 11)})
        self.assertEqual(r["engineStatus"], "BLOCKED_ENG_M24")
        self.assertEqual(r["resultStatus"], "M10_OFFLINE_MILESTONE_PREFLIGHT_ONLY")
        self.assertFalse(r["remoteBucketOrNetworkContacted"])
        self.assertFalse(r["writerCredentialsEverLoaded"])
        self.assertFalse(r["clientDownloadObserved"])
        self.assertFalse(r["offlinePlayerFallbackProved"])
        self.assertFalse(r["canaryAudienceReleased"])
        self.assertFalse(r["productionPointerModified"])
        self.assertFalse(r["ownerAccepted"])
        self.assertFalse(r["officialMilestonePass"])
        self.assertFalse(r["publishAuthorized"])
        self.assertEqual(r["inspectedLocalArtifacts"][0]["contentSha256"],
                         hashlib.sha256(self.item()["body"]).hexdigest())
        self.assertEqual(r, self.run_one(), "bounded offline plans must be deterministic")

    def test_all_five_profiles_three_platforms_nonproduction_and_prod_blocked(self):
        for game in PROFILES:
            for platform in ("android", "ios", "windows"):
                artifact = self.item(game=game)
                for channel in ("development", "staging", "production"):
                    with self.subTest(game=game, platform=platform, channel=channel):
                        r = self.run_one(game_id=game, platform=platform,
                                         channel=channel, artifacts=[artifact])
                        route = r["proposedR2PathsNotUploaded"][0]
                        self.assertTrue(route["proposedRelativeObjectKey"].startswith(
                            game + "/" + channel + "/" + platform + "/levels/"))
                        self.assertIsNone(route["bucketOrEndpoint"])
                        self.assertFalse(route["remoteWriteAuthorized"])
                        self.assertFalse(r["publishPreflight"]["publishAuthorized"])
                        if channel == "production":
                            self.assertIn("EXPLICIT_PRODUCTION_OWNER_APPROVAL_MISSING",
                                          r["publishPreflight"]["blockReasons"])

    def test_actual_artifact_bytes_and_media_rights_are_screened(self):
        objects = [
            self.item(),
            self.item(path="localization/en.json", kind="localization",
                      body=b'{"ui.title":"Example"}'),
            self.item(path="media/icon.svg", kind="media_svg",
                      rights="OWNER_ORIGINAL",
                      body=b'<svg xmlns="http://www.w3.org/2000/svg"><circle cx="1" cy="1" r="1"/></svg>'),
        ]
        original = copy.deepcopy(objects)
        r = self.run_one(artifacts=objects)
        self.assertEqual(objects, original)
        self.assertEqual(len(r["inspectedLocalArtifacts"]), 3)
        self.assertEqual(len(r["proposedR2PathsNotUploaded"]), 3)
        self.assertTrue(all(not x["distributionAuthorized"]
                            for x in r["inspectedLocalArtifacts"]))

    def test_wrong_game_code_kind_secret_and_duplicate_fail_closed(self):
        for case in ("foreign", "code", "hidden_secret", "duplicate", "wrong_rights"):
            a = self.item()
            if case == "foreign":
                a["gameProfileId"] = "Wonder_Pop"
            if case == "code":
                a["kind"] = "script"
            if case == "hidden_secret":
                a["relativePath"] = "levels/secret.json"
            if case == "wrong_rights":
                a = self.item(path="media/a.svg", kind="media_svg",
                              body=b'<svg xmlns="http://www.w3.org/2000/svg"/>')
            group = [a, copy.deepcopy(a)] if case == "duplicate" else [a]
            with self.subTest(case=case), self.assertRaises(ValueError):
                self.run_one(artifacts=group)

    def test_binary_and_malformed_json_svg_rejected_without_upload(self):
        for data, path, kind, rights in (
            (b"bad json", "levels/a.json", "level", "REFERENCE_ONLY"),
            (b'{"x":1,"x":2}', "levels/a.json", "level", "REFERENCE_ONLY"),
            (b'{"password":"secret"}', "levels/a.json", "level", "REFERENCE_ONLY"),
            (b'<svg xmlns="http://www.w3.org/2000/svg"><script/></svg>',
             "media/icon.svg", "media_svg", "OWNER_ORIGINAL"),
        ):
            with self.subTest(path=path, data=data), self.assertRaises(ValueError):
                self.run_one(artifacts=[self.item(path=path, kind=kind,
                                                    body=data, rights=rights)])

    def test_incident_disable_is_only_unverified_offline_proposal(self):
        level = {"worldId": "w1", "chapterId": "c1",
                 "levelId": "l1", "reason": "BAD_HASH"}
        with self.assertRaises(ValueError):
            self.run_one(incident_affected=[level])
        r = self.run_one(incident_affected=[level],
                         owner_review_reference="Owner/pending-review")
        d = r["disabledLevelIncidentProposal"]
        self.assertEqual(len(d["disabledLevels"]), 1)
        self.assertFalse(d["safeProgressFrontierVerified"])
        self.assertFalse(d["signedPatchGenerated"])
        self.assertFalse(d["publishAuthorized"])
        self.assertFalse(r["officialMilestonePass"])
        with self.assertRaises(ValueError):
            self.run_one(incident_affected=[dict(level, reason="UNLISTED")],
                         owner_review_reference="Owner/pending-review")

    def test_unverified_manifest_and_source_git_sha_rejected_if_malformed(self):
        for args in ({"manifest_sha256": "f" * 63},
                     {"git_commit_sha": "G" * 40},
                     {"platform": "playstation"},
                     {"channel": "local"},
                     {"game_id": "Other"},
                     {"artifacts": []},
                     {"artifacts": [dict(self.item(), unknownField=True)]}):
            with self.subTest(args=repr(args)[:100]), self.assertRaises(ValueError):
                self.run_one(**args)


if __name__ == "__main__":
    unittest.main()
