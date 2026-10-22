from __future__ import annotations
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from theme_contract import (all_five_theme_contracts, create_symbolic_theme_contract,
                            COMMON_SLOTS, GENERIC_PLACEHOLDER)

def rights_entry(*, status="OWNER_ORIGINAL", source="ref:Owner/original-icon-v1",
                 proof="evidence:owner-proof-v1"):
    return {"profileId":"Coral_Rescue","slotId":"ui.goal","kind":"UI_ICON",
            "rightsStatus":status,"sourceReference":source,"contentSha256":"a"*64,
            "permissionEvidenceReference":proof,"scope":"LOCAL_EDITOR_PREVIEW_ONLY"}

class ThemeContractTests(unittest.TestCase):
    def test_every_profile_has_neutral_slots_not_game_authority(self):
        t=all_five_theme_contracts()
        self.assertEqual(len(t),5)
        self.assertEqual(len({x["profileId"] for x in t}),5)
        for x in t:
            self.assertEqual(len(x["slots"]),len(COMMON_SLOTS))
            self.assertFalse(x["releaseAuthorized"])
            self.assertTrue(x["doesNotModifyGameplay"])
            self.assertEqual(x["engineStatus"],"BLOCKED_ENG_M24")
            self.assertEqual(x["rightsAuditStatus"],"RIGHTS_INTAKE_ONLY")
            self.assertFalse(x["rightsDistributionAuthorized"])
            self.assertTrue(all(z["placeholderWhenMissing"]==GENERIC_PLACEHOLDER for z in x["slots"]))
            self.assertTrue(all(z["rightsMetadata"]["rightsStatus"]=="RIGHTS_UNKNOWN" for z in x["slots"]))
    def test_symbolic_path_override_rejects_unknown_and_traversal(self):
        a=create_symbolic_theme_contract("Coral_Rescue",slot_assignments={"ui.goal":"ref:Owner/original-icon-v1"})
        self.assertTrue(any(x["symbolicBinding"]=="ref:Owner/original-icon-v1" for x in a["slots"]))
        for settings in ({"unknown":"ref:Owner/asset"},{"ui.goal":"../../secrets"},
                         {"ui.goal":"ref:x/../z"}):
            with self.assertRaises(ValueError):
                create_symbolic_theme_contract("Coral_Rescue",slot_assignments=settings)
        with self.assertRaises(ValueError):
            create_symbolic_theme_contract("WrongProfile")

    def test_theme_binding_links_exact_rights_source_without_granting_production(self):
        contract=create_symbolic_theme_contract("Coral_Rescue",
            slot_assignments={"ui.goal":"ref:Owner/original-icon-v1"},
            rights_entries=[rights_entry()])
        slot=next(x for x in contract["slots"] if x["slotId"]=="ui.goal")
        self.assertEqual(slot["symbolicBinding"],"ref:Owner/original-icon-v1")
        self.assertEqual(slot["rightsMetadata"]["rightsStatus"],"OWNER_ORIGINAL")
        self.assertTrue(slot["rightsMetadata"]["localPreviewCandidate"])
        self.assertTrue(slot["rightsMetadata"]["requiresHumanRightsReview"])
        self.assertFalse(slot["rightsMetadata"]["productionDistributionAuthorized"])
        self.assertFalse(contract["rightsDistributionAuthorized"])

    def test_theme_rights_source_mismatch_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"does not match independent rights source"):
            create_symbolic_theme_contract("Coral_Rescue",
                slot_assignments={"ui.goal":"ref:Owner/original-icon-v1"},
                rights_entries=[rights_entry(source="ref:Owner/other-icon-v1")])

    def test_unknown_or_unlicensed_rights_never_become_preview_permission(self):
        contract=create_symbolic_theme_contract("Coral_Rescue",
            slot_assignments={"ui.goal":"ref:Owner/original-icon-v1"},
            rights_entries=[rights_entry(status="RIGHTS_UNKNOWN",proof=None)])
        slot=next(x for x in contract["slots"] if x["slotId"]=="ui.goal")
        self.assertFalse(slot["rightsMetadata"]["localPreviewCandidate"])
        self.assertFalse(slot["rightsMetadata"]["productionDistributionAuthorized"])

if __name__=="__main__": unittest.main()
