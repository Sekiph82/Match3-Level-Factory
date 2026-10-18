from __future__ import annotations
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from asset_rights import audit_asset_bindings


class AssetRightsTests(unittest.TestCase):
    def record(self, **overrides):
        src = {
            "profileId": "Coral_Rescue", "slotId": "ui.level.gem",
            "kind": "SPRITE", "rightsStatus": "OWNER_ORIGINAL",
            "sourceReference": "Owner/image-sheet-v1",
            "contentSha256": "a"*64,
            "permissionEvidenceReference": "Owner/original-art-record",
            "scope": "LOCAL_EDITOR_PREVIEW_ONLY",
        }
        src.update(overrides)
        return src

    def test_neutral_original_preview_not_a_commercial_license(self):
        r = audit_asset_bindings([self.record()])
        self.assertEqual(r["blocked"], 0)
        self.assertTrue(r["entries"][0]["localPreviewCandidate"])
        self.assertFalse(r["entries"][0]["productionDistributionAuthorized"])
        self.assertFalse(r["distributionAuthorized"])
        self.assertEqual(r["engineStatus"], "BLOCKED_ENG_M24")

    def test_missing_license_noncommercial_reference_and_duplicate_slot_block(self):
        for kind in ("REFERENCE_ONLY", "UNLICENSED", "RIGHTS_UNKNOWN"):
            with self.subTest(kind=kind):
                r = audit_asset_bindings([self.record(rightsStatus=kind)])
                self.assertEqual(r["blocked"], 1)
        self.assertEqual(audit_asset_bindings([self.record(permissionEvidenceReference=None)])["blocked"], 1)
        with self.assertRaises(ValueError):
            audit_asset_bindings([self.record(), self.record()])
        with self.assertRaises(ValueError):
            audit_asset_bindings([self.record(rightsStatus="ASSUMED_FREE")])
        with self.assertRaises(ValueError):
            audit_asset_bindings([self.record(scope="ANYWHERE")])

if __name__ == "__main__":
    unittest.main()
