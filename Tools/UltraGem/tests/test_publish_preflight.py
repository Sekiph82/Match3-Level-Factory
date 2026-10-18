from __future__ import annotations
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from publish_preflight import assess_remote_publish_preflight

class PublishPreflightTests(unittest.TestCase):
    def test_stage_and_production_cannot_bypass_engine_gate(self):
        for channel in ("development","staging","production"):
            p=assess_remote_publish_preflight(channel=channel,game_id="Coral_Rescue",
                    manifest_sha256="a"*64,owner_approval_reference="Owner/approval-reference",
                    preview_confirmed=True)
            self.assertEqual(p["resultStatus"],"PUBLISH_PREFLIGHT_BLOCKED")
            self.assertFalse(p["publishAuthorized"])
            self.assertFalse(p["networkOrStorageAccessPerformed"])
            self.assertFalse(p["writerCredentialsAvailable"])
            self.assertIn("ENG_M24_FINAL_PACKAGE_NOT_INDEPENDENTLY_ACCEPTED",p["blockReasons"])
        p=assess_remote_publish_preflight(channel="production",game_id="Wonder_Pop",
                      manifest_sha256="a"*64)
        self.assertIn("EXPLICIT_PRODUCTION_OWNER_APPROVAL_MISSING",p["blockReasons"])
        self.assertIn("OWNER_PREVIEW_NOT_CONFIRMED",p["blockReasons"])
    def test_wrong_game_channel_or_manifest_fails_closed(self):
        for args in (dict(channel="prod",game_id="Coral_Rescue",manifest_sha256="a"*64),
                     dict(channel="staging",game_id="Other",manifest_sha256="a"*64),
                     dict(channel="staging",game_id="Coral_Rescue",manifest_sha256="not_a_sha")):
            with self.assertRaises(ValueError):
                assess_remote_publish_preflight(**args)

if __name__=="__main__":unittest.main()
