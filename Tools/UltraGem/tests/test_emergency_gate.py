from __future__ import annotations
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from emergency_gate import propose_emergency_gate
from theme_contract import PROFILES

class EmergencyGateTests(unittest.TestCase):
    def call(self,game="Coral_Rescue",enabled=False,kind="LEVEL"):
        return propose_emergency_gate(game_id=game,content_kind=kind,
                content_id="world1.level10",requested_enabled=enabled,
                reason="Bad level observed in reference QA; preserve old player progress.",
                current_manifest_sha256="c"*64,owner_review_reference="Owner/hotfix-approval")
    def test_five_game_disable_and_reenable_stay_proposals(self):
        for game in PROFILES:
            for enabled in (False,True):
                result=self.call(game,enabled)
                self.assertEqual(result["reEnableRequiresSignedRollbackOrRelease"],enabled)
                self.assertFalse(result["playerSaveOrClaimsModified"])
                self.assertFalse(result["remoteConfigChanged"])
                self.assertFalse(result["productionAuthorized"])
                self.assertFalse(result["compatibilityMatrixVerified"])
                self.assertEqual(result["engineStatus"],"BLOCKED_ENG_M24")
    def test_bad_reason_unknown_kind_or_user_grant_not_accepted(self):
        with self.assertRaises(ValueError):self.call(kind="PREMIUM_REWARD_GRANT")
        with self.assertRaises(ValueError):
            propose_emergency_gate(game_id="Coral_Rescue",content_kind="LEVEL",
                   content_id="world1.level10",requested_enabled=False,
                   reason="ok",current_manifest_sha256="c"*64,
                   owner_review_reference="Owner/hotfix-approval")
        with self.assertRaises(ValueError):
            propose_emergency_gate(game_id="Coral_Rescue",content_kind="LEVEL",
                   content_id="../evil",requested_enabled=False,
                   reason="Suspicious content cannot be enabled without legitimate approval.",
                   current_manifest_sha256="c"*64,owner_review_reference="Owner/hotfix-approval")
if __name__=="__main__":unittest.main()
