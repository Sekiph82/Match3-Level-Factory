from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from operations_checklist import (
    CHECKS,
    build_operations_checklist,
    build_operations_checklist_from_json,
)


class OperationsChecklistTests(unittest.TestCase):
    def references(self):
        return {key: f"ticket/LFX-M10-007-{index:02d}" for index, (key, _) in enumerate(CHECKS, 1)}

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

    def test_partial_reference_set_reports_only_the_stable_missing_check_id(self):
        references = self.references()
        del references["known_good_manifest"]
        result = build_operations_checklist(
            profile_id="Coral_Rescue", incident_id="INC-712",
            evidence_references=references,
        )
        self.assertEqual(result["missingEvidenceCheckIds"], ["known_good_manifest"])
        row = next(item for item in result["checks"] if item["checkId"] == "known_good_manifest")
        self.assertEqual(row["status"], "MISSING")

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
            {"profile_id": "Coral_Rescue", "incident_id": "INC-1", "evidence_references": {"owner_approval": "provider/ghp_" + "a" * 36}},
            {"profile_id": "Coral_Rescue", "incident_id": "INC-1", "evidence_references": {"owner_approval": "provider/sk_live_" + "b" * 24}},
            {"profile_id": "Coral_Rescue", "incident_id": "INC-1", "evidence_references": {"owner_approval": "provider/github_pat_" + "c" * 32}},
            {"profile_id": "Coral_Rescue", "incident_id": "INC-1", "evidence_references": {"owner_approval": "provider/xoxb-" + "d" * 24}},
            {"profile_id": "Coral_Rescue", "incident_id": "INC-1", "evidence_references": {"owner_approval": "provider/glpat-" + "e" * 28}},
            {"profile_id": "Coral_Rescue", "incident_id": "INC-1", "evidence_references": {"owner_approval": "provider/npm_" + "f" * 32}},
            {"profile_id": "Coral_Rescue", "incident_id": "INC-1", "evidence_references": {"owner_approval": "ticket/glpat-" + "g" * 28}},
            {"profile_id": "Coral_Rescue", "incident_id": "INC-1", "evidence_references": {"owner_approval": "drive/sk-proj-" + "h" * 32}},
            {"profile_id": "Coral_Rescue", "incident_id": "INC-1", "evidence_references": {"owner_approval": 42}},
        ]
        for kwargs in cases:
            with self.subTest(kwargs=repr(kwargs)[:100]), self.assertRaises(ValueError):
                build_operations_checklist(**kwargs)
        valid["owner_approval"] = "owner/APPROVAL-INC-712"
        self.assertFalse(build_operations_checklist(profile_id="Wonder_Pop", incident_id="INC-712",
                            evidence_references=valid)["productionAuthorization"])

    def test_overlong_control_character_and_forged_authorization_inputs_reject(self):
        for reference in ("owner/" + "a" * 123, "owner/approval\nforged"):
            with self.subTest(reference=reference[:20]), self.assertRaises(ValueError):
                build_operations_checklist(
                    profile_id="Coral_Rescue", incident_id="INC-712",
                    evidence_references={"owner_approval": reference},
                )
        with self.assertRaisesRegex(ValueError, "unknown checklist evidence reference"):
            build_operations_checklist(
                profile_id="Coral_Rescue", incident_id="INC-712",
                evidence_references={"productionAuthorization": "owner/approved"},
            )
        with self.assertRaises(TypeError):
            build_operations_checklist(
                profile_id="Coral_Rescue", incident_id="INC-712",
                productionAuthorization=True,
            )

    def test_output_contains_only_fixed_checks_and_no_secret_material_fields(self):
        result = build_operations_checklist(profile_id="Garage_Legends", incident_id="INC.1")
        self.assertEqual([row["checkId"] for row in result["checks"]], [key for key, _ in CHECKS])
        forbidden = {"password", "token", "secret", "privateKey", "credentialValue", "keyBytes"}
        self.assertFalse(forbidden.intersection(result))
        self.assertTrue(all("Unverified" in key or key in {"checkId", "requirement", "status", "executionPerformed"}
                            for row in result["checks"] for key in row))

    def test_json_entry_point_rejects_duplicate_keys_before_dict_conversion(self):
        cases = [
            '{"owner_approval":"ticket/first","owner_approval":"ticket/second"}',
            '{"outer":{"reference":"ticket/first","reference":"ticket/second"}}',
        ]
        for payload in cases:
            with self.subTest(payload=payload), self.assertRaisesRegex(ValueError, "duplicate JSON object key"):
                build_operations_checklist_from_json(
                    profile_id="Coral_Rescue", incident_id="INC-712",
                    evidence_references_json=payload,
                )

    def test_json_entry_point_is_bounded_and_uses_the_same_reference_validation(self):
        payload = json.dumps(self.references(), sort_keys=True)
        parsed = build_operations_checklist_from_json(
            profile_id="Coral_Rescue", incident_id="INC-712",
            evidence_references_json=payload,
        )
        direct = build_operations_checklist(
            profile_id="Coral_Rescue", incident_id="INC-712",
            evidence_references=self.references(),
        )
        self.assertEqual(parsed, direct)
        invalid_payloads = ["[]", "not-json", '{"owner_approval": NaN}', " " * 4097]
        for raw in invalid_payloads:
            with self.subTest(raw=raw[:20]), self.assertRaises(ValueError):
                build_operations_checklist_from_json(
                    profile_id="Coral_Rescue", incident_id="INC-712",
                    evidence_references_json=raw,
                )


if __name__ == "__main__":
    unittest.main()
