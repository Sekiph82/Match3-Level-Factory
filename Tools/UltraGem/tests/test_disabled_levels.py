from __future__ import annotations
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from disabled_levels import propose_disabled_levels


class DisabledLevelsTests(unittest.TestCase):
    def entry(self,**replace):
        v={"worldId":"world.prototype","chapterId":"chapter.prototype",
           "levelId":"level.seed-712","reason":"BAD_HASH"}
        v.update(replace)
        return v
    def request(self,affected):
        return propose_disabled_levels(game_id="Coral_Rescue",manifest_sha256="a"*64,
               affected=affected,owner_review_reference="Owner/disable-level-R01")
    def test_deterministic_recovery_plan_does_not_fake_grants_or_delete(self):
        p=self.request([self.entry(),self.entry(levelId="level.seed-713",reason="CRASH_ON_OPEN")])
        self.assertEqual(len(p["disabledLevels"]),2)
        self.assertFalse(p["safeProgressFrontierVerified"])
        self.assertFalse(p["fakeWinOrStarGranted"])
        self.assertFalse(p["levelRewardsModified"])
        self.assertFalse(p["remoteObjectsDeleted"])
        self.assertFalse(p["reenableAuthorized"])
        self.assertFalse(p["publishAuthorized"])
        self.assertEqual(p["engineStatus"],"BLOCKED_ENG_M24")
        self.assertEqual(p,self.request(list(reversed([self.entry(),self.entry(levelId="level.seed-713",reason="CRASH_ON_OPEN")]))))
    def test_invalid_reason_duplicate_and_wrong_game_fail_closed(self):
        with self.assertRaises(ValueError):self.request([self.entry(reason="FORCE_WIN")])
        with self.assertRaises(ValueError):self.request([self.entry(),self.entry()])
        with self.assertRaises(ValueError):self.request([self.entry(levelId="../sandbox")])
        with self.assertRaises(ValueError):
            propose_disabled_levels(game_id="UNKNOWN",manifest_sha256="a"*64,
                   affected=[self.entry()],owner_review_reference="Owner/source-review")

if __name__=="__main__":
    unittest.main()
