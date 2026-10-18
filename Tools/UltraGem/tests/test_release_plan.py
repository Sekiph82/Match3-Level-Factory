from __future__ import annotations
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from release_plan import plan_platform_preview,plan_rollback_only,plan_r2_topology
from theme_contract import PROFILES

class ReleasePlanTests(unittest.TestCase):
    def test_five_profiles_three_platforms_and_locales_without_publish(self):
        for profile in PROFILES:
            for platform in ("android","ios","windows"):
                x=plan_platform_preview(profile_id=profile,channel="staging",platform=platform,locales=["tr","en"])
                self.assertEqual(x["locales"],["en","tr"])
                self.assertFalse(x["productionValid"])
                self.assertFalse(x["publishAuthorized"])
                self.assertEqual(x["engineStatus"],"BLOCKED_ENG_M24")
        with self.assertRaises(ValueError):
            plan_platform_preview(profile_id="Coral_Rescue",channel="production",platform="linux",locales=["en"])
        with self.assertRaises(ValueError):
            plan_platform_preview(profile_id="Wonder_Pop",channel="staging",platform="ios",locales=["tr","tr"])

    def test_rollback_metadata_requires_distinct_digests_never_mutates_pointer(self):
        plan=plan_rollback_only(previous_manifest_sha256="a"*64,next_manifest_sha256="b"*64,
                                previous_release_reference="Drive/accepted-R01")
        self.assertFalse(plan["previousAcceptanceIndependentlyVerified"])
        self.assertFalse(plan["atomicPointerSwitchAuthorized"])
        self.assertFalse(plan["uploadAuthorized"])
        with self.assertRaises(ValueError):
            plan_rollback_only(previous_manifest_sha256="a"*64,next_manifest_sha256="a"*64,
                               previous_release_reference="Drive/accepted-R01")

    def test_five_game_r2_paths_are_symbolic_and_never_uploaded(self):
        for game in PROFILES:
            levels=plan_r2_topology(profile_id=game,channel="staging",platform="ios",
                          content_kind="levels",content_sha256="c"*64)
            media=plan_r2_topology(profile_id=game,channel="staging",platform="ios",
                          content_kind="media",content_sha256="c"*64)
            self.assertNotEqual(levels["proposedRelativeObjectKey"],media["proposedRelativeObjectKey"])
            self.assertTrue(levels["proposedRelativeObjectKey"].startswith(game+"/staging/ios/"))
            self.assertIsNone(levels["bucketOrEndpoint"])
            self.assertFalse(levels["remoteWriteAuthorized"])
        with self.assertRaises(ValueError):
            plan_r2_topology(profile_id="Coral_Rescue",channel="production",platform="android",
                             content_kind="../secret",content_sha256="c"*64)

if __name__=="__main__":unittest.main()
