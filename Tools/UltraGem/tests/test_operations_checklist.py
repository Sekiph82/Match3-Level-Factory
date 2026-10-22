from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from operations_checklist import CHECKS, build_operations_checklist


class OperationsChecklistTests(unittest.TestCase):
    def references(self):
        return {key: f"ticket/M10-007-{index:02d}" for index, (key, _) in enumerate(CHECKS, 1)}

    def test_incomplete_checklist_names_missing_steps_and_keeps_all_actions_disabled(self):
        result = build_operations_checklist(profile_id="Coral_Rescue", incident_id="INC-712")
        self.assertEqual(result["checklistStatus"], "INCOMPLETE_REFERENCES")
        self.assertEqual(result["missingEvidenceCheckIds"], [key for key, _ in CHECKS])
        self.assertFalse(result["ownerApprovalVerified"])
        self.assertFalse(result["productionAuthorization"])
        self.assertFalse(result["publishAuthorized"])
        self.assertFalse(result["rollbackExecuted"])
        self.assertFalse(result["keyRotationExecuted"])
        self.assertFalse(result["networkOrProviderAccessPerformed"])

    def test_complete_candidate_references_remain_unverified_and_non_authorizing(self):
        result = build_operations_checklist(profile_id="Coral_Rescue", incident_id="INC-712",
                                            evidence_references=self.references())
        self.assertEqual(result["checklistStatus"], "CANDIDATE_REFERENCES_COMPLETE_UNVERIFIED")
        self.assertEqual(result["missingEvidenceCheckIds"], [])
        self.assertTrue(result["ownerApprovalReferenceRecorded"])
        self.assertFalse(result["ownerApprovalVerified"])
        self.assertFalse(result["evidenceReferencesVerified"])
        for name in ("productionEnabled", "productionAuthorization", "publishAuthorized",
                     "writerCredentialsLoaded", "networkOrProviderAccessPerformed",
                     "rollbackExecuted", "keyRotationExecuted", "keyRevocationExecuted",
                     "clientRollbackValidated", "officialTaskPass"):
            self.assertIs(result[name], False, name)
        self.assertTrue(all(row["executionPerformed"] is False for row in result["checks"]))
        self.assertEqual(result, build_operations_checklist(profile_id="Coral_Rescue", incident_id="INC-712",
                                            evidence_references=self.references()))

    def test_profile_incident_and_evidence_shape_reject_invalid_inputs(self):
        valid = self.references()
        cases = [
            {"profile_id": [], "incident_id": "INC-1", "evidence_references": {}},
            {"profile_id": "Unknown", "incident_id": "INC-1", "evidence_references": {}},
            {"profile_id": "Coral_Rescue", "incident_id": "../INC", "evidence_references": {}},
            {"profile_id": "Coral_Rescue", "incident_id": "INC-1", "evidence_references": []},
            {"profile_id": "Coral_Rescue", "incident_id": "INC-1", "evidence_references": {"secret": "x"}},
            {"profile_id": "Coral_Rescue", "incident_id": "INC-1", "evidence_references": {"owner_approval": "ticket/ok", "token": "secret"}},
            {"profile_id": "Coral_Rescue", "incident_id": "INC-1", "evidence_references": {"owner_approval": "ticket/../secret"}},
            {"profile_id": "Coral_Rescue", "incident_id": "INC-1", "evidence_references": {"owner_approval": "https://example.test/key"}},
            {"profile_id": "Coral_Rescue", "incident_id": "INC-1", "evidence_references": {"owner_approval": "drive/API_KEY=abc"}},
            {"profile_id": "Coral_Rescue", "incident_id": "INC-1", "evidence_references": {"owner_approval": "drive/secret"}},
            {"profile_id": "Coral_Rescue", "incident_id": "INC-1", "evidence_references": {"owner_approval": 42}},
        ]
        for kwargs in cases:
            with self.subTest(kwargs=repr(kwargs)[:100]), self.assertRaises(ValueError):
                build_operations_checklist(**kwargs)
        valid["owner_approval"] = "owner/approval-INC-712"
        self.assertFalse(build_operations_checklist(profile_id="Wonder_Pop", incident_id="INC-712",
                            evidence_references=valid)["productionAuthorization"])

    def test_output_contains_only_fixed_checks_and_no_secret_material_fields(self):
        result = build_operations_checklist(profile_id="Garage_Legends", incident_id="INC.1")
        self.assertEqual([row["checkId"] for row in result["checks"]], [key for key, _ in CHECKS])
        forbidden = {"password", "token", "secret", "privateKey", "credentialValue", "keyBytes"}
        self.assertFalse(forbidden.intersection(result))
        self.assertTrue(all("Unverified" in key or key in {"checkId", "requirement", "status", "executionPerformed"}
                            for row in result["checks"] for key in row))


if __name__ == "__main__":
    unittest.main()
