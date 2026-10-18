"""Optional modes cannot bypass Engine/child policy."""
from __future__ import annotations
import copy
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import leveldraft
from optional_modes import propose_optional_mode

class OptionalModesTests(unittest.TestCase):
    def fixture(self):
        p=ROOT.parents[1]/"Assets/Match3Factory/Tests/Fixtures/ultragem_seed_712_draft.json"
        return leveldraft.loads_strict(p.read_text(encoding="utf-8"))
    def test_time_attack_prototype_preserves_original(self):
        source=self.fixture()
        snapshot=copy.deepcopy(source)
        out=propose_optional_mode(source,expected_sha256=leveldraft.sha256(source),
              mode="TIME_ATTACK",owner_request_reference="Owner/time-attack-v1",time_limit_seconds=120)
        self.assertEqual(source,snapshot)
        self.assertTrue(out["levelDraftV1CanRepresentMode"])
        self.assertEqual(out["authoringDraft"]["timeLimitSeconds"],120)
        self.assertTrue(out["authoringDraft"]["timedMode"])
        self.assertEqual(out["proposalDraftSha256"],leveldraft.sha256(out["authoringDraft"]))
        self.assertNotEqual(out["proposalDraftSha256"],out["sourceDraftSha256"])
        self.assertFalse(out["productionAuthorized"])
        self.assertFalse(out["economyModified"])
        self.assertEqual(out["engineStatus"],"BLOCKED_ENG_M24")
    def test_endless_stays_unrepresentable_and_no_fabricated_draft(self):
        source=self.fixture()
        out=propose_optional_mode(source,expected_sha256=leveldraft.sha256(source),
           mode="ENDLESS",owner_request_reference="Owner/endless-v1")
        self.assertFalse(out["levelDraftV1CanRepresentMode"])
        self.assertIsNone(out["proposalDraftSha256"])
        self.assertIsNone(out["authoringDraft"])
        with self.assertRaises(ValueError):
            propose_optional_mode(source,expected_sha256=leveldraft.sha256(source),
              mode="ENDLESS",owner_request_reference="Owner/endless-v1",time_limit_seconds=99)
    def test_wonder_pop_child_safeguard_and_hash_guard(self):
        source=self.fixture()
        source["gameProfileId"]="Wonder_Pop"
        digest=leveldraft.sha256(source)
        with self.assertRaises(ValueError):
            propose_optional_mode(source,expected_sha256=digest,mode="TIME_ATTACK",
              owner_request_reference="Owner/child-mode-request",time_limit_seconds=90)
        allowed=propose_optional_mode(source,expected_sha256=digest,mode="TIME_ATTACK",
              owner_request_reference="Owner/child-mode-request",age_review_reference="Owner/age-review-002",time_limit_seconds=90)
        self.assertFalse(allowed["productionAuthorized"])
        with self.assertRaises(ValueError):
            propose_optional_mode(source,expected_sha256="0"*64,mode="ENDLESS",
              owner_request_reference="Owner/request",age_review_reference="Owner/age-review-002")

if __name__=="__main__":
    unittest.main()
