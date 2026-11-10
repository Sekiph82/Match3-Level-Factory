"""Tests for LFX-M14-003: Offline staging manifest validation — OTA replay."""
from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from m14_ota_replay import (
    apply_update,
    check_engine_compatibility,
    check_rollback,
    replay_staging_sequence,
    validate_manifest,
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_digest(manifest: dict) -> str:
    """Compute the integrityDigest over the canonical key set."""
    canonical = json.dumps(
        {k: manifest[k] for k in
         ("profileId", "version", "levelPackSha256", "schemaVersion")},
        sort_keys=True, separators=(",", ":"))
    return _sha256(canonical.encode())


FAKE_SHA = "a" * 64


def _manifest(profile: str = "Coral_Rescue",
              version: int = 1,
              sha: str = FAKE_SHA,
              schema: int = 1,
              engine_min: int = 1,
              claims: list | None = None,
              integrity: bool = False) -> dict:
    m: dict = {
        "profileId": profile,
        "version": version,
        "levelPackSha256": sha,
        "schemaVersion": schema,
        "engineSchemaVersionMin": engine_min,
    }
    if claims is not None:
        m["claimIds"] = claims
    if integrity:
        m["integrityDigest"] = _canonical_digest(m)
    return m


class TestValidateManifest(unittest.TestCase):
    def test_valid_minimal(self):
        r = validate_manifest(_manifest())
        self.assertEqual(r["status"], "VALID")
        self.assertEqual(r["profileId"], "Coral_Rescue")
        self.assertEqual(r["version"], 1)
        self.assertFalse(r["productionAuthorized"])
        self.assertTrue(r["prototype"])

    def test_valid_with_integrity(self):
        m = _manifest(integrity=True)
        r = validate_manifest(m)
        self.assertEqual(r["integrityStatus"], "VALID")
        self.assertEqual(r["status"], "VALID")

    def test_corrupted_integrity_digest(self):
        m = _manifest()
        m["integrityDigest"] = "b" * 64  # wrong
        r = validate_manifest(m)
        self.assertEqual(r["integrityStatus"], "CORRUPTED")
        self.assertEqual(r["status"], "CORRUPTED")

    def test_claims_preserved(self):
        m = _manifest(claims=["clm-001", "clm-002"])
        r = validate_manifest(m)
        self.assertEqual(r["claimsPreserved"], ["clm-001", "clm-002"])

    def test_all_five_profiles(self):
        for p in ("Coral_Rescue", "Garage_Legends", "Dino_Islands",
                  "The_Fractured_Realms", "Wonder_Pop"):
            r = validate_manifest(_manifest(profile=p))
            self.assertEqual(r["profileId"], p)

    def test_invalid_profile(self):
        with self.assertRaises(ValueError):
            validate_manifest(_manifest(profile="Unknown_Game"))

    def test_missing_field(self):
        m = _manifest()
        del m["levelPackSha256"]
        with self.assertRaises((ValueError, KeyError)):
            validate_manifest(m)

    def test_version_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_manifest(_manifest(version=0))

    def test_bad_sha_rejected(self):
        with self.assertRaises(ValueError):
            validate_manifest(_manifest(sha="tooshort"))

    def test_schema_version_out_of_range(self):
        with self.assertRaises(ValueError):
            validate_manifest(_manifest(schema=99))

    def test_engine_min_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_manifest(_manifest(engine_min=0))

    def test_non_dict_rejected(self):
        with self.assertRaises(ValueError):
            validate_manifest([])

    def test_bad_claim_type_rejected(self):
        m = _manifest()
        m["claimIds"] = [123]  # int instead of str
        with self.assertRaises(ValueError):
            validate_manifest(m)

    def test_empty_claim_id_rejected(self):
        m = _manifest()
        m["claimIds"] = [""]
        with self.assertRaises(ValueError):
            validate_manifest(m)


class TestApplyUpdate(unittest.TestCase):
    def test_basic_update(self):
        old = _manifest(version=1, claims=["clm-1"])
        new = _manifest(version=2, claims=["clm-2"])
        r = apply_update(old, new)
        self.assertEqual(r["status"], "UPDATE_APPLIED")
        self.assertEqual(r["oldVersion"], 1)
        self.assertEqual(r["newVersion"], 2)
        # Both claims merged
        self.assertIn("clm-1", r["claimsPreserved"])
        self.assertIn("clm-2", r["claimsPreserved"])
        self.assertFalse(r["productionAuthorized"])

    def test_rollback_sha_recorded(self):
        old = _manifest(version=1)
        new = _manifest(version=2)
        r = apply_update(old, new)
        # rollbackManifestSha256 should be non-empty 64-char hex
        self.assertRegex(r["rollbackManifestSha256"], r"[0-9a-f]{64}")

    def test_same_version_rejected(self):
        m = _manifest(version=1)
        with self.assertRaises(ValueError):
            apply_update(m, _manifest(version=1))

    def test_downgrade_rejected(self):
        with self.assertRaises(ValueError):
            apply_update(_manifest(version=3), _manifest(version=2))

    def test_profile_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            apply_update(_manifest(profile="Coral_Rescue"),
                         _manifest(profile="Dino_Islands"))

    def test_corrupted_old_rejected(self):
        old = _manifest()
        old["integrityDigest"] = "c" * 64  # corrupt
        with self.assertRaises(ValueError):
            apply_update(old, _manifest(version=2))

    def test_corrupted_new_rejected(self):
        new = _manifest(version=2)
        new["integrityDigest"] = "c" * 64  # corrupt
        with self.assertRaises(ValueError):
            apply_update(_manifest(version=1), new)


class TestCheckRollback(unittest.TestCase):
    def test_valid_rollback(self):
        cur = _manifest(version=3, claims=["clm-3"])
        prev = _manifest(version=1, claims=["clm-1"])
        r = check_rollback(cur, prev)
        self.assertEqual(r["status"], "ROLLBACK_ELIGIBLE")
        self.assertEqual(r["currentVersion"], 3)
        self.assertEqual(r["rollbackVersion"], 1)
        self.assertIn("clm-1", r["claimsPreserved"])
        self.assertIn("clm-3", r["claimsPreserved"])

    def test_rollback_to_higher_version_rejected(self):
        with self.assertRaises(ValueError):
            check_rollback(_manifest(version=1), _manifest(version=2))

    def test_rollback_to_same_version_rejected(self):
        with self.assertRaises(ValueError):
            check_rollback(_manifest(version=2), _manifest(version=2))

    def test_corrupted_target_rejected(self):
        prev = _manifest(version=1)
        prev["integrityDigest"] = "d" * 64  # corrupt
        with self.assertRaises(ValueError):
            check_rollback(_manifest(version=2), prev)

    def test_profile_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            check_rollback(_manifest(profile="Coral_Rescue", version=2),
                           _manifest(profile="Garage_Legends", version=1))


class TestCheckEngineCompatibility(unittest.TestCase):
    def test_compatible(self):
        m = _manifest(engine_min=1)
        r = check_engine_compatibility(m, installed_version=1)
        self.assertEqual(r["compatibilityStatus"], "COMPATIBLE")

    def test_compatible_higher_installed(self):
        m = _manifest(engine_min=1)
        r = check_engine_compatibility(m, installed_version=5)
        self.assertEqual(r["compatibilityStatus"], "COMPATIBLE")

    def test_incompatible(self):
        m = _manifest(engine_min=5)
        r = check_engine_compatibility(m, installed_version=1)
        self.assertEqual(r["compatibilityStatus"], "INCOMPATIBLE")

    def test_zero_installed_rejected(self):
        with self.assertRaises(ValueError):
            check_engine_compatibility(_manifest(), installed_version=0)

    def test_negative_installed_rejected(self):
        with self.assertRaises(ValueError):
            check_engine_compatibility(_manifest(), installed_version=-1)

    def test_engine_status_always_blocked(self):
        r = check_engine_compatibility(_manifest(), installed_version=1)
        self.assertEqual(r["engineStatus"], "BLOCKED_ENG_M24")


class TestReplayStagingSequence(unittest.TestCase):
    def test_two_step_sequence(self):
        seq = [_manifest(version=1, claims=["clm-1"]),
               _manifest(version=2, claims=["clm-2"])]
        r = replay_staging_sequence(seq)
        self.assertEqual(r["status"], "SEQUENCE_REPLAYED")
        self.assertEqual(r["steps"], 2)
        self.assertEqual(r["finalVersion"], 2)
        self.assertIn("clm-1", r["claimsPreserved"])
        self.assertIn("clm-2", r["claimsPreserved"])
        self.assertFalse(r["productionAuthorized"])
        self.assertFalse(r["officialMilestonePass"])

    def test_three_step_sequence(self):
        seq = [_manifest(version=1),
               _manifest(version=2),
               _manifest(version=3)]
        r = replay_staging_sequence(seq)
        self.assertEqual(r["finalVersion"], 3)
        self.assertEqual(r["steps"], 3)

    def test_single_item_rejected(self):
        with self.assertRaises(ValueError):
            replay_staging_sequence([_manifest(version=1)])

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            replay_staging_sequence([])

    def test_non_monotonic_sequence_rejected(self):
        seq = [_manifest(version=1),
               _manifest(version=3),
               _manifest(version=2)]  # downgrade
        with self.assertRaises(ValueError):
            replay_staging_sequence(seq)

    def test_prototype_always_true(self):
        seq = [_manifest(version=1), _manifest(version=2)]
        r = replay_staging_sequence(seq)
        self.assertTrue(r["prototype"])


if __name__ == "__main__":
    unittest.main()
